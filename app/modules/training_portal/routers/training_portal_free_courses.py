import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import require_super_admin, require_training_portal_user
from app.modules.training_portal.models.training_portal_free_course import (
    TrainingPortalFreeCourse,
    TrainingPortalFreeCourseLesson,
)
from app.modules.training_portal.schemas.training_portal_free_course import (
    FreeCourseImportIn,
    FreeCourseListItemOut,
    FreeCourseOut,
    FreeCourseUpdateIn,
)
from app.modules.training_portal.services.youtube_playlist_service import (
    PlaylistImport,
    YouTubeImportError,
    fetch_playlist,
)
from app.shared.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training-portal/free-courses", tags=["Training Portal Free Courses"])


def _lesson_models(course_id: str, imported: PlaylistImport) -> list[TrainingPortalFreeCourseLesson]:
    now = datetime.utcnow()
    return [
        TrainingPortalFreeCourseLesson(
            id=str(uuid.uuid4()),
            course_id=course_id,
            youtube_video_id=video.video_id,
            youtube_url=video.youtube_url,
            title=video.title[:300],
            description=video.description or None,
            thumbnail_url=video.thumbnail_url,
            duration_seconds=video.duration_seconds,
            sort_order=video.sort_order,
            created_at=now,
        )
        for video in imported.videos
    ]


def _to_out(course: TrainingPortalFreeCourse, *, include_lessons: bool) -> FreeCourseOut:
    lessons = list(course.lessons or [])
    return FreeCourseOut(
        id=course.id,
        title=course.title,
        description=course.description,
        youtube_url=course.youtube_url,
        playlist_id=course.playlist_id,
        thumbnail_url=course.thumbnail_url,
        channel_title=course.channel_title,
        status=course.status,  # type: ignore[arg-type]
        lesson_count=len(lessons),
        lessons=lessons if include_lessons else [],
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


def _to_list_item(course: TrainingPortalFreeCourse, lesson_count: int) -> FreeCourseListItemOut:
    return FreeCourseListItemOut(
        id=course.id,
        title=course.title,
        description=course.description,
        youtube_url=course.youtube_url,
        playlist_id=course.playlist_id,
        thumbnail_url=course.thumbnail_url,
        channel_title=course.channel_title,
        status=course.status,  # type: ignore[arg-type]
        lesson_count=lesson_count,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


async def _get_course(db: AsyncSession, course_id: str) -> TrainingPortalFreeCourse:
    result = await db.execute(
        select(TrainingPortalFreeCourse)
        .options(selectinload(TrainingPortalFreeCourse.lessons))
        .where(TrainingPortalFreeCourse.id == course_id)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Free course not found")
    return course


async def _replace_lessons(db: AsyncSession, course: TrainingPortalFreeCourse, imported: PlaylistImport) -> None:
    existing = await db.execute(
        select(TrainingPortalFreeCourseLesson).where(TrainingPortalFreeCourseLesson.course_id == course.id)
    )
    for lesson in existing.scalars().all():
        await db.delete(lesson)
    await db.flush()
    db.add_all(_lesson_models(course.id, imported))


@router.get("/public", response_model=List[FreeCourseListItemOut])
async def list_public_free_courses(
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(TrainingPortalFreeCourse).where(TrainingPortalFreeCourse.status == "published")
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                TrainingPortalFreeCourse.title.ilike(term),
                TrainingPortalFreeCourse.description.ilike(term),
                TrainingPortalFreeCourse.channel_title.ilike(term),
            )
        )
    query = query.order_by(TrainingPortalFreeCourse.created_at.desc())
    result = await db.execute(query)
    courses = list(result.scalars().all())
    counts = await _lesson_counts(db, [c.id for c in courses])
    return [_to_list_item(course, counts.get(course.id, 0)) for course in courses]


@router.get("/public/{course_id}", response_model=FreeCourseOut)
async def get_public_free_course(course_id: str, db: AsyncSession = Depends(get_db)):
    course = await _get_course(db, course_id)
    if course.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Free course not found")
    return _to_out(course, include_lessons=True)


@router.get("/", response_model=List[FreeCourseListItemOut])
async def list_free_courses(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(TrainingPortalFreeCourse)
    is_super_admin = (
        getattr(current_user, "is_super_admin", False)
        or (hasattr(current_user.role, "value") and current_user.role.value == "superadmin")
        or (str(current_user.role or "") == "superadmin")
    )
    if not is_super_admin:
        query = query.where(TrainingPortalFreeCourse.status == "published")
    elif status_filter and status_filter.strip() and status_filter.strip().lower() != "all":
        query = query.where(TrainingPortalFreeCourse.status == status_filter.strip())

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                TrainingPortalFreeCourse.title.ilike(term),
                TrainingPortalFreeCourse.description.ilike(term),
                TrainingPortalFreeCourse.channel_title.ilike(term),
            )
        )
    query = query.order_by(TrainingPortalFreeCourse.created_at.desc())
    result = await db.execute(query)
    courses = list(result.scalars().all())
    counts = await _lesson_counts(db, [c.id for c in courses])
    return [_to_list_item(course, counts.get(course.id, 0)) for course in courses]


@router.post("/import", response_model=FreeCourseOut, status_code=status.HTTP_201_CREATED)
async def import_free_course(
    body: FreeCourseImportIn,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    youtube_url = body.youtube_url.strip()
    try:
        imported = await fetch_playlist(youtube_url)
    except YouTubeImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception:
        logger.exception("Free course playlist import failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch videos from YouTube. Please try again.",
        )

    if imported.playlist_id:
        existing = await db.execute(
            select(TrainingPortalFreeCourse).where(TrainingPortalFreeCourse.playlist_id == imported.playlist_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This playlist is already imported. Open it and use Re-sync to refresh videos.",
            )

    now = datetime.utcnow()
    custom_title = (body.title or "").strip()
    course = TrainingPortalFreeCourse(
        id=str(uuid.uuid4()),
        created_by_id=current_user.id,
        title=(custom_title or imported.title)[:300],
        description=imported.description or None,
        youtube_url=youtube_url,
        playlist_id=imported.playlist_id,
        thumbnail_url=imported.thumbnail_url,
        channel_title=imported.channel_title,
        status="published",
        created_at=now,
        updated_at=now,
    )
    db.add(course)
    await db.flush()
    db.add_all(_lesson_models(course.id, imported))
    await db.commit()
    return _to_out(await _get_course(db, course.id), include_lessons=True)


@router.get("/{course_id}", response_model=FreeCourseOut)
async def get_free_course(
    course_id: str,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_course(db, course_id)
    is_super_admin = (
        getattr(current_user, "is_super_admin", False)
        or (hasattr(current_user.role, "value") and current_user.role.value == "superadmin")
        or (str(current_user.role or "") == "superadmin")
    )
    if course.status != "published" and not is_super_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Free course not found")
    return _to_out(course, include_lessons=True)


@router.put("/{course_id}", response_model=FreeCourseOut)
async def update_free_course(
    course_id: str,
    body: FreeCourseUpdateIn,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_course(db, course_id)
    data = body.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        data["title"] = data["title"].strip()
    for field, value in data.items():
        setattr(course, field, value)
    course.updated_at = datetime.utcnow()
    await db.commit()
    return _to_out(await _get_course(db, course.id), include_lessons=True)


@router.post("/{course_id}/resync", response_model=FreeCourseOut)
async def resync_free_course(
    course_id: str,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_course(db, course_id)
    try:
        imported = await fetch_playlist(course.youtube_url)
    except YouTubeImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await _replace_lessons(db, course, imported)
    if imported.playlist_id:
        course.playlist_id = imported.playlist_id
    if imported.thumbnail_url:
        course.thumbnail_url = imported.thumbnail_url
    if imported.channel_title:
        course.channel_title = imported.channel_title
    if imported.description and not course.description:
        course.description = imported.description
    course.updated_at = datetime.utcnow()
    await db.commit()
    return _to_out(await _get_course(db, course.id), include_lessons=True)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_free_course(
    course_id: str,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_course(db, course_id)
    await db.delete(course)
    await db.commit()
    return None


async def _lesson_counts(db: AsyncSession, course_ids: list[str]) -> dict[str, int]:
    if not course_ids:
        return {}
    rows = await db.execute(
        select(TrainingPortalFreeCourseLesson.course_id, func.count())
        .where(TrainingPortalFreeCourseLesson.course_id.in_(course_ids))
        .group_by(TrainingPortalFreeCourseLesson.course_id)
    )
    return {row[0]: int(row[1]) for row in rows.all()}
