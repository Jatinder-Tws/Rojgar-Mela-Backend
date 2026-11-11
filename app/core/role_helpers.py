"""Pure role helpers (no FastAPI/JWT imports) for auth checks and unit tests."""
from typing import Any


def user_role_str(user: Any) -> str:
    role = getattr(user, "role", None)
    if role is None:
        return ""
    return role.value if hasattr(role, "value") else str(role)


def is_super_admin_user(user: Any) -> bool:
    """True for flag-based SA and legacy accounts with role=superadmin."""
    if getattr(user, "is_super_admin", False):
        return True
    return user_role_str(user) == "superadmin"
