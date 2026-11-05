"""Regression: legacy industrial_visits with is_deleted=NULL must still list."""

from app.modules.jobs_portal.controllers.industrial_visit_controller import _visit_not_deleted
from app.modules.jobs_portal.models.industrial_visit import IndustrialVisit


def test_visit_not_deleted_excludes_only_true():
    clause = _visit_not_deleted()
    sql = str(clause.compile(compile_kwargs={"literal_binds": True}))
    assert "is_deleted" in sql.lower()
    # is_not(True) matches False and NULL; is_(False) would hide legacy NULL rows.
    assert "true" in sql.lower() or "1" in sql


def test_model_defaults_is_deleted_false():
    assert IndustrialVisit.is_deleted.default.arg is False
