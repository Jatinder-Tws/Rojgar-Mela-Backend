import uuid
import logging
from datetime import datetime, date
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, Form, File, UploadFile, BackgroundTasks, HTTPException, status, Query, Request
from jose import JWTError, jwt
from sqlalchemy import select, or_, and_, func, exists
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User, UserRole
from models.company_internship import CompanyInternship, CompanyInternshipApplication
from models.imported_user_password import ImportedUserPassword
from models.resume import Resume
from schemas.company_internship import (
    CompanyInternshipCreate,
    CompanyInternshipUpdate,
    CompanyInternshipOut,
    CompanyInternshipListResponse,
    CompanyInternshipApplicationOut,
    CompanyInternshipApplicationDetailOut,
    CandidateDetailsOut,
    CompanyInternshipApplicationListResponse
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
from services.file_service import save_upload
from services.email_service import send_welcome_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internships", tags=["Company Internships"])


# ── FILE UPLOAD HELPER ────────────────────────────────────────────────────────

@router.post("/thumbnail", response_model=dict)
async def upload_internship_thumbnail(
    file: UploadFile = File(...),
    current_user: User = Depends(require_provider_or_super_admin)
):
    """
    Upload cover thumbnail for internships.
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

    thumbnail_dir = base_dir / "internship_thumbnails"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = thumbnail_dir / safe_name

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return {"thumbnail_url": f"/uploads/internship_thumbnails/{safe_name}"}


@router.post("/brochure", response_model=dict)
async def upload_internship_brochure(
    file: UploadFile = File(...),
    current_user: User = Depends(require_provider_or_super_admin)
):
    """
    Upload brochure document for internships.
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

    brochure_dir = base_dir / "internship_brochures"
    brochure_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = brochure_dir / safe_name

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return {"brochure_url": f"/uploads/internship_brochures/{safe_name}"}


# ── INTERNSHIPS CRUD ─────────────────────────────────────────────────────────

@router.post("/", response_model=CompanyInternshipOut, status_code=201)
async def create_internship(
    internship_in: CompanyInternshipCreate,
    current_user: User = Depends(require_provider_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Post a new internship listing. Requires Provider role or SuperAdmin.
    """
    internship = CompanyInternship(
        id=str(uuid.uuid4()),
        provider_id=current_user.id,
        title=internship_in.title,
        description=internship_in.description,
        thumbnail_url=internship_in.thumbnail_url,
        brochure_url=internship_in.brochure_url,
        is_stipend=internship_in.is_stipend,
        stipend_amount=internship_in.stipend_amount if internship_in.is_stipend else None,
        duration=internship_in.duration,
        duration_unit=internship_in.duration_unit,
        state=internship_in.state,
        city=internship_in.city,
        address=internship_in.address,
        apply_by=internship_in.apply_by,
        start_date=internship_in.start_date,
        company_name=internship_in.company_name,
        who_can_apply=internship_in.who_can_apply,
        skills_required=internship_in.skills_required,
        perks=internship_in.perks,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(internship)
    await db.flush()
    
    # Return output (applicant_count defaults to 0)
    out = CompanyInternshipOut.model_validate(internship)
    out.applicant_count = 0
    return out


@router.get("/my", response_model=List[CompanyInternshipOut])
async def get_my_internships(
    current_user: User = Depends(require_provider_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all internships posted by the logged-in Provider (or all for SuperAdmin).
    Includes applicant count for each.
    """
    query = (
        select(
            CompanyInternship,
            func.count(CompanyInternshipApplication.id).label("applicant_count")
        )
        .outerjoin(CompanyInternshipApplication, CompanyInternship.id == CompanyInternshipApplication.internship_id)
    )

    is_admin = getattr(current_user, "is_super_admin", False) or current_user.role == UserRole.superadmin
    if not is_admin:
        query = query.where(CompanyInternship.provider_id == current_user.id)

    query = query.group_by(CompanyInternship.id).order_by(CompanyInternship.created_at.desc())
    
    result = await db.execute(query)
    out = []
    for row in result.all():
        internship, app_count = row
        val = CompanyInternshipOut.model_validate(internship)
        val.applicant_count = app_count
        out.append(val)
    return out


@router.get("/", response_model=CompanyInternshipListResponse)
async def list_internships(
    search: Optional[str] = Query(None),
    is_stipend: Optional[bool] = Query(None),
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
    Public endpoint: Browse active internships with search, filtering, sorting, and pagination.
    """
    # Base query for active listings
    query = (
        select(
            CompanyInternship,
            func.count(CompanyInternshipApplication.id).label("applicant_count")
        )
        .outerjoin(CompanyInternshipApplication, CompanyInternship.id == CompanyInternshipApplication.internship_id)
        .where(CompanyInternship.is_active == True)
    )

    # 1. Filters
    if is_stipend is not None:
        query = query.where(CompanyInternship.is_stipend == is_stipend)
    if city:
        query = query.where(CompanyInternship.city.ilike(f"%{city.strip()}%"))
    if state:
        query = query.where(CompanyInternship.state.ilike(f"%{state.strip()}%"))
    if duration:
        query = query.where(CompanyInternship.duration <= duration)
    if duration_unit:
        query = query.where(CompanyInternship.duration_unit == duration_unit)

    if search:
        term = f"%{search.strip()}%"
        # Search title, description, company name, city, state, or skills_required json array
        # JSON cast to string for ilike matching
        from sqlalchemy import cast, String as SqlString
        query = query.where(
            or_(
                CompanyInternship.title.ilike(term),
                CompanyInternship.description.ilike(term),
                CompanyInternship.company_name.ilike(term),
                CompanyInternship.city.ilike(term),
                CompanyInternship.state.ilike(term),
                cast(CompanyInternship.skills_required, SqlString).ilike(term)
            )
        )

    query = query.group_by(CompanyInternship.id)

    # 2. Sorting
    if sort_by == "oldest":
        query = query.order_by(CompanyInternship.created_at.asc())
    elif sort_by == "apply_by_soonest":
        query = query.order_by(CompanyInternship.apply_by.asc())
    else:
        query = query.order_by(CompanyInternship.created_at.desc())

    # Count total matching results
    # We create a subquery count to support grouping properly
    count_subquery = query.subquery()
    total_result = await db.execute(select(func.count()).select_from(count_subquery))
    total = total_result.scalar() or 0

    # 3. Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = []
    for row in result.all():
        internship, app_count = row
        val = CompanyInternshipOut.model_validate(internship)
        val.applicant_count = app_count
        items.append(val)

    return CompanyInternshipListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{id}", response_model=CompanyInternshipOut)
async def get_internship_detail(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed description of a single internship.
    """
    query = (
        select(
            CompanyInternship,
            func.count(CompanyInternshipApplication.id).label("applicant_count")
        )
        .outerjoin(CompanyInternshipApplication, CompanyInternship.id == CompanyInternshipApplication.internship_id)
        .where(CompanyInternship.id == id)
        .group_by(CompanyInternship.id)
    )
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Internship posting not found"
        )
    internship, app_count = row
    val = CompanyInternshipOut.model_validate(internship)
    val.applicant_count = app_count
    return val


@router.put("/{id}", response_model=CompanyInternshipOut)
async def update_internship(
    id: str,
    internship_update: CompanyInternshipUpdate,
    current_user: User = Depends(require_provider_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update internship details. Requires Provider who posted it, or SuperAdmin.
    """
    result = await db.execute(select(CompanyInternship).where(CompanyInternship.id == id))
    internship = result.scalar_one_or_none()
    if not internship:
        raise HTTPException(status_code=404, detail="Internship not found")

    is_admin = getattr(current_user, "is_super_admin", False) or current_user.role == UserRole.superadmin
    if not is_admin and internship.provider_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this internship listing."
        )

    # Apply updates
    update_data = internship_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(internship, field, value)
    
    internship.updated_at = datetime.utcnow()
    await db.flush()

    # Get application count
    app_count_res = await db.execute(
        select(func.count(CompanyInternshipApplication.id))
        .where(CompanyInternshipApplication.internship_id == id)
    )
    app_count = app_count_res.scalar() or 0

    out = CompanyInternshipOut.model_validate(internship)
    out.applicant_count = app_count
    return out


@router.delete("/{id}", status_code=204)
async def delete_internship(
    id: str,
    current_user: User = Depends(require_provider_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove an internship listing. Requires Provider who posted it, or SuperAdmin.
    """
    result = await db.execute(select(CompanyInternship).where(CompanyInternship.id == id))
    internship = result.scalar_one_or_none()
    if not internship:
        raise HTTPException(status_code=404, detail="Internship not found")

    is_admin = getattr(current_user, "is_super_admin", False) or current_user.role == UserRole.superadmin
    if not is_admin and internship.provider_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this internship listing."
        )

    await db.delete(internship)
    await db.commit()
    return None


# ── SEEKER APPLICATIONS & FLOW ────────────────────────────────────────────────

@router.post("/{id}/apply", status_code=201)
async def apply_to_internship(
    id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    why_join: str = Form(...),
    career_goals: str = Form(...),
    why_consider: str = Form(...),
    resume: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Apply for an internship listing.
    Supports Prefill for logged in seekers and Guest Flow for unregistered users.
    Blocks double-applying.
    """
    # 1. Resolve Internship
    internship_res = await db.execute(select(CompanyInternship).where(CompanyInternship.id == id))
    internship = internship_res.scalar_one_or_none()
    if not internship:
        raise HTTPException(status_code=404, detail="Internship listing not found")

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
                detail="Only seekers can submit internship applications."
            )
        
        # Check if they already applied
        existing_res = await db.execute(
            select(CompanyInternshipApplication).where(
                CompanyInternshipApplication.internship_id == id,
                CompanyInternshipApplication.seeker_id == seeker_user.id
            )
        )
        if existing_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already applied for this internship."
            )
        
        # Resolve resume
        resume_url = None
        if resume and resume.filename:
            # Seeker uploaded a new resume
            file_path, filename, size_bytes = await save_upload(resume, seeker_user.id)
            resume_url = f"/api/resumes/{seeker_user.id}/download"
            
            # Save or update Resume model for search/matches
            exist_res = await db.execute(
                select(Resume).where(Resume.user_id == seeker_user.id).order_by(Resume.created_at.desc()).limit(1)
            )
            ex_resume = exist_res.scalar_one_or_none()
            if ex_resume:
                ex_resume.filename = filename
                ex_resume.file_path = file_path
                ex_resume.file_size_bytes = size_bytes
                ex_resume.updated_at = datetime.utcnow()
            else:
                db_resume = Resume(
                    id=str(uuid.uuid4()),
                    user_id=seeker_user.id,
                    filename=filename,
                    file_path=file_path,
                    file_size_bytes=size_bytes,
                    source="upload",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(db_resume)
        else:
            # Retrieve latest uploaded resume of the user
            exist_res = await db.execute(
                select(Resume).where(Resume.user_id == seeker_user.id).order_by(Resume.created_at.desc()).limit(1)
            )
            ex_resume = exist_res.scalar_one_or_none()
            if not ex_resume:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Please upload your resume to apply."
                )
            resume_url = f"/api/resumes/{seeker_user.id}/download"

    else:
        # Seeker is a guest (not logged in)
        # Check if email is already registered
        email_clean = email.strip().lower()
        existing_user_res = await db.execute(select(User).where(User.email == email_clean))
        existing_user = existing_user_res.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered. Please log in to submit your application."
            )
        
        if not resume or not resume.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resume upload is required for new applicants."
            )
        
        is_new_user = True
        temp_pwd = generate_secure_password()
        hashed_pwd = hash_password(temp_pwd)

        # Create new seeker user
        seeker_user = User(
            id=str(uuid.uuid4()),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=email_clean,
            phone=phone_number.strip(),
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

        # Save uploaded resume
        file_path, filename, size_bytes = await save_upload(resume, seeker_user.id)
        resume_url = f"/api/resumes/{seeker_user.id}/download"
        
        db_resume = Resume(
            id=str(uuid.uuid4()),
            user_id=seeker_user.id,
            filename=filename,
            file_path=file_path,
            file_size_bytes=size_bytes,
            source="upload",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(db_resume)
        await db.flush()

    # 3. Save application record
    application = CompanyInternshipApplication(
        id=str(uuid.uuid4()),
        internship_id=id,
        seeker_id=seeker_user.id,
        why_join=why_join.strip(),
        career_goals=career_goals.strip(),
        why_consider=why_consider.strip(),
        resume_url=resume_url,
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
            user_id=internship.provider_id,
            type=NotificationType.application,
            title="New Internship Application",
            message=f"A new candidate {seeker_user.first_name} {seeker_user.last_name or ''} has applied for your internship listing: {internship.title}.",
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


@router.get("/applications/me", response_model=List[CompanyInternshipApplicationOut])
async def get_my_applications(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db)
):
    """
    Get application history for the logged-in seeker.
    Non-seekers (providers, super-admins) receive an empty list instead of a 403.
    """
    role_str = current_user.role.value if current_user.role and hasattr(current_user.role, "value") else str(current_user.role or "")
    if role_str != "seeker" and not getattr(current_user, "is_super_admin", False):
        return []
    query = (
        select(CompanyInternshipApplication)
        .where(CompanyInternshipApplication.seeker_id == current_user.id)
        .order_by(CompanyInternshipApplication.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


# ── RECRUITER APPLICANT VIEW ──────────────────────────────────────────────────

@router.get("/{id}/applications", response_model=CompanyInternshipApplicationListResponse)
async def get_internship_applications(
    id: str,
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("newest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_provider_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve applicant list for a specific internship. Requires posting Provider or SuperAdmin.
    Supports filtering by candidate name, sorting, and pagination.
    """
    # Verify ownership of internship
    internship_res = await db.execute(select(CompanyInternship).where(CompanyInternship.id == id))
    internship = internship_res.scalar_one_or_none()
    if not internship:
        raise HTTPException(status_code=404, detail="Internship listing not found")

    is_admin = getattr(current_user, "is_super_admin", False) or current_user.role == UserRole.superadmin
    if not is_admin and internship.provider_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view applications for this internship listing."
        )

    query = (
        select(CompanyInternshipApplication, User)
        .join(User, CompanyInternshipApplication.seeker_id == User.id)
        .where(CompanyInternshipApplication.internship_id == id)
    )

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.first_name.ilike(term),
                User.last_name.ilike(term),
                func.concat(User.first_name, " ", User.last_name).ilike(term)
            )
        )

    if sort_by == "oldest":
        query = query.order_by(CompanyInternshipApplication.created_at.asc())
    elif sort_by == "updated_newest":
        query = query.order_by(CompanyInternshipApplication.updated_at.desc())
    elif sort_by == "updated_oldest":
        query = query.order_by(CompanyInternshipApplication.updated_at.asc())
    else:
        query = query.order_by(CompanyInternshipApplication.created_at.desc())

    # Count total matching results
    count_subquery = query.subquery()
    total_result = await db.execute(select(func.count()).select_from(count_subquery))
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    
    items = []
    for row in result.all():
        app, seeker = row
        items.append(
            CompanyInternshipApplicationDetailOut(
                id=app.id,
                internship_id=app.internship_id,
                seeker_id=app.seeker_id,
                why_join=app.why_join,
                career_goals=app.career_goals,
                why_consider=app.why_consider,
                resume_url=app.resume_url,
                created_at=app.created_at,
                candidate=CandidateDetailsOut(
                    seeker_id=seeker.id,
                    first_name=seeker.first_name,
                    last_name=seeker.last_name,
                    email=seeker.email,
                    phone=seeker.phone
                )
            )
        )
    return CompanyInternshipApplicationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )
