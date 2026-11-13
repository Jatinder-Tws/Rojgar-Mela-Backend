from types import SimpleNamespace

from app.shared.services.account_origin import (
    ORIGIN_SELF,
    ORIGIN_SUPERADMIN,
    ORIGIN_SUPERVISOR,
    actor_display_name,
    creator_label,
    origin_for_actor,
    stamp_creator,
)


def test_origin_for_super_admin_flag():
    actor = SimpleNamespace(is_super_admin=True, role="supervisor", first_name="A", last_name="B")
    assert origin_for_actor(actor) == ORIGIN_SUPERADMIN


def test_origin_for_supervisor_role():
    actor = SimpleNamespace(is_super_admin=False, role=SimpleNamespace(value="supervisor"))
    assert origin_for_actor(actor) == ORIGIN_SUPERVISOR


def test_creator_labels():
    assert creator_label(ORIGIN_SELF) == "Self"
    assert creator_label(ORIGIN_SUPERADMIN, "Anita Sharma") == "Super Admin · Anita Sharma"
    assert creator_label(ORIGIN_SUPERVISOR, "Ravi") == "Supervisor · Ravi"
    assert creator_label(None) == "Not recorded"
    assert creator_label("import") == "Imported"


def test_stamp_and_display_name():
    user = SimpleNamespace(account_origin=None, created_by_id=None)
    stamp_creator(user, origin=ORIGIN_SUPERVISOR, created_by_id="abc")
    assert user.account_origin == ORIGIN_SUPERVISOR
    assert user.created_by_id == "abc"
    assert actor_display_name(SimpleNamespace(first_name="Ravi", last_name="Singh", email="r@x.com")) == "Ravi Singh"
