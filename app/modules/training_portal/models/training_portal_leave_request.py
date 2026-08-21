import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalLeaveRequest(Base):
    __tablename__ = "training_portal_leave_requests"

    id = Column(String(50), primary_key=True, default=_uuid)
    requester_type = Column(String(20), nullable=False, default="student", index=True)
    candidate_email = Column(String(200), nullable=True, index=True)
    candidate_name = Column(String(200), nullable=True)
    teacher_email = Column(String(200), nullable=True, index=True)
    teacher_name = Column(String(200), nullable=True)
    session_id = Column(String(50), nullable=True)
    date = Column(String(50), nullable=False, index=True)
    batch_id = Column(String(50), nullable=True, index=True)
    batch_name = Column(String(200), nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    reviewed_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_role = Column(String(20), nullable=True)
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
