import secrets
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def generate_check_in_slug() -> str:
    return secrets.token_urlsafe(18)


ATTENDANCE_PENDING = "pending"
ATTENDANCE_PRESENT = "present"

CERTIFICATE_PENDING = "pending"
CERTIFICATE_SENT = "sent"
CERTIFICATE_FAILED = "failed"

DEFAULT_VISIT_SLUG = "office-industrial-visit"
DEFAULT_VISIT_TITLE = "Tekki Web Solutions Industrial Training Visit 2026"
DEFAULT_VISIT_VENUE = (
    "Tekki Web Solutions Pvt. Ltd., Bajwa Colony, 67-68, Dhandra Rd, "
    "near Green City, Dhandra, Ludhiana, Mahmudpura, Punjab 141116"
)
PLACEHOLDER_VISIT_TITLES = {"Office Industrial Visit"}
PLACEHOLDER_VISIT_VENUES = {"Rojgar Mela Office", "Rojgar Mela Office HQ"}


class IndustrialVisit(Base):
    __tablename__ = "industrial_visits"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    title = Column(String(200), nullable=False)
    visit_date = Column(DateTime, nullable=False)
    venue = Column(String(300), nullable=True)
    college_name = Column(String(200), nullable=True)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    check_in_slug = Column(String(80), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    certificates_sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    students = relationship(
        "IndustrialVisitStudent",
        back_populates="visit",
        cascade="all, delete-orphan",
    )


class IndustrialVisitStudent(Base):
    __tablename__ = "industrial_visit_students"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    visit_id = Column(
        UUID(as_uuid=False),
        ForeignKey("industrial_visits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name = Column(String(150), nullable=False)
    college_name = Column(String(200), nullable=False)
    department = Column(String(120), nullable=False)
    year_of_study = Column(String(40), nullable=False)
    email = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    location = Column(String(120), nullable=False)
    area_of_interest = Column(String(500), nullable=False)
    graduation_year = Column(String(10), nullable=False)
    attendance_status = Column(String(20), nullable=False, default=ATTENDANCE_PENDING)
    attended_at = Column(DateTime, nullable=True)
    certificate_status = Column(String(20), nullable=False, default=CERTIFICATE_PENDING)
    certificate_sent_at = Column(DateTime, nullable=True)
    certificate_id = Column(String(40), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    visit = relationship("IndustrialVisit", back_populates="students")

    __table_args__ = (
        UniqueConstraint("visit_id", "email", name="uq_industrial_visit_student_email"),
        Index("ix_iv_students_visit_attendance", "visit_id", "attendance_status"),
        Index("ix_iv_students_visit_certificate", "visit_id", "certificate_status"),
        Index("ix_iv_students_phone", "phone"),
    )
