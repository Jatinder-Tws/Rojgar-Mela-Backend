import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class FeedbackCategory(str, enum.Enum):
    general = "general"
    platform = "platform"
    feature_request = "feature_request"
    bug_report = "bug_report"
    other = "other"


class PlatformFeedback(Base):
    __tablename__ = "platform_feedback"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    rating = Column(Integer, nullable=False)
    category = Column(Enum(FeedbackCategory), nullable=False, default=FeedbackCategory.general)
    comment = Column(Text, nullable=False)
    page_context = Column(String(100), nullable=True)

    # Admin response on the same feedback row (no separate reply table).
    admin_reply = Column(Text, nullable=True)
    admin_replied_by = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admin_replied_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id], back_populates="platform_feedback")
    replied_by_user = relationship("User", foreign_keys=[admin_replied_by])
