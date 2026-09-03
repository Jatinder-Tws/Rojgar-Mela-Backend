import uuid
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.shared.models.user import User
from app.modules.training_portal.models.training_portal_course import TrainingPortalCourse
from app.modules.training_portal.models.training_portal_category import TrainingPortalCourseCategory
from app.modules.training_portal.schemas.training_portal_category import (
    TrainingPortalCategoryCreate,
    TrainingPortalCategoryUpdate,
    TrainingPortalCategoryOut,
)
from app.core.dependencies import require_super_admin, require_training_portal_user, require_super_admin_or_permission

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    "Software Development",
    "Data Science",
    "Digital Marketing",
    "Mobile Apps",
    "Design & Creative",
]

router = APIRouter(prefix="/training-portal/categories", tags=["Training Portal Categories"])


async def _ensure_default_categories(db: AsyncSession) -> None:
    result = await db.execute(select(func.count()).select_from(TrainingPortalCourseCategory))
    if (result.scalar() or 0) > 0:
        return
    now = datetime.utcnow()
    for idx, name in enumerate(DEFAULT_CATEGORIES):
        db.add(
            TrainingPortalCourseCategory(
                id=str(uuid.uuid4()),
                name=name,
                sort_order=idx,
                created_at=now,
                updated_at=now,
            )
        )
    await db.commit()


async def _category_out(db: AsyncSession, category: TrainingPortalCourseCategory) -> TrainingPortalCategoryOut:
    count_res = await db.execute(
        select(func.count())
        .select_from(TrainingPortalCourse)
        .where(TrainingPortalCourse.category == category.name)
    )
    return TrainingPortalCategoryOut(
        id=category.id,
        name=category.name,
        sort_order=category.sort_order,
        course_count=count_res.scalar() or 0,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.get("/", response_model=List[TrainingPortalCategoryOut])
async def list_categories(
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_default_categories(db)
    result = await db.execute(
        select(TrainingPortalCourseCategory).order_by(
            TrainingPortalCourseCategory.sort_order,
            TrainingPortalCourseCategory.name,
        )
    )
    categories = result.scalars().all()
    out = []
    for cat in categories:
        out.append(await _category_out(db, cat))
    return out


@router.post("/", response_model=TrainingPortalCategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: TrainingPortalCategoryCreate,
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
    db: AsyncSession = Depends(get_db),
):
    name = payload.name.strip()
    existing = await db.execute(
        select(TrainingPortalCourseCategory).where(TrainingPortalCourseCategory.name.ilike(name))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Category already exists")

    max_order = await db.execute(select(func.max(TrainingPortalCourseCategory.sort_order)))
    sort_order = (max_order.scalar() or 0) + 1
    now = datetime.utcnow()
    category = TrainingPortalCourseCategory(
        id=str(uuid.uuid4()),
        name=name,
        sort_order=sort_order,
        created_at=now,
        updated_at=now,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return await _category_out(db, category)


@router.put("/{category_id}", response_model=TrainingPortalCategoryOut)
async def update_category(
    category_id: str,
    payload: TrainingPortalCategoryUpdate,
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalCourseCategory).where(TrainingPortalCourseCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    new_name = payload.name.strip()
    if new_name.lower() != category.name.lower():
        dup = await db.execute(
            select(TrainingPortalCourseCategory).where(
                TrainingPortalCourseCategory.name.ilike(new_name),
                TrainingPortalCourseCategory.id != category_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Category name already exists")

        old_name = category.name
        category.name = new_name
        category.updated_at = datetime.utcnow()
        await db.execute(
            update(TrainingPortalCourse)
            .where(TrainingPortalCourse.category == old_name)
            .values(category=new_name, updated_at=datetime.utcnow())
        )
    else:
        category.name = new_name
        category.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(category)
    return await _category_out(db, category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    current_user: User = Depends(require_super_admin_or_permission("training_courses")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalCourseCategory).where(TrainingPortalCourseCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    count_res = await db.execute(
        select(func.count())
        .select_from(TrainingPortalCourse)
        .where(TrainingPortalCourse.category == category.name)
    )
    if (count_res.scalar() or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete category while courses are assigned to it",
        )

    await db.delete(category)
    await db.commit()
    return None
