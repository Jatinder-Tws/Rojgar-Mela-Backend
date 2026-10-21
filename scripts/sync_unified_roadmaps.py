import asyncio
import re
import uuid
import app.main  # registers all models
from app.core.database import AsyncSessionLocal
from sqlalchemy import text, select
from app.shared.models.user import User
from app.modules.jobs_portal.models.roadmap import (
    Roadmap,
    Milestone,
    Resource,
    DifficultyLevel,
    ResourceType,
    MilestoneStatus,
)
from app.modules.jobs_portal.models.career_roadmap import CareerRoadmap


def slugify(text: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9]+', '-', text).strip('-').lower()
    return s or 'roadmap'


async def sync():
    async with AsyncSessionLocal() as session:
        # 1. Backfill slugs and master flags on existing roadmaps
        existing_rms = (await session.execute(select(Roadmap))).scalars().all()
        for rm in existing_rms:
            if not rm.slug:
                rm.slug = slugify(rm.target_role)
            rm.is_published = True
        await session.commit()
        print(f"Backfilled {len(existing_rms)} existing roadmaps with slugs")

        # 2. Get existing roadmap slugs/roles
        existing_roles = {rm.target_role.strip().lower() for rm in existing_rms}
        existing_slugs = {rm.slug for rm in existing_rms if rm.slug}

        # 3. Pull all career_roadmaps
        crs = (await session.execute(select(CareerRoadmap))).scalars().all()
        migrated = 0
        for cr in crs:
            role_key = cr.title.strip().lower()
            slug_key = cr.slug or slugify(cr.title)
            if role_key in existing_roles or slug_key in existing_slugs:
                continue

            # Create master roadmap in roadmaps table
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

            # Create milestones & resources from steps
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

                    # Add resources
                    sub_res = sub.get("resources") or []
                    if not sub_res:
                        primary_skill = sub_skills[0] if sub_skills else sub_title
                        query_encoded = primary_skill.replace(" ", "+")
                        sub_res = [
                            {
                                "title": f"{primary_skill} Documentation & Guide",
                                "type": "article",
                                "url": f"https://developer.mozilla.org/en-US/search?q={query_encoded}",
                                "platform": "MDN / Official Docs",
                            },
                            {
                                "title": f"{primary_skill} Masterclass & Tutorial",
                                "type": "video",
                                "url": f"https://www.youtube.com/results?search_query={query_encoded}+tutorial",
                                "platform": "YouTube",
                            },
                        ]

                    for r_data in sub_res:
                        res = Resource(
                            id=str(uuid.uuid4()),
                            milestone_id=m.id,
                            title=r_data.get("title") or f"{sub_title} Resource",
                            type=ResourceType.article if r_data.get("type") == "article" else ResourceType.video,
                            url=r_data.get("url") or "https://www.youtube.com",
                            platform=r_data.get("platform") or "Learning Platform",
                            duration=r_data.get("duration") or "1-2 hours",
                            difficulty=DifficultyLevel.intermediate,
                        )
                        session.add(res)

                    order += 1

            existing_roles.add(role_key)
            existing_slugs.add(slug_key)
            migrated += 1

        await session.commit()
        print(f"Successfully migrated {migrated} roadmaps into unified roadmaps table!")


if __name__ == "__main__":
    asyncio.run(sync())
