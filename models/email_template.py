import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSON, UUID

from database import Base


def _uuid():
    return str(uuid.uuid4())


class EmailTemplateCategory(str, enum.Enum):
    job_fair = "job_fair"
    announcement = "announcement"
    invitation = "invitation"
    custom = "custom"


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    subject = Column(String(500), nullable=False)
    html_body = Column(Text, nullable=False)
    design_config = Column(JSON, nullable=False, server_default=text("'{}'::json"))
    category = Column(
        Enum(EmailTemplateCategory, name="emailtemplatecategory"),
        nullable=False,
        server_default="custom",
    )
    placeholders = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, server_default=text("true"))
    is_system = Column(Boolean, default=False, nullable=False, server_default=text("false"))
    created_by = Column(
        "created_by_id",
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
