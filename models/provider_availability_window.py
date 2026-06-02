import uuid

from sqlalchemy import Column, ForeignKey, SmallInteger, Time,String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


def _uuid():
    return str(uuid.uuid4())


class ProviderAvailabilityWindow(Base):
    __tablename__ = "provider_availability_windows"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    provider_id = Column(
        UUID(as_uuid=False),
        ForeignKey("provider_interview_settings.provider_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week = Column(SmallInteger, nullable=False)  # 0=Monday … 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    # period = Column(String(2),nullable=True)  # AM / PM
    start_period = Column(String(2),nullable=True)  # AM / PM
    end_period = Column(String(2),nullable=True)  # AM / PM

    settings = relationship(
        "ProviderInterviewSettings",
        back_populates="availability_windows",
        foreign_keys=[provider_id],
    )
