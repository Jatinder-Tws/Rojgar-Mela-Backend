import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalRefundRequest(Base):
    __tablename__ = "training_portal_refund_requests"

    id = Column(String(50), primary_key=True, default=_uuid)
    enrollment_id = Column(
        String(50),
        ForeignKey("training_portal_enrollments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_email = Column(String(200), nullable=False, index=True)
    candidate_name = Column(String(200), nullable=False)
    program_title = Column(String(300), nullable=False)
    requested_amount = Column(Float, nullable=False, default=0.0)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    admin_notes = Column(Text, nullable=True)
    resolved_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
