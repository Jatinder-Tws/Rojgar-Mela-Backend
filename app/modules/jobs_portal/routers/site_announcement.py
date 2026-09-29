import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_upload_dir
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


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _order():
    return SiteAnnouncement.sort_order.asc(), SiteAnnouncement.created_at.desc()


@public_router.get("", response_model=List[SiteAnnouncementPublicOut])
async def list_public_announcements(
    placement: Optional[str] = Query(None, description="top_banner | popup_modal | home_slider | all"),
    target_page: Optional[str] = Query(None, description="home | colleges | jobs | training | all"),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    query = select(SiteAnnouncement).where(SiteAnnouncement.is_active.is_(True))

    # Auto-hide expired
    query = query.where(
        or_(
            SiteAnnouncement.expires_at.is_(None),
            SiteAnnouncement.expires_at > now,
        )
    )
    # Start date if set
    query = query.where(
        or_(
            SiteAnnouncement.start_date.is_(None),
            SiteAnnouncement.start_date <= now,
        )
    )

    if placement:
        query = query.where(
            or_(
                SiteAnnouncement.display_placement == placement,
                SiteAnnouncement.display_placement == "all",
            )
        )

    if category:
        query = query.where(SiteAnnouncement.category == category)

    if target_page:
        query = query.where(
            or_(
                SiteAnnouncement.target_pages == "all",
                SiteAnnouncement.target_pages.contains(target_page),
            )
        )

    query = query.order_by(*_order()).limit(50)
    result = await db.execute(query)
    return result.scalars().all()


@admin_router.get("", response_model=SiteAnnouncementListResponse)
async def list_admin_announcements(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    placement: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    _admin: User = Depends(require_super_admin_or_permission("announcements")),
    db: AsyncSession = Depends(get_db),
):
    query = select(SiteAnnouncement)
    if category and category != "all":
        query = query.where(SiteAnnouncement.category == category)
    if placement and placement != "all":
        query = query.where(SiteAnnouncement.display_placement == placement)
    if search:
        s = f"%{search.strip()}%"
        query = query.where(
            or_(
                SiteAnnouncement.title.ilike(s),
                SiteAnnouncement.text.ilike(s),
                SiteAnnouncement.organizer.ilike(s),
                SiteAnnouncement.event_location.ilike(s),
            )
        )

    query = query.order_by(*_order())
    result = await db.execute(query)
    items = result.scalars().all()
    start = (page - 1) * page_size
    return SiteAnnouncementListResponse(
        items=items[start : start + page_size],
        total=len(items),
    )


@admin_router.post("/upload-image")
async def upload_announcement_image(
    file: UploadFile = File(...),
    _admin: User = Depends(require_super_admin_or_permission("announcements")),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")

    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    filename = f"announcement_{uuid.uuid4().hex[:12]}{ext}"
    upload_dir = get_upload_dir() / "announcements"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 15MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    return {"url": f"/api/uploads/announcements/{filename}"}


@admin_router.post("", response_model=SiteAnnouncementOut, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    body: SiteAnnouncementCreate,
    _admin: User = Depends(require_super_admin_or_permission("announcements")),
    db: AsyncSession = Depends(get_db),
):
    row = SiteAnnouncement(
        title=body.title,
        text=body.text,
        category=body.category,
        display_placement=body.display_placement,
        target_pages=body.target_pages,
        image_url=body.image_url,
        link_url=body.link_url,
        link_text=body.link_text,
        event_date=_to_naive_utc(body.event_date),
        event_location=body.event_location,
        organizer=body.organizer,
        home_layout=body.home_layout,
        badge_label=body.badge_label,
        tagline=body.tagline,
        show_content_on_image=body.show_content_on_image,
        gallery_images=body.gallery_images or [],
        qr_code_url=body.qr_code_url,
        modal_delay_seconds=body.modal_delay_seconds,
        start_date=_to_naive_utc(body.start_date),
        expires_at=_to_naive_utc(body.expires_at),
        is_active=body.is_active,
        sort_order=body.sort_order,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@admin_router.get("/{announcement_id}", response_model=SiteAnnouncementOut)
async def get_admin_announcement(
    announcement_id: str,
    _admin: User = Depends(require_super_admin_or_permission("announcements")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SiteAnnouncement).where(SiteAnnouncement.id == announcement_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Announcement not found")
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
        if key in ("event_date", "start_date", "expires_at") and isinstance(value, datetime):
            value = _to_naive_utc(value)
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

