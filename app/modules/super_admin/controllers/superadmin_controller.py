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
        is_verified=True, onboarding_complete=True, is_assessment_done=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


async def login_superadmin(body, db: AsyncSession) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No account found with this email")
    if user.role != UserRole.superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account does not have superadmin privileges")
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password")
    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))
