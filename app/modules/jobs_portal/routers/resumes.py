from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.shared.models.user import User
from app.modules.jobs_portal.schemas.jobs import ResumeImproveRequest, ResumeOut, ResumeProcessingStatusOut
from app.core.dependencies import require_seeker, require_provider_or_super_admin
from app.modules.jobs_portal.controllers.resumes_controller import (
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
async def download_candidate_resume(
    user_id: str,
    _user: User = Depends(require_provider_or_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_download_candidate_resume(user_id, db)


@router.get("/{user_id}/status")
async def check_candidate_resume_status(
    user_id: str,
    _user: User = Depends(require_provider_or_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_check_candidate_resume_status(user_id, db)


@router.post("/resume/improve")
async def improve_resume(request: ResumeImproveRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_improve_resume(request, db)


@router.get("/resume/improve/status/{task_id}")
async def get_resume_improvement_status(task_id: str):
    from celery.result import AsyncResult
    from app.core.celery_app import celery_app
    res = AsyncResult(task_id, app=celery_app)
    state = res.state
    if state == "SUCCESS":
        result = res.result or {}
        raw_score = result.get("score") or 0.0
        # Normalize score to 0.0 - 10.0 scale
        if raw_score > 10.0:
            score_out_of_10 = min(max(raw_score / 10.0, 0.0), 10.0)
        else:
            score_out_of_10 = min(max(raw_score, 0.0), 10.0)
            
        match_score = int(score_out_of_10 * 10)

        return {
            "status": "SUCCESS",
            "result": {
                "missing_skills": result.get("missing_skills") or [],
                "improvements": result.get("improvements") or [],
                "rewritten_bullets": result.get("rewritten_bullets") or [],
                "ats_keywords": result.get("ats_keywords") or [],
                "score": score_out_of_10,
                "futureTechToLearn": result.get("futureTechToLearn") or [],
                # Legacy compatibility mapping for ResumeOptimizerModal.tsx
                "match_score": match_score,
                "suggestions": result.get("improvements") or [],
                "feedback": result.get("improvements")[0] if result.get("improvements") else "No specific suggestions."
            }
        }
    elif state == "FAILURE":
        return {
            "status": "FAILURE",
            "error": str(res.result)
        }
    else:
        return {
            "status": state,
            "result": None
        }
