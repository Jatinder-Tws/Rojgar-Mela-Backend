from datetime import datetime, time, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator,AliasChoices

ALLOWED_SLOT_DURATIONS = {15, 30, 45, 60}


class AvailabilityWindowIn(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday … 6=Sunday")
    start_time: time
    end_time: time
    # period: Optional[str] = None
    start_period: Optional[str] = None
    end_period: Optional[str] = None


    @model_validator(mode="after")
    def end_after_start(self) -> "AvailabilityWindowIn":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class AvailabilityWindowOut(BaseModel):
    id: str
    provider_id: str
    day_of_week: int
    start_time: time
    end_time: time
    # period: Optional[str] = None
    start_period: Optional[str] = None
    end_period: Optional[str] = None


    class Config:
        from_attributes = True


class ProviderInterviewSettingsUpdate(BaseModel):
    auto_schedule_enabled: Optional[bool] = None
    slot_duration_minutes: Optional[int] = Field(None, ge=15, le=180)
    buffer_minutes: Optional[int] = Field(None, ge=0, le=120)
    timezone: Optional[str] = Field(None, min_length=1, max_length=64)
    lookahead_days: Optional[int] = Field(None, ge=1, le=90)
    min_notice_hours: Optional[int] = Field(None, ge=0, le=168)
    default_title: Optional[str] = Field(None, min_length=1, max_length=200)
    default_interviewer_name: Optional[str] = Field(None, max_length=200)
    default_agenda: Optional[str] = None
    windows: Optional[List[AvailabilityWindowIn]] = None

    @field_validator("slot_duration_minutes")
    @classmethod
    def validate_slot_duration(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in ALLOWED_SLOT_DURATIONS:
            raise ValueError(
                f"slot_duration_minutes must be one of {sorted(ALLOWED_SLOT_DURATIONS)}"
            )
        return v

    @model_validator(mode="after")
    def windows_required_when_enabling(self) -> "ProviderInterviewSettingsUpdate":
        if self.auto_schedule_enabled is True:
            if self.windows is not None and len(self.windows) == 0:
                raise ValueError(
                    "At least one availability window is required when enabling auto-schedule"
                )
        return self


class ProviderInterviewSettingsOut(BaseModel):
    provider_id: str
    auto_schedule_enabled: bool
    slot_duration_minutes: int
    buffer_minutes: int
    timezone: str
    lookahead_days: int
    min_notice_hours: int
    default_title: str
    default_interviewer_name: Optional[str] = None
    default_agenda: Optional[str] = None
    # windows: List[AvailabilityWindowOut] = []
    windows: List[AvailabilityWindowOut] = Field(
        default_factory=list,
        # Look for the database attribute 'availability_windows' first during ORM loading
        validation_alias=AliasChoices("availability_windows", "windows")
    )
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_dt_as_utc_z(self, value: datetime) -> str:
        if value.tzinfo is None:
            dt = value.replace(tzinfo=timezone.utc)
        else:
            dt = value.astimezone(timezone.utc)
        s = dt.isoformat()
        return s.replace("+00:00", "Z") if s.endswith("+00:00") else s

    class Config:
        from_attributes = True


class AutoScheduleToggle(BaseModel):
    auto_schedule_enabled: bool


class SlotPreviewOut(BaseModel):
    scheduled_at: datetime
    scheduled_period: Optional[str] = None

    @field_serializer("scheduled_at", when_used="json")
    def serialize_scheduled_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            dt = value.replace(tzinfo=timezone.utc)
        else:
            dt = value.astimezone(timezone.utc)
        s = dt.isoformat()
        return s.replace("+00:00", "Z") if s.endswith("+00:00") else s


class SlotPreviewListOut(BaseModel):
    slots: List[SlotPreviewOut]
    slot_duration_minutes: int
    timezone: str
