"""Shared job-role quality rules for seeker/admin profile writes."""

from __future__ import annotations

import re
from typing import Optional

JOB_ROLE_MAX_LEN = 100
JOB_ROLE_MIN_LETTERS = 3

_EXPERIENCE_ONLY = re.compile(
    r"""^
    (
      fresher|experienced|experience|exp\.?
      |\d+\s*[-–to/]+\s*\d+\s*(yrs?|years?)?
      |\d+\s*\+?\s*(yrs?|years?)
      |\d+\s*[-–]?\s*\d*\s*year(s)?
      |0\s*[-–]\s*1\s*year(s)?
    )
    $""",
    re.IGNORECASE | re.VERBOSE,
)

_PLACEHOLDER = re.compile(
    r"^(n/?a|na|none|nil|null|test|asdf|xyz|abc|role|job|other|-)$",
    re.IGNORECASE,
)


def normalize_job_role(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = " ".join(str(value).strip().split())
    return cleaned or None


def job_role_error(value: Optional[str], *, required: bool = False) -> Optional[str]:
    """Return an error message if invalid, else None. Empty is OK when not required."""
    cleaned = normalize_job_role(value)
    if not cleaned:
        if required:
            return "Enter a real job role (e.g. Software Developer)"
        return None

    if len(cleaned) > JOB_ROLE_MAX_LEN:
        return f"Job role cannot exceed {JOB_ROLE_MAX_LEN} characters"

    # Letters + spaces only — no digits or symbols.
    if any(ch.isdigit() for ch in cleaned):
        return "Job role can only contain letters — remove numbers"
    if any(not (ch.isalpha() or ch.isspace()) for ch in cleaned):
        return "Job role can only contain letters — remove symbols"

    letter_count = sum(1 for ch in cleaned if ch.isalpha())
    if letter_count < JOB_ROLE_MIN_LETTERS:
        return "Enter a real job role with at least 3 letters"

    if _EXPERIENCE_ONLY.match(cleaned):
        return "Use the Experience field for years/fresher — enter a job title here"

    if _PLACEHOLDER.match(cleaned):
        return "Enter a real job role (e.g. Software Developer)"

    return None


def validate_job_role_value(value: Optional[str], *, required: bool = False) -> Optional[str]:
    """Normalize and validate. Raises ValueError with a user-facing message."""
    cleaned = normalize_job_role(value)
    error = job_role_error(cleaned, required=required)
    if error:
        raise ValueError(error)
    return cleaned
