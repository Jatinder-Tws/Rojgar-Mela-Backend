"""
AI Feedback Service – analyze rejection reason against resume and provide
actionable improvement suggestions. Single GPT call per rejection.
"""
from __future__ import annotations
import json
import logging
from typing import Optional

from services.ai_service import get_ai

logger = logging.getLogger(__name__)


async def generate_rejection_feedback(
    resume_text: str,
    rejection_reason: str,
    job_title: str,
) -> dict:
    """
    Analyze reconciliation reason against resume and return structured improvement suggestions.
    Returns: {summary, missing_skills, improvement_areas, suggested_courses, overall_tips}
    """
    ai = get_ai()

    system = (
        "You are a career coach. Analyze why a candidate was rejected and "
        "provide constructive, actionable feedback to help them improve their resume "
        "and skills. Be specific, encouraging, and practical. "
        "Return ONLY valid JSON, no markdown, no prose outside JSON."
    )

    user_prompt = (
        f"Job Role: {job_title}\n\n"
        f"Rejection Reason from Recruiter: {rejection_reason}\n\n"
        f"Candidate Resume (excerpt):\n{resume_text[:2500]}\n\n"
        "Return JSON:\n"
        "{\n"
        '  "summary": "Brief 2-sentence overview of why the profile was rejected.",\n'
        '  "missing_skills": ["skill1", "skill2"],\n'
        '  "improvement_areas": ["area1", "area2"],\n'
        '  "suggested_courses": [{"name": "Course Name", "platform": "Coursera or Udemy etc"}],\n'
        '  "resume_tips": ["tip1", "tip2"],\n'
        '  "overall_encouragement": "Short motivational note"\n'
        "}\n\n"
        "Crucial: Make sure `suggested_courses` contains at least 1-2 realistic, known courses directly related to `missing_skills`. Provide real platform names like Coursera, Udemy, or edX."
    )

    raw = await ai.chat_completion(system, user_prompt)

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception as e:
        logger.warning(f"AI feedback parse error: {e}")
        return {
            "summary": f"You were not selected for the {job_title} role.",
            "missing_skills": [],
            "improvement_areas": ["Review job requirements and align your resume accordingly"],
            "suggested_courses": [],
            "resume_tips": ["Tailor your resume for each application"],
            "overall_encouragement": "Keep learning and applying — the right opportunity is ahead!",
        }

# """
# AI Feedback Service – analyze rejection reason against resume and provide
# actionable improvement suggestions. Single GPT call per rejection.
# """
# from __future__ import annotations
# import json
# import logging
# from typing import Optional

# from services.ai_service import get_ai

# logger = logging.getLogger(__name__)


# async def generate_rejection_feedback(
#     resume_text: str,
#     rejection_reason: str,
#     job_title: str,
# ) -> dict:
#     """
#     Analyze reconciliation reason against resume and return structured improvement suggestions.
#     Returns: {summary, missing_skills, improvement_areas, suggested_courses, overall_tips}
#     """
#     ai = get_ai()

#     system = (
#         "You are a career coach. Analyze why a candidate was rejected and "
#         "provide constructive, actionable feedback to help them improve their resume "
#         "and skills. Be specific, encouraging, and practical. "
#         "Return ONLY valid JSON, no markdown, no prose outside JSON."
#     )

#     user_prompt = (
#         f"Job Role: {job_title}\n\n"
#         f"Rejection Reason from Recruiter: {rejection_reason}\n\n"
#         f"Candidate Resume (excerpt):\n{resume_text[:2500]}\n\n"
#         "Return JSON:\n"
#         "{\n"
#         '  "summary": "Brief 2-sentence overview of why the profile was rejected.",\n'
#         '  "missing_skills": ["skill1", "skill2"],\n'
#         '  "improvement_areas": ["area1", "area2"],\n'
#         '  "suggested_courses": [{"name": "Course Name", "platform": "Coursera or Udemy etc"}],\n'
#         '  "resume_tips": ["tip1", "tip2"],\n'
#         '  "overall_encouragement": "Short motivational note"\n'
#         "}\n\n"
#         "Crucial: Make sure `suggested_courses` contains at least 1-2 realistic, known courses directly related to `missing_skills`. Provide real platform names like Coursera, Udemy, or edX."
#     )

#     raw = await ai.chat_completion(system, user_prompt)

#     try:
#         start = raw.find("{")
#         end = raw.rfind("}") + 1
#         return json.loads(raw[start:end])
#     except Exception as e:
#         logger.warning(f"AI feedback parse error: {e}")
#         return {
#             "summary": f"You were not selected for the {job_title} role.",
#             "missing_skills": [],
#             "improvement_areas": ["Review job requirements and align your resume accordingly"],
#             "suggested_courses": [],
#             "resume_tips": ["Tailor your resume for each application"],
#             "overall_encouragement": "Keep learning and applying — the right opportunity is ahead!",
#         }
