import json
import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import redis.asyncio as aioredis
from sqlalchemy import select, func, or_, and_, desc, asc, cast, String, Text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.config import settings
from app.modules.jobs_portal.models.scholarship import Scholarship
from app.shared.services.scholarship_sync_service import ScholarshipSyncService, REDIS_SCHOLARSHIP_PREFIX

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 5 * 3600  # 5 hours


def generate_cache_key(prefix: str, params: Dict[str, Any]) -> str:
    """Generate a consistent md5 hash cache key for query parameters."""
    serialized = json.dumps(params, sort_keys=True, default=str)
    hashed = hashlib.md5(serialized.encode("utf-8")).hexdigest()
    return f"{prefix}:{hashed}"


async def get_redis_connection() -> Optional[aioredis.Redis]:
    """Get active Redis client or None on failure."""
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return r
    except Exception as e:
        logger.warning(f"[ScholarshipsController] Redis connection failed: {e}")
        return None


def serialize_scholarship(s: Scholarship) -> Dict[str, Any]:
    """Convert Scholarship model to clean serializable dict."""
    return {
        "id": str(s.id),
        "external_id": s.external_id,
        "source_platform": s.source_platform,
        "title": s.title,
        "slug": s.slug,
        "organization_name": s.organization_name,
        "organization_logo": s.organization_logo,
        "banner_image": s.banner_image,
        "description": s.description,
        "eligibility_criteria": s.eligibility_criteria,
        "award_amount": s.award_amount,
        "award_type": s.award_type,
        "currency": s.currency,
        "target_education_levels": s.target_education_levels or [],
        "gender_eligibility": s.gender_eligibility,
        "region_or_country": s.region_or_country,
        "deadline": s.deadline.isoformat() if s.deadline else None,
        "is_featured": s.is_featured,
        "is_active": s.is_active,
        "application_url": s.application_url,
        "last_synced_at": s.last_synced_at.isoformat() if s.last_synced_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


class ScholarshipsController:
    @staticmethod
    async def get_scholarships(
        db: AsyncSession,
        search: Optional[str] = None,
        source: Optional[str] = None,
        education_level: Optional[str] = None,
        gender: Optional[str] = None,
        is_featured: Optional[bool] = None,
        sort_by: str = "deadline_asc",
        page: int = 1,
        page_size: int = 12,
    ) -> Dict[str, Any]:
        """Fetch filtered, paginated scholarships with Redis cache fallback."""
        cache_params = {
            "search": search,
            "source": source,
            "education_level": education_level,
            "gender": gender,
            "is_featured": is_featured,
            "sort_by": sort_by,
            "page": page,
            "page_size": page_size,
        }
        cache_key = generate_cache_key(f"{REDIS_SCHOLARSHIP_PREFIX}:list", cache_params)

        # 1. Try reading from Redis Cache
        redis_client = await get_redis_connection()
        if redis_client:
            try:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    await redis_client.close()
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"[ScholarshipsController] Redis get error: {e}")

        # 2. Build Database Query
        query = select(Scholarship).where(Scholarship.is_active == True)

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(Scholarship.title).like(term),
                    func.lower(Scholarship.organization_name).like(term),
                    func.lower(Scholarship.description).like(term),
                    func.lower(Scholarship.eligibility_criteria).like(term),
                )
            )

        if source and source.strip().lower() not in ("all", ""):
            query = query.where(Scholarship.source_platform == source.strip().lower())

        if gender and gender.strip().lower() not in ("all", ""):
            query = query.where(
                or_(
                    func.lower(Scholarship.gender_eligibility) == gender.strip().lower(),
                    Scholarship.gender_eligibility == "All",
                )
            )

        if is_featured is not None:
            query = query.where(Scholarship.is_featured == is_featured)

        if education_level and education_level.strip().lower() not in ("all", ""):
            edu_term = f"%{education_level.strip().lower()}%"
            query = query.where(
                or_(
                    cast(Scholarship.target_education_levels, String).ilike(edu_term),
                    func.lower(Scholarship.eligibility_criteria).like(edu_term),
                    func.lower(Scholarship.title).like(edu_term),
                )
            )

        # Count total matching records
        count_query = select(func.count()).select_from(query.subquery())
        total_records = (await db.execute(count_query)).scalar() or 0

        # Sort order
        if sort_by == "deadline_asc":
            # Place null deadlines at the end
            query = query.order_by(Scholarship.deadline.asc().nullslast(), Scholarship.created_at.desc())
        elif sort_by == "recent":
            query = query.order_by(Scholarship.created_at.desc())
        elif sort_by == "featured":
            query = query.order_by(Scholarship.is_featured.desc(), Scholarship.deadline.asc().nullslast())
        else:
            query = query.order_by(Scholarship.deadline.asc().nullslast(), Scholarship.created_at.desc())

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        scholarships = result.scalars().all()

        response = {
            "items": [serialize_scholarship(s) for s in scholarships],
            "total": total_records,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_records + page_size - 1) // page_size if total_records > 0 else 1,
        }

        # 3. Store result in Redis Cache (5-hour TTL)
        if redis_client:
            try:
                await redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response))
                await redis_client.close()
            except Exception as e:
                logger.warning(f"[ScholarshipsController] Redis set error: {e}")

        return response

    @staticmethod
    async def get_scholarship_stats(db: AsyncSession) -> Dict[str, Any]:
        """Aggregate summary counts and metrics for the Scholarships discovery hub."""
        cache_key = f"{REDIS_SCHOLARSHIP_PREFIX}:stats"
        redis_client = await get_redis_connection()
        if redis_client:
            try:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    await redis_client.close()
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"[ScholarshipsController] Redis stats error: {e}")

        now = datetime.utcnow()
        total_active = (await db.execute(
            select(func.count(Scholarship.id)).where(Scholarship.is_active == True)
        )).scalar() or 0

        total_featured = (await db.execute(
            select(func.count(Scholarship.id)).where(Scholarship.is_active == True, Scholarship.is_featured == True)
        )).scalar() or 0

        unstop_count = (await db.execute(
            select(func.count(Scholarship.id)).where(Scholarship.is_active == True, Scholarship.source_platform == "unstop")
        )).scalar() or 0

        b4s_count = (await db.execute(
            select(func.count(Scholarship.id)).where(Scholarship.is_active == True, Scholarship.source_platform == "buddy4study")
        )).scalar() or 0

        stats = {
            "total_active": total_active,
            "total_featured": total_featured,
            "unstop_count": unstop_count,
            "buddy4study_count": b4s_count,
            "last_updated": now.isoformat(),
        }

        if redis_client:
            try:
                await redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(stats))
                await redis_client.close()
            except Exception as e:
                logger.warning(f"[ScholarshipsController] Redis set stats error: {e}")

        return stats

    @staticmethod
    async def get_scholarship_by_id_or_slug(db: AsyncSession, identifier: str) -> Dict[str, Any]:
        """Retrieve single scholarship by UUID or slug."""
        import uuid as uuid_pkg
        parsed_uuid = None
        try:
            parsed_uuid = uuid_pkg.UUID(identifier)
        except (ValueError, TypeError, AttributeError):
            pass

        conditions = [Scholarship.slug == identifier, Scholarship.external_id == identifier]
        if parsed_uuid:
            conditions.append(Scholarship.id == parsed_uuid)

        query = select(Scholarship).where(or_(*conditions))
        result = await db.execute(query)
        scholarship = result.scalars().first()
        if not scholarship:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scholarship not found")
        return serialize_scholarship(scholarship)

    @staticmethod
    async def trigger_manual_sync() -> Dict[str, Any]:
        """Trigger an instant scraper & sync run."""
        return await ScholarshipSyncService.sync_all_scholarships()
