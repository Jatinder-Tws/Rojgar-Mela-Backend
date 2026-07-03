from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


InternshipStatus = Literal["draft", "active", "closed"]


class TrainingPortalInternshipCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    duration: str = Field(..., min_length=1, max_length=50)
    is_paid: bool = True
    fee: float = Field(default=0.0, ge=0)
    start_date: str = Field(..., min_length=1)
    end_date: str = Field(..., min_length=1)
    venue: str = Field(..., min_length=1, max_length=300)
    max_seats: int = Field(default=15, ge=1)
    seats_filled: int = Field(default=0, ge=0)
    status: InternshipStatus = "active"
    laptop_required: bool = True


class TrainingPortalInternshipUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    duration: Optional[str] = Field(None, min_length=1, max_length=50)
    is_paid: Optional[bool] = None
    fee: Optional[float] = Field(None, ge=0)
    start_date: Optional[str] = Field(None, min_length=1)
    end_date: Optional[str] = Field(None, min_length=1)
    venue: Optional[str] = Field(None, min_length=1, max_length=300)
    max_seats: Optional[int] = Field(None, ge=1)
    seats_filled: Optional[int] = Field(None, ge=0)
    status: Optional[InternshipStatus] = None
    laptop_required: Optional[bool] = None


class TrainingPortalInternshipOut(BaseModel):
    id: str
    title: str
    description: str
    duration: str
    is_paid: bool
    fee: float
    start_date: str
    end_date: str
    venue: str
    max_seats: int
    seats_filled: int
    status: InternshipStatus
    laptop_required: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True