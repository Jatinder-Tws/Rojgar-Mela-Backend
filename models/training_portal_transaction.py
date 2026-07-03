import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalTransaction(Base):
    __tablename__ = "training_portal_transactions"

    id = Column(String(50), primary_key=True, default=_uuid)
    transaction_id = Column(String(80), nullable=False, unique=True, index=True)
    enrollment_id = Column(
        String(50),
        ForeignKey("training_portal_enrollments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    candidate_email = Column(String(200), nullable=False, index=True)
    candidate_name = Column(String(200), nullable=False)
    program_title = Column(String(300), nullable=False)
    transaction_type = Column(String(30), nullable=False, index=True)
    amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), nullable=False, default="INR")
    payment_mode = Column(String(30), nullable=True)
    status = Column(String(30), nullable=False, default="completed", index=True)
    provider = Column(String(30), nullable=True)
    provider_transaction_id = Column(String(120), nullable=True, index=True)
    reference_order_id = Column(String(50), nullable=True)
    batch_id = Column(String(50), nullable=True)
    batch_name = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
