import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from database import Base


def _uuid():
    return str(uuid.uuid4())


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    # Track the basic seed info
    experience_level = Column(String(50), nullable=True)
    domain_interest = Column(String(100), nullable=True)
    
    # Store Q&A history as JSON to maintain context
    qa_history = Column(JSON, default=list, nullable=False)
    
    # State tracking
    status = Column(String(20), default="in_progress") # in_progress, completed
    tokens_utilized = Column(Integer, default=0, nullable=False)
    cost = Column(Float, nullable=True)  # monetary cost based on token usage
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)



class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id = Column(UUID(as_uuid=False), ForeignKey("assessment_sessions.id", ondelete="CASCADE"), unique=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Store the final evaluation
    personality_type = Column(String(100), nullable=True)
    personality_score = Column(Integer, nullable=True)
    iq_score = Column(Integer, nullable=True)
    aptitude_score = Column(Integer, nullable=True)
    reasoning_score = Column(Integer, nullable=True)
    emotional_intelligence_score = Column(Integer, nullable=True)
    recommended_domains = Column(JSON, default=list, nullable=False)
    detailed_evaluation = Column(String, nullable=True)
    tokens_utilized = Column(Integer, default=0, nullable=False)
    cost = Column(Float, nullable=True)  # monetary cost based on token usage
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
