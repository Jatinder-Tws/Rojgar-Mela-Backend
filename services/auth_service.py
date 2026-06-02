import random
import string
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


def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def otp_expiry() -> datetime:
    return datetime.utcnow() + timedelta(minutes=10)


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
        if user_id is None:
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


async def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if not getattr(user, "is_super_admin", False):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user
