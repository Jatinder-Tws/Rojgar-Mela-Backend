import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


class ApplicationStatus(str, enum.Enum):
    applied = "applied"
    shortlisted = "shortlisted"
    rejected = "rejected"
    auto_applied = "auto_applied"


def _uuid():
    return str(uuid.uuid4())


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    seeker_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    job_id = Column(UUID(as_uuid=False), ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True)

    # Guest candidate details
    candidate_name = Column(String(200), nullable=True)
    candidate_email = Column(String(200), nullable=True)
    candidate_phone = Column(String(20), nullable=True)
    candidate_experience = Column(String(100), nullable=True)
    candidate_resume_url = Column(Text, nullable=True)

    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.applied, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    ai_feedback = Column(JSON, nullable=True)   # Structured improvement suggestions

    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    seeker = relationship("User", foreign_keys=[seeker_id], back_populates="applications")
    job = relationship("JobPosting", back_populates="applications")
