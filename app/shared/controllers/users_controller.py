import os
import uuid
from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.config import settings, get_upload_dir
from app.modules.jobs_portal.models.portfolio import Portfolio
from app.shared.models.user import User, UserRole, JobType, CompanyType
from app.shared.schemas.auth import UserOut, OnboardingRequest, UpdateSettingsRequest, UpdateSettingsResponse
from app.shared.services.email_service import send_welcome_email
from app.shared.services.totp_service import totp_service


async def get_me(user: User, db: Optional[AsyncSession] = None) -> UserOut:
    out = UserOut.model_validate(user)
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role or "")
    if role_str == "supervisor":
        cached_profile = getattr(user, "_supervisor_profile", None)
        if cached_profile:
            out.permissions = cached_profile.permissions or []
        elif db:
            from app.shared.models.supervisor_profile import SupervisorProfile
            res = await db.execute(select(SupervisorProfile).where(SupervisorProfile.user_id == user.id))
            profile = res.scalar_one_or_none()
            if profile:
                out.permissions = profile.permissions or []
    return out


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

    from app.shared.services.celery_tasks import send_welcome_email_task, invalidate_seeker_matches_task
    send_welcome_email_task.delay(user.email, user.first_name or "", str(body.role))

    if user.role == UserRole.seeker:
        invalidate_seeker_matches_task.delay(str(user.id))

    return UserOut.model_validate(user)


def _phone_key(value: Optional[str]) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


async def phone_is_available(phone: str, user: User, db: AsyncSession) -> bool:
    incoming_key = _phone_key(phone)
    if len(incoming_key) != 10:
        raise HTTPException(status_code=400, detail="Phone number must be exactly 10 digits")
    if incoming_key == _phone_key(user.phone):
        return True
    taken_phone = await db.execute(
        select(User.id).where(
            User.id != user.id,
            User.phone.isnot(None),
            or_(User.phone == incoming_key, User.phone.like(f"%{incoming_key}")),
        ).limit(1)
    )
    return taken_phone.scalar_one_or_none() is None


async def update_settings(
    body: UpdateSettingsRequest,
    background_tasks: BackgroundTasks,
    user: User,
    db: AsyncSession,
) -> UpdateSettingsResponse:
    phone_to_apply: Optional[str] = None
    if body.email and body.email != user.email:
        taken_email = await db.execute(
            select(User.id).where(User.email == body.email, User.id != user.id).limit(1)
        )
        if taken_email.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")

    if body.phone:
        incoming_key = _phone_key(body.phone)
        current_key = _phone_key(user.phone)
        if incoming_key and incoming_key == current_key:
            phone_to_apply = None
        elif len(incoming_key) != 10:
            raise HTTPException(status_code=400, detail="Phone number must be exactly 10 digits")
        else:
            taken_phone = await db.execute(
                select(User.id).where(
                    User.id != user.id,
                    User.phone.isnot(None),
                    or_(User.phone == incoming_key, User.phone.like(f"%{incoming_key}")),
                ).limit(1)
            )
            if taken_phone.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="This phone number is already registered.")
            phone_to_apply = incoming_key

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
    if phone_to_apply and phone_to_apply != _phone_key(user.phone):
        had_totp = bool(user.totp_enabled)
        user.phone = phone_to_apply
        # A disabled authenticator has no live login codes, so do not force a new setup.
        if had_totp:
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
    if body.company_website is not None:
        website = (body.company_website or "").strip()
        if website and not website.lower().startswith(("http://", "https://")):
            website = f"https://{website}"
        user.company_website = website or None
    if body.company_about is not None:
        user.company_about = (body.company_about or "").strip()[:4000] or None
    if body.company_rating is not None:
        user.company_rating = body.company_rating
        if not user.company_rating_source:
            user.company_rating_source = "manual"
    if body.company_review_count is not None:
        user.company_review_count = body.company_review_count
    if body.company_reviews is not None:
        user.company_reviews = body.company_reviews
    if body.company_rating_source is not None:
        user.company_rating_source = body.company_rating_source or None
    if body.google_place_id is not None:
        user.google_place_id = body.google_place_id or None
    if body.google_maps_url is not None:
        user.google_maps_url = body.google_maps_url or None
    if body.preferred_locations is not None:
        user.preferred_locations = body.preferred_locations[:5]
    if body.job_type is not None:
        try:
            user.job_type = JobType(body.job_type)
        except ValueError:
            pass

    await db.commit()

    if user.role == UserRole.seeker and seeker_match_fields_changed:
        from app.shared.services.celery_tasks import invalidate_seeker_matches_task
        invalidate_seeker_matches_task.delay(str(user.id))

    response_data = UpdateSettingsResponse.model_validate(user)
    if new_qr_code:
        response_data.new_totp_qr_code = new_qr_code
    return response_data


async def upload_profile_pic(file: UploadFile, user: User, db: AsyncSession) -> UserOut:
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG, WEBP, or GIF image")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo must be 5 MB or smaller")
    ext = os.path.splitext(file.filename or "")[1]
    filename = f"profile_{user.id}_{uuid.uuid4().hex}{ext}"
    file_path = str(get_upload_dir() / filename)
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not save file")
    user.profile_pic_url = f"/uploads/{filename}"
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


async def delete_own_account(user: User, db: AsyncSession) -> None:
    """
    Permanently delete the authenticated user's own account and all associated data.
    Cascades are handled by FK constraints / ORM relationships; remaining loose data
    is deleted explicitly to be safe.
    """
    from sqlalchemy import delete as sql_delete
    from app.modules.jobs_portal.models.application import Application
    from app.modules.jobs_portal.models.portfolio import Portfolio

    # Delete applications submitted by this user
    await db.execute(sql_delete(Application).where(Application.user_id == user.id))

    # Delete portfolio (cascade handles portfolio sub-records if configured)
    await db.execute(sql_delete(Portfolio).where(Portfolio.user_id == user.id))

    # Delete the user record itself
    await db.delete(user)
    await db.commit()


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


async def get_existing_public_user_ids(ids: list[str], db: AsyncSession) -> list[str]:
    """Return which of the given user IDs still exist (for seeker interest list filtering)."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in ids[:100]:
        if not raw or not isinstance(raw, str):
            continue
        value = raw.strip()
        if not value or value in seen:
            continue
        try:
            uuid.UUID(value)
        except ValueError:
            continue
        seen.add(value)
        cleaned.append(value)
    if not cleaned:
        return []
    res = await db.execute(select(User.id).where(User.id.in_(cleaned)))
    return [str(row[0]) for row in res.all()]
