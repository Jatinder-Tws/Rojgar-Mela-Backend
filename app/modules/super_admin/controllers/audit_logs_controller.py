import csv
import io
import math
from datetime import datetime, time, timedelta
from typing import Optional
from fastapi import HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.audit_log import AuditLog
from app.modules.super_admin.schemas.audit_logs import (
    AuditLogItem,
    AuditLogListResponse,
    AuditLogStatsResponse,
)


async def list_audit_logs(
    db: AsyncSession,
    role: Optional[str] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 25,
) -> AuditLogListResponse:
    """Lists paginated audit logs with multi-filter search."""
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    query = select(AuditLog)

    if role:
        query = query.where(AuditLog.actor_role == role.lower().strip())

    if action:
        query = query.where(AuditLog.action == action.upper().strip())

    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type.lower().strip())

    if start_date:
        query = query.where(AuditLog.created_at >= start_date)

    if end_date:
        query = query.where(AuditLog.created_at <= end_date)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                AuditLog.actor_name.ilike(term),
                AuditLog.actor_email.ilike(term),
                AuditLog.entity_name.ilike(term),
                AuditLog.description.ilike(term),
            )
        )

    # Count total matching rows
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate and order by newest first
    offset = (page - 1) * page_size
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.scalars().all()

    items = [AuditLogItem.model_validate(r) for r in rows]
    total_pages = math.ceil(total / page_size) if page_size > 0 else 1

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


async def get_audit_log_detail(db: AsyncSession, log_id: str) -> AuditLogItem:
    """Retrieves a single audit log entry by ID."""
    result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Audit log entry not found")
    return AuditLogItem.model_validate(entry)


async def get_audit_log_stats(db: AsyncSession) -> AuditLogStatsResponse:
    """Calculates audit metrics and breakdown statistics."""
    now = datetime.utcnow()
    start_of_today = datetime.combine(now.date(), time.min)

    # 1. Total counts
    total_all_time = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0
    total_today = (
        await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.created_at >= start_of_today)
        )
    ).scalar() or 0

    # 2. Counts grouped by role
    role_rows = (
        await db.execute(
            select(AuditLog.actor_role, func.count(AuditLog.id)).group_by(AuditLog.actor_role)
        )
    ).all()
    role_counts = {r[0]: r[1] for r in role_rows if r[0]}

    # 3. Counts grouped by action
    action_rows = (
        await db.execute(
            select(AuditLog.action, func.count(AuditLog.id))
            .group_by(AuditLog.action)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
        )
    ).all()
    action_counts = {r[0]: r[1] for r in action_rows if r[0]}

    # 4. Top 5 most active actors
    top_actor_rows = (
        await db.execute(
            select(
                AuditLog.actor_name,
                AuditLog.actor_email,
                AuditLog.actor_role,
                func.count(AuditLog.id).label("count"),
            )
            .group_by(AuditLog.actor_name, AuditLog.actor_email, AuditLog.actor_role)
            .order_by(func.count(AuditLog.id).desc())
            .limit(5)
        )
    ).all()
    top_actors = [
        {"name": r[0], "email": r[1], "role": r[2], "activity_count": r[3]}
        for r in top_actor_rows
    ]

    # 5. Last 7 days trend
    seven_days_ago = now - timedelta(days=7)
    trend_rows = (
        await db.execute(
            select(
                func.date(AuditLog.created_at).label("day"),
                func.count(AuditLog.id).label("count"),
            )
            .where(AuditLog.created_at >= seven_days_ago)
            .group_by(func.date(AuditLog.created_at))
            .order_by(func.date(AuditLog.created_at).asc())
        )
    ).all()
    recent_trend = [{"date": str(r[0]), "count": r[1]} for r in trend_rows]

    return AuditLogStatsResponse(
        total_today=total_today,
        total_all_time=total_all_time,
        role_counts=role_counts,
        action_counts=action_counts,
        top_actors=top_actors,
        recent_trend=recent_trend,
    )


async def export_audit_logs_csv(
    db: AsyncSession,
    role: Optional[str] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> StreamingResponse:
    """Exports matching audit logs to a downloadable CSV stream."""
    query = select(AuditLog)

    if role:
        query = query.where(AuditLog.actor_role == role.lower().strip())
    if action:
        query = query.where(AuditLog.action == action.upper().strip())
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type.lower().strip())
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                AuditLog.actor_name.ilike(term),
                AuditLog.actor_email.ilike(term),
                AuditLog.entity_name.ilike(term),
                AuditLog.description.ilike(term),
            )
        )

    query = query.order_by(AuditLog.created_at.desc()).limit(5000)
    result = await db.execute(query)
    rows = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Timestamp (UTC)",
        "Actor Name",
        "Actor Email",
        "Actor Role",
        "Action",
        "Entity Type",
        "Entity ID",
        "Entity Name",
        "Description",
        "Request Path",
        "Request Method",
        "IP Address",
    ])

    for row in rows:
        writer.writerow([
            row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
            row.actor_name or "",
            row.actor_email or "",
            row.actor_role or "",
            row.action or "",
            row.entity_type or "",
            row.entity_id or "",
            row.entity_name or "",
            row.description or "",
            row.request_path or "",
            row.request_method or "",
            row.ip_address or "",
        ])

    output.seek(0)
    filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
