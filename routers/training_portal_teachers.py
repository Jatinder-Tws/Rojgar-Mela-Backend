import uuid
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, BackgroundTasks
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User, UserRole
from models.training_portal_teacher import TrainingPortalTeacher
from models.training_portal_batch import TrainingPortalBatch
from schemas.training_portal_teacher import (
    TrainingPortalTeacherCreate,
    TrainingPortalTeacherUpdate,
    TrainingPortalTeacherOut,
)
from services.auth_service import (
    require_super_admin,
    require_training_portal_user,
    hash_password,
)
from services.email_service import send_welcome_email
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training-portal/teachers", tags=["Training Portal Teachers"])


def _to_out(teacher: TrainingPortalTeacher, batches_count: int = 0) -> TrainingPortalTeacherOut:
    return TrainingPortalTeacherOut(
        id=teacher.id,
        name=teacher.name,
        email=teacher.email,
        phone=teacher.phone,
        bio=teacher.bio,
        subjects=teacher.subjects or [],
        assigned_batches_count=batches_count,
        rating=teacher.rating,
        status=teacher.status,
        avatar=teacher.avatar,
        login_username=teacher.login_username,
        login_password=teacher.login_password,
        login_active=teacher.login_active,
        last_login_at=teacher.last_login_at,
        created_at=teacher.created_at,
        updated_at=teacher.updated_at,
    )


async def _get_batches_count(db: AsyncSession, teacher_id: str) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(TrainingPortalBatch)
        .where(TrainingPortalBatch.instructor_id == teacher_id)
    )
    return int(result.scalar() or 0)


def _split_name(full_name: str) -> tuple[str, str]:
    parts = (full_name or "").strip().split(" ", 1)
    first = parts[0] if parts else "Instructor"
    last = parts[1] if len(parts) > 1 else ""
    return first or "Instructor", last


async def _sync_login_user(
    db: AsyncSession,
    teacher: TrainingPortalTeacher,
    *,
    email: str,
    name: str,
    password: Optional[str],
    is_active: bool,
) -> None:
    """Create or update the linked users-table login account for a portal teacher.

    Teacher logs in on the main site with this email + password, then gets
    redirected to the training portal (role == teacher).
    """
    email_norm = email.strip().lower()
    first_name, last_name = _split_name(name)

    user: Optional[User] = None
    if teacher.user_id:
        res = await db.execute(select(User).where(User.id == teacher.user_id))
        user = res.scalar_one_or_none()

    if user is None:
        # Reuse an existing account with the same email if present, else create one.
        res = await db.execute(select(User).where(User.email == email_norm))
        user = res.scalar_one_or_none()

    if user is None:
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email_norm,
            phone=(teacher.phone or "0000000000")[:15],
            role=UserRole.teacher,
            is_verified=True,
            onboarding_complete=True,
            is_super_admin=False,
            totp_enabled=False,
        )
        if password:
            user.hashed_password = hash_password(password)
        db.add(user)
        await db.flush()
    else:
        user.first_name = first_name
        user.last_name = last_name
        user.email = email_norm
        user.role = UserRole.teacher
        user.is_verified = True
        if password:
            user.hashed_password = hash_password(password)

    # `inactive` teachers cannot log in: unverify so login is blocked cleanly.
    user.is_verified = bool(is_active)

    teacher.user_id = user.id


@router.get("/", response_model=List[TrainingPortalTeacherOut])
async def list_portal_teachers(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    """List training portal teachers."""
    query = select(TrainingPortalTeacher).order_by(TrainingPortalTeacher.created_at.desc())

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                TrainingPortalTeacher.name.ilike(term),
                TrainingPortalTeacher.email.ilike(term),
            )
        )
    if status_filter and status_filter != "all":
        query = query.where(TrainingPortalTeacher.status == status_filter.strip())

    result = await db.execute(query)
    teachers = result.scalars().all()
    out: list[TrainingPortalTeacherOut] = []
    for teacher in teachers:
        batches_count = await _get_batches_count(db, teacher.id)
        out.append(_to_out(teacher, batches_count))
    return out


@router.post("/", response_model=TrainingPortalTeacherOut, status_code=status.HTTP_201_CREATED)
async def create_portal_teacher(
    teacher_in: TrainingPortalTeacherCreate,background_tasks: BackgroundTasks,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new training portal teacher (super admin only)."""
    # Check for duplicate email
    existing = await db.execute(
        select(TrainingPortalTeacher).where(TrainingPortalTeacher.email == teacher_in.email.strip().lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A teacher with this email already exists",
        )

    # Check for duplicate username
    existing_user = await db.execute(
        select(TrainingPortalTeacher).where(TrainingPortalTeacher.login_username == teacher_in.login_username.strip())
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A teacher with this login username already exists",
        )

    now = datetime.utcnow()
    teacher = TrainingPortalTeacher(
        id=str(uuid.uuid4()),
        created_by_id=current_user.id,
        name=teacher_in.name.strip(),
        email=teacher_in.email.strip().lower(),
        phone=teacher_in.phone or "+91 00000 00000",
        bio=teacher_in.bio or "Qualified physical classroom instructor.",
        subjects=teacher_in.subjects or [],
        rating=teacher_in.rating or 5.0,
        status=teacher_in.status or "active",
        avatar=teacher_in.avatar,
        login_username=teacher_in.login_username.strip(),
        login_password=teacher_in.login_password,  # stored as-is for now (same pattern as static data)
        login_active=teacher_in.login_active if teacher_in.login_active is not None else True,
        created_at=now,
        updated_at=now,
    )
    db.add(teacher)
    await db.flush()

    # Create the linked login account so the teacher can actually sign in.
    await _sync_login_user(
        db,
        teacher,
        email=teacher.email,
        name=teacher.name,
        password=teacher_in.login_password,
        is_active=teacher.status == "active" and teacher.login_active,
    )

    await db.flush()
    await db.refresh(teacher)
    background_tasks.add_task(send_welcome_email,teacher.email, teacher.name, "teacher")
    return _to_out(teacher)


@router.get("/{teacher_id}", response_model=TrainingPortalTeacherOut)
async def get_portal_teacher(
    teacher_id: str,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TrainingPortalTeacher).where(TrainingPortalTeacher.id == teacher_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    batches_count = await _get_batches_count(db, teacher.id)
    return _to_out(teacher, batches_count)


@router.put("/{teacher_id}", response_model=TrainingPortalTeacherOut)
async def update_portal_teacher(
    teacher_id: str,
    teacher_update: TrainingPortalTeacherUpdate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TrainingPortalTeacher).where(TrainingPortalTeacher.id == teacher_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")

    update_data = teacher_update.model_dump(exclude_unset=True)

    # Check unique email if changed
    if "email" in update_data:
        new_email = update_data["email"].strip().lower()
        dup = await db.execute(
            select(TrainingPortalTeacher).where(
                TrainingPortalTeacher.email == new_email,
                TrainingPortalTeacher.id != teacher_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        update_data["email"] = new_email

    # Check unique username if changed
    if "login_username" in update_data:
        new_username = update_data["login_username"].strip()
        dup = await db.execute(
            select(TrainingPortalTeacher).where(
                TrainingPortalTeacher.login_username == new_username,
                TrainingPortalTeacher.id != teacher_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login username already in use")
        update_data["login_username"] = new_username

    for field, value in update_data.items():
        setattr(teacher, field, value)
    teacher.updated_at = datetime.utcnow()

    # Keep the linked login account in sync (email, name, password, active state).
    login_touched = any(
        key in update_data
        for key in ("email", "name", "login_password", "login_active", "status")
    )
    if login_touched:
        await _sync_login_user(
            db,
            teacher,
            email=teacher.email,
            name=teacher.name,
            password=update_data.get("login_password"),
            is_active=teacher.status == "active" and teacher.login_active,
        )

    await db.flush()
    await db.refresh(teacher)
    return _to_out(teacher)


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portal_teacher(
    teacher_id: str,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalTeacher).where(TrainingPortalTeacher.id == teacher_id)
    )
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")

    batches_count = await _get_batches_count(db, teacher_id)
    if batches_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete instructor assigned to {batches_count} batch(es). Reassign or delete those batches first.",
        )

    # Block login for the linked account (keep the user row for history/audit).
    if teacher.user_id:
        res = await db.execute(select(User).where(User.id == teacher.user_id))
        login_user = res.scalar_one_or_none()
        if login_user:
            login_user.is_verified = False

    await db.delete(teacher)
    return None