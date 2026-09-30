import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class EventRegistrationForm(Base):
    __tablename__ = "event_registration_forms"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    slug = Column(String(80), nullable=False, unique=True, index=True)
    event_name = Column(String(200), nullable=False)
    booth_location = Column(String(200), nullable=True)
    headline = Column(String(200), nullable=False, default="Get Your Lucky Scratch Ticket")
    subtitle = Column(Text, nullable=True)
    badge_label = Column(String(80), nullable=True)
    cta_label = Column(String(120), nullable=False, default="Register & Get Random Lucky Ticket")
    ticket_prefix = Column(String(12), nullable=False, default="TKT")
    lucky_draw_enabled = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    fields = Column(JSON, nullable=False, default=list)
    thank_you_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    prizes = relationship(
        "EventRegistrationPrize",
        back_populates="form",
        cascade="all, delete-orphan",
        order_by="EventRegistrationPrize.sort_order",
    )
    submissions = relationship(
        "EventRegistrationSubmission",
        back_populates="form",
        cascade="all, delete-orphan",
    )


class EventRegistrationPrize(Base):
    __tablename__ = "event_registration_prizes"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    form_id = Column(
        UUID(as_uuid=False),
        ForeignKey("event_registration_forms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False)
    category = Column(String(80), nullable=True)
    worth_value = Column(String(80), nullable=True)
    description = Column(Text, nullable=True)
    total_inventory = Column(Integer, nullable=False, default=0)
    remaining_inventory = Column(Integer, nullable=False, default=0)
    win_weight = Column(Integer, nullable=False, default=10)
    voucher_expiry_days = Column(Integer, nullable=True)
    redemption_instructions = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    form = relationship("EventRegistrationForm", back_populates="prizes")


class EventRegistrationSubmission(Base):
    __tablename__ = "event_registration_submissions"
    __table_args__ = (UniqueConstraint("ticket_number", name="uq_event_reg_ticket_number"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    form_id = Column(
        UUID(as_uuid=False),
        ForeignKey("event_registration_forms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enquiry_id = Column(UUID(as_uuid=False), nullable=True, index=True)
    answers = Column(JSON, nullable=False, default=dict)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    visitor_role = Column(String(120), nullable=True)
    organization = Column(String(200), nullable=True)
    interest = Column(String(200), nullable=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    ticket_number = Column(String(40), nullable=True)
    prize_id = Column(UUID(as_uuid=False), nullable=True)
    prize_title = Column(String(200), nullable=True)
    prize_category = Column(String(80), nullable=True)
    prize_worth = Column(String(80), nullable=True)
    redemption_instructions = Column(Text, nullable=True)
    is_winner = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    form = relationship("EventRegistrationForm", back_populates="submissions")
