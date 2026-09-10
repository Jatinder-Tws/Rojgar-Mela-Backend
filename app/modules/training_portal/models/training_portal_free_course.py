import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalFreeCourse(Base):
    """Public YouTube playlist course that anyone can watch on Rojgar Mela."""

    __tablename__ = "training_portal_free_courses"

    id = Column(String(50), primary_key=True, default=_uuid)
    created_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    youtube_url = Column(String(500), nullable=False)
    playlist_id = Column(String(80), nullable=True, unique=True, index=True)
    thumbnail_url = Column(String(500), nullable=True)
    channel_title = Column(String(200), nullable=True)
    status = Column(String(20), nullable=False, default="published", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id])
    lessons = relationship(
        "TrainingPortalFreeCourseLesson",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="TrainingPortalFreeCourseLesson.sort_order",
    )
    resources = relationship(
        "TrainingPortalFreeCourseResource",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="TrainingPortalFreeCourseResource.sort_order",
    )


class TrainingPortalFreeCourseLesson(Base):
    __tablename__ = "training_portal_free_course_lessons"

    id = Column(String(50), primary_key=True, default=_uuid)
    course_id = Column(
        String(50),
        ForeignKey("training_portal_free_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    youtube_video_id = Column(String(32), nullable=False)
    youtube_url = Column(String(300), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    course = relationship("TrainingPortalFreeCourse", back_populates="lessons")


class TrainingPortalFreeCourseResource(Base):
    __tablename__ = "training_portal_free_course_resources"

    id = Column(String(50), primary_key=True, default=_uuid)
    course_id = Column(
        String(50),
        ForeignKey("training_portal_free_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category = Column(String(30), nullable=False, index=True)
    url = Column(String(700), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    course = relationship("TrainingPortalFreeCourse", back_populates="resources")
