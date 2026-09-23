"""Public universities page catalog. Card copy is managed here; counts come from colleges."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.super_admin.models.college_models import (
    College,
    CollegeApproval,
    CollegeCourse,
    CollegeSpecialization,
    UniversityCatalogCategory,
    UniversityCatalogCourse,
    UniversityPageSetting,
)
from app.modules.super_admin.services.college_importer_service import slugify

# Decision points the public compare view actually returns. The page shows this count.
REVIEW_FACTORS = (
    "Duration",
    "Total fee",
    "Semester fee",
    "Annual fee",
    "Monthly EMI",
    "Specializations",
    "UGC-DEB",
    "AICTE",
    "NAAC",
    "NIRF",
    "WES",
    "Approvals",
    "No-cost EMI",
    "Loan sanction time",
    "Lending partners",
    "Exam mode",
    "Admission process",
    "Hiring partners",
    "Highest package",
    "Average package",
)

DEFAULT_EYEBROW = "{total} Online Universities"
DEFAULT_LEAD = "UGC-approved universities,"
DEFAULT_REST = "verified by us and reviewed by learners, on {factors} factors"

# Layout matches the public universities explorer. match_course_name points at real college courses.
DEFAULT_CATEGORIES: list[dict[str, Any]] = [
    {
        "slug": "pg",
        "label": "PG Courses",
        "hint": "After Graduation",
        "courses": [
            {"title": "MBA Sorted", "subtitle": "Which MBA fits you?", "badge_text": "Right MBA", "badge_tone": "green", "badge_mode": "custom", "icon_key": "compass", "match_course_name": "MBA", "match_mode": "exact"},
            {"title": "Online MBA", "badge_tone": "amber", "badge_mode": "specializations", "icon_key": "monitor", "match_course_name": "Online MBA", "match_mode": "exact"},
            {"title": "Online Global MBA", "badge_text": "Trending", "badge_tone": "green", "badge_mode": "custom", "icon_key": "globe", "match_course_name": "Online Global MBA", "match_mode": "exact"},
            {"title": "1 Year MBA Online", "badge_text": "ROI 100%", "badge_tone": "green", "badge_mode": "custom", "icon_key": "trending", "match_course_name": "1 Year Online MBA", "match_mode": "exact"},
            {"title": "Online MCA", "badge_tone": "amber", "badge_mode": "specializations", "icon_key": "laptop", "match_course_name": "Online MCA", "match_mode": "exact"},
            {"title": "Online M.Sc", "badge_tone": "amber", "badge_mode": "specializations", "icon_key": "flask", "match_course_name": "Online M.Sc", "match_mode": "exact"},
            {"title": "MS Degree Online", "badge_text": "Global", "badge_tone": "green", "badge_mode": "custom", "icon_key": "graduation", "match_course_name": "MS Degree", "match_mode": "contains"},
            {"title": "Online MA", "badge_tone": "amber", "badge_mode": "specializations", "icon_key": "book", "match_course_name": "Online MA", "match_mode": "exact"},
            {"title": "Online M.Com", "badge_tone": "amber", "badge_mode": "specializations", "icon_key": "calculator", "match_course_name": "Online M.Com", "match_mode": "exact"},
            {"title": "Dual MBA Online", "badge_tone": "amber", "badge_mode": "specializations", "icon_key": "layers", "match_course_name": "Online MBA Dual", "match_mode": "exact"},
            {"title": "Online MBA after Diploma", "badge_text": "NEW", "badge_tone": "green", "badge_mode": "custom", "icon_key": "sparkles", "match_course_name": "MBA after Diploma", "match_mode": "contains"},
            {"title": "Online Master of Education (M.Ed)", "badge_tone": "amber", "badge_mode": "specializations", "icon_key": "school", "match_course_name": "M.Ed", "match_mode": "contains"},
            {"title": "Online Global MCA", "badge_text": "2 Years", "badge_tone": "amber", "badge_mode": "duration", "icon_key": "cpu", "match_course_name": "Global MCA", "match_mode": "contains"},
            {"title": "Online Master of Social Work", "badge_text": "2 Years", "badge_tone": "amber", "badge_mode": "duration", "icon_key": "heart", "match_course_name": "Online Master of Social Work", "match_mode": "exact"},
            {"title": "Online MBA & Doctorate", "badge_text": "Dr Title", "badge_tone": "green", "badge_mode": "custom", "icon_key": "award", "match_course_name": "MBA & DBA", "match_mode": "contains"},
            {"title": "Online M.Ed & Ed.D", "badge_text": "Edu Leader", "badge_tone": "green", "badge_mode": "custom", "icon_key": "users", "match_course_name": "M.Ed & Ed.D", "match_mode": "contains"},
        ],
    },
    {
        "slug": "executive",
        "label": "Executive Education",
        "hint": "Working Professionals & CXOs",
        "courses": [
            {"title": "Executive MBA", "subtitle": "Lead without leaving work", "badge_text": "For CXOs", "badge_tone": "green", "badge_mode": "custom", "icon_key": "briefcase", "match_course_name": "Executive MBA", "match_mode": "exact"},
            {"title": "PGDM for Working Pros", "badge_text": "1 Year", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "linechart", "match_course_name": "PGDM", "match_mode": "exact"},
            {"title": "Leadership Certificate", "badge_text": "Leadership", "badge_tone": "green", "badge_mode": "custom", "icon_key": "users", "match_course_name": "Leadership", "match_mode": "contains"},
            {"title": "Finance for Managers", "badge_text": "Finance", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "calculator", "match_course_name": "Finance", "match_mode": "exact"},
            {"title": "Digital Transformation", "badge_text": "Trending", "badge_tone": "green", "badge_mode": "custom", "icon_key": "rocket", "match_course_name": "Digital Transformation", "match_mode": "contains"},
            {"title": "People & Culture Program", "badge_text": "HR Leaders", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "heart", "match_course_name": "HR", "match_mode": "contains"},
        ],
    },
    {
        "slug": "doctorate",
        "label": "Doctorate/Ph.D.",
        "hint": "After UG + Work Experience",
        "courses": [
            {"title": "Ph.D. in Management", "badge_text": "Dr Title", "badge_tone": "green", "badge_mode": "custom", "icon_key": "award", "match_course_name": "PhD", "match_mode": "exact"},
            {"title": "Online DBA", "subtitle": "Research while you work", "badge_text": "For Leaders", "badge_tone": "green", "badge_mode": "custom", "icon_key": "briefcase", "match_course_name": "DBA", "match_mode": "exact"},
            {"title": "Ph.D. in Computer Science", "badge_text": "Tech", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "cpu", "match_course_name": "PhD Program", "match_mode": "exact"},
            {"title": "Doctor of Education", "badge_text": "Education", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "school", "match_course_name": "Ed.D", "match_mode": "contains"},
            {"title": "Ph.D. after MBA", "badge_text": "After MBA", "badge_tone": "green", "badge_mode": "custom", "icon_key": "graduation", "match_course_name": "Executive PhD", "match_mode": "contains"},
        ],
    },
    {
        "slug": "genai",
        "label": "Gen AI / Agentic AI",
        "hint": "Future Proof Career",
        "courses": [
            {"title": "Gen AI for Managers", "badge_text": "NEW", "badge_tone": "green", "badge_mode": "custom", "icon_key": "brain", "match_course_name": "Generative AI", "match_mode": "contains"},
            {"title": "Agentic AI Certificate", "badge_text": "Trending", "badge_tone": "green", "badge_mode": "custom", "icon_key": "sparkles", "match_course_name": "Agentic AI", "match_mode": "contains"},
            {"title": "Prompt Engineering", "badge_text": "8 Weeks", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "languages", "match_course_name": "Prompt Engineering", "match_mode": "contains"},
            {"title": "M.Sc in AI & ML", "badge_text": "PG", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "flask", "match_course_name": "Machine Learning", "match_mode": "contains"},
            {"title": "Applied AI PG Diploma", "badge_text": "Hands-on", "badge_tone": "green", "badge_mode": "custom", "icon_key": "cpu", "match_course_name": "Applied AI", "match_mode": "contains"},
        ],
    },
    {
        "slug": "ug",
        "label": "UG Courses",
        "hint": "After 12th",
        "courses": [
            {"title": "Online BBA", "badge_text": "Popular", "badge_tone": "green", "badge_mode": "custom", "icon_key": "briefcase", "match_course_name": "Online BBA", "match_mode": "exact"},
            {"title": "Online BCA", "badge_text": "Tech", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "laptop", "match_course_name": "Online BCA", "match_mode": "exact"},
            {"title": "Online B.Com", "badge_text": "Commerce", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "calculator", "match_course_name": "Online B.Com", "match_mode": "exact"},
            {"title": "Online BA", "badge_tone": "amber", "badge_mode": "specializations", "icon_key": "book", "match_course_name": "Online BA", "match_mode": "exact"},
            {"title": "Online B.Sc", "badge_text": "Science", "badge_tone": "green", "badge_mode": "custom", "icon_key": "flask", "match_course_name": "Online B.Sc", "match_mode": "exact"},
        ],
    },
    {
        "slug": "engineering",
        "label": "Engineering",
        "hint": "Flexi Timing",
        "courses": [
            {"title": "B.Tech for Working Professionals", "badge_text": "Working Pros", "badge_tone": "green", "badge_mode": "custom", "icon_key": "cpu", "match_course_name": "Working Professional", "match_mode": "contains"},
            {"title": "M.Tech Online", "badge_text": "PG", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "laptop", "match_course_name": "M.Tech", "match_mode": "contains"},
            {"title": "Diploma in Engineering", "badge_text": "After 10th", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "layers", "match_course_name": "Diploma", "match_mode": "contains"},
            {"title": "CSE Specialization", "badge_text": "Trending", "badge_tone": "green", "badge_mode": "custom", "icon_key": "monitor", "match_course_name": "Computer Science", "match_mode": "contains"},
        ],
    },
    {
        "slug": "abroad",
        "label": "Study Abroad",
        "hint": "Pathway / Hybrid Mode",
        "courses": [
            {"title": "Pathway MBA", "subtitle": "Start in India, finish abroad", "badge_text": "Pathway", "badge_tone": "green", "badge_mode": "custom", "icon_key": "plane", "match_course_name": "Pathway", "match_mode": "contains"},
            {"title": "MS Abroad", "badge_text": "Global", "badge_tone": "green", "badge_mode": "custom", "icon_key": "globe", "match_course_name": "MS Abroad", "match_mode": "contains"},
            {"title": "Hybrid Undergraduate", "badge_text": "Hybrid", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "graduation", "match_course_name": "Hybrid", "match_mode": "contains"},
            {"title": "UK & Europe Pathways", "badge_text": "1+1", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "compass", "match_course_name": "Study In", "match_mode": "contains"},
        ],
    },
    {
        "slug": "skilling",
        "label": "Skilling & Certificate",
        "hint": "After 10th & 12th",
        "courses": [
            {"title": "Data Analytics Certificate", "badge_text": "Job Ready", "badge_tone": "green", "badge_mode": "custom", "icon_key": "linechart", "match_course_name": "Data Analytics", "match_mode": "contains"},
            {"title": "Digital Marketing", "badge_text": "8 Weeks", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "rocket", "match_course_name": "Digital Marketing", "match_mode": "contains"},
            {"title": "Full Stack Development", "badge_text": "Trending", "badge_tone": "green", "badge_mode": "custom", "icon_key": "laptop", "match_course_name": "Full Stack", "match_mode": "contains"},
            {"title": "Tally & Accounts", "badge_text": "Commerce", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "calculator", "match_course_name": "Accounting", "match_mode": "contains"},
            {"title": "Spoken English", "badge_text": "Communication", "badge_tone": "amber", "badge_mode": "custom", "icon_key": "languages", "match_course_name": "Spoken English", "match_mode": "contains"},
            {"title": "Healthcare Assistant", "badge_text": "Healthcare", "badge_tone": "green", "badge_mode": "custom", "icon_key": "stethoscope", "match_course_name": "Healthcare", "match_mode": "contains"},
        ],
    },
]


def _fill(template: str, **values: Any) -> str:
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        return template


def _matches(course_name: str, needle: str, mode: str) -> bool:
    left = (course_name or "").strip().lower()
    right = (needle or "").strip().lower()
    if not left or not right:
        return False
    if mode == "contains":
        return right in left
    return left == right


async def _course_index(db: AsyncSession) -> dict[str, Any]:
    course_rows = (
        await db.execute(
            select(CollegeCourse.course_name, CollegeCourse.college_id, CollegeCourse.duration).where(
                CollegeCourse.course_name.is_not(None)
            )
        )
    ).all()
    spec_rows = (
        await db.execute(
            select(CollegeSpecialization.course_name, CollegeSpecialization.specialization_name).where(
                CollegeSpecialization.specialization_name.is_not(None)
            )
        )
    ).all()
    return {"courses": course_rows, "specs": spec_rows}


def _stats_for_card(card: UniversityCatalogCourse, index: dict[str, Any]) -> dict[str, Any]:
    matched_names: set[str] = set()
    college_ids: set[str] = set()
    durations: list[str] = []
    name_colleges: dict[str, set[str]] = defaultdict(set)

    for course_name, college_id, duration in index["courses"]:
        if not _matches(course_name, card.match_course_name, card.match_mode or "exact"):
            continue
        matched_names.add(course_name)
        if college_id:
            college_ids.add(college_id)
            name_colleges[course_name].add(college_id)
        if duration and str(duration).strip():
            durations.append(str(duration).strip())

    specs: set[str] = set()
    lowered = {name.lower() for name in matched_names}
    for course_name, spec_name in index["specs"]:
        if course_name and course_name.lower() in lowered and spec_name:
            specs.add(spec_name.strip())

    compare_course_name = card.match_course_name
    if name_colleges:
        compare_course_name = max(name_colleges.items(), key=lambda item: len(item[1]))[0]

    spec_count = len(specs)
    duration_label = Counter(durations).most_common(1)[0][0] if durations else None
    if card.badge_mode == "specializations" and spec_count > 0:
        badge = f"{spec_count}+ Specializations" if spec_count > 1 else "1 Specialization"
    elif card.badge_mode == "duration" and duration_label:
        badge = duration_label
    else:
        badge = (card.badge_text or "").strip()

    return {
        "colleges_count": len(college_ids),
        "specializations_count": spec_count,
        "compare_course_name": compare_course_name,
        "badge": badge,
    }


def _card_out(card: UniversityCatalogCourse, index: dict[str, Any], *, admin: bool) -> dict[str, Any]:
    stats = _stats_for_card(card, index)
    payload = {
        "id": card.id,
        "title": card.title,
        "subtitle": card.subtitle,
        "badge": stats["badge"],
        "badge_tone": card.badge_tone or "amber",
        "icon_key": card.icon_key or "graduation",
        "colleges_count": stats["colleges_count"],
        "specializations_count": stats["specializations_count"],
        "compare_course_name": stats["compare_course_name"],
    }
    if admin:
        payload.update(
            {
                "category_id": card.category_id,
                "badge_text": card.badge_text,
                "badge_mode": card.badge_mode,
                "match_course_name": card.match_course_name,
                "match_mode": card.match_mode,
                "sort_order": card.sort_order,
                "is_active": card.is_active,
            }
        )
    return payload


async def _get_or_create_settings(db: AsyncSession) -> UniversityPageSetting:
    row = (await db.execute(select(UniversityPageSetting).limit(1))).scalar_one_or_none()
    if row:
        return row
    row = UniversityPageSetting(
        eyebrow_template=DEFAULT_EYEBROW,
        lead_template=DEFAULT_LEAD,
        rest_template=DEFAULT_REST,
        catalog_seeded=False,
    )
    db.add(row)
    await db.flush()
    return row


async def ensure_university_catalog(db: AsyncSession) -> UniversityPageSetting:
    settings = await _get_or_create_settings(db)
    if settings.catalog_seeded:
        return settings
    existing = (await db.execute(select(func.count()).select_from(UniversityCatalogCategory))).scalar() or 0
    if existing == 0:
        for cat_index, cat in enumerate(DEFAULT_CATEGORIES):
            category = UniversityCatalogCategory(
                slug=cat["slug"],
                label=cat["label"],
                hint=cat["hint"],
                sort_order=(cat_index + 1) * 10,
                is_active=True,
            )
            db.add(category)
            await db.flush()
            for course_index, course in enumerate(cat["courses"]):
                db.add(
                    UniversityCatalogCourse(
                        category_id=category.id,
                        title=course["title"],
                        subtitle=course.get("subtitle"),
                        badge_text=course.get("badge_text"),
                        badge_tone=course.get("badge_tone") or "amber",
                        badge_mode=course.get("badge_mode") or "custom",
                        icon_key=course.get("icon_key") or "graduation",
                        match_course_name=course["match_course_name"],
                        match_mode=course.get("match_mode") or "exact",
                        sort_order=(course_index + 1) * 10,
                        is_active=True,
                    )
                )
    settings.catalog_seeded = True
    await db.commit()
    return settings


async def _university_headline(db: AsyncSession, settings: UniversityPageSetting) -> dict[str, Any]:
    total = (
        await db.execute(select(func.count()).select_from(College).where(College.is_active.is_(True)))
    ).scalar() or 0
    reviews = (
        await db.execute(select(func.coalesce(func.sum(College.total_reviews), 0)).where(College.is_active.is_(True)))
    ).scalar() or 0
    ugc = (
        await db.execute(
            select(func.count())
            .select_from(College)
            .outerjoin(CollegeApproval, CollegeApproval.college_id == College.id)
            .where(
                College.is_active.is_(True),
                or_(
                    College.approvals_summary.ilike("%UGC%"),
                    and_(CollegeApproval.ugc_deb.is_not(None), CollegeApproval.ugc_deb != ""),
                ),
            )
        )
    ).scalar() or 0
    factors = len(REVIEW_FACTORS)
    values = {"total": int(total), "ugc": int(ugc), "reviews": int(reviews), "factors": factors}
    colleges = (
        await db.execute(
            select(College)
            .where(College.is_active.is_(True))
            .order_by(College.cv_rating.desc(), College.total_courses.desc(), College.name)
            .limit(18)
        )
    ).scalars().all()
    return {
        "total": int(total),
        "ugc_approved": int(ugc),
        "learner_reviews": int(reviews),
        "review_factors": factors,
        "eyebrow": _fill(settings.eyebrow_template or DEFAULT_EYEBROW, **values),
        "lead": _fill(settings.lead_template or DEFAULT_LEAD, **values),
        "rest": _fill(settings.rest_template or DEFAULT_REST, **values),
        "items": [
            {
                "id": college.id,
                "name": college.name,
                "slug": college.slug,
                "logo_image": college.logo_image,
                "city": college.city,
                "state": college.state,
                "country": college.country,
                "full_address": college.full_address,
                "total_courses": college.total_courses or 0,
            }
            for college in colleges
        ],
    }


async def build_public_explore(db: AsyncSession) -> dict[str, Any]:
    settings = await ensure_university_catalog(db)
    categories = (
        await db.execute(
            select(UniversityCatalogCategory)
            .where(UniversityCatalogCategory.is_active.is_(True))
            .order_by(UniversityCatalogCategory.sort_order, UniversityCatalogCategory.label)
            .options(selectinload(UniversityCatalogCategory.courses))
        )
    ).scalars().all()
    index = await _course_index(db)
    payload = []
    for category in categories:
        courses = [c for c in category.courses if c.is_active]
        courses.sort(key=lambda c: (c.sort_order, c.title.lower()))
        payload.append(
            {
                "id": category.id,
                "slug": category.slug,
                "label": category.label,
                "hint": category.hint,
                "courses": [_card_out(c, index, admin=False) for c in courses],
            }
        )
    return {
        "categories": payload,
        "universities": await _university_headline(db, settings),
        "settings": {
            "eyebrow_template": settings.eyebrow_template,
            "lead_template": settings.lead_template,
            "rest_template": settings.rest_template,
        },
    }


async def build_admin_catalog(db: AsyncSession) -> dict[str, Any]:
    settings = await ensure_university_catalog(db)
    categories = (
        await db.execute(
            select(UniversityCatalogCategory)
            .order_by(UniversityCatalogCategory.sort_order, UniversityCatalogCategory.label)
            .options(selectinload(UniversityCatalogCategory.courses))
        )
    ).scalars().all()
    index = await _course_index(db)
    payload = []
    for category in categories:
        courses = list(category.courses)
        courses.sort(key=lambda c: (c.sort_order, c.title.lower()))
        payload.append(
            {
                "id": category.id,
                "slug": category.slug,
                "label": category.label,
                "hint": category.hint,
                "sort_order": category.sort_order,
                "is_active": category.is_active,
                "courses": [_card_out(c, index, admin=True) for c in courses],
            }
        )
    headline = await _university_headline(db, settings)
    return {
        "categories": payload,
        "settings": {
            "eyebrow_template": settings.eyebrow_template,
            "lead_template": settings.lead_template,
            "rest_template": settings.rest_template,
        },
        "preview": {
            "eyebrow": headline["eyebrow"],
            "lead": headline["lead"],
            "rest": headline["rest"],
            "total": headline["total"],
            "ugc_approved": headline["ugc_approved"],
            "learner_reviews": headline["learner_reviews"],
            "review_factors": headline["review_factors"],
        },
    }


async def update_page_settings(db: AsyncSession, payload: dict[str, str]) -> dict[str, Any]:
    settings = await ensure_university_catalog(db)
    for key in ("eyebrow_template", "lead_template", "rest_template"):
        value = (payload.get(key) or "").strip()
        if not value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{key} is required")
        setattr(settings, key, value)
    await db.commit()
    return await build_admin_catalog(db)


async def _unique_slug(db: AsyncSession, label: str, current_id: Optional[str] = None) -> str:
    base = slugify(label) or "category"
    slug = base
    n = 2
    while True:
        existing = (
            await db.execute(select(UniversityCatalogCategory).where(UniversityCatalogCategory.slug == slug))
        ).scalar_one_or_none()
        if not existing or existing.id == current_id:
            return slug
        slug = f"{base}-{n}"
        n += 1


async def create_category(db: AsyncSession, data: dict[str, Any]) -> dict[str, Any]:
    await ensure_university_catalog(db)
    label = (data.get("label") or "").strip()
    if not label:
        raise HTTPException(status_code=400, detail="Category name is required")
    category = UniversityCatalogCategory(
        slug=await _unique_slug(db, label),
        label=label,
        hint=(data.get("hint") or "").strip(),
        sort_order=int(data.get("sort_order") or 0),
        is_active=bool(data.get("is_active", True)),
    )
    db.add(category)
    await db.commit()
    return await build_admin_catalog(db)


async def update_category(db: AsyncSession, category_id: str, data: dict[str, Any]) -> dict[str, Any]:
    category = await db.get(UniversityCatalogCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if "label" in data:
        label = (data.get("label") or "").strip()
        if not label:
            raise HTTPException(status_code=400, detail="Category name is required")
        category.label = label
        category.slug = await _unique_slug(db, label, category.id)
    if "hint" in data:
        category.hint = (data.get("hint") or "").strip()
    if "sort_order" in data and data["sort_order"] is not None:
        category.sort_order = int(data["sort_order"])
    if "is_active" in data and data["is_active"] is not None:
        category.is_active = bool(data["is_active"])
    await db.commit()
    return await build_admin_catalog(db)


async def delete_category(db: AsyncSession, category_id: str) -> dict[str, Any]:
    category = await db.get(UniversityCatalogCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(category)
    await db.commit()
    return await build_admin_catalog(db)


def _clean_course(data: dict[str, Any]) -> dict[str, Any]:
    title = (data.get("title") or "").strip()
    match_name = (data.get("match_course_name") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Course title is required")
    if not match_name:
        raise HTTPException(status_code=400, detail="Match course name is required")
    badge_mode = data.get("badge_mode") or "custom"
    if badge_mode not in {"custom", "specializations", "duration"}:
        raise HTTPException(status_code=400, detail="Badge mode is invalid")
    match_mode = data.get("match_mode") or "exact"
    if match_mode not in {"exact", "contains"}:
        raise HTTPException(status_code=400, detail="Match mode is invalid")
    tone = data.get("badge_tone") or "amber"
    if tone not in {"green", "amber"}:
        raise HTTPException(status_code=400, detail="Badge tone is invalid")
    badge_text = (data.get("badge_text") or "").strip() or None
    if badge_mode == "custom" and not badge_text:
        raise HTTPException(status_code=400, detail="Badge text is required")
    return {
        "title": title,
        "subtitle": (data.get("subtitle") or "").strip() or None,
        "badge_text": badge_text,
        "badge_tone": tone,
        "badge_mode": badge_mode,
        "icon_key": (data.get("icon_key") or "graduation").strip() or "graduation",
        "match_course_name": match_name,
        "match_mode": match_mode,
        "sort_order": int(data.get("sort_order") or 0),
        "is_active": bool(data.get("is_active", True)),
        "category_id": data.get("category_id"),
    }


async def create_catalog_course(db: AsyncSession, data: dict[str, Any]) -> dict[str, Any]:
    await ensure_university_catalog(db)
    cleaned = _clean_course(data)
    category = await db.get(UniversityCatalogCategory, cleaned["category_id"])
    if not category:
        raise HTTPException(status_code=400, detail="Category is required")
    db.add(UniversityCatalogCourse(**cleaned))
    await db.commit()
    return await build_admin_catalog(db)


async def update_catalog_course(db: AsyncSession, course_id: str, data: dict[str, Any]) -> dict[str, Any]:
    course = await db.get(UniversityCatalogCourse, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course card not found")
    merged = {
        "title": data.get("title", course.title),
        "subtitle": data.get("subtitle", course.subtitle),
        "badge_text": data.get("badge_text", course.badge_text),
        "badge_tone": data.get("badge_tone", course.badge_tone),
        "badge_mode": data.get("badge_mode", course.badge_mode),
        "icon_key": data.get("icon_key", course.icon_key),
        "match_course_name": data.get("match_course_name", course.match_course_name),
        "match_mode": data.get("match_mode", course.match_mode),
        "sort_order": data.get("sort_order", course.sort_order),
        "is_active": course.is_active if data.get("is_active") is None else data.get("is_active"),
        "category_id": data.get("category_id", course.category_id),
    }
    cleaned = _clean_course(merged)
    category = await db.get(UniversityCatalogCategory, cleaned["category_id"])
    if not category:
        raise HTTPException(status_code=400, detail="Category is required")
    for key, value in cleaned.items():
        setattr(course, key, value)
    await db.commit()
    return await build_admin_catalog(db)


async def delete_catalog_course(db: AsyncSession, course_id: str) -> dict[str, Any]:
    course = await db.get(UniversityCatalogCourse, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course card not found")
    await db.delete(course)
    await db.commit()
    return await build_admin_catalog(db)
