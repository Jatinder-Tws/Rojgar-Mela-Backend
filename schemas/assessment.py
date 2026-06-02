from pydantic import BaseModel, EmailStr
from typing import List, Optional
from uuid import UUID

class AssessmentStart(BaseModel):
    experience_level: str
    domain_interest: str

class AssessmentAnswer(BaseModel):
    question: Optional[str] = None
    answer: str

class AssessmentComplete(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    password: str
    role: str = "seeker"

class AssessmentResultResponse(BaseModel):
    personality_type: str
    iq_score: int
    aptitude_score: int | None = None
    reasoning_score: int | None = None
    emotional_intelligence_score: int | None = None
    personality_score: int | None = None
    recommended_domains: List[str]
    detailed_evaluation: str
    tokens_utilized: int | None = None

    class Config:
        from_attributes = True
