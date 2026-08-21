from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.jobs_portal.schemas.attendance import MarkAttendanceRequest, AttendanceResponse, UserAttendanceResponse
from app.modules.jobs_portal.controllers.attendance_controller import (
    mark_attendance as ctrl_mark_attendance,
    get_daily_attendance as ctrl_get_daily_attendance,
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/mark", response_model=AttendanceResponse)
async def mark_attendance(request: MarkAttendanceRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_mark_attendance(request, db)


@router.get("/daily", response_model=list[UserAttendanceResponse])
async def get_daily_attendance(
    target_date: date | None = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Return daily attendance with optional search & status filters.

    - search: matches name, email, or phone (handled in controller)
    - status: 'Present' or 'Absent'
    """
    return await ctrl_get_daily_attendance(target_date, search, status, db)
