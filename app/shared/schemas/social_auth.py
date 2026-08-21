from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator
import re


class CompleteProfileRequest(BaseModel):
    token: str
    role: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not str(v).strip():
            return None
        v = v.strip().lower()
        if v in {"candidate"}:
            v = "seeker"
        if v not in {"seeker", "provider"}:
            raise ValueError("Role must be seeker or provider")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not str(v).strip():
            return None
        v = re.sub(r"\D", "", v)
        if len(v) != 10:
            raise ValueError("Phone number must be exactly 10 digits")
        return v


class ConfirmEmailRequest(BaseModel):
    token: str
    email: EmailStr


class ConfirmEmailVerifyRequest(BaseModel):
    token: str
    email: EmailStr
    code: str


class SocialTwoFactorRequest(BaseModel):
    token: str
    code: str


class UnlinkProviderResponse(BaseModel):
    message: str


class LinkedAccountOut(BaseModel):
    provider: str
    provider_email: Optional[str] = None
    connected_at: datetime


class SessionOut(BaseModel):
    id: str
    login_method: Optional[str] = None
    device_label: Optional[str] = None
    ip_address: Optional[str] = None
    last_active_at: datetime
    created_at: datetime
    is_current: bool = False


class AuthProviderPublicConfig(BaseModel):
    enabled: bool
    configured: bool = False
    roles: List[str] = []
    onRegister: bool = False
    onLogin: bool = False
    sortOrder: int = 99


class AuthConfigResponse(BaseModel):
    google: AuthProviderPublicConfig
    github: AuthProviderPublicConfig
    linkedin: AuthProviderPublicConfig
    lastLoginMethod: Optional[str] = None


class AdminAuthProviderUpdate(BaseModel):
    is_enabled: bool
    enabled_for_roles: List[str]
    enabled_on_register: bool
    enabled_on_login: bool
    display_order: Optional[int] = None

    @field_validator("enabled_for_roles")
    @classmethod
    def validate_roles(cls, v: List[str]) -> List[str]:
        allowed = {"seeker", "provider"}
        out = []
        for item in v or []:
            role = "seeker" if item == "candidate" else item
            if role in allowed and role not in out:
                out.append(role)
        return out

    @field_validator("display_order")
    @classmethod
    def validate_order(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        return max(1, int(v))


class AdminAuthProviderOut(BaseModel):
    provider: str
    is_enabled: bool
    enabled_for_roles: List[str]
    enabled_on_register: bool
    enabled_on_login: bool
    display_order: int = 1
    configured: bool = False
    updated_at: Optional[datetime] = None


class AdminAuthHistoryItem(BaseModel):
    id: str
    provider: str
    changed_by: Optional[str] = None
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    changed_at: datetime
