import re
import uuid
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status, Query
from fastapi.responses import Response
from sqlalchemy import select, or_, and_, func, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings, get_upload_dir
from app.core.database import get_db
from app.modules.jobs_portal.models.job_fair import JobFairCompany, JobFairSeeker
from app.shared.models.notification import NotificationType
from app.shared.models.user import User, UserRole, CompanyType
from app.shared.models.imported_user_password import ImportedUserPassword
from app.modules.jobs_portal.schemas.job_fair import (
    JobFairCreate,
    JobFairUpdate,
    JobFairOut,
    JobFairListResponse,
    JobFairCompanyOut,
    JobFairSeekerOut,
    JobFairCompanyListResponse,
    JobFairCompanyPublicOut,
    JobFairCompanyPublicListResponse,
    JobFairSeekerListResponse,
    JobFairPublicOut,
    JobFairPublicCatalogResponse,
)
from app.core.dependencies import (
    get_current_user,
    hash_password,
    require_super_admin,
    generate_secure_password,
)
from app.shared.services.totp_service import totp_service
from app.shared.services.email_service import send_job_fair_welcome_email
from app.modules.jobs_portal.services.job_fair_db import (
    get_job_fair_db,
    list_job_fairs_db,
    list_job_fairs_for_ids_db,
    list_public_job_fairs_catalog,
    get_public_job_fair_db,
    slug_exists_db,
    create_job_fair_db,
    update_job_fair_db,
    set_job_fair_banner_db,
    delete_job_fair_db,
)

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
    while await slug_exists_db(db, slug):
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


async def get_job_fair_by_id_or_slug(id_or_slug: str, db: AsyncSession) -> JobFairOut | None:
    return await get_job_fair_db(db, id_or_slug)


async def _save_banner_image(banner_image: UploadFile) -> str:
    """Save a banner image file and return its URL path."""
    from pathlib import Path
    base_dir = get_upload_dir()
    if not base_dir.is_absolute():
        base_dir = get_upload_dir()
    banner_dir = base_dir / "job_fair_banners"
    banner_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(banner_image.filename or "").suffix.lower().strip()
    if not ext and banner_image.content_type:
        ct = banner_image.content_type.lower()
        if "jpeg" in ct or "jpg" in ct:
            ext = ".jpeg"
        elif "png" in ct:
            ext = ".png"
        elif "webp" in ct:
            ext = ".webp"
        elif "gif" in ct:
            ext = ".gif"
        elif "svg" in ct:
            ext = ".svg"

    allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".jfif", ".pjpeg", ".pjp", ".svg"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail="Only image files (.jpg, .jpeg, .png, .webp, .svg, .gif) are allowed for the banner image.",
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
    industries: str = Form(None),
    banner_image: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Super Admin: Create a new Job Fair (multipart/form-data, optional banner image)."""
    import json as _json

    if len(title) > 200:
        raise HTTPException(
            status_code=400,
            detail="Title cannot exceed 200 characters. Please enter a shorter title to continue.",
        )

    banner_url = None
    if banner_image and banner_image.filename:
        banner_url = await _save_banner_image(banner_image)

    slug = await generate_unique_slug(title, db)
    industries_list = None
    if industries:
        try:
            parsed = _json.loads(industries)
            if isinstance(parsed, list):
                industries_list = parsed
        except _json.JSONDecodeError:
            pass

    fair_date = datetime.fromisoformat(date.replace("Z", "+00:00")).replace(tzinfo=None)
    if fair_date < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Job fair date cannot be in the past")
    return await create_job_fair_db(
        db,
        title=title,
        description=description,
        fair_date=fair_date,
        location=location,
        is_active=is_active,
        slug=slug,
        banner_image_url=banner_url,
        industries=industries_list,
        created_by_id=admin.id,
    )


@router.put("/{id}", response_model=JobFairOut)
async def update_job_fair(
    id: str,
    body: JobFairUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Super Admin: Update an existing Job Fair."""
    existing = await get_job_fair_db(db, id)
    if not existing:
        raise HTTPException(status_code=404, detail="Job Fair not found")

    update_data = body.model_dump(exclude_unset=True)
    if update_data.get("title") and len(update_data["title"]) > 200:
        raise HTTPException(
            status_code=400,
            detail="Title cannot exceed 200 characters. Please enter a shorter title to continue.",
        )
    new_slug = None
    if "title" in update_data and update_data["title"] != existing.title:
        new_slug = await generate_unique_slug(update_data["title"], db)

    fair_date = None
    if "date" in update_data and update_data["date"] is not None:
        fair_date = update_data["date"].replace(tzinfo=None)

    updated = await update_job_fair_db(
        db,
        id,
        title=update_data.get("title"),
        description=update_data.get("description"),
        fair_date=fair_date,
        location=update_data.get("location"),
        is_active=update_data.get("is_active"),
        slug=new_slug,
        banner_image_url=update_data.get("banner_image_url"),
        industries=update_data.get("industries"),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Job Fair not found")
    return updated


@router.delete("/{id}", status_code=204)
async def delete_job_fair(
    id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Super Admin: Delete a Job Fair."""
    if not await delete_job_fair_db(db, id):
        raise HTTPException(status_code=404, detail="Job Fair not found")
    return Response(status_code=204)


@router.post("/{id}/upload-banner", response_model=JobFairOut)
async def upload_job_fair_banner(
    id: str,
    banner_image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Super Admin: Upload or replace the banner/poster image for a Job Fair."""
    existing = await get_job_fair_db(db, id)
    if not existing:
        raise HTTPException(status_code=404, detail="Job Fair not found")

    banner_url = await _save_banner_image(banner_image)
    updated = await set_job_fair_banner_db(db, id, banner_url)
    if not updated:
        raise HTTPException(status_code=404, detail="Job Fair not found")
    return updated


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
    items, total = await list_job_fairs_db(
        db, search=search, sort_by=sort_by or "date_asc", page=page, page_size=page_size
    )
    return JobFairListResponse(items=items, total=total, page=page, page_size=page_size)

@router.get("/my-fairs", response_model=List[JobFairOut])
async def get_my_job_fairs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all Job Fairs that the logged-in user (seeker or provider) has registered for."""
    if current_user.role == UserRole.provider:
        result = await db.execute(
            select(JobFairCompany.job_fair_id)
            .where(JobFairCompany.provider_id == current_user.id)
        )
        fair_ids = [str(row[0]) for row in result.fetchall()]
        return await list_job_fairs_for_ids_db(db, fair_ids)
    elif current_user.role == UserRole.seeker:
        result = await db.execute(
            select(JobFairSeeker.job_fair_id)
            .where(JobFairSeeker.seeker_id == current_user.id)
        )
        fair_ids = [str(row[0]) for row in result.fetchall()]
        return await list_job_fairs_for_ids_db(db, fair_ids)
    else:
        raise HTTPException(
            status_code=403,
            detail="Only job seekers and providers can view their registered job fairs."
        )



@router.get("/public", response_model=JobFairPublicCatalogResponse)
async def list_job_fairs_public(
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None),
):
    """Public catalog of job fairs. No authentication required."""
    return await list_public_job_fairs_catalog(db, search=search)


@router.get("/public/{id_or_slug}", response_model=JobFairPublicOut)
async def get_job_fair_public(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Public job fair detail with participation stats. No authentication required."""
    job_fair = await get_public_job_fair_db(db, id_or_slug)
    if not job_fair:
        raise HTTPException(status_code=404, detail="Job Fair not found")
    return job_fair


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
        select(JobFairCompany.job_fair_id)
        .where(JobFairCompany.provider_id == current_user.id)
    )
    fair_ids = [str(row[0]) for row in result.fetchall()]
    return await list_job_fairs_for_ids_db(db, fair_ids)


@router.get("/{id_or_slug}", response_model=JobFairOut)
async def get_job_fair(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
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
    background_tasks: BackgroundTasks,
    company_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    department: str = Form(None),
    sector: str = Form(None),
    job_category: str = Form(None),
    vacancy: str = Form(None),
    company_location: str = Form(None),
    company_size: str = Form(None),
    company_address: str = Form(None),
    website: str = Form(None),
    state: str = Form(None),
    city: str = Form(None),
    contact_person_name: str = Form(None),
    contact_person_designation: str = Form(None),
    contact_person_phone: str = Form(None),
    openings: str = Form(None),
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

        base_dir = get_upload_dir()
        if not base_dir.is_absolute():
            base_dir = get_upload_dir()

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

    import json as _json

    # Resolve location from state/city if provided
    resolved_location = company_location
    if city or state:
        parts = [p for p in [city, state] if p and p.strip()]
        if parts:
            resolved_location = ", ".join(parts)

    # Parse multiple openings JSON if provided
    parsed_openings = []
    if openings:
        try:
            parsed_openings = _json.loads(openings)
            if not isinstance(parsed_openings, list):
                parsed_openings = []
        except (ValueError, TypeError):
            parsed_openings = []

    if parsed_openings:
        dept_parts = [o.get("department", "").strip() for o in parsed_openings if o.get("department")]
        vac_parts = [str(o.get("vacancy", "")).strip() for o in parsed_openings if o.get("vacancy")]
        if dept_parts and not department:
            department = ", ".join(dept_parts)
        if vac_parts and not vacancy:
            vacancy = ", ".join(vac_parts)

    extra_meta = {}
    if website and website.strip():
        extra_meta["website"] = website.strip()
    if job_category and job_category.strip():
        extra_meta["job_category"] = job_category.strip()
    if contact_person_name and contact_person_name.strip():
        extra_meta["contact_person_name"] = contact_person_name.strip()
    if contact_person_designation and contact_person_designation.strip():
        extra_meta["contact_person_designation"] = contact_person_designation.strip()
    if contact_person_phone and contact_person_phone.strip():
        extra_meta["contact_person_phone"] = contact_person_phone.strip()
    if parsed_openings:
        extra_meta["openings"] = parsed_openings
    extra_meta_json = _json.dumps(extra_meta) if extra_meta else None

    # Check if User (provider) exists by email only
    user_result = await db.execute(
        select(User).where(User.email == email)
    )
    user = user_result.scalars().first()

    if not user:
        # Create new provider user
        temp_pwd = generate_secure_password()
        hashed_pwd = hash_password(temp_pwd)

        user = User(
            id=str(uuid.uuid4()),
            first_name=(contact_person_name or company_name).strip(),
            last_name="",
            email=email,
            phone=phone,
            hashed_password=hashed_pwd,
            role=UserRole.provider,
            company_name=company_name,
            company_type=CompanyType.company,
            industry=sector,
            job_role=contact_person_designation,
            profile_pic_url=logo_url,
            company_location=resolved_location,
            company_size=company_size,
            company_address=company_address,
            job_roles_offering=_json.dumps(parsed_openings) if parsed_openings else None,
            specific_requirements=extra_meta_json,
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

        background_tasks.add_task(
            send_job_fair_welcome_email,
            email,
            (contact_person_name or company_name).strip(),
            temp_pwd,
            f"{settings.FRONTEND_URL.rstrip('/')}/login",
            job_fair=jf,
            role="provider",
        )
    else:
        # Update details if missing
        if not user.company_name:
            user.company_name = company_name
        if logo_url and not user.profile_pic_url:
            user.profile_pic_url = logo_url
        if resolved_location and not user.company_location:
            user.company_location = resolved_location
        if company_size and not user.company_size:
            user.company_size = company_size
        if company_address and not user.company_address:
            user.company_address = company_address
        if sector and not user.industry:
            user.industry = sector
        if contact_person_designation and not user.job_role:
            user.job_role = contact_person_designation
        if parsed_openings and not user.job_roles_offering:
            user.job_roles_offering = _json.dumps(parsed_openings)
        if extra_meta_json and not user.specific_requirements:
            user.specific_requirements = extra_meta_json
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
    is_new_registration = False

    if not jfc:
        is_new_registration = True
        jfc = JobFairCompany(
            id=str(uuid.uuid4()),
            job_fair_id=jf.id,
            provider_id=user.id,
            department=department,
            sector=sector,
            vacancy=vacancy,
            registered_at=datetime.utcnow(),
            company_name=company_name,
            email=email,
            phone=phone,
            website=website,
            company_size=company_size,
            company_address=company_address,
            contact_person_name=contact_person_name,
            contact_person_designation=contact_person_designation,
            contact_person_phone=contact_person_phone,
            openings=parsed_openings,
            logo_url=logo_url,
            state=state,
            city=city,
        )
        db.add(jfc)
    else:
        # Update vacancy and details
        jfc.department = department or jfc.department
        jfc.sector = sector or jfc.sector
        jfc.vacancy = vacancy or jfc.vacancy
        jfc.company_name = company_name or jfc.company_name
        jfc.email = email or jfc.email
        jfc.phone = phone or jfc.phone
        jfc.website = website or jfc.website
        jfc.company_size = company_size or jfc.company_size
        jfc.company_address = company_address or jfc.company_address
        jfc.contact_person_name = contact_person_name or jfc.contact_person_name
        jfc.contact_person_designation = contact_person_designation or jfc.contact_person_designation
        jfc.contact_person_phone = contact_person_phone or jfc.contact_person_phone
        jfc.openings = parsed_openings if parsed_openings else jfc.openings
        jfc.logo_url = logo_url or jfc.logo_url
        jfc.state = state or jfc.state
        jfc.city = city or jfc.city

    await db.commit()

    if is_new_registration:
        from app.shared.services.notification_service import notify_super_admins
        await notify_super_admins(
            db,
            title="New Job Fair Registration",
            message=f"{company_name} registered for {jf.title}.",
            type=NotificationType.application,
            related_job_id=str(jf.id),
            related_user_id=str(user.id),
        )

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

    from app.modules.jobs_portal.services.job_fair_qr_service import generate_job_fair_qr_poster

    portal_label = "Student Registration" if type == "student" else "Employer Registration"
    headline = f"{jf.title} — {portal_label}"
    img_bytes = generate_job_fair_qr_poster(url, headline=headline)

    return Response(content=img_bytes, media_type="image/png")


# ── ORGANIZER REGISTRANT LISTS ────────────────────────────────────────────────

@router.get("/{id_or_slug}/companies/public", response_model=JobFairCompanyPublicListResponse)
async def get_job_fair_companies_public(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """Public preview of registered companies (no contact details)."""
    jf = await get_job_fair_by_id_or_slug(id_or_slug, db)
    if not jf:
        raise HTTPException(status_code=404, detail="Job Fair not found")

    count_res = await db.execute(
        select(func.count(JobFairCompany.id)).where(JobFairCompany.job_fair_id == jf.id)
    )
    total = count_res.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(JobFairCompany, User)
        .join(User, JobFairCompany.provider_id == User.id)
        .where(JobFairCompany.job_fair_id == jf.id)
        .order_by(JobFairCompany.registered_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    items = [
        JobFairCompanyPublicOut(
            id=jfc.id,
            company_name=jfc.company_name or provider.company_name or provider.first_name,
            profile_pic_url=jfc.logo_url or provider.profile_pic_url,
            sector=jfc.sector,
            vacancy=jfc.vacancy,
        )
        for jfc, provider in result.all()
    ]
    return JobFairCompanyPublicListResponse(items=items, total=total, page=page, page_size=page_size)


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
                company_name=jfc.company_name or provider.company_name or provider.first_name,
                email=jfc.email or provider.email,
                phone=jfc.phone or provider.phone,
                profile_pic_url=jfc.logo_url or provider.profile_pic_url,
                website=jfc.website,
                company_size=jfc.company_size,
                company_address=jfc.company_address,
                contact_person_name=jfc.contact_person_name,
                contact_person_designation=jfc.contact_person_designation,
                contact_person_phone=jfc.contact_person_phone,
                openings=jfc.openings,
                state=jfc.state,
                city=jfc.city,
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
    industry: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("date_newest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
):
    """Get registered student/seeker attendees for a Job Fair with search, filtering, sorting, and pagination."""
    jf = await get_job_fair_by_id_or_slug(id_or_slug, db)
    if not jf:
        raise HTTPException(status_code=404, detail="Job Fair not found")

    is_admin = current_user.is_super_admin or current_user.role == UserRole.superadmin or (
        hasattr(current_user.role, "value") and current_user.role.value == "superadmin"
    )
    if not is_admin:
        if current_user.role == UserRole.provider:
            # Check if provider is registered
            jfc_exists = await db.execute(
                select(exists().where(
                    and_(
                        JobFairCompany.job_fair_id == jf.id,
                        JobFairCompany.provider_id == current_user.id
                    )
                ))
            )
            if not jfc_exists.scalar():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You must be registered for this Job Fair to view candidates."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view candidates for this Job Fair."
            )


    query = (
        select(JobFairSeeker, User)
        .join(User, JobFairSeeker.seeker_id == User.id)
        .where(JobFairSeeker.job_fair_id == jf.id)
    )

    from app.modules.jobs_portal.models.resume import Resume

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

    if industry:
        from app.modules.jobs_portal.models.external_candidate import ExternalCandidate
        from sqlalchemy import String
        query = query.where(
            exists().where(
                and_(
                    ExternalCandidate.email == User.email,
                    func.cast(ExternalCandidate.industries, String).ilike(f"%{industry.strip()}%")
                )
            )
        )

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

    if industry:
        from app.modules.jobs_portal.models.external_candidate import ExternalCandidate
        from sqlalchemy import String
        count_query = count_query.where(
            exists().where(
                and_(
                    ExternalCandidate.email == User.email,
                    func.cast(ExternalCandidate.industries, String).ilike(f"%{industry.strip()}%")
                )
            )
        )

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

        # Fetch candidate details
        from app.modules.jobs_portal.models.external_candidate import ExternalCandidate
        cand_res = await db.execute(
            select(ExternalCandidate)
            .where(ExternalCandidate.email == seeker.email)
            .order_by(ExternalCandidate.applied_at.desc())
            .limit(1)
        )
        cand = cand_res.scalar_one_or_none()

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
                seeker_resume_url=resume_url or (cand.resume_url if cand else None),
                seeker_gender=cand.gender if cand else None,
                seeker_date_of_birth=cand.date_of_birth if cand else None,
                seeker_state=cand.state if cand else None,
                seeker_city=cand.city if cand else None,
                seeker_sub_role=cand.sub_role if cand else None,
                seeker_industries=cand.industries if cand else None,
                seeker_available_shift=cand.available_shift if cand else None,
                seeker_total_experience=cand.total_experience if cand else None,
                seeker_current_ctc=cand.current_ctc if cand else None,
                seeker_source=cand.source if cand else None,
                seeker_current_designation=cand.current_designation if cand else None,
                seeker_profile_picture_url=cand.profile_picture_url if cand else None,
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

