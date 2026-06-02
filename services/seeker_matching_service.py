"""
Seeker Matching Service – bidirectional AI-powered job ↔ resume matching.
Optimized for minimum GPT calls: embeddings cached, GPT ranks in one batch.
"""
from __future__ import annotations
import json
import logging
from typing import List, Optional

from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.job import JobPosting
from models.resume import Resume
from models.match import Match
from services.ai_service import get_ai

logger = logging.getLogger(__name__)

SEEKER_TOP_N = 10
PROVIDER_TOP_N = 50
SIMILARITY_THRESHOLD = 0.55
MATCH_SCORE_THRESHOLD = 60  # Only store/return matches with score >= this


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
    text_content = (resume.parsed_text or "")[:6000]
    if not text_content.strip():
        return
    ai = get_ai()
    embedding = await ai.embed(text_content)
    # Store using raw SQL to avoid ORM vector cast issues
    await db.execute(
        text("UPDATE resumes SET embedding = CAST(:emb AS vector) WHERE id = :id"),
        {"emb": str(embedding), "id": resume.id},
    )
    await db.commit()


async def embed_and_store_job(job: JobPosting, db: AsyncSession) -> None:
    """Compute and persist embedding for a job posting."""
    if await _get_embedding_from_db(job):
        return
    skills_text = ", ".join(job.required_skills or [])
    text_content = f"Job Title: {job.title}\nIndustry: {job.industry or ''}\nSkills: {skills_text}\nDescription: {job.description}"
    ai = get_ai()
    embedding = await ai.embed(text_content[:6000])
    await db.execute(
        text("UPDATE job_postings SET embedding = CAST(:emb AS vector) WHERE id = :id"),
        {"emb": str(embedding), "id": job.id},
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
            f"IMPORTANT: Do NOT factor in location or geography when scoring. "
            f"Score purely on skills, experience, role alignment, and domain knowledge.\n"
            f"Keep highlights/gaps as short bullet strings. Score 0-100.\n\n"
            f'Example response:\n'
            f'{{"rankings": ['
            f'  {{"index":0,"score":85,"highlights":["Python experience","backend knowledge"],"gaps":["AWS required"],"fit_reason":"Strong technical match with relevant skills"}},'
            f'  {{"index":1,"score":20,"highlights":[],"gaps":["Different domain","No relevant skills"],"fit_reason":"Poor fit — candidate profile does not align with this role"}}'
            f']}}'
        )
    else:
        system = (
            "You are an expert recruiter. Given a job description and a list of candidate profiles, "
            "score each candidate for fit (0–100). Return ONLY a JSON object, no prose."
        )
        candidates_text = "\n".join(
            f"[{i}] {c.get('candidate_name', '')} – {c.get('resume_text', '')[:300]}"
            for i, c in enumerate(candidates)
        )
        user_prompt = (
            f"Job Description:\n{resume_text[:2000]}\n\n"
            f"Candidates:\n{candidates_text}\n\n"
            f"Return a JSON object with a 'rankings' key containing an array. "
            f"Each array element must have: index (int), score (int 0-100), "
            f"highlights (list of strings), gaps (list of strings), fit_reason (string).\n"
            f"IMPORTANT: Do NOT factor in location or geography when scoring. "
            f"Score purely on skills, experience, role alignment, and domain knowledge.\n"
            f"Keep highlights and gaps as short bullet-point strings. Score 0-100.\n\n"
            f'Example response:\n'
            f'{{"rankings": ['
            f'  {{"index":0,"score":85,"highlights":["Python experience","project management"],"gaps":["AWS required"],"fit_reason":"Strong technical match with relevant experience"}},'
            f'  {{"index":1,"score":40,"highlights":["Willing to learn"],"gaps":["No relevant skills","Wrong domain"],"fit_reason":"Entry level — lacks required experience"}}'
            f']}}'
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

    emb_str = str(resume_emb)

    # pgvector similarity query
    rows = await db.execute(
        text(
            f"""
            SELECT jp.id, jp.provider_id, jp.title, jp.description, jp.required_skills,
                   jp.salary_range, jp.job_type, jp.industry, jp.posted_by_name,
                   jp.experience_required, jp.created_at, jp.is_active,
                   1 - (jp.embedding <=> CAST(:emb AS vector)) AS similarity
            FROM job_postings jp
            WHERE jp.is_active = true
              AND jp.embedding IS NOT NULL
              AND (1 - (jp.embedding <=> CAST(:emb AS vector))) > {SIMILARITY_THRESHOLD}
            ORDER BY jp.embedding <=> CAST(:emb AS vector)
            LIMIT {SEEKER_TOP_N}
            """
        ),
        {"emb": emb_str},
    )
    jobs_raw = rows.fetchall()
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
        candidates = [
            {"index": i, "title": r.title, "description": r.description}
            for i, r in jobs_needing_ranking
        ]
        rankings = await _batch_rerank_gpt(resume.parsed_text or "", candidates, mode="jobs")
        
        # Store new matches in DB (only >= threshold)
        for ranking in rankings:
            original_idx = jobs_needing_ranking[ranking["index"]][0]
            job_row = jobs_needing_ranking[ranking["index"]][1]
            score = float(ranking.get("score", 70))

            if score < MATCH_SCORE_THRESHOLD:
                continue

            new_match = Match(
                seeker_id=seeker.id,
                job_id=str(job_row.id),
                score=score,
                highlights=ranking.get("highlights", []),
                gaps=ranking.get("gaps", []),
                fit_reason=ranking.get("fit_reason", "")
            )
            db.add(new_match)
            rank_map[original_idx] = ranking
        
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

    emb_str = str(job_emb)

    rows = await db.execute(
        text(
            f"""
            SELECT r.id as resume_id, r.parsed_text, r.parsed_json, r.filename,
                   u.id as user_id, u.first_name, u.last_name, u.email,
                   1 - (r.embedding <=> CAST(:emb AS vector)) AS similarity
            FROM resumes r
            JOIN users u ON u.id = r.user_id
            WHERE r.embedding IS NOT NULL
              AND u.role = 'seeker'
              AND u.is_verified = true
              AND (1 - (r.embedding <=> CAST(:emb AS vector))) > {SIMILARITY_THRESHOLD}
            ORDER BY r.embedding <=> CAST(:emb AS vector)
            LIMIT {PROVIDER_TOP_N}
            """
        ),
        {"emb": emb_str},
    )
    candidates_raw = rows.fetchall()
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
        jd_text = f"Title: {job.title}\nSkills: {', '.join(job.required_skills or [])}\n{job.description}"
        
        batch_input = [
            {"index": i, "candidate_name": f"{r.first_name} {r.last_name}", "resume_text": r.parsed_text or ""}
            for i, r in candidates_needing_ranking
        ]
        rankings = await _batch_rerank_gpt(jd_text, batch_input, mode="resumes")
        
        # Store new matches in DB
        for ranking in rankings:
            original_idx = candidates_needing_ranking[ranking["index"]][0]
            candidate_row = candidates_needing_ranking[ranking["index"]][1]
            
            new_match = Match(
                seeker_id=str(candidate_row.user_id),
                job_id=job.id,
                score=float(ranking.get("score", 70)),
                highlights=ranking.get("highlights", []),
                gaps=ranking.get("gaps", []),
                fit_reason=ranking.get("fit_reason", "")
            )
            db.add(new_match)
            rank_map[original_idx] = ranking
        
        await db.commit()

    # Build results from both cached and new matches
    results = []
    for i, row in enumerate(candidates_raw):
        seeker_id = str(row.user_id)
        
        # Use cached match if available
        if seeker_id in existing_matches:
            match = existing_matches[seeker_id]
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
            # Get the match_id from the newly created match
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
            # Delete all existing matches for this seeker
            await db.execute(
                text("DELETE FROM matches WHERE seeker_id = :sid"),
                {"sid": seeker_id},
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
            await db.execute(
                text("UPDATE resumes SET embedding = NULL WHERE id = :id"),
                {"id": resume.id},
            )
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
            # Delete all existing matches for this job
            await db.execute(
                text("DELETE FROM matches WHERE job_id = :jid"),
                {"jid": job_id},
            )
            await db.commit()
            logger.info(f"[REMATCH] Cleared all matches for job {job_id}")

            # Get the job
            job = await db.get(JobPosting, job_id)
            if not job:
                logger.error(f"[REMATCH] Job {job_id} not found")
                return

            # Clear stale embedding and re-embed
            await db.execute(
                text("UPDATE job_postings SET embedding = NULL WHERE id = :id"),
                {"id": job_id},
            )
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
            
            emb_str = str(resume_emb)
            
            # Find all active jobs with similarity above threshold
            rows = await db.execute(
                text(
                    f"""
                    SELECT jp.id, jp.provider_id, jp.title, jp.description, jp.required_skills,
                           jp.salary_range, jp.job_type, jp.industry, jp.posted_by_name,
                           jp.experience_required, jp.created_at, jp.is_active,
                           1 - (jp.embedding <=> CAST(:emb AS vector)) AS similarity
                    FROM job_postings jp
                    WHERE jp.is_active = true
                      AND jp.embedding IS NOT NULL
                      AND (1 - (jp.embedding <=> CAST(:emb AS vector))) > {SIMILARITY_THRESHOLD}
                    ORDER BY jp.embedding <=> CAST(:emb AS vector)
                    LIMIT {SEEKER_TOP_N * 2}
                    """
                ),
                {"emb": emb_str},
            )
            jobs_raw = rows.fetchall()
            
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
            
            # Run GPT batch ranking
            candidates = [
                {"index": i, "title": r.title, "description": r.description}
                for i, r in jobs_to_process
            ]
            rankings = await _batch_rerank_gpt(resume.parsed_text or "", candidates, mode="jobs")

            # Store matches in DB
            matches_created = 0
            from services.notification_service import create_notification
            from models.notification import NotificationType

            if rankings:
                # GPT succeeded — use real scores (only store >= threshold)
                for ranking in rankings:
                    job_row = jobs_to_process[ranking["index"]][1]
                    score = float(ranking.get("score", 70))

                    if score < MATCH_SCORE_THRESHOLD:
                        continue

                    new_match = Match(
                        seeker_id=seeker.id,
                        job_id=str(job_row.id),
                        score=score,
                        highlights=ranking.get("highlights", []),
                        gaps=ranking.get("gaps", []),
                        fit_reason=ranking.get("fit_reason", "")
                    )
                    db.add(new_match)
                    await db.flush()

                    # Notify seeker of high matches
                    if score >= 85:
                        await create_notification(
                            db=db,
                            user_id=seeker.id,
                            type=NotificationType.match,
                            title=f"🔥 Perfect match found: {job_row.title}",
                            message=f"We found a job that perfectly matches your profile! {job_row.title} with a {score}% match score.",
                            related_job_id=str(job_row.id),
                        )
                        # Also notify the job's provider about this strong candidate
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
            else:
                # GPT failed — fallback to vector similarity scores (only store >= threshold)
                logger.warning("[PROACTIVE_MATCH] GPT ranking failed — using similarity scores")
                for _, job_row in jobs_to_process:
                    sim_score = round(
                        float(getattr(job_row, "similarity", 0.5)) * 100, 1
                    )
                    if sim_score < MATCH_SCORE_THRESHOLD:
                        continue
                    new_match = Match(
                        seeker_id=seeker.id,
                        job_id=str(job_row.id),
                        score=sim_score,
                        highlights=[],
                        gaps=[],
                        fit_reason="Score based on vector similarity (AI re-ranking unavailable)"
                    )
                    db.add(new_match)
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
            
            emb_str = str(job_emb)

            
            # Find all matching candidates
            rows = await db.execute(
                text(
                    f"""
                    SELECT r.id as resume_id, r.parsed_text, r.parsed_json, r.filename,
                           u.id as user_id, u.first_name, u.last_name, u.email,
                           1 - (r.embedding <=> CAST(:emb AS vector)) AS similarity
                    FROM resumes r
                    JOIN users u ON u.id = r.user_id
                    WHERE r.embedding IS NOT NULL
                      AND u.role = 'seeker'
                      AND u.is_verified = true
                      AND (1 - (r.embedding <=> CAST(:emb AS vector))) > {SIMILARITY_THRESHOLD}
                    ORDER BY r.embedding <=> CAST(:emb AS vector)
                    LIMIT {PROVIDER_TOP_N}
                    """
                ),
                {"emb": emb_str},
            )
            candidates_raw = rows.fetchall()
            
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
            
            # Run GPT batch ranking
            jd_text = f"Title: {job.title}\nSkills: {', '.join(job.required_skills or [])}\n{job.description}"
            batch_input = [
                {"index": i, "candidate_name": f"{r.first_name} {r.last_name}", "resume_text": r.parsed_text or ""}
                for i, r in candidates_to_process
            ]
            rankings = await _batch_rerank_gpt(jd_text, batch_input, mode="resumes")
            
            # Store matches in DB
            matches_created = 0
            from services.notification_service import create_notification
            from models.notification import NotificationType

            if rankings:
                # GPT succeeded — use real scores
                for ranking in rankings:
                    candidate_row = candidates_to_process[ranking["index"]][1]
                    score = float(ranking.get("score", 70))
                    
                    new_match = Match(
                        seeker_id=str(candidate_row.user_id),
                        job_id=job.id,
                        score=score,
                        highlights=ranking.get("highlights", []),
                        gaps=ranking.get("gaps", []),
                        fit_reason=ranking.get("fit_reason", "")
                    )
                    db.add(new_match)
                    await db.flush()

                    # Notify provider of high matches
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
                        # Also notify the seeker about this strong match
                        await create_notification(
                            db=db,
                            user_id=str(candidate_row.user_id),
                            type=NotificationType.match,
                            title=f"🔥 Perfect match found: {job.title}",
                            message=f"You're a {score}% match for {job.title}! Log in to view and apply.",
                            related_job_id=str(job.id),
                        )

                    matches_created += 1
            else:
                # GPT failed — fallback to vector similarity scores
                logger.warning("[PROACTIVE_MATCH] GPT ranking failed — using similarity scores")
                for _, candidate_row in candidates_to_process:
                    sim_score = round(
                        float(getattr(candidate_row, "similarity", 0.5)) * 100, 1
                    )
                    new_match = Match(
                        seeker_id=str(candidate_row.user_id),
                        job_id=job.id,
                        score=sim_score,
                        highlights=[],
                        gaps=[],
                        fit_reason="Score based on vector similarity (AI re-ranking unavailable)"
                    )
                    db.add(new_match)
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

            # Delete matches
            await db.execute(
                text("DELETE FROM matches WHERE job_id = :jid"),
                {"jid": job_id},
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
