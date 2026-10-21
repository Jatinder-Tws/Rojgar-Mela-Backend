import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_upload_dir
from app.modules.jobs_portal.services.career_roadmap_seed import CATALOG_ROADMAPS
from app.shared.models.user import User
from app.modules.jobs_portal.models.career_roadmap import CareerRoadmap
from app.modules.jobs_portal.models.roadmap import (
    Roadmap,
    Milestone,
    Resource,
    DifficultyLevel,
    ResourceType,
    MilestoneStatus,
)
from app.modules.jobs_portal.schemas.career_roadmap import (
    CareerInsightsOut,
    CareerRoadmapCreate,
    CareerRoadmapListItem,
    CareerRoadmapOut,
    CareerRoadmapUpdate,
    RoadmapFaqOut,
    RoadmapImportItemResult,
    RoadmapImportResponse,
    RoadmapLessonOut,
    RoadmapResourceIn,
    RoadmapResourceOut,
    RoadmapStepIn,
    RoadmapStepOut,
    RoadmapSubStepIn,
    RoadmapSubStepOut,
)

_ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
}

HERO_IMAGE_MAX_BYTES = 2 * 1024 * 1024

SEED_ROADMAPS: list[dict] = [
    *CATALOG_ROADMAPS,
    {
        "title": "DevOps & Cloud Engineer",
        "slug": "devops-cloud-engineer",
        "category": "Cloud & DevOps",
        "level": "Intermediate",
        "industries": ["IT", "Software"],
        "short_description": "From Linux and Docker to Kubernetes, Terraform, and multi-cloud CI/CD.",
        "long_description": (
            "DevOps engineers bridge software development and operations. This roadmap guides you "
            "from OS fundamentals to cloud infrastructure automation and GitOps."
        ),
        "skill_tags": ["Linux", "Docker", "Kubernetes", "Terraform", "CI/CD", "AWS"],
        "duration_months": "6 months",
        "salary_lpa": "₹16L",
        "growth_percent": "High",
        "openings_count": "4200+",
        "is_published": True,
        "is_featured": True,
        "is_trending": False,
        "sort_order": 2,
        "steps": [
            {"title": "Linux, Shell & Networking", "content": "OS internals, bash, SSH and DNS basics.", "lessons_count": 6, "projects_count": 1, "quizzes_count": 2, "lessons": []},
            {"title": "Git & Docker", "content": "Version control and containerization.", "lessons_count": 6, "projects_count": 1, "quizzes_count": 2, "lessons": []},
            {"title": "CI/CD Pipelines", "content": "Jenkins, GitHub Actions and quality gates.", "lessons_count": 5, "projects_count": 1, "quizzes_count": 1, "lessons": []},
            {"title": "Kubernetes & Terraform", "content": "Orchestration and infrastructure as code.", "lessons_count": 8, "projects_count": 2, "quizzes_count": 2, "lessons": []},
        ],
    },
    {
        "title": "AI, ML & Data Scientist",
        "slug": "ai-data-scientist",
        "category": "AI & Data",
        "level": "Intermediate",
        "industries": ["IT", "Fintech", "Startup"],
        "short_description": "Python, statistics, machine learning, deep learning and generative AI.",
        "long_description": "Build a data science career from Python and SQL through ML models and LLM applications.",
        "skill_tags": ["Python", "SQL", "Machine Learning", "Pandas", "GenAI"],
        "duration_months": "7 months",
        "salary_lpa": "₹14L",
        "growth_percent": "Very High",
        "openings_count": "3100+",
        "is_published": True,
        "is_featured": True,
        "is_trending": True,
        "sort_order": 3,
        "steps": [
            {"title": "Python & SQL", "content": "Data analysis foundations.", "lessons_count": 8, "projects_count": 1, "quizzes_count": 2, "lessons": []},
            {"title": "EDA & BI", "content": "Explore data and present insights.", "lessons_count": 5, "projects_count": 1, "quizzes_count": 1, "lessons": []},
            {"title": "Machine Learning", "content": "Classic ML algorithms and evaluation.", "lessons_count": 8, "projects_count": 2, "quizzes_count": 2, "lessons": []},
            {"title": "Generative AI", "content": "LLMs, LangChain and RAG systems.", "lessons_count": 6, "projects_count": 1, "quizzes_count": 1, "lessons": []},
        ],
    },
    {
        "title": "Cybersecurity Analyst",
        "slug": "cybersecurity-analyst",
        "category": "Cybersecurity",
        "level": "Beginner",
        "industries": ["IT", "Fintech"],
        "short_description": "Network security, ethical hacking, SIEM and incident response.",
        "long_description": "Prepare for SOC analyst roles with networking, web security, and incident response practice.",
        "skill_tags": ["Networking", "Linux", "OWASP", "SIEM", "Splunk"],
        "duration_months": "5 months",
        "salary_lpa": "₹11L",
        "growth_percent": "High",
        "openings_count": "2200+",
        "is_published": True,
        "is_featured": False,
        "is_trending": False,
        "sort_order": 4,
        "steps": [
            {"title": "Networking & Linux Security", "content": "Foundations of secure systems.", "lessons_count": 6, "projects_count": 1, "quizzes_count": 2, "lessons": []},
            {"title": "Web Security & OWASP", "content": "Find and fix common web vulnerabilities.", "lessons_count": 6, "projects_count": 1, "quizzes_count": 2, "lessons": []},
            {"title": "SOC, SIEM & IR", "content": "Monitor, detect and respond to incidents.", "lessons_count": 6, "projects_count": 1, "quizzes_count": 1, "lessons": []},
        ],
    },
    {
        "title": "UI/UX Product Designer",
        "slug": "ui-ux-product-designer",
        "category": "Design & Product",
        "level": "Beginner",
        "industries": ["Software", "Startup", "E-commerce"],
        "short_description": "User research, wireframing, Figma design systems and interactive prototypes.",
        "long_description": "Learn visual design, research, and Figma workflows used by product teams.",
        "skill_tags": ["Figma", "User Research", "Wireframing", "Prototyping"],
        "duration_months": "4 months",
        "salary_lpa": "₹9L",
        "growth_percent": "Stable",
        "openings_count": "1800+",
        "is_published": True,
        "is_featured": False,
        "is_trending": False,
        "sort_order": 5,
        "steps": [
            {"title": "Design Principles", "content": "Typography, color and visual hierarchy.", "lessons_count": 5, "projects_count": 1, "quizzes_count": 1, "lessons": []},
            {"title": "Research & Wireframes", "content": "User journeys and low-fidelity flows.", "lessons_count": 5, "projects_count": 1, "quizzes_count": 1, "lessons": []},
            {"title": "Figma & Prototyping", "content": "Design systems and high-fidelity prototypes.", "lessons_count": 6, "projects_count": 1, "quizzes_count": 1, "lessons": []},
        ],
    },
]


def slugify(text: str) -> str:
    text = (text or "").lower().strip().lstrip("/")
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-") or "roadmap"


def _normalize_steps(steps: list[RoadmapStepIn] | list[dict] | None) -> list[dict]:
    normalized = []
    for step in steps or []:
        data = step.model_dump() if isinstance(step, RoadmapStepIn) else dict(step)
        lessons = []
        for lesson in data.get("lessons") or []:
            lesson_data = lesson if isinstance(lesson, dict) else lesson.model_dump()
            title = str(lesson_data.get("title") or "").strip()
            if not title:
                continue
            lessons.append({"id": lesson_data.get("id") or str(uuid.uuid4()), "title": title})

        sub_steps = []
        for sub in data.get("sub_steps") or []:
            sub_data = sub.model_dump() if isinstance(sub, RoadmapSubStepIn) else dict(sub)
            sub_title = str(sub_data.get("title") or "").strip()
            sub_subtitle = str(sub_data.get("subtitle") or "").strip()
            sub_tags = _as_list(sub_data.get("skill_tags"))
            sub_resources = _normalize_resources(sub_data.get("resources"))
            if not (sub_title or sub_subtitle or sub_tags or sub_resources):
                continue
            sub_steps.append(
                {
                    "id": sub_data.get("id") or str(uuid.uuid4()),
                    "title": sub_title,
                    "subtitle": sub_subtitle,
                    "duration": (str(sub_data.get("duration") or "").strip() or None),
                    "level": (str(sub_data.get("level") or "").strip() or None),
                    "skill_tags": sub_tags,
                    "resources": sub_resources,
                }
            )

        lessons_count = int(data.get("lessons_count") or 0)
        duration = str(data.get("duration") or "").strip() or None
        normalized.append(
            {
                "id": data.get("id") or str(uuid.uuid4()),
                "title": str(data.get("title") or "").strip(),
                "content": str(data.get("content") or "").strip(),
                "duration": duration,
                "lessons_count": max(lessons_count, len(lessons)),
                "projects_count": int(data.get("projects_count") or 0),
                "quizzes_count": int(data.get("quizzes_count") or 0),
                "lessons": lessons,
                "sub_steps": sub_steps,
            }
        )
    return normalized


def _normalize_insights(insights, video_link: Optional[str] = None) -> dict:
    if insights is None:
        data = {}
    else:
        data = insights.model_dump() if hasattr(insights, "model_dump") else dict(insights or {})
    stored_video = video_link if video_link is not None else data.get("video_link")
    return {
        "top_hiring_companies": _as_list(data.get("top_hiring_companies")),
        "in_demand_skills": _as_list(data.get("in_demand_skills")),
        "related_career_paths": _as_list(data.get("related_career_paths")),
        "video_link": (str(stored_video).strip() if stored_video else None) or None,
    }


def _normalize_faqs(faqs) -> list[dict]:
    normalized = []
    for item in faqs or []:
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item or {})
        question = str(data.get("question") or "").strip()
        answer = str(data.get("answer") or "").strip()
        if not question and not answer:
            continue
        normalized.append(
            {
                "id": data.get("id") or str(uuid.uuid4()),
                "question": question,
                "answer": answer,
            }
        )
    return normalized


_ALLOWED_RESOURCE_TYPES = {"course", "article", "video", "project", "certification", "other"}


def _normalize_resources(resources: list[RoadmapResourceIn] | list[dict] | None) -> list[dict]:
    normalized = []
    for resource in resources or []:
        data = resource.model_dump() if isinstance(resource, RoadmapResourceIn) else dict(resource)
        title = str(data.get("title") or "").strip()
        url = str(data.get("url") or "").strip()
        if not title and not url:
            continue
        rtype = str(data.get("type") or "article").strip().lower() or "article"
        if rtype not in _ALLOWED_RESOURCE_TYPES:
            rtype = "other"
        platform = str(data.get("platform") or "").strip() or None
        normalized.append(
            {
                "id": data.get("id") or str(uuid.uuid4()),
                "title": title or "Untitled resource",
                "type": rtype,
                "url": url,
                "platform": platform,
                "is_free": bool(data.get("is_free", True)),
            }
        )
    return normalized


def _as_list(value) -> list:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _to_out(row: Roadmap | CareerRoadmap) -> CareerRoadmapOut:
    title = getattr(row, "target_role", None) or getattr(row, "title", "Career Roadmap")
    slug = getattr(row, "slug", None) or slugify(title)
    category = getattr(row, "category", None) or "Technology"
    level = getattr(row, "current_level", None) or getattr(row, "level", "Intermediate")
    short_desc = getattr(row, "short_description", None) or f"Step-by-step career roadmap for {title}."
    long_desc = getattr(row, "long_description", None) or f"Complete practical curriculum to master {title}."
    skills = getattr(row, "skills_to_develop", None) or getattr(row, "skill_tags", []) or []
    duration = getattr(row, "estimated_duration", None) or getattr(row, "duration_months", "6-9 months")

    salary_raw = getattr(row, "salary_lpa", None)
    if not salary_raw and getattr(row, "market_based_salary", None):
        mbs = row.market_based_salary
        if isinstance(mbs, dict):
            salary_raw = mbs.get("average") or mbs.get("formatted") or "Market-based"
    salary = salary_raw or "Market-based"

    milestones = getattr(row, "milestones", None) or []
    if milestones:
        stages_order: list[str] = []
        stages_map: dict[str, list[Milestone]] = {}
        for m in milestones:
            st = getattr(m, "stage_title", None) or "Core Curriculum"
            if st not in stages_map:
                stages_map[st] = []
                stages_order.append(st)
            stages_map[st].append(m)

        steps: list[RoadmapStepOut] = []
        all_resources: list[RoadmapResourceOut] = []

        for s_idx, st_title in enumerate(stages_order, start=1):
            s_milestones = stages_map[st_title]
            sub_steps: list[RoadmapSubStepOut] = []
            for m_idx, m in enumerate(s_milestones, start=1):
                sub_res: list[RoadmapResourceOut] = []
                for r in (getattr(m, "resources", None) or []):
                    res_out = RoadmapResourceOut(
                        id=str(r.id),
                        title=r.title or "Learning Resource",
                        type=str(r.type.value if hasattr(r.type, "value") else r.type),
                        url=r.url or "",
                        platform=r.platform,
                        is_free=True,
                    )
                    sub_res.append(res_out)
                    all_resources.append(res_out)

                diff_val = getattr(m, "difficulty", "intermediate")
                level_str = diff_val.value if hasattr(diff_val, "value") else str(diff_val or "intermediate")
                sub_steps.append(
                    RoadmapSubStepOut(
                        id=str(m.id),
                        title=m.title or f"Milestone {m_idx}",
                        subtitle=m.description or "",
                        duration=m.estimated_time,
                        level=level_str,
                        skill_tags=_as_list(m.skills),
                        resources=sub_res,
                    )
                )

            steps.append(
                RoadmapStepOut(
                    id=f"step-{s_idx}",
                    title=st_title,
                    content=f"Key milestones and competencies for {st_title}",
                    duration=None,
                    lessons_count=len(sub_steps),
                    projects_count=1,
                    quizzes_count=1,
                    lessons=[],
                    sub_steps=sub_steps,
                )
            )
    else:
        steps = []
        for step in (getattr(row, "steps", None) or []):
            lessons = [
                RoadmapLessonOut(id=str(lesson.get("id") or uuid.uuid4()), title=str(lesson.get("title") or ""))
                for lesson in (step.get("lessons") or [])
            ]
            sub_steps = [
                RoadmapSubStepOut(
                    id=str(sub.get("id") or uuid.uuid4()),
                    title=str(sub.get("title") or ""),
                    subtitle=str(sub.get("subtitle") or ""),
                    duration=(str(sub.get("duration")).strip() if sub.get("duration") else None),
                    level=(str(sub.get("level")).strip() if sub.get("level") else None),
                    skill_tags=_as_list(sub.get("skill_tags")),
                    resources=[
                        RoadmapResourceOut(
                            id=str(item.get("id") or uuid.uuid4()),
                            title=str(item.get("title") or ""),
                            type=str(item.get("type") or "article"),
                            url=str(item.get("url") or ""),
                            platform=(str(item.get("platform")).strip() if item.get("platform") else None),
                            is_free=bool(item.get("is_free", True)),
                        )
                        for item in (sub.get("resources") or [])
                    ],
                )
                for sub in (step.get("sub_steps") or [])
            ]
            steps.append(
                RoadmapStepOut(
                    id=str(step.get("id") or uuid.uuid4()),
                    title=str(step.get("title") or ""),
                    content=str(step.get("content") or ""),
                    duration=(str(step.get("duration")).strip() if step.get("duration") else None),
                    lessons_count=int(step.get("lessons_count") or 0),
                    projects_count=int(step.get("projects_count") or 0),
                    quizzes_count=int(step.get("quizzes_count") or 0),
                    lessons=lessons,
                    sub_steps=sub_steps,
                )
            )
        all_resources = [
            RoadmapResourceOut(
                id=str(item.get("id") or uuid.uuid4()),
                title=str(item.get("title") or ""),
                type=str(item.get("type") or "article"),
                url=str(item.get("url") or ""),
                platform=(str(item.get("platform")).strip() if item.get("platform") else None),
                is_free=bool(item.get("is_free", True)),
            )
            for item in (getattr(row, "resources", None) or [])
        ]

    insights_raw = getattr(row, "career_insights", None) or {}
    if not isinstance(insights_raw, dict):
        insights_raw = {}
    faqs = [
        RoadmapFaqOut(
            id=str(item.get("id") or uuid.uuid4()),
            question=str(item.get("question") or ""),
            answer=str(item.get("answer") or ""),
        )
        for item in (getattr(row, "faqs", None) or [])
    ]
    return CareerRoadmapOut(
        id=str(row.id),
        title=title,
        slug=slug,
        category=category,
        level=level,
        industries=_as_list(getattr(row, "industries", [])),
        short_description=short_desc,
        long_description=long_desc,
        skill_tags=_as_list(skills),
        duration_months=duration,
        salary_lpa=salary,
        growth_percent=getattr(row, "growth_percent", None) or "+22%",
        openings_count=getattr(row, "openings_count", None) or "5000+",
        steps=steps,
        resources=all_resources,
        career_insights=CareerInsightsOut(
            top_hiring_companies=_as_list(insights_raw.get("top_hiring_companies")),
            in_demand_skills=_as_list(insights_raw.get("in_demand_skills")),
            related_career_paths=_as_list(insights_raw.get("related_career_paths")),
        ),
        faqs=faqs,
        hero_image_url=getattr(row, "hero_image_url", None),
        video_link=(insights_raw.get("video_link") or None),
        is_published=bool(getattr(row, "is_published", True)),
        is_featured=bool(getattr(row, "is_featured", False)),
        is_trending=bool(getattr(row, "is_trending", False)),
        sort_order=getattr(row, "sort_order", 0) or 0,
        created_by=getattr(row, "user_id", None) or getattr(row, "created_by", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_list_item(row: Roadmap | CareerRoadmap) -> CareerRoadmapListItem:
    title = getattr(row, "target_role", None) or getattr(row, "title", "Career Roadmap")
    slug = getattr(row, "slug", None) or slugify(title)
    category = getattr(row, "category", None) or "Technology"
    level = getattr(row, "current_level", None) or getattr(row, "level", "Intermediate")
    short_desc = getattr(row, "short_description", None)
    duration = getattr(row, "estimated_duration", None) or getattr(row, "duration_months", None)
    salary_raw = getattr(row, "salary_lpa", None)
    if not salary_raw and getattr(row, "market_based_salary", None):
        mbs = row.market_based_salary
        if isinstance(mbs, dict):
            salary_raw = mbs.get("average") or mbs.get("formatted")

    steps_count = 5
    if "milestones" in row.__dict__:
        steps_count = len(row.__dict__["milestones"] or [])
    elif "steps" in row.__dict__:
        steps_count = len(row.__dict__["steps"] or [])

    return CareerRoadmapListItem(
        id=str(row.id),
        title=title,
        slug=slug,
        category=category,
        level=level,
        short_description=short_desc,
        duration_months=duration,
        salary_lpa=salary_raw,
        openings_count=getattr(row, "openings_count", None),
        steps_count=steps_count,
        is_published=bool(getattr(row, "is_published", True)),
        is_featured=bool(getattr(row, "is_featured", False)),
        is_trending=bool(getattr(row, "is_trending", False)),
        hero_image_url=getattr(row, "hero_image_url", None),
        updated_at=row.updated_at,
    )


async def _ensure_unique_slug(db: AsyncSession, base: str, exclude_id: Optional[str] = None) -> str:
    slug = slugify(base)
    candidate = slug
    suffix = 2
    while True:
        q = select(Roadmap.id).where(Roadmap.slug == candidate)
        if exclude_id:
            q = q.where(Roadmap.id != exclude_id)
        exists = (await db.execute(q)).scalar_one_or_none()
        if not exists:
            return candidate
        candidate = f"{slug}-{suffix}"
        suffix += 1


async def list_roadmaps(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    published_only: bool = False,
) -> tuple[list[Roadmap], int]:
    q = select(Roadmap).options(selectinload(Roadmap.milestones))
    if published_only:
        q = q.where(Roadmap.is_published.is_(True))
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.where(
            or_(
                Roadmap.target_role.ilike(term),
                Roadmap.slug.ilike(term),
                Roadmap.category.ilike(term),
                Roadmap.short_description.ilike(term),
            )
        )
    if status and status != "all":
        if status == "published":
            q = q.where(Roadmap.is_published.is_(True))
        elif status == "draft":
            q = q.where(Roadmap.is_published.is_(False))
        elif status == "featured":
            q = q.where(Roadmap.is_featured.is_(True))
        elif status == "trending":
            q = q.where(Roadmap.is_trending.is_(True))
    if category and category != "all":
        q = q.where(Roadmap.category == category)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    q = (
        q.order_by(Roadmap.sort_order.asc(), Roadmap.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(q)).scalars().all()
    return list(items), total


async def get_by_id(db: AsyncSession, roadmap_id: str) -> Roadmap:
    q = (
        select(Roadmap)
        .options(selectinload(Roadmap.milestones).selectinload(Milestone.resources))
        .where(Roadmap.id == roadmap_id)
    )
    row = (await db.execute(q)).scalar_one_or_none()
    if not row:
        row = (await db.execute(select(CareerRoadmap).where(CareerRoadmap.id == roadmap_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return row


async def get_by_slug(db: AsyncSession, slug: str, *, published_only: bool = True) -> Roadmap:
    clean_slug = slugify(slug)
    q = (
        select(Roadmap)
        .options(selectinload(Roadmap.milestones).selectinload(Milestone.resources))
        .where(
            or_(
                Roadmap.slug == clean_slug,
                Roadmap.slug == slug,
                func.lower(Roadmap.target_role) == func.lower(slug.replace("-", " ")),
                func.lower(Roadmap.target_role) == func.lower(slug),
            )
        )
    )
    if published_only:
        q = q.where(Roadmap.is_published.is_(True))
    row = (await db.execute(q)).scalar_one_or_none()
    if not row:
        cr_q = select(CareerRoadmap).where(CareerRoadmap.slug == clean_slug)
        if published_only:
            cr_q = cr_q.where(CareerRoadmap.is_published.is_(True))
        row = (await db.execute(cr_q)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return row


async def create_roadmap(db: AsyncSession, body: CareerRoadmapCreate, admin_id: Optional[str]) -> Roadmap:
    slug = await _ensure_unique_slug(db, body.slug or body.title)
    row = Roadmap(
        id=str(uuid.uuid4()),
        user_id=admin_id,
        target_role=body.title.strip(),
        slug=slug,
        category=body.category.strip() or "Technology",
        current_level=body.level.strip() or "Intermediate",
        target_level="Senior",
        industries=body.industries or [],
        short_description=(body.short_description or "").strip() or None,
        long_description=(body.long_description or "").strip() or None,
        skills_to_develop=body.skill_tags or [],
        estimated_duration=body.duration_months,
        salary_lpa=body.salary_lpa,
        market_based_salary={"average": body.salary_lpa or "Market-based"},
        growth_percent=body.growth_percent,
        openings_count=body.openings_count,
        hero_image_url=body.hero_image_url,
        is_published=body.is_published,
        is_featured=body.is_featured,
        is_trending=body.is_trending,
        sort_order=body.sort_order or 0,
        career_insights=_normalize_insights(body.career_insights, body.video_link),
        faqs=_normalize_faqs(body.faqs),
        status="active",
    )
    db.add(row)
    await db.flush()

    order = 1
    for stage_idx, step in enumerate(body.steps or [], 1):
        stage_title = getattr(step, "title", None) or f"Stage {stage_idx}"
        subs = getattr(step, "sub_steps", None) or []
        if not subs:
            subs = [
                RoadmapSubStepIn(
                    title=getattr(step, "title", f"Milestone {order}"),
                    subtitle=getattr(step, "content", ""),
                    duration=getattr(step, "duration", "2-3 weeks"),
                    level="intermediate",
                    skill_tags=body.skill_tags[:3],
                    resources=[],
                )
            ]

        for sub in subs:
            m = Milestone(
                id=str(uuid.uuid4()),
                roadmap_id=row.id,
                title=sub.title,
                description=sub.subtitle or "",
                stage_title=stage_title,
                stage_order=stage_idx,
                order_num=order,
                skills=sub.skill_tags or [],
                estimated_time=sub.duration or "2 weeks",
                difficulty=DifficultyLevel.intermediate,
                status=MilestoneStatus.pending,
            )
            db.add(m)
            await db.flush()

            for r_data in sub.resources or []:
                res = Resource(
                    id=str(uuid.uuid4()),
                    milestone_id=m.id,
                    title=r_data.title,
                    type=ResourceType.article if getattr(r_data, "type", "article") == "article" else ResourceType.video,
                    url=r_data.url or "https://www.youtube.com",
                    platform=r_data.platform or "Learning Platform",
                    duration="1-2 hours",
                    difficulty=DifficultyLevel.intermediate,
                )
                db.add(res)
            order += 1

    await db.commit()
    return await get_by_id(db, row.id)


async def update_roadmap(db: AsyncSession, roadmap_id: str, body: CareerRoadmapUpdate) -> Roadmap:
    row = await get_by_id(db, roadmap_id)
    data = body.model_dump(exclude_unset=True)

    if isinstance(row, Roadmap):
        if "title" in data and data["title"] is not None:
            row.target_role = data["title"].strip()
        if "slug" in data:
            row.slug = await _ensure_unique_slug(db, data["slug"] or row.target_role, exclude_id=row.id)
        if "category" in data and data["category"] is not None:
            row.category = data["category"].strip() or row.category
        if "level" in data and data["level"] is not None:
            row.current_level = data["level"].strip() or row.current_level
        if "industries" in data:
            row.industries = data["industries"] or []
        if "short_description" in data:
            row.short_description = (data["short_description"] or "").strip() or None
        if "long_description" in data:
            row.long_description = (data["long_description"] or "").strip() or None
        if "skill_tags" in data:
            row.skills_to_develop = data["skill_tags"] or []
        if "duration_months" in data:
            row.estimated_duration = data["duration_months"]
        if "salary_lpa" in data:
            row.salary_lpa = data["salary_lpa"]
            row.market_based_salary = {"average": data["salary_lpa"] or "Market-based"}
        if "growth_percent" in data:
            row.growth_percent = data["growth_percent"]
        if "openings_count" in data:
            row.openings_count = data["openings_count"]
        if "career_insights" in data or "video_link" in data:
            current = row.career_insights if isinstance(row.career_insights, dict) else {}
            incoming = data["career_insights"] if "career_insights" in data else current
            video_value = data["video_link"] if "video_link" in data else current.get("video_link")
            row.career_insights = _normalize_insights(incoming, video_value)
        if "faqs" in data:
            row.faqs = _normalize_faqs(data["faqs"])
        if "hero_image_url" in data:
            row.hero_image_url = data["hero_image_url"] or None
        if "is_published" in data:
            row.is_published = bool(data["is_published"])
        if "is_featured" in data:
            row.is_featured = bool(data["is_featured"])
        if "is_trending" in data:
            row.is_trending = bool(data["is_trending"])
        if "sort_order" in data and data["sort_order"] is not None:
            row.sort_order = data["sort_order"]

        if "steps" in data and data["steps"] is not None:
            # Delete old milestones and resources
            from sqlalchemy import delete
            await db.execute(delete(Milestone).where(Milestone.roadmap_id == row.id))
            await db.flush()

            order = 1
            for stage_idx, step in enumerate(body.steps or [], 1):
                stage_title = getattr(step, "title", None) or f"Stage {stage_idx}"
                subs = getattr(step, "sub_steps", None) or []
                for sub in subs:
                    m = Milestone(
                        id=str(uuid.uuid4()),
                        roadmap_id=row.id,
                        title=sub.title,
                        description=sub.subtitle or "",
                        stage_title=stage_title,
                        stage_order=stage_idx,
                        order_num=order,
                        skills=sub.skill_tags or [],
                        estimated_time=sub.duration or "2 weeks",
                        difficulty=DifficultyLevel.intermediate,
                        status=MilestoneStatus.pending,
                    )
                    db.add(m)
                    await db.flush()

                    for r_data in sub.resources or []:
                        res = Resource(
                            id=str(uuid.uuid4()),
                            milestone_id=m.id,
                            title=r_data.title,
                            type=ResourceType.article if getattr(r_data, "type", "article") == "article" else ResourceType.video,
                            url=r_data.url or "https://www.youtube.com",
                            platform=r_data.platform or "Learning Platform",
                            duration="1-2 hours",
                            difficulty=DifficultyLevel.intermediate,
                        )
                        db.add(res)
                    order += 1

        await db.commit()
        return await get_by_id(db, row.id)

    # Legacy CareerRoadmap fallback
    if "title" in data and data["title"] is not None:
        row.title = data["title"].strip()
    if "slug" in data:
        row.slug = await _ensure_unique_slug(db, data["slug"] or row.title, exclude_id=row.id)
    if "category" in data and data["category"] is not None:
        row.category = data["category"].strip() or row.category
    if "level" in data and data["level"] is not None:
        row.level = data["level"].strip() or row.level
    if "industries" in data:
        row.industries = data["industries"] or []
    if "short_description" in data:
        row.short_description = (data["short_description"] or "").strip() or None
    if "long_description" in data:
        row.long_description = (data["long_description"] or "").strip() or None
    if "skill_tags" in data:
        row.skill_tags = data["skill_tags"] or []
    if "duration_months" in data:
        row.duration_months = data["duration_months"]
    if "salary_lpa" in data:
        row.salary_lpa = data["salary_lpa"]
    if "growth_percent" in data:
        row.growth_percent = data["growth_percent"]
    if "openings_count" in data:
        row.openings_count = data["openings_count"]
    if "steps" in data:
        row.steps = _normalize_steps(data["steps"])
    if "resources" in data:
        row.resources = _normalize_resources(data["resources"])
    if "career_insights" in data or "video_link" in data:
        current = row.career_insights if isinstance(row.career_insights, dict) else {}
        incoming = data["career_insights"] if "career_insights" in data else current
        video_value = data["video_link"] if "video_link" in data else current.get("video_link")
        row.career_insights = _normalize_insights(incoming, video_value)
    if "faqs" in data:
        row.faqs = _normalize_faqs(data["faqs"])
    if "hero_image_url" in data:
        row.hero_image_url = data["hero_image_url"] or None
    if "is_published" in data:
        row.is_published = bool(data["is_published"])
    if "is_featured" in data:
        row.is_featured = bool(data["is_featured"])
    if "is_trending" in data:
        row.is_trending = bool(data["is_trending"])
    if "sort_order" in data and data["sort_order"] is not None:
        row.sort_order = data["sort_order"]
    await db.commit()
    await db.refresh(row)
    return row


async def delete_roadmap(db: AsyncSession, roadmap_id: str) -> None:
    row = await get_by_id(db, roadmap_id)
    await db.delete(row)
    await db.commit()


async def import_roadmaps_from_json(db: AsyncSession, raw: bytes, admin_id: Optional[str]) -> RoadmapImportResponse:
    from app.modules.jobs_portal.services.career_roadmap_import import (
        IMPORT_LIMIT,
        IMPORT_MAX_BYTES,
        decode_import_payload,
        extract_import_items,
        to_create_payload,
    )

    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw) > IMPORT_MAX_BYTES:
        raise HTTPException(status_code=400, detail="JSON file must be 8MB or smaller")
    try:
        payload = decode_import_payload(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    records = extract_import_items(payload)
    if not records:
        raise HTTPException(status_code=400, detail="JSON has no roadmap records to import")
    if len(records) > IMPORT_LIMIT:
        raise HTTPException(status_code=400, detail=f"Import at most {IMPORT_LIMIT} roadmaps at a time")

    created = 0
    updated = 0
    failed = 0
    results: list[RoadmapImportItemResult] = []

    for index, record in enumerate(records, start=1):
        title = str(record.get("title") or record.get("detail_title") or f"Item {index}")
        try:
            body = to_create_payload(record, sort_order=index)
            existing = (
                await db.execute(select(CareerRoadmap).where(CareerRoadmap.slug == body.slug))
            ).scalar_one_or_none()
            if existing:
                update = CareerRoadmapUpdate(
                    title=body.title,
                    slug=body.slug,
                    category=body.category,
                    level=body.level,
                    industries=body.industries,
                    short_description=body.short_description,
                    long_description=body.long_description,
                    skill_tags=body.skill_tags,
                    duration_months=body.duration_months,
                    salary_lpa=body.salary_lpa,
                    growth_percent=body.growth_percent,
                    openings_count=body.openings_count,
                    steps=body.steps,
                    resources=body.resources,
                    career_insights=body.career_insights,
                    faqs=body.faqs,
                    video_link=body.video_link,
                    is_published=True,
                    is_featured=body.is_featured,
                    is_trending=body.is_trending,
                    sort_order=body.sort_order,
                )
                await update_roadmap(db, existing.id, update)
                updated += 1
                results.append(
                    RoadmapImportItemResult(title=body.title, slug=body.slug, action="updated")
                )
            else:
                body.is_published = True
                await create_roadmap(db, body, admin_id)
                created += 1
                results.append(
                    RoadmapImportItemResult(title=body.title, slug=body.slug, action="created")
                )
        except HTTPException as exc:
            failed += 1
            results.append(
                RoadmapImportItemResult(
                    title=title,
                    slug="",
                    action="failed",
                    message=str(exc.detail),
                )
            )
        except Exception as exc:
            failed += 1
            results.append(
                RoadmapImportItemResult(
                    title=title,
                    slug="",
                    action="failed",
                    message=str(exc)[:240],
                )
            )

    return RoadmapImportResponse(created=created, updated=updated, failed=failed, items=results)


async def save_hero_image(file: UploadFile) -> str:
    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPG, PNG and WebP images are allowed")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > HERO_IMAGE_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Image must be 2MB or smaller")
    ext = _ALLOWED_IMAGE_TYPES[content_type]
    dest_dir = get_upload_dir() / "career_roadmaps"
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    Path(dest_dir / filename).write_bytes(data)
    return f"/uploads/career_roadmaps/{filename}"


def _infer_category(role: str) -> str:
    r = role.lower()
    if any(k in r for k in ["data", "ml", "ai", "machine learning", "analyst", "scientist"]):
        return "AI & Data"
    if any(k in r for k in ["devops", "cloud", "sre", "aws", "azure", "gcp", "docker", "kubernetes"]):
        return "Cloud & DevOps"
    if any(k in r for k in ["security", "cyber", "penetration", "ethical"]):
        return "Cybersecurity"
    if any(k in r for k in ["design", "ui", "ux", "product"]):
        return "Design & Product"
    return "Software Engineering"


async def generate_career_roadmap_ai(
    role: str,
    category: Optional[str] = None,
    level: Optional[str] = "Intermediate",
) -> dict:
    from app.modules.jobs_portal.services.ai_roadmap_service import ai_roadmap_service
    from app.shared.models.user import User

    dummy_user = User(id="00000000-0000-0000-0000-000000000000", skills=[])
    ai_data = await ai_roadmap_service.generate_roadmap(
        user=dummy_user,
        target_role=role.strip(),
        current_level=level or "Intermediate",
        target_level="Senior",
    )

    clean_category = category or _infer_category(role)
    slug = re.sub(r"[^a-z0-9]+", "-", role.lower()).strip("-")

    milestones = ai_data.get("milestones", [])
    stages_dict: dict[str, list] = {}
    for m in milestones:
        st = m.get("stage_title") or "Core Curriculum"
        if st not in stages_dict:
            stages_dict[st] = []
        stages_dict[st].append(m)

    steps = []
    for s_idx, (st_title, s_milestones) in enumerate(stages_dict.items(), start=1):
        subs = []
        for m_idx, m in enumerate(s_milestones, start=1):
            res_list = []
            for r in m.get("resources", []):
                res_list.append({
                    "id": str(uuid.uuid4()),
                    "title": r.get("title") or "Learning Guide",
                    "type": r.get("type") or "article",
                    "url": r.get("url") or "",
                    "platform": r.get("platform") or "Documentation",
                    "is_free": r.get("is_free", True),
                })
            subs.append({
                "id": str(uuid.uuid4()),
                "title": m.get("title") or f"Milestone {m_idx}",
                "subtitle": m.get("description") or "",
                "duration": m.get("estimated_time") or "2-3 weeks",
                "level": m.get("difficulty") or "Intermediate",
                "skill_tags": m.get("skills", []),
                "resources": res_list,
            })
        steps.append({
            "id": f"step-{s_idx}",
            "title": st_title,
            "content": f"Master the essential competencies and hands-on skills in {st_title}.",
            "duration": f"{len(subs) * 2}-{len(subs) * 3} weeks",
            "lessons_count": len(subs),
            "projects_count": 1,
            "quizzes_count": 0,
            "lessons": [],
            "sub_steps": subs,
        })

    all_skills = ai_data.get("skills_to_develop", [])
    if not all_skills:
        skill_set = set()
        for m in milestones:
            for s in m.get("skills", []):
                skill_set.add(s)
        all_skills = list(skill_set)

    salary = ai_data.get("market_based_salary")
    salary_str = str(salary) if salary else "₹8-16 LPA"
    duration = ai_data.get("estimated_duration") or "6-9 Months"

    return {
        "title": role.strip(),
        "slug": slug,
        "category": clean_category,
        "level": level or "Intermediate",
        "industries": ["IT", "Software", "Tech"],
        "short_description": f"Complete guide to becoming a job-ready {role.strip()} with structured milestones and resources.",
        "long_description": (
            f"Step-by-step career path for {role.strip()}. Learn foundational to advanced tools, "
            "build real-world capstone projects, and prepare for interviews with industry partners."
        ),
        "skill_tags": all_skills[:12],
        "duration_months": duration,
        "salary_lpa": salary_str,
        "growth_percent": "+24%",
        "openings_count": "10,000+",
        "steps": steps,
        "resources": [],
        "career_insights": {
            "top_hiring_companies": ["Google", "Amazon", "Microsoft", "TCS", "Infosys", "Wipro", "Accenture"],
            "in_demand_skills": all_skills[:5],
            "related_career_paths": [f"Senior {role.strip()}", f"{role.strip()} Lead", "Technical Architect"],
        },
        "faqs": [
            {
                "id": str(uuid.uuid4()),
                "question": "How long will it take to complete this roadmap?",
                "answer": f"Typically {duration} dedicating 10-15 hours per week.",
            },
            {
                "id": str(uuid.uuid4()),
                "question": "Are the study resources included free?",
                "answer": "Yes, curated links point to official documentation, high-quality free guides, and open courses.",
            },
            {
                "id": str(uuid.uuid4()),
                "question": "Do I need prior experience?",
                "answer": "This path starts from foundational fundamentals and progressively advances to production-level skills.",
            },
        ],
        "is_published": True,
        "is_featured": False,
        "is_trending": True,
        "sort_order": 0,
    }
