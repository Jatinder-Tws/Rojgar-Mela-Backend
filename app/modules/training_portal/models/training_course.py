import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, Date, DateTime, ForeignKey, JSON, UniqueConstraint, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base

def _uuid():
    return str(uuid.uuid4())


class TrainingCourse(Base):
    __tablename__ = "training_courses"

    id = Column(String(50), primary_key=True, default=_uuid)
    provider_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    brochure_url = Column(String(500), nullable=True)
    is_paid = Column(Boolean, default=False, nullable=False)
    price = Column(String(100), nullable=True)
    duration = Column(Integer, nullable=False)
    duration_unit = Column(String(50), default="month", nullable=False)  # "week" or "month"
    skills_learned = Column(JSON, nullable=True)  # list of skill tags
    has_certificate = Column(Boolean, default=True, nullable=False)
    company_name = Column(String(200), nullable=False)
    state = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    provider = relationship("User", foreign_keys=[provider_id])
    modules = relationship("TrainingModule", back_populates="course", order_by="TrainingModule.order_index", cascade="all, delete-orphan")
    applications = relationship("TrainingCourseApplication", back_populates="course", cascade="all, delete-orphan")


class TrainingModule(Base):
    __tablename__ = "training_modules"

    id = Column(String(50), primary_key=True, default=_uuid)
    course_id = Column(String(50), ForeignKey("training_courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, default=0, nullable=False)
    estimated_hours = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    course = relationship("TrainingCourse", back_populates="modules")
    topics = relationship("TrainingModuleTopic", back_populates="module", order_by="TrainingModuleTopic.order_index", cascade="all, delete-orphan")


class TrainingModuleTopic(Base):
    __tablename__ = "training_module_topics"

    id = Column(String(50), primary_key=True, default=_uuid)
    module_id = Column(String(50), ForeignKey("training_modules.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    module = relationship("TrainingModule", back_populates="topics")


class TrainingCourseApplication(Base):
    __tablename__ = "training_course_applications"

    id = Column(String(50), primary_key=True, default=_uuid)
    course_id = Column(String(50), ForeignKey("training_courses.id", ondelete="CASCADE"), nullable=False, index=True)
    seeker_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(100), nullable=False)
    location = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    course = relationship("TrainingCourse", back_populates="applications")
    seeker = relationship("User", foreign_keys=[seeker_id])

    __table_args__ = (
        UniqueConstraint("course_id", "seeker_id", name="uq_course_seeker_app"),
    )
