import uuid
import enum
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

try:
    from pgvector.sqlalchemy import Vector

    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

from database import Base


class UserRole(str, enum.Enum):
    seeker = "seeker"
    provider = "provider"
    superadmin = "superadmin"
    teacher = "teacher"


class JobType(str, enum.Enum):
    in_office = "in_office"
    wfh = "wfh"
    hybrid = "hybrid"


class CompanyType(str, enum.Enum):
    individual = "individual"
    company = "company"


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(15), nullable=False)
    hashed_password = Column(String(255), nullable=True)
    profile_pic_url = Column(Text, nullable=True)

    # Auth state
    is_super_admin = Column(Boolean, default=False, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    onboarding_complete = Column(Boolean, default=False, nullable=False)
    is_assessment_done = Column(Boolean, default=False, nullable=False)
    totp_secret = Column(String(32), nullable=True)
    totp_enabled = Column(Boolean, default=False, nullable=False)
    is_first_login = Column(Boolean, default=True, nullable=True)
    is_super_admin = Column(Boolean, default=False, nullable=False)

    # Role & profile
    role = Column(Enum(UserRole), nullable=True, index=True)

    # Seeker preferences
    industry = Column(String(100), nullable=True)
    job_role = Column(String(100), nullable=True)
    job_type = Column(Enum(JobType), nullable=True)
    salary_range = Column(String(50), nullable=True)
    experience = Column(String(50), nullable=True, index=True)
    auto_apply_enabled = Column(Boolean, default=False, nullable=False)

    # Provider info
    company_type = Column(Enum(CompanyType), nullable=True)
    company_name = Column(String(200), nullable=True)
    company_location = Column(String(200), nullable=True)
    company_address = Column(String(500), nullable=True)
    company_size = Column(String(50), nullable=True)

    # Excel Import New Fields
    father_or_mother_name = Column(String(200), nullable=True)
    gender = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    highest_qualification = Column(String(200), nullable=True)
    stream_specialization = Column(String(200), nullable=True)
    college_institute_name = Column(String(255), nullable=True)
    preferred_job_sector = Column(String(200), nullable=True)
    job_roles_offering = Column(Text, nullable=True)
    specific_requirements = Column(Text, nullable=True)

    # Seeker preferred locations (list of up to 5 cities/states)
    preferred_locations = Column(JSON, nullable=True)

    # Bulk import welcome email tracking (seekers)
    welcome_email_status = Column(String(20), nullable=True)  # pending | sent | failed
    welcome_email_error = Column(Text, nullable=True)

    # Profile embedding for similarity (1536 dims = text-embedding-3-small)
    if VECTOR_AVAILABLE:
        profile_embedding = Column(Vector(3072), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    resumes = relationship(
        "Resume", back_populates="user", cascade="all, delete-orphan"
    )
    job_postings = relationship(
        "JobPosting", back_populates="provider", cascade="all, delete-orphan"
    )
    applications = relationship(
        "Application",
        foreign_keys="Application.seeker_id",
        back_populates="seeker",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    support_tickets = relationship(
        "SupportTicket", back_populates="user", cascade="all, delete-orphan"
    )
    platform_feedback = relationship(
        "PlatformFeedback", back_populates="user", cascade="all, delete-orphan"
    )
    roadmaps = relationship(
        "Roadmap", back_populates="user", cascade="all, delete-orphan"
    )
    portfolio = relationship(
        "Portfolio",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    imported_password = relationship(
        "ImportedUserPassword",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
