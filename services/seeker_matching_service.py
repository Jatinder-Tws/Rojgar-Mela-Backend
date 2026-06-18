"""
Seeker Matching Service – bidirectional AI-powered job ↔ resume matching.
Optimized for minimum GPT calls: embeddings cached, GPT ranks in one batch.
"""
from __future__ import annotations
import json
import logging
import re
from typing import Any, List, Optional

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.job import JobPosting
from models.resume import Resume
from models.match import Match
from models.portfolio import Portfolio
from services.ai_service import get_ai

logger = logging.getLogger(__name__)

# How many candidates to pull from the vector index before any GPT re-ranking.
SEEKER_TOP_N = 10
PROVIDER_TOP_N = 50

# Vector similarity and final match thresholds.
SIMILARITY_THRESHOLD = 0.55
MATCH_SCORE_THRESHOLD = 60  # Only store/return matches with score >= this

# Skip GPT when vector + skills signal is already very strong or clearly weak.
HIGH_CONFIDENCE_SIMILARITY = 0.78
HIGH_CONFIDENCE_SKILLS_OVERLAP = 0.55
LOW_CONFIDENCE_SIMILARITY = 0.58


def _norm_skill(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _skills_from_json(skills_data: Any) -> List[str]:
    if not skills_data:
        return []
    if not isinstance(skills_data, list):
        return []
    skills: List[str] = []
    for item in skills_data:
        if isinstance(item, str) and item.strip():
            skills.append(item.strip())
        elif isinstance(item, dict):
            name = item.get("name") or item.get("skill")
            if name and str(name).strip():
                skills.append(str(name).strip())
    return skills


def _collect_resume_skills(
    resume: Resume,
    user: User | None = None,
    portfolio: Portfolio | None = None,
    parsed_json: dict | None = None,
) -> List[str]:
    parsed = parsed_json if parsed_json is not None else (resume.parsed_json if isinstance(resume.parsed_json, dict) else {})
    skills = _skills_from_json(parsed.get("skills"))
    skills.extend(_skills_from_json(portfolio.skills if portfolio else None))
    return list(dict.fromkeys(skills))


def _parse_min_experience_years(text: str | None) -> float | None:
    if not text:
        return None
    lowered = text.lower().strip()
    if any(token in lowered for token in ("fresher", "fresh graduate", "no experience", "0 year")):
        return 0.0
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+|plus)?\s*(?:to|-)?\s*(\d+(?:\.\d+)?)?\s*year", lowered)
    if match:
        return float(match.group(1))
    plus_match = re.search(r"(\d+(?:\.\d+)?)\+", lowered)
    if plus_match:
        return float(plus_match.group(1))
    return None


def _candidate_experience_years(
    resume: Resume,
    user: User | None = None,
    portfolio: Portfolio | None = None,
    parsed_json: dict | None = None,
) -> float | None:
    parsed = parsed_json if parsed_json is not None else (resume.parsed_json if isinstance(resume.parsed_json, dict) else {})
    if parsed.get("experience_years") is not None:
        try:
            return float(parsed["experience_years"])
        except (TypeError, ValueError):
            pass
    if portfolio and portfolio.total_experience_years is not None:
        return float(portfolio.total_experience_years)
    if user and user.experience:
        parsed_exp = _parse_min_experience_years(user.experience)
        if parsed_exp is not None:
            return parsed_exp
    return None


def _skills_overlap_ratio(resume_skills: List[str], required_skills: List[str]) -> float:
    required = [_norm_skill(skill) for skill in (required_skills or []) if skill]
    if not required:
        return 0.65
    resume_norm = {_norm_skill(skill) for skill in resume_skills if skill}
    if not resume_norm:
        return 0.0
    matched = 0
    for req in required:
        if req in resume_norm or any(req in skill or skill in req for skill in resume_norm):
            matched += 1
    return matched / len(required)


def _experience_fit_score(candidate_years: float | None, required_text: str | None) -> float:
    required_years = _parse_min_experience_years(required_text)
    if required_years is None or candidate_years is None:
        return 0.7
    if candidate_years >= required_years:
        return 1.0
    if candidate_years >= required_years * 0.7:
        return 0.6
    return 0.25


def _hybrid_match_score(similarity: float, skills_overlap: float, experience_fit: float) -> float:
    return round((similarity * 100 * 0.50) + (skills_overlap * 100 * 0.35) + (experience_fit * 100 * 0.15), 1)


def _matched_and_missing_skills(required_skills: List[str], resume_skills: List[str]) -> tuple[List[str], List[str]]:
    required = [skill for skill in (required_skills or []) if skill]
    resume_norm = {_norm_skill(skill) for skill in resume_skills if skill}
    matched: List[str] = []
    missing: List[str] = []
    for skill in required:
        norm = _norm_skill(skill)
        if norm in resume_norm or any(norm in rs or rs in norm for rs in resume_norm):
            matched.append(skill)
        else:
            missing.append(skill)
    return matched[:4], missing[:4]


def _rule_based_ranking(
    similarity: float,
    skills_overlap: float,
    experience_fit: float,
    required_skills: List[str],
    resume_skills: List[str],
) -> dict | None:
    """Return a ranking dict, {'reject': True}, or None if GPT should decide."""
    if required_skills and skills_overlap == 0 and similarity < LOW_CONFIDENCE_SIMILARITY:
        return {"reject": True}

    hybrid_score = _hybrid_match_score(similarity, skills_overlap, experience_fit)
    matched, missing = _matched_and_missing_skills(required_skills, resume_skills)

    if similarity >= HIGH_CONFIDENCE_SIMILARITY or (
        similarity >= 0.68 and skills_overlap >= HIGH_CONFIDENCE_SKILLS_OVERLAP
    ):
        return {
            "score": min(hybrid_score, 95.0),
            "highlights": matched or ["Strong profile alignment"],
            "gaps": missing,
            "fit_reason": "High-confidence match based on skills and profile similarity",
        }

    if hybrid_score < MATCH_SCORE_THRESHOLD and skills_overlap < 0.2 and similarity < 0.62:
        return {"reject": True}

    return None


def _fallback_ranking(
    similarity: float,
    skills_overlap: float,
    experience_fit: float,
    required_skills: List[str],
    resume_skills: List[str],
) -> dict:
    matched, missing = _matched_and_missing_skills(required_skills, resume_skills)
    return {
        "score": _hybrid_match_score(similarity, skills_overlap, experience_fit),
        "highlights": matched,
        "gaps": missing,
        "fit_reason": "Score based on profile similarity and skill alignment",
    }


def _build_resume_embedding_text(resume: Resume, user: User | None, portfolio: Portfolio | None) -> str:
    parts: List[str] = []
    skills = _collect_resume_skills(resume, user, portfolio)
    if skills:
        parts.append(f"Skills: {', '.join(skills[:40])}")
    experience_years = _candidate_experience_years(resume, user, portfolio)
    if experience_years is not None:
        parts.append(f"Experience: {experience_years} years")
    if user:
        if user.industry:
            parts.append(f"Industry: {user.industry}")
        if user.job_role:
            parts.append(f"Role: {user.job_role}")
    if portfolio:
        if portfolio.headline:
            parts.append(f"Headline: {portfolio.headline}")
        if portfolio.current_role:
            parts.append(f"Current Role: {portfolio.current_role}")
        location = ", ".join(part for part in [portfolio.city, portfolio.state] if part)
        if location:
            parts.append(f"Location: {location}")
    if resume.parsed_text:
        parts.append(resume.parsed_text[:4500])
    return "\n".join(parts)[:6000]


def _build_job_embedding_text(job: JobPosting) -> str:
    skills_text = ", ".join(job.required_skills or [])
    job_type = str(job.job_type.value) if hasattr(job.job_type, "value") else (job.job_type or "")
    return (
        f"Job Title: {job.title}\n"
        f"Industry: {job.industry or ''}\n"
        f"Location: {job.location or ''}\n"
        f"Experience Required: {job.experience_required or ''}\n"
        f"Job Type: {job_type}\n"
        f"Salary: {job.salary_range or ''}\n"
        f"Skills: {skills_text}\n"
        f"Description: {job.description or ''}"
    )[:6000]


def _build_resume_gpt_summary(resume: Resume, user: User | None = None, portfolio: Portfolio | None = None) -> str:
    parsed = resume.parsed_json if isinstance(resume.parsed_json, dict) else {}
    lines: List[str] = []
    skills = _collect_resume_skills(resume, user, portfolio)
    if skills:
        lines.append(f"Skills: {', '.join(skills[:25])}")
    experience_years = _candidate_experience_years(resume, user, portfolio)
    if experience_years is not None:
        lines.append(f"Experience: {experience_years} years")
    if user and user.job_role:
        lines.append(f"Target Role: {user.job_role}")
    if user and user.industry:
        lines.append(f"Industry: {user.industry}")
    if portfolio and portfolio.headline:
        lines.append(f"Headline: {portfolio.headline[:180]}")
    if resume.parsed_text:
        lines.append(resume.parsed_text[:900])
    return "\n".join(lines)[:1500]


def _build_job_gpt_summary(job: JobPosting) -> str:
    return (
        f"Title: {job.title}\n"
        f"Skills: {', '.join(job.required_skills or [])}\n"
        f"Experience: {job.experience_required or ''}\n"
        f"Industry: {job.industry or ''}\n"
        f"{(job.description or '')[:700]}"
    )[:1500]


async def _rank_seeker_jobs(
    resume: Resume,
    seeker: User,
    jobs_to_process: List[tuple[int, Any]],
    portfolio: Portfolio | None = None,
) -> dict[int, dict]:
    resume_skills = _collect_resume_skills(resume, seeker, portfolio)
    resume_summary = _build_resume_gpt_summary(resume, seeker, portfolio)
    rankings: dict[int, dict] = {}
    gpt_queue: List[tuple[int, Any, int]] = []

    for original_idx, row in jobs_to_process:
        similarity = float(getattr(row, "similarity", SIMILARITY_THRESHOLD))
        required_skills = getattr(row, "required_skills", None) or []
        overlap = _skills_overlap_ratio(resume_skills, required_skills)
        experience_fit = _experience_fit_score(
            _candidate_experience_years(resume, seeker, portfolio),
            getattr(row, "experience_required", None),
        )
        rule_result = _rule_based_ranking(similarity, overlap, experience_fit, required_skills, resume_skills)
        if rule_result is None:
            gpt_queue.append((original_idx, row, len(gpt_queue)))
        elif not rule_result.get("reject"):
            rankings[original_idx] = rule_result

    if gpt_queue:
        candidates = [
            {
                "index": gpt_index,
                "title": getattr(row, "title", ""),
                "description": getattr(row, "description", "") or "",
            }
            for _, row, gpt_index in gpt_queue
        ]
        gpt_rankings = await _batch_rerank_gpt(resume_summary, candidates, mode="jobs")
        for ranking in gpt_rankings or []:
            gpt_index = int(ranking.get("index", -1))
            if 0 <= gpt_index < len(gpt_queue):
                original_idx = gpt_queue[gpt_index][0]
                rankings[original_idx] = {
                    "score": float(ranking.get("score", 70)),
                    "highlights": ranking.get("highlights", []),
                    "gaps": ranking.get("gaps", []),
                    "fit_reason": ranking.get("fit_reason", ""),
                }

        for original_idx, row, _ in gpt_queue:
            if original_idx in rankings:
                continue
            similarity = float(getattr(row, "similarity", SIMILARITY_THRESHOLD))
            required_skills = getattr(row, "required_skills", None) or []
            overlap = _skills_overlap_ratio(resume_skills, required_skills)
            experience_fit = _experience_fit_score(
                _candidate_experience_years(resume, seeker, portfolio),
                getattr(row, "experience_required", None),
            )
            rankings[original_idx] = _fallback_ranking(
                similarity, overlap, experience_fit, required_skills, resume_skills
            )

    return rankings


async def _rank_provider_candidates(job: JobPosting, candidates_to_process: List[tuple[int, Any]]) -> dict[int, dict]:
    job_summary = _build_job_gpt_summary(job)
    required_skills = job.required_skills or []
    rankings: dict[int, dict] = {}
    gpt_queue: List[tuple[int, Any, int]] = []

    for original_idx, row in candidates_to_process:
        resume_skills = _skills_from_json(
            (row.parsed_json or {}).get("skills") if isinstance(getattr(row, "parsed_json", None), dict) else None
        )
        similarity = float(getattr(row, "similarity", SIMILARITY_THRESHOLD))
        overlap = _skills_overlap_ratio(resume_skills, required_skills)
        parsed_json = row.parsed_json if isinstance(getattr(row, "parsed_json", None), dict) else {}
        candidate_years = None
        if parsed_json.get("experience_years") is not None:
            try:
                candidate_years = float(parsed_json["experience_years"])
            except (TypeError, ValueError):
                candidate_years = None
        experience_fit = _experience_fit_score(candidate_years, job.experience_required)
        rule_result = _rule_based_ranking(similarity, overlap, experience_fit, required_skills, resume_skills)
        if rule_result is None:
            gpt_queue.append((original_idx, row, len(gpt_queue)))
        elif not rule_result.get("reject"):
            rankings[original_idx] = rule_result

    if gpt_queue:
        batch_input = []
        for _, row, gpt_index in gpt_queue:
            parsed_json = row.parsed_json if isinstance(getattr(row, "parsed_json", None), dict) else {}
            summary_lines = []
            skills = _skills_from_json(parsed_json.get("skills"))
            if skills:
                summary_lines.append(f"Skills: {', '.join(skills[:25])}")
            if parsed_json.get("experience_years") is not None:
                summary_lines.append(f"Experience: {parsed_json['experience_years']} years")
            if getattr(row, "parsed_text", None):
                summary_lines.append((row.parsed_text or "")[:900])
            batch_input.append({
                "index": gpt_index,
                "candidate_name": f"{getattr(row, 'first_name', '')} {getattr(row, 'last_name', '')}".strip(),
                "resume_text": "\n".join(summary_lines)[:1200],
            })

        gpt_rankings = await _batch_rerank_gpt(job_summary, batch_input, mode="resumes")
        for ranking in gpt_rankings or []:
            gpt_index = int(ranking.get("index", -1))
            if 0 <= gpt_index < len(gpt_queue):
                original_idx = gpt_queue[gpt_index][0]
                rankings[original_idx] = {
                    "score": float(ranking.get("score", 70)),
                    "highlights": ranking.get("highlights", []),
                    "gaps": ranking.get("gaps", []),
                    "fit_reason": ranking.get("fit_reason", ""),
                }

        for original_idx, row, _ in gpt_queue:
            if original_idx in rankings:
                continue
            resume_skills = _skills_from_json(
                (row.parsed_json or {}).get("skills") if isinstance(getattr(row, "parsed_json", None), dict) else None
            )
            similarity = float(getattr(row, "similarity", SIMILARITY_THRESHOLD))
            overlap = _skills_overlap_ratio(resume_skills, required_skills)
            parsed_json = row.parsed_json if isinstance(getattr(row, "parsed_json", None), dict) else {}
            candidate_years = None
            if parsed_json.get("experience_years") is not None:
                try:
                    candidate_years = float(parsed_json["experience_years"])
                except (TypeError, ValueError):
                    candidate_years = None
            experience_fit = _experience_fit_score(candidate_years, job.experience_required)
            rankings[original_idx] = _fallback_ranking(
                similarity, overlap, experience_fit, required_skills, resume_skills
            )

    return rankings


async def _get_embedding_from_db(obj) -> Optional[List[float]]:
    """Retrieve stored embedding from model object."""
    emb = getattr(obj, "embedding", None)
    if emb is None:
        return None
    if hasattr(emb, "tolist"):
        return emb.tolist()
    return list(emb)


async def embed_and_store_resume(resume: Resume, db: AsyncSession) -> None:
    """Compute and persist embedding for a resume. Skips if already embedded."""
    if await _get_embedding_from_db(resume):
        return

    user = await db.get(User, resume.user_id)
    portfolio_result = await db.execute(select(Portfolio).where(Portfolio.user_id == resume.user_id))
    portfolio = portfolio_result.scalar_one_or_none()
    text_content = _build_resume_embedding_text(resume, user, portfolio)
    if not text_content.strip():
        return
    ai = get_ai()
    embedding = await ai.embed(text_content)
    await db.execute(
        update(Resume).where(Resume.id == resume.id).values(embedding=embedding)
    )
    await db.commit()


async def embed_and_store_job(job: JobPosting, db: AsyncSession) -> None:
    """Compute and persist embedding for a job posting."""
    if await _get_embedding_from_db(job):
        return
    text_content = _build_job_embedding_text(job)
    ai = get_ai()
    embedding = await ai.embed(text_content)
    await db.execute(
        update(JobPosting).where(JobPosting.id == job.id).values(embedding=embedding)
    )
    await db.commit()


async def _batch_rerank_gpt(resume_text: str, candidates: list, mode: str = "jobs") -> list:
    """
    Single GPT call to rank all candidates.
    mode="jobs" → rank jobs for a resume
    mode="resumes" → rank resumes for a JD

    Uses JSON object format compatible with both OpenAI (response_format=json_object)
    and Gemini (response_mime_type=application/json).
    """
    ai = get_ai()

    if mode == "jobs":
        system = (
            "You are a professional career advisor. Given a resume and a list of job postings, "
            "score each job for fit (0–100). Return ONLY a JSON object, no prose."
        )
        candidates_text = "\n".join(
            f"[{i}] {c.get('title', '')} – {c.get('description', '')[:300]}"
            for i, c in enumerate(candidates)
        )
        user_prompt = (
            f"Resume:\n{resume_text[:3000]}\n\n"
            f"Jobs:\n{candidates_text}\n\n"
            f"Return a JSON object with a 'rankings' key containing an array. "
            f"Each array element must have: index (int), score (int 0-100), "
            f"highlights (list of strings), gaps (list of strings), fit_reason (string).\n"
            f"Score purely on skills, experience, role alignment, and domain knowledge.\n"
            f"Keep highlights/gaps as short bullet strings. Score 0-100."
        )
    else:
        system = (
            "You are an expert recruiter. Given a job description and a list of candidate profiles, "
            "score each candidate for fit (0–100). Return ONLY a JSON object, no prose."
        )
        candidates_text = "\n".join(
            f"[{i}] {c.get('candidate_name', '')} – {c.get('resume_text', '')[:220]}"
            for i, c in enumerate(candidates)
        )
        user_prompt = (
            f"Job Description:\n{resume_text[:2000]}\n\n"
            f"Candidates:\n{candidates_text}\n\n"
            f"Return a JSON object with a 'rankings' key containing an array. "
            f"Each array element must have: index (int), score (int 0-100), "
            f"highlights (list of strings), gaps (list of strings), fit_reason (string).\n"
            f"Score purely on skills, experience, role alignment, and domain knowledge.\n"
            f"Keep highlights and gaps as short bullet-point strings. Score 0-100."
        )

    # ── Call GPT safely ──────────────────────────────────────────────
    try:
        raw = await ai.chat_completion(system, user_prompt)
    except Exception as exc:
        logger.exception(f"GPT chat_completion raised exception: {exc}")
        print(f"\n[GPT DEBUG] API call FAILED with exception: {exc}\n")
        return []

    # ── Parse JSON robustly ────────────────────────────────────────────
    rankings = _extract_rankings(raw)
    if rankings is not None:
        return rankings

    # ── GPT failed — log and return empty so caller falls back to similarity ──
    logger.warning(f"GPT rank parse failed. Raw (first 300): {raw[:300]}")
    print(f"\n[GPT DEBUG] Parse FAILED. Raw response (first 500 chars):\n{raw[:500]}\n")
    return []


def _extract_rankings(raw: str) -> list | None:
    """
    Extract the rankings array from a GPT response that may be:
      - a JSON object like {"rankings": […]}
      - a JSON object like {"results": […]}
      - a bare JSON array […]  (legacy / Gemini)
      - wrapped in markdown code fences
    Returns None if extraction fails.
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # Strip markdown code fences
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Try direct JSON parse
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Look for the rankings array under common keys
            for key in ("rankings", "results", "matches", "candidates", "data", "items"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            # If no known key, grab the first list value we find
            for value in data.values():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    return value
            logger.warning(f"JSON object parsed but no rankings array found. Keys: {list(data.keys())}")
        return None
    except json.JSONDecodeError:
        pass

    # Fallback: extract array between first [ and last ]
    try:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except (json.JSONDecodeError, Exception):
        pass

    return None


async def match_jobs_for_seeker(seeker: User, db: AsyncSession) -> List[dict]:
    """
    Seeker flow:
    1. Get seeker's latest resume embedding (already stored)
    2. Check for cached matches in DB (skip GPT if recent)
    3. If no cache: pgvector cosine similarity → top N jobs
    4. Single GPT batch re-rank
    5. Store matches in DB for future use
    6. Return sorted list
    """
    # Get latest resume
    res = await db.execute(
        select(Resume).where(Resume.user_id == seeker.id).order_by(Resume.created_at.desc()).limit(1)
    )
    resume = res.scalar_one_or_none()
    if not resume:
        return []

    resume_emb = await _get_embedding_from_db(resume)
    if not resume_emb:
        await embed_and_store_resume(resume, db)
        resume_emb = await _get_embedding_from_db(resume)
        if not resume_emb:
            return []

    # pgvector similarity query
    similarity = (1 - JobPosting.embedding.cosine_distance(resume_emb)).label("similarity")
    stmt = (
        select(
            JobPosting.id,
            JobPosting.provider_id,
            JobPosting.title,
            JobPosting.description,
            JobPosting.required_skills,
            JobPosting.salary_range,
            JobPosting.job_type,
            JobPosting.industry,
            JobPosting.posted_by_name,
            JobPosting.experience_required,
            JobPosting.created_at,
            JobPosting.is_active,
            similarity
        )
        .where(
            JobPosting.is_active == True,
            JobPosting.embedding.isnot(None),
            similarity > SIMILARITY_THRESHOLD
        )
        .order_by(JobPosting.embedding.cosine_distance(resume_emb))
        .limit(SEEKER_TOP_N)
    )
    rows = await db.execute(stmt)
    jobs_raw = rows.all()
    if not jobs_raw:
        return []

    # Check for existing matches in DB to avoid re-running GPT
    job_ids = [str(r.id) for r in jobs_raw]
    existing_matches_result = await db.execute(
        select(Match).where(
            and_(
                Match.seeker_id == seeker.id,
                Match.job_id.in_(job_ids)
            )
        )
    )
    existing_matches = {str(m.job_id): m for m in existing_matches_result.scalars().all()}

    # Separate jobs that need GPT ranking vs cached
    jobs_needing_ranking = []
    jobs_with_cache = []
    
    for i, row in enumerate(jobs_raw):
        job_id = str(row.id)
        if job_id in existing_matches:
            jobs_with_cache.append((i, row, existing_matches[job_id]))
        else:
            jobs_needing_ranking.append((i, row))

    # Only run GPT for jobs without cached matches
    rank_map = {}
    if jobs_needing_ranking:
        portfolio_result = await db.execute(select(Portfolio).where(Portfolio.user_id == seeker.id))
        portfolio = portfolio_result.scalar_one_or_none()
        rankings_by_idx = await _rank_seeker_jobs(resume, seeker, jobs_needing_ranking, portfolio)

        for original_idx, job_row in jobs_needing_ranking:
            rank = rankings_by_idx.get(original_idx)
            if not rank:
                continue
            score = float(rank.get("score", 70))
            if score < MATCH_SCORE_THRESHOLD:
                continue

            new_match = Match(
                seeker_id=seeker.id,
                job_id=str(job_row.id),
                score=score,
                highlights=rank.get("highlights", []),
                gaps=rank.get("gaps", []),
                fit_reason=rank.get("fit_reason", "")
            )
            db.add(new_match)
            rank_map[original_idx] = rank

        await db.commit()

    # Build results from both cached and new matches
    results = []
    for i, row in enumerate(jobs_raw):
        job_id = str(row.id)
        
        # Use cached match if available (only >= threshold)
        if job_id in existing_matches:
            match = existing_matches[job_id]
            if match.score < MATCH_SCORE_THRESHOLD:
                continue
            rank = {
                "score": match.score,
                "highlights": match.highlights or [],
                "gaps": match.gaps or [],
                "fit_reason": match.fit_reason or ""
            }
        else:
            # Use newly computed rank
            rank = rank_map.get(i, {"score": round(row.similarity * 100, 1), "highlights": [], "gaps": [], "fit_reason": ""})
            if rank.get("score", 0) < MATCH_SCORE_THRESHOLD:
                continue
        
        results.append({
            "id": str(row.id),
            "provider_id": str(row.provider_id),
            "title": row.title,
            "description": row.description,
            "required_skills": row.required_skills or [],
            "salary_range": row.salary_range,
            "job_type": str(row.job_type.value) if hasattr(row.job_type, 'value') else row.job_type,
            "industry": row.industry,
            "posted_by_name": row.posted_by_name,
            "experience_required": row.experience_required,
            "is_active": row.is_active,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "match_score": float(rank.get("score", 70)),
            "highlights": rank.get("highlights", []),
            "gaps": rank.get("gaps", []),
            "fit_reason": rank.get("fit_reason", ""),
        })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results


async def match_candidates_for_job(job: JobPosting, db: AsyncSession) -> List[dict]:
    """
    Provider flow:
    1. Get job embedding
    2. Check for cached matches in DB (skip GPT if recent)
    3. If no cache: pgvector cosine similarity → top N seeker resumes
    4. Single GPT batch re-rank
    5. Store matches in DB for future use
    6. Return sorted list
    """
    job_emb = await _get_embedding_from_db(job)
    if not job_emb:
        await embed_and_store_job(job, db)
        await db.refresh(job)
        job_emb = await _get_embedding_from_db(job)
        if not job_emb:
            return []

    similarity = (1 - Resume.embedding.cosine_distance(job_emb)).label("similarity")
    stmt = (
        select(
            Resume.id.label("resume_id"),
            Resume.parsed_text,
            Resume.parsed_json,
            Resume.filename,
            User.id.label("user_id"),
            User.first_name,
            User.last_name,
            User.email,
            similarity
        )
        .select_from(Resume)
        .join(User, User.id == Resume.user_id)
        .where(
            Resume.embedding.isnot(None),
            User.role == 'seeker',
            User.is_verified == True,
            similarity > SIMILARITY_THRESHOLD
        )
        .order_by(Resume.embedding.cosine_distance(job_emb))
        .limit(PROVIDER_TOP_N)
    )
    rows = await db.execute(stmt)
    candidates_raw = rows.all()
    if not candidates_raw:
        return []

    # Check for existing matches in DB to avoid re-running GPT
    seeker_ids = [str(r.user_id) for r in candidates_raw]
    existing_matches_result = await db.execute(
        select(Match).where(
            and_(
                Match.job_id == job.id,
                Match.seeker_id.in_(seeker_ids)
            )
        )
    )
    existing_matches = {str(m.seeker_id): m for m in existing_matches_result.scalars().all()}

    # Separate candidates that need GPT ranking vs cached
    candidates_needing_ranking = []
    candidates_with_cache = []
    
    for i, row in enumerate(candidates_raw):
        seeker_id = str(row.user_id)
        if seeker_id in existing_matches:
            candidates_with_cache.append((i, row, existing_matches[seeker_id]))
        else:
            candidates_needing_ranking.append((i, row))

    # Only run GPT for candidates without cached matches
    rank_map = {}
    if candidates_needing_ranking:
        rankings_by_idx = await _rank_provider_candidates(job, candidates_needing_ranking)

        for original_idx, candidate_row in candidates_needing_ranking:
            rank = rankings_by_idx.get(original_idx)
            if not rank:
                continue
            score = float(rank.get("score", 70))
            if score < MATCH_SCORE_THRESHOLD:
                continue

            new_match = Match(
                seeker_id=str(candidate_row.user_id),
                job_id=job.id,
                score=score,
                highlights=rank.get("highlights", []),
                gaps=rank.get("gaps", []),
                fit_reason=rank.get("fit_reason", "")
            )
            db.add(new_match)
            rank_map[original_idx] = rank

        await db.commit()

    # Build results from both cached and new matches
    results = []
    for i, row in enumerate(candidates_raw):
        seeker_id = str(row.user_id)
        
        # Use cached match if available
        if seeker_id in existing_matches:
            match = existing_matches[seeker_id]
            if match.score < MATCH_SCORE_THRESHOLD:
                continue
            rank = {
                "score": match.score,
                "highlights": match.highlights or [],
                "gaps": match.gaps or [],
                "fit_reason": match.fit_reason or ""
            }
            match_id = match.id
        else:
            # Use newly computed rank
            rank = rank_map.get(i, {"score": round(row.similarity * 100, 1), "highlights": [], "gaps": [], "fit_reason": ""})
            if rank.get("score", 0) < MATCH_SCORE_THRESHOLD:
                continue
            match_result = await db.execute(
                select(Match).where(
                    and_(Match.seeker_id == seeker_id, Match.job_id == job.id)
                )
            )
            new_match = match_result.scalar_one_or_none()
            match_id = new_match.id if new_match else f"{seeker_id}-{job.id}"
        
        results.append({
            "match_id": str(match_id),
            "user_id": seeker_id,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "email": row.email,
            "score": float(rank.get("score", 70)),
            "highlights": rank.get("highlights", []),
            "gaps": rank.get("gaps", []),
            "fit_reason": rank.get("fit_reason", ""),
            "resume_parsed_json": row.parsed_json,
            "resume_filename": row.filename,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


async def invalidate_seeker_matches(seeker_id: str) -> None:
    """
    Background task: Delete all existing matches for a seeker, re-embed their resume,
    and re-run proactive matching. Called when portfolio or resume changes.
    """
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import delete
            # Delete all existing matches for this seeker
            await db.execute(
                delete(Match).where(Match.seeker_id == seeker_id)
            )
            await db.commit()
            logger.info(f"[REMATCH] Cleared all matches for seeker {seeker_id}")

            # Get the seeker's latest resume
            res = await db.execute(
                select(Resume).where(Resume.user_id == seeker_id).order_by(Resume.created_at.desc()).limit(1)
            )
            resume = res.scalar_one_or_none()
            if not resume:
                logger.info(f"[REMATCH] No resume found for seeker {seeker_id}, skipping re-match")
                return

            # Clear stale embedding and re-embed
            resume.embedding = None
            await db.commit()
            await db.refresh(resume)

            await embed_and_store_resume(resume, db)
            logger.info(f"[REMATCH] Re-embedded resume for seeker {seeker_id}")

            # Re-run proactive matching
            await proactive_match_resume_to_jobs(resume.id)
            logger.info(f"[REMATCH] Re-matched seeker {seeker_id} to all jobs")

        except Exception as e:
            logger.exception(f"[REMATCH] Failed for seeker {seeker_id}: {e}")


async def invalidate_job_matches(job_id: str) -> None:
    """
    Background task: Delete all existing matches for a job, re-embed the job,
    and re-run proactive matching. Called when job description/skills change.
    """
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import delete
            # Delete all existing matches for this job
            await db.execute(
                delete(Match).where(Match.job_id == job_id)
            )
            await db.commit()
            logger.info(f"[REMATCH] Cleared all matches for job {job_id}")

            # Get the job
            job = await db.get(JobPosting, job_id)
            if not job:
                logger.error(f"[REMATCH] Job {job_id} not found")
                return

            # Clear stale embedding and re-embed
            job.embedding = None
            await db.commit()
            await db.refresh(job)

            await embed_and_store_job(job, db)
            logger.info(f"[REMATCH] Re-embedded job {job_id}")

            # Re-run proactive matching
            await proactive_match_job_to_candidates(job_id)
            logger.info(f"[REMATCH] Re-matched job {job_id} to all candidates")

        except Exception as e:
            logger.exception(f"[REMATCH] Failed for job {job_id}: {e}")


async def proactive_match_resume_to_jobs(resume_id: str) -> None:
    """
    Background task: When a resume is uploaded, find all matching jobs and store in DB.
    This runs ONCE per resume upload, then dashboard just reads from matches table.
    """
    from database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            # Get the resume
            resume = await db.get(Resume, resume_id)
            if not resume:
                logger.error(f"[PROACTIVE_MATCH] Resume {resume_id} not found")
                return
            
            # Get the seeker
            seeker_result = await db.execute(select(User).where(User.id == resume.user_id))
            seeker = seeker_result.scalar_one_or_none()
            if not seeker:
                logger.error(f"[PROACTIVE_MATCH] Seeker not found for resume {resume_id}")
                return
            
            # Ensure resume has embedding
            resume_emb = await _get_embedding_from_db(resume)
            if not resume_emb:
                await embed_and_store_resume(resume, db)
                await db.refresh(resume)
                resume_emb = await _get_embedding_from_db(resume)
                if not resume_emb:
                    logger.warning(f"[PROACTIVE_MATCH] Could not generate embedding for resume {resume_id}")
                    return
            
            # Find all active jobs with similarity above threshold
            similarity = (1 - JobPosting.embedding.cosine_distance(resume_emb)).label("similarity")
            stmt = (
                select(
                    JobPosting.id,
                    JobPosting.provider_id,
                    JobPosting.title,
                    JobPosting.description,
                    JobPosting.required_skills,
                    JobPosting.salary_range,
                    JobPosting.job_type,
                    JobPosting.industry,
                    JobPosting.posted_by_name,
                    JobPosting.experience_required,
                    JobPosting.created_at,
                    JobPosting.is_active,
                    similarity
                )
                .where(
                    JobPosting.is_active == True,
                    JobPosting.embedding.isnot(None),
                    similarity > SIMILARITY_THRESHOLD
                )
                .order_by(JobPosting.embedding.cosine_distance(resume_emb))
                .limit(SEEKER_TOP_N * 2)
            )
            rows = await db.execute(stmt)
            jobs_raw = rows.all()
            
            if not jobs_raw:
                logger.info(f"[PROACTIVE_MATCH] No matching jobs found for resume {resume_id}")
                return
            
            # Check which jobs already have matches
            job_ids = [str(r.id) for r in jobs_raw]
            existing_matches_result = await db.execute(
                select(Match).where(
                    and_(
                        Match.seeker_id == seeker.id,
                        Match.job_id.in_(job_ids)
                    )
                )
            )
            existing_job_ids = {str(m.job_id) for m in existing_matches_result.scalars().all()}
            
            # Only process jobs without existing matches
            jobs_to_process = [(i, r) for i, r in enumerate(jobs_raw) if str(r.id) not in existing_job_ids]
            
            if not jobs_to_process:
                logger.info(f"[PROACTIVE_MATCH] All jobs already matched for resume {resume_id}")
                return

            portfolio_result = await db.execute(select(Portfolio).where(Portfolio.user_id == seeker.id))
            portfolio = portfolio_result.scalar_one_or_none()
            rankings_by_idx = await _rank_seeker_jobs(resume, seeker, jobs_to_process, portfolio)

            # Store matches in DB
            matches_created = 0
            from services.notification_service import create_notification
            from models.notification import NotificationType

            for list_idx, job_row in jobs_to_process:
                rank = rankings_by_idx.get(list_idx)
                if not rank:
                    continue
                score = float(rank.get("score", 70))
                if score < MATCH_SCORE_THRESHOLD:
                    continue

                new_match = Match(
                    seeker_id=seeker.id,
                    job_id=str(job_row.id),
                    score=score,
                    highlights=rank.get("highlights", []),
                    gaps=rank.get("gaps", []),
                    fit_reason=rank.get("fit_reason", "")
                )
                db.add(new_match)
                await db.flush()

                if score >= 85:
                    await create_notification(
                        db=db,
                        user_id=seeker.id,
                        type=NotificationType.match,
                        title=f"🔥 Perfect match found: {job_row.title}",
                        message=f"We found a job that perfectly matches your profile! {job_row.title} with a {score}% match score.",
                        related_job_id=str(job_row.id),
                    )
                    await create_notification(
                        db=db,
                        user_id=str(job_row.provider_id),
                        type=NotificationType.match,
                        title=f"✨ Top Candidate for {job_row.title}",
                        message=f"A new candidate {seeker.first_name} {seeker.last_name} is a {score}% match for your job!",
                        related_job_id=str(job_row.id),
                        related_user_id=str(seeker.id),
                    )

                matches_created += 1
            
            await db.commit()
            
            # Broadcast update to seeker's dashboard
            from services.websocket_manager import manager
            await manager.send_personal_message(
                {"type": "MATCH_UPDATE", "user_role": "seeker", "count": matches_created},
                str(seeker.id)
            )
            
            logger.info(f"[PROACTIVE_MATCH] Created {matches_created} job matches for resume {resume_id}")
            
        except Exception as e:
            logger.exception(f"[PROACTIVE_MATCH] Failed for resume {resume_id}: {e}")


async def proactive_match_job_to_candidates(job_id: str) -> None:
    """
    Background task: When a job is posted, find all matching candidates and store in DB.
    This runs ONCE per job posting, then dashboard just reads from matches table.
    """
    from database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            # Get the job
            job = await db.get(JobPosting, job_id)
            if not job:
                logger.error(f"[PROACTIVE_MATCH] Job {job_id} not found")
                return
            
            # Ensure job has embedding
            job_emb = await _get_embedding_from_db(job)
            if not job_emb:
                await embed_and_store_job(job, db)
                await db.refresh(job)
                job_emb = await _get_embedding_from_db(job)
                if not job_emb:
                    logger.warning(f"[PROACTIVE_MATCH] Could not generate embedding for job {job_id}")
                    return
            
            # Find all matching candidates
            similarity = (1 - Resume.embedding.cosine_distance(job_emb)).label("similarity")
            stmt = (
                select(
                    Resume.id.label("resume_id"),
                    Resume.parsed_text,
                    Resume.parsed_json,
                    Resume.filename,
                    User.id.label("user_id"),
                    User.first_name,
                    User.last_name,
                    User.email,
                    similarity
                )
                .select_from(Resume)
                .join(User, User.id == Resume.user_id)
                .where(
                    Resume.embedding.isnot(None),
                    User.role == 'seeker',
                    User.is_verified == True,
                    similarity > SIMILARITY_THRESHOLD
                )
                .order_by(Resume.embedding.cosine_distance(job_emb))
                .limit(PROVIDER_TOP_N)
            )
            rows = await db.execute(stmt)
            candidates_raw = rows.all()
            
            if not candidates_raw:
                logger.info(f"[PROACTIVE_MATCH] No matching candidates found for job {job_id}")
                return
            
            # Check which candidates already have matches
            seeker_ids = [str(r.user_id) for r in candidates_raw]
            existing_matches_result = await db.execute(
                select(Match).where(
                    and_(
                        Match.job_id == job.id,
                        Match.seeker_id.in_(seeker_ids)
                    )
                )
            )
            existing_seeker_ids = {str(m.seeker_id) for m in existing_matches_result.scalars().all()}
            
            # Only process candidates without existing matches
            candidates_to_process = [(i, r) for i, r in enumerate(candidates_raw) if str(r.user_id) not in existing_seeker_ids]
            
            if not candidates_to_process:
                logger.info(f"[PROACTIVE_MATCH] All candidates already matched for job {job_id}")
                return

            rankings_by_idx = await _rank_provider_candidates(job, candidates_to_process)

            # Store matches in DB
            matches_created = 0
            from services.notification_service import create_notification
            from models.notification import NotificationType

            for original_idx, candidate_row in candidates_to_process:
                rank = rankings_by_idx.get(original_idx)
                if not rank:
                    continue
                score = float(rank.get("score", 70))
                if score < MATCH_SCORE_THRESHOLD:
                    continue

                new_match = Match(
                    seeker_id=str(candidate_row.user_id),
                    job_id=job.id,
                    score=score,
                    highlights=rank.get("highlights", []),
                    gaps=rank.get("gaps", []),
                    fit_reason=rank.get("fit_reason", "")
                )
                db.add(new_match)
                await db.flush()

                if score >= 85:
                    await create_notification(
                        db=db,
                        user_id=job.provider_id,
                        type=NotificationType.match,
                        title=f"✨ Top Candidate for {job.title}",
                        message=f"A new candidate {candidate_row.first_name} {candidate_row.last_name} is a {score}% match for your job!",
                        related_job_id=str(job.id),
                        related_user_id=str(new_match.id),
                    )
                    await create_notification(
                        db=db,
                        user_id=str(candidate_row.user_id),
                        type=NotificationType.match,
                        title=f"🔥 Perfect match found: {job.title}",
                        message=f"You're a {score}% match for {job.title}! Log in to view and apply.",
                        related_job_id=str(job.id),
                    )

                matches_created += 1
            
            await db.commit()

            # Broadcast update to provider's dashboard
            from services.websocket_manager import manager
            await manager.send_personal_message(
                {"type": "MATCH_UPDATE", "user_role": "provider", "job_id": str(job.id), "count": matches_created},
                str(job.provider_id)
            )

            logger.info(f"[PROACTIVE_MATCH] Created {matches_created} candidate matches for job {job_id}")
            
        except Exception as e:
            logger.exception(f"[PROACTIVE_MATCH] Failed for job {job_id}: {e}")


async def _cleanup_job_matches_and_notify(job_id: str, job_title: str) -> None:
    """
    Background task: When a job is deactivated/closed, delete all its matches
    and notify every seeker who had been matched.
    """
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Find all seekers who were matched to this job
            matches_result = await db.execute(
                select(Match).where(Match.job_id == job_id)
            )
            matches = matches_result.scalars().all()
            seeker_ids = [str(m.seeker_id) for m in matches]

            from sqlalchemy import delete
            # Delete matches
            await db.execute(
                delete(Match).where(Match.job_id == job_id)
            )
            await db.commit()
            logger.info(f"[CLEANUP] Deleted {len(seeker_ids)} matches for closed job {job_id}")

            # Notify affected seekers
            from services.notification_service import create_notification
            from models.notification import NotificationType
            for sid in seeker_ids:
                await create_notification(
                    db=db,
                    user_id=sid,
                    type=NotificationType.general,
                    title=f"Job Closed: {job_title}",
                    message=f"The position '{job_title}' that matched your profile has been closed by the recruiter.",
                    related_job_id=job_id,
                )
            await db.commit()

            # Broadcast dashboard update to all affected seekers
            from services.websocket_manager import manager
            for sid in seeker_ids:
                await manager.send_personal_message(
                    {"type": "MATCH_UPDATE", "user_role": "seeker", "action": "job_closed"},
                    sid
                )

        except Exception as e:
            logger.exception(f"[CLEANUP] Failed for job {job_id}: {e}")
