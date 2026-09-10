import logging
import uuid
from datetime import datetime
from typing import List, Optional

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import and_, exists, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_upload_dir
from app.core.database import get_db
from app.core.dependencies import require_training_portal_user, require_super_admin_or_permission
from app.modules.training_portal.models.training_portal_free_course import (
    TrainingPortalFreeCourse,
    TrainingPortalFreeCourseLesson,
    TrainingPortalFreeCourseResource,
)
from app.modules.training_portal.schemas.training_portal_free_course import (
    FreeCourseImportIn,
    FreeCourseLessonImportIn,
    FreeCourseListItemOut,
    FreeCourseOut,
    FreeCourseResourceCreateIn,
    FreeCourseResourcePreviewIn,
    FreeCourseResourcePreviewOut,
    FreeCourseResourceUpdateIn,
    FreeCourseUpdateIn,
    PublicFreeCourseListOut,
)
from app.modules.training_portal.services.url_metadata_service import (
    UrlMetadataError,
    fetch_url_metadata,
    is_hosted_upload_url,
    is_pdf_url,
    pdf_metadata_from_url,
    resolve_resource_category,
)
from app.modules.training_portal.services.youtube_playlist_service import (
    PlaylistImport,
    YouTubeImportError,
    fetch_playlist,
    parse_youtube_ids,
)
from app.shared.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training-portal/free-courses", tags=["Training Portal Free Courses"])


def _lesson_models(course_id: str, imported: PlaylistImport, *, start_order: int = 0) -> list[TrainingPortalFreeCourseLesson]:
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
            sort_order=start_order + video.sort_order,
            created_at=now,
        )
        for video in imported.videos
    ]


def _to_out(course: TrainingPortalFreeCourse, *, include_lessons: bool, include_resources: bool = True) -> FreeCourseOut:
    lessons = list(course.lessons or [])
    resources = list(course.resources or [])
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
        resource_count=len(resources),
        lessons=lessons if include_lessons else [],
        resources=resources if include_resources else [],
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


def _to_list_item(
    course: TrainingPortalFreeCourse,
    lesson_count: int,
    resource_count: int,
    *,
    youtube_video_id: Optional[str] = None,
    resource_category: Optional[str] = None,
    resource_metadata: Optional[dict] = None,
) -> FreeCourseListItemOut:
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
        resource_count=resource_count,
        youtube_video_id=youtube_video_id,
        resource_category=resource_category,  # type: ignore[arg-type]
        resource_metadata=resource_metadata,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


async def _get_course(
    db: AsyncSession,
    course_id: str,
    *,
    with_lessons: bool = True,
    with_resources: bool = True,
) -> TrainingPortalFreeCourse:
    options = []
    if with_lessons:
        options.append(selectinload(TrainingPortalFreeCourse.lessons))
    if with_resources:
        options.append(selectinload(TrainingPortalFreeCourse.resources))
    result = await db.execute(
        select(TrainingPortalFreeCourse).options(*options).where(TrainingPortalFreeCourse.id == course_id)
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


async def _next_lesson_order(db: AsyncSession, course_id: str) -> int:
    result = await db.execute(
        select(func.max(TrainingPortalFreeCourseLesson.sort_order)).where(
            TrainingPortalFreeCourseLesson.course_id == course_id
        )
    )
    current = result.scalar()
    return int(current or -1) + 1


async def _next_resource_order(db: AsyncSession, course_id: str, category: str) -> int:
    result = await db.execute(
        select(func.max(TrainingPortalFreeCourseResource.sort_order)).where(
            TrainingPortalFreeCourseResource.course_id == course_id,
            TrainingPortalFreeCourseResource.category == category,
        )
    )
    current = result.scalar()
    return int(current or -1) + 1


async def _lesson_counts(db: AsyncSession, course_ids: list[str]) -> dict[str, int]:
    if not course_ids:
        return {}
    rows = await db.execute(
        select(TrainingPortalFreeCourseLesson.course_id, func.count())
        .where(TrainingPortalFreeCourseLesson.course_id.in_(course_ids))
        .group_by(TrainingPortalFreeCourseLesson.course_id)
    )
    return {row[0]: int(row[1]) for row in rows.all()}


async def _resource_counts(db: AsyncSession, course_ids: list[str]) -> dict[str, int]:
    if not course_ids:
        return {}
    rows = await db.execute(
        select(TrainingPortalFreeCourseResource.course_id, func.count())
        .where(TrainingPortalFreeCourseResource.course_id.in_(course_ids))
        .group_by(TrainingPortalFreeCourseResource.course_id)
    )
    return {row[0]: int(row[1]) for row in rows.all()}


async def _first_lesson_video_ids(db: AsyncSession, course_ids: list[str]) -> dict[str, str]:
    if not course_ids:
        return {}
    rows = await db.execute(
        select(
            TrainingPortalFreeCourseLesson.course_id,
            TrainingPortalFreeCourseLesson.youtube_video_id,
        )
        .where(TrainingPortalFreeCourseLesson.course_id.in_(course_ids))
        .order_by(
            TrainingPortalFreeCourseLesson.course_id,
            TrainingPortalFreeCourseLesson.sort_order,
        )
    )
    first: dict[str, str] = {}
    for course_id, video_id in rows.all():
        if course_id not in first:
            first[course_id] = video_id
    return first


async def _first_resources(
    db: AsyncSession, course_ids: list[str]
) -> dict[str, TrainingPortalFreeCourseResource]:
    if not course_ids:
        return {}
    rows = await db.execute(
        select(TrainingPortalFreeCourseResource)
        .where(TrainingPortalFreeCourseResource.course_id.in_(course_ids))
        .order_by(
            TrainingPortalFreeCourseResource.course_id,
            TrainingPortalFreeCourseResource.sort_order,
        )
    )
    first: dict[str, TrainingPortalFreeCourseResource] = {}
    for resource in rows.scalars().all():
        if resource.course_id not in first:
            first[resource.course_id] = resource
    return first


def _list_items_for_courses(
    courses: list[TrainingPortalFreeCourse],
    counts: dict[str, int],
    resource_counts: dict[str, int],
    video_ids: dict[str, str],
    resources: dict[str, TrainingPortalFreeCourseResource],
) -> list[FreeCourseListItemOut]:
    items = []
    for course in courses:
        resource = resources.get(course.id)
        items.append(
            _to_list_item(
                course,
                counts.get(course.id, 0),
                resource_counts.get(course.id, 0),
                youtube_video_id=video_ids.get(course.id),
                resource_category=resource.category if resource else None,
                resource_metadata=resource.metadata_json if resource else None,
            )
        )
    return items


FREE_COURSE_SOURCE_KEYS = (
    "youtube",
    "github_repo",
    "book",
    "research_paper",
    "course",
    "guide",
    "pdf",
)

_SOURCE_ALIASES = {
    "github": "github_repo",
    "git": "github_repo",
    "paper": "research_paper",
    "papers": "research_paper",
    "video": "youtube",
    "videos": "youtube",
    "pdfs": "pdf",
}


def _parse_source_keys(source: Optional[str]) -> list[str]:
    if not source:
        return []
    keys: list[str] = []
    for part in source.split(","):
        raw = part.strip().lower()
        if not raw or raw == "all":
            continue
        key = _SOURCE_ALIASES.get(raw, raw)
        if key not in keys:
            keys.append(key)
    return keys


def _has_resource_category(*categories: str):
    return exists(
        select(TrainingPortalFreeCourseResource.id).where(
            TrainingPortalFreeCourseResource.course_id == TrainingPortalFreeCourse.id,
            TrainingPortalFreeCourseResource.category.in_(categories),
        )
    )


def _has_any_resource():
    return exists(
        select(TrainingPortalFreeCourseResource.id).where(
            TrainingPortalFreeCourseResource.course_id == TrainingPortalFreeCourse.id,
        )
    )


def _has_lessons():
    return exists(
        select(TrainingPortalFreeCourseLesson.id).where(
            TrainingPortalFreeCourseLesson.course_id == TrainingPortalFreeCourse.id,
        )
    )


def _source_clause(source_key: str):
    url_col = TrainingPortalFreeCourse.youtube_url
    is_pdf = or_(
        _has_resource_category("pdf"),
        url_col.ilike("%.pdf%"),
        url_col.ilike("%training_portal_free_course_files%"),
    )
    if source_key == "pdf":
        return is_pdf

    no_pdf = ~is_pdf
    categorized = _has_any_resource()
    url_only = and_(no_pdf, ~categorized)

    if source_key == "youtube":
        return and_(
            no_pdf,
            or_(
                _has_resource_category("video"),
                and_(
                    ~categorized,
                    or_(
                        TrainingPortalFreeCourse.playlist_id.isnot(None),
                        _has_lessons(),
                        url_col.ilike("%youtube.com%"),
                        url_col.ilike("%youtu.be%"),
                    ),
                ),
            ),
        )
    if source_key == "github_repo":
        return or_(
            and_(no_pdf, _has_resource_category("github_repo")),
            and_(url_only, url_col.ilike("%github.com%")),
        )
    if source_key == "research_paper":
        return or_(
            and_(no_pdf, _has_resource_category("research_paper")),
            and_(url_only, url_col.ilike("%arxiv.org%")),
        )
    if source_key == "course":
        return or_(
            and_(no_pdf, _has_resource_category("course")),
            and_(url_only, url_col.ilike("%huggingface.co%")),
        )
    if source_key == "book":
        return or_(
            and_(no_pdf, _has_resource_category("book")),
            and_(
                url_only,
                or_(
                    url_col.ilike("%manning.com%"),
                    url_col.ilike("%oreilly.com%"),
                    url_col.ilike("%github.io%"),
                ),
            ),
        )
    if source_key == "guide":
        known_url = or_(
            url_col.ilike("%youtube.com%"),
            url_col.ilike("%youtu.be%"),
            url_col.ilike("%github.com%"),
            url_col.ilike("%arxiv.org%"),
            url_col.ilike("%huggingface.co%"),
            url_col.ilike("%manning.com%"),
            url_col.ilike("%oreilly.com%"),
            url_col.ilike("%github.io%"),
        )
        return or_(
            and_(no_pdf, _has_resource_category("guide")),
            and_(url_only, ~known_url),
        )
    return None


def _apply_free_course_filters(
    query,
    *,
    search: Optional[str],
    status_filter: Optional[str] = None,
    source: Optional[str] = None,
    published_only: bool = False,
):
    if published_only:
        query = query.where(TrainingPortalFreeCourse.status == "published")
    elif status_filter and status_filter.strip() and status_filter.strip().lower() != "all":
        query = query.where(TrainingPortalFreeCourse.status == status_filter.strip())

    if search and search.strip():
        term = f"%{search.strip()}%"
        resource_match = exists(
            select(TrainingPortalFreeCourseResource.id).where(
                TrainingPortalFreeCourseResource.course_id == TrainingPortalFreeCourse.id,
                or_(
                    TrainingPortalFreeCourseResource.title.ilike(term),
                    TrainingPortalFreeCourseResource.url.ilike(term),
                ),
            )
        )
        query = query.where(
            or_(
                TrainingPortalFreeCourse.title.ilike(term),
                TrainingPortalFreeCourse.description.ilike(term),
                TrainingPortalFreeCourse.channel_title.ilike(term),
                TrainingPortalFreeCourse.youtube_url.ilike(term),
                resource_match,
            )
        )

    source_keys = _parse_source_keys(source)
    clauses = [clause for key in source_keys if (clause := _source_clause(key)) is not None]
    if clauses:
        query = query.where(or_(*clauses))
    return query


async def _query_count(db: AsyncSession, query) -> int:
    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    result = await db.execute(count_stmt)
    return int(result.scalar() or 0)


@router.get("/public", response_model=PublicFreeCourseListOut)
async def list_public_free_courses(
    search: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100, alias="limit"),
    db: AsyncSession = Depends(get_db),
):
    base_query = _apply_free_course_filters(
        select(TrainingPortalFreeCourse), search=search, published_only=True
    )
    filtered_query = _apply_free_course_filters(
        select(TrainingPortalFreeCourse), search=search, source=source, published_only=True
    )
    total_published = await _query_count(db, base_query)
    total = await _query_count(db, filtered_query)
    source_counts: dict[str, int] = {}
    for key in FREE_COURSE_SOURCE_KEYS:
        source_counts[key] = await _query_count(
            db,
            _apply_free_course_filters(
                select(TrainingPortalFreeCourse), search=search, source=key, published_only=True
            ),
        )

    offset = (page - 1) * page_size
    result = await db.execute(
        filtered_query.order_by(TrainingPortalFreeCourse.created_at.desc()).offset(offset).limit(page_size)
    )
    courses = list(result.scalars().all())
    course_ids = [c.id for c in courses]
    counts = await _lesson_counts(db, course_ids)
    resource_counts = await _resource_counts(db, course_ids)
    video_ids = await _first_lesson_video_ids(db, course_ids)
    resources = await _first_resources(db, course_ids)
    items = _list_items_for_courses(courses, counts, resource_counts, video_ids, resources)
    return PublicFreeCourseListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(items)) < total,
        source_counts=source_counts,
        total_published=total_published,
    )


@router.get("/public/{course_id}", response_model=FreeCourseOut)
async def get_public_free_course(course_id: str, db: AsyncSession = Depends(get_db)):
    course = await _get_course(db, course_id)
    if course.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Free course not found")
    return _to_out(course, include_lessons=True, include_resources=True)


@router.post("/resources/preview", response_model=FreeCourseResourcePreviewOut)
async def preview_free_course_resource(
    body: FreeCourseResourcePreviewIn,
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
):
    try:
        meta = await fetch_url_metadata(body.url, body.category)
    except UrlMetadataError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception:
        logger.exception("Resource preview failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch metadata from that URL.",
        )
    return FreeCourseResourcePreviewOut(
        url=meta.url,
        title=meta.title,
        description=meta.description or None,
        thumbnail_url=meta.thumbnail_url,
        category=meta.category,  # type: ignore[arg-type]
        is_youtube=meta.is_youtube,
        youtube_video_id=meta.youtube_video_id,
        metadata=meta.metadata,
    )


@router.get("/", response_model=List[FreeCourseListItemOut])
async def list_free_courses(
    response: Response,
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    source: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100, alias="limit"),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(TrainingPortalFreeCourse)
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role or "")
    is_admin = getattr(current_user, "is_super_admin", False) or role_val in ("superadmin", "supervisor")
    query = _apply_free_course_filters(
        query,
        search=search,
        status_filter=status_filter if is_admin else "published",
        source=source,
        published_only=not is_admin,
    )
    query = query.order_by(TrainingPortalFreeCourse.created_at.desc())

    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total_result = await db.execute(count_stmt)
    total_count = total_result.scalar() or 0
    response.headers["X-Total-Count"] = str(total_count)

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    courses = list(result.scalars().all())
    course_ids = [c.id for c in courses]
    counts = await _lesson_counts(db, course_ids)
    resource_counts = await _resource_counts(db, course_ids)
    video_ids = await _first_lesson_video_ids(db, course_ids)
    resources = await _first_resources(db, course_ids)
    return _list_items_for_courses(courses, counts, resource_counts, video_ids, resources)


MAX_FREE_COURSE_PDF_BYTES = 25 * 1024 * 1024


@router.post("/upload-file")
async def upload_free_course_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
):
    original = Path(file.filename or "document.pdf").name
    if Path(original).suffix.lower() != ".pdf":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")
    if len(content) > MAX_FREE_COURSE_PDF_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF must be 25 MB or smaller.")

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed.")

    base_dir = get_upload_dir()
    file_dir = base_dir / "training_portal_free_course_files"
    file_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}.pdf"
    dest = file_dir / safe_name
    dest.write_bytes(content)
    return {
        "url": f"/uploads/training_portal_free_course_files/{safe_name}",
        "filename": original,
    }


@router.post("/import", response_model=FreeCourseOut, status_code=status.HTTP_201_CREATED)
async def import_free_course(
    body: FreeCourseImportIn,
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
    db: AsyncSession = Depends(get_db),
):
    source = (body.source or "youtube").strip().lower()
    source_url = (body.url or body.youtube_url or "").strip()
    if not source_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please paste a URL.")
    custom_title = (body.title or "").strip()

    if source == "youtube":
        try:
            imported = await fetch_playlist(source_url)
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
        course = TrainingPortalFreeCourse(
            id=str(uuid.uuid4()),
            created_by_id=current_user.id,
            title=(custom_title or imported.title)[:300],
            description=imported.description or None,
            youtube_url=source_url,
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

    if source == "pdf" or is_hosted_upload_url(source_url) or (source != "youtube" and is_pdf_url(source_url)):
        if is_hosted_upload_url(source_url):
            meta = pdf_metadata_from_url(source_url, title=custom_title or None)
        else:
            try:
                meta = await fetch_url_metadata(source_url, "pdf")
            except UrlMetadataError:
                meta = pdf_metadata_from_url(source_url, title=custom_title or None)
        if meta.is_youtube:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This is a YouTube link. Select YouTube as the source.",
            )
        if custom_title:
            meta.title = custom_title[:300]
        saved_category = "pdf"
        now = datetime.utcnow()
        course = TrainingPortalFreeCourse(
            id=str(uuid.uuid4()),
            created_by_id=current_user.id,
            title=meta.title[:300],
            description=meta.description or None,
            youtube_url=meta.url[:500],
            playlist_id=None,
            thumbnail_url=meta.thumbnail_url,
            channel_title=None,
            status="published",
            created_at=now,
            updated_at=now,
        )
        db.add(course)
        await db.flush()
        db.add(
            TrainingPortalFreeCourseResource(
                id=str(uuid.uuid4()),
                course_id=course.id,
                category=saved_category,
                url=meta.url[:700],
                title=meta.title[:300],
                description=meta.description or None,
                thumbnail_url=meta.thumbnail_url,
                metadata_json=meta.metadata or None,
                sort_order=0,
                created_at=now,
            )
        )
        await db.commit()
        return _to_out(await _get_course(db, course.id), include_lessons=True)

    try:
        meta = await fetch_url_metadata(source_url, source)
    except UrlMetadataError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if meta.is_youtube:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is a YouTube link. Select YouTube as the source.",
        )

    try:
        saved_category = resolve_resource_category(source, meta.category)
    except UrlMetadataError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    now = datetime.utcnow()
    course = TrainingPortalFreeCourse(
        id=str(uuid.uuid4()),
        created_by_id=current_user.id,
        title=(custom_title or meta.title)[:300],
        description=meta.description or None,
        youtube_url=meta.url[:500],
        playlist_id=None,
        thumbnail_url=meta.thumbnail_url,
        channel_title=None,
        status="published",
        created_at=now,
        updated_at=now,
    )
    db.add(course)
    await db.flush()
    db.add(
        TrainingPortalFreeCourseResource(
            id=str(uuid.uuid4()),
            course_id=course.id,
            category=saved_category,
            url=meta.url[:700],
            title=(custom_title or meta.title)[:300],
            description=meta.description or None,
            thumbnail_url=meta.thumbnail_url,
            metadata_json=meta.metadata or None,
            sort_order=0,
            created_at=now,
        )
    )
    await db.commit()
    return _to_out(await _get_course(db, course.id), include_lessons=True)


@router.get("/{course_id}", response_model=FreeCourseOut)
async def get_free_course(
    course_id: str,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_course(db, course_id)
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role or "")
    is_admin = getattr(current_user, "is_super_admin", False) or role_val in ("superadmin", "supervisor")
    if course.status != "published" and not is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Free course not found")
    return _to_out(course, include_lessons=True)


@router.put("/{course_id}", response_model=FreeCourseOut)
async def update_free_course(
    course_id: str,
    body: FreeCourseUpdateIn,
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
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
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_course(db, course_id, with_resources=False)
    if not course.playlist_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Re-sync is only available for playlist-based courses.",
        )
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


@router.post("/{course_id}/lessons/import", response_model=FreeCourseOut)
async def import_free_course_lesson(
    course_id: str,
    body: FreeCourseLessonImportIn,
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_course(db, course_id, with_resources=False)
    youtube_url = body.youtube_url.strip()
    playlist_id, video_id = parse_youtube_ids(youtube_url)
    if not video_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please paste a single YouTube video link.")
    if playlist_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the main Import screen for playlists. Paste a single video link here.",
        )

    try:
        imported = await fetch_playlist(youtube_url)
    except YouTubeImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if len(imported.videos) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one video can be added at a time. Use Import for playlists.",
        )

    video = imported.videos[0]
    existing = await db.execute(
        select(TrainingPortalFreeCourseLesson).where(
            TrainingPortalFreeCourseLesson.course_id == course.id,
            TrainingPortalFreeCourseLesson.youtube_video_id == video.video_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This video is already in the course.")

    custom_title = (body.title or "").strip()
    start_order = await _next_lesson_order(db, course.id)
    now = datetime.utcnow()
    lesson = TrainingPortalFreeCourseLesson(
        id=str(uuid.uuid4()),
        course_id=course.id,
        youtube_video_id=video.video_id,
        youtube_url=video.youtube_url,
        title=(custom_title or video.title)[:300],
        description=video.description or None,
        thumbnail_url=video.thumbnail_url,
        duration_seconds=video.duration_seconds,
        sort_order=start_order,
        created_at=now,
    )
    db.add(lesson)
    course.updated_at = datetime.utcnow()
    await db.commit()
    return _to_out(await _get_course(db, course.id), include_lessons=True)


@router.post("/{course_id}/resources", response_model=FreeCourseOut, status_code=status.HTTP_201_CREATED)
async def add_free_course_resource(
    course_id: str,
    body: FreeCourseResourceCreateIn,
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_course(db, course_id, with_lessons=False)
    requested = (body.category or "").strip().lower()
    if requested == "pdf" or is_hosted_upload_url(body.url) or is_pdf_url(body.url):
        if is_hosted_upload_url(body.url):
            meta = pdf_metadata_from_url(body.url, title=(body.title or "").strip() or None)
        else:
            try:
                meta = await fetch_url_metadata(body.url, "pdf")
            except UrlMetadataError:
                meta = pdf_metadata_from_url(body.url, title=(body.title or "").strip() or None)
        saved_category = "pdf"
        custom_title = (body.title or "").strip()
        sort_order = await _next_resource_order(db, course.id, saved_category)
        resource = TrainingPortalFreeCourseResource(
            id=str(uuid.uuid4()),
            course_id=course.id,
            category=saved_category,
            url=meta.url[:700],
            title=(custom_title or meta.title)[:300],
            description=(body.description or meta.description or None),
            thumbnail_url=meta.thumbnail_url,
            metadata_json=meta.metadata or None,
            sort_order=sort_order,
            created_at=datetime.utcnow(),
        )
        db.add(resource)
        course.updated_at = datetime.utcnow()
        await db.commit()
        return _to_out(await _get_course(db, course.id), include_lessons=True)

    try:
        meta = await fetch_url_metadata(body.url)
    except UrlMetadataError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if meta.is_youtube:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is a YouTube link. Use Add video in the Videos section.",
        )

    try:
        saved_category = resolve_resource_category(body.category, meta.category)
    except UrlMetadataError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    custom_title = (body.title or "").strip()
    sort_order = await _next_resource_order(db, course.id, saved_category)
    resource = TrainingPortalFreeCourseResource(
        id=str(uuid.uuid4()),
        course_id=course.id,
        category=saved_category,
        url=meta.url[:700],
        title=(custom_title or meta.title)[:300],
        description=(body.description or meta.description or None),
        thumbnail_url=meta.thumbnail_url,
        metadata_json=meta.metadata or None,
        sort_order=sort_order,
        created_at=datetime.utcnow(),
    )
    db.add(resource)
    course.updated_at = datetime.utcnow()
    await db.commit()
    return _to_out(await _get_course(db, course.id), include_lessons=True)


@router.put("/{course_id}/resources/{resource_id}", response_model=FreeCourseOut)
async def update_free_course_resource(
    course_id: str,
    resource_id: str,
    body: FreeCourseResourceUpdateIn,
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
    db: AsyncSession = Depends(get_db),
):
    await _get_course(db, course_id, with_lessons=False)
    result = await db.execute(
        select(TrainingPortalFreeCourseResource).where(
            TrainingPortalFreeCourseResource.id == resource_id,
            TrainingPortalFreeCourseResource.course_id == course_id,
        )
    )
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    data = body.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        data["title"] = data["title"].strip()
    for field, value in data.items():
        setattr(resource, field, value)

    course = await _get_course(db, course_id, with_lessons=False)
    course.updated_at = datetime.utcnow()
    await db.commit()
    return _to_out(await _get_course(db, course_id), include_lessons=True)


@router.delete("/{course_id}/resources/{resource_id}", response_model=FreeCourseOut)
async def delete_free_course_resource(
    course_id: str,
    resource_id: str,
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
    db: AsyncSession = Depends(get_db),
):
    await _get_course(db, course_id, with_lessons=False)
    result = await db.execute(
        select(TrainingPortalFreeCourseResource).where(
            TrainingPortalFreeCourseResource.id == resource_id,
            TrainingPortalFreeCourseResource.course_id == course_id,
        )
    )
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    await db.delete(resource)
    course = await _get_course(db, course_id, with_lessons=False)
    course.updated_at = datetime.utcnow()
    await db.commit()
    return _to_out(await _get_course(db, course_id), include_lessons=True)


@router.delete("/{course_id}/lessons/{lesson_id}", response_model=FreeCourseOut)
async def delete_free_course_lesson(
    course_id: str,
    lesson_id: str,
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
    db: AsyncSession = Depends(get_db),
):
    await _get_course(db, course_id, with_resources=False)
    result = await db.execute(
        select(TrainingPortalFreeCourseLesson).where(
            TrainingPortalFreeCourseLesson.id == lesson_id,
            TrainingPortalFreeCourseLesson.course_id == course_id,
        )
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    await db.delete(lesson)
    course = await _get_course(db, course_id, with_resources=False)
    course.updated_at = datetime.utcnow()
    await db.commit()
    return _to_out(await _get_course(db, course_id), include_lessons=True)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_free_course(
    course_id: str,
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_course(db, course_id, with_lessons=False, with_resources=False)
    await db.delete(course)
    await db.commit()
    return None
