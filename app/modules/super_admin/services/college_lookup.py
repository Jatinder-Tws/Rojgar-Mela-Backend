"""Resolve a college/university by either its UUID id or its public URL slug."""

from __future__ import annotations

import uuid
from typing import Any, List

from sqlalchemy import func, or_

from app.modules.super_admin.models.college_models import College


def college_identity_filter(value: str) -> Any:
    """Build the WHERE clause used to look up a single college.

    ``colleges.id`` is a native PostgreSQL ``UUID`` column, so a public slug such
    as ``"lpu-online"`` must never be compared against it: asyncpg raises
    ``invalid input syntax for type uuid`` and the request dies with a 500 before
    the slug comparison can match. The id branch is therefore only added when the
    incoming value is a well-formed UUID.

    The slug branch is case-insensitive so URLs typed or shared with different
    capitalisation still resolve.
    """
    cleaned = (value or "").strip()
    conditions: List[Any] = [func.lower(College.slug) == cleaned.lower()]
    try:
        uuid.UUID(cleaned)
    except (ValueError, AttributeError, TypeError):
        pass
    else:
        conditions.append(College.id == cleaned)
    return or_(*conditions)