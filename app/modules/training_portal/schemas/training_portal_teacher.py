from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


TeacherStatus = Literal["active", "inactive"]


class TrainingPortalTeacherCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=1, max_length=200)
    phone: Optional[str] = "+91 00000 00000"
    bio: Optional[str] = "Qualified physical classroom instructor."
    subjects: Optional[List[str]] = []
    rating: Optional[float] = 5.0
    status: TeacherStatus = "active"
    avatar: Optional[str] = None
    login_username: str = Field(..., min_length=1, max_length=100)
    login_password: str = Field(..., min_length=6, max_length=200)
    login_active: bool = True


class TrainingPortalTeacherUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[str] = Field(None, min_length=1, max_length=200)
    phone: Optional[str] = None
    bio: Optional[str] = None
    subjects: Optional[List[str]] = None
    rating: Optional[float] = None
    status: Optional[TeacherStatus] = None
    avatar: Optional[str] = None
    login_username: Optional[str] = Field(None, min_length=1, max_length=100)
    login_password: Optional[str] = Field(None, min_length=6, max_length=200)
    login_active: Optional[bool] = None


class TrainingPortalTeacherOut(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    bio: str
    subjects: List[str] = []
    assigned_batches_count: int = 0
    rating: float
    status: TeacherStatus
    avatar: Optional[str] = None
    login_username: str
    login_password: str = ""
    login_active: bool
    last_login_at: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True