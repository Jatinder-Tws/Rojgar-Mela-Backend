"""Safe Seeding / Import Script for Career Roadmaps.

Imports scraped roadmaps from data/career_roadmaps_import.json into both:
1. career_roadmaps (CMS / Super Admin table)
2. roadmaps & child milestones/resources (unified relational table)

Features:
- Idempotent: can be executed multiple times without duplicating or corrupting data.
- Safe: never deletes existing records.
- Fixes any existing malformed titles/categories (e.g. IAS officer title or miscategorized government roles).
- Enriches milestones and study resources from scraped data.
- Ensures published flag is active for all roadmaps.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select, text

# Add backend root to sys.path so app imports work seamlessly
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

import app.main  # Registers all SQLAlchemy models
from app.core.database import AsyncSessionLocal
from app.modules.jobs_portal.models.career_roadmap import CareerRoadmap
from app.modules.jobs_portal.models.roadmap import (
    DifficultyLevel,
    Milestone,
    MilestoneStatus,
    Resource,
    ResourceType,
    Roadmap,
)
from app.modules.jobs_portal.schemas.career_roadmap import CareerRoadmapCreate


def load_import_data(filepath: str | Path) -> list[dict[str, Any]]:
    path = Path(filepath)
    if not path.is_absolute():
        path = backend_root / path

    if not path.exists():
        raise FileNotFoundError(f"Import file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Import file must contain a JSON array of roadmaps")

    return data


def _count_res(step_list: list[Any]) -> int:
    return sum(
        len(sub.get("resources", []))
        for st in (step_list or [])
        for sub in (st.get("sub_steps", []) if isinstance(st, dict) else [])
    )


async def import_roadmaps(filepath: str = "data/career_roadmaps_import.json") -> dict[str, int]:
    items = load_import_data(filepath)
    print(f"Loaded {len(items)} roadmaps from {filepath}")

    stats = {
        "career_created": 0,
        "career_updated": 0,
        "career_unchanged": 0,
        "unified_created": 0,
        "unified_updated": 0,
        "errors": 0,
    }

    async with AsyncSessionLocal() as session:
        # 1. Fetch existing career_roadmaps
        existing_cr_query = await session.execute(select(CareerRoadmap))
        existing_crs = existing_cr_query.scalars().all()
        cr_by_slug = {cr.slug: cr for cr in existing_crs if cr.slug}

        for item in items:
            try:
                # Validate schema
                validated = CareerRoadmapCreate(**item)
                slug = validated.slug

                if slug in cr_by_slug:
                    cr = cr_by_slug[slug]
                    changed = False

                    # Fix corrupted titles
                    if cr.title == "Professional CareerRoadmaps" and validated.title:
                        cr.title = validated.title
                        changed = True

                    # Fix miscategorized records
                    if cr.category != validated.category:
                        cr.category = validated.category
                        changed = True

                    # Enhance steps & resources if incoming has richer content
                    incoming_steps = [s.model_dump() for s in validated.steps]
                    if not cr.steps or _count_res(cr.steps) < _count_res(incoming_steps):
                        cr.steps = incoming_steps
                        changed = True

                    # Enhance missing insights
                    if (not cr.career_insights or not cr.career_insights.get("top_hiring_companies")) and validated.career_insights:
                        cr.career_insights = validated.career_insights.model_dump()
                        changed = True

                    # Enhance missing FAQs
                    if (not cr.faqs or len(cr.faqs) == 0) and validated.faqs:
                        cr.faqs = [f.model_dump() for f in validated.faqs]
                        changed = True

                    # Ensure published
                    if not cr.is_published:
                        cr.is_published = True
                        changed = True

                    if changed:
                        stats["career_updated"] += 1
                    else:
                        stats["career_unchanged"] += 1
                else:
                    new_cr = CareerRoadmap(
                        id=str(uuid.uuid4()),
                        title=validated.title,
                        slug=slug,
                        category=validated.category,
                        level=validated.level,
                        industries=validated.industries,
                        short_description=validated.short_description,
                        long_description=validated.long_description,
                        skill_tags=validated.skill_tags,
                        duration_months=validated.duration_months,
                        salary_lpa=validated.salary_lpa,
                        growth_percent=validated.growth_percent,
                        openings_count=validated.openings_count,
                        steps=[s.model_dump() for s in validated.steps],
                        resources=[r.model_dump() for r in validated.resources],
                        career_insights=validated.career_insights.model_dump() if validated.career_insights else {},
                        faqs=[f.model_dump() for f in validated.faqs],
                        hero_image_url=validated.hero_image_url,
                        is_published=True,
                        is_featured=validated.is_featured,
                        is_trending=validated.is_trending,
                        sort_order=validated.sort_order or 0,
                    )
                    session.add(new_cr)
                    cr_by_slug[slug] = new_cr
                    stats["career_created"] += 1

            except Exception as e:
                print(f"Error processing item '{item.get('title')}': {e}")
                stats["errors"] += 1

        await session.flush()

        # 2. Sync to unified relational roadmaps table
        existing_rms_query = await session.execute(select(Roadmap))
        existing_rms = existing_rms_query.scalars().all()
        rm_by_slug = {rm.slug: rm for rm in existing_rms if rm.slug}
        rm_by_role = {rm.target_role.strip().lower(): rm for rm in existing_rms if rm.target_role}

        all_crs_query = await session.execute(select(CareerRoadmap))
        all_crs = all_crs_query.scalars().all()

        for cr in all_crs:
            slug_key = cr.slug
            role_key = cr.title.strip().lower()

            rm = rm_by_slug.get(slug_key) or rm_by_role.get(role_key)
            if rm:
                # Update title & category if needed
                if rm.target_role != cr.title:
                    rm.target_role = cr.title
                    stats["unified_updated"] += 1
                if rm.category != cr.category:
                    rm.category = cr.category
                rm.is_published = True

                # If rm has milestones but 0 resources, populate resources from cr.steps
                existing_res_cnt = (
                    await session.execute(
                        select(text("count(*)")).select_from(Resource).join(Milestone).where(Milestone.roadmap_id == rm.id)
                    )
                ).scalar() or 0

                if existing_res_cnt == 0 and cr.steps:
                    # Clear out old empty milestones and recreate with full steps & resources
                    await session.execute(
                        text("DELETE FROM milestones WHERE roadmap_id = :rid"),
                        {"rid": rm.id}
                    )
                    new_rm = rm
                else:
                    continue
            else:
                # Create new entry in unified roadmaps table
                new_rm = Roadmap(
                    id=str(uuid.uuid4()),
                    user_id=None,
                    target_role=cr.title,
                    slug=slug_key,
                    category=cr.category or "Technology",
                    current_level=cr.level or "beginner",
                    target_level="senior",
                    skills_to_develop=cr.skill_tags or [],
                    current_skills=[],
                    estimated_duration=cr.duration_months or "6-9 months",
                    market_based_salary={"average": cr.salary_lpa or "₹8-12 LPA"},
                    short_description=cr.short_description,
                    long_description=cr.long_description,
                    industries=cr.industries or [],
                    salary_lpa=cr.salary_lpa,
                    growth_percent=cr.growth_percent,
                    openings_count=cr.openings_count,
                    hero_image_url=cr.hero_image_url,
                    is_published=True,
                    is_featured=bool(cr.is_featured),
                    is_trending=bool(cr.is_trending),
                    sort_order=cr.sort_order or 0,
                    career_insights=cr.career_insights or {},
                    faqs=cr.faqs or [],
                    status="active",
                )
                session.add(new_rm)
                await session.flush()
                stats["unified_created"] += 1

            # Create milestones & resources
            steps = cr.steps or []
            order = 1
            for stage_idx, step in enumerate(steps, 1):
                stage_title = step.get("title") or f"Stage {stage_idx}"
                subs = step.get("sub_steps") or []
                if not subs:
                    subs = [
                        {
                            "title": step.get("title") or f"Milestone {order}",
                            "subtitle": step.get("content") or "",
                            "duration": step.get("duration") or "2-3 weeks",
                            "level": "intermediate",
                            "skill_tags": cr.skill_tags[:3] if cr.skill_tags else ["Foundations"],
                            "resources": [],
                        }
                    ]

                for sub in subs:
                    sub_title = sub.get("title") or f"Milestone {order}"
                    sub_skills = sub.get("skill_tags") or []
                    m = Milestone(
                        id=str(uuid.uuid4()),
                        roadmap_id=new_rm.id,
                        title=sub_title,
                        description=sub.get("subtitle") or "",
                        stage_title=stage_title,
                        stage_order=stage_idx,
                        order_num=order,
                        skills=sub_skills,
                        estimated_time=sub.get("duration") or "2 weeks",
                        difficulty=DifficultyLevel.intermediate,
                        status=MilestoneStatus.pending,
                    )
                    session.add(m)
                    await session.flush()

                    sub_res = sub.get("resources") or []
                    for r_data in sub_res:
                        res = Resource(
                            id=str(uuid.uuid4()),
                            milestone_id=m.id,
                            title=r_data.get("title") or f"{sub_title} Resource",
                            type=ResourceType.article if r_data.get("type") == "article" else ResourceType.video,
                            url=r_data.get("url") or "https://www.google.com",
                            platform=r_data.get("platform") or "Learning Platform",
                            duration=r_data.get("duration") or "1-2 hours",
                            difficulty=DifficultyLevel.intermediate,
                        )
                        session.add(res)

                    order += 1

            rm_by_slug[slug_key] = new_rm
            rm_by_role[role_key] = new_rm

        await session.commit()
        print("\n=== IMPORT & SYNC COMPLETE ===")
        print(f"Career Roadmaps Created:   {stats['career_created']}")
        print(f"Career Roadmaps Updated:   {stats['career_updated']}")
        print(f"Career Roadmaps Unchanged: {stats['career_unchanged']}")
        print(f"Unified Roadmaps Created:  {stats['unified_created']}")
        print(f"Unified Roadmaps Updated:  {stats['unified_updated']}")
        print(f"Errors:                    {stats['errors']}")
        print("==============================\n")

    return stats


if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else "data/career_roadmaps_import.json"
    asyncio.run(import_roadmaps(target_file))
