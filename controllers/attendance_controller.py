"""
Attendance controller – business logic from routers/attendance.py
"""
import uuid
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.attendance import Attendance
from models.user import User, UserRole
from schemas.attendance import MarkAttendanceRequest, AttendanceResponse, UserAttendanceResponse


async def mark_attendance(request: MarkAttendanceRequest, db: AsyncSession) -> AttendanceResponse:
    user_result = await db.execute(select(User).where(User.email == request.email))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    target_date = request.date or date.today()
    existing_attendance = await db.execute(
        select(Attendance).where(Attendance.user_id == user.id, Attendance.date == target_date)
    )
    attendance = existing_attendance.scalars().first()
    if attendance:
        if attendance.attendance_status == request.status:
            return attendance
        else:
            if request.status == "Absent":
                await db.delete(attendance)
                await db.commit()
                return Attendance(id=uuid.uuid4(), user_id=user.id, date=target_date, attendance_status="Absent", marked_at=datetime.utcnow())
            else:
                attendance.attendance_status = request.status
                await db.commit()
                await db.refresh(attendance)
                return attendance
    if request.status == "Absent":
        return Attendance(id=uuid.uuid4(), user_id=user.id, date=target_date, attendance_status="Absent", marked_at=datetime.utcnow())
    new_attendance = Attendance(user_id=user.id, date=target_date, attendance_status=request.status)
    db.add(new_attendance)
    await db.commit()
    await db.refresh(new_attendance)
    return new_attendance


async def get_daily_attendance(target_date: date, db: AsyncSession) -> list:
    if not target_date:
        target_date = date.today()
    users_result = await db.execute(select(User).where(User.role != UserRole.provider))
    users = users_result.scalars().all()
    attendance_result = await db.execute(select(Attendance).where(Attendance.date == target_date))
    attendances = {str(att.user_id): att for att in attendance_result.scalars().all()}
    response_list = []
    for user in users:
        status = "Absent"
        if str(user.id) in attendances:
            status = attendances[str(user.id)].attendance_status
        response_list.append(UserAttendanceResponse(
            id=user.id, first_name=user.first_name, last_name=user.last_name,
            email=user.email, phone=user.phone, attendance_status=status
        ))
    return response_list
