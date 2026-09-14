"""Scrape government jobs from Punjab Rozgar (pgrkam.com) and sync into job_postings.

Primary source is the public PGRKAM admin API used by https://www.pgrkam.com/govt-jobs.
HTML parsing (matching data.html card markup) is the fallback if the API is unavailable.
Each sync upserts current listings and deactivates PGRKAM jobs that disappeared.
"""

from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime
from html import unescape
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.modules.jobs_portal.models.job import JobPosting, JobType
from app.shared.models.user import CompanyType, User, UserRole

logger = logging.getLogger(__name__)

PGRKAM_LISTING_URL = "https://www.pgrkam.com/govt-jobs"
PGRKAM_API_URL = "https://pgrkamadmin.pgrkam.com/m_api/v1/index.php/govt-job/index"
SOURCE_PLATFORM = "pgrkam"
PGRKAM_PROVIDER_EMAIL = "pgrkam-sync@rojgarmela.ai"

BROWSER_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "referer": PGRKAM_LISTING_URL,
    "origin": "https://www.pgrkam.com",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
}

_WHITESPACE_RE = re.compile(r"\s+")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = unescape(str(value)).replace("\xa0", " ").replace("\r", " ")
    return _WHITESPACE_RE.sub(" ", text).strip()


def _strip_label(text: str, *labels: str) -> str:
    cleaned = _clean(text)
    for label in labels:
        if cleaned.lower().startswith(label.lower()):
            cleaned = cleaned[len(label):].lstrip(" :-")
    return cleaned.strip()


def _to_int(value: Any) -> Optional[int]:
    cleaned = _clean(value)
    if not cleaned:
        return None
    match = re.search(r"-?\d+", cleaned.replace(",", ""))
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def _card_text(element) -> str:
    return _clean(element.get_text(" ", strip=True) if element else "")


def _link_after_label(card, label: str) -> str:
    for anchor in card.select("a[href]"):
        preceding = _clean(anchor.find_previous(string=True) or "")
        parent_text = _card_text(anchor.parent)
        if label.lower() in preceding.lower() or label.lower() in parent_text.lower():
            href = (anchor.get("href") or "").strip()
            if href and href.lower() not in {"#", "javascript:void(0)"}:
                return href
    return ""


def parse_govt_jobs_html(html: str) -> List[Dict[str, Any]]:
    """Parse PGRKAM listing cards (same markup as data.html) into normalized JSON."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".first-job")
    jobs: List[Dict[str, Any]] = []

    for index, card in enumerate(cards, start=1):
        title = _strip_label(_card_text(card.select_one("h4.company-name")), "Name Of Post")
        employer = _strip_label(
            _card_text(card.select_one("h6.company-name2")),
            "Name Of Employer",
        )
        location = ""
        qualification = ""
        vacancies = None
        last_date = ""
        experience = ""
        gender = ""
        min_age = None
        max_age = None
        apply_mode = ""
        posted_by = ""
        posted_on = ""

        def _set_if_value(current: str, raw: str, *labels: str) -> str:
            value = _strip_label(raw, *labels)
            return value or current

        for node in card.select("p, li, span.date-clr, span.disabled-color, span"):
            text = _card_text(node)
            if not text:
                continue
            lower = text.lower()
            if lower.startswith("place of posting"):
                location = _set_if_value(location, text, "Place Of Posting")
            elif lower.startswith("required qualification"):
                qualification = _set_if_value(qualification, text, "Required Qualification")
            elif lower.startswith("vacancies"):
                vacancies = _to_int(_strip_label(text, "Vacancies")) or vacancies
            elif lower.startswith("last date to apply"):
                last_date = _set_if_value(last_date, text, "Last Date To Apply")
            elif lower.startswith("exp. (in years)"):
                experience = _set_if_value(experience, text, "Exp. (in years)")
            elif lower.startswith("gender"):
                gender = _set_if_value(gender, text, "Gender")
            elif lower.startswith("minimum age"):
                min_age = _to_int(_strip_label(text, "Minimum Age (in years)")) or min_age
            elif lower.startswith("maximum age"):
                max_age = _to_int(_strip_label(text, "Maximum Age (in years)")) or max_age
            elif lower.startswith("where to apply"):
                apply_mode = _set_if_value(apply_mode, text, "Where To Apply")
            elif lower.startswith("posted by"):
                posted_by = _set_if_value(posted_by, text, "Posted by")
            elif lower.startswith("posted on"):
                posted_on = _set_if_value(posted_on, text, "Posted on")

        if not title:
            continue

        jobs.append(
            {
                "external_id": f"html-{index}-{title[:40]}",
                "source_platform": SOURCE_PLATFORM,
                "source_url": PGRKAM_LISTING_URL,
                "title": title,
                "employer": employer,
                "government": "",
                "location": location,
                "qualification": qualification,
                "description": qualification,
                "vacancies": vacancies,
                "last_date_to_apply": last_date,
                "experience": experience,
                "gender": gender or "Any",
                "min_age": min_age,
                "max_age": max_age,
                "apply_url": _link_after_label(card, "Apply Here"),
                "notification_url": _link_after_label(card, "Read Notification"),
                "apply_mode": apply_mode or "Online",
                "posted_by": posted_by,
                "posted_on": posted_on,
                "status": "Published",
                "salary": None,
            }
        )

    return jobs


def normalize_api_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = _clean(item.get("job_title"))
    if not title:
        return None
    ext_id = _clean(item.get("id"))
    qualification = _clean(item.get("display_qualification") or item.get("description"))
    return {
        "external_id": ext_id or title,
        "source_platform": SOURCE_PLATFORM,
        "source_url": PGRKAM_LISTING_URL,
        "title": title,
        "employer": _clean(item.get("company_name")),
        "government": _clean(item.get("govt")),
        "location": _clean(item.get("place_of_posting") or item.get("location")),
        "qualification": qualification,
        "description": _clean(item.get("description")) or qualification,
        "vacancies": _to_int(item.get("vacancy")),
        "last_date_to_apply": _clean(item.get("last_date")),
        "experience": _clean(item.get("experience")),
        "gender": _clean(item.get("gender_preference")) or "Any",
        "min_age": _to_int(item.get("min_age")),
        "max_age": _to_int(item.get("max_age")),
        "apply_url": _clean(item.get("apply_link")),
        "notification_url": _clean(item.get("pdf_link")),
        "apply_mode": _clean(item.get("apply_mode")) or "Online",
        "posted_by": _clean(item.get("postedBy")),
        "posted_on": _clean(item.get("posted_on") or item.get("created_at")),
        "status": _clean(item.get("status")) or "Published",
        "salary": _clean(item.get("salary")) or None,
    }


def _truncate(value: Any, limit: int) -> Optional[str]:
    text = _clean(value)
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _experience_required(value: Any) -> Optional[str]:
    text = _clean(value)
    if not text or text.lower() in {"na", "n/a", "nil", "-"}:
        return "0"
    return _truncate(text, 100)


def build_job_description(item: Dict[str, Any]) -> str:
    lines: List[str] = []

    def add(label: str, raw: Any) -> None:
        text = _clean(raw)
        if text:
            lines.append(f"{label}: {text}")

    add("Name Of Employer", item.get("employer"))
    add("Government", item.get("government"))
    add("Place Of Posting", item.get("location"))
    add("Required Qualification", item.get("qualification") or item.get("description"))
    add("Experience", item.get("experience"))
    add("Vacancies", item.get("vacancies"))
    add("Last Date To Apply", item.get("last_date_to_apply"))
    add("Gender", item.get("gender"))
    if item.get("min_age") is not None or item.get("max_age") is not None:
        lines.append(f"Age: {item.get('min_age') or '-'} to {item.get('max_age') or '-'} years")
    add("Where To Apply", item.get("apply_mode"))
    add("Apply Here", item.get("apply_url"))
    add("Read Notification", item.get("notification_url"))
    add("Posted by", item.get("posted_by"))
    add("Posted on", item.get("posted_on"))
    return "\n".join(lines) or _clean(item.get("title")) or "Government job"


def map_scraped_job_to_row(item: Dict[str, Any]) -> Dict[str, Any]:
    vacancies = item.get("vacancies")
    try:
        post_count = max(int(vacancies), 0) if vacancies is not None else 0
    except (TypeError, ValueError):
        post_count = 0

    return {
        "title": _truncate(item.get("title"), 200) or "Government Job",
        "description": build_job_description(item),
        "required_skills": [],
        "experience_required": _experience_required(item.get("experience")),
        "job_type": JobType.in_office,
        "salary_range": _truncate(item.get("salary"), 100),
        "industry": _truncate(item.get("government") or "Government", 100),
        "posted_by_name": _truncate(item.get("employer") or item.get("posted_by") or "Punjab Rozgar", 200),
        "location": _truncate(item.get("location"), 200),
        "post_count": post_count,
        "ai_interview_enabled": False,
        "employment_type": _truncate(item.get("apply_mode") or "Online", 20),
        "source_metadata": item,
    }


class GovtJobSyncService:
    @staticmethod
    async def fetch_from_api() -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=BROWSER_HEADERS) as client:
            resp = await client.get(PGRKAM_API_URL)
            resp.raise_for_status()
            payload = resp.json()

        raw_items: List[Dict[str, Any]] = []
        if isinstance(payload, list):
            raw_items = [item for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            data = payload.get("data") or payload.get("jobs") or payload.get("result") or []
            if isinstance(data, list):
                raw_items = [item for item in data if isinstance(item, dict)]

        jobs = [job for item in raw_items if (job := normalize_api_item(item))]
        logger.info("[GovtJobSync] Parsed %s jobs from PGRKAM API", len(jobs))
        return jobs

    @staticmethod
    async def fetch_from_html() -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=BROWSER_HEADERS) as client:
            resp = await client.get(PGRKAM_LISTING_URL)
            resp.raise_for_status()
            jobs = parse_govt_jobs_html(resp.text)
        if jobs:
            logger.info("[GovtJobSync] Parsed %s jobs from listing HTML", len(jobs))
            return jobs

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("[GovtJobSync] Playwright not available for HTML fallback")
            return []

        logger.info("[GovtJobSync] Listing HTML was empty; rendering with Playwright")
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            page = await browser.new_page(user_agent=BROWSER_HEADERS["user-agent"])
            try:
                await page.goto(PGRKAM_LISTING_URL, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_selector(".first-job", timeout=15000)
                html = await page.content()
            finally:
                await browser.close()
        jobs = parse_govt_jobs_html(html)
        logger.info("[GovtJobSync] Parsed %s jobs from Playwright HTML", len(jobs))
        return jobs

    @classmethod
    async def scrape_govt_jobs(cls) -> Dict[str, Any]:
        source = "api"
        jobs: List[Dict[str, Any]] = []
        try:
            jobs = await cls.fetch_from_api()
        except Exception as exc:
            logger.warning("[GovtJobSync] API fetch failed: %s. Falling back to HTML.", exc)

        if not jobs:
            source = "html"
            try:
                jobs = await cls.fetch_from_html()
            except Exception as exc:
                logger.error("[GovtJobSync] HTML fallback failed: %s", exc, exc_info=True)
                source = "error"

        return {
            "status": "ok" if jobs else "no_data",
            "source": source,
            "count": len(jobs),
            "jobs": jobs,
        }

    @staticmethod
    async def get_or_create_provider(session) -> User:
        result = await session.execute(select(User).where(User.email == PGRKAM_PROVIDER_EMAIL))
        provider = result.scalar_one_or_none()
        if provider:
            return provider

        provider = User(
            email=PGRKAM_PROVIDER_EMAIL,
            first_name="Punjab",
            last_name="Rozgar",
            company_name="Punjab Rozgar (PGRKAM)",
            company_type=CompanyType.company,
            industry="Government",
            role=UserRole.provider,
            is_verified=True,
            onboarding_complete=True,
            is_first_login=False,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
        )
        session.add(provider)
        await session.flush()
        logger.info("[GovtJobSync] Created PGRKAM system provider %s", provider.id)
        return provider

    @classmethod
    async def persist_jobs(cls, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        now = datetime.utcnow()
        created = 0
        updated = 0
        deactivated = 0

        async with AsyncSessionLocal() as session:
            try:
                provider = await cls.get_or_create_provider(session)
                existing_result = await session.execute(
                    select(JobPosting).where(JobPosting.source_platform == SOURCE_PLATFORM)
                )
                existing = {job.external_id: job for job in existing_result.scalars().all() if job.external_id}
                seen_ids: set[str] = set()

                for item in jobs:
                    ext_id = _clean(item.get("external_id"))
                    if not ext_id:
                        continue
                    seen_ids.add(ext_id)
                    values = map_scraped_job_to_row(item)
                    job = existing.get(ext_id)
                    if job:
                        for key, value in values.items():
                            setattr(job, key, value)
                        job.is_active = True
                        job.updated_at = now
                        updated += 1
                    else:
                        session.add(
                            JobPosting(
                                provider_id=provider.id,
                                source_platform=SOURCE_PLATFORM,
                                external_id=ext_id,
                                is_active=True,
                                **values,
                            )
                        )
                        created += 1

                for ext_id, job in existing.items():
                    if ext_id not in seen_ids and job.is_active:
                        job.is_active = False
                        job.updated_at = now
                        deactivated += 1

                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("[GovtJobSync] Failed to persist government jobs")
                raise

        logger.info(
            "[GovtJobSync] DB sync complete created=%s updated=%s deactivated=%s",
            created,
            updated,
            deactivated,
        )
        return {
            "created": created,
            "updated": updated,
            "deactivated": deactivated,
            "synced_count": created + updated,
            "synced_at": now.isoformat(),
        }

    @classmethod
    async def scrape_and_sync(cls) -> Dict[str, Any]:
        payload = await cls.scrape_govt_jobs()
        jobs = payload.get("jobs") or []
        if payload.get("status") != "ok" or not jobs:
            logger.warning("[GovtJobSync] No government jobs to persist: %s", payload.get("status"))
            return {**payload, "created": 0, "updated": 0, "deactivated": 0, "synced_count": 0}

        db_result = await cls.persist_jobs(jobs)
        result = {**payload, **db_result}
        logger.info(
            "[GovtJobSync] Scraped %s jobs from %s and synced to job_postings: %s",
            result.get("count"),
            result.get("source"),
            {k: result.get(k) for k in ("created", "updated", "deactivated", "synced_count")},
        )
        return result
