import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

def _uuid():
    return str(uuid.uuid4())

class AIInterviewSession(Base):
    __tablename__ = "ai_interview_sessions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    application_id = Column(UUID(as_uuid=False), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    seeker_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=False), ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True)

    # Store the conversation history: [{"role": "bot", "content": "..."}, {"role": "user", "content": "..."}]
    chat_history = Column(JSON, default=list, nullable=False)
    
    status = Column(String(20), default="in_progress") # in_progress, completed, failed
    score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    application = relationship("Application")
    seeker = relationship("User", foreign_keys=[seeker_id])
    job = relationship("JobPosting")
