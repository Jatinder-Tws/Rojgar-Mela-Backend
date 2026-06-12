import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


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

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="platform_feedback")
