"""
External Candidate Matching Service — vector similarity + GPT re-rank for
unregistered/external candidates against active job postings.
"""
from __future__ import annotations
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.job import JobPosting
from services.seeker_matching_service import (
    _get_embedding_from_db,
    embed_and_store_job,
    _batch_rerank_gpt,
    SIMILARITY_THRESHOLD,
    logger as shared_logger,
)

logger = logging.getLogger(__name__)

EXTERNAL_TOP_N = 10
EXTERNAL_SIMILARITY_THRESHOLD = SIMILARITY_THRESHOLD  # 0.55 — same as registered seekers


async def embed_and_store_external_candidate(candidate, db: AsyncSession) -> None:
    """Compute and persist embedding for an ExternalCandidate.
    Uses the same 3072-dim vector space as jobs (gemini-embedding-001).
    """
    # candidate can be ORM object or Row
    if hasattr(candidate, "embedding") and await _get_embedding_from_db(candidate):
        return

    text_content = _build_external_candidate_text(candidate)[:6000]
    if not text_content.strip():
        return

    from services.ai_service import get_ai
    ai = get_ai()
    embedding = await ai.embed(text_content)
    cid = str(candidate.id)
    from models.external_candidate import ExternalCandidate
    await db.execute(
        update(ExternalCandidate).where(ExternalCandidate.id == cid).values(embedding=embedding)
    )
    await db.commit()
    logger.info(f"[EXT_MATCH] Embedded external candidate {cid}")


def _build_external_candidate_text(candidate) -> str:
    """Build a plain-text profile for embedding/GPT.
    Works with both ORM objects and raw query rows.
    Location fields are intentionally excluded.
    """
    parts = []

    def _add(label: str, value):
        if value:
            parts.append(f"{label}: {value}")

    _add("Name", getattr(candidate, "full_name", None))
    _add("Department", getattr(candidate, "department", None))
    _add("Role", getattr(candidate, "sub_role", None))

    industries = getattr(candidate, "industries", None)
    if industries:
        if isinstance(industries, list):
            _add("Industries", ", ".join(industries))
        elif isinstance(industries, str):
            _add("Industries", industries)

    _add("Experience", getattr(candidate, "total_experience", None))
    _add("Available Shift", getattr(candidate, "available_shift", None))
    _add("Year of Passing", getattr(candidate, "year_of_passing", None))
    _add("Skills", getattr(candidate, "skills", None))
    _add("Professional Journey", getattr(candidate, "professional_journey", None))
    return "\n".join(parts)


async def proactive_match_external_candidate_to_jobs(candidate_id: str) -> None:
    """
    Background task triggered on POST /api/external/apply.

    Flow (mirrors seeker matching):
    1. Embed candidate profile → store vector
    2. pgvector cosine similarity → top N active jobs
    3. GPT batch re-rank the top N
    4. Persist the SINGLE best match
    5. Jobs below similarity threshold → score=0 fallback (only if no similar jobs)
    """
    from database import AsyncSessionLocal
    from models.external_candidate import ExternalCandidate
    from models.external_candidate_match import ExternalCandidateMatch

    async with AsyncSessionLocal() as db:
        try:
            candidate = await db.get(ExternalCandidate, candidate_id)
            if not candidate:
                logger.error(f"[EXT_MATCH] Candidate {candidate_id} not found")
                return

            candidate_text = _build_external_candidate_text(candidate)
            if not candidate_text.strip():
                logger.warning(f"[EXT_MATCH] No profile text for candidate {candidate_id}")
                return

            # ── 1. Embed if not already embedded ─────────────────────────
            if not await _get_embedding_from_db(candidate):
                await embed_and_store_external_candidate(candidate, db)
                # Re-fetch to get the updated embedding
                await db.refresh(candidate)

            cand_emb = await _get_embedding_from_db(candidate)
            if not cand_emb:
                logger.error(f"[EXT_MATCH] Failed to embed candidate {candidate_id}")
                return

            emb_str = str(cand_emb)

            # ── 2. pgvector cosine similarity → top N similar jobs ───────
            similarity = (1 - JobPosting.embedding.cosine_distance(cand_emb)).label("similarity")
            stmt = (
                select(
                    JobPosting.id,
                    JobPosting.provider_id,
                    JobPosting.title,
                    JobPosting.description,
                    JobPosting.required_skills,
                    JobPosting.industry,
                    JobPosting.experience_required,
                    similarity
                )
                .where(
                    JobPosting.is_active == True,
                    JobPosting.embedding.isnot(None),
                    similarity > EXTERNAL_SIMILARITY_THRESHOLD
                )
                .order_by(JobPosting.embedding.cosine_distance(cand_emb))
                .limit(EXTERNAL_TOP_N)
            )
            rows = await db.execute(stmt)
            similar_jobs = rows.all()

            # ── 3. Also fetch jobs below threshold (for score=0 records) ──
            similar_ids = {str(r.id) for r in similar_jobs}
            all_rows = await db.execute(
                select(JobPosting.id, JobPosting.title).where(JobPosting.is_active == True)
            )
            all_jobs = all_rows.fetchall()
            below_threshold_jobs = [
                r for r in all_jobs if str(r.id) not in similar_ids
            ]

            # ── 4. Skip already-matched jobs ─────────────────────────────
            all_job_ids = [str(r.id) for r in all_jobs]
            existing = await db.execute(
                select(ExternalCandidateMatch.job_id).where(
                    ExternalCandidateMatch.candidate_id == candidate_id,
                    ExternalCandidateMatch.job_id.in_(all_job_ids)
                )
            )
            existing_ids = {str(row[0]) for row in existing.fetchall()}

            # Filter out already-matched from both lists
            similar_jobs = [r for r in similar_jobs if str(r.id) not in existing_ids]
            below_threshold_jobs = [
                r for r in below_threshold_jobs if str(r.id) not in existing_ids
            ]

            # ── 5. Build all candidate matches, keep only the BEST ────────
            candidates_matches: list = []  # (job_row, score, highlights, gaps, fit_reason)

            if similar_jobs:
                candidates_input = [
                    {"index": i, "title": r.title, "description": r.description}
                    for i, r in enumerate(similar_jobs)
                ]
                rankings = await _batch_rerank_gpt(
                    candidate_text, candidates_input, mode="jobs"
                )

                if rankings:
                    # GPT succeeded — use real scores
                    for ranking in rankings:
                        idx = ranking.get("index", 0)
                        if idx >= len(similar_jobs):
                            continue
                        job_row = similar_jobs[idx]
                        candidates_matches.append((
                            job_row,
                            float(ranking.get("score", 50)),
                            ranking.get("highlights", []),
                            ranking.get("gaps", []),
                            ranking.get("fit_reason", ""),
                        ))
                else:
                    # GPT failed — use vector similarity score as fallback
                    print("[EXT_MATCH DEBUG] GPT ranking failed — using similarity scores")
                    for job_row in similar_jobs:
                        candidates_matches.append((
                            job_row,
                            round(float(getattr(job_row, "similarity", 0.5)) * 100, 1),
                            [],
                            [],
                            "Score based on vector similarity (AI re-ranking unavailable)",
                        ))

            # Below-threshold jobs (score=0, never selected unless no similar jobs exist)
            for job_row in below_threshold_jobs:
                candidates_matches.append((
                    job_row,
                    0.0,
                    [],
                    ["No vector similarity with candidate profile"],
                    "Different domain/industry — candidate profile embedding does not match this job",
                ))

            # ── 6. Persist only the SINGLE best match ────────────────────
            if candidates_matches:
                candidates_matches.sort(key=lambda x: x[1], reverse=True)
                best = candidates_matches[0]
                job_row, score, highlights, gaps, fit_reason = best

                db.add(
                    ExternalCandidateMatch(
                        candidate_id=candidate_id,
                        job_id=str(job_row.id),
                        score=score,
                        highlights=highlights,
                        gaps=gaps,
                        fit_reason=fit_reason,
                    )
                )

                await db.commit()

                # ── Mark candidate as matched ──────────────────────────
                if not candidate.is_matched:
                    candidate.is_matched = True
                    await db.commit()

                logger.info(
                    f"[EXT_MATCH] Stored best match for candidate {candidate_id}: "
                    f"job={job_row.title} score={score} "
                    f"(evaluated {len(candidates_matches)} jobs)"
                )

        except Exception as e:
            logger.exception(f"[EXT_MATCH] Failed for candidate {candidate_id}: {e}")


async def proactive_match_job_to_external_candidates(job_id: str) -> None:
    """
    Background task triggered on POST /api/jobs.

    Flow (mirrors seeker matching):
    1. Get job embedding
    2. pgvector cosine similarity → top N external candidates
    3. GPT batch re-rank the top N
    4. Persist matches with real scores
    5. Candidates below threshold → score=0 records
    """
    from database import AsyncSessionLocal
    from models.external_candidate import ExternalCandidate
    from models.external_candidate_match import ExternalCandidateMatch

    async with AsyncSessionLocal() as db:
        try:
            job = await db.get(JobPosting, job_id)
            if not job:
                logger.error(f"[EXT_MATCH] Job {job_id} not found")
                return

            job_emb = await _get_embedding_from_db(job)
            if not job_emb:
                logger.warning(f"[EXT_MATCH] Job {job_id} has no embedding — embedding now")
                await embed_and_store_job(job, db)
                await db.refresh(job)
                job_emb = await _get_embedding_from_db(job)
                if not job_emb:
                    logger.error(f"[EXT_MATCH] Failed to embed job {job_id}")
                    return

            jd_text = (
                f"Title: {job.title}\n"
                f"Skills: {', '.join(job.required_skills or [])}\n"
                f"{job.description}"
            )
            # ── pgvector cosine similarity → top N candidates ────────────
            similarity = (1 - ExternalCandidate.embedding.cosine_distance(job_emb)).label("similarity")
            stmt = (
                select(
                    ExternalCandidate.id,
                    ExternalCandidate.full_name,
                    ExternalCandidate.department,
                    ExternalCandidate.sub_role,
                    ExternalCandidate.industries,
                    ExternalCandidate.total_experience,
                    ExternalCandidate.available_shift,
                    ExternalCandidate.professional_journey,
                    similarity
                )
                .where(
                    ExternalCandidate.embedding.isnot(None),
                    ExternalCandidate.status != 'rejected',
                    similarity > EXTERNAL_SIMILARITY_THRESHOLD
                )
                .order_by(ExternalCandidate.embedding.cosine_distance(job_emb))
                .limit(EXTERNAL_TOP_N)
            )
            rows = await db.execute(stmt)
            similar_candidates = rows.all()

            # ── Also fetch below-threshold candidates ────────────────────
            similar_ids = {str(r.id) for r in similar_candidates}
            all_rows = await db.execute(
                select(ExternalCandidate.id, ExternalCandidate.full_name).where(
                    ExternalCandidate.status != "rejected"
                )
            )
            all_candidates = all_rows.fetchall()
            below_threshold = [
                c for c in all_candidates if str(c.id) not in similar_ids
            ]

            # ── Skip already-matched ─────────────────────────────────────
            all_ids = [str(c.id) for c in all_candidates]
            existing = await db.execute(
                select(ExternalCandidateMatch.candidate_id).where(
                    ExternalCandidateMatch.job_id == job_id,
                    ExternalCandidateMatch.candidate_id.in_(all_ids)
                )
            )
            existing_ids = {str(row[0]) for row in existing.fetchall()}

            similar_candidates = [
                c for c in similar_candidates if str(c.id) not in existing_ids
            ]
            below_threshold = [
                c for c in below_threshold if str(c.id) not in existing_ids
            ]

            matches_created = 0

            # ── GPT batch re-rank similar candidates ─────────────────────
            if similar_candidates:
                # Build profile text for each candidate
                profiles = []
                for row in similar_candidates:
                    profile_text = _build_external_candidate_text(row)
                    if profile_text.strip():
                        profiles.append((row, profile_text))

                if profiles:
                    batch_input = [
                        {
                            "index": i,
                            "candidate_name": row.full_name,
                            "resume_text": text,
                        }
                        for i, (row, text) in enumerate(profiles)
                    ]
                    rankings = await _batch_rerank_gpt(
                        jd_text, batch_input, mode="resumes"
                    )

                    if rankings:
                        # GPT succeeded — use real scores
                        for ranking in rankings:
                            idx = ranking.get("index", 0)
                            if idx >= len(profiles):
                                continue
                            candidate_row = profiles[idx][0]
                            score = float(ranking.get("score", 50))

                            db.add(
                                ExternalCandidateMatch(
                                    candidate_id=str(candidate_row.id),
                                    job_id=job_id,
                                    score=score,
                                    highlights=ranking.get("highlights", []),
                                    gaps=ranking.get("gaps", []),
                                    fit_reason=ranking.get("fit_reason", ""),
                                )
                            )
                            matches_created += 1
                    else:
                        # GPT failed — use vector similarity as fallback
                        print("[EXT_MATCH DEBUG] GPT ranking failed — using similarity scores")
                        for row, profile_text in profiles:
                            sim_score = round(
                                float(getattr(row, "similarity", 0.5)) * 100, 1
                            )
                            db.add(
                                ExternalCandidateMatch(
                                    candidate_id=str(row.id),
                                    job_id=job_id,
                                    score=sim_score,
                                    highlights=[],
                                    gaps=[],
                                    fit_reason=(
                                        "Score based on vector similarity "
                                        "(AI re-ranking unavailable)"
                                    ),
                                )
                            )
                            matches_created += 1

            # ── Below-threshold candidates → score=0 ─────────────────────
            for candidate_row in below_threshold:
                db.add(
                    ExternalCandidateMatch(
                        candidate_id=str(candidate_row.id),
                        job_id=job_id,
                        score=0.0,
                        highlights=[],
                        gaps=["No vector similarity with job posting"],
                        fit_reason=(
                            "Different domain/industry — candidate embedding "
                            "does not match this job"
                        ),
                    )
                )
                matches_created += 1

            await db.commit()

            # ── Mark all processed candidates as matched ───────────────
            if matches_created > 0:
                from sqlalchemy import update
                await db.execute(
                    update(ExternalCandidate)
                    .where(
                        ExternalCandidate.id.in_([str(c.id) for c in similar_candidates]),
                        ExternalCandidate.is_matched == False
                    )
                    .values(is_matched=True)
                )
                await db.commit()

            logger.info(
                f"[EXT_MATCH] Created {matches_created} matches for job {job_id} "
                f"(similar={len(similar_candidates)}, below-threshold={len(below_threshold)})"
            )

        except Exception as e:
            logger.exception(
                f"[EXT_MATCH] Failed matching external candidates for job {job_id}: {e}"
            )
