# service to handle job update put and patch
from app.modules.jobs_portal.models.job import JobPosting, JobType
from app.shared.models.user import User
from app.modules.jobs_portal.schemas.jobs import JobUpdate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import  BackgroundTasks,  HTTPException


async def update_job_service(
    job: JobPosting,
    body: JobUpdate,
    background_tasks: BackgroundTasks,
):
    content_changed = False

    if body.title is not None:
        job.title = body.title
        content_changed = True

    if body.description is not None:
        job.description = body.description
        content_changed = True

    if body.required_skills is not None:
        job.required_skills = body.required_skills
        content_changed = True

    if body.experience_required is not None:
        job.experience_required = body.experience_required

    if body.job_type is not None:
        job.job_type = JobType(body.job_type)

    if body.salary_range is not None:
        job.salary_range = body.salary_range

    if body.is_active is not None:
        job.is_active = body.is_active

    if body.post_count is not None:
        job.post_count = int(body.post_count)


        if not body.is_active:
            content_changed = False
            from app.modules.jobs_portal.services.seeker_matching_service import _cleanup_job_matches_and_notify
            background_tasks.add_task(
                _cleanup_job_matches_and_notify,
                str(job.id),
                job.title
            )

    if body.location is not None:
        job.location = body.location

    if body.ai_interview_enabled is not None:
        job.ai_interview_enabled = body.ai_interview_enabled

    if body.selection_threshold is not None:
        job.selection_threshold = body.selection_threshold

    if body.shift is not None:
        job.shift = body.shift
    
    if body.employment_type is not None:
        job.employment_type = body.employment_type
    
    if body.perks is not None:
        job.perks = body.perks

    return content_changed


async def deactivate_job_service(job: JobPosting):
    job.is_active = False

async def activate_job_service(job: JobPosting):
    job.is_active = True


def schedule_cleanup(background_tasks, job: JobPosting):
    from app.modules.jobs_portal.services.seeker_matching_service import _cleanup_job_matches_and_notify

    background_tasks.add_task(
        _cleanup_job_matches_and_notify,
        str(job.id),
        job.title
    )

def schedule_activation(background_tasks, job: JobPosting):
    from app.modules.jobs_portal.services.seeker_matching_service import proactive_match_job_to_candidates
    background_tasks.add_task(proactive_match_job_to_candidates, str(job.id))

async def get_job_or_404(job_id: str, user: User, db: AsyncSession):
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()

    if not job or str(job.provider_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Job not found")

    return job