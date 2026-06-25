import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, Date, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base

def _uuid():
    return str(uuid.uuid4())


class CompanyInternship(Base):
    __tablename__ = "company_internships"

    id = Column(String(50), primary_key=True, default=_uuid)
    provider_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    brochure_url = Column(String(500), nullable=True)
    is_stipend = Column(Boolean, default=False, nullable=False)
    stipend_amount = Column(String(100), nullable=True)
    duration = Column(Integer, nullable=False)
    duration_unit = Column(String(50), default="month", nullable=False)  # "week" or "month"
    state = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    apply_by = Column(Date, nullable=True)
    start_date = Column(String(200), nullable=True)
    company_name = Column(String(200), nullable=False)
    who_can_apply = Column(Text, nullable=True)
    skills_required = Column(JSON, nullable=True)  # list of skill tags
    perks = Column(JSON, nullable=True)  # list of perks/certificates
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    provider = relationship("User", foreign_keys=[provider_id])
    applications = relationship("CompanyInternshipApplication", back_populates="internship", cascade="all, delete-orphan")


class CompanyInternshipApplication(Base):
    __tablename__ = "company_internship_applications"

    id = Column(String(50), primary_key=True, default=_uuid)
    internship_id = Column(String(50), ForeignKey("company_internships.id", ondelete="CASCADE"), nullable=False, index=True)
    seeker_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    why_join = Column(Text, nullable=False)
    career_goals = Column(Text, nullable=False)
    why_consider = Column(Text, nullable=False)
    resume_url = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    internship = relationship("CompanyInternship", back_populates="applications")
    seeker = relationship("User", foreign_keys=[seeker_id])

    __table_args__ = (
        UniqueConstraint("internship_id", "seeker_id", name="uq_internship_seeker_app"),
    )
