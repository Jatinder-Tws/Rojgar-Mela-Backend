from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import os
import uuid
from pathlib import Path

from config import settings
from database import get_db
from models.user import User, UserRole, JobType, CompanyType
from schemas.auth import UserOut, OnboardingRequest, UpdateSettingsRequest, UpdateSettingsResponse
from services.auth_service import require_verified, get_current_user
from services.email_service import send_welcome_email
from services.totp_service import totp_service
from models.portfolio import Portfolio

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.patch("/me/onboarding", response_model=UserOut)
async def complete_onboarding(
    body: OnboardingRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    try:
        user.role = UserRole(body.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'seeker' or 'provider'")

    user.industry = body.industry
    user.job_role = body.job_role
    user.company_name = body.company_name

    # Basic Info
    if body.first_name:
        user.first_name = body.first_name
    if body.last_name:
        user.last_name = body.last_name
    if body.email:
        user.email = body.email

    if body.experience:
        user.experience = body.experience
    if body.company_size:
        user.company_size = body.company_size

    if body.job_type:
        try:
            user.job_type = JobType(body.job_type)
        except ValueError:
            pass

    if body.salary_range:
        user.salary_range = body.salary_range

    if body.company_type:
        try:
            user.company_type = CompanyType(body.company_type)
        except ValueError:
            pass

    if body.company_location:
        user.company_location = body.company_location

    if body.company_address:
        user.company_address = body.company_address

    if body.preferred_locations:
        user.preferred_locations = body.preferred_locations[:5]  # max 5

    user.onboarding_complete = True
    await db.commit()
    await db.refresh(user)

    # Auto-create portfolio for seekers if not exists
    if user.role == UserRole.seeker:
        res = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id))
        if not res.scalar_one_or_none():
            db.add(Portfolio(user_id=user.id))
            await db.commit()

    # Trigger welcome email
    background_tasks.add_task(send_welcome_email, user.email, user.first_name, body.role)

    # Trigger AI matching if seeker already has a resume
    if user.role == UserRole.seeker:
        from services.seeker_matching_service import invalidate_seeker_matches
        background_tasks.add_task(invalidate_seeker_matches, str(user.id))

    return UserOut.model_validate(user)


@router.patch("/me/settings", response_model=UpdateSettingsResponse)
async def update_settings(
    body: UpdateSettingsRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    # Check uniqueness if email or phone is changing
    if body.email and body.email != user.email:
        exist_email = await db.execute(select(User).where(User.email == body.email))
        if exist_email.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")

    if body.phone and body.phone != user.phone:
        exist_phone = await db.execute(select(User).where(User.phone == body.phone))
        if exist_phone.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Phone number already in use")

    # Base profile fields
    if body.first_name is not None:
        user.first_name = body.first_name
    if body.last_name is not None:
        user.last_name = body.last_name
    if body.email is not None:
        user.email = body.email

    # Track if phone changed
    new_qr_code = None
    if body.phone is not None and body.phone != user.phone:
        user.phone = body.phone
        # Regenerate TOTP
        user.totp_secret = totp_service.generate_secret()
        user.totp_enabled = False # Require setup/verification again
        uri = totp_service.get_provisioning_uri(user.phone, user.totp_secret)
        new_qr_code = totp_service.generate_qr_base64(uri)

    if body.auto_apply_enabled is not None:
        user.auto_apply_enabled = body.auto_apply_enabled
    if body.industry is not None:
        user.industry = body.industry
    if body.job_role is not None:
        user.job_role = body.job_role
    if body.salary_range is not None:
        user.salary_range = body.salary_range
    if body.company_name is not None:
        user.company_name = body.company_name
    if body.company_location is not None:
        user.company_location = body.company_location
    if body.company_address is not None:
        user.company_address = body.company_address
    if body.preferred_locations is not None:
        user.preferred_locations = body.preferred_locations[:5]
    if body.job_type is not None:
        try:
            user.job_type = JobType(body.job_type)
        except ValueError:
            pass

    await db.commit()
    await db.refresh(user)

    # Re-run matching when profile fields change
    if user.role == UserRole.seeker:
        from services.seeker_matching_service import invalidate_seeker_matches
        background_tasks.add_task(invalidate_seeker_matches, str(user.id))
    elif user.role == UserRole.provider:
        # Re-match all active jobs for this provider
        from models.job import JobPosting
        from services.seeker_matching_service import invalidate_job_matches
        jobs_result = await db.execute(
            select(JobPosting).where(JobPosting.provider_id == user.id, JobPosting.is_active == True)
        )
        for job in jobs_result.scalars().all():
            background_tasks.add_task(invalidate_job_matches, str(job.id))

    # Prepare Response
    response_data = UpdateSettingsResponse.model_validate(user)
    if new_qr_code:
        response_data.new_totp_qr_code = new_qr_code

    return response_data


@router.post("/me/profile-pic", response_model=UserOut)
async def upload_profile_pic(
    file: UploadFile = File(...),
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Create unique filename
    ext = os.path.splitext(file.filename)[1]
    filename = f"profile_{user.id}_{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    # Save file
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

    # Update user record
    # If old pic exists, maybe delete it later (optional)
    user.profile_pic_url = f"/api/uploads/{filename}"
    await db.commit()
    await db.refresh(user)

    return UserOut.model_validate(user)
