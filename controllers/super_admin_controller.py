"""
Super Admin controller – business logic from routers/super_admin.py
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
import os
import uuid as uuid_lib

from fastapi import UploadFile
from models.application import Application, ApplicationStatus
from models.assessment import AssessmentResult, AssessmentSession
from models.interview import Interview
from models.job import JobPosting
from models.match import Match
from models.portfolio import Portfolio
from models.user import CompanyType, JobType, User, UserRole
from schemas.super_admin import (
    AdminApplicationListItem, AdminApplicationListResponse, AdminAssessmentListItem,
    AdminAssessmentListResponse, AdminInterviewListItem, AdminInterviewListResponse,
    AdminJobListItem, AdminJobListResponse, AdminMatchListItem, AdminMatchListResponse,
    AdminProviderCreate, AdminProviderUpdate, AdminSeekerCreate, AdminSeekerUpdate,
    AdminSetPasswordRequest, AdminUserListResponse, AdminUserOut, BulkImportJobStarted,
    DashboardAnalyticsResponse, DetailedPlatformAnalytics, ImportJobStatus, PlatformStatsResponse,
    SuperAdminChangePasswordRequest, SuperAdminLoginRequest, SuperAdminLoginResponse,
    SuperAdminProfileOut, SuperAdminProfileUpdate,
)
from schemas.super_admin_detail import (
    AdminProviderDetailResponse, AdminSeekerDetailResponse,
    ProviderJobItem, SeekerApplicationItem,
    ProviderInterviewItem, SeekerInterviewItem,
)
from services.auth_service import create_access_token, hash_password, verify_password
from services.import_job_store import create_job as _create_job, get_job as _get_job
from services.super_admin_analytics import get_detailed_platform_analytics
from services.dashboard_analytics import get_dashboard_analytics
from services.super_admin_bulk_import import run_bulk_import_job
from services.portfolio_service import calculate_completion
from services.super_admin_utils import normalize_phone as _normalize_phone, temp_password as _temp_password


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


def _user_to_admin_out(user: User, role_label: str, profile_completion_percentage: Optional[int] = None, registered_job_fairs: Optional[List[str]] = None) -> AdminUserOut:
    job_type = user.job_type.value if user.job_type and hasattr(user.job_type, "value") else user.job_type
    company_type = user.company_type.value if user.company_type and hasattr(user.company_type, "value") else user.company_type
    return AdminUserOut(
        id=user.id, first_name=user.first_name, last_name=user.last_name, email=user.email,
        profile_pic_url=user.profile_pic_url, phone=user.phone, role=role_label,
        has_password=bool(user.hashed_password), is_verified=user.is_verified,
        onboarding_complete=user.onboarding_complete, industry=user.industry, job_role=user.job_role,
        job_type=job_type, salary_range=user.salary_range, experience=user.experience,
        company_name=user.company_name, company_type=company_type, company_location=user.company_location,
        company_size=user.company_size, profile_completion_percentage=profile_completion_percentage,
        welcome_email_status=user.welcome_email_status, welcome_email_error=user.welcome_email_error,
        created_at=user.created_at, registered_job_fairs=registered_job_fairs,
    )


async def _check_duplicate(db: AsyncSession, email: str, phone: str, exclude_id: Optional[str] = None):
    q = select(User).where(or_(User.email == email, User.phone == phone), User.is_super_admin.is_(False))
    if exclude_id:
        q = q.where(User.id != exclude_id)
    existing = (await db.execute(q)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email or phone already in use")


async def _seeker_job_fair_names(db: AsyncSession, seeker_id: str) -> List[str]:
    """DB uses job_fairs.title column."""
    from models.job_fair import JobFair, JobFairSeeker
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
    asyncio.create_task(run_bulk_import_job(job_id, content, role))


async def super_admin_login(body: SuperAdminLoginRequest, db: AsyncSession) -> SuperAdminLoginResponse:
    result = await db.execute(select(User).where(User.email == body.email, User.is_super_admin.is_(True)))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.id})
    return SuperAdminLoginResponse(access_token=token, user={"id": user.id, "email": user.email, "first_name": user.first_name, "last_name": user.last_name, "role": "super_admin", "is_super_admin": True})


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
    if not admin.hashed_password or not verify_password(body.current_password, admin.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    admin.hashed_password = hash_password(body.new_password)
    await db.commit()
    await db.refresh(admin)
    return super_admin_me(admin)


async def upload_super_admin_profile_pic(file: UploadFile, admin: User, db: AsyncSession) -> SuperAdminProfileOut:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    filename = f"profile_{admin.id}_{uuid_lib.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
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
    from models.job_fair import JobFairSeeker
    seeker_filters = [User.role == UserRole.seeker, User.is_super_admin.is_(False)]
    if industry:
        seeker_filters.append(User.industry.ilike(f"%{industry.strip()}%"))
    if search:
        seeker_filters.append(_build_user_search_filter(search.strip()))

    if status:
        has_pwd = and_(User.hashed_password.isnot(None), User.hashed_password != "")
        no_pwd = or_(User.hashed_password.is_(None), User.hashed_password == "")
        if status == "no_password":
            seeker_filters.append(no_pwd)
        elif status == "active":
            seeker_filters.append(and_(has_pwd, User.is_verified.is_(True), User.onboarding_complete.is_(True)))
        elif status == "verified":
            seeker_filters.append(and_(has_pwd, User.is_verified.is_(True), User.onboarding_complete.is_(False)))
        elif status == "onboarded":
            seeker_filters.append(and_(has_pwd, User.is_verified.is_(False), User.onboarding_complete.is_(True)))
        elif status == "pending":
            seeker_filters.append(and_(has_pwd, User.is_verified.is_(False), User.onboarding_complete.is_(False)))

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
    items = []
    for user, portfolio in result.all():
        pct = 0
        if portfolio:
            pct, _, _ = calculate_completion(portfolio, user)
        jf_titles = await _seeker_job_fair_names(db, user.id)
        items.append(_user_to_admin_out(user, "seeker", profile_completion_percentage=pct, registered_job_fairs=jf_titles))
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
    await db.flush()
    await db.refresh(user)
    return _user_to_admin_out(user, "seeker")


async def get_seeker(user_id: str, db: AsyncSession) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.seeker)
    portfolio = (await db.execute(select(Portfolio).where(Portfolio.user_id == user.id))).scalar_one_or_none()
    pct = 0
    if portfolio:
        pct, _, _ = calculate_completion(portfolio, user)
    jf_titles = await _seeker_job_fair_names(db, user.id)
    return _user_to_admin_out(user, "seeker", profile_completion_percentage=pct, registered_job_fairs=jf_titles)


async def get_seeker_detail(user_id: str, db: AsyncSession) -> AdminSeekerDetailResponse:
    """Full seeker detail including applications, interviews, and extended personal info."""
    user = await _get_role_user(db, user_id, UserRole.seeker)

    # Profile completion
    portfolio = (await db.execute(select(Portfolio).where(Portfolio.user_id == user.id))).scalar_one_or_none()
    pct = 0
    if portfolio:
        pct, _, _ = calculate_completion(portfolio, user)

    # Job fair names
    jf_titles = await _seeker_job_fair_names(db, user.id)

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
        father_or_mother_name=user.father_or_mother_name,
        gender=user.gender,
        address=user.address,
        highest_qualification=user.highest_qualification,
        stream_specialization=user.stream_specialization,
        college_institute_name=user.college_institute_name,
        preferred_job_sector=user.preferred_job_sector,
        registered_job_fairs=jf_titles,
        created_at=user.created_at,
        updated_at=user.updated_at,
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
    await db.flush()
    await db.refresh(user)
    return _user_to_admin_out(user, "seeker")


async def delete_seeker(user_id: str, db: AsyncSession) -> None:
    user = await _get_role_user(db, user_id, UserRole.seeker)
    await db.delete(user)


async def set_seeker_password(user_id: str, body: AdminSetPasswordRequest, db: AsyncSession) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.seeker)
    user.hashed_password = hash_password(body.password)
    await db.flush()
    await db.refresh(user)
    return _user_to_admin_out(user, "seeker")


async def bulk_import_seekers(content: bytes, filename: str) -> BulkImportJobStarted:
    job_id = _create_job("seekers", filename or "import.csv")
    _start_background_import(job_id, content, UserRole.seeker)
    return BulkImportJobStarted(job_id=job_id)


async def list_providers(
    db: AsyncSession, page: int, page_size: int, search: Optional[str], status: Optional[str] = None
) -> AdminUserListResponse:
    provider_filters = [User.role == UserRole.provider, User.is_super_admin.is_(False)]
    if search:
        provider_filters.append(_build_user_search_filter(search.strip(), include_company=True))

    if status:
        has_pwd = and_(User.hashed_password.isnot(None), User.hashed_password != "")
        no_pwd = or_(User.hashed_password.is_(None), User.hashed_password == "")

        if status == "no_password":
            provider_filters.append(no_pwd)
        elif status == "active":
            provider_filters.append(and_(has_pwd, User.is_verified.is_(True), User.onboarding_complete.is_(True)))
        elif status == "verified":
            provider_filters.append(and_(has_pwd, User.is_verified.is_(True), User.onboarding_complete.is_(False)))
        elif status == "onboarded":
            provider_filters.append(and_(has_pwd, User.is_verified.is_(False), User.onboarding_complete.is_(True)))
        elif status == "pending":
            provider_filters.append(and_(has_pwd, User.is_verified.is_(False), User.onboarding_complete.is_(False)))

    total = await db.scalar(select(func.count(User.id)).where(*provider_filters))
    result = await db.execute(
        select(User).where(*provider_filters).order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()
    return AdminUserListResponse(items=[_user_to_admin_out(u, "provider") for u in users], total=total or 0, page=page, page_size=page_size)


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
    await db.flush()
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
    await db.flush()
    await db.refresh(user)
    return _user_to_admin_out(user, "provider")


async def delete_provider(user_id: str, db: AsyncSession) -> None:
    user = await _get_role_user(db, user_id, UserRole.provider)
    await db.delete(user)


async def set_provider_password(user_id: str, body: AdminSetPasswordRequest, db: AsyncSession) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.provider)
    user.hashed_password = hash_password(body.password)
    await db.flush()
    await db.refresh(user)
    return _user_to_admin_out(user, "provider")


async def bulk_import_providers(content: bytes, filename: str) -> BulkImportJobStarted:
    job_id = _create_job("providers", filename or "import.csv")
    _start_background_import(job_id, content, UserRole.provider)
    return BulkImportJobStarted(job_id=job_id)


async def ensure_super_admin_user():
    """Create default super admin from env if missing, and default teacher/student for quick testing."""
    from database import AsyncSessionLocal
    from models.user import UserRole
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
