from typing import Optional
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.modules.super_admin.controllers.supervisor_admin_controller import _format_supervisor_out
from app.modules.super_admin.schemas.supervisor import (
    SupervisorItemOut,
    SupervisorLoginRequest,
    SupervisorLoginResponse,
)
from app.shared.models.supervisor_profile import SupervisorProfile
from app.shared.models.user import User, UserRole
from app.shared.services.audit_service import log_audit_event


async def supervisor_login(
    body: SupervisorLoginRequest,
    db: AsyncSession,
    request: Optional[Request] = None,
) -> SupervisorLoginResponse:
    email_clean = body.email.strip().lower()

    query = (
        select(User, SupervisorProfile)
        .join(SupervisorProfile, SupervisorProfile.user_id == User.id)
        .where(User.email == email_clean)
    )
    res = await db.execute(query)
    row = res.first()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user, profile = row

    if user.role != UserRole.supervisor:
        raise HTTPException(status_code=403, detail="Account is not assigned to the supervisor role")

    if not profile.is_active:
        raise HTTPException(status_code=403, detail="Supervisor account is deactivated. Please contact Super Admin.")

    if not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate JWT tokens
    token_data = {
        "sub": str(user.id),
        "role": "supervisor",
        "email": user.email,
        "permissions": profile.permissions or [],
    }
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data={"sub": str(user.id), "role": "supervisor"})

    user_out = _format_supervisor_out(profile, user)

    await log_audit_event(
        db,
        user,
        action="LOGIN",
        entity_type="session",
        entity_id=str(user.id),
        entity_name=f"Supervisor Login ({user.email})",
        description=f"Supervisor {user.first_name or ''} {user.last_name or ''} ({user.email}) logged in successfully",
        changes={
            "role": "supervisor",
            "department": getattr(profile, "department", None),
            "permissions_count": len(profile.permissions or []),
        },
        request=request,
    )
    await db.commit()

    return SupervisorLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_out,
    )


async def supervisor_me(
    current_user: User,
    db: AsyncSession,
) -> SupervisorItemOut:
    query = (
        select(SupervisorProfile)
        .where(SupervisorProfile.user_id == current_user.id)
    )
    res = await db.execute(query)
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Supervisor profile not found")

    return _format_supervisor_out(profile, current_user)
