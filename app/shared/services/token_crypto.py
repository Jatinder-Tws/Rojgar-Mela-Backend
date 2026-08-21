import base64
import hashlib
import hmac
import secrets
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import settings


def _fernet() -> Fernet:
    raw = (settings.TOKEN_ENCRYPTION_KEY or "").strip()
    if raw:
        try:
            return Fernet(raw.encode() if isinstance(raw, str) else raw)
        except (ValueError, TypeError):
            digest = hashlib.sha256(raw.encode()).digest()
            return Fernet(base64.urlsafe_b64encode(digest))
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return _fernet().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def sign_oauth_state(payload: dict, minutes: int = 10) -> str:
    from datetime import datetime, timedelta, timezone

    to_encode = {**payload, "typ": "oauth_state"}
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_oauth_state(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired OAuth state") from exc
    if payload.get("typ") != "oauth_state":
        raise ValueError("Invalid OAuth state")
    return payload


def create_pending_token(payload: dict, minutes: int = 30) -> str:
    from datetime import datetime, timedelta, timezone

    to_encode = {**payload, "typ": "social_pending"}
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_pending_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
    if payload.get("typ") != "social_pending":
        raise ValueError("Invalid token")
    return payload


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
