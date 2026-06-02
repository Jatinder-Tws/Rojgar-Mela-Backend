import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
import enum

def _uuid():
    return str(uuid.uuid4())

class InterviewSource(str,enum.Enum):
    manual = "manual"
    auto = "auto"

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    seeker_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=False), ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    agenda = Column(Text, nullable=True)
    scheduled_at = Column(DateTime, nullable=False)
    scheduled_period = Column(String(2), nullable=True)
    interviewer_name = Column(String(200),nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    seeker = relationship("User", foreign_keys=[seeker_id])
    provider = relationship("User", foreign_keys=[provider_id])
    job = relationship("JobPosting")
    application_id = Column(UUID(as_uuid=False),ForeignKey("applications.id", ondelete="SET NULL"),nullable=True,index=True)
    source = Column(Enum(InterviewSource),default=InterviewSource.manual,nullable=False)
    application = relationship("Application",foreign_keys=[application_id])