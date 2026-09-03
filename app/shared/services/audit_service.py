import logging
from typing import Any, Dict, Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.audit_log import AuditLog
from app.shared.models.user import User

logger = logging.getLogger(__name__)


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
) -> Optional[AuditLog]:
    """
    Records an operational action in the audit_logs table.
    
    IMPORTANT:
    Super-Admin actions (is_super_admin == True or role == 'superadmin')
    are EXCLUDED and will never be logged.
    """
    if actor is not None:
        # Strict Super-Admin exclusion check
        if getattr(actor, "is_super_admin", False):
            return None
        role_val = getattr(actor, "role", None)
        if hasattr(role_val, "value"):
            role_val = role_val.value
        if str(role_val).lower() in ("superadmin", "super_admin"):
            return None

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
        )
        db.add(log_entry)
        # Flush so the log entry is prepared with the current transaction
        await db.flush()
        return log_entry
    except Exception as e:
        logger.warning("Failed to record audit log event: %s", e)
        return None
