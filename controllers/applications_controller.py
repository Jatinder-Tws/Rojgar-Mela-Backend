import logging
from typing import List
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.application import Application, ApplicationStatus
from models.job import JobPosting
from models.resume import Resume
from models.user import User
from models.notification import Notification, NotificationType
from models.external_candidate import ExternalCandidate
from schemas.jobs import ApplicationCreate, ApplicationOut, RejectApplicationRequest, ShortlistedApplicationOut
from services.ai_feedback_service import generate_rejection_feedback
from services.email_service import send_notification_email
from services.notification_service import create_notification
from services.auto_interview_service import auto_schedule_for_application

logger = logging.getLogger(__name__)


async def apply_to_job(
    body: ApplicationCreate,
    user: User,
    db: AsyncSession,
) -> ApplicationOut:
    result = await db.execute(select(JobPosting).where(JobPosting.id == body.job_id, JobPosting.is_active == True))  # noqa
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or no longer active")

    dup = await db.execute(
        select(Application).where(and_(Application.seeker_id == user.id, Application.job_id == body.job_id))
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already applied to this job")

    app = Application(seeker_id=user.id, job_id=body.job_id, status=ApplicationStatus.applied)
    db.add(app)

    provider_result = await db.execute(select(User).where(User.id == job.provider_id))
    provider = provider_result.scalar_one_or_none()
    if provider:
        from models.match import Match
        match_result = await db.execute(
            select(Match.id).where(and_(Match.seeker_id == user.id, Match.job_id == body.job_id))
        )
        match_id = match_result.scalar()
        await create_notification(
            db=db,
            user_id=provider.id,
            type=NotificationType.application,
            title=f"New application for {job.title}",
            message=f"{user.first_name} {user.last_name} has applied to your '{job.title}' posting.",
            related_job_id=body.job_id,
            related_user_id=match_id if match_id else user.id,
        )

    await db.commit()
    try:
        await auto_schedule_for_application(db, app, user, job)
        await db.commit()
    except Exception:
        await db.rollback()
    await db.refresh(app)
    return ApplicationOut.model_validate(app)


async def get_my_applications(user: User, db: AsyncSession) -> List[ApplicationOut]:
    result = await db.execute(
        select(Application, JobPosting)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .where(Application.seeker_id == user.id)
        .order_by(Application.applied_at.desc())
    )
    rows = result.all()
    out = []
    for app, job in rows:
        out.append(ApplicationOut(
            id=str(app.id),
            seeker_id=str(app.seeker_id),
            job_id=str(app.job_id),
            status=app.status,
            rejection_reason=app.rejection_reason,
            ai_feedback=app.ai_feedback,
            applied_at=app.applied_at,
            updated_at=app.updated_at,
            job_title=job.title,
            job_type=job.job_type,
            company_name=job.posted_by_name,
            experience_required=job.experience_required,
            salary_range=job.salary_range,
            job_description=job.description,
            required_skills=job.required_skills if isinstance(job.required_skills, list) else [],
            ai_interview_enabled=job.ai_interview_enabled,
        ))
    return out


async def get_all_applicants(user: User, db: AsyncSession) -> List[ApplicationOut]:
    result = await db.execute(
        select(Application, User, JobPosting)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .outerjoin(User, Application.seeker_id == User.id)
        .where(JobPosting.provider_id == user.id)
        .order_by(Application.applied_at.desc())
    )
    rows = result.all()
    out = []
    for app, seeker, job in rows:
        app_out = ApplicationOut.model_validate(app)
        app_out.job_title = job.title
        app_out.job_type = job.job_type
        app_out.company_name = job.posted_by_name
        app_out.experience_required = job.experience_required
        app_out.salary_range = job.salary_range
        if seeker:
            app_out.seeker_first_name = seeker.first_name
            app_out.seeker_last_name = seeker.last_name
            app_out.seeker_email = seeker.email
            app_out.seeker_phone = seeker.phone
            app_out.seeker_profile_pic_url = seeker.profile_pic_url
        else:
            app_out.seeker_first_name = app.candidate_name
            app_out.seeker_last_name = ""
        out.append(app_out)
    return out


async def get_job_applications(job_id: str, user: User, db: AsyncSession) -> List[ApplicationOut]:
    job_result = await db.execute(
        select(JobPosting).where(JobPosting.id == job_id, JobPosting.provider_id == user.id)
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = await db.execute(
        select(Application, User)
        .outerjoin(User, Application.seeker_id == User.id)
        .where(Application.job_id == job_id)
        .order_by(Application.applied_at.desc())
    )
    rows = result.all()
    print("The rows result are ----------------------------", rows)
    out = []
    for app, seeker in rows:
        app_out = ApplicationOut.model_validate(app)
        app_out.job_title = job.title
        app_out.job_type = job.job_type
        app_out.company_name = job.posted_by_name
        app_out.experience_required = job.experience_required
        app_out.salary_range = job.salary_range
        app_out.job_description = job.description
        app_out.required_skills = job.required_skills if isinstance(job.required_skills, list) else []
        app_out.ai_interview_enabled = job.ai_interview_enabled
        if seeker:
            app_out.seeker_first_name = seeker.first_name
            app_out.seeker_last_name = seeker.last_name
            app_out.seeker_email = seeker.email
            app_out.seeker_phone = seeker.phone
            app_out.seeker_profile_pic_url = seeker.profile_pic_url
        else:
            app_out.seeker_first_name = app.candidate_name
            app_out.seeker_last_name = ""
            app_out.seeker_email = app.candidate_email
            app_out.seeker_phone = app.candidate_phone
            app_out.candidate_experience = app.candidate_experience
            app_out.candidate_resume_url = app.candidate_resume_url
        app_out.ai_feedback = app.ai_feedback
        out.append(app_out)
    print(out)
    return out


async def get_all_external_applications(user: User, db: AsyncSession) -> List[ApplicationOut]:
    result = await db.execute(
        select(ExternalCandidate, JobPosting)
        .outerjoin(JobPosting, ExternalCandidate.job_id == JobPosting.id)
        .where(
            or_(
                JobPosting.provider_id == user.id,
                ExternalCandidate.job_id == None,
            )
        )
        .order_by(ExternalCandidate.applied_at.desc())
    )
    rows = result.all()
    out = []
    for candidate, job in rows:
        app_out = ApplicationOut(
            id=str(candidate.id),
            job_id=str(candidate.job_id) if candidate.job_id else "",
            status=str(candidate.status or "pending"),
            applied_at=candidate.applied_at,
            updated_at=candidate.updated_at or candidate.applied_at,
            job_title=job.title if job else "General Interest",
            job_type=job.job_type if job else "N/A",
            company_name=job.posted_by_name if job else "N/A",
            seeker_first_name=candidate.full_name,
            seeker_last_name="",
            seeker_email=candidate.email,
            seeker_phone=candidate.phone,
            candidate_name=candidate.full_name,
            candidate_email=candidate.email,
            candidate_phone=candidate.phone,
            candidate_date_of_birth=candidate.date_of_birth,
            candidate_gender=candidate.gender,
            candidate_experience=candidate.total_experience,
            candidate_resume_url=candidate.resume_url,
            candidate_job_category=candidate.department,
            candidate_job_role=candidate.sub_role,
            candidate_job_location=candidate.state,
            candidate_journey=candidate.professional_journey,
        )
        out.append(app_out)
    return out


async def get_shortlisted_applications(user: User, db: AsyncSession) -> List[ShortlistedApplicationOut]:
    result = await db.execute(
        select(Application, JobPosting, User)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .outerjoin(User, Application.seeker_id == User.id)
        .where(
            and_(
                JobPosting.provider_id == user.id,
                Application.status == ApplicationStatus.shortlisted,
            )
        )
        .order_by(Application.updated_at.desc())
    )
    rows = result.all()
    out = []
    for app, job, seeker in rows:
        out.append(ShortlistedApplicationOut(
            id=str(app.id),
            job_id=str(app.job_id),
            seeker_id=str(app.seeker_id) if app.seeker_id else None,
            status=str(app.status),
            applied_at=app.applied_at,
            job_title=job.title,
            seeker_first_name=seeker.first_name if seeker else (app.candidate_name or "Guest"),
            seeker_last_name=seeker.last_name if seeker else "",
            seeker_email=seeker.email if seeker else (app.candidate_email or ""),
            seeker_phone=seeker.phone if seeker else app.candidate_phone,
            seeker_profile_pic_url=seeker.profile_pic_url if seeker else None,
        ))
    return out


async def shortlist_application(app_id: str, user: User, db: AsyncSession) -> ApplicationOut:
    app_result = await db.execute(select(Application).where(Application.id == app_id))
    app = app_result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job_result = await db.execute(
        select(JobPosting).where(JobPosting.id == app.job_id, JobPosting.provider_id == user.id)
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=403, detail="Forbidden")

    app.status = ApplicationStatus.shortlisted
    await db.commit()

    seeker_result = await db.execute(select(User).where(User.id == app.seeker_id))
    seeker = seeker_result.scalar_one_or_none()
    if seeker:
        await create_notification(
            db=db,
            user_id=seeker.id,
            type=NotificationType.shortlisted,
            title=f"🎉 Your resume was shortlisted for {job.title}!",
            message=f"Congratulations! {user.first_name} from {user.company_name or 'a company'} has shortlisted your application for '{job.title}'. They may reach out soon. Keep your profile updated!",
            related_job_id=str(job.id),
            related_user_id=str(user.id),
        )

    try:
        await auto_schedule_for_application(db, app, user, job)
    except Exception:
        logger.exception("Auto-schedule failed for application %s", app.id)

    await db.refresh(app)
    return ApplicationOut.model_validate(app)


async def reject_application(
    app_id: str,
    body: RejectApplicationRequest,
    background_tasks: BackgroundTasks,
    user: User,
    db: AsyncSession,
) -> ApplicationOut:
    app_result = await db.execute(select(Application).where(Application.id == app_id))
    app = app_result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job_result = await db.execute(
        select(JobPosting).where(JobPosting.id == app.job_id, JobPosting.provider_id == user.id)
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=403, detail="Forbidden")

    app.status = ApplicationStatus.rejected
    app.rejection_reason = body.rejection_reason
    await db.commit()

    seeker_result = await db.execute(select(User).where(User.id == app.seeker_id))
    seeker = seeker_result.scalar_one_or_none()

    resume_result = await db.execute(
        select(Resume).where(Resume.user_id == app.seeker_id).order_by(Resume.created_at.desc()).limit(1)
    )
    resume = resume_result.scalar_one_or_none()

    async def _generate_and_save_feedback():
        feedback = await generate_rejection_feedback(
            resume_text=resume.parsed_text or "" if resume else "",
            rejection_reason=body.rejection_reason,
            job_title=job.title,
        )
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as s:
            a = await s.get(Application, app_id)
            if a:
                a.ai_feedback = feedback
                await s.commit()
            if seeker:
                await create_notification(
                    db=s,
                    user_id=seeker.id,
                    type=NotificationType.rejected,
                    title=f"Application update for {job.title}",
                    message=f"Your application for '{job.title}' was not selected this time. Don't be discouraged — we've generated personalized AI suggestions to help you improve. Check your dashboard.",
                    related_job_id=str(job.id),
                )

    background_tasks.add_task(_generate_and_save_feedback)
    await db.refresh(app)
    return ApplicationOut.model_validate(app)


async def update_application_status(
    app_id: str,
    body: dict,
    user: User,
    db: AsyncSession,
) -> ApplicationOut:
    try:
        status = body.get("status")
        ai_feedback = body.get("ai_feedback")

        result = await db.execute(select(Application).where(Application.id == app_id))
        app = result.scalar_one_or_none()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        job_result = await db.execute(
            select(JobPosting).where(JobPosting.id == app.job_id, JobPosting.provider_id == user.id)
        )
        job = job_result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=403, detail="Forbidden")

        if status == "shortlisted":
            app.status = ApplicationStatus.shortlisted
            await db.commit()

            seeker_result = await db.execute(select(User).where(User.id == app.seeker_id))
            seeker = seeker_result.scalar_one_or_none()
            if seeker:
                await create_notification(
                    db=db,
                    user_id=seeker.id,
                    type=NotificationType.shortlisted,
                    title=f"🎉 Your resume was shortlisted for {job.title}!",
                    message=f"Congratulations! {user.first_name} from {user.company_name or 'a company'} has shortlisted your application for '{job.title}'. They may reach out soon. Keep your profile updated!",
                    related_job_id=str(job.id),
                    related_user_id=str(user.id),
                )
            try:
                await auto_schedule_for_application(db, app, user, job)
            except Exception:
                logger.exception("Auto-schedule failed for application %s", app.id)

        elif status == "rejected":
            app.status = ApplicationStatus.rejected
            app.rejection_reason = ai_feedback or "Not specified"
            await db.commit()

        else:
            app.status = status
            if ai_feedback:
                app.ai_feedback = ai_feedback
            await db.commit()

        await db.refresh(app)
        return ApplicationOut.model_validate(app)

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Error updating application status: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to update application status")
