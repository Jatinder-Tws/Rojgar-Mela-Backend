import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.shared.models.user import User


def _uuid():
    return str(uuid.uuid4())


class AuthProviderSettings(Base):
    __tablename__ = "auth_provider_settings"

    provider = Column(String(32), primary_key=True)  # google | github | linkedin
    is_enabled = Column(Boolean, default=True, nullable=False)
    enabled_for_roles = Column(ARRAY(String), nullable=False)
    enabled_on_register = Column(Boolean, default=True, nullable=False)
    enabled_on_login = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=1, nullable=False)
    updated_by = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuthSettingsHistory(Base):
    __tablename__ = "auth_settings_history"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    provider = Column(String(32), nullable=False, index=True)
    changed_by = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    changed_by_user = relationship("User", foreign_keys=[changed_by])
