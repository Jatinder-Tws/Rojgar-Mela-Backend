from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date as dt_date, datetime
import uuid

class MarkAttendanceRequest(BaseModel):
    email: EmailStr
    date: Optional[dt_date] = None
    status: Optional[str] = "Present"

class AttendanceResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: dt_date
    attendance_status: str
    marked_at: datetime
    
    class Config:
        from_attributes = True

class UserAttendanceResponse(BaseModel):
    id: uuid.UUID
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    attendance_status: str
