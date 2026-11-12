"""
Superadmin controller – business logic from routers/superadmin.py
"""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.shared.models.user import User, UserRole
from app.shared.schemas.auth import UserOut, TokenResponse
from app.core.dependencies import hash_password, verify_password, create_access_token


class SuperAdminRegisterRequest:
    pass


async def register_superadmin(body, db: AsyncSession) -> TokenResponse:
    if not settings.SUPERADMIN_SECRET_KEY:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SUPERADMIN_SECRET_KEY is not configured.")
    if body.secret_key != settings.SUPERADMIN_SECRET_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid superadmin secret key.")
    existing = await db.execute(select(User).where((User.email == body.email) | (User.phone == body.phone)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="An account with this email or phone already exists")
    user = User(
        first_name=body.first_name, last_name=body.last_name, email=body.email, phone=body.phone,
        role=UserRole.superadmin, hashed_password=hash_password(body.password),
        is_verified=True, onboarding_complete=True, is_assessment_done=True, is_super_admin=True,
    )
    db.add(user)
    await db.flush()
    from app.shared.services.audit_service import log_audit_event
    await log_audit_event(
        db,
        user,
        action="CREATE",
        entity_type="superadmin",
        entity_id=str(user.id),
        entity_name=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
        description=f"Registered super admin account ({user.email})",
        changes={"email": user.email},
        source_portal="auth",
    )
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


async def login_superadmin(body, db: AsyncSession) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No account found with this email")
    if user.role != UserRole.superadmin and not getattr(user, "is_super_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account does not have superadmin privileges")
    if not verify_password(body.password, user.hashed_password):
        from app.shared.services.audit_service import log_audit_event
        await log_audit_event(
            db,
            user,
            action="LOGIN_FAILED",
            entity_type="session",
            entity_id=str(user.id),
            entity_name=f"Super Admin login failed ({user.email})",
            description=f"Failed super admin password login for {user.email}",
            changes={"method": "password"},
            request_path_override="/super-admin/login",
            request_method_override="POST",
            source_portal="auth",
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password")
    if not getattr(user, "is_super_admin", False) or user.role != UserRole.superadmin:
        user.is_super_admin = True
        user.role = UserRole.superadmin
    from app.shared.services.audit_service import log_audit_event
    await log_audit_event(
        db,
        user,
        action="LOGIN",
        entity_type="session",
        entity_id=str(user.id),
        entity_name=f"Super Admin Login ({user.email})",
        description=f"Super admin {user.first_name or ''} {user.last_name or ''} ({user.email}) logged in successfully",
        changes={"method": "password"},
        request_path_override="/super-admin/login",
        request_method_override="POST",
        source_portal="auth",
    )
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))
