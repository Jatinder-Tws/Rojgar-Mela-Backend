import uuid
import enum
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


class NotificationType(str, enum.Enum):
    interest = "interest"
    shortlisted = "shortlisted"
    rejected = "rejected"
    match = "match"
    application = "application"
    auto_match = "auto_match"
    welcome = "welcome"
    general = "general"


def _uuid():
    return str(uuid.uuid4())


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)

    # Optional references
    related_job_id = Column(UUID(as_uuid=False), nullable=True)
    related_user_id = Column(UUID(as_uuid=False), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="notifications")
