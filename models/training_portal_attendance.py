import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalAttendanceRecord(Base):
    __tablename__ = "training_portal_attendance_records"
    __table_args__ = (
        UniqueConstraint(
            "class_session_id",
            "enrollment_id",
            "occurrence_date",
            name="uq_session_enrollment_occurrence_attendance",
        ),
    )

    id = Column(String(50), primary_key=True, default=_uuid)
    class_session_id = Column(
        String(50),
        ForeignKey("training_portal_class_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enrollment_id = Column(
        String(50),
        ForeignKey("training_portal_enrollments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    occurrence_date = Column(String(50), nullable=False, default="")
    batch_id = Column(String(50), nullable=True, index=True)
    candidate_email = Column(String(200), nullable=False, index=True)
    candidate_name = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False, default="present")
    marked_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    marked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
