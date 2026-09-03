import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class AuditLog(Base):
    """
    Audit log table for recording actions performed by non-super-admin users:
    - Supervisor
    - Teacher / Instructor
    - Job Seeker
    - Student / Learner
    - Job Provider / Employer

    Note: Super-Admin actions are excluded by design.
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)

    # Actor information snapshot
    actor_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_name = Column(String(150), nullable=False, default="Unknown User")
    actor_email = Column(String(255), nullable=True, index=True)
    actor_role = Column(String(50), nullable=False, index=True)  # supervisor, teacher, seeker, provider, student

    # Action metadata
    action = Column(String(80), nullable=False, index=True)  # CREATE, UPDATE, DELETE, ATTENDANCE_MARK, ENROLL, APPLICATION_SUBMIT, STATUS_CHANGE, LEAVE_APPLY, PAYMENT_RECORD, etc.
    entity_type = Column(String(80), nullable=False, index=True)  # batch, student, teacher, job, application, attendance, fee, leave, blog, certificate, interview, etc.
    entity_id = Column(String(120), nullable=True, index=True)
    entity_name = Column(String(255), nullable=True)  # Snapshot human name (e.g. "Batch MERN-2026", "Senior Frontend Dev")

    # Detailed description and diff
    description = Column(Text, nullable=False)
    changes = Column(JSON, nullable=True)  # {"before": {...}, "after": {...}} or action context

    # Request context
    request_path = Column(String(255), nullable=True)
    request_method = Column(String(20), nullable=True)
    ip_address = Column(String(60), nullable=True)
    user_agent = Column(String(300), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    actor = relationship("User", foreign_keys=[actor_id], lazy="select")

    __table_args__ = (
        Index("ix_audit_logs_role_created", "actor_role", "created_at"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )
