"""Regression: import job status must serialize to ImportJobStatus (no float created_at)."""

from app.modules.super_admin.schemas.super_admin import ImportJobStatus
from app.modules.super_admin.services.import_job_store import (
    create_job,
    normalize_job,
)


def test_create_job_matches_import_job_status_schema():
    job = create_job("job-abc", total=0, role="seeker")
    status = ImportJobStatus(**job)
    assert status.id == "job-abc"
    assert status.role == "seeker"
    assert status.status == "processing"
    assert status.created == 0
    assert status.failed == 0
    assert isinstance(status.created_at, str)
    assert status.message


def test_normalize_legacy_float_created_at():
    legacy = {
        "id": "legacy-1",
        "role": "seeker",
        "status": "processing",
        "progress": 12.5,
        "processed": 1,
        "total": 8,
        "success_count": 1,
        "failed_count": 0,
        "errors": [],
        "created": 1793787147.5946364,
        "created_at": 1793787147.5946364,
        "message": "Processed 1 of 8 rows…",
    }
    normalized = normalize_job(legacy)
    status = ImportJobStatus(**normalized)
    assert isinstance(status.created_at, str)
    assert status.created == 1
    assert status.failed == 0
    assert status.progress == 12
