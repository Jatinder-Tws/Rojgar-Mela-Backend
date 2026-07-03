import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime

from database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalCourseCategory(Base):
    __tablename__ = "training_portal_course_categories"

    id = Column(String(50), primary_key=True, default=_uuid)
    name = Column(String(100), unique=True, nullable=False, index=True)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
