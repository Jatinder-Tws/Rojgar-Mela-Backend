import uuid
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, BackgroundTasks, HTTPException, status, Query, Request
from jose import JWTError, jwt
from sqlalchemy import select, or_, and_, func, exists
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User, UserRole
from models.training_course import TrainingCourse, TrainingModule, TrainingModuleTopic, TrainingCourseApplication
from models.imported_user_password import ImportedUserPassword
from schemas.training_course import (
    TrainingCourseCreate,
    TrainingCourseUpdate,
    TrainingCourseOut,
    TrainingCourseListResponse,
    TrainingCourseApplicationCreate,
    TrainingCourseApplicationOut,
    TrainingCourseApplicationDetailOut,
    TrainingCourseApplicationListResponse
)
from services.auth_service import (
    get_current_user,
    require_seeker,
    require_provider,
    require_provider_or_super_admin,
    require_super_admin,
    require_authenticated,
    hash_password,
    generate_secure_password
)
from services.email_service import send_welcome_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training", tags=["Training Courses"])


# ── FILE UPLOAD ENDPOINTS ───────────────────────────────────────────────────

@router.post("/thumbnail", response_model=dict)
async def upload_training_thumbnail(
    file: UploadFile = File(...),
    current_user: User = Depends(require_provider_or_super_admin)
):
    """
    Upload cover thumbnail for training courses.
    """
    ext = Path(file.filename or "thumbnail").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files (.jpg, .jpeg, .png, .webp) are allowed."
        )

    base_dir = Path(settings.UPLOAD_DIR)
    if not base_dir.is_absolute():
        base_dir = Path(__file__).parent.parent / base_dir

    thumbnail_dir = base_dir / "training_thumbnails"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = thumbnail_dir / safe_name

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return {"thumbnail_url": f"/uploads/training_thumbnails/{safe_name}"}


@router.post("/brochure", response_model=dict)
async def upload_training_brochure(
    file: UploadFile = File(...),
    current_user: User = Depends(require_provider_or_super_admin)
):
    """
    Upload brochure document for training courses.
    """
    ext = Path(file.filename or "brochure").suffix.lower()
    if ext not in {".pdf", ".doc", ".docx", ".txt", ".jpg", ".jpeg", ".png"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only document/image files (.pdf, .doc, .docx, .txt, .jpg, .jpeg, .png) are allowed."
        )

    base_dir = Path(settings.UPLOAD_DIR)
    if not base_dir.is_absolute():
        base_dir = Path(__file__).parent.parent / base_dir

    brochure_dir = base_dir / "training_brochures"
    brochure_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = brochure_dir / safe_name

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return {"brochure_url": f"/uploads/training_brochures/{safe_name}"}


# ── TRAINING CRUD ENDPOINTS ─────────────────────────────────────────────────

@router.post("/", response_model=TrainingCourseOut, status_code=201)
async def create_course(
    course_in: TrainingCourseCreate,
    current_user: User = Depends(require_provider_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new training course with nested modules and topics.
    """
    course = TrainingCourse(
        id=str(uuid.uuid4()),
        provider_id=current_user.id,
        title=course_in.title,
        description=course_in.description,
        thumbnail_url=course_in.thumbnail_url,
        brochure_url=course_in.brochure_url,
        is_paid=course_in.is_paid,
        price=course_in.price if course_in.is_paid else None,
        duration=course_in.duration,
        duration_unit=course_in.duration_unit,
        skills_learned=course_in.skills_learned,
        has_certificate=course_in.has_certificate,
        company_name=course_in.company_name,
        state=course_in.state,
        city=course_in.city,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(course)
    await db.flush()

    if course_in.modules:
        for m_idx, mod_in in enumerate(course_in.modules):
            module = TrainingModule(
                id=str(uuid.uuid4()),
                course_id=course.id,
                title=mod_in.title,
                description=mod_in.description,
                order_index=mod_in.order_index if mod_in.order_index else m_idx,
                estimated_hours=mod_in.estimated_hours,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(module)
            await db.flush()

            if mod_in.topics:
                for t_idx, topic_in in enumerate(mod_in.topics):
                    topic = TrainingModuleTopic(
                        id=str(uuid.uuid4()),
                        module_id=module.id,
                        title=topic_in.title,
                        order_index=topic_in.order_index if topic_in.order_index else t_idx,
                        created_at=datetime.utcnow()
                    )
                    db.add(topic)

    await db.commit()

    # Re-fetch course details to include modules & topics
    result = await db.execute(
        select(TrainingCourse)
        .options(selectinload(TrainingCourse.modules).selectinload(TrainingModule.topics))
        .where(TrainingCourse.id == course.id)
    )
    course_updated = result.unique().scalar_one()
    out = TrainingCourseOut.model_validate(course_updated)
    out.applicant_count = 0
    return out


@router.get("/my", response_model=List[TrainingCourseOut])
async def get_my_courses(
    current_user: User = Depends(require_provider_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all training courses posted by the logged-in Provider (or all for SuperAdmin).
    Includes applicant count for each course.
    """
    query = (
        select(
            TrainingCourse,
            func.count(TrainingCourseApplication.id).label("applicant_count")
        )
        .options(selectinload(TrainingCourse.modules).selectinload(TrainingModule.topics))
        .outerjoin(TrainingCourseApplication, TrainingCourse.id == TrainingCourseApplication.course_id)
    )

    is_admin = getattr(current_user, "is_super_admin", False) or current_user.role == UserRole.superadmin
    if not is_admin:
        query = query.where(TrainingCourse.provider_id == current_user.id)

    query = query.group_by(TrainingCourse.id).order_by(TrainingCourse.created_at.desc())
    
    result = await db.execute(query)
    out = []
    for row in result.all():
        course, app_count = row
        val = TrainingCourseOut.model_validate(course)
        val.applicant_count = app_count
        out.append(val)
    return out


@router.get("/", response_model=TrainingCourseListResponse)
async def list_courses(
    search: Optional[str] = Query(None),
    is_paid: Optional[bool] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    duration: Optional[int] = Query(None),
    duration_unit: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("newest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint: Browse active training courses with search, filtering, and pagination.
    """
    query = (
        select(
            TrainingCourse,
            func.count(TrainingCourseApplication.id).label("applicant_count")
        )
        .options(selectinload(TrainingCourse.modules).selectinload(TrainingModule.topics))
        .outerjoin(TrainingCourseApplication, TrainingCourse.id == TrainingCourseApplication.course_id)
        .where(TrainingCourse.is_active == True)
    )

    # Filters
    if is_paid is not None:
        query = query.where(TrainingCourse.is_paid == is_paid)
    if city:
        query = query.where(TrainingCourse.city.ilike(f"%{city.strip()}%"))
    if state:
        query = query.where(TrainingCourse.state.ilike(f"%{state.strip()}%"))
    if duration:
        query = query.where(TrainingCourse.duration <= duration)
    if duration_unit:
        query = query.where(TrainingCourse.duration_unit == duration_unit)

    if search:
        term = f"%{search.strip()}%"
        from sqlalchemy import cast, String as SqlString
        query = query.where(
            or_(
                TrainingCourse.title.ilike(term),
                TrainingCourse.description.ilike(term),
                TrainingCourse.company_name.ilike(term),
                TrainingCourse.city.ilike(term),
                TrainingCourse.state.ilike(term),
                cast(TrainingCourse.skills_learned, SqlString).ilike(term)
            )
        )

    query = query.group_by(TrainingCourse.id)

    # Sorting
    if sort_by == "oldest":
        query = query.order_by(TrainingCourse.created_at.asc())
    else:
        query = query.order_by(TrainingCourse.created_at.desc())

    # Count total
    count_subquery = query.subquery()
    total_result = await db.execute(select(func.count()).select_from(count_subquery))
    total = total_result.scalar() or 0

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = []
    for row in result.all():
        course, app_count = row
        val = TrainingCourseOut.model_validate(course)
        val.applicant_count = app_count
        items.append(val)

    return TrainingCourseListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{id}", response_model=TrainingCourseOut)
async def get_course_detail(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get course details for a single training course, including nested modules and topics.
    """
    query = (
            select(
                TrainingCourse,
                func.count(TrainingCourseApplication.id).label("applicant_count")
            )
            .options(selectinload(TrainingCourse.modules).selectinload(TrainingModule.topics))
            .outerjoin(TrainingCourseApplication, TrainingCourse.id == TrainingCourseApplication.course_id)
            .where(TrainingCourse.id == id)
            .group_by(TrainingCourse.id)
        )
    result = await db.execute(query)
    row = result.unique().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training course not found."
        )
    course, app_count = row
    val = TrainingCourseOut.model_validate(course)
    val.applicant_count = app_count
    return val


@router.put("/{id}", response_model=TrainingCourseOut)
async def update_course(
    id: str,
    course_update: TrainingCourseUpdate,
    current_user: User = Depends(require_provider_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update training course metadata, modules, and topics.
    """
    result = await db.execute(select(TrainingCourse).where(TrainingCourse.id == id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Training course not found")

    is_admin = getattr(current_user, "is_super_admin", False) or current_user.role == UserRole.superadmin
    if not is_admin and course.provider_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this course."
        )

    # Exclude modules from top-level updates since we handle them separately
    update_data = course_update.model_dump(exclude_unset=True, exclude={"modules"})
    for field, value in update_data.items():
        setattr(course, field, value)
    
    course.updated_at = datetime.utcnow()

    # Recreate modules and topics if present in update payload
    if course_update.modules is not None:
        # Delete existing modules (cascades to topics)
        await db.execute(
            select(TrainingModule)
            .where(TrainingModule.course_id == id)
        )
        del_modules_res = await db.execute(
            select(TrainingModule).where(TrainingModule.course_id == id)
        )
        for m in del_modules_res.scalars().all():
            await db.delete(m)
        await db.flush()

        for m_idx, mod_in in enumerate(course_update.modules):
            module = TrainingModule(
                id=str(uuid.uuid4()),
                course_id=course.id,
                title=mod_in.title,
                description=mod_in.description,
                order_index=mod_in.order_index if mod_in.order_index else m_idx,
                estimated_hours=mod_in.estimated_hours,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(module)
            await db.flush()

            if mod_in.topics:
                for t_idx, topic_in in enumerate(mod_in.topics):
                    topic = TrainingModuleTopic(
                        id=str(uuid.uuid4()),
                        module_id=module.id,
                        title=topic_in.title,
                        order_index=topic_in.order_index if topic_in.order_index else t_idx,
                        created_at=datetime.utcnow()
                    )
                    db.add(topic)

    await db.flush()

    # Get application count
    app_count_res = await db.execute(
        select(func.count(TrainingCourseApplication.id))
        .where(TrainingCourseApplication.course_id == id)
    )
    app_count = app_count_res.scalar() or 0

    # Refresh relationship to get updated modules
    await db.refresh(course)
    
    # Re-fetch with fresh session state
    refetched_res = await db.execute(
        select(TrainingCourse)
        .options(selectinload(TrainingCourse.modules).selectinload(TrainingModule.topics))
        .where(TrainingCourse.id == course.id)
    )
    refetched = refetched_res.unique().scalar_one()

    out = TrainingCourseOut.model_validate(refetched)
    out.applicant_count = app_count
    return out


@router.delete("/{id}", status_code=204)
async def delete_course(
    id: str,
    current_user: User = Depends(require_provider_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a training course.
    """
    result = await db.execute(select(TrainingCourse).where(TrainingCourse.id == id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Training course not found")

    is_admin = getattr(current_user, "is_super_admin", False) or current_user.role == UserRole.superadmin
    if not is_admin and course.provider_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this course."
        )

    await db.delete(course)
    await db.commit()
    return None


# ── SEEKER APPLICATIONS & FLOW ──────────────────────────────────────────────

@router.post("/{id}/apply", status_code=201)
async def apply_to_course(
    id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    application_in: TrainingCourseApplicationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Apply for a training course listing.
    Supports Prefill for logged in seekers and Guest Flow for unregistered users.
    Blocks double-applying.
    """
    # 1. Resolve Course
    course_res = await db.execute(select(TrainingCourse).where(TrainingCourse.id == id))
    course = course_res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Training course not found")

    # 2. Check if Seeker is authenticated
    seeker_user = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                user_res = await db.execute(select(User).where(User.id == user_id))
                seeker_user = user_res.scalar_one_or_none()
        except JWTError:
            pass

    is_new_user = False
    temp_pwd = None

    if seeker_user:
        # Seeker is logged in
        role_str = seeker_user.role.value if hasattr(seeker_user.role, "value") else str(seeker_user.role)
        if role_str != "seeker" and not seeker_user.is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only seekers can apply for training courses."
            )
        
        # Check if they already applied
        existing_res = await db.execute(
            select(TrainingCourseApplication).where(
                TrainingCourseApplication.course_id == id,
                TrainingCourseApplication.seeker_id == seeker_user.id
            )
        )
        if existing_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already applied for this training course."
            )

    else:
        # Seeker is a guest (not logged in)
        # Check if email is already registered
        email_clean = application_in.email.strip().lower()
        existing_user_res = await db.execute(select(User).where(User.email == email_clean))
        existing_user = existing_user_res.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered. Please log in to submit your application."
            )
        
        is_new_user = True
        temp_pwd = generate_secure_password()
        hashed_pwd = hash_password(temp_pwd)

        # Create new seeker user
        seeker_user = User(
            id=str(uuid.uuid4()),
            first_name=application_in.first_name.strip(),
            last_name=application_in.last_name.strip(),
            email=email_clean,
            phone=application_in.phone.strip(),
            hashed_password=hashed_pwd,
            role=UserRole.seeker,
            is_verified=True,  # Auto-verify on registration through application
            onboarding_complete=False,
            is_first_login=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(seeker_user)
        await db.flush()

        # Save credentials to ImportedUserPassword
        db_pwd = ImportedUserPassword(
            id=str(uuid.uuid4()),
            user_id=seeker_user.id,
            email=email_clean,
            plain_password=temp_pwd,
            created_at=datetime.utcnow()
        )
        db.add(db_pwd)
        await db.flush()

    # 3. Save application record
    application = TrainingCourseApplication(
        id=str(uuid.uuid4()),
        course_id=id,
        seeker_id=seeker_user.id,
        first_name=application_in.first_name.strip(),
        last_name=application_in.last_name.strip(),
        email=application_in.email.strip().lower(),
        phone=application_in.phone.strip(),
        location=application_in.location.strip(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(application)
    await db.commit()

    # Send notification to the provider
    try:
        from services.notification_service import create_notification
        from models.notification import NotificationType
        await create_notification(
            db=db,
            user_id=course.provider_id,
            type=NotificationType.application,
            title="New Training Registration",
            message=f"A new candidate {seeker_user.first_name} {seeker_user.last_name or ''} has registered for your training course: {course.title}.",
            related_user_id=seeker_user.id
        )
    except Exception as e:
        logger.error(f"Failed to send notification to provider: {e}")

    # 4. Trigger Welcome/Credentials Email for newly registered seekers in background
    if is_new_user:
        background_tasks.add_task(
            send_welcome_email,
            seeker_user.email,
            seeker_user.first_name,
            "seeker",
            password=temp_pwd
        )

    return {"status": "success", "message": "Application submitted successfully"}


@router.get("/applications/me", response_model=List[TrainingCourseApplicationDetailOut])
async def get_my_applications(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db)
):
    """
    Get application history (My Trainings) for the logged-in seeker.
    Non-seekers (providers, super-admins) receive an empty list instead of a 403.
    """
    role_str = current_user.role.value if current_user.role and hasattr(current_user.role, "value") else str(current_user.role or "")
    if role_str != "seeker" and not getattr(current_user, "is_super_admin", False):
        return []
    query = (
        select(TrainingCourseApplication, TrainingCourse)
        .join(TrainingCourse, TrainingCourseApplication.course_id == TrainingCourse.id)
        .where(TrainingCourseApplication.seeker_id == current_user.id)
        .order_by(TrainingCourseApplication.created_at.desc())
    )
    result = await db.execute(query)
    
    out = []
    for row in result.all():
        app, course = row
        out.append(
            TrainingCourseApplicationDetailOut(
                id=app.id,
                course_id=app.course_id,
                seeker_id=app.seeker_id,
                first_name=app.first_name,
                last_name=app.last_name,
                email=app.email,
                phone=app.phone,
                location=app.location,
                created_at=app.created_at,
                course_title=course.title,
                course_company=course.company_name
            )
        )
    return out


# ── APPLICANT VIEW FOR RECRUITERS / ADMINS ───────────────────────────────────

@router.get("/{id}/applications", response_model=TrainingCourseApplicationListResponse)
async def get_course_applications(
    id: str,
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("newest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_provider_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve applicant list for a specific training course. Requires course Provider or SuperAdmin.
    Supports filtering by seeker name (first name/last name), sorting, and page-based pagination.
    """
    # Verify ownership of course
    course_res = await db.execute(select(TrainingCourse).where(TrainingCourse.id == id))
    course = course_res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Training course not found")

    is_admin = getattr(current_user, "is_super_admin", False) or current_user.role == UserRole.superadmin
    if not is_admin and course.provider_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view applications for this course."
        )

    # Base query
    query = select(TrainingCourseApplication).where(TrainingCourseApplication.course_id == id)

    # Apply search filter
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                TrainingCourseApplication.first_name.ilike(term),
                TrainingCourseApplication.last_name.ilike(term),
                func.concat(TrainingCourseApplication.first_name, " ", TrainingCourseApplication.last_name).ilike(term)
            )
        )

    # Apply sorting
    if sort_by == "oldest":
        query = query.order_by(TrainingCourseApplication.created_at.asc())
    elif sort_by == "updated_newest":
        query = query.order_by(TrainingCourseApplication.updated_at.desc())
    elif sort_by == "updated_oldest":
        query = query.order_by(TrainingCourseApplication.updated_at.asc())
    else:
        query = query.order_by(TrainingCourseApplication.created_at.desc())

    # Count total matching results
    count_subquery = query.subquery()
    total_result = await db.execute(select(func.count()).select_from(count_subquery))
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    
    items = []
    for app in result.scalars().all():
        items.append(
            TrainingCourseApplicationDetailOut(
                id=app.id,
                course_id=app.course_id,
                seeker_id=app.seeker_id,
                first_name=app.first_name,
                last_name=app.last_name,
                email=app.email,
                phone=app.phone,
                location=app.location,
                created_at=app.created_at,
                course_title=course.title,
                course_company=course.company_name
            )
        )
    return TrainingCourseApplicationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )
