import logging
from typing import Any, Dict, Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.audit_log import AuditLog
from app.shared.models.user import User

logger = logging.getLogger(__name__)

SOURCE_PORTAL_JOB = "job_portal"
SOURCE_PORTAL_TRAINING = "training_portal"
SOURCE_PORTAL_AUTH = "auth"
SOURCE_PORTAL_SYSTEM = "system"

_VALID_SOURCE_PORTALS = {
    SOURCE_PORTAL_JOB,
    SOURCE_PORTAL_TRAINING,
    SOURCE_PORTAL_AUTH,
    SOURCE_PORTAL_SYSTEM,
}


def extract_client_ip(request: Optional[Request]) -> Optional[str]:
    """
    Extracts the client IP address from request headers, prioritizing X-Forwarded-For
    to correctly resolve the original client IP behind reverse proxies, load balancers, and CDNs.
    """
    if not request:
        return None

    # 1. Check X-Forwarded-For header (comma-separated list: "client, proxy1, proxy2")
    forwarded_for = (
        request.headers.get("x-forwarded-for")
        or request.headers.get("X-Forwarded-For")
        or request.headers.get("X-FORWARDED-FOR")
    )
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    # 2. Check X-Real-IP header
    real_ip = (
        request.headers.get("x-real-ip")
        or request.headers.get("X-Real-IP")
        or request.headers.get("X-REAL-IP")
    )
    if real_ip and real_ip.strip():
        return real_ip.strip()

    # 3. Check Cloudflare CF-Connecting-IP
    cf_ip = request.headers.get("cf-connecting-ip") or request.headers.get("CF-Connecting-IP")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()

    # 4. Fallback to direct client host connection
    if request.client and request.client.host:
        return request.client.host

    return None


def infer_source_portal(
    request_path: Optional[str] = None,
    source_portal: Optional[str] = None,
) -> str:
    """Resolve source_portal from explicit override or request path prefixes."""
    if source_portal:
        normalized = source_portal.strip().lower()
        if normalized in _VALID_SOURCE_PORTALS:
            return normalized

    path = (request_path or "").lower()
    if path.startswith("/training-portal") or path.startswith("/google-calendar"):
        return SOURCE_PORTAL_TRAINING
    if path.startswith("/auth") or path.startswith("/supervisor/login"):
        return SOURCE_PORTAL_AUTH
    if path.startswith("/superadmin") and "/login" in path:
        return SOURCE_PORTAL_AUTH
    return SOURCE_PORTAL_JOB


async def log_audit_event(
    db: AsyncSession,
    actor: Optional[User],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    description: str = "",
    changes: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
    ip_address_override: Optional[str] = None,
    user_agent_override: Optional[str] = None,
    request_path_override: Optional[str] = None,
    request_method_override: Optional[str] = None,
    actor_name_override: Optional[str] = None,
    actor_role_override: Optional[str] = None,
    actor_email_override: Optional[str] = None,
    source_portal: Optional[str] = None,
    force: bool = False,  # retained for call-site compatibility; no longer excludes actors
) -> Optional[AuditLog]:
    """
    Records an operational action in the audit_logs table for every role,
    including Super Admin. Failures are logged and swallowed so product
    mutations are never blocked by audit persistence issues.

    ``force`` is accepted for backward compatibility with older call sites
    and has no filtering effect.
    """
    _ = force  # compatibility shim

    # Derive actor details
    actor_id = getattr(actor, "id", None) if actor else None
    actor_email = actor_email_override or (getattr(actor, "email", None) if actor else None)

    if actor_name_override:
        actor_name = actor_name_override
    elif actor:
        first = getattr(actor, "first_name", "") or ""
        last = getattr(actor, "last_name", "") or ""
        actor_name = f"{first} {last}".strip() or actor_email or "User"
    else:
        actor_name = "System / Guest"

    if actor_role_override:
        actor_role = actor_role_override
    elif actor:
        role_val = getattr(actor, "role", None)
        actor_role = role_val.value if hasattr(role_val, "value") else str(role_val or "user")
        if getattr(actor, "is_super_admin", False) and str(actor_role).lower() not in (
            "superadmin",
            "super_admin",
        ):
            actor_role = "superadmin"
    else:
        actor_role = "system"

    # Request context
    request_path = request_path_override
    request_method = request_method_override
    ip_address = ip_address_override
    user_agent = user_agent_override

    if request:
        if not request_path:
            request_path = str(request.url.path)[:250]
        if not request_method:
            request_method = request.method
        if not ip_address:
            ip_address = extract_client_ip(request)
        if not user_agent:
            user_agent = request.headers.get("user-agent", "")[:290]

    resolved_portal = infer_source_portal(request_path=request_path, source_portal=source_portal)

    try:
        log_entry = AuditLog(
            actor_id=str(actor_id) if actor_id else None,
            actor_name=actor_name[:145],
            actor_email=actor_email[:250] if actor_email else None,
            actor_role=actor_role.lower(),
            action=action.upper(),
            entity_type=entity_type.lower(),
            entity_id=str(entity_id) if entity_id else None,
            entity_name=entity_name[:250] if entity_name else None,
            description=description or f"{action.capitalize()} {entity_type}",
            changes=changes,
            request_path=request_path,
            request_method=request_method,
            ip_address=ip_address,
            user_agent=user_agent,
            source_portal=resolved_portal,
        )
        db.add(log_entry)
        # Flush so the log entry is prepared with the current transaction
        await db.flush()
        return log_entry
    except Exception as e:
        logger.warning("Failed to record audit log event: %s", e)
        return None
