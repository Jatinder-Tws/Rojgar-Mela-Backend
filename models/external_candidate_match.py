import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


def _uuid():
    return str(uuid.uuid4())


class ExternalCandidateMatch(Base):
    """
    Stores AI match scores between external (guest) candidates and job postings.
    Separate from the main `matches` table which requires a registered seeker user.
    """
    __tablename__ = "external_candidate_matches"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    candidate_id = Column(
        UUID(as_uuid=False),
        ForeignKey("external_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id = Column(
        UUID(as_uuid=False),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    score = Column(Float, nullable=False)           # 0–100
    highlights = Column(JSON, nullable=True)        # list of matching strengths
    gaps = Column(JSON, nullable=True)              # list of gaps/missing skills
    fit_reason = Column(String(500), nullable=True) # Short GPT summary

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    candidate = relationship("ExternalCandidate", back_populates="matches")
    job = relationship("JobPosting")
