import uuid
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.training_portal_course import TrainingPortalCourse
from models.training_portal_batch import TrainingPortalBatch
from models.training_portal_enrollment import TrainingPortalEnrollment
from schemas.training_portal_course import (
    TrainingPortalCourseCreate,
    TrainingPortalCourseUpdate,
    TrainingPortalCourseOut,
)
from services.auth_service import require_super_admin, require_training_portal_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training-portal/courses", tags=["Training Portal Courses"])


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
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    delivery_mode: Optional[str] = Query(None),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    """List training portal courses for admin, teacher, and candidate views."""
    query = select(TrainingPortalCourse).order_by(TrainingPortalCourse.created_at.desc())

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                TrainingPortalCourse.title.ilike(term),
                TrainingPortalCourse.description.ilike(term),
                TrainingPortalCourse.category.ilike(term),
            )
        )
    if category:
        query = query.where(TrainingPortalCourse.category == category.strip())
    if status_filter and status_filter != "all":
        query = query.where(TrainingPortalCourse.status == status_filter.strip())
    if delivery_mode and delivery_mode != "all":
        query = query.where(TrainingPortalCourse.delivery_mode == delivery_mode.strip())

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
        thumbnail_url=course_in.thumbnail_url,
        prerequisites=course_in.prerequisites,
        key_highlights=course_in.key_highlights or [],
        curriculum=course_in.curriculum or [],
        created_at=now,
        updated_at=now,
    )
    db.add(course)
    await db.flush()
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

    await db.flush()
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
    return None
