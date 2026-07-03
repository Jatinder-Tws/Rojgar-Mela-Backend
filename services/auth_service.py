import random
import string
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User

bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    to_encode.update({"type": "refresh"})
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def otp_expiry() -> datetime:
    return datetime.utcnow() + timedelta(minutes=10)


def generate_secure_password(min_len: int = 8, max_len: int = 15) -> str:
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*"
    alphabet = lower + upper + digits + special
    
    length = secrets.choice(range(min_len, max_len + 1))
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c in lower for c in password) and
            any(c in upper for c in password) and
            any(c in digits for c in password) and
            any(c in special for c in password)):
            return password



async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: Optional[str] = payload.get("type")
        if user_id is None or token_type == "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


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
    if role_str not in ("seeker", "provider"):
        raise HTTPException(status_code=403, detail="Only job seekers and providers can access support")
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
