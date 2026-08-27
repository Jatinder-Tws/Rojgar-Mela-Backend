import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class CareerRoadmapOption(Base):
    """Admin-managed dropdown values for career roadmaps (category, level, industry, etc.)."""

    __tablename__ = "career_roadmap_options"
    __table_args__ = (
        UniqueConstraint("kind", "name", name="uq_career_roadmap_options_kind_name"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    kind = Column(String(40), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False, server_default=text("0"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
