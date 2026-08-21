from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.shared.models.auth_session import AuthSession
from app.shared.models.login_history import LoginHistory
from app.shared.models.user import User
from app.shared.services.token_crypto import hash_refresh_token


def parse_device_label(user_agent: Optional[str]) -> str:
    ua = (user_agent or "").lower()
    if "edg/" in ua or "edge/" in ua:
        browser = "Edge"
    elif "chrome" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua:
        browser = "Safari"
    else:
        browser = "Browser"

    if "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipad" in ua:
        os_name = "iOS"
    elif "mac os" in ua or "macintosh" in ua:
        os_name = "macOS"
    elif "windows" in ua:
        os_name = "Windows"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Unknown"
    return f"{browser} on {os_name}"


async def is_new_device_and_location(
    db: AsyncSession,
    user_id: str,
    *,
    ip_address: Optional[str],
    user_agent: Optional[str],
) -> bool:
    """True when this login is both a new device and a new IP vs recent successes."""
    device = parse_device_label(user_agent)
    rows = (
        await db.execute(
            select(LoginHistory)
            .where(LoginHistory.user_id == user_id, LoginHistory.status == "success")
            .order_by(LoginHistory.created_at.desc())
            .limit(25)
        )
    ).scalars().all()
    if not rows:
        return False
    known_device = any(row.device_label == device for row in rows)
    known_ip = any(row.ip_address and row.ip_address == ip_address for row in rows) if ip_address else True
    return not known_device and not known_ip


async def log_login_attempt(
    db: AsyncSession,
    *,
    user_id: Optional[str],
    method: str,
    status: str,
    ip_address: Optional[str],
    user_agent: Optional[str],
) -> None:
    db.add(
        LoginHistory(
            user_id=user_id,
            method=method,
            status=status,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:512] or None,
            device_label=parse_device_label(user_agent),
        )
    )


async def create_session_and_tokens(
    db: AsyncSession,
    user: User,
    *,
    method: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra_claims: Optional[dict] = None,
) -> tuple[str, str, AuthSession]:
    session = AuthSession(
        user_id=user.id,
        refresh_token_hash="pending",
        login_method=method,
        ip_address=ip_address,
        device_label=parse_device_label(user_agent),
        user_agent=(user_agent or "")[:512] or None,
        expires_at=datetime.utcnow() + timedelta(days=settings.SESSION_EXPIRE_DAYS),
    )
    db.add(session)
    await db.flush()

    claims = {"sub": user.id, "sid": session.id, "role": getattr(user.role, "value", user.role)}
    if extra_claims:
        claims.update(extra_claims)
    access = create_access_token(claims)
    refresh = create_refresh_token({"sub": user.id, "sid": session.id})
    session.refresh_token_hash = hash_refresh_token(refresh)

    user.last_login_method = method
    user.last_login_at = datetime.utcnow()
    user.failed_login_attempts = 0
    user.locked_until = None
    await log_login_attempt(
        db,
        user_id=user.id,
        method=method,
        status="success",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return access, refresh, session


async def rotate_session(
    db: AsyncSession,
    session: AuthSession,
    user: User,
) -> tuple[str, str]:
    access = create_access_token({"sub": user.id, "sid": session.id, "role": getattr(user.role, "value", user.role)})
    refresh = create_refresh_token({"sub": user.id, "sid": session.id})
    session.refresh_token_hash = hash_refresh_token(refresh)
    session.last_active_at = datetime.utcnow()
    return access, refresh


async def get_session_by_refresh(db: AsyncSession, refresh_token: str) -> Optional[AuthSession]:
    token_hash = hash_refresh_token(refresh_token)
    return await db.scalar(select(AuthSession).where(AuthSession.refresh_token_hash == token_hash))


async def revoke_session(db: AsyncSession, session: AuthSession) -> None:
    session.is_revoked = True


async def revoke_all_sessions(db: AsyncSession, user_id: str, except_id: Optional[str] = None) -> None:
    stmt = update(AuthSession).where(
        AuthSession.user_id == user_id,
        AuthSession.is_revoked.is_(False),
    )
    if except_id:
        stmt = stmt.where(AuthSession.id != except_id)
    await db.execute(stmt.values(is_revoked=True))


def is_session_valid(session: Optional[AuthSession]) -> bool:
    if not session or session.is_revoked:
        return False
    return session.expires_at > datetime.utcnow()
