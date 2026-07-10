import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Float, Boolean, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalEnrollment(Base):
    __tablename__ = "training_portal_enrollments"

    id = Column(String(50), primary_key=True, default=_uuid)
    candidate_user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    candidate_name = Column(String(200), nullable=False)
    candidate_email = Column(String(200), nullable=False, index=True)
    candidate_phone = Column(String(50), nullable=True)
    enrollment_type = Column(String(20), nullable=False, index=True)  # course | internship
    item_id = Column(String(50), nullable=False, index=True)
    batch_id = Column(String(50), ForeignKey("training_portal_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(300), nullable=False)
    batch_name = Column(String(200), nullable=True)
    enrollment_date = Column(String(50), nullable=False)
    payment_type = Column(String(30), nullable=False, default="Full Payment")
    payment_status = Column(String(30), nullable=False, default="pending", index=True)
    payment_mode = Column(String(30), nullable=True)
    total_fee = Column(Float, nullable=False, default=0.0)
    paid_amount = Column(Float, nullable=False, default=0.0)
    balance_due = Column(Float, nullable=False, default=0.0)
    installments = Column(JSON, nullable=False, default=list)
    status = Column(String(20), nullable=False, default="active", index=True)
    attendance_percentage = Column(Integer, nullable=False, default=0)
    completion_percentage = Column(Integer, nullable=False, default=0)
    is_certificate_issued = Column(Boolean, nullable=False, default=False)
    certificate_id = Column(String(100), nullable=True)
    certificate_status = Column(String(30), nullable=True)
    certificate_reason = Column(Text, nullable=True)
    voter_card_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    preferred_batch_id = Column(String(50), ForeignKey("training_portal_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    candidate_user = relationship("User", foreign_keys=[candidate_user_id])
    batch = relationship("TrainingPortalBatch", foreign_keys=[batch_id])
