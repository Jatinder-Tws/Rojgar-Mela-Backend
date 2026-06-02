import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


def _uuid():
    return str(uuid.uuid4())


class Match(Base):
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    seeker_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=False), ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True)

    score = Column(Float, nullable=False)            # 0–100
    highlights = Column(JSON, nullable=True)         # list of matching strengths
    gaps = Column(JSON, nullable=True)               # list of gaps/missing skills
    fit_reason = Column(String(500), nullable=True)  # Short GPT summary

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    seeker = relationship("User", foreign_keys=[seeker_id])
    job = relationship("JobPosting", back_populates="matches")
