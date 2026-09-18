from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_super_admin_or_permission
from app.modules.jobs_portal.models.site_announcement import SiteAnnouncement
from app.modules.jobs_portal.schemas.site_announcement import (
    SiteAnnouncementCreate,
    SiteAnnouncementListResponse,
    SiteAnnouncementOut,
    SiteAnnouncementPublicOut,
    SiteAnnouncementUpdate,
)
from app.shared.models.user import User

public_router = APIRouter(prefix="/announcements", tags=["announcements"])
admin_router = APIRouter(prefix="/super-admin/announcements", tags=["super-admin-announcements"])


def _order():
    return SiteAnnouncement.sort_order.asc(), SiteAnnouncement.created_at.desc()


@public_router.get("", response_model=List[SiteAnnouncementPublicOut])
async def list_public_announcements(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SiteAnnouncement)
        .where(SiteAnnouncement.is_active.is_(True))
        .order_by(*_order())
        .limit(20)
    )
    return result.scalars().all()


@admin_router.get("", response_model=SiteAnnouncementListResponse)
async def list_admin_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    _admin: User = Depends(require_super_admin_or_permission("announcements")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SiteAnnouncement).order_by(*_order()))
    items = result.scalars().all()
    start = (page - 1) * page_size
    return SiteAnnouncementListResponse(
        items=items[start : start + page_size],
        total=len(items),
    )


@admin_router.post("", response_model=SiteAnnouncementOut, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    body: SiteAnnouncementCreate,
    _admin: User = Depends(require_super_admin_or_permission("announcements")),
    db: AsyncSession = Depends(get_db),
):
    row = SiteAnnouncement(
        text=body.text,
        link_url=body.link_url,
        is_active=body.is_active,
        sort_order=body.sort_order,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@admin_router.patch("/{announcement_id}", response_model=SiteAnnouncementOut)
async def update_announcement(
    announcement_id: str,
    body: SiteAnnouncementUpdate,
    _admin: User = Depends(require_super_admin_or_permission("announcements")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SiteAnnouncement).where(SiteAnnouncement.id == announcement_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Announcement not found")

    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return row


@admin_router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: str,
    _admin: User = Depends(require_super_admin_or_permission("announcements")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SiteAnnouncement).where(SiteAnnouncement.id == announcement_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Announcement not found")
    await db.delete(row)
    await db.commit()
