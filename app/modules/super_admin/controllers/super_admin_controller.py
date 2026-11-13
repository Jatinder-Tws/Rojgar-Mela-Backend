"""
Super Admin controller – business logic from routers/super_admin.py
"""
import asyncio
import csv
import io
import logging
import re
from datetime import date, datetime, time, timedelta
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# Calendar-day filters from the admin UI are IST; stored timestamps are naive UTC.
_IST_OFFSET = timedelta(hours=5, minutes=30)


def _parse_ymd(value: Optional[str]) -> Optional[date]:
    if not value or not str(value).strip():
        return None
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _created_range_filters(column, created_from: Optional[str], created_to: Optional[str]) -> list:
    """Inclusive calendar-day range on a UTC-naive timestamp column (IST picker days)."""
    filters = []
    start_day = _parse_ymd(created_from)
    end_day = _parse_ymd(created_to)
    if start_day:
        filters.append(column >= datetime.combine(start_day, time.min) - _IST_OFFSET)
    if end_day:
        filters.append(column <= datetime.combine(end_day, time.max) - _IST_OFFSET)
    return filters

from fastapi import BackgroundTasks, HTTPException
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
from app.shared.services.account_origin import actor_display_name, creator_label, origin_for_actor, stamp_creator
from app.modules.jobs_portal.controllers.jobs_controller import create_job_for_provider
from app.modules.jobs_portal.schemas.jobs import JobCreate, JobUpdate
from app.modules.jobs_portal.services.jobs_service import (
    activate_job_service,
    deactivate_job_service,
    schedule_cleanup,
    update_job_service,
)
from app.modules.super_admin.schemas.super_admin import (
    AdminJobCreate,
    AdminJobUpdate,
    AdminJobProviderOption,
    AdminJobProviderOptionsResponse,
    AdminApplicationListItem, AdminApplicationListResponse, AdminAssessmentListItem,
    AdminAssessmentListResponse, AdminInterviewListItem, AdminInterviewListResponse,
    AdminJobDetailResponse, AdminJobListItem, AdminJobListResponse, AdminMatchListItem, AdminMatchListResponse,
    AdminProviderCreate, AdminProviderUpdate, AdminSeekerCreate, AdminSeekerUpdate,
    AdminSetPasswordRequest, AdminUserExportRequest, AdminUserListResponse, AdminUserOut,
    BulkImportJobStarted, DashboardAnalyticsResponse, DetailedPlatformAnalytics, ImportJobStatus,
    PlatformStatsResponse, SuperAdminChangePasswordRequest, SuperAdminLoginRequest,
    SuperAdminLoginResponse, SuperAdminProfileOut, SuperAdminProfileUpdate,
)
from app.modules.super_admin.schemas.super_admin_detail import (
    AdminProviderDetailResponse, AdminSeekerDetailResponse,
    ProviderApplicationItem, ProviderJobItem, SeekerApplicationItem,
    ProviderInterviewItem, SeekerInterviewItem,
)
from app.core.dependencies import create_access_token, create_refresh_token, hash_password, verify_password, async_hash_password, async_verify_password
from app.modules.super_admin.services.import_job_store import create_job as _create_job, get_job as _get_job
from app.modules.super_admin.services.super_admin_analytics import get_detailed_platform_analytics
from app.modules.jobs_portal.services.dashboard_analytics import get_dashboard_analytics
from app.modules.super_admin.services.super_admin_bulk_import import run_bulk_import_job
from app.modules.jobs_portal.services.portfolio_service import (
    calculate_completion,
    normalize_certifications,
    normalize_education,
    normalize_languages,
    normalize_projects,
    normalize_skills,
    normalize_work_experiences,
)
from app.modules.super_admin.services.seeker_profile_fields import (
    apply_seeker_profile_fields,
    seeker_profile_payload,
)
from app.modules.super_admin.services.super_admin_utils import normalize_phone as _normalize_phone, temp_password as _temp_password


_INDUSTRY_SPLIT = re.compile(r"[,;/|]+")
_INDUSTRY_ALIAS_GROUPS = (
    ("information technology", "it", "it & software", "it/software", "it and software", "it / saas", "technology", "tech"),
    ("automotive", "automobile"),
    ("banking & finance", "banking", "finance", "financial services"),
    ("logistics", "transportation & logistics", "transportation", "supply chain"),
    ("hospitality", "hospitality & tourism", "tourism"),
    ("energy", "energy & utilities", "utilities"),
    ("retail & e-commerce", "retail", "e-commerce", "ecommerce", "retail & ecommerce"),
    ("fmcg", "consumer goods", "fast moving consumer goods"),
    ("fashion & textiles", "textiles", "fashion", "apparel"),
    ("media & entertainment", "media", "entertainment"),
    ("pharmaceuticals", "pharma"),
    ("real estate", "property"),
    ("telecommunications", "telecom"),
)

CANONICAL_INDUSTRIES: List[str] = [
    "Agriculture",
    "Automotive",
    "Aviation",
    "Banking & Finance",
    "BPO/KPO",
    "Construction",
    "Consulting",
    "Education",
    "Energy",
    "Fashion & Textiles",
    "FMCG",
    "Government",
    "Healthcare",
    "Hospitality",
    "Human Resources",
    "Information Technology",
    "IT & Software",
    "Legal",
    "Logistics",
    "Manufacturing",
    "Media & Entertainment",
    "Pharmaceuticals",
    "Real Estate",
    "Retail & E-Commerce",
    "Startups & Entrepreneurship",
    "Telecommunications",
]


def _is_valid_industry_name(name: str) -> bool:
    if not name or len(name.strip()) < 2:
        return False
    clean = name.strip()
    if clean.isdigit() or re.match(r"^[\d\s\-_.,/]+$", clean):
        return False
    if clean.lower() in ("nan", "null", "undefined", "none", "n/a", "other", "others"):
        return False
    return True


def _parse_industries(*values: Optional[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for value in values:
        if not value or not str(value).strip():
            continue
        for part in _INDUSTRY_SPLIT.split(str(value)):
            name = part.strip()
            if not _is_valid_industry_name(name):
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(name)
    return out


def _expand_industry_terms(industry: str) -> List[str]:
    raw = industry.strip()
    if not raw:
        return []
    lower = raw.lower()
    terms = [raw]
    for group in _INDUSTRY_ALIAS_GROUPS:
        if lower in group:
            terms.extend(group)
            break
    unique: List[str] = []
    seen: set[str] = set()
    for term in terms:
        key = term.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(term.strip())
    return unique


def _column_matches_industry_term(column, term: str):
    escaped = re.escape(term.strip())
    if not escaped:
        return None
    pattern = rf"(^|[,;/|]\s*){escaped}(\s*[,;/]|$)"
    return column.op("~*")(pattern)


def _seeker_industry_clause(industry: Optional[str]):
    if not industry or not industry.strip() or industry.strip().lower() == "all":
        return None
    clauses = []
    for term in _expand_industry_terms(industry):
        for column in (User.industry, User.preferred_job_sector):
            match = _column_matches_industry_term(column, term)
            if match is not None:
                clauses.append(match)
    return or_(*clauses) if clauses else None


_USER_FULL_NAME_EXPR = func.concat(func.coalesce(User.first_name, ""), " ", func.coalesce(User.last_name, ""))


def _sort_desc(sort_dir: Optional[str]) -> bool:
    return (sort_dir or "desc").strip().lower() != "asc"


def _ordered(column, sort_dir: Optional[str]):
    clause = column.desc() if _sort_desc(sort_dir) else column.asc()
    return clause.nulls_last()


def _seeker_job_fair_count_expr():
    from app.modules.jobs_portal.models.job_fair import JobFairSeeker

    return (
        select(func.count(JobFairSeeker.id))
        .where(JobFairSeeker.seeker_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )


def _seeker_sort_column(sort_by: Optional[str]):
    key = (sort_by or "created_at").strip().lower()
    columns = {
        "candidate": _USER_FULL_NAME_EXPR,
        "contact": User.phone,
        "role": User.job_role,
        "email": User.email,
        "created_at": User.created_at,
        "status": User.is_verified,
        "last_active_at": User.last_login_at,
        "industries": func.coalesce(User.industry, User.preferred_job_sector),
        "job_fair_participation": _seeker_job_fair_count_expr(),
        # profile_completion_percentage is computed in Python — see list_seekers.
    }
    return columns.get(key, User.created_at)


def _provider_sort_column(sort_by: Optional[str]):
    key = (sort_by or "created_at").strip().lower()
    columns = {
        "candidate": _USER_FULL_NAME_EXPR,
        "contact": User.phone,
        "role": User.company_name,
        "email": User.email,
        "created_at": User.created_at,
        "status": User.is_verified,
        "last_active_at": User.last_login_at,
    }
    return columns.get(key, User.created_at)


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
    created_by_name: Optional[str] = None,
) -> AdminUserOut:
    job_type = user.job_type.value if user.job_type and hasattr(user.job_type, "value") else user.job_type
    company_type = user.company_type.value if user.company_type and hasattr(user.company_type, "value") else user.company_type
    resolved_last_active = last_active_at if last_active_at is not None else getattr(user, "last_login_at", None)
    industries = _parse_industries(user.industry, getattr(user, "preferred_job_sector", None))
    return AdminUserOut(
        id=user.id, first_name=user.first_name, last_name=user.last_name, email=user.email,
        profile_pic_url=user.profile_pic_url, phone=user.phone, role=role_label,
        has_password=bool(user.hashed_password), is_verified=user.is_verified,
        onboarding_complete=user.onboarding_complete,
        industry=user.industry or (industries[0] if industries else None),
        industries=industries,
        job_role=user.job_role,
        job_type=job_type, salary_range=user.salary_range, experience=user.experience,
        company_name=user.company_name, company_type=company_type, company_location=user.company_location,
        company_size=user.company_size,
        company_address=user.company_address,
        company_website=user.company_website,
        company_about=user.company_about,
        company_rating=user.company_rating,
        company_review_count=user.company_review_count,
        company_reviews=user.company_reviews if isinstance(user.company_reviews, list) else None,
        company_rating_source=user.company_rating_source,
        google_place_id=user.google_place_id,
        google_maps_url=user.google_maps_url,
        profile_completion_percentage=profile_completion_percentage,
        welcome_email_status=user.welcome_email_status, welcome_email_error=user.welcome_email_error,
        has_resume=has_resume,
        account_origin=getattr(user, "account_origin", None),
        created_by_name=created_by_name,
        created_by_label=creator_label(getattr(user, "account_origin", None), created_by_name),
        created_at=user.created_at,
        last_active_at=resolved_last_active,
        registered_job_fairs=registered_job_fairs,
    )


async def _creator_name_map(db: AsyncSession, users: List[User]) -> dict:
    ids = list({user.created_by_id for user in users if getattr(user, "created_by_id", None)})
    if not ids:
        return {}
    rows = await db.execute(
        select(User.id, User.first_name, User.last_name, User.email).where(User.id.in_(ids))
    )
    names = {}
    for uid, first, last, email in rows.all():
        names[uid] = f"{first or ''} {last or ''}".strip() or email
    return names


async def _creator_name_for(db: AsyncSession, user: User) -> Optional[str]:
    if not getattr(user, "created_by_id", None):
        return None
    return (await _creator_name_map(db, [user])).get(user.created_by_id)


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


def _start_background_import(
    job_id: str,
    content: bytes,
    role: UserRole,
    filename: str = "",
    created_by_id: Optional[str] = None,
    account_origin: Optional[str] = None,
) -> None:
    import os
    from app.core.config import get_upload_dir
    from app.modules.super_admin.services.import_job_store import update_job
    from app.shared.services.celery_tasks import process_bulk_candidate_import_task

    original_name = (filename or "import.csv").strip() or "import.csv"
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in {".csv", ".xlsx", ".xls", ".txt"}:
        # Detect Excel by magic bytes when the browser omitted a useful extension.
        if content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            ext = ".xls"
        elif len(content) > 4 and content[:2] == b"PK":
            ext = ".xlsx"
        else:
            ext = ".csv"

    update_job(job_id, filename=original_name)

    temp_dir = get_upload_dir() / "temp_imports"
    os.makedirs(temp_dir, exist_ok=True)
    tmp_path = str(temp_dir / f"import_{job_id}{ext}")
    with open(tmp_path, "wb") as f:
        f.write(content)

    role_str = role.value if hasattr(role, "value") else str(role)
    process_bulk_candidate_import_task.delay(
        job_id, tmp_path, role_str, created_by_id, account_origin,
    )


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
        role=admin.role.value if hasattr(admin.role, "value") else str(admin.role or "super_admin"),
        is_super_admin=getattr(admin, "is_super_admin", False),
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
    provider_id: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
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
    if provider_id and provider_id.strip():
        filters.append(JobPosting.provider_id == provider_id.strip())
    filters.extend(_created_range_filters(JobPosting.created_at, created_from, created_to))

    if filters:
        base = base.where(and_(*filters))
        count_q = count_q.where(and_(*filters))

    total = await db.scalar(count_q) or 0
    offset = (page - 1) * page_size
    rows = (
        await db.execute(
            base.order_by(JobPosting.updated_at.desc().nullslast(), JobPosting.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).all()
    job_ids = [job.id for job, _ in rows]
    application_counts: dict = {}
    if job_ids:
        app_count_rows = (
            await db.execute(
                select(Application.job_id, func.count(Application.id))
                .join(JobPosting, Application.job_id == JobPosting.id)
                .where(
                    Application.job_id.in_(job_ids),
                    JobPosting.platform_managed_clause(),
                )
                .group_by(Application.job_id)
            )
        ).all()
        application_counts = {job_id: int(count or 0) for job_id, count in app_count_rows}
    items = [
        AdminJobListItem(
            id=str(job.id),
            provider_id=str(user.id) if user.id else None,
            title=job.title,
            company=user.company_name or _user_display_name(user, "Provider"),
            industry=job.industry,
            location=job.location,
            post_count=int(job.post_count or 0),
            # Official/external listings have no in-platform hiring pipeline.
            application_count=0 if job.is_external_listing else int(application_counts.get(job.id, 0)),
            is_active=bool(job.is_active),
            created_at=job.created_at,
            updated_at=job.updated_at,
            source_platform=job.source_platform,
        )
        for job, user in rows
    ]
    return AdminJobListResponse(items=items, total=int(total), page=page, page_size=page_size)


async def get_platform_job(db: AsyncSession, job_id: str) -> AdminJobDetailResponse:
    result = await db.execute(
        select(JobPosting, User)
        .join(User, JobPosting.provider_id == User.id)
        .where(JobPosting.id == job_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    job, provider = row

    applications_by_status: dict = {}
    application_count = 0
    if not job.is_external_listing:
        status_rows = (
            await db.execute(
                select(Application.status, func.count(Application.id))
                .where(Application.job_id == job.id)
                .group_by(Application.status)
            )
        ).all()
        for status, count in status_rows:
            key = str(status.value if hasattr(status, "value") else status)
            n = int(count or 0)
            applications_by_status[key] = n
            application_count += n

    match_count = int(
        await db.scalar(select(func.count(Match.id)).where(Match.job_id == job.id)) or 0
    )

    job_type = job.job_type.value if job.job_type and hasattr(job.job_type, "value") else job.job_type
    required_skills = job.required_skills if isinstance(job.required_skills, list) else []
    perks = job.perks if isinstance(job.perks, list) else []
    posting_details = job.posting_details if isinstance(job.posting_details, dict) else None

    return AdminJobDetailResponse(
        id=str(job.id),
        provider_id=str(job.provider_id),
        title=job.title,
        description=job.description or "",
        required_skills=required_skills,
        experience_required=job.experience_required,
        job_type=job_type,
        salary_range=job.salary_range,
        industry=job.industry,
        posted_by_name=job.posted_by_name,
        location=job.location,
        is_active=bool(job.is_active),
        post_count=int(job.post_count or 0),
        ai_interview_enabled=bool(job.ai_interview_enabled),
        selection_threshold=int(job.selection_threshold or 70),
        shift=job.shift,
        employment_type=job.employment_type,
        perks=perks,
        posting_details=posting_details,
        source_platform=job.source_platform,
        external_apply_url=job.external_apply_url,
        created_at=job.created_at,
        updated_at=job.updated_at,
        company=provider.company_name or _user_display_name(provider, "Provider"),
        company_type=provider.company_type.value if getattr(provider.company_type, "value", None) else provider.company_type,
        company_industry=(provider.industry or "").strip() or None,
        company_about=(provider.company_about or "").strip() or None,
        provider_email=provider.email,
        provider_phone=provider.phone,
        company_location=provider.company_location,
        company_address=provider.company_address,
        company_size=provider.company_size,
        company_website=provider.company_website,
        company_logo_url=provider.profile_pic_url,
        application_count=application_count,
        applications_by_status=applications_by_status,
        match_count=match_count,
    )


async def list_job_provider_options(
    db: AsyncSession,
    page: int,
    page_size: int,
    search: Optional[str] = None,
) -> AdminJobProviderOptionsResponse:
    """Lightweight provider picker for admin/supervisor job creation (jobs permission)."""
    filters = [User.role == UserRole.provider, User.is_super_admin.is_(False)]
    if search and search.strip():
        filters.append(_build_user_search_filter(search.strip(), include_company=True))

    total = await db.scalar(select(func.count(User.id)).where(*filters)) or 0
    result = await db.execute(
        select(User)
        .where(*filters)
        .order_by(User.company_name.asc().nulls_last(), User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = result.scalars().all()
    items = [
        AdminJobProviderOption(
            id=str(u.id),
            company_name=u.company_name,
            first_name=u.first_name,
            last_name=u.last_name,
            email=u.email,
            industry=u.industry,
            company_location=u.company_location,
        )
        for u in users
    ]
    return AdminJobProviderOptionsResponse(
        items=items,
        total=int(total),
        page=page,
        page_size=page_size,
    )


async def create_platform_job(
    db: AsyncSession,
    body: AdminJobCreate,
    admin: User,
    background_tasks: BackgroundTasks,
) -> AdminJobDetailResponse:
    provider = await _get_role_user(db, body.provider_id, UserRole.provider)
    job_body = JobCreate(
        title=body.title,
        description=body.description,
        required_skills=body.required_skills or [],
        experience_required=body.experience_required,
        job_type=body.job_type,
        salary_range=body.salary_range,
        industry=body.industry,
        posted_by_name=body.posted_by_name,
        location=body.location,
        post_count=body.post_count,
        ai_interview_enabled=body.ai_interview_enabled,
        selection_threshold=body.selection_threshold,
        shift=body.shift,
        employment_type=body.employment_type,
        perks=body.perks or [],
        posting_details=body.posting_details,
        is_active=body.is_active,
    )
    actor_label = f"{(admin.first_name or '').strip()} {(admin.last_name or '').strip()}".strip() or admin.email
    company_label = provider.company_name or _user_display_name(provider, "Provider")
    created = await create_job_for_provider(
        job_body,
        background_tasks,
        provider,
        admin,
        db,
        audit_description=(
            f"Admin/supervisor ({actor_label}) created job '{body.title.strip()}' "
            f"for provider '{company_label}'"
        ),
    )
    return await get_platform_job(db, str(created.id))


def _parse_admin_post_count(value: Optional[str]) -> Optional[int]:
    if value is None or str(value).strip() == "":
        return None
    try:
        count = int(str(value).strip())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Total openings must be a whole number") from exc
    if count < 1:
        raise HTTPException(status_code=422, detail="Total openings must be at least 1")
    if count > 9999:
        raise HTTPException(status_code=422, detail="Total openings cannot exceed 9999")
    return count


def _job_audit_snapshot(job: JobPosting) -> dict:
    """Compact job fields for audit before/after diffs."""
    job_type = getattr(job, "job_type", None)
    if job_type is not None and hasattr(job_type, "value"):
        job_type = job_type.value
    elif job_type is not None:
        job_type = str(job_type)
    skills = getattr(job, "required_skills", None)
    return {
        "title": job.title,
        "location": job.location,
        "industry": job.industry,
        "job_type": job_type,
        "salary_range": job.salary_range,
        "experience_required": job.experience_required,
        "post_count": job.post_count,
        "is_active": bool(job.is_active),
        "ai_interview_enabled": bool(getattr(job, "ai_interview_enabled", False)),
        "selection_threshold": getattr(job, "selection_threshold", None),
        "shift": getattr(job, "shift", None),
        "employment_type": getattr(job, "employment_type", None),
        "perks": getattr(job, "perks", None),
        "posted_by_name": getattr(job, "posted_by_name", None),
        "required_skills": list(skills) if skills is not None else None,
        "description_len": len(job.description or ""),
    }


def _audit_field_diff(before: dict, after: dict) -> dict:
    changed = {}
    for key in sorted(set(before.keys()) | set(after.keys())):
        old = before.get(key)
        new = after.get(key)
        if old != new:
            changed[key] = {"from": old, "to": new}
    return changed


async def update_platform_job(
    db: AsyncSession,
    job_id: str,
    body: AdminJobUpdate,
    admin: User,
    background_tasks: BackgroundTasks,
    request=None,
) -> AdminJobDetailResponse:
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    before = _job_audit_snapshot(job)

    post_count = _parse_admin_post_count(body.post_count)
    update_payload = JobUpdate(
        title=body.title,
        description=body.description,
        required_skills=body.required_skills,
        experience_required=body.experience_required,
        job_type=body.job_type,
        salary_range=body.salary_range,
        location=body.location,
        post_count=post_count,
        ai_interview_enabled=body.ai_interview_enabled,
        selection_threshold=body.selection_threshold,
        shift=body.shift,
        employment_type=body.employment_type,
        perks=body.perks,
        posting_details=body.posting_details,
        is_active=body.is_active,
    )

    was_active = bool(job.is_active)
    content_changed = await update_job_service(job, update_payload, background_tasks)

    if body.industry is not None:
        job.industry = body.industry.strip() or None
        content_changed = True
    if body.posted_by_name is not None:
        job.posted_by_name = body.posted_by_name.strip() or None

    after = _job_audit_snapshot(job)
    field_diff = _audit_field_diff(before, after)
    if "description_len" in field_diff:
        field_diff["description"] = {"from": "(previous text)", "to": "(updated text)"}
        del field_diff["description_len"]

    actor_label = f"{(admin.first_name or '').strip()} {(admin.last_name or '').strip()}".strip() or admin.email
    from app.shared.services.audit_service import log_audit_event

    await log_audit_event(
        db,
        admin,
        action="UPDATE",
        entity_type="job",
        entity_id=str(job.id),
        entity_name=job.title,
        description=f"Admin/supervisor ({actor_label}) updated job posting: '{job.title}'",
        changes={
            "fields_changed": list(field_diff.keys()),
            "diff": field_diff,
            "content_changed": bool(content_changed),
        },
        request=request,
        source_portal="job_portal",
    )
    await db.commit()
    await db.refresh(job)

    if job.is_active and not was_active:
        from app.modules.jobs_portal.controllers.jobs_controller import _queue_job_processing

        _queue_job_processing(background_tasks, str(job.id))
    elif content_changed and job.is_active:
        from app.modules.jobs_portal.services.seeker_matching_service import invalidate_job_matches

        background_tasks.add_task(invalidate_job_matches, job.id)

    return await get_platform_job(db, str(job.id))


async def delete_platform_job(
    db: AsyncSession,
    job_id: str,
    admin: User,
) -> None:
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    actor_label = f"{(admin.first_name or '').strip()} {(admin.last_name or '').strip()}".strip() or admin.email
    from app.shared.services.audit_service import log_audit_event

    await log_audit_event(
        db,
        admin,
        action="DELETE",
        entity_type="job",
        entity_id=str(job.id),
        entity_name=job.title,
        description=f"Admin/supervisor ({actor_label}) deleted job posting: '{job.title}'",
        source_portal="job_portal",
    )
    await db.delete(job)
    await db.commit()


async def deactivate_platform_job(
    db: AsyncSession,
    job_id: str,
    admin: User,
    background_tasks: BackgroundTasks,
) -> AdminJobDetailResponse:
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.is_active:
        return await get_platform_job(db, str(job.id))

    actor_label = f"{(admin.first_name or '').strip()} {(admin.last_name or '').strip()}".strip() or admin.email
    from app.shared.services.audit_service import log_audit_event

    await deactivate_job_service(job)
    await log_audit_event(
        db,
        admin,
        action="STATUS_CHANGE",
        entity_type="job",
        entity_id=str(job.id),
        entity_name=job.title,
        description=f"Admin/supervisor ({actor_label}) closed job posting: '{job.title}'",
        changes={"is_active": False},
        source_portal="job_portal",
    )
    await db.commit()
    schedule_cleanup(background_tasks, job)
    return await get_platform_job(db, str(job.id))


async def activate_platform_job(
    db: AsyncSession,
    job_id: str,
    admin: User,
    background_tasks: BackgroundTasks,
) -> AdminJobDetailResponse:
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.is_active:
        return await get_platform_job(db, str(job.id))

    actor_label = f"{(admin.first_name or '').strip()} {(admin.last_name or '').strip()}".strip() or admin.email
    from app.shared.services.audit_service import log_audit_event
    from app.modules.jobs_portal.controllers.jobs_controller import _queue_job_processing

    await activate_job_service(job)
    await log_audit_event(
        db,
        admin,
        action="STATUS_CHANGE",
        entity_type="job",
        entity_id=str(job.id),
        entity_name=job.title,
        description=f"Admin/supervisor ({actor_label}) activated job posting: '{job.title}'",
        changes={"is_active": True},
        source_portal="job_portal",
    )
    await db.commit()
    _queue_job_processing(background_tasks, str(job.id))
    return await get_platform_job(db, str(job.id))


async def list_platform_matches(
    db: AsyncSession,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    job_id: Optional[str] = None,
    provider_id: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
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
    count_q = (
        select(func.count(Match.id))
        .select_from(Match)
        .join(Seeker, Match.seeker_id == Seeker.id)
        .join(JobPosting, Match.job_id == JobPosting.id)
        .join(Provider, JobPosting.provider_id == Provider.id)
    )

    filters = []
    if job_id and job_id.strip():
        filters.append(Match.job_id == job_id.strip())
    if provider_id and provider_id.strip():
        filters.append(JobPosting.provider_id == provider_id.strip())
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Seeker.first_name.ilike(term),
                Seeker.last_name.ilike(term),
                Seeker.email.ilike(term),
                JobPosting.title.ilike(term),
                Provider.company_name.ilike(term),
            )
        )
    filters.extend(_created_range_filters(Match.created_at, created_from, created_to))
    if filters:
        base = base.where(*filters)
        count_q = count_q.where(*filters)

    total = await db.scalar(count_q) or 0
    offset = (page - 1) * page_size
    rows = (await db.execute(base.order_by(Match.score.desc(), Match.created_at.desc()).offset(offset).limit(page_size))).all()

    app_by_pair: dict[tuple[str, str], Application] = {}
    if rows:
        pair_filters = [
            and_(Application.seeker_id == match.seeker_id, Application.job_id == match.job_id)
            for match, *_ in rows
        ]
        apps_res = await db.execute(select(Application).where(or_(*pair_filters)))
        for app in apps_res.scalars().all():
            if app.seeker_id:
                app_by_pair[(str(app.seeker_id), str(app.job_id))] = app

    items = []
    for match, seeker, job, provider in rows:
        app = app_by_pair.get((str(seeker.id), str(job.id)))
        items.append(
            AdminMatchListItem(
                id=str(match.id),
                seeker_name=_user_display_name(seeker),
                seeker_email=seeker.email,
                seeker_id=str(seeker.id),
                job_id=str(job.id),
                provider_id=str(job.provider_id),
                job_title=job.title,
                company=provider.company_name or _user_display_name(provider, "Provider"),
                score=float(match.score or 0),
                created_at=match.created_at,
                application_id=str(app.id) if app else None,
                application_status=(
                    str(app.status.value if hasattr(app.status, "value") else app.status) if app else None
                ),
                source_platform=job.source_platform,
            )
        )
    return AdminMatchListResponse(items=items, total=int(total), page=page, page_size=page_size)


async def list_platform_applications(
    db: AsyncSession,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
    job_id: Optional[str] = None,
    provider_id: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
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
    count_q = (
        select(func.count(Application.id))
        .select_from(Application)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .join(Provider, JobPosting.provider_id == Provider.id)
        .outerjoin(Seeker, Application.seeker_id == Seeker.id)
    )

    filters = [JobPosting.platform_managed_clause()]
    if job_id and job_id.strip():
        filters.append(Application.job_id == job_id.strip())
    if provider_id and provider_id.strip():
        filters.append(JobPosting.provider_id == provider_id.strip())
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Application.candidate_name.ilike(term),
                Application.candidate_email.ilike(term),
                JobPosting.title.ilike(term),
                Provider.company_name.ilike(term),
                Seeker.first_name.ilike(term),
                Seeker.last_name.ilike(term),
                func.concat(Seeker.first_name, " ", Seeker.last_name).ilike(term),
                Seeker.email.ilike(term),
            )
        )
    if status and status != "all":
        filters.append(Application.status == status)
    # Funnel / application KPIs are period-scoped on applied_at
    filters.extend(_created_range_filters(Application.applied_at, created_from, created_to))
    if filters:
        base = base.where(*filters)
        count_q = count_q.where(*filters)

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
                provider_id=str(job.provider_id),
                job_title=job.title,
                company=provider.company_name or _user_display_name(provider, "Provider"),
                status=str(app.status.value if hasattr(app.status, "value") else app.status),
                applied_at=app.applied_at,
                updated_at=app.updated_at,
                source_platform=job.source_platform,
            )
        )
    return AdminApplicationListResponse(items=items, total=int(total), page=page, page_size=page_size)


def _admin_actor_label(admin: User) -> str:
    return f"{(admin.first_name or '').strip()} {(admin.last_name or '').strip()}".strip() or admin.email or "Admin"


def _provider_company_label(provider: Optional[User]) -> str:
    if not provider:
        return "Provider"
    return provider.company_name or _user_display_name(provider, "Provider")


async def _application_list_item(
    db: AsyncSession,
    app: Application,
) -> AdminApplicationListItem:
    job_result = await db.execute(select(JobPosting).where(JobPosting.id == app.job_id))
    job = job_result.scalar_one_or_none()
    provider = None
    if job:
        provider_result = await db.execute(select(User).where(User.id == job.provider_id))
        provider = provider_result.scalar_one_or_none()
    seeker = None
    if app.seeker_id:
        seeker_result = await db.execute(select(User).where(User.id == app.seeker_id))
        seeker = seeker_result.scalar_one_or_none()
    candidate = app.candidate_name or _user_display_name(seeker, "Candidate")
    return AdminApplicationListItem(
        id=str(app.id),
        candidate_name=candidate,
        candidate_email=app.candidate_email or (seeker.email if seeker else None),
        candidate_phone=app.candidate_phone or (seeker.phone if seeker else None),
        seeker_id=str(app.seeker_id) if app.seeker_id else None,
        job_id=str(app.job_id),
        provider_id=str(job.provider_id) if job else None,
        job_title=job.title if job else "—",
        company=_provider_company_label(provider),
        status=str(app.status.value if hasattr(app.status, "value") else app.status),
        applied_at=app.applied_at,
        updated_at=app.updated_at,
        source_platform=job.source_platform if job else None,
    )


async def update_platform_application_status(
    db: AsyncSession,
    app_id: str,
    status: str,
    admin: User,
    rejection_reason: Optional[str] = None,
) -> AdminApplicationListItem:
    from app.shared.models.notification import NotificationType
    from app.shared.services.audit_service import log_audit_event
    from app.shared.services.notification_service import create_notification
    from app.modules.jobs_portal.services.auto_interview_service import auto_schedule_for_application

    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    allowed = {s.value for s in ApplicationStatus}
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {', '.join(sorted(allowed))}")

    job_result = await db.execute(select(JobPosting).where(JobPosting.id == app.job_id))
    job = job_result.scalar_one_or_none()
    if job is not None and job.is_external_listing:
        raise HTTPException(
            status_code=400,
            detail="This is an official listing. Hiring is not managed on the platform.",
        )

    previous_status = str(app.status.value if hasattr(app.status, "value") else app.status)
    app.status = ApplicationStatus(status)
    if status == "rejected":
        app.rejection_reason = rejection_reason or "Not specified"
    elif status != "rejected":
        app.rejection_reason = None

    provider = None
    if job:
        provider_result = await db.execute(select(User).where(User.id == job.provider_id))
        provider = provider_result.scalar_one_or_none()
    seeker = None
    if app.seeker_id:
        seeker_result = await db.execute(select(User).where(User.id == app.seeker_id))
        seeker = seeker_result.scalar_one_or_none()

    company = _provider_company_label(provider)
    actor_label = _admin_actor_label(admin)
    job_title = job.title if job else "job"

    await log_audit_event(
        db,
        admin,
        action="STATUS_CHANGE",
        entity_type="application",
        entity_id=str(app.id),
        entity_name=job_title,
        description=(
            f"Admin/supervisor ({actor_label}) set application status to '{status}' "
            f"for '{job_title}' on behalf of provider '{company}'"
        ),
        changes={
            "from": previous_status,
            "to": status,
            "rejection_reason": rejection_reason if status == "rejected" else None,
            "provider_id": str(job.provider_id) if job else None,
            "acted_for_provider": True,
        },
        source_portal="job_portal",
        force=True,
    )

    await db.commit()
    await db.refresh(app)

    if seeker and job and status == "shortlisted":
        shortlist_msg = (
            f"Congratulations! You have been shortlisted for '{job.title}' at {company}. "
            f"They may reach out soon."
        )
        await create_notification(
            db=db,
            user_id=seeker.id,
            type=NotificationType.shortlisted,
            title=company,
            message=shortlist_msg,
            related_job_id=str(job.id),
            related_user_id=str(job.provider_id),
            auto_commit=True,
        )
        from app.shared.services.notification_service import queue_notification_email

        queue_notification_email(
            seeker.email, "Resume Shortlisted", shortlist_msg, seeker.first_name or "there"
        )
        if provider:
            try:
                await auto_schedule_for_application(db, app, provider, job)
                await db.commit()
            except Exception:
                logger.exception("Auto-schedule failed for admin shortlist on application %s", app.id)

    if seeker and job and status == "rejected":
        rejected_msg = (
            f"Your application for '{job.title}' was not selected this time. "
            f"Keep applying — better opportunities are ahead."
        )
        await create_notification(
            db=db,
            user_id=seeker.id,
            type=NotificationType.rejected,
            title="Application Update",
            message=rejected_msg,
            related_job_id=str(job.id),
            auto_commit=True,
        )
        from app.shared.services.notification_service import queue_notification_email

        queue_notification_email(
            seeker.email, "Application Update", rejected_msg, seeker.first_name or "there"
        )

    if seeker and job and status == "selected":
        selected_msg = (
            f"Congratulations! You have been selected for '{job.title}' at {company}."
        )
        await create_notification(
            db=db,
            user_id=seeker.id,
            type=NotificationType.shortlisted,
            title="Congratulations",
            message=selected_msg,
            related_job_id=str(job.id),
            related_user_id=str(job.provider_id),
            auto_commit=True,
        )
        from app.shared.services.notification_service import queue_notification_email

        queue_notification_email(
            seeker.email,
            "Congratulations — You're Selected",
            selected_msg,
            seeker.first_name or "there",
        )

    return await _application_list_item(db, app)


async def shortlist_platform_candidate(
    db: AsyncSession,
    seeker_id: str,
    job_id: str,
    admin: User,
) -> AdminApplicationListItem:
    """Create or promote an application to shortlisted on behalf of the job's provider."""
    from app.shared.models.notification import NotificationType
    from app.shared.services.audit_service import log_audit_event
    from app.shared.services.notification_service import create_notification
    from app.modules.jobs_portal.services.auto_interview_service import auto_schedule_for_application

    job_result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.is_external_listing:
        raise HTTPException(
            status_code=400,
            detail="This is an official listing. Hiring is not managed on the platform.",
        )

    provider_result = await db.execute(select(User).where(User.id == job.provider_id))
    provider = provider_result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    seeker_result = await db.execute(select(User).where(User.id == seeker_id))
    seeker = seeker_result.scalar_one_or_none()
    if not seeker:
        raise HTTPException(status_code=404, detail="Candidate not found")

    existing = await db.execute(
        select(Application).where(
            and_(Application.seeker_id == seeker_id, Application.job_id == job_id)
        )
    )
    app = existing.scalar_one_or_none()
    created = False

    if app:
        current = str(app.status.value if hasattr(app.status, "value") else app.status)
        if app.status in (
            ApplicationStatus.shortlisted,
            ApplicationStatus.interviewing,
            ApplicationStatus.selected,
        ):
            raise HTTPException(status_code=409, detail="Candidate is already shortlisted for this job")
        if app.status == ApplicationStatus.rejected:
            raise HTTPException(status_code=409, detail="Candidate was rejected for this job")
        previous_status = current
        app.status = ApplicationStatus.shortlisted
        app.rejection_reason = None
    else:
        previous_status = None
        created = True
        app = Application(
            seeker_id=seeker_id,
            job_id=job_id,
            status=ApplicationStatus.shortlisted,
        )
        db.add(app)

    company = _provider_company_label(provider)
    actor_label = _admin_actor_label(admin)

    await db.flush()
    await log_audit_event(
        db,
        admin,
        action="SHORTLIST",
        entity_type="application",
        entity_id=str(app.id),
        entity_name=job.title,
        description=(
            f"Admin/supervisor ({actor_label}) shortlisted candidate "
            f"'{_user_display_name(seeker)}' for '{job.title}' on behalf of provider '{company}'"
        ),
        changes={
            "from": previous_status,
            "to": "shortlisted",
            "created_application": created,
            "seeker_id": str(seeker_id),
            "job_id": str(job_id),
            "provider_id": str(job.provider_id),
            "acted_for_provider": True,
        },
        source_portal="job_portal",
        force=True,
    )

    await db.commit()
    await db.refresh(app)

    shortlist_msg = (
        f"Congratulations! You have been shortlisted for '{job.title}' at {company}. "
        f"They may reach out soon."
    )
    await create_notification(
        db=db,
        user_id=seeker.id,
        type=NotificationType.shortlisted,
        title=company,
        message=shortlist_msg,
        related_job_id=str(job.id),
        related_user_id=str(job.provider_id),
        auto_commit=True,
    )
    from app.shared.services.notification_service import queue_notification_email

    queue_notification_email(
        seeker.email, "Resume Shortlisted", shortlist_msg, seeker.first_name or "there"
    )

    try:
        await auto_schedule_for_application(db, app, provider, job)
        await db.commit()
    except Exception:
        logger.exception("Auto-schedule failed for admin shortlist on application %s", app.id)

    return await _application_list_item(db, app)


async def list_platform_interviews(
    db: AsyncSession,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
) -> AdminInterviewListResponse:
    from sqlalchemy.orm import aliased
    Seeker = aliased(User)
    Provider = aliased(User)
    schedule_filters = _created_range_filters(Interview.scheduled_at, created_from, created_to)
    base = (
        select(Interview, Seeker, Provider, JobPosting)
        .join(Seeker, Interview.seeker_id == Seeker.id)
        .join(Provider, Interview.provider_id == Provider.id)
        .join(JobPosting, Interview.job_id == JobPosting.id)
    )
    if schedule_filters:
        base = base.where(*schedule_filters)
    if search:
        term = f"%{search.strip()}%"
        base = base.where(or_(Interview.title.ilike(term), JobPosting.title.ilike(term)))
    # Count uses the same joins as the list so totals match visible rows.
    count_q = (
        select(func.count(Interview.id))
        .select_from(Interview)
        .join(Seeker, Interview.seeker_id == Seeker.id)
        .join(Provider, Interview.provider_id == Provider.id)
        .join(JobPosting, Interview.job_id == JobPosting.id)
    )
    if schedule_filters:
        count_q = count_q.where(*schedule_filters)
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
            seeker_id=str(seeker.id) if seeker and seeker.id else None,
            seeker_name=_user_display_name(seeker),
            provider_id=str(provider.id) if provider and provider.id else None,
            provider_name=provider.company_name or _user_display_name(provider, "Provider"),
            job_id=str(job.id) if job and job.id else None,
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
    total_apps = await db.scalar(
        select(func.count(Application.id))
        .select_from(Application)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .where(JobPosting.platform_managed_clause())
    )
    verified = await db.scalar(select(func.count(User.id)).where(User.is_verified.is_(True), User.is_super_admin.is_(False)))
    new_users = await db.scalar(select(func.count(User.id)).where(User.created_at >= thirty_days_ago, User.is_super_admin.is_(False)))
    reg_time = await db.execute(
        select(func.date_trunc("day", User.created_at).label("day"), func.count(User.id))
        .where(and_(User.created_at >= thirty_days_ago, User.is_super_admin.is_(False)))
        .group_by("day").order_by("day")
    )
    registrations_over_time = [{"date": row[0].isoformat() if row[0] else "", "count": row[1]} for row in reg_time.fetchall()]
    apps_status = await db.execute(
        select(Application.status, func.count(Application.id))
        .select_from(Application)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .where(JobPosting.platform_managed_clause())
        .group_by(Application.status)
    )
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
    industry: Optional[str], status: Optional[str] = None, job_fair_id: Optional[str] = None,
    sort_by: Optional[str] = None, sort_dir: Optional[str] = None,
    created_from: Optional[str] = None, created_to: Optional[str] = None,
    profile: Optional[str] = None,
) -> AdminUserListResponse:
    from app.modules.jobs_portal.models.job_fair import JobFairSeeker
    seeker_filters = [User.role == UserRole.seeker, User.is_super_admin.is_(False)]
    industry_clause = _seeker_industry_clause(industry)
    if industry_clause is not None:
        seeker_filters.append(industry_clause)
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

    seeker_filters.extend(_created_range_filters(User.created_at, created_from, created_to))

    count_q = select(func.count(User.id)).where(*seeker_filters)
    select_q = select(User, Portfolio).outerjoin(Portfolio, Portfolio.user_id == User.id).where(*seeker_filters)

    if job_fair_id:
        count_q = count_q.join(JobFairSeeker, JobFairSeeker.seeker_id == User.id).where(JobFairSeeker.job_fair_id == job_fair_id)
        select_q = select_q.join(JobFairSeeker, JobFairSeeker.seeker_id == User.id).where(JobFairSeeker.job_fair_id == job_fair_id)

    sort_key = (sort_by or "created_at").strip().lower()
    ordered = select_q.order_by(_ordered(_seeker_sort_column(sort_by), sort_dir), User.id.desc())
    profile_key = (profile or "").strip().lower()
    # Profile % is computed in Python — load matching rows, sort/filter, then page.
    needs_profile_scan = profile_key == "incomplete" or sort_key == "profile_completion_percentage"
    if needs_profile_scan:
        all_rows = (await db.execute(ordered)).all()
        scored_rows = []
        for user, portfolio in all_rows:
            pct = 0
            if portfolio:
                pct, _, _ = calculate_completion(portfolio, user)
            if profile_key == "incomplete" and pct >= 50:
                continue
            scored_rows.append((user, portfolio, pct))
        if sort_key == "profile_completion_percentage":
            scored_rows.sort(key=lambda row: row[2], reverse=_sort_desc(sort_dir))
        total = len(scored_rows)
        offset = (page - 1) * page_size
        page_slice = scored_rows[offset: offset + page_size]
        user_ids = [user.id for user, _, _ in page_slice]
        has_resume_ids = await _seeker_has_resume_ids(db, user_ids)
        last_active = await _last_active_map(db, user_ids)
        creator_names = await _creator_name_map(db, [user for user, _, _ in page_slice])
        items = []
        for user, _portfolio, pct in page_slice:
            jf_titles = await _seeker_job_fair_names(db, user.id)
            items.append(
                _user_to_admin_out(
                    user,
                    "seeker",
                    profile_completion_percentage=pct,
                    registered_job_fairs=jf_titles,
                    has_resume=user.id in has_resume_ids,
                    last_active_at=last_active.get(user.id),
                    created_by_name=creator_names.get(user.created_by_id),
                )
            )
        return AdminUserListResponse(items=items, total=total, page=page, page_size=page_size)

    total = await db.scalar(count_q)
    result = await db.execute(ordered.offset((page - 1) * page_size).limit(page_size))
    rows = result.all()
    user_ids = [user.id for user, _ in rows]
    has_resume_ids = await _seeker_has_resume_ids(db, user_ids)
    last_active = await _last_active_map(db, user_ids)
    creator_names = await _creator_name_map(db, [user for user, _ in rows])
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
                created_by_name=creator_names.get(user.created_by_id),
            )
        )
    return AdminUserListResponse(items=items, total=total or 0, page=page, page_size=page_size)


async def list_seeker_industries(db: AsyncSession) -> List[str]:
    """Canonical industries for the seekers filter dropdown, aligned across provider, seeker, and admin sides."""
    seen: dict[str, str] = {}
    for item in CANONICAL_INDUSTRIES:
        seen[item.lower()] = item

    # Include any valid distinct non-numeric industries registered in users.industry
    seeker_rows = await db.execute(
        select(User.industry).where(
            User.role == UserRole.seeker,
            User.is_super_admin.is_(False),
            User.industry.isnot(None),
            func.trim(User.industry) != "",
        )
    )
    for (industry,) in seeker_rows.all():
        for parsed in _parse_industries(industry):
            seen.setdefault(parsed.lower(), parsed)

    return sorted(seen.values(), key=str.lower)


def _parse_job_type(value: Optional[str]) -> Optional[JobType]:
    if value is None or not str(value).strip():
        return None
    try:
        return JobType(str(value).strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Job type must be in_office, wfh, or hybrid") from exc


async def _email_seeker_credentials(db: AsyncSession, user: User, plain_password: str) -> None:
    """Email login email + password. Account stays created if SMTP fails."""
    from app.shared.services.email_service import send_welcome_email

    try:
        await send_welcome_email(
            to_email=user.email,
            first_name=user.first_name or "there",
            role="seeker",
            password=plain_password,
            raise_on_error=True,
        )
        user.welcome_email_status = "sent"
        user.welcome_email_error = None
    except Exception as exc:
        logger.exception("Seeker credential email failed for user %s", user.id)
        user.welcome_email_status = "failed"
        user.welcome_email_error = str(exc)[:500]
    await db.commit()


def _queue_seeker_match_refresh(user_id: str) -> None:
    try:
        from app.shared.services.celery_tasks import invalidate_seeker_matches_task

        invalidate_seeker_matches_task.delay(str(user_id))
    except Exception:
        logger.warning("Could not queue seeker match refresh for %s", user_id, exc_info=True)


async def create_seeker(
    body: AdminSeekerCreate,
    db: AsyncSession,
    actor: Optional[User] = None,
) -> AdminUserOut:
    phone = _normalize_phone(body.phone)
    if len(phone) != 10:
        raise HTTPException(status_code=400, detail="Phone must be 10 digits")
    if not body.industry or not body.industry.strip():
        raise HTTPException(status_code=400, detail="Industry Type is required")
    if not body.job_role or not body.job_role.strip():
        raise HTTPException(status_code=400, detail="Job Role is required")
    await _check_duplicate(db, body.email, phone)
    pwd = body.password or _temp_password()
    user = User(
        first_name=body.first_name.strip(), last_name=(body.last_name or "").strip(), email=body.email, phone=phone,
        hashed_password=hash_password(pwd), role=UserRole.seeker, is_verified=True, onboarding_complete=True,
        industry=body.industry.strip(), job_role=body.job_role.strip(), job_type=_parse_job_type(body.job_type),
        salary_range=body.salary_range, experience=body.experience, is_assessment_done=True,
        welcome_email_status="pending",
    )
    stamp_creator(
        user,
        origin=origin_for_actor(actor),
        created_by_id=str(actor.id) if actor else None,
    )
    db.add(user)
    await db.flush()
    portfolio = Portfolio(user_id=user.id)
    apply_seeker_profile_fields(user, portfolio, seeker_profile_payload(body, exclude_unset=False))
    db.add(portfolio)
    from app.shared.services.audit_service import log_audit_event
    await log_audit_event(
        db,
        actor,
        action="CREATE",
        entity_type="seeker",
        entity_id=str(user.id),
        entity_name=_user_display_name(user),
        description=f"Created seeker '{_user_display_name(user)}' ({user.email})",
        changes={"email": user.email, "phone": phone, "industry": user.industry, "job_role": user.job_role},
        source_portal="job_portal",
    )
    await db.commit()
    await db.refresh(user)
    await _email_seeker_credentials(db, user, pwd)
    await db.refresh(user)
    _queue_seeker_match_refresh(user.id)
    return _user_to_admin_out(user, "seeker", created_by_name=actor_display_name(actor))


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
        created_by_name=await _creator_name_for(db, user),
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
    certifications = []
    languages = []
    projects = []
    if portfolio:
        pct, filled, missing = calculate_completion(portfolio, user)
        sections_filled = len(filled)
        sections_total = len(filled) + len(missing)
        skills = normalize_skills(portfolio.skills)
        education_history = normalize_education(portfolio.education)
        work_experiences = normalize_work_experiences(portfolio.work_experiences)
        certifications = normalize_certifications(portfolio.certifications)
        languages = normalize_languages(portfolio.languages)
        projects = normalize_projects(portfolio.projects)

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
            job_id=str(job.id),
            provider_id=str(provider.id) if provider else None,
            job_title=job.title,
            company_name=provider.company_name or _user_display_name(provider, "Provider"),
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
            job_id=str(job.id) if job else None,
            provider_id=str(provider.id) if provider else None,
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
        gender=user.gender or (portfolio.gender if portfolio else None),
        address=user.address,
        highest_qualification=user.highest_qualification,
        stream_specialization=user.stream_specialization,
        college_institute_name=user.college_institute_name,
        preferred_job_sector=user.preferred_job_sector,
        headline=portfolio.headline if portfolio else None,
        bio=portfolio.bio if portfolio else None,
        date_of_birth=portfolio.date_of_birth if portfolio else None,
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
        certifications=certifications,
        languages=languages,
        projects=projects,
        registered_job_fairs=jf_titles,
        account_origin=user.account_origin,
        created_by_name=(creator_name := await _creator_name_for(db, user)),
        created_by_label=creator_label(user.account_origin, creator_name),
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


async def update_seeker(
    user_id: str,
    body: AdminSeekerUpdate,
    db: AsyncSession,
    actor: Optional[User] = None,
) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.seeker)
    new_password = body.password if body.password else None
    await _apply_user_update(db, user, body)
    updates = body.model_dump(exclude_unset=True)
    if "job_type" in updates:
        user.job_type = _parse_job_type(body.job_type)
    for field in ("industry", "job_role", "salary_range", "experience"):
        if field in updates:
            val = updates[field]
            setattr(user, field, val.strip() if isinstance(val, str) else val)
    portfolio = (await db.execute(select(Portfolio).where(Portfolio.user_id == user.id))).scalar_one_or_none()
    if portfolio is None:
        portfolio = Portfolio(user_id=user.id)
        db.add(portfolio)
    apply_seeker_profile_fields(user, portfolio, seeker_profile_payload(body, exclude_unset=True))
    safe_changes = {k: v for k, v in updates.items() if k != "password"}
    if new_password:
        safe_changes["password_reset"] = True
    from app.shared.services.audit_service import log_audit_event
    await log_audit_event(
        db,
        actor,
        action="UPDATE",
        entity_type="seeker",
        entity_id=str(user.id),
        entity_name=_user_display_name(user),
        description=f"Updated seeker '{_user_display_name(user)}' ({user.email})",
        changes=safe_changes or None,
        source_portal="job_portal",
    )
    await db.commit()
    await db.refresh(user)
    if new_password:
        await _email_seeker_credentials(db, user, new_password)
        await db.refresh(user)
    _queue_seeker_match_refresh(user.id)
    return _user_to_admin_out(user, "seeker")


_RESUME_FIELDS_KEPT_WHEN_SET = (
    "experience",
    "highest_qualification",
    "stream_specialization",
    "college_institute_name",
    "preferred_job_sector",
    "job_role",
)


async def upload_seeker_resume(user_id: str, file, background_tasks, db: AsyncSession) -> AdminUserOut:
    """Store a resume for a seeker using the same parser as the seeker upload."""
    from app.modules.jobs_portal.controllers.resumes_controller import upload_resume

    user = await _get_role_user(db, user_id, UserRole.seeker)
    preserved = {
        field: getattr(user, field)
        for field in _RESUME_FIELDS_KEPT_WHEN_SET
        if getattr(user, field)
    }
    await upload_resume(background_tasks, file, user, db)
    await db.refresh(user)
    for field, value in preserved.items():
        setattr(user, field, value)
    if preserved:
        await db.commit()
        await db.refresh(user)
    has_resume = await _seeker_has_resume(db, user.id)
    _queue_seeker_match_refresh(user.id)
    return _user_to_admin_out(user, "seeker", has_resume=has_resume)


async def delete_seeker(
    user_id: str,
    db: AsyncSession,
    actor: Optional[User] = None,
) -> None:
    user = await _get_role_user(db, user_id, UserRole.seeker)
    snapshot_name = _user_display_name(user)
    snapshot_email = user.email
    from app.shared.services.audit_service import log_audit_event
    await log_audit_event(
        db,
        actor,
        action="DELETE",
        entity_type="seeker",
        entity_id=str(user.id),
        entity_name=snapshot_name,
        description=f"Deleted seeker '{snapshot_name}' ({snapshot_email})",
        source_portal="job_portal",
    )
    await _hard_delete_user(db, user)


async def set_seeker_password(
    user_id: str,
    body: AdminSetPasswordRequest,
    db: AsyncSession,
    actor: Optional[User] = None,
) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.seeker)
    user.hashed_password = await async_hash_password(body.password)
    from app.shared.services.audit_service import log_audit_event
    await log_audit_event(
        db,
        actor,
        action="UPDATE",
        entity_type="seeker",
        entity_id=str(user.id),
        entity_name=_user_display_name(user),
        description=f"Reset password for seeker '{_user_display_name(user)}' ({user.email})",
        changes={"password_reset": True},
        source_portal="job_portal",
    )
    await db.commit()
    await db.refresh(user)
    return _user_to_admin_out(user, "seeker")


async def bulk_import_seekers(
    content: bytes,
    filename: str,
    actor: Optional[User] = None,
    db: Optional[AsyncSession] = None,
) -> BulkImportJobStarted:
    import uuid
    job_id = str(uuid.uuid4())
    _create_job(job_id, total=0, role="seeker")
    _start_background_import(
        job_id,
        content,
        UserRole.seeker,
        filename=filename or "",
        created_by_id=str(actor.id) if actor else None,
        account_origin=origin_for_actor(actor) if actor else "import",
    )
    if db is not None:
        from app.shared.services.audit_service import log_audit_event
        await log_audit_event(
            db,
            actor,
            action="IMPORT",
            entity_type="seeker",
            entity_id=job_id,
            entity_name=filename or "seekers_import",
            description=f"Started seeker bulk import job ({filename or 'upload'})",
            changes={"job_id": job_id, "filename": filename or ""},
            source_portal="job_portal",
        )
        await db.commit()
    return BulkImportJobStarted(job_id=job_id)


async def list_providers(
    db: AsyncSession, page: int, page_size: int, search: Optional[str], status: Optional[str] = None,
    sort_by: Optional[str] = None, sort_dir: Optional[str] = None,
    created_from: Optional[str] = None, created_to: Optional[str] = None,
    has_active_job: Optional[bool] = None,
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

    if has_active_job:
        active_provider_ids = (
            select(JobPosting.provider_id)
            .where(JobPosting.is_active.is_(True))
            .distinct()
        )
        provider_filters.append(User.id.in_(active_provider_ids))

    provider_filters.extend(_created_range_filters(User.created_at, created_from, created_to))

    total = await db.scalar(select(func.count(User.id)).where(*provider_filters))
    result = await db.execute(
        select(User).where(*provider_filters)
        .order_by(_ordered(_provider_sort_column(sort_by), sort_dir), User.id.desc())
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


def _apply_provider_company_fields(user: User, body) -> None:
    """Apply optional company-profile fields shared by create/update."""
    mapping = (
        "company_name",
        "company_location",
        "company_size",
        "company_address",
        "company_website",
        "company_about",
        "industry",
        "job_role",
        "company_rating",
        "company_review_count",
        "company_rating_source",
        "google_place_id",
        "google_maps_url",
    )
    for field in mapping:
        val = getattr(body, field, None)
        if val is not None:
            if isinstance(val, str):
                val = val.strip() or None
            setattr(user, field, val)
    reviews = getattr(body, "company_reviews", None)
    if reviews is not None:
        user.company_reviews = reviews


async def create_provider(
    body: AdminProviderCreate,
    db: AsyncSession,
    actor: Optional[User] = None,
) -> AdminUserOut:
    phone = _normalize_phone(body.phone)
    if len(phone) != 10:
        raise HTTPException(status_code=400, detail="Phone must be 10 digits")
    await _check_duplicate(db, body.email, phone)
    pwd = body.password or _temp_password()
    user = User(
        first_name=body.first_name.strip(),
        last_name=body.last_name.strip(),
        email=body.email,
        phone=phone,
        hashed_password=hash_password(pwd),
        role=UserRole.provider,
        is_verified=True,
        onboarding_complete=True,
        company_type=CompanyType(body.company_type) if body.company_type else None,
    )
    _apply_provider_company_fields(user, body)
    db.add(user)
    await db.flush()
    from app.shared.services.audit_service import log_audit_event
    await log_audit_event(
        db,
        actor,
        action="CREATE",
        entity_type="provider",
        entity_id=str(user.id),
        entity_name=user.company_name or _user_display_name(user),
        description=f"Created provider '{_user_display_name(user)}' ({user.email})",
        changes={"email": user.email, "company_name": user.company_name},
        source_portal="job_portal",
    )
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

    # Applications across this provider's jobs (read-only enrichment for CRM detail)
    apps_q = (
        select(Application, JobPosting, User)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .outerjoin(User, Application.seeker_id == User.id)
        .where(JobPosting.provider_id == user.id)
        .order_by(Application.applied_at.desc())
    )
    app_rows = (await db.execute(apps_q)).all()
    app_items: list[ProviderApplicationItem] = []
    shortlisted_count = 0
    interviewing_count = 0
    selected_count = 0
    for app, job, seeker in app_rows:
        status_str = str(app.status.value if hasattr(app.status, "value") else app.status)
        if status_str == "shortlisted":
            shortlisted_count += 1
        elif status_str == "interviewing":
            interviewing_count += 1
        elif status_str == "selected":
            selected_count += 1
        app_items.append(
            ProviderApplicationItem(
                id=str(app.id),
                candidate_name=app.candidate_name or _user_display_name(seeker, "Candidate"),
                candidate_email=app.candidate_email or (seeker.email if seeker else None),
                candidate_phone=app.candidate_phone or (seeker.phone if seeker else None),
                seeker_id=str(app.seeker_id) if app.seeker_id else None,
                job_id=str(job.id),
                job_title=job.title,
                status=status_str,
                applied_at=app.applied_at,
                updated_at=app.updated_at,
            )
        )

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
            seeker_id=str(seeker.id) if seeker else None,
            seeker_name=_user_display_name(seeker),
            job_id=str(job.id) if job else None,
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
        applications=app_items,
        shortlisted_count=shortlisted_count,
        interviewing_count=interviewing_count,
        selected_count=selected_count,
        interviews=interview_items,
    )


async def update_provider(
    user_id: str,
    body: AdminProviderUpdate,
    db: AsyncSession,
    actor: Optional[User] = None,
) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.provider)
    updates = body.model_dump(exclude_unset=True)
    await _apply_user_update(db, user, body)
    if body.company_type is not None:
        user.company_type = CompanyType(body.company_type) if body.company_type else None
    _apply_provider_company_fields(user, body)
    safe_changes = {k: v for k, v in updates.items() if k != "password"}
    if updates.get("password"):
        safe_changes["password_reset"] = True
    from app.shared.services.audit_service import log_audit_event
    await log_audit_event(
        db,
        actor,
        action="UPDATE",
        entity_type="provider",
        entity_id=str(user.id),
        entity_name=user.company_name or _user_display_name(user),
        description=f"Updated provider '{_user_display_name(user)}' ({user.email})",
        changes=safe_changes or None,
        source_portal="job_portal",
    )
    await db.commit()
    await db.refresh(user)
    return _user_to_admin_out(user, "provider")


async def upload_provider_profile_pic(user_id: str, file: UploadFile, db: AsyncSession) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.provider)
    content_type = (file.content_type or "").lower()
    if content_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG, WEBP, or GIF image")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo must be 5 MB or smaller")
    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    upload_dir = get_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"provider_{user.id}_{uuid_lib.uuid4().hex}{ext}"
    (upload_dir / filename).write_bytes(content)
    user.profile_pic_url = f"/uploads/{filename}"
    await db.commit()
    await db.refresh(user)
    return _user_to_admin_out(user, "provider")


async def get_provider_company_profile(user_id: str, db: AsyncSession):
    from app.modules.jobs_portal.services import company_profile_service as company_svc

    user = await _get_role_user(db, user_id, UserRole.provider)
    return await company_svc.get_company_profile(user, db)


async def admin_lookup_company(body):
    from app.modules.jobs_portal.services import company_profile_service as company_svc

    return await company_svc.lookup_company(body)


async def admin_apply_company_lookup(user_id: str, body, db: AsyncSession):
    from app.modules.jobs_portal.services import company_profile_service as company_svc

    user = await _get_role_user(db, user_id, UserRole.provider)
    return await company_svc.apply_lookup(user, body, db)


async def upload_provider_gallery_image(user_id: str, file: UploadFile, db: AsyncSession, caption: Optional[str] = None):
    from app.modules.jobs_portal.services import company_profile_service as company_svc

    user = await _get_role_user(db, user_id, UserRole.provider)
    return await company_svc.upload_gallery_image(user, file, db, caption)


async def delete_provider_gallery_image(user_id: str, image_id: str, db: AsyncSession):
    from app.modules.jobs_portal.services import company_profile_service as company_svc

    user = await _get_role_user(db, user_id, UserRole.provider)
    return await company_svc.delete_gallery_image(user, image_id, db)


async def delete_provider(
    user_id: str,
    db: AsyncSession,
    actor: Optional[User] = None,
) -> None:
    user = await _get_role_user(db, user_id, UserRole.provider)
    snapshot_name = user.company_name or _user_display_name(user)
    snapshot_email = user.email
    from app.shared.services.audit_service import log_audit_event
    await log_audit_event(
        db,
        actor,
        action="DELETE",
        entity_type="provider",
        entity_id=str(user.id),
        entity_name=snapshot_name,
        description=f"Deleted provider '{snapshot_name}' ({snapshot_email})",
        source_portal="job_portal",
    )
    await _hard_delete_user(db, user)


async def set_provider_password(
    user_id: str,
    body: AdminSetPasswordRequest,
    db: AsyncSession,
    actor: Optional[User] = None,
) -> AdminUserOut:
    user = await _get_role_user(db, user_id, UserRole.provider)
    user.hashed_password = await async_hash_password(body.password)
    from app.shared.services.audit_service import log_audit_event
    await log_audit_event(
        db,
        actor,
        action="UPDATE",
        entity_type="provider",
        entity_id=str(user.id),
        entity_name=user.company_name or _user_display_name(user),
        description=f"Reset password for provider '{_user_display_name(user)}' ({user.email})",
        changes={"password_reset": True},
        source_portal="job_portal",
    )
    await db.commit()
    await db.refresh(user)
    return _user_to_admin_out(user, "provider")


async def bulk_import_providers(
    content: bytes,
    filename: str,
    actor: Optional[User] = None,
    db: Optional[AsyncSession] = None,
) -> BulkImportJobStarted:
    import uuid
    job_id = str(uuid.uuid4())
    _create_job(job_id, total=0, role="provider")
    _start_background_import(job_id, content, UserRole.provider, filename=filename or "")
    if db is not None:
        from app.shared.services.audit_service import log_audit_event
        await log_audit_event(
            db,
            actor,
            action="IMPORT",
            entity_type="provider",
            entity_id=job_id,
            entity_name=filename or "providers_import",
            description=f"Started provider bulk import job ({filename or 'upload'})",
            changes={"job_id": job_id, "filename": filename or ""},
            source_portal="job_portal",
        )
        await db.commit()
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
    "created_by_label": "Created By",
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
    if key == "industry":
        if user.industries:
            return ", ".join(user.industries)
        return user.industry or ""
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
    industry_clause = _seeker_industry_clause(body.industry)
    if industry_clause is not None:
        seeker_filters.append(industry_clause)
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
    creator_names = (
        await _creator_name_map(db, [u for u, _ in rows_db]) if "created_by_label" in field_keys else {}
    )

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
            created_by_name=creator_names.get(user.created_by_id),
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
