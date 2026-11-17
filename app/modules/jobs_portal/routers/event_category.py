import re
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_super_admin_or_permission
from app.modules.jobs_portal.models.event_category import EventCategory
from app.modules.jobs_portal.schemas.event_category import (
    EventCategoryCreate,
    EventCategoryOut,
    EventCategoryUpdate,
)
from app.shared.models.user import User
from app.shared.services.audit_service import log_audit_event

public_router = APIRouter(prefix="/event-categories", tags=["event-categories"])
admin_router = APIRouter(prefix="/super-admin/event-categories", tags=["super-admin-event-categories"])


def slugify_category(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", name).strip().lower()
    cleaned = re.sub(r"[\s_-]+", "-", cleaned)
    return cleaned[:80] or "custom-event"


def is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _find_category_query(category_id: str):
    if is_valid_uuid(category_id):
        return select(EventCategory).where(
            (EventCategory.id == category_id) | (EventCategory.key == category_id)
        )
    return select(EventCategory).where(EventCategory.key == category_id)


PALETTE = [
    ("#F26522", "rgba(242, 101, 34, 0.1)"),
    ("#3B82F6", "rgba(59, 130, 246, 0.1)"),
    ("#10B981", "rgba(16, 185, 129, 0.1)"),
    ("#8B5CF6", "rgba(139, 92, 246, 0.1)"),
    ("#06B6D4", "rgba(6, 182, 212, 0.1)"),
    ("#F59E0B", "rgba(245, 158, 11, 0.1)"),
    ("#EC4899", "rgba(236, 72, 153, 0.1)"),
    ("#7C3AED", "rgba(124, 58, 237, 0.1)"),
    ("#059669", "rgba(5, 150, 105, 0.1)"),
    ("#D97706", "rgba(217, 119, 6, 0.1)"),
]


@public_router.get("", response_model=List[EventCategoryOut])
async def list_public_categories(db: AsyncSession = Depends(get_db)):
    """Public list of active event categories."""
    stmt = (
        select(EventCategory)
        .where(EventCategory.is_active.is_(True))
        .order_by(EventCategory.sort_order.asc(), EventCategory.name.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@admin_router.get("", response_model=List[EventCategoryOut])
async def list_admin_categories(
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin_or_permission("announcements", "events")),
):
    """Admin view of event categories."""
    stmt = select(EventCategory)
    if active_only:
        stmt = stmt.where(EventCategory.is_active.is_(True))
    stmt = stmt.order_by(EventCategory.sort_order.asc(), EventCategory.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@admin_router.post("", response_model=EventCategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: EventCategoryCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("announcements", "events")),
):
    """Create a new event category."""
    name_clean = payload.name.strip()
    if not name_clean:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category name cannot be empty")

    base_key = payload.key.strip() if payload.key and payload.key.strip() else slugify_category(name_clean)
    candidate_key = base_key

    # Check collision and disambiguate if needed
    for i in range(1, 100):
        stmt = select(EventCategory).where(EventCategory.key == candidate_key)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if not existing:
            break
        # If existing has the exact same name, return it if active or reactivate it
        if existing.name.strip().lower() == name_clean.lower():
            if not existing.is_active:
                existing.is_active = True
                await db.commit()
                await db.refresh(existing)
            return existing
        candidate_key = f"{base_key}-{i}"

    # Pick smart color if default is given
    color = payload.tag_color or "#64748B"
    bg = payload.pill_bg or "rgba(100, 116, 139, 0.1)"
    if color == "#64748B":
        palette_idx = abs(hash(name_clean)) % len(PALETTE)
        color, bg = PALETTE[palette_idx]

    category = EventCategory(
        id=str(uuid.uuid4()),
        key=candidate_key,
        name=name_clean,
        description=(payload.description or "").strip(),
        icon_name=payload.icon_name or "Sparkles",
        tag_color=color,
        pill_bg=bg,
        sort_order=payload.sort_order or 0,
        is_active=payload.is_active if payload.is_active is not None else True,
        is_builtin=False,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)

    await log_audit_event(
        db=db,
        actor=admin,
        action="CREATE",
        entity_type="event_category",
        entity_id=category.id,
        entity_name=category.name,
        description=f"Created event category '{category.name}' ({category.key})",
    )

    return category


@admin_router.put("/{category_id}", response_model=EventCategoryOut)
async def update_category(
    category_id: str,
    payload: EventCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("announcements", "events")),
):
    """Update an existing event category."""
    stmt = _find_category_query(category_id)
    cat = (await db.execute(stmt)).scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if payload.name is not None:
        new_name = payload.name.strip()
        if not new_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty")
        cat.name = new_name
    if payload.description is not None:
        cat.description = payload.description.strip()
    if payload.icon_name is not None:
        cat.icon_name = payload.icon_name.strip() or "Sparkles"
    if payload.tag_color is not None:
        cat.tag_color = payload.tag_color.strip() or "#64748B"
    if payload.pill_bg is not None:
        cat.pill_bg = payload.pill_bg.strip() or "rgba(100, 116, 139, 0.1)"
    if payload.sort_order is not None:
        cat.sort_order = payload.sort_order
    if payload.is_active is not None:
        cat.is_active = payload.is_active

    await db.commit()
    await db.refresh(cat)

    await log_audit_event(
        db=db,
        actor=admin,
        action="UPDATE",
        entity_type="event_category",
        entity_id=cat.id,
        entity_name=cat.name,
        description=f"Updated event category '{cat.name}'",
    )

    return cat


@admin_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    permanent: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("announcements", "events")),
):
    """Delete or deactivate an event category."""
    stmt = _find_category_query(category_id)
    cat = (await db.execute(stmt)).scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    cat_name = cat.name
    cat_id = cat.id

    events_count = 0
    try:
        from app.modules.jobs_portal.models.site_announcement import SiteAnnouncement
        stmt_events = select(func.count(SiteAnnouncement.id)).where(
            SiteAnnouncement.category == "event",
            or_(
                SiteAnnouncement.event_profile["category"].astext == cat.key,
                SiteAnnouncement.event_profile["category"].astext == cat.name,
            ),
        )
        events_count = (await db.execute(stmt_events)).scalar() or 0
    except Exception:
        events_count = 0

    if not cat.is_builtin and (events_count == 0 or permanent):
        # Permanently delete if custom and no events attached
        await db.delete(cat)
        await db.commit()
        action_desc = f"Permanently deleted event category '{cat_name}'"
    else:
        # Soft delete to preserve existing event references
        cat.is_active = False
        await db.commit()
        action_desc = f"Deactivated event category '{cat_name}' (associated with {events_count} event(s))"

    await log_audit_event(
        db=db,
        actor=admin,
        action="DELETE",
        entity_type="event_category",
        entity_id=cat_id,
        entity_name=cat_name,
        description=action_desc,
    )
    return None
