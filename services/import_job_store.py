"""In-memory + Redis store for background admin CSV import jobs."""
import json
import uuid
from datetime import datetime
from typing import Any, Optional

_memory: dict[str, dict[str, Any]] = {}
_redis = None

try:
    import redis
    from config import settings

    _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    _redis.ping()
except Exception:
    _redis = None


def _key(job_id: str) -> str:
    return f"admin_import_job:{job_id}"


def create_job(role: str, filename: str = "") -> str:
    job_id = str(uuid.uuid4())
    data = {
        "id": job_id,
        "role": role,
        "filename": filename,
        "status": "queued",
        "progress": 0,
        "total": 0,
        "processed": 0,
        "created": 0,
        "failed": 0,
        "errors": [],
        "email_sent": 0,
        "email_failed": 0,
        "email_logs": [],
        "message": "Queued for processing…",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    save_job(job_id, data)
    return job_id


def save_job(job_id: str, data: dict[str, Any]) -> None:
    data["updated_at"] = datetime.utcnow().isoformat()
    if _redis:
        _redis.setex(_key(job_id), 86400, json.dumps(data))
    else:
        _memory[job_id] = data


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    if _redis:
        raw = _redis.get(_key(job_id))
        if not raw:
            return None
        return json.loads(raw)
    return _memory.get(job_id)


def update_job(job_id: str, **kwargs: Any) -> Optional[dict[str, Any]]:
    data = get_job(job_id)
    if not data:
        return None
    data.update(kwargs)
    save_job(job_id, data)
    return data
