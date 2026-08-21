import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalBatch(Base):
    __tablename__ = "training_portal_batches"

    id = Column(String(50), primary_key=True, default=_uuid)
    course_id = Column(String(50), ForeignKey("training_portal_courses.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_name = Column(String(200), nullable=False)
    instructor_id = Column(String(50), nullable=True)
    instructor_name = Column(String(200), nullable=False)
    start_date = Column(String(50), nullable=False)
    end_date = Column(String(50), nullable=False)
    days = Column(JSON, nullable=False, default=list)
    time_slot = Column(String(100), nullable=False, default="To be scheduled")
    venue = Column(String(300), nullable=False, default="To be scheduled")
    max_seats = Column(Integer, nullable=False, default=20)
    delivery_mode = Column(String(20), nullable=False, default="Offline")
    status = Column(String(20), nullable=False, default="upcoming", index=True)
    covered_topics = Column(JSON, nullable=False, default=list)
    created_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id])
