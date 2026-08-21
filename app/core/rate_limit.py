from __future__ import annotations

from collections import defaultdict, deque
from time import time

from fastapi import HTTPException, Request

_buckets: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host
    return "unknown"


def rate_limit(max_requests: int = 20, window_seconds: int = 60):
    """Simple in-memory sliding window. ~20 req/min per IP+path (PRD 8.5)."""

    async def _dep(request: Request) -> None:
        key = f"{_client_ip(request)}:{request.url.path}"
        now = time()
        bucket = _buckets[key]
        cutoff = now - window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again in a minute.",
            )
        bucket.append(now)

    return _dep
