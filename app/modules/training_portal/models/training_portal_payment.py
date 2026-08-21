import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalPaymentSettings(Base):
    """Singleton-style portal payment method toggles."""

    __tablename__ = "training_portal_payment_settings"

    id = Column(String(50), primary_key=True, default="default")
    upi = Column(Boolean, nullable=False, default=True)
    card = Column(Boolean, nullable=False, default=True)
    emi = Column(Boolean, nullable=False, default=True)
    offline = Column(Boolean, nullable=False, default=True)
    email = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TrainingPortalPaymentOrder(Base):
    __tablename__ = "training_portal_payment_orders"

    id = Column(String(50), primary_key=True, default=_uuid)
    enrollment_id = Column(String(50), ForeignKey("training_portal_enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_email = Column(String(200), nullable=False, index=True)
    amount_paise = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    payment_method = Column(String(30), nullable=False, default="upi")
    payment_purpose = Column(String(20), nullable=False, default="full")
    provider = Column(String(30), nullable=False, default="razorpay")
    provider_order_id = Column(String(100), nullable=True, index=True)
    provider_payment_id = Column(String(100), nullable=True, index=True)
    provider_signature = Column(String(300), nullable=True)
    status = Column(String(30), nullable=False, default="created", index=True)
    webhook_payload = Column(JSON, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
