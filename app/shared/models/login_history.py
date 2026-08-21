import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class LoginHistory(Base):
    __tablename__ = "login_history"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    method = Column(String(32), nullable=True)  # password | google | github | linkedin
    status = Column(String(16), nullable=False, default="success")  # success | failed | blocked
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    device_label = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="login_history")
