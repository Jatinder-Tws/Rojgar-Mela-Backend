import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


def _uuid():
    return str(uuid.uuid4())


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Personal details
    headline = Column(String(200), nullable=True)
    bio = Column(Text, nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    gender = Column(String(20), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    website_url = Column(String(500), nullable=True)

    # Professional summary
    total_experience_years = Column(Float, nullable=True)
    current_company = Column(String(200), nullable=True)
    current_role = Column(String(200), nullable=True)

    # Structured JSON fields
    skills = Column(JSON, nullable=True)             # [{name, level}]
    work_experiences = Column(JSON, nullable=True)   # [{company, role, start_date, end_date, description, is_current}]
    education = Column(JSON, nullable=True)          # [{institution, degree, field, start_year, end_year}]
    certifications = Column(JSON, nullable=True)     # [{name, issuer, date, url}]
    languages = Column(JSON, nullable=True)          # [{language, proficiency}]
    projects = Column(JSON, nullable=True)           # [{title, description, url, technologies}]

    # Media
    intro_video_path = Column(String(500), nullable=True)
    intro_video_filename = Column(String(255), nullable=True)
    intro_audio_path = Column(String(500), nullable=True)
    intro_audio_filename = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="portfolio", uselist=False)
