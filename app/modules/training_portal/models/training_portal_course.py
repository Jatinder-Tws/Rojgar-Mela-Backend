import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalCourse(Base):
    """Physical training course managed inside the rojgarmela-training admin portal."""

    __tablename__ = "training_portal_courses"

    id = Column(String(50), primary_key=True, default=_uuid)
    created_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    duration = Column(String(50), nullable=False)
    delivery_mode = Column(String(20), nullable=False, default="Offline")
    status = Column(String(20), nullable=False, default="published", index=True)
    skill_level = Column(String(20), nullable=False, default="Beginner")
    fee = Column(Float, nullable=False, default=12000.0)
    emi_fee = Column(Float, nullable=True, default=None)
    thumbnail_url = Column(String(500), nullable=True)
    prerequisites = Column(Text, nullable=True)
    key_highlights = Column(JSON, nullable=False, default=list)
    curriculum = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id])
