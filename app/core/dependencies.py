from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.token_blacklist import is_jti_blacklisted
from app.shared.models.user import User
from app.core.security import (
    hash_password,
    verify_password,
    async_hash_password,
    async_verify_password,
    create_access_token,
    create_refresh_token,
    generate_otp,
    otp_expiry,
    generate_secure_password,
)

bearer_scheme = HTTPBearer()


async def _resolve_user_from_token(token: str, db: AsyncSession) -> User:
    """Decode + validate a JWT and load the matching user. Shared by header-based
    (get_current_user) and query-param-based (get_current_user_ws) auth, since a
    browser WebSocket handshake cannot carry a custom Authorization header."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: Optional[str] = payload.get("type")
        jti: Optional[str] = payload.get("jti")
        if user_id is None or token_type == "refresh":
            raise credentials_exception
        if payload.get("typ") in {"social_pending", "oauth_state"}:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if jti and await is_jti_blacklisted(jti):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not getattr(user, "is_active", True):
        raise HTTPException(status_code=401, detail="User account is deactivated or banned")
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _resolve_user_from_token(credentials.credentials, db)


async def get_current_user_ws(websocket: WebSocket, db: AsyncSession) -> Optional[User]:
    """WebSocket-flavored auth: browsers can't set a custom Authorization header on
    the WS handshake, so the token travels as a `?token=` query param instead. Returns
    None on any auth failure rather than raising, so the caller can close the socket
    with an explicit code instead of letting an HTTPException try to render an HTTP
    response over a WebSocket connection."""
    token = websocket.query_params.get("token")
    if not token:
        return None
    try:
        return await _resolve_user_from_token(token, db)
    except HTTPException:
        return None


async def require_verified(user: User = Depends(get_current_user)) -> User:
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    return user


async def require_authenticated(user: User = Depends(get_current_user)) -> User:
    """Verified seeker/provider or super admin (super admins skip email verification)."""
    if getattr(user, "is_super_admin", False):
        return user
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    return user


async def require_seeker(user: User = Depends(require_verified)) -> User:
    if user.role is None:
        raise HTTPException(status_code=403, detail="Please complete onboarding to access this page")
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role_str != "seeker":
        raise HTTPException(status_code=403, detail="Only job seekers can perform this action")
    return user


async def require_provider(user: User = Depends(require_verified)) -> User:
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role_str != "provider":
        raise HTTPException(status_code=403, detail="Only job providers can perform this action")
    return user


async def require_provider_or_super_admin(user: User = Depends(get_current_user)) -> User:
    if getattr(user, "is_super_admin", False):
        return user
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role_str != "provider":
        raise HTTPException(status_code=403, detail="Only job providers can perform this action")
    return user


async def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if not getattr(user, "is_super_admin", False):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user


async def require_seeker_or_provider(user: User = Depends(require_verified)) -> User:
    if getattr(user, "is_super_admin", False):
        raise HTTPException(status_code=403, detail="Super admins cannot use this endpoint")
    if user.role is None:
        raise HTTPException(status_code=403, detail="Please complete onboarding first")
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role_str not in ("seeker", "provider", "teacher"):
        raise HTTPException(status_code=403, detail="Only job seekers, providers, and teachers can access support")
    return user


async def require_teacher(user: User = Depends(require_verified)) -> User:
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role_str != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can perform this action")
    return user


async def require_teacher_or_super_admin(user: User = Depends(get_current_user)) -> User:
    if getattr(user, "is_super_admin", False):
        return user
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role_str not in ("teacher",):
        raise HTTPException(status_code=403, detail="Only teachers or admins can perform this action")
    return user


async def require_training_portal_user(user: User = Depends(get_current_user)) -> User:
    """Super admin, teacher, or seeker (candidate) using the training portal."""
    if getattr(user, "is_super_admin", False):
        return user
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role or "")
    if role_str in ("teacher", "seeker"):
        return user
    raise HTTPException(status_code=403, detail="Training portal access required")


async def get_current_session_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Optional[str]:
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") == "refresh" or payload.get("typ") in {"social_pending", "oauth_state"}:
            return None
        return payload.get("sid")
    except JWTError:
        return None

