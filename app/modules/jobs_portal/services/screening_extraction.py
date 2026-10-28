"""Staged resume extraction for screening — native parse first, no default LLM."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.modules.jobs_portal.services.screening_skills import normalize_skills, parse_experience_years
from app.shared.services.resume_parser import parse_resume

logger = logging.getLogger(__name__)

PARSER_VERSION = settings.SCREENING_PARSER_VERSION
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-()]{8,}\d)")
URL_RE = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.I)

# Identity / KYC docs are not resumes — never invent skill/education match scores from them.
_ID_DOC_RE = re.compile(
    r"(?i)\b("
    r"aadhaar|aadhar|uidai|enrolment\s*no|enrollment\s*no|"
    r"permanent\s+account\s+number|\bpan\s*(?:card|no\.?|number)?\b|"
    r"passport\s*(?:no|number|card)?|"
    r"voter\s*(?:id|card|i\.?d\.?)|election\s+commission|"
    r"driving\s+licen[cs]e|\bdl\s*no\.?\b|"
    r"unique\s+identification\s+authority|"
    r"digitally\s+signed\s+by\s+ds\s+unique"
    r")\b"
)
_RESUME_SIGNAL_RE = re.compile(
    r"(?i)\b("
    r"resume|curriculum\s+vitae|\bcv\b|work\s+experience|professional\s+experience|"
    r"employment\s+history|career\s+summary|objective|skills?|education|"
    r"projects?|certifications?|internship|responsibilities|job\s+title|"
    r"bachelor|master|b\.?\s*tech|m\.?\s*tech|linkedin"
    r")\b"
)
# Too-short aliases create false hits inside unrelated words; never harvest these from free text.
_HARVEST_SKIP = {
    "git", "js", "ts", "py", "ml", "dl", "go", "r", "c", "c#", "c++", "sql", "rest", "node", "java",
}


def detect_non_resume_document(text: str) -> Optional[str]:
    """
    Return a short reason when the file looks like an ID/KYC document, not a resume.
    """
    blob = text or ""
    if not blob.strip():
        return None
    id_hits = len(_ID_DOC_RE.findall(blob))
    resume_hits = len(_RESUME_SIGNAL_RE.findall(blob))
    lower = blob.lower()
    strong_id = any(
        k in lower
        for k in (
            "aadhaar",
            "aadhar",
            "uidai",
            "unique identification authority",
            "permanent account number",
        )
    )
    if strong_id and resume_hits <= 1:
        return "identity_document"
    if id_hits >= 2 and resume_hits == 0:
        return "identity_document"
    if id_hits >= 1 and resume_hits == 0 and len(blob.split()) < 220:
        return "identity_document"
    return None


def _quality_from_text(text: str, structured: dict) -> tuple[str, bool]:
    words = len((text or "").split())
    has_email = bool(structured.get("email") or EMAIL_RE.search(text or ""))
    has_skills = bool(structured.get("skills"))
    if words < 40:
        return "poor", True
    if words < 120 or not (has_email or has_skills):
        return "partial", True
    return "good", False


def _skills_list(parsed: dict, text: str) -> List[dict]:
    raw = parsed.get("skills") or []
    if isinstance(raw, str):
        raw = [s.strip() for s in raw.split(",") if s.strip()]
    names = normalize_skills([str(s) for s in raw if s])
    # Light keyword harvest only for unambiguous multi-char skills (avoid Git/JS noise).
    if not names and text:
        from app.modules.jobs_portal.services.screening_skills import SKILL_ALIASES, skill_present_in_text
        for canon, aliases in SKILL_ALIASES.items():
            alias_keys = {canon.lower(), *(a.lower() for a in aliases)}
            if alias_keys & _HARVEST_SKIP:
                continue
            if min((len(a) for a in alias_keys), default=0) < 4 and canon.lower() not in {
                "aws", "html", "css", "nlp",
            }:
                # Prefer longer aliases; skip ultra-short-only skills in free-text harvest
                if not any(len(a) >= 4 for a in alias_keys):
                    continue
            if skill_present_in_text(canon, text):
                names.append(canon)
        names = normalize_skills(names)
    return [{"name": n, "normalized_name": n, "source": "skills_section"} for n in names]


def _experience_list(parsed: dict) -> List[dict]:
    # Existing parser returns experience_years scalar; keep structure empty unless richer later
    years = parse_experience_years(parsed.get("experience_years"))
    if years is None:
        return []
    return [{
        "job_title": None,
        "company": None,
        "start_date": None,
        "end_date": None,
        "is_current": None,
        "responsibilities": [],
        "years": years,
        "evidence_pages": [],
    }]


def _name_from_text(text: str, email: Optional[str]) -> Optional[str]:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    for ln in lines[:8]:
        if EMAIL_RE.search(ln) or PHONE_RE.search(ln) or URL_RE.search(ln):
            continue
        if len(ln) > 60 or len(ln.split()) > 6:
            continue
        if re.search(r"\d", ln):
            continue
        # Avoid section headers
        if ln.lower() in {"resume", "curriculum vitae", "cv", "profile", "objective", "summary"}:
            continue
        return ln[:200]
    if email:
        local = email.split("@", 1)[0]
        cleaned = re.sub(r"[._\-]+", " ", local).strip().title()
        return cleaned[:200] if cleaned else None
    return None


def extract_screening_profile(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Extract structured profile once per resume.
    Uses existing resume_parser (PyMuPDF / python-docx / OCR fallback when needed).
    Does NOT call an LLM by default.
    """
    try:
        raw_text, parsed = parse_resume(file_path, filename)
    except Exception as exc:
        logger.warning("screening extract failed for %s: %s", filename, type(exc).__name__)
        detail = str(exc).strip() or type(exc).__name__
        return {
            "schema_version": "1.0",
            "candidate": {"name": None, "email": None, "phone": None, "location": None},
            "skills": [],
            "experience": [],
            "education": [],
            "projects": [],
            "certifications": [],
            "experience_years": None,
            "extraction": {
                "method": "failed",
                "quality_status": "failed",
                "requires_review": True,
                "parser_version": PARSER_VERSION,
                "error": "extraction_failed",
                "error_message": f"Could not read this file ({detail}). Try a text-based PDF or DOCX.",
            },
            "raw_text_excerpt": "",
            "evidence": {},
        }

    email = parsed.get("email") or (EMAIL_RE.search(raw_text).group(0) if EMAIL_RE.search(raw_text or "") else None)
    phone_m = PHONE_RE.search(raw_text or "")
    phone = parsed.get("phone") or (phone_m.group(0).strip() if phone_m else None)
    education = parsed.get("education")
    if isinstance(education, str):
        education = [{"degree": education}] if education else []
    elif not isinstance(education, list):
        education = []

    non_resume = detect_non_resume_document(raw_text or "")
    skills = [] if non_resume else _skills_list(parsed, raw_text or "")
    experience = [] if non_resume else _experience_list(parsed)
    years = None if non_resume else parse_experience_years(parsed.get("experience_years"))
    if non_resume:
        education = []
    name = _name_from_text(raw_text or "", email)
    quality, needs_review = _quality_from_text(raw_text or "", parsed)
    method = "native_text"
    error_code = None
    error_message = None
    if not (raw_text or "").strip():
        method = "empty"
        quality = "failed"
        needs_review = True
        error_code = "empty_or_scanned"
        error_message = (
            "No readable text found. File is likely a scanned/image PDF, password-protected, "
            "or corrupt. Re-upload a text-based PDF or DOCX."
        )
    elif non_resume:
        method = "identity_document"
        quality = "failed"
        needs_review = True
        error_code = "not_a_resume"
        error_message = (
            "This file looks like an identity document (e.g. Aadhaar / PAN / passport), not a resume. "
            "Upload a CV/resume with skills and work history."
        )

    excerpt = (raw_text or "")[:2500]
    extraction_meta = {
        "method": method,
        "quality_status": quality,
        "requires_review": needs_review,
        "parser_version": PARSER_VERSION,
    }
    if error_code:
        extraction_meta["error"] = error_code
    if error_message:
        extraction_meta["error_message"] = error_message
    if non_resume:
        extraction_meta["document_kind"] = non_resume
    return {
        "schema_version": "1.0",
        "candidate": {
            "name": name,
            "email": email,
            "phone": phone,
            "location": None,
        },
        "skills": skills,
        "experience": experience,
        "education": education,
        "projects": [],
        "certifications": [],
        "experience_years": years,
        "extraction": extraction_meta,
        "raw_text_excerpt": excerpt,
        "evidence": {
            "word_count": len((raw_text or "").split()),
            "has_email": bool(email),
            "has_phone": bool(phone),
            "document_kind": non_resume or "resume",
        },
        "_full_text": raw_text or "",  # in-memory only; not persisted in full
    }
