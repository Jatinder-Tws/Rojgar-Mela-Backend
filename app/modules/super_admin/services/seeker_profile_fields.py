"""Apply admin-entered seeker profile fields onto User + Portfolio."""

from typing import Any

SEEKER_PROFILE_KEYS = (
    "preferred_locations",
    "father_or_mother_name",
    "gender",
    "address",
    "highest_qualification",
    "stream_specialization",
    "college_institute_name",
    "preferred_job_sector",
    "headline",
    "bio",
    "date_of_birth",
    "city",
    "state",
    "linkedin_url",
    "github_url",
    "website_url",
    "total_experience_years",
    "current_company",
    "current_role",
    "skills",
    "work_experiences",
    "education",
    "certifications",
    "languages",
    "projects",
)

_USER_TEXT = (
    "father_or_mother_name",
    "gender",
    "address",
    "highest_qualification",
    "stream_specialization",
    "college_institute_name",
    "preferred_job_sector",
)

_PORTFOLIO_TEXT = (
    "headline",
    "bio",
    "date_of_birth",
    "gender",
    "city",
    "state",
    "linkedin_url",
    "github_url",
    "website_url",
    "current_company",
    "current_role",
)

_LIST_FIELDS = (
    "skills",
    "work_experiences",
    "education",
    "certifications",
    "languages",
    "projects",
)


def seeker_profile_payload(body: Any, *, exclude_unset: bool) -> dict:
    data = body.model_dump(exclude_unset=exclude_unset)
    return {key: data[key] for key in SEEKER_PROFILE_KEYS if key in data}


def apply_seeker_profile_fields(user: Any, portfolio: Any, data: dict) -> None:
    """Write only keys present in data. Empty lists clear that section."""
    if "preferred_locations" in data:
        locs = data.get("preferred_locations") or []
        user.preferred_locations = locs or None

    for field in _USER_TEXT:
        if field in data:
            setattr(user, field, data[field])

    for field in _PORTFOLIO_TEXT:
        if field in data:
            setattr(portfolio, field, data[field])

    if "total_experience_years" in data:
        portfolio.total_experience_years = data["total_experience_years"]

    for field in _LIST_FIELDS:
        if field in data and data[field] is not None:
            setattr(portfolio, field, list(data[field]))
