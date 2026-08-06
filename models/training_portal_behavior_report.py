import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey

from database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalBehaviorReport(Base):
    __tablename__ = "training_portal_behavior_reports"

    id = Column(String(50), primary_key=True, default=_uuid)
    enrollment_id = Column(String(50), ForeignKey("training_portal_enrollments.id", ondelete="SET NULL"), nullable=True, index=True)
    candidate_name = Column(String(200), nullable=False)
    candidate_email = Column(String(200), nullable=False, index=True)
    batch_id = Column(String(50), ForeignKey("training_portal_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    batch_name = Column(String(200), nullable=True)
    instructor_id = Column(String(50), nullable=True, index=True)
    instructor_name = Column(String(200), nullable=False)
    teacher_email = Column(String(200), nullable=True, index=True)
    report_date = Column(String(50), nullable=False, index=True)
    discipline_rating = Column(Integer, nullable=False, default=4)
    participation_rating = Column(Integer, nullable=False, default=4)
    performance_rating = Column(Integer, nullable=False, default=4)
    comments = Column(Text, nullable=False)
    flagged_for_review = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
