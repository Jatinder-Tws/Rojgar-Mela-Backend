import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

try:
    from pgvector.sqlalchemy import Vector

    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

from app.core.database import Base


class JobType(str, enum.Enum):
    in_office = "in_office"
    wfh = "wfh"
    hybrid = "hybrid"


def _uuid():
    return str(uuid.uuid4())


class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    provider_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    required_skills = Column(JSON, nullable=True)  # list of skill strings
    experience_required = Column(String(100), nullable=True)
    job_type = Column(Enum(JobType), nullable=True)
    salary_range = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    posted_by_name = Column(String(200), nullable=True)  # recruiter display name
    location = Column(String(200), nullable=True)  # job location
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    post_count = Column(Integer, default=0, nullable=False)
    ai_interview_enabled = Column(Boolean, default=False, nullable=False)
    selection_threshold = Column(Integer, default=70, nullable=False)
    shift = Column(String(20), nullable=True)
    perks = Column(JSON, nullable=True)
    employment_type = Column(String(20), nullable=True)

    # Embedding for similarity search
    if VECTOR_AVAILABLE:
        embedding = Column(Vector(3072), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    provider = relationship("User", back_populates="job_postings")
    applications = relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )
    matches = relationship("Match", back_populates="job", cascade="all, delete-orphan")
