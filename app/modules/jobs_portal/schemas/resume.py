from pydantic import BaseModel
from typing import List

# response for resume improvement suggesstions
class ResumeResponse(BaseModel):
    missing_skills: List[str]
    improvements: List[str]
    rewritten_bullets: List[str]
    ats_keywords: List[str]
    score: float
    futureTechToLearn: List[str]