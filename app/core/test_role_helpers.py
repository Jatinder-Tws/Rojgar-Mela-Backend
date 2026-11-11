"""Unit tests for staff-role helpers used by resume download auth."""
from types import SimpleNamespace

from app.core.role_helpers import is_super_admin_user, user_role_str
from app.shared.models.user import UserRole


def test_is_super_admin_user_flag():
    user = SimpleNamespace(is_super_admin=True, role=None)
    assert is_super_admin_user(user) is True


def test_is_super_admin_user_legacy_role():
    user = SimpleNamespace(is_super_admin=False, role=UserRole.superadmin)
    assert is_super_admin_user(user) is True


def test_is_super_admin_user_provider_false():
    user = SimpleNamespace(is_super_admin=False, role=UserRole.provider)
    assert is_super_admin_user(user) is False


def test_user_role_str_enum_and_none():
    assert user_role_str(SimpleNamespace(role=UserRole.supervisor)) == "supervisor"
    assert user_role_str(SimpleNamespace(role=None)) == ""
