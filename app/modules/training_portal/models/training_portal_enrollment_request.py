import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalEnrollmentRequest(Base):
    """Candidate-submitted request to enroll in a course, reviewed by a super admin
    before being converted into a real TrainingPortalEnrollment."""

    __tablename__ = "training_portal_enrollment_requests"

    id = Column(String(50), primary_key=True, default=_uuid)
    candidate_user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    candidate_name = Column(String(200), nullable=False)
    candidate_email = Column(String(200), nullable=False, index=True)
    candidate_phone = Column(String(50), nullable=True)
    gender = Column(String(30), nullable=True)
    qualification = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)

    course_id = Column(String(50), ForeignKey("training_portal_courses.id", ondelete="CASCADE"), nullable=False, index=True)
    course_title = Column(String(300), nullable=False)
    preferred_batch_id = Column(String(50), nullable=True)

    payment_preference = Column(String(30), nullable=False, default="Full Payment")
    total_fee = Column(Float, nullable=False, default=0.0)

    laptop_confirmed = Column(Boolean, nullable=False, default=False)
    attendance_policy_agreed = Column(Boolean, nullable=False, default=False)
    certification_policy_agreed = Column(Boolean, nullable=False, default=False)

    notes = Column(JSON, nullable=False, default=list)

    status = Column(String(30), nullable=False, default="pending", index=True)
    resolved_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    enrollment_id = Column(String(50), nullable=True)

    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
