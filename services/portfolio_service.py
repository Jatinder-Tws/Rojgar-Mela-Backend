import json
from typing import Any, List

from models.user import User
from models.portfolio import Portfolio


def _coerce_json_list(value: Any) -> list:
    """Parse JSON list fields that may be stored as a JSON string."""
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return value if isinstance(value, list) else []


def normalize_skills(skills: Any) -> List[dict]:
    normalized: List[dict] = []
    for item in _coerce_json_list(skills):
        if isinstance(item, dict) and item.get("name"):
            normalized.append(
                {
                    "name": str(item["name"]).strip(),
                    "level": str(item.get("level") or "Intermediate").strip(),
                }
            )
        elif isinstance(item, str) and item.strip():
            normalized.append({"name": item.strip(), "level": "Intermediate"})
    return normalized


def _normalize_structured_items(items: Any, required_keys: tuple[str, ...]) -> List[dict]:
    out: List[dict] = []
    for item in _coerce_json_list(items):
        if not isinstance(item, dict):
            continue
        row = {key: item.get(key) for key in item.keys()}
        if all(str(row.get(key) or "").strip() for key in required_keys):
            out.append(row)
    return out


def normalize_work_experiences(items: Any) -> List[dict]:
    return _normalize_structured_items(items, ("company", "role"))


def normalize_education(items: Any) -> List[dict]:
    return _normalize_structured_items(items, ("institution", "degree"))


def normalize_certifications(items: Any) -> List[dict]:
    out: List[dict] = []
    for item in _coerce_json_list(items):
        if isinstance(item, dict) and str(item.get("name") or "").strip():
            out.append(item)
    return out


def normalize_languages(items: Any) -> List[dict]:
    return _normalize_structured_items(items, ("language",))


def normalize_projects(items: Any) -> List[dict]:
    return _normalize_structured_items(items, ("title",))


def calculate_completion(portfolio: Portfolio, user: User) -> tuple[int, list[str], list[str]]:
    """Calculate portfolio completion percentage and list filled/missing sections."""
    skills = normalize_skills(portfolio.skills)
    work_experiences = normalize_work_experiences(portfolio.work_experiences)
    education = normalize_education(portfolio.education)
    certifications = normalize_certifications(portfolio.certifications)
    languages = normalize_languages(portfolio.languages)
    projects = normalize_projects(portfolio.projects)

    sections = {
        "Personal Details": bool(user.first_name and user.last_name and user.email),
        "Headline": bool(portfolio.headline),
        "Bio / About Me": bool(portfolio.bio),
        "Location": bool(portfolio.city or portfolio.state),
        "Skills": bool(skills),
        "Work Experience": bool(work_experiences),
        "Education": bool(education),
        "Social Links": bool(portfolio.linkedin_url or portfolio.github_url or portfolio.website_url),
        "Certifications": bool(certifications),
        "Languages": bool(languages),
        "Projects": bool(projects),
        "Intro Video / Audio": bool(portfolio.intro_video_path or portfolio.intro_audio_path),
        "AI Assessment": bool(user.is_assessment_done),
    }
    filled = [k for k, v in sections.items() if v]
    missing = [k for k, v in sections.items() if not v]
    pct = int((len(filled) / len(sections)) * 100) if sections else 0
    return pct, filled, missing


def portfolio_json_fields(portfolio: Portfolio) -> dict:
    """Normalized portfolio JSON fields safe for PortfolioOut serialization."""
    return {
        "skills": normalize_skills(portfolio.skills),
        "work_experiences": normalize_work_experiences(portfolio.work_experiences),
        "education": normalize_education(portfolio.education),
        "certifications": normalize_certifications(portfolio.certifications),
        "languages": normalize_languages(portfolio.languages),
        "projects": normalize_projects(portfolio.projects),
    }
