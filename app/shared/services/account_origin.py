"""Who created a user account: the person themselves, or a staff member."""

from __future__ import annotations

from typing import Optional

ORIGIN_SELF = "self"
ORIGIN_SUPERADMIN = "superadmin"
ORIGIN_SUPERVISOR = "supervisor"
ORIGIN_IMPORT = "import"


def origin_for_actor(actor) -> str:
    """Map the logged-in staff user to a stored origin."""
    if actor is None:
        return ORIGIN_IMPORT
    if getattr(actor, "is_super_admin", False):
        return ORIGIN_SUPERADMIN
    role = getattr(actor, "role", None)
    role_val = role.value if hasattr(role, "value") else str(role or "")
    role_val = role_val.strip().lower()
    if role_val in {"superadmin", "super_admin"}:
        return ORIGIN_SUPERADMIN
    if role_val == "supervisor":
        return ORIGIN_SUPERVISOR
    return role_val or ORIGIN_IMPORT


def actor_display_name(actor) -> Optional[str]:
    if actor is None:
        return None
    name = f"{getattr(actor, 'first_name', '') or ''} {getattr(actor, 'last_name', '') or ''}".strip()
    return name or getattr(actor, "email", None) or None


def stamp_creator(user, *, origin: str, created_by_id: Optional[str] = None) -> None:
    user.account_origin = origin
    if created_by_id:
        user.created_by_id = str(created_by_id)


def creator_label(origin: Optional[str], creator_name: Optional[str] = None) -> str:
    """Admin-facing label. Unknown historical rows stay 'Not recorded'."""
    key = (origin or "").strip().lower()
    name = (creator_name or "").strip()
    if key == ORIGIN_SELF:
        return "Self"
    if key in {ORIGIN_SUPERADMIN, "super_admin"}:
        role = "Super Admin"
    elif key == ORIGIN_SUPERVISOR:
        role = "Supervisor"
    elif key == ORIGIN_IMPORT:
        role = "Imported"
    elif not key:
        return "Not recorded"
    else:
        role = key.replace("_", " ").title()
    return f"{role} · {name}" if name else role
