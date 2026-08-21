import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class GoogleCalendarToken(Base):
    """Per-user OAuth credentials for Google Calendar auto-sync.

    One row per user who has connected their Google account. Presence of a row
    (with a refresh token) means the user opted into automatic calendar sync.
    """

    __tablename__ = "google_calendar_tokens"

    id = Column(String(50), primary_key=True, default=_uuid)
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    google_email = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_uri = Column(String(255), nullable=False, default="https://oauth2.googleapis.com/token")
    scopes = Column(Text, nullable=True)
    expiry = Column(DateTime, nullable=True)  # UTC access-token expiry
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
