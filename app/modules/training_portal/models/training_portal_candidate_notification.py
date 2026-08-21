import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Boolean

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalCandidateNotification(Base):
    __tablename__ = "training_portal_candidate_notifications"

    id = Column(String(50), primary_key=True, default=_uuid)
    candidate_email = Column(String(200), nullable=False, index=True)
    recipient_role = Column(String(30), nullable=False, default="candidate", index=True)
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    detail = Column(Text, nullable=True)
    event_date = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, default="info")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
