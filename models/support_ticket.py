import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


def _uuid():
    return str(uuid.uuid4())


class TicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class TicketCategory(str, enum.Enum):
    account = "account"
    technical = "technical"
    jobs = "jobs"
    billing = "billing"
    other = "other"


class TicketPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticket_number = Column(String(32), unique=True, nullable=False, index=True)

    category = Column(Enum(TicketCategory), nullable=False, default=TicketCategory.other)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), nullable=False, default=TicketStatus.open, index=True)
    priority = Column(Enum(TicketPriority), nullable=False, default=TicketPriority.medium)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    bot_handled = Column(Boolean, default=False, nullable=False)
    escalated_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="support_tickets")
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketMessage.created_at")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    ticket_id = Column(UUID(as_uuid=False), ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    body = Column(Text, nullable=False)
    is_staff_reply = Column(Boolean, default=False, nullable=False)
    is_bot_reply = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ticket = relationship("SupportTicket", back_populates="messages")
    author = relationship("User")
