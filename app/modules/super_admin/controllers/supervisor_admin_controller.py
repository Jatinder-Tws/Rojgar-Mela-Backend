import math
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.super_admin.constants.supervisor_permissions import (
    SUPERVISOR_PERMISSIONS,
    VALID_PERMISSION_KEYS,
    get_categorized_permissions,
)
from app.modules.super_admin.schemas.supervisor import (
    SupervisorCreateRequest,
    SupervisorItemOut,
    SupervisorListResponse,
    SupervisorResetPasswordRequest,
    SupervisorStatusUpdateRequest,
    SupervisorUpdateRequest,
)
from app.shared.models.supervisor_profile import SupervisorProfile
from app.shared.models.user import User, UserRole


def _format_supervisor_out(profile: SupervisorProfile, user: User) -> SupervisorItemOut:
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or (user.email or "Supervisor")
    return SupervisorItemOut(
        id=str(profile.id),
        user_id=str(user.id),
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=full_name,
        email=user.email,
        phone=user.phone,
        department=profile.department,
        is_active=profile.is_active,
        permissions=profile.permissions or [],
        notes=profile.notes,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


async def list_supervisors(
    db: AsyncSession,
    search: Optional[str] = None,
    department: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    limit: int = 20,
) -> SupervisorListResponse:
    query = (
        select(SupervisorProfile, User)
        .join(User, SupervisorProfile.user_id == User.id)
    )

    if search:
        s = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.first_name.ilike(s),
                User.last_name.ilike(s),
                User.email.ilike(s),
                SupervisorProfile.department.ilike(s),
            )
        )

    if department:
        query = query.where(SupervisorProfile.department.ilike(f"%{department.strip()}%"))

    if is_active is not None:
        query = query.where(SupervisorProfile.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # Pagination
    offset = (page - 1) * limit
    query = query.order_by(SupervisorProfile.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    rows = res.all()

    items = [_format_supervisor_out(profile, user) for profile, user in rows]
    pages = math.ceil(total / limit) if limit > 0 else 1

    return SupervisorListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


async def get_permissions_catalog():
    return {
        "flat": SUPERVISOR_PERMISSIONS,
        "categories": get_categorized_permissions(),
    }


async def get_supervisor(supervisor_id: str, db: AsyncSession) -> SupervisorItemOut:
    query = (
        select(SupervisorProfile, User)
        .join(User, SupervisorProfile.user_id == User.id)
        .where(
            or_(
                SupervisorProfile.id == supervisor_id,
                SupervisorProfile.user_id == supervisor_id,
            )
        )
    )
    res = await db.execute(query)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    profile, user = row
    return _format_supervisor_out(profile, user)


async def create_supervisor(
    body: SupervisorCreateRequest,
    current_admin: User,
    db: AsyncSession,
) -> SupervisorItemOut:
    email_clean = body.email.strip().lower()

    # Check if user with email already exists
    existing = await db.execute(select(User).where(User.email == email_clean))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    # Validate permission keys
    valid_perms = [p for p in body.permissions if p in VALID_PERMISSION_KEYS or p == "*"]

    # Create user
    user = User(
        first_name=body.first_name.strip(),
        last_name=body.last_name.strip() if body.last_name else None,
        email=email_clean,
        phone=body.phone.strip() if body.phone else None,
        hashed_password=hash_password(body.password),
        role=UserRole.supervisor,
        is_verified=True,
        onboarding_complete=True,
        is_super_admin=False,
    )
    db.add(user)
    await db.flush()

    # Create supervisor profile
    profile = SupervisorProfile(
        user_id=user.id,
        is_active=True,
        department=body.department.strip() if body.department else None,
        notes=body.notes.strip() if body.notes else None,
        permissions=valid_perms,
        created_by_id=current_admin.id,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    await db.refresh(user)

    # Dispatch welcome email with credentials via Celery queue (with DLQ fallback)
    try:
        from app.shared.services.celery_tasks import send_supervisor_welcome_email_task
        send_supervisor_welcome_email_task.delay(
            email=user.email,
            first_name=user.first_name or "",
            password=body.password,
            department=profile.department,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to enqueue supervisor welcome email task: {e}")

    return _format_supervisor_out(profile, user)


async def update_supervisor(
    supervisor_id: str,
    body: SupervisorUpdateRequest,
    db: AsyncSession,
) -> SupervisorItemOut:
    query = (
        select(SupervisorProfile, User)
        .join(User, SupervisorProfile.user_id == User.id)
        .where(
            or_(
                SupervisorProfile.id == supervisor_id,
                SupervisorProfile.user_id == supervisor_id,
            )
        )
    )
    res = await db.execute(query)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    profile, user = row

    if body.first_name is not None:
        user.first_name = body.first_name.strip()
    if body.last_name is not None:
        user.last_name = body.last_name.strip() if body.last_name else None
    if body.phone is not None:
        user.phone = body.phone.strip() if body.phone else None

    if body.department is not None:
        profile.department = body.department.strip() if body.department else None
    if body.notes is not None:
        profile.notes = body.notes.strip() if body.notes else None
    if body.permissions is not None:
        valid_perms = [p for p in body.permissions if p in VALID_PERMISSION_KEYS or p == "*"]
        profile.permissions = valid_perms
    if body.is_active is not None:
        profile.is_active = body.is_active

    await db.commit()
    await db.refresh(profile)
    await db.refresh(user)

    return _format_supervisor_out(profile, user)


async def update_supervisor_status(
    supervisor_id: str,
    body: SupervisorStatusUpdateRequest,
    db: AsyncSession,
) -> SupervisorItemOut:
    query = (
        select(SupervisorProfile, User)
        .join(User, SupervisorProfile.user_id == User.id)
        .where(
            or_(
                SupervisorProfile.id == supervisor_id,
                SupervisorProfile.user_id == supervisor_id,
            )
        )
    )
    res = await db.execute(query)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    profile, user = row

    profile.is_active = body.is_active
    await db.commit()
    await db.refresh(profile)
    await db.refresh(user)

    return _format_supervisor_out(profile, user)


async def reset_supervisor_password(
    supervisor_id: str,
    body: SupervisorResetPasswordRequest,
    db: AsyncSession,
) -> dict:
    query = (
        select(User)
        .join(SupervisorProfile, SupervisorProfile.user_id == User.id)
        .where(
            or_(
                SupervisorProfile.id == supervisor_id,
                SupervisorProfile.user_id == supervisor_id,
            )
        )
    )
    res = await db.execute(query)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Supervisor user not found")

    user.hashed_password = hash_password(body.new_password)
    await db.commit()

    return {"message": "Supervisor password reset successfully"}


async def delete_supervisor(
    supervisor_id: str,
    db: AsyncSession,
) -> dict:
    query = (
        select(SupervisorProfile, User)
        .join(User, SupervisorProfile.user_id == User.id)
        .where(
            or_(
                SupervisorProfile.id == supervisor_id,
                SupervisorProfile.user_id == supervisor_id,
            )
        )
    )
    res = await db.execute(query)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    profile, user = row

    await db.delete(user)
    await db.commit()

    return {"message": "Supervisor deleted successfully"}
