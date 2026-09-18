from __future__ import annotations

import os
import uuid
from typing import Any, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_upload_dir
from app.modules.jobs_portal.models.company_gallery import CompanyGalleryImage
from app.modules.jobs_portal.schemas.company_profile import (
    CompanyApplyLookupRequest,
    CompanyGalleryImageOut,
    CompanyLookupPreview,
    CompanyLookupRequest,
    CompanyLookupResponse,
    CompanyPlaceCandidate,
    CompanyProfileOut,
    CompanyProfileUpdateRequest,
    CompanyReviewItem,
)
from app.modules.jobs_portal.services.company_website_service import fetch_website_preview
from app.modules.jobs_portal.services.google_places_service import (
    download_place_photo,
    lookup_places,
    places_enabled,
)
from app.shared.models.user import User

MAX_GALLERY_IMAGES = 8
MAX_GALLERY_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}


def _reviews_from_user(user: User) -> list[CompanyReviewItem]:
    raw = user.company_reviews or []
    if not isinstance(raw, list):
        return []
    items: list[CompanyReviewItem] = []
    for row in raw:
        if isinstance(row, dict):
            items.append(CompanyReviewItem.model_validate(row))
    return items


def serialize_gallery(image: CompanyGalleryImage) -> CompanyGalleryImageOut:
    return CompanyGalleryImageOut.model_validate(image)


def serialize_company_profile(user: User, gallery: list[CompanyGalleryImage]) -> CompanyProfileOut:
    return CompanyProfileOut(
        places_enabled=places_enabled(),
        company_name=user.company_name,
        company_website=user.company_website,
        company_about=user.company_about,
        company_address=user.company_address,
        company_location=user.company_location,
        company_size=user.company_size,
        industry=user.industry,
        company_rating=user.company_rating,
        company_review_count=user.company_review_count,
        company_reviews=_reviews_from_user(user),
        company_rating_source=user.company_rating_source,
        google_place_id=user.google_place_id,
        google_maps_url=user.google_maps_url,
        logo_url=user.profile_pic_url,
        gallery=[serialize_gallery(img) for img in gallery],
    )


def public_company_payload(provider: Optional[User]) -> dict[str, Any]:
    """Public company card. Never includes phone, email, or recruiter identity."""
    if not provider:
        return {}
    gallery_rel = getattr(provider, "company_gallery_images", None) or []
    gallery = []
    for img in gallery_rel:
        gallery.append(
            {
                "id": img.id,
                "image_url": img.image_url,
                "caption": img.caption,
            }
        )
    reviews = []
    for row in provider.company_reviews or []:
        if not isinstance(row, dict):
            continue
        text = (row.get("text") or "").strip()
        if not text:
            continue
        reviews.append(
            {
                "author_name": row.get("author_name"),
                "rating": row.get("rating"),
                "text": text,
                "relative_time": row.get("relative_time"),
            }
        )
    return {
        "company_name": provider.company_name,
        "company_website": provider.company_website,
        "company_about": provider.company_about,
        "company_size": provider.company_size,
        "company_address": provider.company_address,
        "company_location": provider.company_location,
        "company_rating": provider.company_rating,
        "company_review_count": provider.company_review_count,
        "company_reviews": reviews,
        "company_rating_source": provider.company_rating_source,
        "google_maps_url": provider.google_maps_url,
        "company_logo_url": provider.profile_pic_url,
        "company_gallery": gallery,
    }


async def load_gallery(db: AsyncSession, provider_id: str) -> list[CompanyGalleryImage]:
    result = await db.execute(
        select(CompanyGalleryImage)
        .where(CompanyGalleryImage.provider_id == provider_id)
        .order_by(CompanyGalleryImage.sort_order.asc(), CompanyGalleryImage.created_at.asc())
    )
    return list(result.scalars().all())


async def get_company_profile(user: User, db: AsyncSession) -> CompanyProfileOut:
    gallery = await load_gallery(db, user.id)
    return serialize_company_profile(user, gallery)


def _merge_preview(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = {**base}
    for key, value in extra.items():
        if value in (None, "", [], {}):
            continue
        if key == "company_reviews" and merged.get("company_reviews"):
            continue
        if key == "photo_references" and merged.get("photo_references"):
            continue
        if not merged.get(key):
            merged[key] = value
    return merged


async def lookup_company(body: CompanyLookupRequest) -> CompanyLookupResponse:
    if not body.website and not body.query and not body.place_id:
        raise HTTPException(status_code=400, detail="Enter a website, company name, or Google Place")

    website_preview: dict[str, Any] = {}
    if body.website:
        website_preview = await fetch_website_preview(body.website)

    places = await lookup_places(website=body.website, query=body.query, place_id=body.place_id)
    google_preview = places.get("preview") or {}
    candidates = [CompanyPlaceCandidate.model_validate(c) for c in (places.get("candidates") or []) if c.get("place_id")]

    if google_preview:
        preview_data = _merge_preview(google_preview, website_preview)
        source = "google"
        message = "Company details loaded from Google Places. Review and save, or pick another match."
        if places.get("error"):
            message = f"Google Places had an issue ({places['error']}). Website details were used instead." if website_preview else f"Google Places lookup failed: {places['error']}"
            if website_preview and not google_preview.get("company_name"):
                source = "website"
    elif website_preview:
        preview_data = website_preview
        source = "website"
        if places.get("enabled"):
            message = "No Google Place matched. Website details were filled — complete the rest manually."
        else:
            message = "Google Places key is not configured. Website details were filled — complete the rest manually."
    else:
        preview_data = {"company_website": body.website}
        source = "manual"
        if not places.get("enabled"):
            message = "Google Places key is not configured. Fill company details manually."
        elif places.get("error"):
            message = f"Could not auto-fill ({places['error']}). Fill company details manually."
        else:
            message = "No company details found. Fill them manually."

    if body.website and not preview_data.get("company_website"):
        preview_data["company_website"] = body.website

    return CompanyLookupResponse(
        places_enabled=bool(places.get("enabled")),
        source=source,
        message=message,
        preview=CompanyLookupPreview.model_validate(preview_data),
        candidates=candidates,
    )


async def update_company_profile(
    user: User,
    body: CompanyProfileUpdateRequest,
    db: AsyncSession,
) -> CompanyProfileOut:
    if body.company_name is not None:
        user.company_name = body.company_name.strip() or user.company_name
    if body.company_website is not None:
        user.company_website = body.company_website
    if body.company_about is not None:
        user.company_about = body.company_about
    if body.company_address is not None:
        user.company_address = body.company_address.strip() or None
    if body.company_location is not None:
        user.company_location = body.company_location.strip() or None
    if body.company_rating is not None:
        user.company_rating = body.company_rating
        if not user.company_rating_source:
            user.company_rating_source = "manual"
    if body.company_review_count is not None:
        user.company_review_count = body.company_review_count
    if body.company_reviews is not None:
        user.company_reviews = [item.model_dump() for item in body.company_reviews]
    if body.company_rating_source is not None:
        user.company_rating_source = body.company_rating_source
    if body.google_place_id is not None:
        user.google_place_id = body.google_place_id or None
    if body.google_maps_url is not None:
        user.google_maps_url = body.google_maps_url or None

    await db.commit()
    await db.refresh(user)
    gallery = await load_gallery(db, user.id)
    return serialize_company_profile(user, gallery)


async def apply_lookup(
    user: User,
    body: CompanyApplyLookupRequest,
    db: AsyncSession,
) -> CompanyProfileOut:
    lookup = await lookup_company(
        CompanyLookupRequest(website=body.website, query=body.query, place_id=body.place_id)
    )
    preview = lookup.preview
    if preview.company_name:
        user.company_name = preview.company_name
    if preview.company_website:
        user.company_website = preview.company_website
    if preview.company_about:
        user.company_about = preview.company_about
    if preview.company_address:
        user.company_address = preview.company_address
    if preview.company_location:
        user.company_location = preview.company_location
    if preview.company_rating is not None:
        user.company_rating = preview.company_rating
    if preview.company_review_count is not None:
        user.company_review_count = preview.company_review_count
    if preview.company_reviews:
        user.company_reviews = [item.model_dump() for item in preview.company_reviews]
    if preview.company_rating_source:
        user.company_rating_source = preview.company_rating_source
    if preview.google_place_id:
        user.google_place_id = preview.google_place_id
    if preview.google_maps_url:
        user.google_maps_url = preview.google_maps_url

    await db.commit()
    await db.refresh(user)

    if body.import_photos and preview.photo_references and places_enabled():
        await _import_google_photos(user, db, preview.photo_references)

    gallery = await load_gallery(db, user.id)
    return serialize_company_profile(user, gallery)


async def _import_google_photos(user: User, db: AsyncSession, refs: list[str]) -> None:
    existing = await load_gallery(db, user.id)
    remaining = MAX_GALLERY_IMAGES - len(existing)
    if remaining <= 0:
        return
    gallery_dir = get_upload_dir() / "company_gallery" / str(user.id)
    gallery_dir.mkdir(parents=True, exist_ok=True)
    next_order = (existing[-1].sort_order + 1) if existing else 0
    for ref in refs[:remaining]:
        try:
            content = await download_place_photo(ref)
        except Exception:
            continue
        filename = f"{uuid.uuid4().hex}.jpg"
        path = gallery_dir / filename
        path.write_bytes(content)
        db.add(
            CompanyGalleryImage(
                provider_id=user.id,
                image_url=f"/uploads/company_gallery/{user.id}/{filename}",
                sort_order=next_order,
                source="google",
            )
        )
        next_order += 1
    await db.commit()


async def upload_gallery_image(
    user: User,
    file: UploadFile,
    db: AsyncSession,
    caption: Optional[str] = None,
) -> CompanyProfileOut:
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG, WEBP, or GIF image")
    existing = await load_gallery(db, user.id)
    if len(existing) >= MAX_GALLERY_IMAGES:
        raise HTTPException(status_code=400, detail=f"You can upload up to {MAX_GALLERY_IMAGES} gallery images")

    content = await file.read()
    if len(content) > MAX_GALLERY_BYTES:
        raise HTTPException(status_code=400, detail="Each image must be 5 MB or smaller")

    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    gallery_dir = get_upload_dir() / "company_gallery" / str(user.id)
    gallery_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    (gallery_dir / filename).write_bytes(content)

    next_order = (existing[-1].sort_order + 1) if existing else 0
    db.add(
        CompanyGalleryImage(
            provider_id=user.id,
            image_url=f"/uploads/company_gallery/{user.id}/{filename}",
            caption=(caption or "").strip()[:200] or None,
            sort_order=next_order,
            source="upload",
        )
    )
    await db.commit()
    gallery = await load_gallery(db, user.id)
    return serialize_company_profile(user, gallery)


async def delete_gallery_image(user: User, image_id: str, db: AsyncSession) -> CompanyProfileOut:
    result = await db.execute(
        select(CompanyGalleryImage).where(
            CompanyGalleryImage.id == image_id,
            CompanyGalleryImage.provider_id == user.id,
        )
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    rel = image.image_url or ""
    if rel.startswith("/uploads/"):
        disk = get_upload_dir() / rel.replace("/uploads/", "", 1)
        try:
            if disk.is_file():
                disk.unlink()
        except OSError:
            pass
    await db.delete(image)
    await db.commit()
    gallery = await load_gallery(db, user.id)
    return serialize_company_profile(user, gallery)
