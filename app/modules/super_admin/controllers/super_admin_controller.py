"""
Super Admin controller – business logic from routers/super_admin.py
"""
import asyncio
import csv
import io
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, delete as sql_delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings, get_upload_dir
import os
import uuid as uuid_lib

from fastapi import UploadFile
from app.modules.jobs_portal.models.application import Application, ApplicationStatus
from app.modules.jobs_portal.models.assessment import AssessmentResult, AssessmentSession
from app.modules.jobs_portal.models.interview import Interview
from app.modules.jobs_portal.models.job import JobPosting
from app.modules.jobs_portal.models.match import Match
from app.modules.jobs_portal.models.portfolio import Portfolio
from app.modules.jobs_portal.models.resume import Resume
from app.modules.jobs_portal.models.roadmap import Milestone, Resource, Roadmap
from app.shared.models.user import CompanyType, JobType, User, UserRole
from app.modules.super_admin.schemas.super_admin import (
    AdminApplicationListItem, AdminApplicationListResponse, AdminAssessmentListItem,
    AdminAssessmentListResponse, AdminInterviewListItem, AdminInterviewListResponse,
    AdminJobListItem, AdminJobListResponse, AdminMatchListItem, AdminMatchListResponse,
    AdminProviderCreate, AdminProviderUpdate, AdminSeekerCreate, AdminSeekerUpdate,
    AdminSetPasswordRequest, AdminUserExportRequest, AdminUserListResponse, AdminUserOut,
    BulkImportJobStarted, DashboardAnalyticsResponse, DetailedPlatformAnalytics, ImportJobStatus,
    PlatformStatsResponse, SuperAdminChangePasswordRequest, SuperAdminLoginRequest,
    SuperAdminLoginResponse, SuperAdminProfileOut, SuperAdminProfileUpdate,
)
from app.modules.super_admin.schemas.super_admin_detail import (
    AdminProviderDetailResponse, AdminSeekerDetailResponse,
    ProviderJobItem, SeekerApplicationItem,
    ProviderInterviewItem, SeekerInterviewItem,
)
from app.core.dependencies import create_access_token, create_refresh_token, hash_password, verify_password, async_hash_password, async_verify_password
from app.modules.super_admin.services.import_job_store import create_job as _create_job, get_job as _get_job
from app.modules.super_admin.services.super_admin_analytics import get_detailed_platform_analytics
from app.modules.jobs_portal.services.dashboard_analytics import get_dashboard_analytics
from app.modules.super_admin.services.super_admin_bulk_import import run_bulk_import_job
from app.modules.jobs_portal.services.portfolio_service import (
    calculate_completion,
    normalize_education,
    normalize_skills,
    normalize_work_experiences,
)
from app.modules.super_admin.services.super_admin_utils import normalize_phone as _normalize_phone, temp_password as _temp_password


def _build_user_search_filter(search: str, include_company: bool = False):
    term = f"%{search.strip()}%"
    full_name_expr = func.concat(func.coalesce(User.first_name, ""), " ", func.coalesce(User.last_name, ""))
    predicates = [
        User.first_name.ilike(term), User.last_name.ilike(term), full_name_expr.ilike(term),
        User.email.ilike(term), User.phone.ilike(term),
    ]
    if include_company:
        predicates.append(User.company_name.ilike(term))
    return or_(*predicates)


def _user_to_admin_out(
    user: User,
    role_label: str,
    profile_completion_percentage: Optional[int] = None,
    registered_job_fairs: Optional[List[str]] = None,
    has_resume: Optional[bool] = None,
    last_active_at: Optional[datetime] = None,
) -> AdminUserOut:
    job_type = user.job_type.value if user.job_type and hasattr(user.job_type, "value") else user.job_type
    company_type = user.company_type.value if user.company_type and hasattr(user.company_type, "value") else user.company_type
    resolved_last_active = last_active_at if last_active_at is not None else getattr(user, "last_login_at", None)
    return AdminUserOut(
        id=user.id, first_name=user.first_name, last_name=user.last_name, email=user.email,
        profile_pic_url=user.profile_pic_url, phone=user.phone, role=role_label,
        has_password=bool(user.hashed_password), is_verified=user.is_verified,
        onboarding_complete=user.onboarding_complete, industry=user.industry, job_role=user.job_role,
        job_type=job_type, salary_range=user.salary_range, experience=user.experience,
        company_name=user.company_name, company_type=company_type, company_location=user.company_location,
        company_size=user.company_size, profile_completion_percentage=profile_completion_percentage,
        welcome_email_status=user.welcome_email_status, welcome_email_error=user.welcome_email_error,
        has_resume=has_resume, created_at=user.created_at,
        last_active_at=resolved_last_active,
        registered_job_fairs=registered_job_fairs,
    )


async def _last_active_map(db: AsyncSession, user_ids: List[str]) -> dict:
    """Best-effort last activity: max(user.last_login_at, latest auth_session.last_active_at)."""
    if not user_ids:
        return {}
    from app.shared.models.auth_session import AuthSession

    result = await db.execute(
        select(AuthSession.user_id, func.max(AuthSession.last_active_at))
        .where(AuthSession.user_id.in_(user_ids))
        .group_by(AuthSession.user_id)
    )
    session_map = {uid: ts for uid, ts in result.all() if uid and ts}

    users = await db.execute(select(User.id, User.last_login_at).where(User.id.in_(user_ids)))
    out: dict = {}
    for uid, login_at in users.all():
        candidates = [t for t in (login_at, session_map.get(uid)) if t is not None]
        out[uid] = max(candidates) if candidates else None
    return out


async def _seeker_has_resume_ids(db: AsyncSession, user_ids: List[str]) -> set:
    """Same rule as job-fair seeker_resume_url: Resume row exists for the seeker."""
    if not user_ids:
        return set()
    result = await db.execute(
        select(Resume.user_id).where(Resume.user_id.in_(user_ids)).distinct()
    )
    return {row[0] for row in result.all()}


async def _seeker_has_resume(db: AsyncSession, user_id: str) -> bool:
    """Same rule as job-fair seeker_resume_url: Resume row exists for the seeker."""
    result = await db.execute(
        select(Resume.id).where(Resume.user_id == user_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _check_duplicate(db: AsyncSession, email: str, phone: str, exclude_id: Optional[str] = None):
    q = select(User).where(or_(User.email == email, User.phone == phone), User.is_super_admin.is_(False))
    if exclude_id:
        q = q.where(User.id != exclude_id)
    existing = (await db.execute(q)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email or phone already in use")


async def _seeker_job_fair_names(db: AsyncSession, seeker_id: str) -> List[str]:
    """DB uses job_fairs.title column."""
    from app.modules.jobs_portal.models.job_fair import JobFair, JobFairSeeker
    q = (
        select(JobFair.title)
        .join(JobFairSeeker, JobFairSeeker.job_fair_id == JobFair.id)
        .where(JobFairSeeker.seeker_id == seeker_id)
        .order_by(JobFairSeeker.registered_at.desc())
    )
    result = await db.execute(q)
    return [row[0] for row in result.all() if row[0]]


async def _get_role_user(db: AsyncSession, user_id: str, role: UserRole) -> User:
    result = await db.execute(select(User).where(User.id == user_id, User.role == role, User.is_super_admin.is_(False)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def _hard_delete_user(db: AsyncSession, user: User) -> None:
    """Persist user deletion. Roadmaps have no ON DELETE CASCADE, so clear them first."""
    roadmap_ids = select(Roadmap.id).where(Roadmap.user_id == user.id)
    milestone_ids = select(Milestone.id).where(Milestone.roadmap_id.in_(roadmap_ids))
    await db.execute(sql_delete(Resource).where(Resource.milestone_id.in_(milestone_ids)))
    await db.execute(sql_delete(Milestone).where(Milestone.roadmap_id.in_(roadmap_ids)))
    await db.execute(sql_delete(Roadmap).where(Roadmap.user_id == user.id))
    await db.delete(user)
    await db.commit()


async def _apply_user_update(db: AsyncSession, user: User, body):
    data = body.model_dump(exclude_unset=True)
    if "email" in data or "phone" in data:
        email = data.get("email", user.email)
        phone = _normalize_phone(data.get("phone", user.phone))
        if len(phone) != 10:
            raise HTTPException(status_code=400, detail="Phone must be 10 digits")
        await _check_duplicate(db, email, phone, exclude_id=user.id)
        user.email = email
        user.phone = phone
    if "first_name" in data:
        user.first_name = data["first_name"].strip()
    if "last_name" in data:
        user.last_name = data["last_name"].strip()
    if data.get("password"):
        user.hashed_password = hash_password(data["password"])
    if "is_verified" in data:
        user.is_verified = data["is_verified"]
    if "onboarding_complete" in data:
        user.onboarding_complete = data["onboarding_complete"]


def _start_background_import(job_id: str, content: bytes, role: UserRole) -> None:
    import os
    from app.core.config import get_upload_dir
    from app.shared.services.celery_tasks import process_bulk_candidate_import_task

    temp_dir = get_upload_dir() / "temp_imports"
    os.makedirs(temp_dir, exist_ok=True)
    tmp_path = str(temp_dir / f"import_{job_id}.csv")
    with open(tmp_path, "wb") as f:
        f.write(content)

    role_str = role.value if hasattr(role, "value") else str(role)
    process_bulk_candidate_import_task.delay(job_id, tmp_path, role_str)


async def super_admin_login(body: SuperAdminLoginRequest, db: AsyncSession) -> SuperAdminLoginResponse:
    result = await db.execute(select(User).where(User.email == body.email, User.is_super_admin.is_(True)))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not await async_verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    return SuperAdminLoginResponse(access_token=token, refresh_token=refresh_token, user={"id": user.id, "email": user.email, "first_name": user.first_name, "last_name": user.last_name, "role": "super_admin", "is_super_admin": True})


def super_admin_me(admin: User) -> SuperAdminProfileOut:
    return SuperAdminProfileOut(
        id=admin.id,
        email=admin.email,
        first_name=admin.first_name,
        last_name=admin.last_name,
        phone=admin.phone,
        profile_pic_url=admin.profile_pic_url,
        role="super_admin",
        is_super_admin=True,
    )


def _user_display_name(user: User | None, fallback: str = "Unknown") -> str:
    if not user:
        return fallback
    parts = [user.first_name or "", user.last_name or ""]
    name = " ".join(p for p in parts if p).strip()
    return name or user.email or fallback


async def update_super_admin_profile(admin: User, body: SuperAdminProfileUpdate, db: AsyncSession) -> SuperAdminProfileOut:
    if body.email and body.email.lower() != (admin.email or "").lower():
        existing = await db.scalar(select(User).where(User.email == body.email, User.id != admin.id))
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        admin.email = body.email
    if body.first_name is not None:
        admin.first_name = body.first_name
    if body.last_name is not None:
        admin.last_name = body.last_name
    if body.phone is not None:
        admin.phone = _normalize_phone(body.phone)
    await db.commit()
    await db.refresh(admin)
    return super_admin_me(admin)


async def change_super_admin_password(admin: User, body: SuperAdminChangePasswordRequest, db: AsyncSession) -> SuperAdminProfileOut:
    if not admin.hashed_password or not await async_verify_password(body.current_password, admin.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    admin.hashed_password = await async_hash_password(body.new_password)
    await db.commit()
    await db.refresh(admin)
    return super_admin_me(admin)


async def upload_super_admin_profile_pic(file: UploadFile, admin: User, db: AsyncSession) -> SuperAdminProfileOut:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    filename = f"profile_{admin.id}_{uuid_lib.uuid4().hex}{ext}"
    file_path = str(get_upload_dir() / filename)
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not save profile image")
    admin.profile_pic_url = f"/uploads/{filename}"
    await db.commit()
    await db.refresh(admin)
    return super_admin_me(admin)


async def list_platform_jobs(
    db: AsyncSession,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    industry: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> AdminJobListResponse:
    base = (
        select(JobPosting, User)
        .join(User, JobPosting.provider_id == User.id)
    )
    count_q = select(func.count(JobPosting.id)).select_from(JobPosting).join(User, JobPosting.provider_id == User.id)

    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(JobPosting.title.ilike(term), User.company_name.ilike(term)))
    if industry:
        filters.append(JobPosting.industry.ilike(f"%{industry.strip()}%"))
    if is_active is not None:
        filters.append(JobPosting.is_active.is_(is_active))

    if filters:
        base = base.where(and_(*filters))
        count_q = count_q.where(and_(*filters))

    total = await db.scalar(count_q) or 0
    offset = (page - 1) * page_size
    rows = (await db.execute(base.order_by(JobPosting.created_at.desc()).offset(offset).limit(page_size))).all()
    items = [
        AdminJobListItem(
            id=str(job.id),
            title=job.title,
            company=user.company_name or _user_display_name(user, "Provider"),
            industry=job.industry,
            location=job.location,
            is_active=bool(job.is_active),
            created_at=job.created_at,
        )
        for job, user in rows
    ]
    return AdminJobListResponse(items=items, total=int(total), page=page, page_size=page_size)


async def list_platform_matches(
    db: AsyncSession, page: int, page_size: int, search: Optional[str] = None
) -> AdminMatchListResponse:
    from sqlalchemy.orm import aliased
    Seeker = aliased(User)
    Provider = aliased(User)
    base = (
        select(Match, Seeker, JobPosting, Provider)
        .join(Seeker, Match.seeker_id == Seeker.id)
        .join(JobPosting, Match.job_id == JobPosting.id)
        .join(Provider, JobPosting.provider_id == Provider.id)
    )
    if search:
        term = f"%{search.strip()}%"
        base = base.where(or_(Seeker.first_name.ilike(term), Seeker.last_name.ilike(term), JobPosting.title.ilike(term)))
    count_q = select(func.count(Match.id)).select_from(Match).join(Seeker, Match.seeker_id == Seeker.id).join(JobPosting, Match.job_id == JobPosting.id)
    if search:
        term = f"%{search.strip()}%"
        count_q = count_q.where(or_(Seeker.first_name.ilike(term), Seeker.last_name.ilike(term), JobPosting.title.ilike(term)))
    total = await db.scalar(count_q) or 0
    offset = (page - 1) * page_size
    rows = (await db.execute(base.order_by(Match.created_at.desc()).offset(offset).limit(page_size))).all()
    items = [
        AdminMatchListItem(
            id=str(match.id),
            seeker_name=_user_display_name(seeker),
            seeker_email=seeker.email,
            job_title=job.title,
            company=provider.company_name or _user_display_name(provider, "Provider"),
            score=float(match.score or 0),
            created_at=match.created_at,
        )
        for match, seeker, job, provider in rows
    ]
    return AdminMatchListResponse(items=items, total=int(total), page=page, page_size=page_size)


async def list_platform_applications(
    db: AsyncSession, page: int, page_size: int, search: Optional[str] = None, status: Optional[str] = None
) -> AdminApplicationListResponse:
    from sqlalchemy.orm import aliased
    Seeker = aliased(User)
    Provider = aliased(User)
    base = (
        select(Application, JobPosting, Provider, Seeker)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .join(Provider, JobPosting.provider_id == Provider.id)
        .outerjoin(Seeker, Application.seeker_id == Seeker.id)
    )
    if search:
        term = f"%{search.strip()}%"
        base = base.where(
            or_(
                Application.candidate_name.ilike(term),
                Application.candidate_email.ilike(term),
                JobPosting.title.ilike(term),
                Provider.company_name.ilike(term),
                Seeker.first_name.ilike(term),
                Seeker.last_name.ilike(term),
                func.concat(Seeker.first_name, ' ', Seeker.last_name).ilike(term),
                Seeker.email.ilike(term),
            )
        )
    if status and status != "all":
        base = base.where(Application.status == status)
    count_q = select(func.count(Application.id)).select_from(Application).join(JobPosting, Application.job_id == JobPosting.id).join(Provider, JobPosting.provider_id == Provider.id).outerjoin(Seeker, Application.seeker_id == Seeker.id)
    if search:
        term = f"%{search.strip()}%"
        count_q = count_q.where(
            or_(
                Application.candidate_name.ilike(term),
                Application.candidate_email.ilike(term),
                JobPosting.title.ilike(term),
                Provider.company_name.ilike(term),
                Seeker.first_name.ilike(term),
                Seeker.last_name.ilike(term),
                func.concat(Seeker.first_name, ' ', Seeker.last_name).ilike(term),
                Seeker.email.ilike(term),
            )
        )
    if status and status != "all":
        count_q = count_q.where(Application.status == status)
    total = await db.scalar(count_q) or 0
    offset = (page - 1) * page_size
    rows = (await db.execute(base.order_by(Application.applied_at.desc()).offset(offset).limit(page_size))).all()
    items = []
    for app, job, provider, seeker in rows:
        candidate = app.candidate_name or _user_display_name(seeker, "Candidate")
        items.append(
            AdminApplicationListItem(
                id=str(app.id),
                candidate_name=candidate,
                candidate_email=app.candidate_email or (seeker.email if seeker else None),
                candidate_phone=app.candidate_phone or (seeker.phone if seeker else None),
                seeker_id=str(app.seeker_id) if app.seeker_id else None,
                job_id=str(job.id),
                job_title=job.title,
                company=provider.company_name or _user_display_name(provider, "Provider"),
                status=str(app.status.value if hasattr(app.status, "value") else app.status),
                applied_at=app.applied_at,
                updated_at=app.updated_at,
            )
        )
    return AdminApplicationListResponse(items=items, total=int(total), page=page, page_size=page_size)


async def update_platform_application_status(
    db: AsyncSession,
    app_id: str,
    status: str,
    rejection_reason: Optional[str] = None,
) -> AdminApplicationListItem:
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    allowed = {s.value for s in ApplicationStatus}
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {', '.join(sorted(allowed))}")

    app.status = ApplicationStatus(status)
    if status == "rejected":
        app.rejection_reason = rejection_reason or "Not specified"
    elif status != "rejected":
        app.rejection_reason = None

    await db.commit()
    await db.refresh(app)

    job_result = await db.execute(select(JobPosting).where(JobPosting.id == app.job_id))
    job = job_result.scalar_one_or_none()
    provider = None
    if job:
        provider_result = await db.execute(select(User).where(User.id == job.provider_id))
        provider = provider_result.scalar_one_or_none()
    seeker_result = await db.execute(select(User).where(User.id == app.seeker_id)) if app.seeker_id else None
    seeker = seeker_result.scalar_one_or_none() if app.seeker_id else None
    candidate = app.candidate_name or _user_display_name(seeker, "Candidate")

    return AdminApplicationListItem(
        id=str(app.id),
        candidate_name=candidate,
        candidate_email=app.candidate_email or (seeker.email if seeker else None),
        candidate_phone=app.candidate_phone or (seeker.phone if seeker else None),
        seeker_id=str(app.seeker_id) if app.seeker_id else None,
        job_id=str(app.job_id),
        job_title=job.title if job else "—",
        company=provider.company_name or _user_display_name(provider, "Provider") if provider else "—",
        status=str(app.status.value if hasattr(app.status, "value") else app.status),
        applied_at=app.applied_at,
        updated_at=app.updated_at,
    )


async def list_platform_interviews(
    db: AsyncSession, page: int, page_size: int, search: Optional[str] = None
) -> AdminInterviewListResponse:
    from sqlalchemy.orm import aliased
    Seeker = aliased(User)
    Provider = aliased(User)
    base = (
        select(Interview, Seeker, Provider, JobPosting)
        .join(Seeker, Interview.seeker_id == Seeker.id)
        .join(Provider, Interview.provider_id == Provider.id)
        .join(JobPosting, Interview.job_id == JobPosting.id)
    )
    if search:
        term = f"%{search.strip()}%"
        base = base.where(or_(Interview.title.ilike(term), JobPosting.title.ilike(term)))
    count_q = select(func.count(Interview.id)).select_from(Interview).join(JobPosting, Interview.job_id == JobPosting.id)
    if search:
        term = f"%{search.strip()}%"
        count_q = count_q.where(or_(Interview.title.ilike(term), JobPosting.title.ilike(term)))
    total = await db.scalar(count_q) or 0
    offset = (page - 1) * page_size
    rows = (await db.execute(base.order_by(Interview.scheduled_at.desc()).offset(offset).limit(page_size))).all()
    items = [
        AdminInterviewListItem(
            id=str(iv.id),
            title=iv.title,
            seeker_name=_user_display_name(seeker),
            provider_name=provider.company_name or _user_display_name(provider, "Provider"),
            job_title=job.title,
            scheduled_at=iv.scheduled_at,
            source=str(iv.source.value if hasattr(iv.source, "value") else iv.source),
        )
        for iv, seeker, provider, job in rows
    ]
    return AdminInterviewListResponse(items=items, total=int(total), page=page, page_size=page_size)


async def list_platform_assessments(
    db: AsyncSession, page: int, page_size: int, search: Optional[str] = None
) -> AdminAssessmentListResponse:
    base = (
        select(AssessmentResult, User, AssessmentSession)
        .outerjoin(User, AssessmentResult.user_id == User.id)
        .join(AssessmentSession, AssessmentResult.session_id == AssessmentSession.id)
    )
    if search:
        term = f"%{search.strip()}%"
        base = base.where(or_(User.first_name.ilike(term), User.last_name.ilike(term), User.email.ilike(term)))
    count_q = select(func.count(AssessmentResult.id)).select_from(AssessmentResult).outerjoin(User, AssessmentResult.user_id == User.id)
    if search:
        term = f"%{search.strip()}%"
        count_q = count_q.where(or_(User.first_name.ilike(term), User.last_name.ilike(term), User.email.ilike(term)))
    total = await db.scalar(count_q) or 0
    offset = (page - 1) * page_size
    rows = (await db.execute(base.order_by(AssessmentResult.created_at.desc()).offset(offset).limit(page_size))).all()
    items = [
        AdminAssessmentListItem(
            id=str(result.id),
            user_name=_user_display_name(user, "Guest"),
            user_email=user.email if user else None,
            personality_type=result.personality_type,
            iq_score=result.iq_score,
            aptitude_score=result.aptitude_score,
            status=session.status or "completed",
            created_at=result.created_at,
        )
        for result, user, session in rows
    ]
    return AdminAssessmentListResponse(items=items, total=int(total), page=page, page_size=page_size)


async def platform_stats(db: AsyncSession) -> PlatformStatsResponse:
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    seekers = await db.scalar(select(func.count(User.id)).where(User.role == UserRole.seeker, User.is_super_admin.is_(False)))
    providers = await db.scalar(select(func.count(User.id)).where(User.role == UserRole.provider, User.is_super_admin.is_(False)))
    total_jobs = await db.scalar(select(func.count(JobPosting.id)))
    active_jobs = await db.scalar(select(func.count(JobPosting.id)).where(JobPosting.is_active.is_(True)))
    total_apps = await db.scalar(select(func.count(Application.id)))
    verified = await db.scalar(select(func.count(User.id)).where(User.is_verified.is_(True), User.is_super_admin.is_(False)))
    new_users = await db.scalar(select(func.count(User.id)).where(User.created_at >= thirty_days_ago, User.is_super_admin.is_(False)))
    reg_time = await db.execute(
        select(func.date_trunc("day", User.created_at).label("day"), func.count(User.id))
        .where(and_(User.created_at >= thirty_days_ago, User.is_super_admin.is_(False)))
        .group_by("day").order_by("day")
    )
    registrations_over_time = [{"date": row[0].isoformat() if row[0] else "", "count": row[1]} for row in reg_time.fetchall()]
    apps_status = await db.execute(select(Application.status, func.count(Application.id)).group_by(Application.status))
    applications_by_status = {str(row[0]): row[1] for row in apps_status.fetchall()}
    return PlatformStatsResponse(
        total_seekers=seekers or 0, total_providers=providers or 0, total_jobs=total_jobs or 0,
        active_jobs=active_jobs or 0, total_applications=total_apps or 0, verified_users=verified or 0,
        new_users_last_30_days=new_users or 0, users_by_role={"seeker": seekers or 0, "provider": providers or 0},
        registrations_over_time=registrations_over_time, applications_by_status=applications_by_status,
    )


async def detailed_platform_analytics(db: AsyncSession) -> DetailedPlatformAnalytics:
    data = await get_detailed_platform_analytics(db)
    return DetailedPlatformAnalytics(**data)


async def dashboard_analytics(
    db: AsyncSession,
    target_date: Optional[datetime] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> DashboardAnalyticsResponse:
    data = await get_dashboard_analytics(db, target_date, start_date, end_date)
    return DashboardAnalyticsResponse(**data)


def get_import_job_status(job_id: str) -> ImportJobStatus:
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    return ImportJobStatus(**job)


async def list_seekers(
    db: AsyncSession, page: int, page_size: int, search: Optional[str],
    industry: Optional[str], status: Optional[str] = None, job_fair_id: Optional[str] = None
) -> AdminUserListResponse:
    from app.modules.jobs_portal.models.job_fair import JobFairSeeker
    seeker_filters = [User.role == UserRole.seeker, User.is_super_admin.is_(False)]
    if industry:
        seeker_filters.append(User.industry.ilike(f"%{industry.strip()}%"))
    if search:
        seeker_filters.append(_build_user_search_filter(search.strip()))

    if status:
        if status == "active":
            seeker_filters.append(User.is_verified.is_(True))
        elif status == "inactive":
            seeker_filters.append(User.is_verified.is_(False))
        # Legacy aliases kept for old clients / bookmarks
        elif status in {"verified"}:
            seeker_filters.append(User.is_verified.is_(True))
        elif status in {"pending", "onboarded", "no_password"}:
            seeker_filters.append(User.is_verified.is_(False))

    count_q = select(func.count(User.id)).where(*seeker_filters)
    select_q = select(User, Portfolio).outerjoin(Portfolio, Portfolio.user_id == User.id).where(*seeker_filters)

    if job_fair_id:
        count_q = count_q.join(JobFairSeeker, JobFairSeeker.seeker_id == User.id).where(JobFairSeeker.job_fair_id == job_fair_id)
        select_q = select_q.join(JobFairSeeker, JobFairSeeker.seeker_id == User.id).where(JobFairSeeker.job_fair_id == job_fair_id)

    total = await db.scalar(count_q)
    result = await db.execute(
        select_q.order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    rows = result.all()
    user_ids = [user.id for user, _ in rows]
    has_resume_ids = await _seeker_has_resume_ids(db, user_ids)
    last_active = await _last_active_map(db, user_ids)
    items = []
    for user, portfolio in rows:
        pct = 0
        if portfolio:
            pct, _, _ = calculate_completion(portfolio, user)
        jf_titles = await _seeker_job_fair_names(db, user.id)
        items.append(
            _user_to_admin_out(
                user,
                "seeker",
                profile_completion_percentage=pct,
                registered_job_fairs=jf_titles,
                has_resume=user.id in has_resume_ids,
                last_active_at=last_active.get(user.id),
            )
        )
    return AdminUserListResponse(items=items, total=total or 0, page=page, page_size=page_size)


async def create_seeker(body: AdminSeekerCreate, db: AsyncSession) -> AdminUserOut:
    phone = _normalize_phone(body.phone)
    if len(phone) != 10:
        raise HTTPException(status_code=400, detail="Phone must be 10 digits")
    await _check_duplicate(db, body.email, phone)
    pwd = body.password or _temp_password()
    user = User(
        first_name=body.first_name.strip(), last_name=body.last_name.strip(), email=body.email, phone=phone,
        hashed_password=hash_password(pwd), role=UserRole.seeker, is_verified=True, onboarding_complete=True,
        industry=body.industry, job_role=body.job_role, job_type=JobType(body.job_type) if body.job_type else None,
        salary_range=body.salary_range, experience=body.experience, is_assessment_done=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _user_to_admin_out(user, "seeker")


async def get_seeker(user_id: str, db: AsyncSession) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.seeker)
    portfolio = (await db.execute(select(Portfolio).where(Portfolio.user_id == user.id))).scalar_one_or_none()
    pct = 0
    if portfolio:
        pct, _, _ = calculate_completion(portfolio, user)
    jf_titles = await _seeker_job_fair_names(db, user.id)
    has_resume = await _seeker_has_resume(db, user.id)
    return _user_to_admin_out(
        user,
        "seeker",
        profile_completion_percentage=pct,
        registered_job_fairs=jf_titles,
        has_resume=has_resume,
    )


async def get_seeker_detail(user_id: str, db: AsyncSession) -> AdminSeekerDetailResponse:
    """Full seeker detail including applications, interviews, and extended personal info."""
    user = await _get_role_user(db, user_id, UserRole.seeker)

    # Profile completion + portfolio payload
    portfolio = (await db.execute(select(Portfolio).where(Portfolio.user_id == user.id))).scalar_one_or_none()
    pct = 0
    sections_filled = 0
    sections_total = 0
    skills = []
    education_history = []
    work_experiences = []
    if portfolio:
        pct, filled, missing = calculate_completion(portfolio, user)
        sections_filled = len(filled)
        sections_total = len(filled) + len(missing)
        skills = normalize_skills(portfolio.skills)
        education_history = normalize_education(portfolio.education)
        work_experiences = normalize_work_experiences(portfolio.work_experiences)

    # Job fair names
    jf_titles = await _seeker_job_fair_names(db, user.id)
    has_resume = await _seeker_has_resume(db, user.id)

    # Fetch all applications for this seeker
    apps_q = (
        select(Application, JobPosting, User)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .join(User, JobPosting.provider_id == User.id)
        .where(Application.seeker_id == user.id)
        .order_by(Application.applied_at.desc())
    )
    rows = (await db.execute(apps_q)).all()

    app_items = []
    shortlisted_count = 0
    interviewing_count = 0
    selected_count = 0
    for app, job, provider in rows:
        status_str = str(app.status.value if hasattr(app.status, "value") else app.status)
        if status_str == "shortlisted":
            shortlisted_count += 1
        elif status_str == "interviewing":
            interviewing_count += 1
        elif status_str == "selected":
            selected_count += 1
        app_items.append(SeekerApplicationItem(
            id=str(app.id),
            job_title=job.title,
            company_name=provider.company_name,
            company_location=job.location,
            industry=job.industry,
            status=status_str,
            applied_at=app.applied_at,
            updated_at=app.updated_at,
        ))

    # Fetch interviews for this seeker
    interviews_q = (
        select(Interview, JobPosting, User)
        .join(JobPosting, Interview.job_id == JobPosting.id)
        .join(User, Interview.provider_id == User.id)
        .where(Interview.seeker_id == user.id)
        .order_by(Interview.scheduled_at.desc())
    )
    interview_rows = (await db.execute(interviews_q)).all()
    interview_items = [
        SeekerInterviewItem(
            id=str(iv.id),
            title=iv.title,
            job_title=job.title,
            provider_name=provider.company_name or _user_display_name(provider, "Provider"),
            interview_type=iv.interview_type.value if iv.interview_type and hasattr(iv.interview_type, "value") else None,
            status=str(iv.status.value if hasattr(iv.status, "value") else iv.status),
            scheduled_at=iv.scheduled_at,
            meeting_link=iv.meeting_link,
            location=iv.location,
            interviewer_name=iv.interviewer_name,
        )
        for iv, job, provider in interview_rows
    ]

    job_type = user.job_type.value if user.job_type and hasattr(user.job_type, "value") else user.job_type
    company_type = user.company_type.value if user.company_type and hasattr(user.company_type, "value") else user.company_type
    return AdminSeekerDetailResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        profile_pic_url=user.profile_pic_url,
        has_password=bool(user.hashed_password),
        is_verified=user.is_verified,
        onboarding_complete=user.onboarding_complete,
        is_assessment_done=user.is_assessment_done or False,
        is_first_login=user.is_first_login,
        auto_apply_enabled=user.auto_apply_enabled or False,
        welcome_email_status=user.welcome_email_status,
        welcome_email_error=user.welcome_email_error,
        industry=user.industry,
        job_role=user.job_role,
        job_type=job_type,
        salary_range=user.salary_range,
        experience=user.experience,
        preferred_locations=user.preferred_locations,
        profile_completion_percentage=pct,
        profile_sections_filled=sections_filled,
        profile_sections_total=sections_total,
        has_resume=has_resume,
        father_or_mother_name=user.father_or_mother_name,
        gender=user.gender,
        address=user.address,
        highest_qualification=user.highest_qualification,
        stream_specialization=user.stream_specialization,
        college_institute_name=user.college_institute_name,
        preferred_job_sector=user.preferred_job_sector,
        headline=portfolio.headline if portfolio else None,
        bio=portfolio.bio if portfolio else None,
        city=portfolio.city if portfolio else None,
        state=portfolio.state if portfolio else None,
        linkedin_url=portfolio.linkedin_url if portfolio else None,
        github_url=portfolio.github_url if portfolio else None,
        website_url=portfolio.website_url if portfolio else None,
        total_experience_years=portfolio.total_experience_years if portfolio else None,
        current_company=portfolio.current_company if portfolio else None,
        current_role=portfolio.current_role if portfolio else None,
        skills=skills,
        education_history=education_history,
        work_experiences=work_experiences,
        registered_job_fairs=jf_titles,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_active_at=(await _last_active_map(db, [user.id])).get(user.id),
        applications=app_items,
        total_applications=len(app_items),
        shortlisted_count=shortlisted_count,
        interviewing_count=interviewing_count,
        selected_count=selected_count,
        interviews=interview_items,
    )


async def update_seeker(user_id: str, body: AdminSeekerUpdate, db: AsyncSession) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.seeker)
    await _apply_user_update(db, user, body)
    if body.job_type is not None:
        user.job_type = JobType(body.job_type) if body.job_type else None
    for field in ("industry", "job_role", "salary_range", "experience"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(user, field, val)
    await db.commit()
    await db.refresh(user)
    return _user_to_admin_out(user, "seeker")


async def delete_seeker(user_id: str, db: AsyncSession) -> None:
    user = await _get_role_user(db, user_id, UserRole.seeker)
    await _hard_delete_user(db, user)


async def set_seeker_password(user_id: str, body: AdminSetPasswordRequest, db: AsyncSession) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.seeker)
    user.hashed_password = await async_hash_password(body.password)
    await db.commit()
    await db.refresh(user)
    return _user_to_admin_out(user, "seeker")


async def bulk_import_seekers(content: bytes, filename: str) -> BulkImportJobStarted:
    import uuid
    job_id = str(uuid.uuid4())
    _create_job(job_id, total=0, role="seeker")
    _start_background_import(job_id, content, UserRole.seeker)
    return BulkImportJobStarted(job_id=job_id)


async def list_providers(
    db: AsyncSession, page: int, page_size: int, search: Optional[str], status: Optional[str] = None
) -> AdminUserListResponse:
    provider_filters = [User.role == UserRole.provider, User.is_super_admin.is_(False)]
    if search:
        provider_filters.append(_build_user_search_filter(search.strip(), include_company=True))

    if status:
        if status == "active":
            provider_filters.append(User.is_verified.is_(True))
        elif status == "inactive":
            provider_filters.append(User.is_verified.is_(False))
        elif status in {"verified"}:
            provider_filters.append(User.is_verified.is_(True))
        elif status in {"pending", "onboarded", "no_password"}:
            provider_filters.append(User.is_verified.is_(False))

    total = await db.scalar(select(func.count(User.id)).where(*provider_filters))
    result = await db.execute(
        select(User).where(*provider_filters).order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()
    last_active = await _last_active_map(db, [u.id for u in users])
    return AdminUserListResponse(
        items=[
            _user_to_admin_out(u, "provider", last_active_at=last_active.get(u.id))
            for u in users
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def create_provider(body: AdminProviderCreate, db: AsyncSession) -> AdminUserOut:
    phone = _normalize_phone(body.phone)
    if len(phone) != 10:
        raise HTTPException(status_code=400, detail="Phone must be 10 digits")
    await _check_duplicate(db, body.email, phone)
    pwd = body.password or _temp_password()
    user = User(
        first_name=body.first_name.strip(), last_name=body.last_name.strip(), email=body.email, phone=phone,
        hashed_password=hash_password(pwd), role=UserRole.provider, is_verified=True, onboarding_complete=True,
        company_name=body.company_name, company_type=CompanyType(body.company_type) if body.company_type else None,
        company_location=body.company_location, company_size=body.company_size,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _user_to_admin_out(user, "provider")


async def get_provider(user_id: str, db: AsyncSession) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.provider)
    return _user_to_admin_out(user, "provider")


async def get_provider_detail(user_id: str, db: AsyncSession) -> AdminProviderDetailResponse:
    """Full provider detail including job postings and interviews."""
    user = await _get_role_user(db, user_id, UserRole.provider)

    # Fetch all job postings for this provider with application counts
    jobs_q = (
        select(
            JobPosting,
            func.count(Application.id).label("app_count")
        )
        .outerjoin(Application, Application.job_id == JobPosting.id)
        .where(JobPosting.provider_id == user.id)
        .group_by(JobPosting.id)
        .order_by(JobPosting.created_at.desc())
    )
    rows = (await db.execute(jobs_q)).all()

    job_items = []
    active_count = 0
    total_apps_received = 0
    for job, app_count in rows:
        if job.is_active:
            active_count += 1
        total_apps_received += int(app_count)
        job_type = job.job_type.value if job.job_type and hasattr(job.job_type, "value") else job.job_type
        required_skills = job.required_skills if isinstance(job.required_skills, list) else None
        perks = job.perks if isinstance(job.perks, list) else None
        job_items.append(ProviderJobItem(
            id=str(job.id),
            title=job.title,
            industry=job.industry,
            location=job.location,
            job_type=job_type,
            salary_range=job.salary_range,
            experience_required=job.experience_required,
            description=job.description,
            required_skills=required_skills,
            is_active=bool(job.is_active),
            posted_by_name=job.posted_by_name,
            employment_type=job.employment_type,
            shift=job.shift,
            perks=perks,
            application_count=int(app_count),
            created_at=job.created_at,
            updated_at=job.updated_at,
        ))

    # Fetch interviews for this provider
    interviews_q = (
        select(Interview, JobPosting, User)
        .join(JobPosting, Interview.job_id == JobPosting.id)
        .join(User, Interview.seeker_id == User.id)
        .where(Interview.provider_id == user.id)
        .order_by(Interview.scheduled_at.desc())
    )
    interview_rows = (await db.execute(interviews_q)).all()
    interview_items = [
        ProviderInterviewItem(
            id=str(iv.id),
            title=iv.title,
            seeker_name=_user_display_name(seeker),
            job_title=job.title,
            interview_type=iv.interview_type.value if iv.interview_type and hasattr(iv.interview_type, "value") else None,
            status=str(iv.status.value if hasattr(iv.status, "value") else iv.status),
            scheduled_at=iv.scheduled_at,
            meeting_link=iv.meeting_link,
        )
        for iv, job, seeker in interview_rows
    ]

    company_type = user.company_type.value if user.company_type and hasattr(user.company_type, "value") else user.company_type
    return AdminProviderDetailResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        profile_pic_url=user.profile_pic_url,
        has_password=bool(user.hashed_password),
        is_verified=user.is_verified,
        onboarding_complete=user.onboarding_complete,
        is_first_login=user.is_first_login,
        welcome_email_status=user.welcome_email_status,
        welcome_email_error=user.welcome_email_error,
        company_name=user.company_name,
        company_type=company_type,
        company_location=user.company_location,
        company_address=user.company_address,
        company_size=user.company_size,
        gender=user.gender,
        job_roles_offering=user.job_roles_offering,
        specific_requirements=user.specific_requirements,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_active_at=(await _last_active_map(db, [user.id])).get(user.id),
        job_postings=job_items,
        total_jobs=len(job_items),
        active_jobs=active_count,
        total_applications_received=total_apps_received,
        interviews=interview_items,
    )


async def update_provider(user_id: str, body: AdminProviderUpdate, db: AsyncSession) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.provider)
    await _apply_user_update(db, user, body)
    if body.company_type is not None:
        user.company_type = CompanyType(body.company_type) if body.company_type else None
    for field in ("company_name", "company_location", "company_size"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(user, field, val)
    await db.commit()
    await db.refresh(user)
    return _user_to_admin_out(user, "provider")


async def delete_provider(user_id: str, db: AsyncSession) -> None:
    user = await _get_role_user(db, user_id, UserRole.provider)
    await _hard_delete_user(db, user)


async def set_provider_password(user_id: str, body: AdminSetPasswordRequest, db: AsyncSession) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.provider)
    user.hashed_password = await async_hash_password(body.password)
    await db.commit()
    await db.refresh(user)
    return _user_to_admin_out(user, "provider")


async def bulk_import_providers(content: bytes, filename: str) -> BulkImportJobStarted:
    import uuid
    job_id = str(uuid.uuid4())
    _create_job(job_id, total=0, role="provider")
    _start_background_import(job_id, content, UserRole.provider)
    return BulkImportJobStarted(job_id=job_id)


# ── Export helpers ───────────────────────────────────────────────────────────

SEEKER_EXPORT_FIELDS: dict[str, str] = {
    "first_name": "First Name",
    "last_name": "Last Name",
    "email": "Email",
    "phone": "Phone",
    "industry": "Industry",
    "job_role": "Job Role",
    "job_type": "Job Type",
    "salary_range": "Salary Range",
    "experience": "Experience",
    "profile_completion_percentage": "Profile Completion %",
    "has_resume": "Has Resume",
    "registered_job_fairs": "Job Fair Participation",
    "is_verified": "Verified",
    "onboarding_complete": "Onboarding Complete",
    "has_password": "Has Password",
    "status": "Status",
    "created_at": "Joined",
    "last_active_at": "Last Active",
}

PROVIDER_EXPORT_FIELDS: dict[str, str] = {
    "first_name": "First Name",
    "last_name": "Last Name",
    "email": "Email",
    "phone": "Phone",
    "company_name": "Company Name",
    "company_type": "Company Type",
    "company_location": "Company Location",
    "company_size": "Company Size",
    "is_verified": "Verified",
    "onboarding_complete": "Onboarding Complete",
    "has_password": "Has Password",
    "status": "Status",
    "created_at": "Joined",
    "last_active_at": "Last Active",
}


def _format_export_value(key: str, user: AdminUserOut) -> str:
    data = user.model_dump()
    if key == "status":
        return "Active" if user.is_verified else "Inactive"
    if key == "profile_completion_percentage":
        pct = data.get("profile_completion_percentage")
        if pct is None:
            return ""
        return f"{int(round(float(pct)))}%"
    value = data.get(key)
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def _build_export_file(
    rows: List[dict],
    headers: List[str],
    field_keys: List[str],
    fmt: str,
    filename_stem: str,
) -> StreamingResponse:
    fmt = (fmt or "csv").lower().strip()
    if fmt not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="format must be csv or xlsx")

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row.get(k, "") for k in field_keys])
        data = output.getvalue().encode("utf-8-sig")
        media_type = "text/csv"
        filename = f"{filename_stem}.csv"
    else:
        import pandas as pd
        df = pd.DataFrame([{headers[i]: row.get(field_keys[i], "") for i in range(len(field_keys))} for row in rows])
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Export")
        data = buf.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{filename_stem}.xlsx"

    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _resolve_export_fields(
    requested: List[str],
    allowed: dict[str, str],
) -> Tuple[List[str], List[str]]:
    if not requested:
        raise HTTPException(status_code=400, detail="Select at least one field to export")
    keys: List[str] = []
    seen = set()
    for key in requested:
        k = (key or "").strip()
        if not k or k in seen:
            continue
        if k not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid export field: {k}")
        keys.append(k)
        seen.add(k)
    if not keys:
        raise HTTPException(status_code=400, detail="Select at least one field to export")
    return keys, [allowed[k] for k in keys]


async def export_seekers(body: AdminUserExportRequest, db: AsyncSession) -> StreamingResponse:
    field_keys, headers = _resolve_export_fields(body.fields, SEEKER_EXPORT_FIELDS)

    from app.modules.jobs_portal.models.job_fair import JobFairSeeker
    seeker_filters = [User.role == UserRole.seeker, User.is_super_admin.is_(False)]
    if body.industry:
        seeker_filters.append(User.industry.ilike(f"%{body.industry.strip()}%"))
    if body.search:
        seeker_filters.append(_build_user_search_filter(body.search.strip()))

    if body.status:
        if body.status == "active":
            seeker_filters.append(User.is_verified.is_(True))
        elif body.status == "inactive":
            seeker_filters.append(User.is_verified.is_(False))
        elif body.status in {"verified"}:
            seeker_filters.append(User.is_verified.is_(True))
        elif body.status in {"pending", "onboarded", "no_password"}:
            seeker_filters.append(User.is_verified.is_(False))

    select_q = select(User, Portfolio).outerjoin(Portfolio, Portfolio.user_id == User.id).where(*seeker_filters)
    if body.job_fair_id:
        select_q = select_q.join(JobFairSeeker, JobFairSeeker.seeker_id == User.id).where(
            JobFairSeeker.job_fair_id == body.job_fair_id
        )

    result = await db.execute(select_q.order_by(User.created_at.desc(), User.id.desc()))
    rows_db = result.all()
    needs_resume = "has_resume" in field_keys
    needs_fairs = "registered_job_fairs" in field_keys
    needs_pct = "profile_completion_percentage" in field_keys
    has_resume_ids = await _seeker_has_resume_ids(db, [u.id for u, _ in rows_db]) if needs_resume else set()

    export_rows: List[dict] = []
    for user, portfolio in rows_db:
        pct = None
        if needs_pct:
            pct = 0
            if portfolio:
                pct, _, _ = calculate_completion(portfolio, user)
        jf_titles = await _seeker_job_fair_names(db, user.id) if needs_fairs else None
        admin_out = _user_to_admin_out(
            user,
            "seeker",
            profile_completion_percentage=pct,
            registered_job_fairs=jf_titles,
            has_resume=(user.id in has_resume_ids) if needs_resume else None,
        )
        export_rows.append({k: _format_export_value(k, admin_out) for k in field_keys})

    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
    return _build_export_file(export_rows, headers, field_keys, body.format, f"seekers_export_{stamp}")


async def export_providers(body: AdminUserExportRequest, db: AsyncSession) -> StreamingResponse:
    field_keys, headers = _resolve_export_fields(body.fields, PROVIDER_EXPORT_FIELDS)

    provider_filters = [User.role == UserRole.provider, User.is_super_admin.is_(False)]
    if body.search:
        provider_filters.append(_build_user_search_filter(body.search.strip(), include_company=True))

    if body.status:
        if body.status == "active":
            provider_filters.append(User.is_verified.is_(True))
        elif body.status == "inactive":
            provider_filters.append(User.is_verified.is_(False))
        elif body.status in {"verified"}:
            provider_filters.append(User.is_verified.is_(True))
        elif body.status in {"pending", "onboarded", "no_password"}:
            provider_filters.append(User.is_verified.is_(False))

    result = await db.execute(
        select(User).where(*provider_filters).order_by(User.created_at.desc(), User.id.desc())
    )
    users = result.scalars().all()
    export_rows = [
        {k: _format_export_value(k, _user_to_admin_out(u, "provider")) for k in field_keys}
        for u in users
    ]

    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
    return _build_export_file(export_rows, headers, field_keys, body.format, f"providers_export_{stamp}")


async def ensure_super_admin_user():
    """Create default super admin from env if missing, and default teacher/student for quick testing."""
    from app.core.database import AsyncSessionLocal
    from app.shared.models.user import UserRole
    async with AsyncSessionLocal() as db:
        # 1. Super Admin
        email = settings.SUPER_ADMIN_EMAIL.strip().lower()
        result = await db.execute(select(User).where(User.email == email))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                first_name="Super", last_name="Admin", email=email, phone="9999999999",
                hashed_password=hash_password(settings.SUPER_ADMIN_PASSWORD),
                is_verified=True, onboarding_complete=True, is_super_admin=True, totp_enabled=False,
            )
            db.add(admin)
        else:
            admin.is_super_admin = True
            admin.is_verified = True
            if not admin.hashed_password:
                admin.hashed_password = hash_password(settings.SUPER_ADMIN_PASSWORD)
        await db.commit()
