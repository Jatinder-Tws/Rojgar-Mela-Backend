"""
Apply-confirm insights: polish soft-warning copy with AI when available.
Always returns the same warning shape; on AI failure returns input heuristics unchanged.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from app.modules.jobs_portal.services.ai_service import get_ai

logger = logging.getLogger(__name__)

ALLOWED_IDS = frozenset({"profile", "role", "skills", "salary", "low_match"})
AI_TIMEOUT_SEC = 4.0


def _clean_text(value: Any, fallback: str = "", *, max_len: int = 320) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_len] if text else fallback


async def polish_apply_warnings(
    *,
    job_title: str,
    job_description: str | None,
    job_salary: str | None,
    required_skills: list[str] | None,
    seeker_job_role: str | None,
    seeker_industry: str | None,
    seeker_skills: list[str] | None,
    expected_salary: str | None,
    warnings: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], str]:
    """
    Returns (warnings, source) where source is 'ai' | 'heuristic'.
    Never raises — AI errors fall back to the provided warnings.
    """
    base: list[dict[str, str]] = []
    for row in warnings or []:
        wid = str(row.get("id") or "").strip()
        if wid not in ALLOWED_IDS:
            continue
        title = _clean_text(row.get("title"))
        detail = _clean_text(row.get("detail"))
        meaning = _clean_text(row.get("meaning"), max_len=140)
        if not title or not detail:
            continue
        item = {"id": wid, "title": title, "detail": detail}
        if meaning:
            item["meaning"] = meaning
        base.append(item)

    if not base:
        return [], "heuristic"

    system = (
        "You help Indian job seekers decide whether to apply. "
        "Rewrite each warning to be clear, respectful, and specific. "
        "Explain WHY the JD and profile may not fit using the actual job title, description, "
        "required skills, seeker job_role/industry/skills, and salary — dynamically, not from a fixed role list. "
        "For id=role: contrast what the seeker appears to target vs what this JD asks for day-to-day. "
        "For id=skills/salary/low_match/profile: stay concrete and actionable. "
        "Never block applying — tone must stay soft (user can still apply / open official site). "
        "Keep each title under 70 chars and detail under 260 chars. "
        "Optional short meaning (<=120 chars) explaining consequence for the seeker. "
        "Return JSON only: {\"warnings\":[{\"id\":\"...\",\"title\":\"...\",\"detail\":\"...\",\"meaning\":\"...\"}]} "
        "Use the same ids you received. Do not invent new ids."
    )
    user_payload = {
        "job": {
            "title": job_title,
            "salary": job_salary,
            "required_skills": (required_skills or [])[:12],
            "description_excerpt": (job_description or "")[:600],
        },
        "seeker": {
            "job_role": seeker_job_role,
            "industry": seeker_industry,
            "skills": (seeker_skills or [])[:16],
            "expected_salary": expected_salary,
        },
        "warnings": base,
        "example_tone": (
            "When profile keywords barely overlap the JD (e.g. React/TypeScript seeker vs "
            "loading/packaging helper JD), say the day-to-day work and screening bar look different "
            "and recruiters may skip them — without claiming a hardcoded incompatible pair."
        ),
    }
    user = json.dumps(user_payload, ensure_ascii=False)

    try:
        ai = get_ai()
        raw = await asyncio.wait_for(ai.chat_completion(system, user), timeout=AI_TIMEOUT_SEC)
        data = json.loads(raw) if isinstance(raw, str) else raw
        polished_rows = data.get("warnings") if isinstance(data, dict) else None
        if not isinstance(polished_rows, list):
            return base, "heuristic"

        by_id: dict[str, dict[str, str]] = {}
        for row in polished_rows:
            if not isinstance(row, dict):
                continue
            wid = str(row.get("id") or "").strip()
            if wid not in ALLOWED_IDS:
                continue
            title = _clean_text(row.get("title"))
            detail = _clean_text(row.get("detail"))
            meaning = _clean_text(row.get("meaning"), max_len=140)
            if title and detail:
                item = {"id": wid, "title": title, "detail": detail}
                if meaning:
                    item["meaning"] = meaning
                by_id[wid] = item

        if not by_id:
            return base, "heuristic"

        merged = []
        for row in base:
            polished = by_id.get(row["id"])
            merged.append(polished or row)
        return merged, "ai"
    except Exception as exc:
        logger.info("apply insights AI polish skipped: %s", exc)
        return base, "heuristic"
