import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

def _uuid():
    return str(uuid.uuid4())

class AICoachSession(Base):
    __tablename__ = "ai_coach_sessions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    seeker_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    target_role = Column(String(100), nullable=False)
    experience_level = Column(String(50), nullable=False)
    focus_area = Column(String(50), default="General", nullable=False)
    mode = Column(String(10), default="text", nullable=False)  # "text" | "live"

    # Store the conversation history: [{"role": "bot", "content": "..."}, {"role": "user", "content": "..."}]
    chat_history = Column(JSON, default=list, nullable=False)
    
    status = Column(String(20), default="in_progress") # in_progress, completed, failed
    
    # Detailed scores
    overall_score = Column(Integer, nullable=True)
    communication_score = Column(Integer, nullable=True)
    content_score = Column(Integer, nullable=True)
    
    # Analysis & insights
    general_feedback = Column(Text, nullable=True)
    strengths = Column(JSON, default=list, nullable=True) # list of strings
    gaps = Column(JSON, default=list, nullable=True) # list of strings
    improvement_steps = Column(JSON, default=list, nullable=True) # list of strings
    
    # Visual & Delivery review
    video_feedback = Column(JSON, nullable=True) # dict with details on posture, eye contact, expressions
    
    total_tokens = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    seeker = relationship("User", foreign_keys=[seeker_id])
