import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_IMPORT_JOBS_FALLBACK: Dict[str, Dict[str, Any]] = {}


def _get_redis():
    try:
        import redis
        return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception as e:
        logger.warning(f"Failed to connect Redis for import job store: {e}")
        return None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts_to_iso(value: Any) -> Optional[str]:
    """Coerce legacy float/int Unix timestamps (and pass through strings)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
        except (OSError, OverflowError, ValueError):
            return str(value)
    return str(value)


def normalize_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Shape Redis/in-memory job dict to match ImportJobStatus (legacy-safe)."""
    out = dict(job)

    out["created_at"] = _ts_to_iso(out.get("created_at"))
    if "updated_at" in out:
        out["updated_at"] = _ts_to_iso(out.get("updated_at"))
    if "completed_at" in out and out.get("completed_at") is not None:
        out["completed_at"] = _ts_to_iso(out.get("completed_at"))

    # Early jobs mistakenly stored Unix time in `created` (count field).
    created = out.get("created", 0)
    if isinstance(created, float) or (isinstance(created, int) and created > 10_000_000):
        out["created"] = int(out.get("success_count") or 0)
    else:
        out["created"] = int(created or 0)

    if "failed" not in out and "failed_count" in out:
        out["failed"] = int(out.get("failed_count") or 0)
    else:
        out["failed"] = int(out.get("failed") or 0)

    progress = out.get("progress", 0)
    if isinstance(progress, float):
        out["progress"] = int(round(progress))
    else:
        out["progress"] = int(progress or 0)

    out.setdefault("filename", "")
    out.setdefault("errors", [])
    out.setdefault("email_sent", 0)
    out.setdefault("email_failed", 0)
    out.setdefault("email_logs", [])
    out.setdefault("message", "")
    out.setdefault("processed", 0)
    out.setdefault("total", 0)

    return out


def create_job(job_id: str, total: int, role: str = "seeker") -> Dict[str, Any]:
    now = _utc_now_iso()
    job = {
        "id": job_id,
        "job_id": job_id,
        "role": role,
        "filename": "",
        "status": "processing",
        "progress": 0,
        "processed": 0,
        "total": total,
        "created": 0,
        "failed": 0,
        "errors": [],
        "email_sent": 0,
        "email_failed": 0,
        "email_logs": [],
        "message": "Import queued…",
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }
    r = _get_redis()
    if r:
        try:
            r.setex(f"import_job:{job_id}", 86400, json.dumps(job))
        except Exception as e:
            logger.warning(f"Redis setex failed: {e}")
            _IMPORT_JOBS_FALLBACK[job_id] = job
    else:
        _IMPORT_JOBS_FALLBACK[job_id] = job
    return job


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    r = _get_redis()
    raw: Optional[Dict[str, Any]] = None
    if r:
        try:
            data = r.get(f"import_job:{job_id}")
            if data:
                raw = json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
    if raw is None:
        raw = _IMPORT_JOBS_FALLBACK.get(job_id)
    if raw is None:
        return None
    return normalize_job(raw)


def update_job(job_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    job = get_job(job_id)
    if not job:
        return None

    job.update(kwargs)
    job["updated_at"] = _utc_now_iso()
    if "processed" in kwargs and job.get("total", 0) > 0:
        job["progress"] = int(round((job["processed"] / job["total"]) * 100))

    job = normalize_job(job)

    r = _get_redis()
    if r:
        try:
            r.setex(f"import_job:{job_id}", 86400, json.dumps(job))
        except Exception as e:
            logger.warning(f"Redis update setex failed: {e}")
            _IMPORT_JOBS_FALLBACK[job_id] = job
    else:
        _IMPORT_JOBS_FALLBACK[job_id] = job
    return job
