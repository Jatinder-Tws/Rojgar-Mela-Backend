import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class EventCategory(Base):
    __tablename__ = "event_categories"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    key = Column(String(80), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon_name = Column(String(50), nullable=False, default="Sparkles")
    tag_color = Column(String(30), nullable=False, default="#64748B")
    pill_bg = Column(String(50), nullable=False, default="rgba(100, 116, 139, 0.1)")
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_builtin = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
