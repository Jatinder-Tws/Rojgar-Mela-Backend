import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_upload_dir
from app.modules.jobs_portal.models.career_roadmap import CareerRoadmap
from app.modules.jobs_portal.schemas.career_roadmap import (
    CareerInsightsOut,
    CareerRoadmapCreate,
    CareerRoadmapListItem,
    CareerRoadmapOut,
    CareerRoadmapUpdate,
    RoadmapFaqOut,
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
    {
        "title": "Full Stack Developer",
        "slug": "full-stack-developer",
        "category": "Technology",
        "level": "Intermediate",
        "industries": ["IT", "Software", "Startup"],
        "short_description": "Master frontend, backend, databases and cloud deployment to become a job-ready full stack developer.",
        "long_description": (
            "This roadmap takes you from HTML/CSS fundamentals through React, Node.js, databases, "
            "and production deployment. Each step includes lessons, hands-on projects, and quizzes "
            "aligned with hiring demand on Rojgar Mela."
        ),
        "skill_tags": ["React", "Node.js", "Databases", "TypeScript", "REST APIs", "Git"],
        "duration_months": "6 months",
        "salary_lpa": "₹12L",
        "growth_percent": "High",
        "openings_count": "5800+",
        "is_published": True,
        "is_featured": True,
        "is_trending": True,
        "sort_order": 1,
        "steps": [
            {
                "title": "Frontend Fundamentals",
                "content": "HTML5, modern CSS, responsive layouts, and JavaScript ES6+ foundations.",
                "lessons_count": 8,
                "projects_count": 2,
                "quizzes_count": 3,
                "lessons": [
                    {"title": "Semantic HTML & accessibility"},
                    {"title": "Flexbox, Grid & responsive CSS"},
                    {"title": "JavaScript ES6+, DOM & Fetch"},
                ],
            },
            {
                "title": "React & State Management",
                "content": "Build interactive UIs with React 18, hooks, and client-side state.",
                "lessons_count": 10,
                "projects_count": 2,
                "quizzes_count": 2,
                "lessons": [
                    {"title": "Components, props and hooks"},
                    {"title": "React Router & forms"},
                ],
            },
            {
                "title": "Backend APIs & Databases",
                "content": "Node.js, Express, REST APIs, PostgreSQL and authentication.",
                "lessons_count": 9,
                "projects_count": 2,
                "quizzes_count": 2,
                "lessons": [
                    {"title": "Express REST APIs"},
                    {"title": "SQL & PostgreSQL modeling"},
                ],
            },
            {
                "title": "Projects, Testing & Placement",
                "content": "Ship a production app, write tests, and prepare for interviews.",
                "lessons_count": 6,
                "projects_count": 1,
                "quizzes_count": 2,
                "lessons": [
                    {"title": "Deployment on cloud"},
                    {"title": "Interview checklist"},
                ],
            },
        ],
    },
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


def _normalize_insights(insights) -> dict:
    if insights is None:
        return {"top_hiring_companies": [], "in_demand_skills": [], "related_career_paths": []}
    data = insights.model_dump() if hasattr(insights, "model_dump") else dict(insights or {})
    return {
        "top_hiring_companies": _as_list(data.get("top_hiring_companies")),
        "in_demand_skills": _as_list(data.get("in_demand_skills")),
        "related_career_paths": _as_list(data.get("related_career_paths")),
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


def _to_out(row: CareerRoadmap) -> CareerRoadmapOut:
    steps = []
    for step in row.steps or []:
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
    resources = [
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
        id=row.id,
        title=row.title,
        slug=row.slug,
        category=row.category,
        level=row.level,
        industries=_as_list(row.industries),
        short_description=row.short_description,
        long_description=row.long_description,
        skill_tags=_as_list(row.skill_tags),
        duration_months=row.duration_months,
        salary_lpa=row.salary_lpa,
        growth_percent=row.growth_percent,
        openings_count=row.openings_count,
        steps=steps,
        resources=resources,
        career_insights=CareerInsightsOut(
            top_hiring_companies=_as_list(insights_raw.get("top_hiring_companies")),
            in_demand_skills=_as_list(insights_raw.get("in_demand_skills")),
            related_career_paths=_as_list(insights_raw.get("related_career_paths")),
        ),
        faqs=faqs,
        hero_image_url=row.hero_image_url,
        is_published=bool(row.is_published),
        is_featured=bool(row.is_featured),
        is_trending=bool(row.is_trending),
        sort_order=row.sort_order or 0,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_list_item(row: CareerRoadmap) -> CareerRoadmapListItem:
    return CareerRoadmapListItem(
        id=row.id,
        title=row.title,
        slug=row.slug,
        category=row.category,
        level=row.level,
        short_description=row.short_description,
        duration_months=row.duration_months,
        salary_lpa=row.salary_lpa,
        openings_count=row.openings_count,
        steps_count=len(row.steps or []),
        is_published=bool(row.is_published),
        is_featured=bool(row.is_featured),
        is_trending=bool(row.is_trending),
        hero_image_url=row.hero_image_url,
        updated_at=row.updated_at,
    )


async def _ensure_unique_slug(db: AsyncSession, base: str, exclude_id: Optional[str] = None) -> str:
    slug = slugify(base)
    candidate = slug
    suffix = 2
    while True:
        q = select(CareerRoadmap.id).where(CareerRoadmap.slug == candidate)
        if exclude_id:
            q = q.where(CareerRoadmap.id != exclude_id)
        exists = (await db.execute(q)).scalar_one_or_none()
        if not exists:
            return candidate
        candidate = f"{slug}-{suffix}"
        suffix += 1


async def seed_if_empty(db: AsyncSession) -> None:
    count = (await db.execute(select(func.count()).select_from(CareerRoadmap))).scalar() or 0
    if count:
        return
    for item in SEED_ROADMAPS:
        row = CareerRoadmap(
            title=item["title"],
            slug=item["slug"],
            category=item["category"],
            level=item["level"],
            industries=item["industries"],
            short_description=item["short_description"],
            long_description=item["long_description"],
            skill_tags=item["skill_tags"],
            duration_months=item["duration_months"],
            salary_lpa=item["salary_lpa"],
            growth_percent=item["growth_percent"],
            openings_count=item["openings_count"],
            steps=_normalize_steps(item["steps"]),
            resources=_normalize_resources(item.get("resources")),
            is_published=item["is_published"],
            is_featured=item["is_featured"],
            is_trending=item["is_trending"],
            sort_order=item["sort_order"],
        )
        db.add(row)
    await db.commit()


async def list_roadmaps(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    published_only: bool = False,
) -> tuple[list[CareerRoadmap], int]:
    await seed_if_empty(db)
    q = select(CareerRoadmap)
    if published_only:
        q = q.where(CareerRoadmap.is_published.is_(True))
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.where(
            or_(
                CareerRoadmap.title.ilike(term),
                CareerRoadmap.slug.ilike(term),
                CareerRoadmap.category.ilike(term),
                CareerRoadmap.short_description.ilike(term),
            )
        )
    if status and status != "all":
        if status == "published":
            q = q.where(CareerRoadmap.is_published.is_(True))
        elif status == "draft":
            q = q.where(CareerRoadmap.is_published.is_(False))
        elif status == "featured":
            q = q.where(CareerRoadmap.is_featured.is_(True))
        elif status == "trending":
            q = q.where(CareerRoadmap.is_trending.is_(True))
    if category and category != "all":
        q = q.where(CareerRoadmap.category == category)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    q = (
        q.order_by(CareerRoadmap.sort_order.asc(), CareerRoadmap.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(q)).scalars().all()
    return list(items), total


async def get_by_id(db: AsyncSession, roadmap_id: str) -> CareerRoadmap:
    row = (await db.execute(select(CareerRoadmap).where(CareerRoadmap.id == roadmap_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return row


async def get_by_slug(db: AsyncSession, slug: str, *, published_only: bool = True) -> CareerRoadmap:
    q = select(CareerRoadmap).where(CareerRoadmap.slug == slugify(slug))
    if published_only:
        q = q.where(CareerRoadmap.is_published.is_(True))
    row = (await db.execute(q)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return row


async def create_roadmap(db: AsyncSession, body: CareerRoadmapCreate, admin_id: Optional[str]) -> CareerRoadmap:
    slug = await _ensure_unique_slug(db, body.slug or body.title)
    row = CareerRoadmap(
        title=body.title.strip(),
        slug=slug,
        category=body.category.strip() or "Technology",
        level=body.level.strip() or "Intermediate",
        industries=body.industries or [],
        short_description=(body.short_description or "").strip() or None,
        long_description=(body.long_description or "").strip() or None,
        skill_tags=body.skill_tags or [],
        duration_months=body.duration_months,
        salary_lpa=body.salary_lpa,
        growth_percent=body.growth_percent,
        openings_count=body.openings_count,
        steps=_normalize_steps(body.steps),
        resources=_normalize_resources(body.resources),
        career_insights=_normalize_insights(body.career_insights),
        faqs=_normalize_faqs(body.faqs),
        hero_image_url=body.hero_image_url,
        is_published=body.is_published,
        is_featured=body.is_featured,
        is_trending=body.is_trending,
        sort_order=body.sort_order or 0,
        created_by=admin_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_roadmap(db: AsyncSession, roadmap_id: str, body: CareerRoadmapUpdate) -> CareerRoadmap:
    row = await get_by_id(db, roadmap_id)
    data = body.model_dump(exclude_unset=True)
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
    if "career_insights" in data:
        row.career_insights = _normalize_insights(data["career_insights"])
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
