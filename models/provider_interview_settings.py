from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class ProviderInterviewSettings(Base):
    __tablename__ = "provider_interview_settings"

    provider_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    auto_schedule_enabled = Column(Boolean, default=False, nullable=False)
    slot_duration_minutes = Column(Integer, default=30, nullable=False)
    buffer_minutes = Column(Integer, default=0, nullable=False)
    timezone = Column(String(64), default="UTC", nullable=False)
    lookahead_days = Column(Integer, default=14, nullable=False)
    min_notice_hours = Column(Integer, default=24, nullable=False)
    default_title = Column(String(200), default="Interview", nullable=False)
    default_interviewer_name = Column(String(200), nullable=True)
    default_agenda = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    provider = relationship("User", foreign_keys=[provider_id])
    availability_windows = relationship(
        "ProviderAvailabilityWindow",
        back_populates="settings",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
