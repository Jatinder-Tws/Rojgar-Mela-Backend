"""Redis-backed JWT revocation (blacklist) by `jti` claim.

Used on logout and on refresh-token rotation so a token can be invalidated
before its natural expiry. Redis errors fail open (token treated as not
blacklisted) so a transient Redis outage does not lock every user out —
mirrors how the rest of the app already treats Redis as best-effort infra.
"""
import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_PREFIX = "blacklist:jti:"


async def blacklist_jti(jti: str, ttl_seconds: int) -> None:
    """Mark a token's `jti` as revoked for `ttl_seconds` (its remaining lifetime)."""
    if not jti or ttl_seconds <= 0:
        return
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2.0)
        try:
            await r.setex(f"{_PREFIX}{jti}", ttl_seconds, "1")
        finally:
            await r.aclose()
    except Exception:
        logger.warning("Failed to blacklist token jti=%s", jti, exc_info=True)


async def is_jti_blacklisted(jti: str) -> bool:
    if not jti:
        return False
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2.0)
        try:
            return bool(await r.exists(f"{_PREFIX}{jti}"))
        finally:
            await r.aclose()
    except Exception:
        logger.warning("Failed to check blacklist for jti=%s", jti, exc_info=True)
        return False
