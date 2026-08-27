import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class CareerRoadmap(Base):
    """CMS career roadmap shown on the public /roadmaps page and managed by Super Admin."""

    __tablename__ = "career_roadmaps"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=False, server_default="Technology")
    level = Column(String(50), nullable=False, server_default="Intermediate")
    industries = Column(JSON, nullable=False, server_default=text("'[]'::json"))
    short_description = Column(Text, nullable=True)
    long_description = Column(Text, nullable=True)
    skill_tags = Column(JSON, nullable=False, server_default=text("'[]'::json"))
    duration_months = Column(String(80), nullable=True)
    salary_lpa = Column(String(80), nullable=True)
    growth_percent = Column(String(80), nullable=True)
    openings_count = Column(String(80), nullable=True)
    steps = Column(JSON, nullable=False, server_default=text("'[]'::json"))
    resources = Column(JSON, nullable=False, server_default=text("'[]'::json"))
    career_insights = Column(JSON, nullable=False, server_default=text("'{}'::json"))
    faqs = Column(JSON, nullable=False, server_default=text("'[]'::json"))
    hero_image_url = Column(String(500), nullable=True)
    is_published = Column(Boolean, default=False, nullable=False, server_default=text("false"), index=True)
    is_featured = Column(Boolean, default=False, nullable=False, server_default=text("false"))
    is_trending = Column(Boolean, default=False, nullable=False, server_default=text("false"))
    sort_order = Column(Integer, default=0, nullable=False, server_default=text("0"))
    created_by = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
