import os
import uuid
import asyncio
from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.portfolio import Portfolio
from models.user import User, UserRole, JobType, CompanyType
from schemas.auth import UserOut, OnboardingRequest, UpdateSettingsRequest, UpdateSettingsResponse
from services.email_service import send_welcome_email
from services.totp_service import totp_service


async def get_me(user: User) -> UserOut:
    return UserOut.model_validate(user)


async def complete_onboarding(
    body: OnboardingRequest,
    background_tasks: BackgroundTasks,
    user: User,
    db: AsyncSession,
) -> UserOut:
    try:
        user.role = UserRole(body.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'seeker' or 'provider'")

    user.industry = body.industry
    user.job_role = body.job_role
    user.company_name = body.company_name

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
        user.preferred_locations = body.preferred_locations[:5]

    user.onboarding_complete = True
    await db.commit()
    await db.refresh(user)

    if user.role == UserRole.seeker:
        res = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id))
        if not res.scalar_one_or_none():
            db.add(Portfolio(user_id=user.id))
            await db.commit()

    background_tasks.add_task(send_welcome_email, user.email, user.first_name, body.role)

    if user.role == UserRole.seeker:
        from services.seeker_matching_service import invalidate_seeker_matches
        background_tasks.add_task(invalidate_seeker_matches, str(user.id))

    return UserOut.model_validate(user)


async def update_settings(
    body: UpdateSettingsRequest,
    background_tasks: BackgroundTasks,
    user: User,
    db: AsyncSession,
) -> UpdateSettingsResponse:
    uniqueness_checks = []
    if body.email and body.email != user.email:
        uniqueness_checks.append(
            db.execute(select(User.id).where(User.email == body.email).limit(1))
        )
    if body.phone and body.phone != user.phone:
        uniqueness_checks.append(
            db.execute(select(User.id).where(User.phone == body.phone).limit(1))
        )

    if uniqueness_checks:
        results = await asyncio.gather(*uniqueness_checks)
        check_idx = 0
        if body.email and body.email != user.email:
            if results[check_idx].scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Email already in use")
            check_idx += 1
        if body.phone and body.phone != user.phone:
            if results[check_idx].scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Phone number already in use")

    seeker_match_fields_changed = user.role == UserRole.seeker and any(
        getattr(body, field) is not None
        for field in ("industry", "job_role", "salary_range", "job_type", "preferred_locations")
    )

    if body.first_name is not None:
        user.first_name = body.first_name
    if body.last_name is not None:
        user.last_name = body.last_name
    if body.email is not None:
        user.email = body.email

    new_qr_code = None
    if body.phone is not None and body.phone != user.phone:
        user.phone = body.phone
        user.totp_secret = totp_service.generate_secret()
        user.totp_enabled = False
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
    if body.company_type is not None:
        try:
            user.company_type = CompanyType(body.company_type) if body.company_type else None
        except ValueError:
            pass
    if body.company_size is not None:
        user.company_size = body.company_size or None
    if body.preferred_locations is not None:
        user.preferred_locations = body.preferred_locations[:5]
    if body.job_type is not None:
        try:
            user.job_type = JobType(body.job_type)
        except ValueError:
            pass

    await db.commit()

    if user.role == UserRole.seeker and seeker_match_fields_changed:
        from services.seeker_matching_service import invalidate_seeker_matches
        background_tasks.add_task(invalidate_seeker_matches, str(user.id))

    response_data = UpdateSettingsResponse.model_validate(user)
    if new_qr_code:
        response_data.new_totp_qr_code = new_qr_code
    return response_data


async def upload_profile_pic(file: UploadFile, user: User, db: AsyncSession) -> UserOut:
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    ext = os.path.splitext(file.filename)[1]
    filename = f"profile_{user.id}_{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    user.profile_pic_url = f"/uploads/{filename}"
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


async def get_public_user(user_id: str, db: AsyncSession) -> UserOut:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    res = await db.execute(select(User).where(User.id == uid))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)
