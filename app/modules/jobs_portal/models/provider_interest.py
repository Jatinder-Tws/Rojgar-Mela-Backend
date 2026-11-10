import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ProviderInterest(Base):
    """Provider expressed interest in a seeker profile (AI Matching → Show Interest)."""

    __tablename__ = "provider_interests"
    __table_args__ = (
        UniqueConstraint("provider_id", "seeker_id", name="uq_provider_interests_provider_seeker"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    provider_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seeker_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
