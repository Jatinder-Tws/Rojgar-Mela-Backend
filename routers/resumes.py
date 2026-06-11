from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.jobs import ResumeImproveRequest, ResumeOut, ResumeProcessingStatusOut
from services.auth_service import require_seeker, require_provider
from controllers.resumes_controller import (
    upload_resume as ctrl_upload_resume,
    get_my_resume_processing_status as ctrl_get_my_resume_processing_status,
    get_my_resume as ctrl_get_my_resume,
    download_my_resume as ctrl_download_my_resume,
    download_candidate_resume as ctrl_download_candidate_resume,
    check_candidate_resume_status as ctrl_check_candidate_resume_status,
    improve_resume as ctrl_improve_resume,
)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeOut, status_code=201)
async def upload_resume(background_tasks: BackgroundTasks, file: UploadFile = File(...), user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_upload_resume(background_tasks, file, user, db)


@router.get("/me/processing-status", response_model=ResumeProcessingStatusOut)
async def get_my_resume_processing_status(user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_my_resume_processing_status(user, db)


@router.get("/me", response_model=ResumeOut)
async def get_my_resume(user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_my_resume(user, db)


@router.get("/me/download")
async def download_my_resume(user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_download_my_resume(user, db)


@router.get("/{user_id}/download")
async def download_candidate_resume(user_id: str, provider: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_download_candidate_resume(user_id, db)


@router.get("/{user_id}/status")
async def check_candidate_resume_status(user_id: str, provider: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_check_candidate_resume_status(user_id, db)


@router.post("/resume/improve")
async def improve_resume(request: ResumeImproveRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_improve_resume(request, db)