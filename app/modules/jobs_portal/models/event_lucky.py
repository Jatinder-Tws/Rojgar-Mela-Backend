import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class EventLuckyEntry(Base):
    __tablename__ = "event_lucky_entries"
    __table_args__ = (UniqueConstraint("ticket_number", name="uq_event_lucky_ticket"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    # Physical column on the existing table is event_id.
    announcement_id = Column(
        "event_id",
        UUID(as_uuid=False),
        ForeignKey("site_announcements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    location = Column(String(250), nullable=True)
    role = Column(String(20), nullable=False)  # seeker | provider
    organization = Column(String(200), nullable=True)
    track = Column(String(20), nullable=True)  # tech | non_tech
    photo_url = Column(String(400), nullable=True)
    draw_eligible = Column(Boolean, nullable=False, default=True)
    ticket_number = Column(String(40), nullable=True)
    draw_date = Column(String(10), nullable=False, index=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    is_winner = Column(Boolean, nullable=False, default=False)
    enquiry_id = Column(UUID(as_uuid=False), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    verified_at = Column(DateTime, nullable=True)

    announcement = relationship("SiteAnnouncement")


class EventLuckyDraw(Base):
    __tablename__ = "event_lucky_draws"
    __table_args__ = (UniqueConstraint("announcement_id", "draw_date", name="uq_event_lucky_draw_day"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    announcement_id = Column(
        UUID(as_uuid=False),
        ForeignKey("site_announcements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    draw_date = Column(String(10), nullable=False)
    winner_entry_id = Column(UUID(as_uuid=False), nullable=True)
    revealed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
