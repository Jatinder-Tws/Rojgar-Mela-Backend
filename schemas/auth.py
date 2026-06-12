from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator
import re


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    role: str = "seeker"
    password: Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field is required")
        if len(v) > 50:
            raise ValueError("Max 50 characters")
        if re.search(r"[0-9!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("No numbers or special characters allowed")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = re.sub(r"\D", "", v)
        if len(v) != 10:
            raise ValueError("Phone number must be exactly 10 digits")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 15:
            raise ValueError("Password must not exceed 15 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\];:'\\]", v):
            raise ValueError("Password must contain at least one symbol (!@#$%^&*etc)")
        return v


class RegisterResponse(BaseModel):
    message: str
    requires_otp: bool = True


class UnverifiedLoginResponse(BaseModel):
    message: str
    requires_otp: bool = True
    email: str


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code_uri: str
    qr_code_base64: str


class TOTPVerifyRequest(BaseModel):
    code: str


class TOTPLoginRequest(BaseModel):
    email: EmailStr
    password: str
    code: str

class VerifyResetOtpRequest(BaseModel):
    email: EmailStr
    code: str


class TOTPStatusResponse(BaseModel):
    enabled: bool


class CreateTestUserRequest(BaseModel):
    """Request for admin/developer to create a test user with auto-generated password."""
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    role: str = "seeker"


class CreateTestUserResponse(BaseModel):
    """Response after creating a test user — password is sent via email."""
    message: str
    user_id: str
    email: str
    role: str




class VerifyOtpRequest(BaseModel):
    email: EmailStr
    code: str


class SendPhoneOtpRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = re.sub(r"\D", "", v)
        if len(v) != 10:
            raise ValueError("Phone number must be exactly 10 digits")
        return v


class VerifyPhoneOtpRequest(BaseModel):
    phone: str
    code: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = re.sub(r"\D", "", v)
        if len(v) != 10:
            raise ValueError("Phone number must be exactly 10 digits")
        return v


class ResendOtpRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    email: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 15:
            raise ValueError("Password must not exceed 15 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\];:'\\]", v):
            raise ValueError("Password must contain at least one symbol (!@#$%^&*etc)")
        return v


class ResetPasswordResponse(BaseModel):
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: "UserOut"


class LoginResponse(BaseModel):
    message: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = "bearer"
    user: Optional["UserOut"] = None
    requires_totp: bool = False
    requires_otp: bool = False
    requires_setup: bool = False
    email: Optional[str] = None
    qr_code_base64: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"




class UserOut(BaseModel):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: str
    role: Optional[str] = None
    is_verified: bool
    onboarding_complete: bool
    industry: Optional[str] = None
    job_role: Optional[str] = None
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    company_type: Optional[str] = None
    company_name: Optional[str] = None
    company_location: Optional[str] = None
    company_address: Optional[str] = None
    preferred_locations: Optional[List[str]] = None
    auto_apply_enabled: bool = False
    profile_pic_url: Optional[str] = None
    experience: Optional[str] = None
    company_size: Optional[str] = None
    is_first_login: bool = True
    created_at: datetime

    @field_validator("is_first_login", mode="before")
    @classmethod
    def coerce_is_first_login(cls, v):
        if v is None:
            return True
        return v

    class Config:
        from_attributes = True


class OnboardingRequest(BaseModel):
    role: str  # "seeker" | "provider"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    industry: Optional[str] = None
    job_role: Optional[str] = None
    job_type: Optional[str] = None     # "in_office" | "wfh" | "hybrid"
    salary_range: Optional[str] = None
    experience: Optional[str] = None
    company_type: Optional[str] = None  # "individual" | "company"
    company_name: Optional[str] = None
    company_location: Optional[str] = None
    company_address: Optional[str] = None
    company_size: Optional[str] = None
    preferred_locations: Optional[List[str]] = None


class UpdateSettingsRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    auto_apply_enabled: Optional[bool] = None
    industry: Optional[str] = None
    job_role: Optional[str] = None
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    company_name: Optional[str] = None
    company_location: Optional[str] = None
    company_address: Optional[str] = None
    preferred_locations: Optional[List[str]] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = re.sub(r"\D", "", v)
            if len(v) != 10:
                raise ValueError("Phone number must be exactly 10 digits")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Name cannot be empty")
            if len(v) > 50:
                raise ValueError("Max 50 characters")
            if re.search(r"[0-9!@#$%^&*(),.?\":{}|<>]", v):
                raise ValueError("No numbers or special characters allowed")
        return v

class UpdateSettingsResponse(UserOut):
    new_totp_qr_code: Optional[str] = None
