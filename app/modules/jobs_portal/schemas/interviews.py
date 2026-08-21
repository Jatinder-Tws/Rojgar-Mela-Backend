from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import AliasChoices, BaseModel, Field, field_serializer, field_validator

InterviewTypeLiteral = Literal["video", "walk_in"]
InterviewStatusLiteral = Literal["scheduled", "completed", "cancelled", "no_show"]
InterviewOutcomeLiteral = Literal["selected", "rejected"]


class InterviewCreate(BaseModel):
    seeker_id: str
    job_id: str
    title: str
    interviewer_name: str
    agenda: Optional[str] = None
    interview_type: InterviewTypeLiteral = "video"
    meeting_link: Optional[str] = None
    location: Optional[str] = None
    scheduled_at: datetime
    application_id: Optional[str] = None
    scheduled_period: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "scheduled_period",
            "scheduledPeriod",
            "schedule_period",
            "schedulePeriod",
        ),
    )

    @field_validator("scheduled_period", mode="before")
    @classmethod
    def normalize_scheduled_period(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip().upper()
        if not s:
            return None
        if s in ("AM", "PM"):
            return s
        raise ValueError("scheduled_period must be 'AM' or 'PM'")


class InterviewOut(BaseModel):
    id: str
    seeker_id: str
    provider_id: str
    job_id: str
    application_id: Optional[str] = None
    source: str = "manual"
    title: str
    interviewer_name: str
    agenda: Optional[str] = None
    interview_type: str = "video"
    meeting_link: Optional[str] = None
    location: Optional[str] = None
    status: str = "scheduled"
    scheduled_at: datetime
    created_at: datetime
    scheduled_period: Optional[str] = None

    # Enriched data for display
    seeker_name: Optional[str] = None
    provider_name: Optional[str] = None
    job_title: Optional[str] = None

    @field_serializer("scheduled_at", "created_at", when_used="json")
    def serialize_dt_as_utc_z(self, value: datetime) -> str:
        """Naive DB datetimes are UTC; emit Z so clients parse the instant correctly."""
        if value.tzinfo is None:
            dt = value.replace(tzinfo=timezone.utc)
        else:
            dt = value.astimezone(timezone.utc)
        s = dt.isoformat()
        return s.replace("+00:00", "Z") if s.endswith("+00:00") else s

    class Config:
        from_attributes = True


class InterviewOutcomeUpdate(BaseModel):
    outcome: InterviewOutcomeLiteral
    notes: Optional[str] = None
