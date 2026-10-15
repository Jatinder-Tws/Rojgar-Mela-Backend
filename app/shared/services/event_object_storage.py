"""Object storage for event banner, gallery, and video files only."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
from pathlib import Path

from app.core.config import get_upload_dir, settings

logger = logging.getLogger(__name__)

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
}


def event_s3_configured() -> bool:
    return bool(
        (settings.EVENT_S3_BUCKET or "").strip()
        and (settings.EVENT_S3_ACCESS_KEY or "").strip()
        and (settings.EVENT_S3_SECRET_KEY or "").strip()
    )


def _public_url(key: str) -> str:
    bucket = settings.EVENT_S3_BUCKET.strip()
    endpoint = (settings.EVENT_S3_ENDPOINT_URL or "").strip().rstrip("/")
    base = (settings.EVENT_S3_PUBLIC_BASE_URL or "").strip().rstrip("/")
    # Ignore a public base that still points at a different bucket name.
    if base and (base.endswith(f"/{bucket}") or not endpoint):
        return f"{base}/{key}"
    if endpoint:
        return f"{endpoint}/{bucket}/{key}"
    region = (settings.EVENT_S3_REGION or "us-east-1").strip()
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def _client():
    import boto3

    endpoint = (settings.EVENT_S3_ENDPOINT_URL or "").strip() or None
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=(settings.EVENT_S3_REGION or "us-east-1").strip() or "us-east-1",
        aws_access_key_id=settings.EVENT_S3_ACCESS_KEY.strip(),
        aws_secret_access_key=settings.EVENT_S3_SECRET_KEY.strip(),
    )


def _error_code(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        return str((response.get("Error") or {}).get("Code") or "")
    return ""


def _put_object(key: str, content: bytes, content_type: str) -> str:
    client = _client()
    bucket = settings.EVENT_S3_BUCKET.strip()
    try:
        client.put_object(Bucket=bucket, Key=key, Body=content, ContentType=content_type)
    except Exception as exc:
        if _error_code(exc) != "NoSuchBucket":
            raise
        logger.warning("Event bucket %s does not exist. Creating it.", bucket)
        client.create_bucket(Bucket=bucket)
        client.put_object(Bucket=bucket, Key=key, Body=content, ContentType=content_type)
    return _public_url(key)


def _save_local(folder: str, filename: str, content: bytes) -> str:
    directory = get_upload_dir() / folder
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_bytes(content)
    return f"/uploads/{folder}/{filename}"


async def store_event_file(content: bytes, filename: str, folder: str = "job_fair_banners") -> str:
    """Upload one event file. Uses S3 only when event bucket credentials are set."""
    safe_name = Path(filename).name
    if not event_s3_configured():
        return _save_local(folder, safe_name, content)

    ext = Path(safe_name).suffix.lower()
    content_type = _CONTENT_TYPES.get(ext) or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
    key = f"events/{folder}/{safe_name}"
    try:
        return await asyncio.to_thread(_put_object, key, content, content_type)
    except Exception:
        logger.exception("Event file upload to object storage failed; saving on local disk")
        return _save_local(folder, safe_name, content)
