import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Float, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class UserCreditAccount(Base):
    __tablename__ = "user_credit_accounts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    balance = Column(Float, default=10.0, nullable=False)  # 10 initial welcome credits
    total_earned = Column(Float, default=10.0, nullable=False)
    total_spent = Column(Float, default=0.0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="credit_account")


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    amount = Column(Float, nullable=False)  # Positive for earnings/purchases, negative for deductions
    transaction_type = Column(String(30), nullable=False)  # welcome_bonus, call_deduction, purchase
    description = Column(String(255), nullable=True)
    reference_id = Column(String(100), nullable=True)  # session_id or order_id
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CreditPurchaseOrder(Base):
    __tablename__ = "credit_purchase_orders"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    package_id = Column(String(50), nullable=False)  # starter_15, pro_50, ultimate_150
    credits = Column(Integer, nullable=False)
    amount_rupees = Column(Float, nullable=False)
    
    provider_order_id = Column(String(100), nullable=True, index=True)  # Razorpay order_id
    provider_payment_id = Column(String(100), nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, paid, failed
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
