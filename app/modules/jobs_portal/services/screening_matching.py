"""Deterministic JD↔resume scoring + selective AI role audit for bulk screening."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

from app.core.config import settings
from app.modules.jobs_portal.services.screening_skills import match_skills, normalize_skills, parse_experience_years

logger = logging.getLogger(__name__)

SCORING_VERSION = f"{settings.SCREENING_SCORING_VERSION}-rolefit-v2"

# Spec defaults — versioned; role_fit gates overall score
W_REQUIRED_SKILLS = 0.35
W_EXPERIENCE = 0.20
W_RESPONSIBILITIES = 0.15
W_PREFERRED = 0.10
W_EDUCATION = 0.10
W_ROLE_FIT = 0.10

# Generic tokens that should not drive role fit alone
_STOP = {
    "the", "and", "for", "with", "role", "job", "position", "senior", "junior",
    "associate", "assistant", "lead", "head", "manager", "executive", "officer",
    "intern", "trainee", "fresher", "experience", "years", "year", "work",
}


def re_tokens(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{2,}", text or "")


def _role_tokens(text: str) -> Set[str]:
    toks = {t.lower() for t in re_tokens(text)}
    return {t for t in toks if t not in _STOP and len(t) > 2}


def _candidate_role_blob(profile: Dict[str, Any], evidence_text: str) -> str:
    parts: List[str] = []
    for exp in profile.get("experience") or []:
        if isinstance(exp, dict):
            if exp.get("job_title"):
                parts.append(str(exp["job_title"]))
            if exp.get("company"):
                parts.append(str(exp["company"]))
    # Prefer explicit titles; fall back to excerpt only (not full resume dump for matching noise)
    excerpt = (profile.get("raw_text_excerpt") or evidence_text or "")[:1200]
    parts.append(excerpt)
    return " ".join(parts)


def compute_role_fit(
    jd_title: str,
    jd_description: str,
    profile: Dict[str, Any],
    evidence_text: str = "",
) -> Dict[str, Any]:
    """
    Role/title relevance 0..1.
    Years of experience alone must NOT imply role fit for an unrelated job family.
    """
    title_tokens = _role_tokens(jd_title or "")
    # Include a few distinctive nouns from JD description (not the whole blob)
    desc_tokens = _role_tokens((jd_description or "")[:400])
    # Prefer title tokens; supplement lightly from description
    focus = title_tokens or set(list(desc_tokens)[:8])
    if not focus:
        return {"score": 0.55, "note": "role_unspecified", "overlap": []}

    blob = _candidate_role_blob(profile, evidence_text).lower()
    overlap = sorted(t for t in focus if t in blob)
    ratio = len(overlap) / max(len(focus), 1)

    if ratio >= 0.45:
        return {"score": min(1.0, 0.55 + ratio), "note": "role_aligned", "overlap": overlap[:8]}
    if ratio >= 0.2:
        return {"score": 0.35 + ratio * 0.5, "note": "role_partial", "overlap": overlap[:8]}
    # No meaningful title/domain overlap — hard mismatch
    return {"score": 0.08, "note": "role_mismatch", "overlap": overlap[:8]}


def score_candidate_against_jd(
    profile: Dict[str, Any],
    jd: Dict[str, Any],
    evidence_text: str = "",
) -> Dict[str, Any]:
    """
    Transparent match score with role gate.
    Missing evidence ≠ confirmed lack; unrelated roles must not score high on experience alone.
    """
    cand_skills = []
    for s in profile.get("skills") or []:
        if isinstance(s, dict):
            cand_skills.append(s.get("normalized_name") or s.get("name") or "")
        else:
            cand_skills.append(str(s))

    required = normalize_skills(jd.get("normalized_required_skills") or jd.get("required_skills") or [])
    preferred = normalize_skills(jd.get("normalized_preferred_skills") or jd.get("preferred_skills") or [])

    text = evidence_text or (profile.get("raw_text_excerpt") or "")
    matched_req, partial_req, missing_req, matched_pref = match_skills(
        required, preferred, cand_skills, text
    )

    role = compute_role_fit(
        jd.get("title") or "",
        jd.get("description") or "",
        profile,
        evidence_text=text,
    )
    role_score = float(role["score"])

    extraction_meta = profile.get("extraction") or {}
    quality = extraction_meta.get("quality_status") or profile.get("quality_status") or "partial"
    document_kind = (
        extraction_meta.get("document_kind")
        or (profile.get("evidence") or {}).get("document_kind")
        or ""
    )
    is_non_resume = (
        document_kind == "identity_document"
        or extraction_meta.get("error") == "not_a_resume"
        or extraction_meta.get("method") == "identity_document"
        or quality == "failed"
    )
    empty_profile = (
        not cand_skills
        and not (profile.get("experience") or [])
        and not (profile.get("education") or [])
        and parse_experience_years(profile.get("experience_years")) is None
    )

    # Required skills coverage
    if required:
        req_score = (len(matched_req) + 0.4 * len(partial_req)) / max(len(required), 1)
        req_score = min(1.0, req_score)
    else:
        # No listed skills — lean on role fit; do not invent coverage for empty profiles
        req_score = 0.0 if empty_profile else (0.2 + 0.35 * role_score)

    # Experience fit — years only matter when role is at least partially related
    cand_years = parse_experience_years(profile.get("experience_years"))
    min_y = jd.get("min_experience_years")
    max_y = jd.get("max_experience_years")
    if empty_profile or is_non_resume:
        exp_score = 0.0
        exp_note = "no_resume_evidence"
    elif role_score < 0.25:
        exp_score = 0.05
        exp_note = "experience_not_relevant_to_role"
    elif cand_years is None:
        exp_score = 0.25
        exp_note = "experience_unverified"
    elif min_y is not None and cand_years < float(min_y):
        gap = float(min_y) - cand_years
        exp_score = max(0.0, 1.0 - gap / max(float(min_y), 1.0)) * max(role_score, 0.4)
        exp_note = "below_minimum"
    elif max_y is not None and cand_years > float(max_y) * 1.5:
        exp_score = 0.55 * max(role_score, 0.5)
        exp_note = "above_typical_range"
    else:
        exp_score = 0.55 + 0.45 * role_score
        exp_note = "within_range_role_weighted"

    # Responsibilities — only count tokens that are also role-relevant / not ultra-generic
    jd_desc = (jd.get("description") or "").lower()
    resp_score = 0.0 if (empty_profile or is_non_resume) else 0.15
    if not (empty_profile or is_non_resume) and jd_desc and text and role_score >= 0.25:
        tokens = {t for t in re_tokens(jd_desc) if len(t) > 4 and t.lower() not in _STOP}
        hit = sum(1 for t in tokens if t.lower() in text.lower())
        resp_score = min(1.0, hit / max(min(len(tokens), 15), 1)) if tokens else 0.2
        resp_score *= 0.4 + 0.6 * role_score
    elif role_score < 0.25:
        resp_score = 0.0 if (empty_profile or is_non_resume) else 0.05

    if preferred:
        pref_score = len(matched_pref) / max(len(preferred), 1)
        if role_score < 0.25:
            pref_score *= 0.25
    else:
        pref_score = 0.0 if (empty_profile or is_non_resume) else (0.25 * role_score)

    edu_req = (jd.get("education_requirements") or "").strip().lower()
    edu_list = profile.get("education") or []
    edu_blob = " ".join(
        str(e.get("degree") if isinstance(e, dict) else e) for e in edu_list
    ).lower()
    if empty_profile or is_non_resume:
        # Never award free education points for ID cards / empty extracts
        edu_score = 0.0
    elif not edu_req:
        edu_score = 0.2 if edu_blob else 0.0
    elif edu_blob and any(tok in edu_blob for tok in edu_req.split() if len(tok) > 2):
        edu_score = 1.0
    elif not edu_blob:
        edu_score = 0.15
    else:
        edu_score = 0.35

    if is_non_resume:
        role_score = 0.0
        role = {**role, "score": 0.0, "note": "not_a_resume", "overlap": []}

    overall = 100.0 * (
        W_REQUIRED_SKILLS * req_score
        + W_EXPERIENCE * exp_score
        + W_RESPONSIBILITIES * resp_score
        + W_PREFERRED * pref_score
        + W_EDUCATION * edu_score
        + W_ROLE_FIT * role_score
    )

    # Hard caps for clear mismatches (prevents "7 years + Agile" looking like ITI fit)
    if is_non_resume or empty_profile:
        overall = min(overall, 3.0)
    if role["note"] == "role_mismatch":
        overall = min(overall, 22.0)
    if required and len(matched_req) == 0 and len(partial_req) == 0 and role_score < 0.35:
        overall = min(overall, 28.0)
    if required and req_score < 0.2 and role_score < 0.3:
        overall = min(overall, 30.0)

    overall = round(min(100.0, max(0.0, overall)), 2)

    if is_non_resume or empty_profile or role["note"] == "role_mismatch" or (
        required and len(matched_req) == 0
    ):
        confidence = "low"
    elif quality == "good" and role_score >= 0.45 and not missing_req:
        confidence = "high"
    else:
        confidence = "medium"

    highlights = matched_req[:8]
    gaps = missing_req[:8]
    fit_bits = []
    if is_non_resume:
        fit_bits.append(
            "Uploaded file is not a resume (identity/KYC document detected) — match score is not meaningful"
        )
    elif empty_profile:
        fit_bits.append("No skills, education, or work history could be extracted from this file")
    if role["note"] == "role_mismatch":
        fit_bits.append(
            f"Role mismatch: JD “{jd.get('title') or 'role'}” does not align with candidate background"
        )
    elif role.get("overlap"):
        fit_bits.append(f"Role signals: {', '.join(role['overlap'][:5])}")
    if matched_req:
        fit_bits.append(f"Matched required skills: {', '.join(matched_req[:5])}")
    if missing_req:
        fit_bits.append(f"Unverified/missing required skills: {', '.join(missing_req[:5])}")
    fit_bits.append(f"Experience signal: {exp_note}")
    fit_reason = "; ".join(fit_bits)

    return {
        "overall_score": overall,
        "score_breakdown": {
            "required_skills": round(req_score * 100, 2),
            "experience": round(exp_score * 100, 2),
            "responsibilities_projects": round(resp_score * 100, 2),
            "preferred_skills": round(pref_score * 100, 2),
            "education_certifications": round(edu_score * 100, 2),
            "role_fit": round(role_score * 100, 2),
            "weights": {
                "required_skills": W_REQUIRED_SKILLS,
                "experience": W_EXPERIENCE,
                "responsibilities_projects": W_RESPONSIBILITIES,
                "preferred_skills": W_PREFERRED,
                "education_certifications": W_EDUCATION,
                "role_fit": W_ROLE_FIT,
            },
            "experience_note": exp_note,
            "role_note": role["note"],
        },
        "matched_requirements": matched_req,
        "partially_matched_requirements": partial_req,
        "missing_requirements": missing_req,
        "matched_preferred": matched_pref,
        "relevant_evidence": {
            "skills_sample": highlights,
            "gaps_sample": gaps,
            "role_overlap": role.get("overlap") or [],
        },
        "match_confidence": confidence,
        "data_quality": quality,
        "scoring_version": SCORING_VERSION,
        "fit_reason": fit_reason,
        "highlights": highlights,
        "gaps": gaps,
        "role_fit": role_score,
        "needs_ai_audit": (
            overall >= 40
            and role["note"] in ("role_mismatch", "role_partial")
        ) or (overall >= 50 and required and len(matched_req) == 0),
    }


async def ai_audit_match(
    profile: Dict[str, Any],
    jd: Dict[str, Any],
    deterministic: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Selective AI audit: verify whether the candidate's actual role family fits the JD.
    Treats resume/JD text as untrusted. Falls back to deterministic result on failure.
    """
    out = dict(deterministic)
    try:
        from app.modules.jobs_portal.services.ai_service import get_ai

        ai = get_ai()
        skills = []
        for s in profile.get("skills") or []:
            if isinstance(s, dict):
                skills.append(s.get("normalized_name") or s.get("name"))
            else:
                skills.append(str(s))
        skills = [s for s in skills if s][:25]
        titles = []
        for exp in profile.get("experience") or []:
            if isinstance(exp, dict) and exp.get("job_title"):
                titles.append(str(exp["job_title"]))

        system = (
            "You are a recruitment matching auditor. "
            "Decide if a candidate's background is relevant to a job role. "
            "Ignore demographics. Do not invent skills. "
            "Return ONLY compact JSON with keys: "
            "role_relevant (bool), role_fit_0_to_100 (number), "
            "score_cap_0_to_100 (number), reason (short string)."
        )
        user = json.dumps(
            {
                "job_title": jd.get("title"),
                "job_required_skills": (jd.get("required_skills") or [])[:20],
                "candidate_titles": titles[:8],
                "candidate_skills": skills,
                "deterministic_score": deterministic.get("overall_score"),
                "deterministic_role_note": (deterministic.get("score_breakdown") or {}).get("role_note"),
                "resume_excerpt": (profile.get("raw_text_excerpt") or "")[:1500],
            },
            ensure_ascii=False,
        )
        raw = await ai.chat_completion(system, user)
        # Extract JSON object
        m = re.search(r"\{[\s\S]*\}", raw or "")
        if not m:
            return out
        data = json.loads(m.group(0))
        relevant = bool(data.get("role_relevant"))
        role_fit = float(data.get("role_fit_0_to_100") or 0)
        score_cap = float(data.get("score_cap_0_to_100") or 100)
        reason = str(data.get("reason") or "").strip()[:400]

        score = float(out.get("overall_score") or 0)
        if not relevant:
            score = min(score, min(score_cap, 30.0))
            out["match_confidence"] = "low"
        else:
            score = min(score, max(score_cap, score * 0.5))
            # Blend role fit from AI into breakdown
            bd = dict(out.get("score_breakdown") or {})
            bd["role_fit"] = round(role_fit, 2)
            bd["ai_audited"] = True
            out["score_breakdown"] = bd

        out["overall_score"] = round(max(0.0, min(100.0, score)), 2)
        if reason:
            out["fit_reason"] = f"{out.get('fit_reason') or ''}; AI audit: {reason}".strip("; ")
        out["scoring_version"] = f"{SCORING_VERSION}+ai-audit"
        return out
    except Exception as exc:
        logger.warning("AI match audit skipped: %s", type(exc).__name__)
        return deterministic
