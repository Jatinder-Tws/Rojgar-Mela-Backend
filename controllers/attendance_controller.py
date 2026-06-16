"""
Attendance controller – business logic from routers/attendance.py
"""
import uuid
from datetime import date, datetime
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import select, or_, func
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
                return Attendance(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    date=target_date,
                    attendance_status="Absent",
                    marked_at=datetime.utcnow(),
                )
            else:
                attendance.attendance_status = request.status
                await db.commit()
                await db.refresh(attendance)
                return attendance
    if request.status == "Absent":
        return Attendance(
            id=uuid.uuid4(),
            user_id=user.id,
            date=target_date,
            attendance_status="Absent",
            marked_at=datetime.utcnow(),
        )
    new_attendance = Attendance(user_id=user.id, date=target_date, attendance_status=request.status)
    db.add(new_attendance)
    await db.commit()
    await db.refresh(new_attendance)
    return new_attendance


def _apply_attendance_search_filter(query, search: Optional[str]):
    if not search:
        return query
    term = f"%{search.strip()}%"
    full_name_expr = func.concat(func.coalesce(User.first_name, ""), " ", func.coalesce(User.last_name, ""))
    return query.where(
        or_(
            User.first_name.ilike(term),
            User.last_name.ilike(term),
            full_name_expr.ilike(term),
            User.email.ilike(term),
            User.phone.ilike(term),
        )
    )


async def get_daily_attendance(
    target_date: Optional[date],
    search: Optional[str],
    status: Optional[str],
    db: AsyncSession,
) -> List[UserAttendanceResponse]:
    """
    Return daily attendance with optional backend search & status filters.

    - search: matches name, email, or phone (case-insensitive, partial)
    - status: 'Present' or 'Absent'
    """
    if not target_date:
        target_date = date.today()

    # Base query: non-provider users (same as before), with optional search filter
    users_query = select(User).where(User.role != UserRole.provider)
    users_query = _apply_attendance_search_filter(users_query, search)
    users_result = await db.execute(users_query)
    users = users_result.scalars().all()

    # Load attendance records for the day
    attendance_result = await db.execute(select(Attendance).where(Attendance.date == target_date))
    attendances = {str(att.user_id): att for att in attendance_result.scalars().all()}

    response_list: List[UserAttendanceResponse] = []
    for user in users:
        user_status = "Absent"
        if str(user.id) in attendances:
            user_status = attendances[str(user.id)].attendance_status

        # Optional backend status filter
        if status in {"Present", "Absent"} and user_status != status:
            continue

        response_list.append(
            UserAttendanceResponse(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                phone=user.phone,
                attendance_status=user_status,
            )
        )
    return response_list
