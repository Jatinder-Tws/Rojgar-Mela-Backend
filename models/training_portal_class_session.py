import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID

from database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalClassSession(Base):
    __tablename__ = "training_portal_class_sessions"

    id = Column(String(50), primary_key=True, default=_uuid)
    batch_id = Column(String(50), ForeignKey("training_portal_batches.id", ondelete="CASCADE"), nullable=True, index=True)
    item_id = Column(String(50), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    instructor_name = Column(String(200), nullable=False)
    date = Column(String(50), nullable=False)
    start_time = Column(String(50), nullable=False)
    end_time = Column(String(50), nullable=False)
    days = Column(JSON, nullable=False, default=list)
    venue = Column(String(300), nullable=True)
    note = Column(Text, nullable=True)
    schedule_type = Column(String(20), nullable=False, default="one_time")
    postponed = Column(Boolean, nullable=False, default=False)
    teacher_unavailable = Column(Boolean, nullable=False, default=False)
    live_status = Column(String(20), nullable=False, default="scheduled", index=True)
    live_occurrence_date = Column(String(50), nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    session_report = Column(Text, nullable=True)
    covered_topic_ids = Column(JSON, nullable=False, default=list)
    reminder_sent = Column(Boolean, nullable=False, default=False)
    reminder_15_sent = Column(Boolean, nullable=False, default=False)
    late_start_reason = Column(Text, nullable=True)
    early_end_reason = Column(Text, nullable=True)
    attendance_marked = Column(Boolean, nullable=False, default=False)
    created_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
