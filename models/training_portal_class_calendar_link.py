import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from database import Base


def _uuid():
    return str(uuid.uuid4())


class TrainingPortalClassCalendarLink(Base):
    """Maps a class session + attendee user to the Google Calendar event created
    in that user's calendar, so we can update / delete it later.

    One row per (class session, user). Recurring sessions use a single Google
    event with an RRULE, so a single event id per attendee is sufficient.
    """

    __tablename__ = "training_portal_class_calendar_links"
    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_class_calendar_session_user"),
    )

    id = Column(String(50), primary_key=True, default=_uuid)
    session_id = Column(
        String(50),
        ForeignKey("training_portal_class_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    calendar_id = Column(String(255), nullable=False, default="primary")
    google_event_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
