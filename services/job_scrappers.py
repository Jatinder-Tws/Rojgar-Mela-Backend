"""
Job Scrapers Service for external job portals (Apna.co, Foundit.in, & Greenhouse.io)
Layer: Service
Responsibilities:
- Async non-blocking scraping with httpx.AsyncClient
- True parallel execution using asyncio.gather for Apna, Foundit, & Greenhouse
- External API pagination support (Apna `page`/`page_size`, Foundit `start`/`limit`, Greenhouse filtered)
- Portal total count extraction (`count` vs `total_count`)
- Result caching and retrieval with Redis (redis.asyncio)
- Standard JSON response format (non-streaming with pagination)
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
import httpx

try:
    import redis.asyncio as aioredis
except ImportError:
    import aioredis

from config import settings

logger = logging.getLogger(__name__)

# Singleton async Redis client instance
_async_redis_client = None


async def get_redis_client():
    """Retrieve or initialize the async Redis client."""
    global _async_redis_client
    if _async_redis_client is None:
        try:
            _async_redis_client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=3.0
            )
            await _async_redis_client.ping()
            logger.info("Successfully connected to Redis for JobScraper caching.")
        except Exception as e:
            logger.warning(f"Redis connection failed in JobScraper (falling back to uncached): {e}")
            _async_redis_client = None
    return _async_redis_client


async def clear_job_search_cache():
    """Clear all existing job search cached keys from Redis."""
    try:
        redis_client = await get_redis_client()
        if redis_client:
            keys = await redis_client.keys("job_search:*")
            if keys:
                await redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} job search keys from Redis cache.")
                return len(keys)
    except Exception as e:
        logger.warning(f"Failed to clear Redis job search cache: {e}")
    return 0


class JobScraper:
    """Async scraper class for Apna.co, Foundit.in, and Greenhouse.io job portals."""

    APNA_URL = "https://production.apna.co/user-profile-orchestrator/public/v1/jobs/"
    FOUNDIT_URL = "https://www.foundit.in/home/api/searchResultsPage"
    GREENHOUSE_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    DEFAULT_GREENHOUSE_BOARDS = [
        "github", "stripe", "cloudflare", "gitlab", "postman", "datadog",
        "figma", "hashicorp", "reddit", "coinbase", "automattic", "discord",
        "elastic", "mongodb", "canonical", "spotify", "deliveroo", "docker",
        "grafana", "vimeo", "unity", "pinterest", "robinhood"
    ]

    APNA_HEADERS = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'origin': 'https://apna.co',
        'priority': 'u=1, i',
        'referer': 'https://apna.co/',
        'sec-ch-ua': '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
    }

    FOUNDIT_HEADERS = {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'priority': 'u=1, i',
        'referer': 'https://www.foundit.in/',
        'sec-ch-ua': '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
        'x-source-site-context': 'rexmonster',
    }

    GREENHOUSE_HEADERS = {
        'accept': 'application/json',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
    }

    @staticmethod
    def _normalize_apna_job(item: dict) -> dict:
        """Normalize job item from Apna.co JSON response."""
        job_id = str(item.get("id") or item.get("job_id") or "")
        title = item.get("title") or item.get("job_title") or item.get("designation") or "Job Opening"

        company = "Unknown Company"
        if isinstance(item.get("organization"), dict):
            company = item["organization"].get("name") or company
        elif isinstance(item.get("company"), dict):
            company = item["company"].get("name") or company
        elif isinstance(item.get("company_name"), str):
            company = item["company_name"]

        location = item.get("location") or item.get("city_name") or item.get("location_name") or "India"
        if isinstance(location, dict):
            location = location.get("name") or location.get("city") or location.get("label") or "India"

        salary = item.get("salary_formatted") or ""
        if not salary:
            min_sal = item.get("min_salary") or item.get("salary_min")
            max_sal = item.get("max_salary") or item.get("salary_max")
            sal_type = item.get("salary_type") or "month"
            if min_sal or max_sal:
                salary = f"₹{min_sal or 0} - ₹{max_sal or 'N/A'}/{sal_type}"
            else:
                salary = "Disclosed on call / Apply to view"

        exp = item.get("experience_required") or item.get("exp_required_text") or item.get("experience") or item.get("min_experience") or "0-2 years"
        if isinstance(exp, dict):
            exp = f"{exp.get('min', 0)}-{exp.get('max', 2)} years"

        url = item.get("canonical_url") or item.get("share_link") or item.get("deep_link") or (f"https://apna.co/job/{job_id}" if job_id else "https://apna.co")

        return {
            "id": f"apna_{job_id}",
            "title": title,
            "company": company,
            "location": str(location),
            "salary": str(salary),
            "experience": str(exp),
            "source": "Apna.co",
            "url": url,
            "skills": item.get("skills") or item.get("tags") or [],
            "posted_date": item.get("created_at") or item.get("posted_on") or ""
        }

    @staticmethod
    def _normalize_foundit_job(item: dict) -> dict:
        """Normalize job item from Foundit.in JSON response."""
        job_id = str(item.get("jobId") or item.get("id") or "")
        title = item.get("title") or item.get("jobTitle") or "Job Opening"

        company = "Unknown Company"
        if isinstance(item.get("companyName"), str):
            company = item["companyName"]
        elif isinstance(item.get("company"), dict):
            company = item["company"].get("name") or company

        locs = item.get("locations") or item.get("locationText") or item.get("location") or []
        if isinstance(locs, list):
            location_names = []
            for l in locs:
                if isinstance(l, dict):
                    location_names.append(l.get("city") or l.get("country") or "Remote")
                else:
                    location_names.append(str(l))
            location = ", ".join(location_names) if location_names else "India"
        else:
            location = str(locs) or "India"

        salary = item.get("salary") or item.get("salaryText") or item.get("salaryDisplay") or "Not Disclosed"

        exp = item.get("experienceText") or item.get("experience") or "0-3 years"
        if not exp or exp == "0-3 years":
            min_exp = item.get("minimumExperience", {}).get("years", 0) if isinstance(item.get("minimumExperience"), dict) else 0
            max_exp = item.get("maximumExperience", {}).get("years", 3) if isinstance(item.get("maximumExperience"), dict) else 3
            exp = f"{min_exp}-{max_exp} years"

        url = item.get("redirectUrl") or (f"https://www.foundit.in/job/{job_id}" if job_id else "https://www.foundit.in")

        return {
            "id": f"foundit_{job_id}",
            "title": title,
            "company": company,
            "location": str(location),
            "salary": str(salary),
            "experience": str(exp),
            "source": "Foundit.in",
            "url": url,
            "skills": item.get("skills") or item.get("roles") or [],
            "posted_date": item.get("postedDate") or item.get("createdDate") or ""
        }

    @staticmethod
    def _normalize_greenhouse_job(item: dict, board_token: str = "") -> dict:
        """Normalize job item from Greenhouse Job Board JSON response."""
        job_id = str(item.get("id") or "")
        title = item.get("title") or "Job Opening"

        location_obj = item.get("location") or {}
        location_name = location_obj.get("name") if isinstance(location_obj, dict) else str(location_obj)
        if not location_name:
            location_name = "Remote / Flexible"

        company_name = board_token.replace("-", " ").replace("_", " ").title() if board_token else "Greenhouse Employer"
        url = item.get("absolute_url") or f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}"

        return {
            "id": f"greenhouse_{job_id}",
            "title": title,
            "company": company_name,
            "location": str(location_name),
            "salary": "Disclosed in application",
            "experience": "Not specified",
            "source": f"Greenhouse ({company_name})",
            "url": url,
            "skills": [title] if title else [],
            "posted_date": item.get("updated_at") or ""
        }

    async def fetch_apna(self, client: httpx.AsyncClient, query: str, location: str = "", page: int = 1, page_size: int = 20) -> dict:
        """Fetch paginated jobs from Apna.co API asynchronously."""
        params = {
            "search": "true",
            "session_id": "search_1785905455473_q4w4r5c",
            "raw_text_correction": "true",
            "text": query,
            "entity_id": "2798",
            "entity_type": "JobTitle",
            "page": page,
            "page_size": page_size
        }
        if location:
            params["location"] = location

        try:
            response = await client.get(self.APNA_URL, headers=self.APNA_HEADERS, params=params, timeout=12.0)
            if response.status_code == 200:
                data = response.json()
                raw_jobs = []
                total_count = 0
                if isinstance(data, dict):
                    total_count = data.get("count") or 0
                    results_val = data.get("results")
                    if isinstance(results_val, dict):
                        raw_jobs = results_val.get("jobs") or []
                        if not total_count:
                            total_count = results_val.get("total_jobs") or 0
                    elif isinstance(results_val, list):
                        raw_jobs = results_val
                    else:
                        raw_jobs = data.get("jobs") or data.get("data", {}).get("jobs") or []
                elif isinstance(data, list):
                    raw_jobs = data

                normalized = [self._normalize_apna_job(j) for j in raw_jobs if isinstance(j, dict)]
                if not total_count:
                    total_count = len(normalized)

                return {
                    "portal": "Apna.co",
                    "status": "success",
                    "count": len(normalized),
                    "total_count": total_count,
                    "jobs": normalized
                }
            return {
                "portal": "Apna.co",
                "status": "error",
                "error": f"HTTP status code {response.status_code}",
                "count": 0,
                "total_count": 0,
                "jobs": []
            }
        except Exception as e:
            logger.error(f"Apna scraper exception: {e}")
            return {
                "portal": "Apna.co",
                "status": "error",
                "error": str(e),
                "count": 0,
                "total_count": 0,
                "jobs": []
            }

    async def fetch_foundit(self, client: httpx.AsyncClient, query: str, location: str = "", page: int = 1, page_size: int = 20) -> dict:
        """Fetch paginated jobs from Foundit.in API asynchronously."""
        start_offset = max(0, (page - 1) * page_size)
        params = {
            "start": start_offset,
            "limit": page_size,
            "query": query,
            "queryDerived": "true",
            "countries": "India",
            "variantName": "DEFAULT"
        }
        if location:
            params["locations"] = f'"{location}"'

        try:
            response = await client.get(self.FOUNDIT_URL, headers=self.FOUNDIT_HEADERS, params=params, timeout=12.0)
            if response.status_code == 200:
                data = response.json()
                raw_jobs = []
                total_count = 0
                if isinstance(data, dict):
                    total_count = data.get("totalResults") or data.get("totalCount") or data.get("count") or 0
                    if not total_count and isinstance(data.get("meta"), dict):
                        total_count = data["meta"].get("totalCount") or 0
                    raw_jobs = data.get("jobResults") or data.get("data") or data.get("jobs") or []
                elif isinstance(data, list):
                    raw_jobs = data

                normalized = [self._normalize_foundit_job(j) for j in raw_jobs if isinstance(j, dict)]
                if not total_count:
                    total_count = len(normalized)

                return {
                    "portal": "Foundit.in",
                    "status": "success",
                    "count": len(normalized),
                    "total_count": total_count,
                    "jobs": normalized
                }
            return {
                "portal": "Foundit.in",
                "status": "error",
                "error": f"HTTP status code {response.status_code}",
                "count": 0,
                "total_count": 0,
                "jobs": []
            }
        except Exception as e:
            logger.error(f"Foundit scraper exception: {e}")
            return {
                "portal": "Foundit.in",
                "status": "error",
                "error": str(e),
                "count": 0,
                "total_count": 0,
                "jobs": []
            }

    async def _fetch_greenhouse_single_board(
        self, client: httpx.AsyncClient, board_token: str, query: str, location: str = ""
    ) -> List[dict]:
        """Fetch and filter jobs from a single Greenhouse board endpoint."""
        url = f"{self.GREENHOUSE_BASE_URL}/{board_token}/jobs?content=true"
        try:
            response = await client.get(url, headers=self.GREENHOUSE_HEADERS, timeout=8.0)
            if response.status_code == 200:
                data = response.json()
                raw_jobs = data.get("jobs") or []
                matching_jobs = []
                q_lower = query.strip().lower()
                query_words = [w for w in q_lower.replace("-", " ").replace(",", " ").split() if len(w) >= 2]
                loc_lower = location.strip().lower()

                for item in raw_jobs:
                    if not isinstance(item, dict):
                        continue
                    job_title = (item.get("title") or "").lower()
                    job_content = (item.get("content") or "").lower() if isinstance(item.get("content"), str) else ""

                    loc_name = ""
                    loc_obj = item.get("location")
                    if isinstance(loc_obj, dict):
                        loc_name = (loc_obj.get("name") or "").lower()
                    elif isinstance(loc_obj, str):
                        loc_name = loc_obj.lower()

                    if not q_lower:
                        title_match = True
                    else:
                        title_match = (q_lower in job_title) or any(w in job_title for w in query_words if len(w) >= 3)
                        if not title_match and "python" in q_lower and "python" in job_content:
                            title_match = True

                    loc_match = (not loc_lower) or (loc_lower in loc_name) or ("remote" in loc_name) or ("flexible" in loc_name)

                    if title_match and loc_match:
                        matching_jobs.append(self._normalize_greenhouse_job(item, board_token))
                return matching_jobs
        except Exception as e:
            logger.debug(f"Greenhouse board '{board_token}' fetch exception: {e}")
        return []

    async def fetch_greenhouse(
        self, client: httpx.AsyncClient, query: str, location: str = "", page: int = 1, page_size: int = 20, board_token: str = ""
    ) -> dict:
        """Fetch jobs from Greenhouse Job Board API across company boards concurrently."""
        try:
            boards_to_search = [board_token.strip().lower()] if board_token else self.DEFAULT_GREENHOUSE_BOARDS
            tasks = [self._fetch_greenhouse_single_board(client, b, query, location) for b in boards_to_search]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_gh_jobs = []
            for r in results:
                if isinstance(r, list):
                    all_gh_jobs.extend(r)

            # Paginate aggregated Greenhouse results
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_jobs = all_gh_jobs[start_idx:end_idx]

            return {
                "portal": "Greenhouse",
                "status": "success",
                "count": len(paginated_jobs),
                "total_count": len(all_gh_jobs),
                "jobs": paginated_jobs
            }
        except Exception as e:
            logger.error(f"Greenhouse scraper exception: {e}")
            return {
                "portal": "Greenhouse",
                "status": "error",
                "error": str(e),
                "count": 0,
                "total_count": 0,
                "jobs": []
            }


async def search_external_jobs_paginated(
    query: str,
    location: str = "",
    page: int = 1,
    page_size: int = 20,
    greenhouse_board: str = "",
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Perform a paginated async job search across Apna.co, Foundit.in, and Greenhouse.io in parallel.
    Returns a standard JSON object cached in Redis.
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    gh_board_str = greenhouse_board.strip().lower() if greenhouse_board else ""
    cache_key = f"job_search:{query.strip().lower()}:{location.strip().lower()}:gh_{gh_board_str}:p{page}:s{page_size}"
    redis_client = await get_redis_client()

    # Step 1: Check Redis Cache
    if redis_client:
        if force_refresh:
            try:
                await redis_client.delete(cache_key)
            except Exception:
                pass
        else:
            try:
                cached_raw = await redis_client.get(cache_key)
                if cached_raw:
                    parsed = json.loads(cached_raw)
                    parsed["from_cache"] = True
                    return parsed
            except Exception as e:
                logger.warning(f"Failed reading from Redis cache: {e}")

    # Step 2: Parallel API Execution with httpx for all 3 portals (Apna, Foundit, Greenhouse)
    scraper = JobScraper()
    async with httpx.AsyncClient(follow_redirects=True) as client:
        apna_task = scraper.fetch_apna(client, query, location, page=page, page_size=page_size)
        foundit_task = scraper.fetch_foundit(client, query, location, page=page, page_size=page_size)
        greenhouse_task = scraper.fetch_greenhouse(client, query, location, page=page, page_size=page_size, board_token=gh_board_str)

        apna_res, foundit_res, greenhouse_res = await asyncio.gather(apna_task, foundit_task, greenhouse_task, return_exceptions=True)

    # Normalize portal output
    apna_data = apna_res if isinstance(apna_res, dict) else {"portal": "Apna.co", "status": "error", "error": str(apna_res), "count": 0, "total_count": 0, "jobs": []}
    foundit_data = foundit_res if isinstance(foundit_res, dict) else {"portal": "Foundit.in", "status": "error", "error": str(foundit_res), "count": 0, "total_count": 0, "jobs": []}
    greenhouse_data = greenhouse_res if isinstance(greenhouse_res, dict) else {"portal": "Greenhouse", "status": "error", "error": str(greenhouse_res), "count": 0, "total_count": 0, "jobs": []}

    all_jobs = []
    if apna_data.get("jobs"):
        all_jobs.extend(apna_data["jobs"])
    if foundit_data.get("jobs"):
        all_jobs.extend(foundit_data["jobs"])
    if greenhouse_data.get("jobs"):
        all_jobs.extend(greenhouse_data["jobs"])

    total_available_across_all_portals = (
        apna_data.get("total_count", 0) +
        foundit_data.get("total_count", 0) +
        greenhouse_data.get("total_count", 0)
    )

    response_payload = {
        "success": True,
        "query": query,
        "location": location,
        "page": page,
        "page_size": page_size,
        "page_jobs_count": len(all_jobs),
        "total_available_jobs": total_available_across_all_portals,
        "from_cache": False,
        "portals": {
            "apna": {
                "status": apna_data.get("status"),
                "count": apna_data.get("count", 0),
                "total_count": apna_data.get("total_count", 0),
                "error": apna_data.get("error")
            },
            "foundit": {
                "status": foundit_data.get("status"),
                "count": foundit_data.get("count", 0),
                "total_count": foundit_data.get("total_count", 0),
                "error": foundit_data.get("error")
            },
            "greenhouse": {
                "status": greenhouse_data.get("status"),
                "count": greenhouse_data.get("count", 0),
                "total_count": greenhouse_data.get("total_count", 0),
                "error": greenhouse_data.get("error")
            }
        },
        "jobs": all_jobs
    }

    # Step 3: Cache result in Redis for 10 seconds (testing mode)
    if redis_client and all_jobs:
        try:
            await redis_client.setex(cache_key, 10, json.dumps(response_payload))
            logger.info(f"Saved {len(all_jobs)} paginated jobs to Redis key '{cache_key}' (TTL=10s)")
        except Exception as e:
            logger.warning(f"Failed to cache search results in Redis: {e}")

    return response_payload
