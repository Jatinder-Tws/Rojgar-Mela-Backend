import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


def _uuid():
    return str(uuid.uuid4())


class ImportedUserPassword(Base):
    __tablename__ = "imported_user_passwords"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    email = Column(String(255), nullable=True, index=True)
    plain_password = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="imported_password")
