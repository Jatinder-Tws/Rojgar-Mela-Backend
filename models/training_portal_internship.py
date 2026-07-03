import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Float, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalInternship(Base):
    """Physical offline internship managed inside the rojgarmela-training admin portal."""

    __tablename__ = "training_portal_internships"

    id = Column(String(50), primary_key=True, default=_uuid)
    created_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    duration = Column(String(50), nullable=False)
    is_paid = Column(Boolean, nullable=False, default=True)
    fee = Column(Float, nullable=False, default=0.0)
    start_date = Column(String(50), nullable=False)
    end_date = Column(String(50), nullable=False)
    venue = Column(String(300), nullable=False)
    max_seats = Column(Integer, nullable=False, default=15)
    seats_filled = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="active", index=True)
    laptop_required = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id])