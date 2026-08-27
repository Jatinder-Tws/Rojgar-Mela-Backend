"""Redis-backed email OTP storage.

OTPs for email verification live in Redis only (not `otp_records`).
TTL defaults to 5 minutes via settings.OTP_EXPIRE_MINUTES.
"""
from __future__ import annotations

import logging
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

PURPOSE_EMAIL_VERIFY = "email_verify"
PURPOSE_PASSWORD_RESET = "password_reset"
PURPOSE_CONFIRM_EMAIL = "confirm_email"

_redis_client: Optional[aioredis.Redis] = None


async def _get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2.0,
        )
        await _redis_client.ping()
    return _redis_client


def _key(purpose: str, email: str) -> str:
    return f"otp:{purpose}:{email.strip().lower()}"


def _ttl_seconds() -> int:
    minutes = int(getattr(settings, "OTP_EXPIRE_MINUTES", 5) or 5)
    return max(60, minutes * 60)


async def store_otp(email: str, code: str, purpose: str = PURPOSE_EMAIL_VERIFY) -> None:
    """Store (or replace) an OTP for `email`. Previous code for the same purpose is overwritten."""
    if not email or not code:
        raise ValueError("email and code are required")
    try:
        r = await _get_redis()
        await r.setex(_key(purpose, email), _ttl_seconds(), code.strip())
    except Exception as exc:
        logger.exception("Failed to store OTP in Redis for %s", email)
        raise RuntimeError("Unable to store verification code. Please try again.") from exc


async def verify_and_consume_otp(
    email: str,
    code: str,
    purpose: str = PURPOSE_EMAIL_VERIFY,
) -> bool:
    """
    Return True if `code` matches the stored OTP, then delete it (single-use).
    Return False if missing, expired, or incorrect. Does not delete on wrong guess
    so the user can retry within the TTL.
    """
    if not email or not code:
        return False
    try:
        r = await _get_redis()
        key = _key(purpose, email)
        stored = await r.get(key)
        if not stored:
            return False
        if stored.strip() != code.strip():
            return False
        await r.delete(key)
        return True
    except Exception as exc:
        logger.exception("Failed to verify OTP in Redis for %s", email)
        raise RuntimeError("Unable to verify code. Please try again.") from exc


async def delete_otp(email: str, purpose: str = PURPOSE_EMAIL_VERIFY) -> None:
    try:
        r = await _get_redis()
        await r.delete(_key(purpose, email))
    except Exception:
        logger.warning("Failed to delete OTP in Redis for %s", email, exc_info=True)
