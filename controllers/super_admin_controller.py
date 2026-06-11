"""
Super Admin controller – business logic from routers/super_admin.py
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.application import Application
from models.job import JobPosting
from models.portfolio import Portfolio
from models.user import CompanyType, JobType, User, UserRole
from schemas.super_admin import (
    AdminProviderCreate, AdminProviderUpdate, AdminSeekerCreate, AdminSeekerUpdate,
    AdminSetPasswordRequest, AdminUserListResponse, AdminUserOut, BulkImportJobStarted,
    DetailedPlatformAnalytics, ImportJobStatus, PlatformStatsResponse,
    SuperAdminLoginRequest, SuperAdminLoginResponse,
)
from services.auth_service import create_access_token, hash_password, verify_password
from services.import_job_store import create_job as _create_job, get_job as _get_job
from services.super_admin_analytics import get_detailed_platform_analytics
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


def super_admin_me(admin: User) -> dict:
    return {"id": admin.id, "email": admin.email, "first_name": admin.first_name, "last_name": admin.last_name, "role": "super_admin", "is_super_admin": True}


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


def get_import_job_status(job_id: str) -> ImportJobStatus:
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    return ImportJobStatus(**job)


async def list_seekers(db: AsyncSession, page: int, page_size: int, search: Optional[str], industry: Optional[str]) -> AdminUserListResponse:
    seeker_filters = [User.role == UserRole.seeker, User.is_super_admin.is_(False)]
    if industry:
        seeker_filters.append(User.industry.ilike(f"%{industry.strip()}%"))
    if search:
        seeker_filters.append(_build_user_search_filter(search.strip()))
    total = await db.scalar(select(func.count(User.id)).where(*seeker_filters))
    result = await db.execute(
        select(User, Portfolio).outerjoin(Portfolio, Portfolio.user_id == User.id)
        .where(*seeker_filters).order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    items = []
    from models.job_fair import JobFair, JobFairSeeker
    for user, portfolio in result.all():
        pct = 0
        if portfolio:
            pct, _, _ = calculate_completion(portfolio, user)
        # Fetch registered job fairs
        jf_res = await db.execute(
            select(JobFair.title)
            .join(JobFairSeeker, JobFairSeeker.job_fair_id == JobFair.id)
            .where(JobFairSeeker.seeker_id == user.id)
            .order_by(JobFairSeeker.registered_at.desc())
        )
        jf_titles = [r[0] for r in jf_res.all()]
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
    from models.job_fair import JobFair, JobFairSeeker
    jf_res = await db.execute(
        select(JobFair.title)
        .join(JobFairSeeker, JobFairSeeker.job_fair_id == JobFair.id)
        .where(JobFairSeeker.seeker_id == user.id)
        .order_by(JobFairSeeker.registered_at.desc())
    )
    jf_titles = [r[0] for r in jf_res.all()]
    return _user_to_admin_out(user, "seeker", profile_completion_percentage=pct, registered_job_fairs=jf_titles)


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


async def list_providers(db: AsyncSession, page: int, page_size: int, search: Optional[str]) -> AdminUserListResponse:
    provider_filters = [User.role == UserRole.provider, User.is_super_admin.is_(False)]
    if search:
        provider_filters.append(_build_user_search_filter(search.strip(), include_company=True))
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
    """Create default super admin from env if missing."""
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
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
