import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


# new | contacted | follow_up_required | visit_scheduled | counselling_done | converted | lost
DEFAULT_STATUS = "new"


class CareerEnquiry(Base):
    __tablename__ = "career_enquiries"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    qualification = Column(String(100), nullable=False)
    domain = Column(String(150), nullable=False)
    message = Column(Text, nullable=True)
    status = Column(String(40), nullable=False, default=DEFAULT_STATUS)
    admin_notes = Column(Text, nullable=True)
    last_contact_date = Column(DateTime, nullable=True)
    next_follow_up_date = Column(DateTime, nullable=True)
    preferred_call_time = Column(String(120), nullable=True)
    interested_after_fee = Column(String(20), nullable=True)
    main_objection = Column(String(255), nullable=True)
    final_outcome = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
