import logging
import re
import html
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import httpx
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.modules.jobs_portal.models.scholarship import Scholarship

logger = logging.getLogger(__name__)

# Default Buddy4Study Public Guest Token (Can be overridden via env / Redis cache)
DEFAULT_B4S_TOKEN = getattr(
    settings,
    "BUDDY4STUDY_BEARER_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJyZWFkIiwid3JpdGUiLCJ0cnVzdCJdLCJleHAiOjE4MTk3NzM2NzgsImF1dGhvcml0aWVzIjpbIlVTRVIiXSwianRpIjoiNjE5MGM3YzItYjIxNS00N2ZlLTk5YWEtM2Y1ZTg0NGMzZjAxIiwiY2xpZW50X2lkIjoiYjRzIn0.5o_gkFQ_tQSo8B7s1yqsAChe1gLn_ufLwHrBTFtadVY"
)

REDIS_SCHOLARSHIP_PREFIX = "scholarships"
REDIS_B4S_TOKEN_KEY = "scholarships:b4s_token"


def clean_html_text(raw_html: Optional[str]) -> str:
    """Strip HTML tags and unescape HTML entities."""
    if not raw_html:
        return ""
    clean_re = re.compile(r"<[^>]+>")
    clean_text = re.sub(clean_re, " ", str(raw_html))
    clean_text = html.unescape(clean_text)
    return " ".join(clean_text.split()).strip()


def parse_datetime_safe(date_str: Optional[str]) -> Optional[datetime]:
    """Safely parse various datetime formats into UTC naive datetime."""
    if not date_str:
        return None
    date_str = str(date_str).strip()
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=None)
        except ValueError:
            continue
    try:
        from dateutil import parser
        dt = parser.parse(date_str)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


class ScholarshipSyncService:
    @staticmethod
    async def fetch_unstop_scholarships() -> List[Dict[str, Any]]:
        """Fetch live open scholarships from Unstop API."""
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "referer": "https://unstop.com/scholarships?oppstatus=open",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
        }
        url = "https://unstop.com/api/public/opportunity/search-result"
        params = {
            "opportunity": "scholarships",
            "page": 1,
            "per_page": 50,
            "oppstatus": "open",
            "undefined": "true",
        }

        normalized_items: List[Dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"[ScholarshipSync] Unstop returned status {resp.status_code}")
                    return []

                payload = resp.json()
                data_list = payload.get("data", {}).get("data", [])
                if not isinstance(data_list, list):
                    return []

                for item in data_list:
                    ext_id = str(item.get("id") or "")
                    if not ext_id:
                        continue

                    title = item.get("title") or "Scholarship Opportunity"
                    slug = item.get("public_url") or item.get("slug") or ext_id

                    org_data = item.get("organisation") or {}
                    org_name = org_data.get("name") or item.get("organisation_name") or "Unstop Partner"
                    org_logo = org_data.get("logo_url2") or org_data.get("logo_url") or ""
                    banner_img = (item.get("banner_mobile") or {}).get("url") or (item.get("banner_desktop") or {}).get("url") or ""

                    desc = (item.get("seo_details") or {}).get("meta_desc") or item.get("details") or ""
                    clean_desc = clean_html_text(desc)

                    # Extract eligibility and education levels
                    target_levels: List[str] = []
                    eligibility_str = item.get("eligibility") or ""
                    if isinstance(eligibility_str, list):
                        target_levels = [str(x) for x in eligibility_str]
                        eligibility_str = ", ".join(target_levels)
                    elif isinstance(eligibility_str, str):
                        eligibility_str = clean_html_text(eligibility_str)
                        lower_el = eligibility_str.lower()
                        if "undergraduate" in lower_el or "college" in lower_el or "b.tech" in lower_el:
                            target_levels.append("Undergraduate")
                        if "postgraduate" in lower_el or "master" in lower_el or "m.tech" in lower_el or "mba" in lower_el:
                            target_levels.append("Postgraduate")
                        if "school" in lower_el or "class" in lower_el:
                            target_levels.append("School")

                    # Awards and prizes
                    prizes_list = item.get("prizes") or []
                    award_amount = "Merit Award / Certificate"
                    if isinstance(prizes_list, list) and len(prizes_list) > 0:
                        first_prize = prizes_list[0]
                        if isinstance(first_prize, dict):
                            cash = first_prize.get("cash") or first_prize.get("amount") or first_prize.get("name")
                            if cash:
                                award_amount = f"₹{cash}" if str(cash).isdigit() else str(cash)
                        elif isinstance(first_prize, (str, int)):
                            award_amount = f"₹{first_prize}" if str(first_prize).isdigit() else str(first_prize)

                    # Deadline
                    end_date_raw = (
                        item.get("end_date")
                        or (item.get("regn_requirements") or {}).get("end_regn_date")
                        or item.get("filters", {}).get("end_date")
                    )
                    deadline = parse_datetime_safe(end_date_raw)

                    # Application URL
                    app_url = f"https://unstop.com/scholarships/{slug}" if slug else f"https://unstop.com/p/{ext_id}"

                    normalized_items.append({
                        "external_id": ext_id,
                        "source_platform": "unstop",
                        "title": title[:500],
                        "slug": slug[:500] if slug else None,
                        "organization_name": org_name[:300] if org_name else None,
                        "organization_logo": org_logo[:1000] if org_logo else None,
                        "banner_image": banner_img[:1000] if banner_img else None,
                        "description": clean_desc or f"{title} hosted on Unstop.",
                        "eligibility_criteria": eligibility_str or "Open to all eligible applicants on Unstop.",
                        "award_amount": award_amount[:200],
                        "award_type": "Scholarship & Recognition",
                        "currency": "INR",
                        "target_education_levels": target_levels or ["All Education Levels"],
                        "gender_eligibility": "All",
                        "region_or_country": "India",
                        "deadline": deadline,
                        "is_featured": bool(item.get("is_featured") or item.get("featured")),
                        "is_active": True,
                        "application_url": app_url[:1000],
                        "raw_data": item,
                    })
        except Exception as e:
            logger.exception(f"[ScholarshipSync] Failed to fetch Unstop scholarships: {e}")

        logger.info(f"[ScholarshipSync] Successfully parsed {len(normalized_items)} scholarships from Unstop")
        return normalized_items

    @classmethod
    def _normalize_b4s_items(cls, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize raw Buddy4Study JSON items into standardized scholarship format."""
        normalized_items: List[Dict[str, Any]] = []
        for item in data_list:
            slug = item.get("slug") or ""
            page_slug = item.get("pageSlug") or ""
            ext_id = slug or page_slug.replace("page/", "") or str(item.get("id") or item.get("bsid") or "")
            if not ext_id:
                continue

            title = item.get("scholarshipName") or "Buddy4Study Scholarship"

            multilingual_list = item.get("scholarshipMultilinguals") or []
            multi_first = multilingual_list[0] if isinstance(multilingual_list, list) and len(multilingual_list) > 0 and isinstance(multilingual_list[0], dict) else {}

            org_name = multi_first.get("title") or "Buddy4Study Partner"
            providers = item.get("scholarshipProviders") or []
            if isinstance(providers, list) and len(providers) > 0 and isinstance(providers[0], dict):
                org_name = providers[0].get("name") or providers[0].get("providerName") or org_name
            elif item.get("postedBy"):
                org_name = str(item.get("postedBy"))

            award_amount = multi_first.get("purposeAward") or "Financial Assistance"
            amount_seat = item.get("scholarshipAmountSeat") or []
            if isinstance(amount_seat, list) and len(amount_seat) > 0 and isinstance(amount_seat[0], dict):
                amt_val = amount_seat[0].get("scholarshipAmount")
                if amt_val:
                    award_amount = f"₹{amt_val:,}" if isinstance(amt_val, (int, float)) else str(amt_val)

            eligibility_text = multi_first.get("applicableFor") or ""
            target_levels: List[str] = []
            profiles = item.get("scholarshipApplicableProfiles") or []
            if isinstance(profiles, list):
                for p in profiles:
                    if isinstance(p, dict) and p.get("profileName"):
                        target_levels.append(str(p.get("profileName")))

            lower_el = (eligibility_text + " " + title).lower()
            if "undergraduate" in lower_el or "graduation" in lower_el or "college" in lower_el:
                target_levels.append("Undergraduate")
            if "postgraduate" in lower_el or "master" in lower_el:
                target_levels.append("Postgraduate")
            if "class 1" in lower_el or "class 9" in lower_el or "class 11" in lower_el or "class 12" in lower_el or "school" in lower_el:
                target_levels.append("School")
            if "diploma" in lower_el or "iti" in lower_el:
                target_levels.append("Diploma")

            target_levels = list(dict.fromkeys(target_levels)) if target_levels else ["Undergraduate", "School"]

            gender_elig = "All"
            if "girl" in lower_el or "women" in lower_el or "female" in lower_el or "kanya" in lower_el:
                gender_elig = "Female"

            clean_desc = clean_html_text(eligibility_text) or f"{title} presented by {org_name}."
            deadline_raw = item.get("deadlineDate") or item.get("onlineDeadline")
            deadline = parse_datetime_safe(deadline_raw)

            if page_slug:
                clean_page_slug = page_slug if page_slug.startswith("page/") else f"page/{page_slug}"
                app_url = f"https://www.buddy4study.com/{clean_page_slug}"
            elif slug:
                app_url = f"https://www.buddy4study.com/page/{slug}"
            else:
                app_url = f"https://www.buddy4study.com/scholarship/{ext_id}"

            logo_url = item.get("logoFid") or ""
            if logo_url and not logo_url.startswith("http"):
                logo_url = f"https://d2w7l1p59qkl0r.cloudfront.net/static/scholarship_logo/{logo_url}"

            normalized_items.append({
                "external_id": ext_id,
                "source_platform": "buddy4study",
                "title": title[:500],
                "slug": slug[:500] if slug else ext_id[:500],
                "organization_name": org_name[:300] if org_name else None,
                "organization_logo": logo_url[:1000] if logo_url else None,
                "banner_image": None,
                "description": clean_desc,
                "eligibility_criteria": clean_desc or "Students matching academic and household income guidelines.",
                "award_amount": award_amount[:200],
                "award_type": "Scholarship Grant",
                "currency": "INR",
                "target_education_levels": target_levels,
                "gender_eligibility": gender_elig,
                "region_or_country": "India",
                "deadline": deadline,
                "is_featured": True,
                "is_active": True,
                "application_url": app_url[:1000],
                "raw_data": item,
            })
        return normalized_items

    @classmethod
    async def _fetch_b4s_api_with_token(cls, token: str) -> List[Dict[str, Any]]:
        """Query the Buddy4Study REST API using a specific Bearer token."""
        headers = {
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.9",
            "authorization": f"Bearer {token}",
            "origin": "https://www.buddy4study.com",
            "referer": "https://www.buddy4study.com/",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
        }
        url = "https://api.buddy4study.com/api/v1.0/ssms/scholarship?featured=true"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data_list = resp.json()
                if isinstance(data_list, list):
                    return cls._normalize_b4s_items(data_list)
            else:
                logger.warning(f"[ScholarshipSync] B4S API returned status {resp.status_code}: {resp.text[:200]}")
        return []

    @classmethod
    async def fetch_b4s_with_playwright(cls) -> List[Dict[str, Any]]:
        """Launch headless Playwright, navigate to Buddy4Study, intercept live guest token / response,
        and fetch active scholarships."""
        captured_token: Optional[str] = None
        intercepted_items: List[Dict[str, Any]] = []

        try:
            from playwright.async_api import async_playwright
            logger.info("[ScholarshipSync] Starting Playwright headless Chromium for Buddy4Study...")

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ],
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                )
                page = await context.new_page()

                # Intercept network requests for bearer tokens
                async def handle_request(request):
                    nonlocal captured_token
                    auth = request.headers.get("authorization", "")
                    if "Bearer " in auth:
                        raw = auth.replace("Bearer ", "").strip()
                        if raw and len(raw) > 30:
                            captured_token = raw

                # Intercept network responses for scholarship data
                async def handle_response(response):
                    nonlocal intercepted_items
                    url = response.url
                    if "ssms/scholarship" in url and response.status == 200:
                        try:
                            payload = await response.json()
                            if isinstance(payload, list) and len(payload) > 0:
                                intercepted_items = payload
                        except Exception:
                            pass

                page.on("request", handle_request)
                page.on("response", handle_response)

                try:
                    await page.goto("https://www.buddy4study.com/scholarships", wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(3000)
                except Exception as nav_err:
                    logger.warning(f"[ScholarshipSync] Playwright navigation notice: {nav_err}")

                await browser.close()

            # Store the intercepted live token in Redis
            if captured_token:
                logger.info("[ScholarshipSync] Intercepted active Buddy4Study token via Playwright headless.")
                try:
                    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                    await r.set(REDIS_B4S_TOKEN_KEY, captured_token)
                    await r.close()
                except Exception as redis_err:
                    logger.warning(f"[ScholarshipSync] Failed to store token in Redis: {redis_err}")

            # If scholarship payload was intercepted directly
            if intercepted_items:
                logger.info(f"[ScholarshipSync] Successfully intercepted {len(intercepted_items)} items from Playwright session.")
                return cls._normalize_b4s_items(intercepted_items)

            # Otherwise use the captured token (or fallback) to fetch API
            active_token = captured_token or DEFAULT_B4S_TOKEN
            return await cls._fetch_b4s_api_with_token(active_token)

        except Exception as e:
            logger.warning(f"[ScholarshipSync] Playwright headless execution encountered: {e}. Falling back to direct API...")
            # Fallback to direct HTTP API
            token = DEFAULT_B4S_TOKEN
            try:
                r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                cached = await r.get(REDIS_B4S_TOKEN_KEY)
                if cached:
                    token = cached
                await r.close()
            except Exception:
                pass
            return await cls._fetch_b4s_api_with_token(token)

    @classmethod
    async def sync_all_scholarships(cls) -> Dict[str, Any]:
        """Fetch from all platforms (Unstop + Playwright Headless B4S), upsert into database, and invalidate Redis cache."""
        logger.info("[ScholarshipSync] Starting 5-hour scholarship sync job with Playwright...")

        unstop_items = await cls.fetch_unstop_scholarships()
        b4s_items = await cls.fetch_b4s_with_playwright()
        all_items = unstop_items + b4s_items

        if not all_items:
            logger.warning("[ScholarshipSync] No scholarship records retrieved from any provider.")
            return {"status": "no_data", "synced_count": 0}

        now = datetime.utcnow()
        upserted_count = 0

        async with AsyncSessionLocal() as session:
            try:
                for item in all_items:
                    stmt = insert(Scholarship).values(
                        external_id=item["external_id"],
                        source_platform=item["source_platform"],
                        title=item["title"],
                        slug=item.get("slug"),
                        organization_name=item.get("organization_name"),
                        organization_logo=item.get("organization_logo"),
                        banner_image=item.get("banner_image"),
                        description=item.get("description"),
                        eligibility_criteria=item.get("eligibility_criteria"),
                        award_amount=item.get("award_amount"),
                        award_type=item.get("award_type"),
                        currency=item.get("currency", "INR"),
                        target_education_levels=item.get("target_education_levels"),
                        gender_eligibility=item.get("gender_eligibility", "All"),
                        region_or_country=item.get("region_or_country", "India"),
                        deadline=item.get("deadline"),
                        is_featured=item.get("is_featured", False),
                        is_active=item.get("is_active", True),
                        application_url=item["application_url"],
                        raw_data=item.get("raw_data"),
                        last_synced_at=now,
                        updated_at=now,
                    )

                    update_dict = {
                        "title": item["title"],
                        "slug": item.get("slug"),
                        "organization_name": item.get("organization_name"),
                        "organization_logo": item.get("organization_logo"),
                        "banner_image": item.get("banner_image"),
                        "description": item.get("description"),
                        "eligibility_criteria": item.get("eligibility_criteria"),
                        "award_amount": item.get("award_amount"),
                        "award_type": item.get("award_type"),
                        "target_education_levels": item.get("target_education_levels"),
                        "gender_eligibility": item.get("gender_eligibility", "All"),
                        "deadline": item.get("deadline"),
                        "is_featured": item.get("is_featured", False),
                        "is_active": True,
                        "application_url": item["application_url"],
                        "raw_data": item.get("raw_data"),
                        "last_synced_at": now,
                        "updated_at": now,
                    }

                    stmt = stmt.on_conflict_do_update(
                        constraint="uq_scholarship_source_external_id",
                        set_=update_dict,
                    )
                    await session.execute(stmt)
                    upserted_count += 1

                # Auto-deactivate expired scholarships
                await session.execute(
                    update(Scholarship)
                    .where(Scholarship.deadline < now, Scholarship.is_active == True)
                    .values(is_active=False, updated_at=now)
                )

                await session.commit()
                logger.info(f"[ScholarshipSync] Successfully committed {upserted_count} scholarships to DB.")
            except Exception as e:
                await session.rollback()
                logger.exception(f"[ScholarshipSync] Database error during sync: {e}")
                raise

        # Invalidate Redis Cache
        await cls.invalidate_cache()

        return {
            "status": "success",
            "synced_count": upserted_count,
            "unstop_count": len(unstop_items),
            "b4s_count": len(b4s_items),
            "synced_at": now.isoformat(),
        }

    @staticmethod
    async def invalidate_cache():
        """Flush all scholarship cache keys in Redis."""
        try:
            redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            keys = await redis_client.keys(f"{REDIS_SCHOLARSHIP_PREFIX}:*")
            if keys:
                await redis_client.delete(*keys)
                logger.info(f"[ScholarshipSync] Flushed {len(keys)} Redis scholarship cache keys.")
            await redis_client.close()
        except Exception as e:
            logger.warning(f"[ScholarshipSync] Failed to clear Redis cache: {e}")
