import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Text, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

try:
    from pgvector.sqlalchemy import Vector

    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

from database import Base

def _uuid():
    return str(uuid.uuid4())

class ExternalCandidate(Base):
    __tablename__ = "external_candidates"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    job_id = Column(UUID(as_uuid=False), ForeignKey("job_postings.id", ondelete="SET NULL"), nullable=True, index=True)

    # Step 1: Personal Information
    full_name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    state = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    date_of_birth = Column(String(100), nullable=True)
    gender = Column(String(100), nullable=True)

    # Step 2: Job & Experience Details  
    sub_role = Column(String(100), nullable=True)
    industries = Column(JSON, nullable=True)  # List of industry specialties
    available_shift = Column(String(50), nullable=True)
    total_experience = Column(String(100), nullable=True)
    current_ctc = Column(String(50), nullable=True)
    current_designation = Column(String(100), nullable=True)
    year_of_passing = Column(String(50), nullable=True)
    skills = Column(Text, nullable=True)

    # Step 3: Final Submission
    source = Column(String(100), nullable=True)  # e.g., Instagram, LinkedIn
    resume_url = Column(Text, nullable=True)
    salary_slip_url = Column(Text, nullable=True)
    experience_letter_url = Column(Text, nullable=True)
    profile_picture_url = Column(Text, nullable=True)

    status = Column(String(50), default="pending")  # pending, reviewed, rejected, shortlisted
    is_matched = Column(Boolean, default=False, server_default="false", nullable=False)  # True once AI-matched to at least one job
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Profile embedding for vector similarity (3072 dims = gemini-embedding-001)
    if VECTOR_AVAILABLE:
        embedding = Column(Vector(3072), nullable=True)

    # Relationships
    job = relationship("JobPosting")
    matches = relationship("ExternalCandidateMatch", back_populates="candidate", cascade="all, delete-orphan")
