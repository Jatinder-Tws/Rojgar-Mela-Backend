from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator
import re


class RegisterRequest(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    role: str = "seeker"
    password: str
    company_name: Optional[str] = None
    work_status: Optional[str] = None  # "experienced" | "fresher"
    current_city: Optional[str] = None

    @field_validator("full_name", "first_name", "last_name", "company_name", "current_city")
    @classmethod
    def validate_optional_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not str(v).strip():
            return None
        v = re.sub(r"\D", "", v)
        if len(v) != 10:
            raise ValueError("Phone number must be exactly 10 digits")
        return v

    @field_validator("work_status")
    @classmethod
    def validate_work_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().lower()
        if v not in {"experienced", "fresher"}:
            raise ValueError("Work status must be experienced or fresher")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        v = (v or "seeker").strip().lower()
        if v not in {"seeker", "provider"}:
            raise ValueError("Role must be seeker or provider")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @model_validator(mode="after")
    def validate_role_fields(self) -> "RegisterRequest":
        if self.role == "provider":
            if not self.company_name:
                raise ValueError("Company name is required")
            return self

        name = (self.full_name or f"{self.first_name or ''} {self.last_name or ''}").strip()
        if not name:
            raise ValueError("Full name is required")
        if not self.phone:
            raise ValueError("Phone number is required")
        if not self.work_status:
            raise ValueError("Work status is required")
        if self.work_status == "fresher" and not self.current_city:
            raise ValueError("Current city is required for freshers")
        return self


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
    # Accepts a normal account email OR a training-portal teacher login username
    # (usernames are not always email-shaped), so kept as a plain string.
    email: str
    password: str
    captcha_token: Optional[str] = None


class GoogleLoginRequest(BaseModel):
    """Google Identity Services ID token (`credential`) from the frontend button."""
    credential: str
    role: str = "seeker"
    intent: str = "login"

    @field_validator("credential")
    @classmethod
    def validate_credential(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Google credential is required")
        return v

    @field_validator("role")
    @classmethod
    def validate_google_role(cls, v: str) -> str:
        v = (v or "seeker").strip().lower()
        if v == "candidate":
            v = "seeker"
        if v not in {"seeker", "provider"}:
            raise ValueError("Role must be seeker or provider")
        return v

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, v: str) -> str:
        v = (v or "login").strip().lower()
        if v not in {"login", "register"}:
            return "login"
        return v


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
    requires_complete_profile: bool = False
    requires_captcha: bool = False
    pending_token: Optional[str] = None
    linked: bool = False
    email: Optional[str] = None
    qr_code_base64: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None




class UserOut(BaseModel):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_verified: bool
    onboarding_complete: bool
    is_super_admin: bool = False
    gender: Optional[str] = None
    address: Optional[str] = None
    highest_qualification: Optional[str] = None
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
    company_type: Optional[str] = None
    company_location: Optional[str] = None
    company_address: Optional[str] = None
    company_size: Optional[str] = None
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
