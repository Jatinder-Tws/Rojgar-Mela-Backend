"""
Raw SQL helpers for job_fairs table (actual DB schema differs from ORM model).
"""
import json
import uuid
from datetime import date, datetime, time
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.job_fair import JobFairOut

_FAIR_SELECT = """
    id, name, description, industries, event_date, venue, status,
    slug, banner_image_url, created_at, updated_at
"""


def _slug_from_row(row: Any) -> str:
    if getattr(row, "slug", None):
        return str(row.slug)
    return str(row.id)


def _parse_industries(val: Any) -> Optional[list[str]]:
    if val is None:
        return None
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else None
        except json.JSONDecodeError:
            return None
    return None


def _row_to_out(row: Any) -> JobFairOut:
    event_date = row.event_date
    if isinstance(event_date, datetime):
        fair_date = event_date
    elif isinstance(event_date, date):
        fair_date = datetime.combine(event_date, time.min)
    else:
        fair_date = row.created_at or datetime.utcnow()

    status = str(row.status) if row.status is not None else "draft"
    return JobFairOut(
        id=str(row.id),
        slug=_slug_from_row(row),
        title=row.name or "Untitled Job Fair",
        description=row.description,
        date=fair_date,
        location=row.venue or "",
        banner_image_url=getattr(row, "banner_image_url", None),
        is_active=status == "active",
        industries=_parse_industries(row.industries),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_event_date(dt: datetime) -> date:
    return dt.date() if isinstance(dt, datetime) else dt


def _status_from_active(is_active: bool) -> str:
    return "active" if is_active else "draft"


async def slug_exists_db(
    db: AsyncSession, slug: str, exclude_id: Optional[str] = None
) -> bool:
    sql = "SELECT 1 FROM job_fairs WHERE slug = :slug"
    params: dict[str, Any] = {"slug": slug}
    if exclude_id:
        sql += " AND id::text != :exclude_id"
        params["exclude_id"] = exclude_id
    sql += " LIMIT 1"
    return (await db.execute(text(sql), params)).fetchone() is not None


async def list_job_fairs_db(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    sort_by: str = "date_asc",
    page: int = 1,
    page_size: int = 12,
) -> tuple[list[JobFairOut], int]:
    params: dict[str, Any] = {"limit": page_size, "offset": (page - 1) * page_size}
    where = ""
    if search and search.strip():
        where = "WHERE name ILIKE :search OR venue ILIKE :search"
        params["search"] = f"%{search.strip()}%"

    order_map = {
        "date_desc": "event_date DESC NULLS LAST, created_at DESC",
        "title_asc": "name ASC",
        "title_desc": "name DESC",
        "date_asc": "event_date ASC NULLS LAST, created_at ASC",
    }
    order_clause = order_map.get(sort_by, order_map["date_asc"])

    count_sql = text(f"SELECT COUNT(*) FROM job_fairs {where}")
    total = (await db.execute(count_sql, params)).scalar() or 0

    list_sql = text(
        f"""
        SELECT {_FAIR_SELECT}
        FROM job_fairs
        {where}
        ORDER BY {order_clause}
        LIMIT :limit OFFSET :offset
        """
    )
    rows = (await db.execute(list_sql, params)).fetchall()
    return [_row_to_out(r) for r in rows], int(total)


async def get_job_fair_db(db: AsyncSession, id_or_slug: str) -> Optional[JobFairOut]:
    sql = text(
        f"""
        SELECT {_FAIR_SELECT}
        FROM job_fairs
        WHERE id::text = :key OR slug = :key
        LIMIT 1
        """
    )
    row = (await db.execute(sql, {"key": id_or_slug})).fetchone()
    return _row_to_out(row) if row else None


async def list_job_fairs_for_ids_db(db: AsyncSession, fair_ids: list[str]) -> list[JobFairOut]:
    if not fair_ids:
        return []
    sql = text(
        f"""
        SELECT {_FAIR_SELECT}
        FROM job_fairs
        WHERE id::text = ANY(:ids)
        ORDER BY event_date DESC NULLS LAST, created_at DESC
        """
    )
    rows = (await db.execute(sql, {"ids": fair_ids})).fetchall()
    return [_row_to_out(r) for r in rows]


async def create_job_fair_db(
    db: AsyncSession,
    *,
    title: str,
    description: Optional[str],
    fair_date: datetime,
    location: str,
    is_active: bool,
    slug: str,
    banner_image_url: Optional[str] = None,
    industries: Optional[list[str]] = None,
    created_by_id: Optional[str] = None,
) -> JobFairOut:
    fair_id = str(uuid.uuid4())
    now = datetime.utcnow()
    sql = text(
        f"""
        INSERT INTO job_fairs (
            id, name, description, industries, event_date, venue, status,
            slug, banner_image_url, created_by_id, created_at, updated_at
        ) VALUES (
            :id, :name, :description, CAST(:industries AS json), :event_date, :venue,
            CAST(:status AS jobfairstatus), :slug, :banner_image_url, :created_by_id,
            :created_at, :updated_at
        )
        RETURNING {_FAIR_SELECT}
        """
    )
    row = (
        await db.execute(
            sql,
            {
                "id": fair_id,
                "name": title,
                "description": description,
                "industries": json.dumps(industries) if industries else None,
                "event_date": _to_event_date(fair_date),
                "venue": location,
                "status": _status_from_active(is_active),
                "slug": slug,
                "banner_image_url": banner_image_url,
                "created_by_id": created_by_id,
                "created_at": now,
                "updated_at": now,
            },
        )
    ).fetchone()
    await db.commit()
    return _row_to_out(row)


async def update_job_fair_db(
    db: AsyncSession,
    fair_id: str,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    fair_date: Optional[datetime] = None,
    location: Optional[str] = None,
    is_active: Optional[bool] = None,
    slug: Optional[str] = None,
    banner_image_url: Optional[str] = None,
    industries: Optional[list[str]] = None,
) -> Optional[JobFairOut]:
    sets: list[str] = ["updated_at = :updated_at"]
    params: dict[str, Any] = {"id": fair_id, "updated_at": datetime.utcnow()}

    if title is not None:
        sets.append("name = :name")
        params["name"] = title
    if description is not None:
        sets.append("description = :description")
        params["description"] = description
    if fair_date is not None:
        sets.append("event_date = :event_date")
        params["event_date"] = _to_event_date(fair_date)
    if location is not None:
        sets.append("venue = :venue")
        params["venue"] = location
    if is_active is not None:
        sets.append("status = CAST(:status AS jobfairstatus)")
        params["status"] = _status_from_active(is_active)
    if slug is not None:
        sets.append("slug = :slug")
        params["slug"] = slug
    if banner_image_url is not None:
        sets.append("banner_image_url = :banner_image_url")
        params["banner_image_url"] = banner_image_url
    if industries is not None:
        sets.append("industries = CAST(:industries AS json)")
        params["industries"] = json.dumps(industries)

    sql = text(
        f"""
        UPDATE job_fairs
        SET {", ".join(sets)}
        WHERE id::text = :id
        RETURNING {_FAIR_SELECT}
        """
    )
    row = (await db.execute(sql, params)).fetchone()
    if not row:
        return None
    await db.commit()
    return _row_to_out(row)


async def set_job_fair_banner_db(
    db: AsyncSession, fair_id: str, banner_image_url: str
) -> Optional[JobFairOut]:
    return await update_job_fair_db(
        db, fair_id, banner_image_url=banner_image_url
    )


async def delete_job_fair_db(db: AsyncSession, fair_id: str) -> bool:
    result = await db.execute(
        text("DELETE FROM job_fairs WHERE id::text = :id RETURNING id"),
        {"id": fair_id},
    )
    deleted = result.fetchone()
    if deleted:
        await db.commit()
        return True
    return False
