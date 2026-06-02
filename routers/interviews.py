from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.interviews import InterviewCreate, InterviewOut
from services.auth_service import require_provider, require_verified
from services.interview_scheduling_dbservice import create_interview, get_user_interviews

router = APIRouter(prefix="/interviews", tags=["interviews"])

@router.post("", response_model=InterviewOut, status_code=201)
async def schedule_interview(
    body: InterviewCreate,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await create_interview(db, body, user)

@router.get("/me", response_model=List[InterviewOut])
async def get_my_interviews(
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_interviews(db, user)

