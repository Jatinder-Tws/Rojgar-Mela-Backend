from datetime import datetime
from typing import List, Optional
import re
from pydantic import BaseModel, EmailStr, Field, field_validator


class SupervisorCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    password: str = Field(..., min_length=6, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        v_clean = v.strip()
        digits = re.sub(r"\D", "", v_clean)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Phone number must contain between 10 and 15 digits")
        return v_clean


class SupervisorUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        v_clean = v.strip()
        digits = re.sub(r"\D", "", v_clean)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Phone number must contain between 10 and 15 digits")
        return v_clean


class SupervisorStatusUpdateRequest(BaseModel):
    is_active: bool


class SupervisorResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=100)


class SupervisorItemOut(BaseModel):
    id: str
    user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str
    email: str
    phone: Optional[str] = None
    department: Optional[str] = None
    is_active: bool
    permissions: List[str]
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SupervisorListResponse(BaseModel):
    items: List[SupervisorItemOut]
    total: int
    page: int
    limit: int
    pages: int


class SupervisorLoginRequest(BaseModel):
    email: EmailStr
    password: str


class SupervisorLoginResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: SupervisorItemOut
