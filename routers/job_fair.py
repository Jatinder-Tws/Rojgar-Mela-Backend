import re
import uuid
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Query
from fastapi.responses import Response
from sqlalchemy import select, or_, and_, func, exists
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.job_fair import JobFair, JobFairCompany, JobFairSeeker
from models.user import User, UserRole, CompanyType
from models.imported_user_password import ImportedUserPassword
from schemas.job_fair import (
    JobFairCreate,
    JobFairUpdate,
    JobFairOut,
    JobFairListResponse,
    JobFairCompanyOut,
    JobFairSeekerOut,
    JobFairCompanyListResponse,
    JobFairSeekerListResponse,
)
from services.auth_service import (
    get_current_user,
    hash_password,
    require_super_admin,
)
from services.totp_service import totp_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/job-fairs", tags=["Job Fairs"])


def slugify(text: str) -> str:
    # Convert to lowercase
    text = text.lower()
    # Replace non-alphanumeric characters with spaces
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    # Replace multiple spaces/hyphens with single hyphen
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


async def generate_unique_slug(title: str, db: AsyncSession) -> str:
    base_slug = slugify(title)
    if not base_slug:
        base_slug = "job-fair"

    slug = base_slug
    counter = 1
    while True:
        result = await db.execute(select(JobFair).where(JobFair.slug == slug))
        if not result.scalar_one_or_none():
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


async def get_job_fair_by_id_or_slug(id_or_slug: str, db: AsyncSession) -> JobFair | None:
    if is_valid_uuid(id_or_slug):
        result = await db.execute(
            select(JobFair).where((JobFair.id == id_or_slug) | (JobFair.slug == id_or_slug))
        )
    else:
        result = await db.execute(
            select(JobFair).where(JobFair.slug == id_or_slug)
        )
    return result.scalar_one_or_none()


async def _save_banner_image(banner_image: UploadFile) -> str:
    """Save a banner image file and return its URL path."""
    from pathlib import Path
    base_dir = Path(settings.UPLOAD_DIR)
    if not base_dir.is_absolute():
        base_dir = Path(__file__).parent.parent / base_dir
    banner_dir = base_dir / "job_fair_banners"
    banner_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(banner_image.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(
            status_code=400,
            detail="Only image files (.jpg, .jpeg, .png, .webp) are allowed for the banner image.",
        )
    safe_name = f"{uuid.uuid4().hex}{ext}"
    banner_path = banner_dir / safe_name
    content = await banner_image.read()
    with open(banner_path, "wb") as f:
        f.write(content)
    return f"/uploads/job_fair_banners/{safe_name}"


# ── SUPER ADMIN CRUD ENDPOINTS ──────────────────────────────────────────────

@router.post("", response_model=JobFairOut, status_code=201)
async def create_job_fair(
    title: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
    description: str = Form(None),
    is_active: bool = Form(True),
    banner_image: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Super Admin: Create a new Job Fair (multipart/form-data, optional banner image)."""
    from datetime import timezone
    banner_url = None
    if banner_image and banner_image.filename:
        banner_url = await _save_banner_image(banner_image)

    slug = await generate_unique_slug(title, db)
    job_fair = JobFair(
        id=str(uuid.uuid4()),
        slug=slug,
        title=title,
        description=description,
        date=datetime.fromisoformat(date).replace(tzinfo=None),
        location=location,
        banner_image_url=banner_url,
        is_active=is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job_fair)
    await db.commit()
    await db.refresh(job_fair)
    return job_fair


@router.put("/{id}", response_model=JobFairOut)
async def update_job_fair(
    id: str,
    body: JobFairUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Super Admin: Update an existing Job Fair."""
    result = await db.execute(select(JobFair).where(JobFair.id == id))
    job_fair = result.scalar_one_or_none()
    if not job_fair:
        raise HTTPException(status_code=404, detail="Job Fair not found")

    update_data = body.model_dump(exclude_unset=True)
    if "title" in update_data and update_data["title"] != job_fair.title:
        # Generate new slug if title changes
        job_fair.slug = await generate_unique_slug(update_data["title"], db)

    if "date" in update_data and update_data["date"] is not None:
        update_data["date"] = update_data["date"].replace(tzinfo=None)

    for key, val in update_data.items():
        setattr(job_fair, key, val)

    job_fair.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job_fair)
    return job_fair


@router.delete("/{id}", status_code=204)
async def delete_job_fair(
    id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Super Admin: Delete a Job Fair."""
    result = await db.execute(select(JobFair).where(JobFair.id == id))
    job_fair = result.scalar_one_or_none()
    if not job_fair:
        raise HTTPException(status_code=404, detail="Job Fair not found")

    await db.delete(job_fair)
    await db.commit()
    return Response(status_code=204)


@router.post("/{id}/upload-banner", response_model=JobFairOut)
async def upload_job_fair_banner(
    id: str,
    banner_image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Super Admin: Upload or replace the banner/poster image for a Job Fair."""
    result = await db.execute(select(JobFair).where(JobFair.id == id))
    job_fair = result.scalar_one_or_none()
    if not job_fair:
        raise HTTPException(status_code=404, detail="Job Fair not found")

    banner_url = await _save_banner_image(banner_image)
    job_fair.banner_image_url = banner_url
    job_fair.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job_fair)
    return job_fair


# ── PUBLIC & AUTHENTICATED USER ENDPOINTS ──────────────────────────────────────

@router.get("", response_model=JobFairListResponse)
async def list_job_fairs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("date_asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
):
    """List all Job Fairs with search, sorting, and pagination (open to all authenticated users)."""
    query = select(JobFair)

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                JobFair.title.ilike(term),
                JobFair.location.ilike(term),
            )
        )

    if sort_by == "date_desc":
        query = query.order_by(JobFair.date.desc())
    elif sort_by == "title_asc":
        query = query.order_by(JobFair.title.asc())
    elif sort_by == "title_desc":
        query = query.order_by(JobFair.title.desc())
    else:
        # Default: date_asc — soonest upcoming first
        query = query.order_by(JobFair.date.asc())

    # Count
    count_query = select(func.count(JobFair.id))
    if search:
        term = f"%{search.strip()}%"
        count_query = count_query.where(
            or_(
                JobFair.title.ilike(term),
                JobFair.location.ilike(term),
            )
        )
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return JobFairListResponse(items=items, total=total, page=page, page_size=page_size)

@router.get("/my-fairs", response_model=List[JobFairOut])
async def get_my_job_fairs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all Job Fairs that the logged-in user (seeker or provider) has registered for."""
    if current_user.role == UserRole.provider:
        result = await db.execute(
            select(JobFair)
            .join(JobFairCompany, JobFair.id == JobFairCompany.job_fair_id)
            .where(JobFairCompany.provider_id == current_user.id)
            .order_by(JobFair.date.desc())
        )
        return result.scalars().all()
    elif current_user.role == UserRole.seeker:
        result = await db.execute(
            select(JobFair)
            .join(JobFairSeeker, JobFair.id == JobFairSeeker.job_fair_id)
            .where(JobFairSeeker.seeker_id == current_user.id)
            .order_by(JobFair.date.desc())
        )
        return result.scalars().all()
    else:
        raise HTTPException(
            status_code=403,
            detail="Only job seekers and providers can view their registered job fairs."
        )



@router.get("/provider/participated", response_model=List[JobFairOut])
async def get_provider_participated_job_fairs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all Job Fairs that the logged-in provider has registered for."""
    if current_user.role != UserRole.provider:
        raise HTTPException(
            status_code=403,
            detail="Only job providers can view participated job fairs."
        )

    result = await db.execute(
        select(JobFair)
        .join(JobFairCompany, JobFair.id == JobFairCompany.job_fair_id)
        .where(JobFairCompany.provider_id == current_user.id)
        .order_by(JobFair.date.desc())
    )
    return result.scalars().all()


@router.get("/{id_or_slug}", response_model=JobFairOut)
async def get_job_fair(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single Job Fair by ID or slug."""
    job_fair = await get_job_fair_by_id_or_slug(id_or_slug, db)
    if not job_fair:
        raise HTTPException(status_code=404, detail="Job Fair not found")
    return job_fair


# ── COMPANY REGISTRATION ENDPOINTS ───────────────────────────────────────────

@router.post("/{id_or_slug}/register-company", status_code=201)
async def register_company_to_job_fair(
    id_or_slug: str,
    company_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    department: str = Form(None),
    sector: str = Form(None),
    vacancy: str = Form(None),
    company_location: str = Form(None),
    company_size: str = Form(None),
    company_address: str = Form(None),
    logo: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Public Endpoint: Self-register a company for a Job Fair.
    If company doesn't exist, create a new Provider user with phone as temporary password.
    """
    # Resolve Job Fair
    jf = await get_job_fair_by_id_or_slug(id_or_slug, db)
    if not jf:
        raise HTTPException(status_code=404, detail="Job Fair not found")

    # Handle logo upload if provided
    logo_url = None
    if logo and logo.filename:
        from pathlib import Path

        base_dir = Path(settings.UPLOAD_DIR)
        if not base_dir.is_absolute():
            base_dir = Path(__file__).parent.parent / base_dir

        logo_dir = base_dir / "company_logos"
        logo_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(logo.filename).suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png"}:
            raise HTTPException(
                status_code=400,
                detail="Only image files (.jpg, .jpeg, .png) are allowed for company logo.",
            )

        safe_name = f"{uuid.uuid4().hex}{ext}"
        logo_path = logo_dir / safe_name

        content = await logo.read()
        with open(logo_path, "wb") as f:
            f.write(content)

        logo_url = f"/uploads/company_logos/{safe_name}"

    # Check if User (provider) exists by email only
    user_result = await db.execute(
        select(User).where(User.email == email)
    )
    user = user_result.scalars().first()

    if not user:
        # Create new provider user
        temp_pwd = phone.strip()
        hashed_pwd = hash_password(temp_pwd)

        user = User(
            id=str(uuid.uuid4()),
            first_name=company_name,
            last_name="",
            email=email,
            phone=phone,
            hashed_password=hashed_pwd,
            role=UserRole.provider,
            company_name=company_name,
            company_type=CompanyType.company,
            profile_pic_url=logo_url,
            company_location=company_location,
            company_size=company_size,
            company_address=company_address,
            is_verified=True,
            onboarding_complete=True,
            totp_secret=totp_service.generate_secret(),
            totp_enabled=False,
            is_first_login=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(user)
        await db.flush()

        # Save ImportedUserPassword
        db_pwd = ImportedUserPassword(
            id=str(uuid.uuid4()),
            user_id=user.id,
            email=email,
            plain_password=temp_pwd,
            created_at=datetime.utcnow(),
        )
        db.add(db_pwd)
        await db.flush()
    else:
        # Update details if missing
        if not user.company_name:
            user.company_name = company_name
        if logo_url and not user.profile_pic_url:
            user.profile_pic_url = logo_url
        if company_location and not user.company_location:
            user.company_location = company_location
        if company_size and not user.company_size:
            user.company_size = company_size
        if company_address and not user.company_address:
            user.company_address = company_address
        if user.role != UserRole.provider:
            # Coerce role to provider if registration was performed as seeker/other
            user.role = UserRole.provider
        await db.flush()

    # Link company user to job fair via JobFairCompany
    jfc_result = await db.execute(
        select(JobFairCompany).where(
            JobFairCompany.job_fair_id == jf.id,
            JobFairCompany.provider_id == user.id,
        )
    )
    jfc = jfc_result.scalar_one_or_none()

    if not jfc:
        jfc = JobFairCompany(
            id=str(uuid.uuid4()),
            job_fair_id=jf.id,
            provider_id=user.id,
            department=department,
            sector=sector,
            vacancy=vacancy,
            registered_at=datetime.utcnow(),
        )
        db.add(jfc)
    else:
        # Update vacancy and details
        jfc.department = department or jfc.department
        jfc.sector = sector or jfc.sector
        jfc.vacancy = vacancy or jfc.vacancy

    await db.commit()
    return {"status": "success", "message": "Company registered successfully"}


# ── QR CODE GENERATION ───────────────────────────────────────────────────────

@router.get("/{id_or_slug}/qrcode")
async def get_job_fair_qrcode(
    id_or_slug: str,
    type: str = "company",
    db: AsyncSession = Depends(get_db),
):
    """Get the QR Code image for the company or student registration form."""
    jf = await get_job_fair_by_id_or_slug(id_or_slug, db)
    if not jf:
        raise HTTPException(status_code=404, detail="Job Fair not found")

    # The registration form link in the frontend
    if type == "student":
        url = f"{settings.FRONTEND_URL}/job-fair/{jf.slug}/apply-student"
    else:
        url = f"{settings.FRONTEND_URL}/job-fair/{jf.slug}/register-company"

    # Generate QR Code using PIL
    import qrcode
    from io import BytesIO

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()

    return Response(content=img_bytes, media_type="image/png")


# ── ORGANIZER REGISTRANT LISTS ────────────────────────────────────────────────

@router.get("/{id_or_slug}/companies", response_model=JobFairCompanyListResponse)
async def get_job_fair_companies(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("date_newest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
):
    """Get registered companies for a Job Fair with search, filtering, sorting, and pagination."""
    jf = await get_job_fair_by_id_or_slug(id_or_slug, db)
    if not jf:
        raise HTTPException(status_code=404, detail="Job Fair not found")

    query = (
        select(JobFairCompany, User)
        .join(User, JobFairCompany.provider_id == User.id)
        .where(JobFairCompany.job_fair_id == jf.id)
    )

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.company_name.ilike(term),
                User.first_name.ilike(term),
                User.email.ilike(term),
                User.phone.ilike(term),
            )
        )

    if sector and sector != "all":
        query = query.where(JobFairCompany.sector == sector)

    if sort_by == "name_asc":
        query = query.order_by(func.coalesce(User.company_name, User.first_name).asc())
    elif sort_by == "name_desc":
        query = query.order_by(func.coalesce(User.company_name, User.first_name).desc())
    elif sort_by == "date_oldest":
        query = query.order_by(JobFairCompany.registered_at.asc())
    else:
        query = query.order_by(JobFairCompany.registered_at.desc())

    # Count query
    count_query = (
        select(func.count(JobFairCompany.id))
        .join(User, JobFairCompany.provider_id == User.id)
        .where(JobFairCompany.job_fair_id == jf.id)
    )
    if search:
        term = f"%{search.strip()}%"
        count_query = count_query.where(
            or_(
                User.company_name.ilike(term),
                User.first_name.ilike(term),
                User.email.ilike(term),
                User.phone.ilike(term),
            )
        )
    if sector and sector != "all":
        count_query = count_query.where(JobFairCompany.sector == sector)

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)

    out = []
    for jfc, provider in result.all():
        out.append(
            JobFairCompanyOut(
                id=jfc.id,
                job_fair_id=jfc.job_fair_id,
                provider_id=jfc.provider_id,
                department=jfc.department,
                sector=jfc.sector,
                vacancy=jfc.vacancy,
                registered_at=jfc.registered_at,
                company_name=provider.company_name or provider.first_name,
                email=provider.email,
                phone=provider.phone,
                profile_pic_url=provider.profile_pic_url,
            )
        )
    return JobFairCompanyListResponse(items=out, total=total, page=page, page_size=page_size)


@router.get("/{id_or_slug}/seekers", response_model=JobFairSeekerListResponse)
async def get_job_fair_seekers(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = Query(None),
    resume: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("date_newest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
):
    """Get registered student/seeker attendees for a Job Fair with search, filtering, sorting, and pagination."""
    jf = await get_job_fair_by_id_or_slug(id_or_slug, db)
    if not jf:
        raise HTTPException(status_code=404, detail="Job Fair not found")

    query = (
        select(JobFairSeeker, User)
        .join(User, JobFairSeeker.seeker_id == User.id)
        .where(JobFairSeeker.job_fair_id == jf.id)
    )

    from models.resume import Resume

    if search:
        term = f"%{search.strip()}%"
        full_name_expr = func.concat(
            func.coalesce(User.first_name, ""),
            " ",
            func.coalesce(User.last_name, ""),
        )
        query = query.where(
            or_(
                User.first_name.ilike(term),
                User.last_name.ilike(term),
                full_name_expr.ilike(term),
                User.email.ilike(term),
                User.phone.ilike(term),
            )
        )

    if resume == "with_resume":
        query = query.where(exists().where(Resume.user_id == User.id))
    elif resume == "no_resume":
        query = query.where(~exists().where(Resume.user_id == User.id))

    if sort_by == "name_asc":
        query = query.order_by(func.concat(func.coalesce(User.first_name, ""), " ", func.coalesce(User.last_name, "")).asc())
    elif sort_by == "name_desc":
        query = query.order_by(func.concat(func.coalesce(User.first_name, ""), " ", func.coalesce(User.last_name, "")).desc())
    elif sort_by == "date_oldest":
        query = query.order_by(JobFairSeeker.registered_at.asc())
    else:
        query = query.order_by(JobFairSeeker.registered_at.desc())

    # Count query
    count_query = (
        select(func.count(JobFairSeeker.id))
        .join(User, JobFairSeeker.seeker_id == User.id)
        .where(JobFairSeeker.job_fair_id == jf.id)
    )
    if search:
        term = f"%{search.strip()}%"
        full_name_expr = func.concat(
            func.coalesce(User.first_name, ""),
            " ",
            func.coalesce(User.last_name, ""),
        )
        count_query = count_query.where(
            or_(
                User.first_name.ilike(term),
                User.last_name.ilike(term),
                full_name_expr.ilike(term),
                User.email.ilike(term),
                User.phone.ilike(term),
            )
        )
    if resume == "with_resume":
        count_query = count_query.where(exists().where(Resume.user_id == User.id))
    elif resume == "no_resume":
        count_query = count_query.where(~exists().where(Resume.user_id == User.id))

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)

    out = []
    for jfs, seeker in result.all():
        resume_res = await db.execute(
            select(Resume)
            .where(Resume.user_id == seeker.id)
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
        resume_db = resume_res.scalar_one_or_none()
        resume_url = f"/api/resumes/{seeker.id}/download" if resume_db else None

        out.append(
            JobFairSeekerOut(
                id=jfs.id,
                job_fair_id=jfs.job_fair_id,
                seeker_id=jfs.seeker_id,
                is_attending=jfs.is_attending,
                registered_at=jfs.registered_at,
                seeker_first_name=seeker.first_name,
                seeker_last_name=seeker.last_name,
                seeker_email=seeker.email,
                seeker_phone=seeker.phone,
                seeker_resume_url=resume_url,
            )
        )
    return JobFairSeekerListResponse(items=out, total=total, page=page, page_size=page_size)


@router.get("/{id_or_slug}/companies/sectors", response_model=List[str])
async def get_job_fair_company_sectors(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all unique sectors of registered companies for a Job Fair."""
    jf = await get_job_fair_by_id_or_slug(id_or_slug, db)
    if not jf:
        raise HTTPException(status_code=404, detail="Job Fair not found")

    result = await db.execute(
        select(JobFairCompany.sector)
        .where(JobFairCompany.job_fair_id == jf.id, JobFairCompany.sector.isnot(None))
        .distinct()
    )
    return [row[0] for row in result.all()]

