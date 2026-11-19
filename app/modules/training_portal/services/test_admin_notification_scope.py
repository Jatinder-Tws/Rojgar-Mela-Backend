from types import SimpleNamespace
from sqlalchemy import select, or_

from app.core.database import import_all_models
from app.core.role_helpers import is_super_admin_user, user_role_str
from app.shared.models.user import User, UserRole

import_all_models()


def _has_admin_scope_ref(user) -> bool:
    role = getattr(user, "role", None)
    role_str = role.value if hasattr(role, "value") else str(role or "")
    return bool(getattr(user, "is_super_admin", False)) or role_str in ("superadmin", "supervisor")


def test_has_admin_scope():
    assert _has_admin_scope_ref(SimpleNamespace(is_super_admin=True, role=None)) is True
    assert _has_admin_scope_ref(SimpleNamespace(is_super_admin=False, role=UserRole.superadmin)) is True
    assert _has_admin_scope_ref(SimpleNamespace(is_super_admin=False, role=UserRole.supervisor)) is True
    assert _has_admin_scope_ref(SimpleNamespace(is_super_admin=False, role=UserRole.teacher)) is False
    assert _has_admin_scope_ref(SimpleNamespace(is_super_admin=False, role=UserRole.seeker)) is False
    assert _has_admin_scope_ref(SimpleNamespace(is_super_admin=False, role=UserRole.provider)) is False


def test_admin_query_enum_parameters():
    stmt = select(User.email).where(
        or_(
            User.is_super_admin.is_(True),
            User.role.in_([UserRole.superadmin, UserRole.supervisor]),
        )
    )
    compiled = stmt.compile()
    flat_params = []
    for p in compiled.params.values():
        if isinstance(p, (list, tuple)):
            flat_params.extend(p)
        else:
            flat_params.append(p)
    assert "admin" not in flat_params
    assert UserRole.superadmin in flat_params or "superadmin" in flat_params
    assert UserRole.supervisor in flat_params or "supervisor" in flat_params
