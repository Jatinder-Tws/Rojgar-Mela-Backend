import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Response
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings, get_upload_dir
from app.core.database import get_db
from app.shared.models.user import User
from app.modules.training_portal.models.training_portal_course import TrainingPortalCourse
from app.modules.training_portal.models.training_portal_batch import TrainingPortalBatch
from app.modules.training_portal.models.training_portal_enrollment import TrainingPortalEnrollment
from app.modules.training_portal.schemas.training_portal_course import (
    TrainingPortalCourseCreate,
    TrainingPortalCourseUpdate,
    TrainingPortalCourseOut,
)
from app.core.dependencies import require_super_admin, require_training_portal_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training-portal/courses", tags=["Training Portal Courses"])


@router.post("/thumbnail", response_model=dict)
async def upload_portal_course_thumbnail(
    file: UploadFile = File(...),
    current_user: User = Depends(require_super_admin),
):
    ext = Path(file.filename or "thumbnail").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files (.jpg, .jpeg, .png, .webp) are allowed.",
        )

    base_dir = get_upload_dir()
    if not base_dir.is_absolute():
        base_dir = get_upload_dir()

    thumbnail_dir = base_dir / "training_portal_course_thumbnails"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = thumbnail_dir / safe_name

    content = await file.read()
    with open(file_path, "wb") as output_file:
        output_file.write(content)

    return {"thumbnail_url": f"/uploads/training_portal_course_thumbnails/{safe_name}"}


def _to_out(
    course: TrainingPortalCourse,
    *,
    batches_count: int = 0,
    enrollments_count: int = 0,
) -> TrainingPortalCourseOut:
    return TrainingPortalCourseOut(
        id=course.id,
        title=course.title,
        description=course.description,
        category=course.category,
        duration=course.duration,
        delivery_mode=course.delivery_mode,
        status=course.status,
        skill_level=course.skill_level,
        fee=course.fee,
        emi_fee=course.emi_fee,
        thumbnail_url=course.thumbnail_url,
        prerequisites=course.prerequisites,
        key_highlights=course.key_highlights or [],
        curriculum=course.curriculum or [],
        batches_count=batches_count,
        enrollments_count=enrollments_count,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


async def _course_counts(
    db: AsyncSession, course_ids: list[str]
) -> dict[str, tuple[int, int]]:
    if not course_ids:
        return {}
    batch_rows = await db.execute(
        select(TrainingPortalBatch.course_id, func.count())
        .where(TrainingPortalBatch.course_id.in_(course_ids))
        .group_by(TrainingPortalBatch.course_id)
    )
    batch_map = {row[0]: int(row[1]) for row in batch_rows.all()}
    enroll_rows = await db.execute(
        select(TrainingPortalEnrollment.item_id, func.count())
        .where(
            TrainingPortalEnrollment.enrollment_type == "course",
            TrainingPortalEnrollment.item_id.in_(course_ids),
            TrainingPortalEnrollment.status != "dropped",
        )
        .group_by(TrainingPortalEnrollment.item_id)
    )
    enroll_map = {row[0]: int(row[1]) for row in enroll_rows.all()}
    return {
        cid: (batch_map.get(cid, 0), enroll_map.get(cid, 0)) for cid in course_ids
    }


async def _course_out(db: AsyncSession, course: TrainingPortalCourse) -> TrainingPortalCourseOut:
    counts = await _course_counts(db, [course.id])
    batches_count, enrollments_count = counts.get(course.id, (0, 0))
    return _to_out(course, batches_count=batches_count, enrollments_count=enrollments_count)


@router.get("/", response_model=List[TrainingPortalCourseOut])
async def list_portal_courses(
    response: Response,
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    delivery_mode: Optional[str] = Query(None),
    page: Optional[int] = Query(None, ge=1),
    limit: Optional[int] = Query(None, ge=1, le=100),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    """List training portal courses for admin, teacher, and candidate views with search, filtering, and pagination."""
    query = select(TrainingPortalCourse)

    is_super_admin = (
        getattr(current_user, "is_super_admin", False)
        or (hasattr(current_user.role, "value") and current_user.role.value == "superadmin")
        or (str(current_user.role or "") == "superadmin")
    )

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                TrainingPortalCourse.title.ilike(term),
                TrainingPortalCourse.description.ilike(term),
                TrainingPortalCourse.category.ilike(term),
            )
        )
    if category and category.strip() and category.strip().lower() != "all":
        query = query.where(TrainingPortalCourse.category == category.strip())

    if not is_super_admin:
        query = query.where(TrainingPortalCourse.status == "published")
    elif status_filter and status_filter.strip() and status_filter.strip().lower() != "all":
        query = query.where(TrainingPortalCourse.status == status_filter.strip())

    if delivery_mode and delivery_mode.strip() and delivery_mode.strip().lower() != "all":
        query = query.where(TrainingPortalCourse.delivery_mode == delivery_mode.strip())

    query = query.order_by(TrainingPortalCourse.created_at.desc())

    # Count total matching items before pagination
    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total_result = await db.execute(count_stmt)
    total_count = total_result.scalar() or 0
    response.headers["X-Total-Count"] = str(total_count)

    # Apply pagination if page and limit/page_size are supplied
    effective_limit = limit or page_size
    if page is not None and effective_limit is not None:
        offset = (page - 1) * effective_limit
        query = query.offset(offset).limit(effective_limit)

    result = await db.execute(query)
    courses = list(result.scalars().all())
    counts = await _course_counts(db, [c.id for c in courses])
    return [
        _to_out(
            course,
            batches_count=counts.get(course.id, (0, 0))[0],
            enrollments_count=counts.get(course.id, (0, 0))[1],
        )
        for course in courses
    ]


@router.get("/public", response_model=List[TrainingPortalCourseOut])
async def list_public_paid_portal_courses(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Published paid training courses for the public /courses catalog."""
    query = select(TrainingPortalCourse).where(
        TrainingPortalCourse.status == "published",
        TrainingPortalCourse.fee > 0,
    )
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                TrainingPortalCourse.title.ilike(term),
                TrainingPortalCourse.description.ilike(term),
                TrainingPortalCourse.category.ilike(term),
            )
        )
    if category and category.strip() and category.strip().lower() != "all":
        query = query.where(TrainingPortalCourse.category == category.strip())
    query = query.order_by(TrainingPortalCourse.created_at.desc())
    result = await db.execute(query)
    courses = list(result.scalars().all())
    counts = await _course_counts(db, [c.id for c in courses])
    return [
        _to_out(
            course,
            batches_count=counts.get(course.id, (0, 0))[0],
            enrollments_count=counts.get(course.id, (0, 0))[1],
        )
        for course in courses
    ]


@router.get("/public/{course_id}", response_model=TrainingPortalCourseOut)
async def get_public_paid_portal_course(course_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrainingPortalCourse).where(TrainingPortalCourse.id == course_id))
    course = result.scalar_one_or_none()
    if not course or course.status != "published" or (course.fee or 0) <= 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return await _course_out(db, course)


@router.post("/", response_model=TrainingPortalCourseOut, status_code=status.HTTP_201_CREATED)
async def create_portal_course(
    course_in: TrainingPortalCourseCreate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new training portal course (super admin only)."""
    now = datetime.utcnow()
    course = TrainingPortalCourse(
        id=str(uuid.uuid4()),
        created_by_id=current_user.id,
        title=course_in.title.strip(),
        description=course_in.description.strip(),
        category=course_in.category.strip(),
        duration=course_in.duration.strip(),
        delivery_mode=course_in.delivery_mode,
        status=course_in.status,
        skill_level=course_in.skill_level,
        fee=course_in.fee,
        emi_fee=course_in.emi_fee,
        thumbnail_url=course_in.thumbnail_url,
        prerequisites=course_in.prerequisites,
        key_highlights=course_in.key_highlights or [],
        curriculum=course_in.curriculum or [],
        created_at=now,
        updated_at=now,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return await _course_out(db, course)


@router.get("/{course_id}", response_model=TrainingPortalCourseOut)
async def get_portal_course(
    course_id: str,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TrainingPortalCourse).where(TrainingPortalCourse.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return await _course_out(db, course)


@router.put("/{course_id}", response_model=TrainingPortalCourseOut)
async def update_portal_course(
    course_id: str,
    course_update: TrainingPortalCourseUpdate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TrainingPortalCourse).where(TrainingPortalCourse.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    update_data = course_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)
    course.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(course)
    return await _course_out(db, course)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portal_course(
    course_id: str,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TrainingPortalCourse).where(TrainingPortalCourse.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    await db.delete(course)
    await db.commit()
    return None
