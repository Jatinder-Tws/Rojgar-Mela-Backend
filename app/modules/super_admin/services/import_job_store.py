import json
import logging
import time
from typing import Dict, Any, Optional
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


def create_job(job_id: str, total: int, role: str = "seeker") -> Dict[str, Any]:
    created_ts = time.time()
    job = {
        "id": job_id,
        "job_id": job_id,
        "role": role,
        "status": "processing",
        "progress": 0.0,
        "processed": 0,
        "total": total,
        "success_count": 0,
        "failed_count": 0,
        "errors": [],
        "created": created_ts,
        "created_at": created_ts,
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
    if r:
        try:
            data = r.get(f"import_job:{job_id}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
    return _IMPORT_JOBS_FALLBACK.get(job_id)


def update_job(job_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    job = get_job(job_id)
    if not job:
        return None

    job.update(kwargs)
    if "processed" in kwargs and job.get("total", 0) > 0:
        job["progress"] = round((job["processed"] / job["total"]) * 100, 1)

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
