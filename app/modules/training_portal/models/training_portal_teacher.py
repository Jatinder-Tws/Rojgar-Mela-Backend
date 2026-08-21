import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalTeacher(Base):
    """Physical classroom instructor managed inside the rojgarmela-training admin portal."""

    __tablename__ = "training_portal_teachers"

    id = Column(String(50), primary_key=True, default=_uuid)
    created_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # Linked login account (role=teacher) in the main users table.
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, unique=True, index=True)
    phone = Column(String(50), nullable=False, default="+91 00000 00000")
    bio = Column(Text, nullable=False, default="Qualified physical classroom instructor.")
    subjects = Column(JSON, nullable=False, default=list)  # list of strings
    rating = Column(Float, nullable=False, default=5.0)
    status = Column(String(20), nullable=False, default="active", index=True)
    avatar = Column(String(500), nullable=True)
    login_username = Column(String(100), nullable=False, unique=True, index=True)
    login_password = Column(String(200), nullable=False)
    login_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id])
    login_user = relationship("User", foreign_keys=[user_id])