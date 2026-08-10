import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from database import Base


def _uuid():
    return str(uuid.uuid4())


DEFAULT_CONTACT_STATUS = "new"


class ContactInquiry(Base):
    __tablename__ = "contact_inquiries"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    subject = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String(40), nullable=False, default=DEFAULT_CONTACT_STATUS)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
