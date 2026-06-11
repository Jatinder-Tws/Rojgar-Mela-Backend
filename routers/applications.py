from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.jobs import ApplicationCreate, ApplicationOut, RejectApplicationRequest, ShortlistedApplicationOut
from services.auth_service import require_seeker, require_provider, require_verified
from controllers.applications_controller import (
    apply_to_job as ctrl_apply_to_job,
    get_my_applications as ctrl_get_my_applications,
    get_all_applicants as ctrl_get_all_applicants,
    get_job_applications as ctrl_get_job_applications,
    get_all_external_applications as ctrl_get_all_external_applications,
    get_shortlisted_applications as ctrl_get_shortlisted_applications,
    shortlist_application as ctrl_shortlist_application,
    reject_application as ctrl_reject_application,
    update_application_status as ctrl_update_application_status,
)

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationOut, status_code=201)
async def apply_to_job(body: ApplicationCreate, user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_apply_to_job(body, user, db)


@router.get("/me", response_model=List[ApplicationOut])
async def get_my_applications(user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_my_applications(user, db)


@router.get("/all", response_model=List[ApplicationOut])
async def get_all_applicants(user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_all_applicants(user, db)


@router.get("/external", response_model=List[ApplicationOut])
async def get_all_external_applications(user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_all_external_applications(user, db)


@router.get("/shortlisted", response_model=List[ShortlistedApplicationOut])
async def get_shortlisted_applications(user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_shortlisted_applications(user, db)


@router.get("/job/{job_id}", response_model=List[ApplicationOut])
async def get_job_applications(job_id: str, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_job_applications(job_id, user, db)


@router.patch("/{app_id}/shortlist", response_model=ApplicationOut)
async def shortlist_application(app_id: str, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_shortlist_application(app_id, user, db)


@router.patch("/{app_id}/reject", response_model=ApplicationOut)
async def reject_application(app_id: str, body: RejectApplicationRequest, background_tasks: BackgroundTasks, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_reject_application(app_id, body, background_tasks, user, db)


@router.patch("/{app_id}/status", response_model=ApplicationOut)
async def update_application_status(app_id: str, body: dict, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_update_application_status(app_id, body, user, db)
