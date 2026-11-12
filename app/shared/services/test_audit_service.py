"""Unit tests for audit_service portal inference and Super Admin logging."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.shared.models.user import UserRole
from app.shared.services.audit_service import (
    SOURCE_PORTAL_AUTH,
    SOURCE_PORTAL_JOB,
    SOURCE_PORTAL_TRAINING,
    infer_source_portal,
    log_audit_event,
)


def test_infer_source_portal_from_path():
    assert infer_source_portal(request_path="/training-portal/runtime/batches") == SOURCE_PORTAL_TRAINING
    assert infer_source_portal(request_path="/google-calendar/callback") == SOURCE_PORTAL_TRAINING
    assert infer_source_portal(request_path="/auth/login") == SOURCE_PORTAL_AUTH
    assert infer_source_portal(request_path="/supervisor/login") == SOURCE_PORTAL_AUTH
    assert infer_source_portal(request_path="/super-admin/seekers") == SOURCE_PORTAL_JOB
    assert infer_source_portal(request_path="/jobs") == SOURCE_PORTAL_JOB


def test_infer_source_portal_override_wins():
    assert (
        infer_source_portal(request_path="/jobs", source_portal="training_portal")
        == SOURCE_PORTAL_TRAINING
    )
    assert infer_source_portal(source_portal="auth") == SOURCE_PORTAL_AUTH


def _run_log(**kwargs):
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    def _fake_audit_log(**fields):
        return SimpleNamespace(**fields)

    with patch("app.shared.services.audit_service.AuditLog", side_effect=_fake_audit_log):
        entry = asyncio.run(log_audit_event(db, **kwargs))
    return entry, db


def test_log_audit_event_records_superadmin():
    actor = SimpleNamespace(
        id="sa-1",
        email="admin@example.com",
        first_name="Super",
        last_name="Admin",
        role=UserRole.superadmin,
        is_super_admin=True,
    )
    entry, db = _run_log(
        actor=actor,
        action="UPDATE",
        entity_type="job",
        entity_id="job-1",
        entity_name="Demo Job",
        description="Updated job",
        source_portal="job_portal",
    )

    assert entry is not None
    assert entry.actor_role == "superadmin"
    assert entry.source_portal == SOURCE_PORTAL_JOB
    assert entry.action == "UPDATE"
    db.add.assert_called_once()
    db.flush.assert_awaited_once()


def test_log_audit_event_infers_training_portal():
    actor = SimpleNamespace(
        id="t-1",
        email="teacher@example.com",
        first_name="Tea",
        last_name="Cher",
        role=UserRole.teacher,
        is_super_admin=False,
    )
    entry, _db = _run_log(
        actor=actor,
        action="ATTENDANCE_MARK",
        entity_type="attendance",
        entity_id="batch-1",
        description="Marked attendance",
        request_path_override="/training-portal/runtime/class-sessions/1/complete",
        request_method_override="POST",
    )

    assert entry is not None
    assert entry.source_portal == SOURCE_PORTAL_TRAINING
    assert entry.actor_role == "teacher"
