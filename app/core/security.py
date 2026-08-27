import asyncio
import random
import string
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
import bcrypt

from app.core.config import settings


def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


async def async_hash_password(password: str) -> str:
    return await asyncio.to_thread(hash_password, password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


async def async_verify_password(plain: str, hashed: str) -> bool:
    return await asyncio.to_thread(verify_password, plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "jti": uuid.uuid4().hex})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    to_encode.update({"type": "refresh"})
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "jti": uuid.uuid4().hex})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def otp_expiry() -> datetime:
    # Naive UTC: otp_records.expires_at is TIMESTAMP WITHOUT TIME ZONE.
    # asyncpg rejects tz-aware datetimes for that column.
    # Prefer Redis OTP TTL (settings.OTP_EXPIRE_MINUTES); this remains for
    # any legacy DB OTP paths (e.g. password reset until migrated).
    minutes = int(getattr(settings, "OTP_EXPIRE_MINUTES", 5) or 5)
    return datetime.utcnow() + timedelta(minutes=minutes)


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
