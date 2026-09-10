"""Public job search, filter, pagination for external candidates."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import Select, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.jobs_portal.models.job import JobPosting, JobType


def serialize_public_job(job: JobPosting) -> dict[str, Any]:
    provider = job.provider
    jt = job.job_type.value if job.job_type else None
    return {
        "id": job.id,
        "title": job.title,
        "company": job.posted_by_name
        or (provider.company_name if provider else None)
        or "Hiring Company",
        "location": job.location,
        "salary_range": job.salary_range,
        "job_type": jt,
        "experience_required": job.experience_required,
        "industry": job.industry,
        "employment_type": job.employment_type,
        "shift": job.shift,
        "post_count": job.post_count or 0,
        "posted_at": job.created_at,
    }


def serialize_public_job_detail(job: JobPosting) -> dict[str, Any]:
    provider = job.provider
    base = serialize_public_job(job)
    base.update(
        {
            "description": job.description,
            "required_skills": job.required_skills or [],
            "perks": job.perks or [],
            "company_address": provider.company_address if provider else None,
            "company_location": provider.company_location if provider else None,
            "posted_by_name": job.posted_by_name,
        }
    )
    return base


def _apply_text_search(query: Select, q: Optional[str]) -> Select:
    if not q or not q.strip():
        return query
    term = f"%{q.strip().lower()}%"
    return query.filter(
        or_(
            func.lower(JobPosting.title).like(term),
            func.lower(JobPosting.industry).like(term),
            func.lower(JobPosting.location).like(term),
            func.lower(JobPosting.posted_by_name).like(term),
            func.lower(JobPosting.experience_required).like(term),
        )
    )


def _apply_location(query: Select, loc: Optional[str]) -> Select:
    if not loc or not loc.strip():
        return query
    return query.filter(func.lower(JobPosting.location).like(f"%{loc.strip().lower()}%"))


def _apply_experience(query: Select, exp: Optional[str]) -> Select:
    if not exp or not exp.strip():
        return query
    exp = exp.strip()
    if exp.startswith("Freshers"):
        return query.filter(
            or_(
                JobPosting.experience_required.is_(None),
                func.lower(JobPosting.experience_required).like("%fresher%"),
                func.lower(JobPosting.experience_required).like("%0%"),
                func.lower(JobPosting.experience_required).like("%entry%"),
                func.lower(JobPosting.experience_required).like("%1 year%"),
                func.lower(JobPosting.experience_required).like("%1 - 2%"),
            )
        )
    if exp == "30 Years or More":
        return query.filter(
            or_(
                func.lower(JobPosting.experience_required).like("%30%"),
                func.lower(JobPosting.experience_required).like("%25%"),
                func.lower(JobPosting.experience_required).like("%20%"),
                func.lower(JobPosting.experience_required).like("%15%"),
                func.lower(JobPosting.experience_required).like("%10+%"),
                func.lower(JobPosting.experience_required).like("%10 +%"),
                func.lower(JobPosting.experience_required).like("%senior%"),
            )
        )
    match = re.match(r"(\d+)", exp)
    if match:
        y = match.group(1)
        return query.filter(
            or_(
                func.lower(JobPosting.experience_required).like(f"%{y}%"),
                func.lower(JobPosting.experience_required).like(f"%{int(y) - 1}%"),
                JobPosting.experience_required.is_(None),
            )
        )
    return query.filter(func.lower(JobPosting.experience_required).like(f"%{exp.lower()}%"))


def _apply_date_filter(query: Select, date_filter: str) -> Select:
    if not date_filter or date_filter == "all":
        return query
    now = datetime.utcnow()
    if date_filter == "24h":
        cutoff = now - timedelta(days=1)
    elif date_filter == "3d":
        cutoff = now - timedelta(days=3)
    elif date_filter == "7d":
        cutoff = now - timedelta(days=7)
    else:
        return query
    return query.filter(JobPosting.created_at >= cutoff)


def _apply_work_modes(query: Select, modes: list[str]) -> Select:
    if not modes:
        return query
    conditions = []
    for mode in modes:
        m = mode.lower()
        if "home" in m or m == "wfh":
            conditions.append(JobPosting.job_type == JobType.wfh)
        elif "office" in m:
            conditions.append(
                or_(
                    JobPosting.job_type == JobType.in_office,
                    JobPosting.job_type == JobType.hybrid,
                )
            )
        elif "field" in m:
            conditions.append(func.lower(JobPosting.title).like("%field%"))
    if conditions:
        return query.filter(or_(*conditions))
    return query


def _apply_work_types(query: Select, types: list[str]) -> Select:
    if not types:
        return query
    conditions = []
    for t in types:
        if "part" in t.lower():
            conditions.append(JobPosting.employment_type == "part_time")
        elif "full" in t.lower():
            conditions.append(
                or_(
                    JobPosting.employment_type == "full_time",
                    JobPosting.employment_type.is_(None),
                )
            )
    if conditions:
        return query.filter(or_(*conditions))
    return query


def _apply_shifts(query: Select, shifts: list[str]) -> Select:
    if not shifts:
        return query
    conditions = []
    for s in shifts:
        if "night" in s.lower():
            conditions.append(JobPosting.shift == "night")
        elif "day" in s.lower():
            conditions.append(
                or_(JobPosting.shift == "day", JobPosting.shift.is_(None))
            )
    if conditions:
        return query.filter(or_(*conditions))
    return query


def _apply_experience_years(query: Select, exp_years: Optional[int]) -> Select:
    if exp_years is None or exp_years <= 0:
        return query
    if exp_years >= 31:
        return query.filter(
            or_(
                func.lower(JobPosting.experience_required).like("%30%"),
                func.lower(JobPosting.experience_required).like("%25%"),
                func.lower(JobPosting.experience_required).like("%20%"),
                func.lower(JobPosting.experience_required).like("%15%"),
                func.lower(JobPosting.experience_required).like("%10+%"),
                func.lower(JobPosting.experience_required).like("%senior%"),
            )
        )
    y = str(exp_years)
    return query.filter(
        or_(
            func.lower(JobPosting.experience_required).like(f"%{y}%"),
            func.lower(JobPosting.experience_required).like(f"%{exp_years - 1}%"),
            func.lower(JobPosting.experience_required).like("%fresher%"),
            JobPosting.experience_required.is_(None),
        )
    )


def _apply_salary_lakh_range(
    query: Select, salary_min: int = 0, salary_max: int = 50
) -> Select:
    if salary_min <= 0 and salary_max >= 50:
        return query
    conditions = []
    lo = max(0, salary_min)
    hi = min(50, salary_max)
    for lakh in range(lo, hi + 1):
        conditions.append(JobPosting.salary_range.ilike(f"%{lakh}%"))
        conditions.append(JobPosting.salary_range.ilike(f"%{lakh}.%"))
        if lakh < 10:
            conditions.append(JobPosting.salary_range.ilike(f"%{lakh * 10000:,}%"))
            conditions.append(JobPosting.salary_range.ilike(f"%{lakh * 10000}%"))
    if conditions:
        return query.filter(or_(*conditions))
    return query


_EDUCATION_KEYWORDS = {
    "below_10th": ["below 10", "8th", "9th"],
    "10th": ["10th", "10 th", "matric"],
    "12th": ["12th", "12 th", "intermediate", "hsc"],
    "diploma": ["diploma"],
    "graduate": ["graduate", "graduation", "bachelor", "b.a", "b.com", "b.tech", "b.e"],
    "post_graduate": ["post graduate", "postgraduate", "master", "m.a", "m.com", "mba", "m.tech"],
    "phd": ["phd", "doctorate"],
    "iti": ["iti"],
}

_ENGLISH_KEYWORDS = {
    "no_english": ["no english"],
    "basic": ["basic english", "basic"],
    "good": ["good english", "intermediate", "advanced english"],
    "fluent": ["fluent", "excellent english"],
}

_GENDER_KEYWORDS = {
    "any": ["any gender", "both male and female", "male and female"],
    "male": ["male only", "male candidate", "only male"],
    "female": ["female only", "female candidate", "only female", "women"],
}

_INDUSTRY_KEYWORDS = {
    "sales": ["sales", "business development", "bd"],
    "healthcare": ["healthcare", "hospital", "medical", "life sciences"],
    "it": ["software", "developer", "it ", "information security", "engineering"],
    "retail": ["retail", "ecommerce", "e-commerce", "counter sales"],
    "delivery": ["delivery", "driver", "logistics"],
    "bpo": ["bpo", "telecaller", "telecalling", "call center"],
    "finance": ["finance", "accounting", "accounts"],
    "hr": ["human resource", " hr", "recruitment"],
    "marketing": ["marketing", "digital marketing", "brand"],
    "manufacturing": ["manufacturing", "production"],
    "hospitality": ["hospitality", "hotel", "restaurant", "tourism"],
    "education": ["teaching", "teacher", "training", "education"],
    "construction": ["construction", "site engineer"],
    "data_science": ["data science", "analytics", "data analyst"],
    "customer_support": ["customer support", "customer service"],
    "admin": ["back office", "admin", "data entry"],
}


def _apply_keyword_filters(
    query: Select,
    *,
    education: Optional[list[str]] = None,
    english: Optional[list[str]] = None,
    gender: Optional[list[str]] = None,
    industries: Optional[list[str]] = None,
) -> Select:
    def _match_keywords(keyword_map: dict[str, list[str]], values: list[str]) -> list:
        conds = []
        for val in values:
            for kw in keyword_map.get(val, [val.replace("_", " ")]):
                conds.append(func.lower(JobPosting.description).like(f"%{kw}%"))
                conds.append(func.lower(JobPosting.title).like(f"%{kw}%"))
        return conds

    if education:
        conds = _match_keywords(_EDUCATION_KEYWORDS, education)
        if conds:
            query = query.filter(or_(*conds))
    if english:
        conds = _match_keywords(_ENGLISH_KEYWORDS, english)
        if conds:
            query = query.filter(or_(*conds))
    if gender:
        conds = _match_keywords(_GENDER_KEYWORDS, gender)
        if conds:
            query = query.filter(or_(*conds))
    if industries:
        conds = []
        for val in industries:
            for kw in _INDUSTRY_KEYWORDS.get(val, [val.replace("_", " ")]):
                conds.append(func.lower(JobPosting.industry).like(f"%{kw}%"))
                conds.append(func.lower(JobPosting.title).like(f"%{kw}%"))
                conds.append(func.lower(JobPosting.description).like(f"%{kw}%"))
        if conds:
            query = query.filter(or_(*conds))
    return query


def _job_matches_keywords(job: JobPosting, keyword_map: dict[str, list[str]], value: str) -> bool:
    text = f"{job.title or ''} {job.description or ''} {job.industry or ''}".lower()
    for kw in keyword_map.get(value, [value.replace("_", " ")]):
        if kw in text:
            return True
    return False


async def get_job_filter_facets(
    db: AsyncSession,
    *,
    q: Optional[str] = None,
    loc: Optional[str] = None,
    exp_years: Optional[int] = None,
    salary_min: int = 0,
    salary_max: int = 50,
    work_modes: Optional[list[str]] = None,
    work_types: Optional[list[str]] = None,
    work_shifts: Optional[list[str]] = None,
    education: Optional[list[str]] = None,
    english: Optional[list[str]] = None,
    gender: Optional[list[str]] = None,
    industries: Optional[list[str]] = None,
    date_filter: str = "all",
) -> dict[str, dict[str, int]]:
    base = build_public_jobs_query(
        q=q,
        loc=loc,
        exp_years=exp_years,
        salary_min=salary_min,
        salary_max=salary_max,
        work_modes=work_modes,
        work_types=work_types,
        work_shifts=work_shifts,
        education=education,
        english=english,
        gender=gender,
        industries=industries,
        date_filter=date_filter,
    )
    result = await db.execute(base.limit(3000))
    jobs = result.scalars().all()

    facets: dict[str, dict[str, int]] = {
        "work_mode": {},
        "work_type": {},
        "work_shift": {},
        "education": {},
        "english": {},
        "gender": {},
        "industry": {},
    }

    for job in jobs:
        jt = job.job_type.value if job.job_type else ""
        if jt in ("wfh",):
            facets["work_mode"]["wfh"] = facets["work_mode"].get("wfh", 0) + 1
        elif jt in ("in_office", "hybrid"):
            facets["work_mode"]["office"] = facets["work_mode"].get("office", 0) + 1
        if "field" in (job.title or "").lower():
            facets["work_mode"]["field"] = facets["work_mode"].get("field", 0) + 1

        et = job.employment_type or "full_time"
        facets["work_type"][et] = facets["work_type"].get(et, 0) + 1

        sh = job.shift or "day"
        facets["work_shift"][sh] = facets["work_shift"].get(sh, 0) + 1

        for key in _EDUCATION_KEYWORDS:
            if _job_matches_keywords(job, _EDUCATION_KEYWORDS, key):
                facets["education"][key] = facets["education"].get(key, 0) + 1
        for key in _ENGLISH_KEYWORDS:
            if _job_matches_keywords(job, _ENGLISH_KEYWORDS, key):
                facets["english"][key] = facets["english"].get(key, 0) + 1
        for key in _GENDER_KEYWORDS:
            if _job_matches_keywords(job, _GENDER_KEYWORDS, key):
                facets["gender"][key] = facets["gender"].get(key, 0) + 1
        for key in _INDUSTRY_KEYWORDS:
            if _job_matches_keywords(job, _INDUSTRY_KEYWORDS, key):
                facets["industry"][key] = facets["industry"].get(key, 0) + 1

    return facets


def _apply_min_salary(query: Select, min_salary: int) -> Select:
    if min_salary <= 0:
        return query
    # Loose match on salary_range text for monthly thresholds
    patterns = []
    for thousands in range(min_salary // 1000, min_salary // 1000 + 200, 5):
        patterns.append(JobPosting.salary_range.ilike(f"%{thousands:,}%"))
        patterns.append(JobPosting.salary_range.ilike(f"%{thousands}%"))
    for lakh in range(1, 50):
        if lakh * 100000 / 12 >= min_salary:
            patterns.append(JobPosting.salary_range.ilike(f"%{lakh}%"))
    return query.filter(or_(*patterns)) if patterns else query


def build_public_jobs_query(
    *,
    q: Optional[str] = None,
    loc: Optional[str] = None,
    exp: Optional[str] = None,
    exp_years: Optional[int] = None,
    date_filter: str = "all",
    min_salary: int = 0,
    salary_min: int = 0,
    salary_max: int = 50,
    work_modes: Optional[list[str]] = None,
    work_types: Optional[list[str]] = None,
    work_shifts: Optional[list[str]] = None,
    department: Optional[str] = None,
    education: Optional[list[str]] = None,
    english: Optional[list[str]] = None,
    gender: Optional[list[str]] = None,
    industries: Optional[list[str]] = None,
    sort: str = "relevant",
) -> Select:
    query = (
        select(JobPosting)
        .options(selectinload(JobPosting.provider))
        .filter(JobPosting.is_active == True)
    )
    query = _apply_text_search(query, q)
    query = _apply_location(query, loc)
    if exp_years is not None and exp_years > 0:
        query = _apply_experience_years(query, exp_years)
    else:
        query = _apply_experience(query, exp)
    query = _apply_date_filter(query, date_filter)
    if salary_min > 0 or salary_max < 50:
        query = _apply_salary_lakh_range(query, salary_min, salary_max)
    else:
        query = _apply_min_salary(query, min_salary)
    query = _apply_work_modes(query, work_modes or [])
    query = _apply_work_types(query, work_types or [])
    query = _apply_shifts(query, work_shifts or [])
    if department:
        term = f"%{department.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(JobPosting.industry).like(term),
                func.lower(JobPosting.title).like(term),
            )
        )
    query = _apply_keyword_filters(
        query,
        education=education,
        english=english,
        gender=gender,
        industries=industries,
    )

    if sort == "date":
        query = query.order_by(desc(JobPosting.created_at))
    else:
        query = query.order_by(desc(JobPosting.created_at))
    return query


async def search_public_jobs(
    db: AsyncSession,
    *,
    q: Optional[str] = None,
    loc: Optional[str] = None,
    exp: Optional[str] = None,
    exp_years: Optional[int] = None,
    date_filter: str = "all",
    min_salary: int = 0,
    salary_min: int = 0,
    salary_max: int = 50,
    work_modes: Optional[list[str]] = None,
    work_types: Optional[list[str]] = None,
    work_shifts: Optional[list[str]] = None,
    department: Optional[str] = None,
    education: Optional[list[str]] = None,
    english: Optional[list[str]] = None,
    gender: Optional[list[str]] = None,
    industries: Optional[list[str]] = None,
    sort: str = "relevant",
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    base = build_public_jobs_query(
        q=q,
        loc=loc,
        exp=exp,
        exp_years=exp_years,
        date_filter=date_filter,
        min_salary=min_salary,
        salary_min=salary_min,
        salary_max=salary_max,
        work_modes=work_modes,
        work_types=work_types,
        work_shifts=work_shifts,
        department=department,
        education=education,
        english=english,
        gender=gender,
        industries=industries,
        sort=sort,
    )

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(base.offset((page - 1) * page_size).limit(page_size))
    jobs = result.scalars().all()

    items = [serialize_public_job(j) for j in jobs]
    if sort == "salary":
        items.sort(
            key=lambda j: _salary_sort_key(j.get("salary_range")),
            reverse=True,
        )

    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def _salary_sort_key(salary_range: Optional[str]) -> int:
    if not salary_range:
        return 0
    nums = re.findall(r"\d+", salary_range.replace(",", ""))
    if not nums:
        return 0
    val = int(nums[0])
    if "lpa" in salary_range.lower() and val < 100:
        return val * 100000
    return val


_STREET_PART_RE = re.compile(
    r"\b("
    r"road|rd\.?|street|st\.?|lane|ln\.?|colony|nagar|sector|plot|phase|"
    r"near|opp\.?|opposite|floor|building|tower|complex|market|chowk|"
    r"avenue|marg|gali|bypass|highway|nh-?\d+"
    r")\b",
    re.IGNORECASE,
)
_PINCODE_RE = re.compile(r"\s*[-–]?\s*\b\d{6}\b")


def _location_place_parts(location: str) -> list[str]:
    """Split a free-text job location into city/state tokens (never 'City, State')."""
    text = _PINCODE_RE.sub("", (location or "").strip())
    text = re.sub(r"\s+", " ", text).strip(" ,-|/")
    if not text:
        return []

    parts = [p.strip(" ,-|/") for p in text.split(",") if p.strip(" ,-|/")]
    if not parts:
        return []

    place_parts = [p for p in parts if not _STREET_PART_RE.search(p)]
    if not place_parts:
        place_parts = [parts[-1]]

    # Prefer last two place tokens (city, state) when address has more segments
    if len(place_parts) >= 2:
        return [place_parts[-2], place_parts[-1]]
    return [place_parts[0]]


_PROTECTED_PLURALS = frozenset(
    {
        "sales",
        "business",
        "human resources",
        "operations",
        "logistics",
        "analytics",
        "graphics",
        "electronics",
        "mathematics",
        "physics",
        "economics",
        "news",
        "series",
        "status",
        "campus",
        "bonus",
        "focus",
        "hr",
        "it",
        "ui",
        "ux",
    }
)


def _singularize_word(word: str) -> str:
    w = word.lower()
    if len(w) <= 3 or w in _PROTECTED_PLURALS:
        return w
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith(("ches", "shes", "xes", "zes", "sses")) and len(w) > 5:
        return w[:-2]
    if w.endswith("es") and len(w) > 4 and w[-3] in "sxz":
        return w[:-2]
    if w.endswith("s") and not w.endswith(("ss", "us", "is", "os")):
        return w[:-1]
    return w


def _title_dedupe_key(title: str) -> str:
    """Collapse singular/plural variants so 'Computer Operator' ≈ 'Computer Operators'."""
    words = re.sub(r"\s+", " ", (title or "").strip().lower()).split()
    if not words:
        return ""
    return " ".join(_singularize_word(w) for w in words)


def _prefer_title(existing: str, candidate: str) -> str:
    """Keep the shorter / singular-leaning display form when titles collide."""
    if len(candidate) < len(existing):
        return candidate
    if len(candidate) == len(existing) and candidate.lower().endswith("s") is False:
        return candidate
    return existing


def _suggestion_matches_term(display: str, term: str, *, normalize_title: bool) -> bool:
    if not term:
        return True
    lower = display.lower()
    if term in lower:
        return True
    if not normalize_title:
        return False
    term_key = _title_dedupe_key(term)
    key = _title_dedupe_key(display)
    return bool(term_key) and bool(key) and (term_key == key or term_key in key or key in term_key)


async def get_job_suggestions(
    db: AsyncSession,
    *,
    suggest_type: str,
    q: str = "",
    limit: int = 8,
) -> list[str]:
    limit = min(max(1, limit), 20)
    query = select(JobPosting).filter(JobPosting.is_active == True)
    term = q.strip().lower()
    normalize_title = suggest_type != "location"

    col = JobPosting.location if suggest_type == "location" else JobPosting.title
    if term:
        like_term = func.lower(col).like(f"%{term}%")
        if normalize_title:
            term_key = _title_dedupe_key(term)
            if term_key and term_key != term:
                query = query.filter(or_(like_term, func.lower(col).like(f"%{term_key}%")))
            else:
                query = query.filter(like_term)
        else:
            query = query.filter(like_term)

    result = await db.execute(query.limit(500))
    jobs = result.scalars().all()

    counts: dict[str, int] = {}
    chosen: dict[str, str] = {}

    def _add(val: str) -> None:
        display = (val or "").strip()
        if not display or not _suggestion_matches_term(display, term, normalize_title=normalize_title):
            return
        key = _title_dedupe_key(display) if normalize_title else display.lower()
        if not key:
            return
        counts[key] = counts.get(key, 0) + 1
        if key in chosen:
            if normalize_title:
                chosen[key] = _prefer_title(chosen[key], display)
        else:
            chosen[key] = display

    for job in jobs:
        if suggest_type == "location":
            # Prefer city token for autocomplete (first place part)
            city = _extract_city_label(job.location or "")
            if city:
                _add(city)
        else:
            _add((job.title or "").strip())

    ranked = sorted(chosen.keys(), key=lambda k: (-counts.get(k, 0), chosen[k].lower()))
    return [chosen[k] for k in ranked[:limit]]


def _extract_city_label(location: str) -> Optional[str]:
    """Return the city token from a job location (not 'City, State')."""
    parts = _location_place_parts(location)
    if not parts:
        return None
    return parts[0]


# Only categories with count > 0 are returned. Counts use the same text search
# as clicking the chip (title/industry/location/experience) — not description
# keyword scans, which produced false positives.
_BROWSE_CATEGORIES: list[dict[str, Any]] = [
    {"key": "remote", "label": "Remote", "query": "remote"},
    {"key": "mnc", "label": "MNC", "query": "mnc"},
    {"key": "fresher", "label": "Fresher", "query": "fresher"},
    {"key": "supply_chain", "label": "Supply Chain", "query": "supply chain"},
    {"key": "software_it", "label": "Software & IT", "query": "software"},
    {"key": "marketing", "label": "Marketing", "query": "marketing"},
    {"key": "banking_finance", "label": "Banking & Finance", "query": "banking"},
    {"key": "project_mgmt", "label": "Project Mgmt", "query": "project manager"},
    {"key": "sales", "label": "Sales", "query": "sales"},
    {"key": "data_science", "label": "Data Science", "query": "data science"},
    {"key": "internship", "label": "Internship", "query": "internship"},
]


async def _count_category_jobs(db: AsyncSession, cat: dict[str, Any]) -> int:
    """Count active jobs that would appear when the category chip is clicked."""
    base = select(func.count()).select_from(JobPosting).filter(JobPosting.is_active == True)
    # Same `q` filter as public job search — chip only if click returns jobs
    result = await db.execute(_apply_text_search(base, cat["query"]))
    return int(result.scalar() or 0)


async def get_job_browse_meta(
    db: AsyncSession,
    *,
    title_limit: int = 10,
    city_limit: int = 12,
) -> dict[str, Any]:
    """Popular job titles, cities, and category chips that have live jobs."""
    title_limit = min(max(1, title_limit), 30)
    city_limit = min(max(1, city_limit), 100)

    total_q = await db.execute(
        select(func.count()).select_from(JobPosting).filter(JobPosting.is_active == True)
    )
    total_jobs = int(total_q.scalar() or 0)

    # Titles: sample recent active jobs for popular chips
    result = await db.execute(
        select(JobPosting.title)
        .filter(JobPosting.is_active == True)
        .order_by(desc(JobPosting.created_at))
        .limit(2000)
    )
    title_rows = result.all()

    title_counts: dict[str, int] = {}
    title_labels: dict[str, str] = {}

    for (title,) in title_rows:
        display = (title or "").strip()
        if display:
            key = _title_dedupe_key(display)
            if key:
                title_counts[key] = title_counts.get(key, 0) + 1
                title_labels[key] = (
                    _prefer_title(title_labels[key], display)
                    if key in title_labels
                    else display
                )

    # Distinct locations only — same city extraction as platform stats / Find Jobs
    city_counts: dict[str, int] = {}
    city_labels: dict[str, str] = {}
    loc_rows = (
        await db.execute(
            select(JobPosting.location, func.count())
            .filter(
                JobPosting.is_active == True,
                JobPosting.location.isnot(None),
                func.trim(JobPosting.location) != "",
            )
            .group_by(JobPosting.location)
        )
    ).all()
    for location, job_count in loc_rows:
        city = _extract_city_label(location or "")
        if not city:
            continue
        ckey = city.lower()
        city_counts[ckey] = city_counts.get(ckey, 0) + int(job_count or 0)
        city_labels[ckey] = city_labels.get(ckey) or city

    industries_q = await db.execute(
        select(func.count(func.distinct(func.lower(func.trim(JobPosting.industry))))).filter(
            JobPosting.is_active == True,
            JobPosting.industry.isnot(None),
            func.trim(JobPosting.industry) != "",
        )
    )
    total_industries = int(industries_q.scalar() or 0)

    categories: list[dict[str, Any]] = []
    for cat in _BROWSE_CATEGORIES:
        count = await _count_category_jobs(db, cat)
        if count <= 0:
            continue
        categories.append(
            {
                "key": cat["key"],
                "label": cat["label"],
                "query": cat["query"],
                "count": count,
            }
        )

    popular_titles = [
        {"label": title_labels[k], "count": title_counts[k]}
        for k in sorted(title_counts.keys(), key=lambda x: (-title_counts[x], title_labels[x].lower()))[
            :title_limit
        ]
    ]
    ranked_city_keys = sorted(
        city_counts.keys(), key=lambda x: (-city_counts[x], city_labels[x].lower())
    )
    cities = [
        {"label": city_labels[k], "count": city_counts[k]}
        for k in ranked_city_keys[:city_limit]
    ]

    return {
        "total_jobs": total_jobs,
        "total_cities": len(city_counts),
        "total_industries": total_industries,
        "popular_titles": popular_titles,
        "cities": cities,
        "categories": categories,
    }


async def get_similar_jobs(
    db: AsyncSession, job: JobPosting, limit: int = 6
) -> list[dict[str, Any]]:
    query = (
        select(JobPosting)
        .options(selectinload(JobPosting.provider))
        .filter(JobPosting.is_active == True, JobPosting.id != job.id)
    )
    if job.industry:
        query = query.filter(
            or_(
                JobPosting.industry == job.industry,
                func.lower(JobPosting.title).like(f"%{job.title.split()[0].lower()}%"),
            )
        )
    result = await db.execute(query.order_by(desc(JobPosting.created_at)).limit(limit))
    return [serialize_public_job(j) for j in result.scalars().all()]
