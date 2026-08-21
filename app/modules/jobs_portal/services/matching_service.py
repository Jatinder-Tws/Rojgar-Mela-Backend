"""
Legacy compatibility shim — re-exports from seeker_matching_service
and external_candidate_matching_service.
Import directly from those modules in new code.
"""
from app.modules.jobs_portal.services.seeker_matching_service import ( # noqa: F401
    _get_embedding_from_db,
    _batch_rerank_gpt,
    _extract_rankings,
    _cleanup_job_matches_and_notify,
    embed_and_store_resume,
    embed_and_store_job,
    match_jobs_for_seeker,
    match_candidates_for_job,
    invalidate_seeker_matches,
    invalidate_job_matches,
    proactive_match_resume_to_jobs,
    proactive_match_job_to_candidates,
    SEEKER_TOP_N,
    PROVIDER_TOP_N,
    SIMILARITY_THRESHOLD,
)

from app.modules.jobs_portal.services.external_candidate_matching_service import ( # noqa: F401
    embed_and_store_external_candidate,
    proactive_match_external_candidate_to_jobs,
    proactive_match_job_to_external_candidates,
    EXTERNAL_TOP_N,
    EXTERNAL_SIMILARITY_THRESHOLD,
)
