from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.attendance import MarkAttendanceRequest, AttendanceResponse, UserAttendanceResponse
from controllers.attendance_controller import (
    mark_attendance as ctrl_mark_attendance,
    get_daily_attendance as ctrl_get_daily_attendance,
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/mark", response_model=AttendanceResponse)
async def mark_attendance(request: MarkAttendanceRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_mark_attendance(request, db)


@router.get("/daily", response_model=list[UserAttendanceResponse])
async def get_daily_attendance(target_date: date = None, db: AsyncSession = Depends(get_db)):
    return await ctrl_get_daily_attendance(target_date, db)
