"""Regression: _to_out must not trigger ORM lazy-loads (MissingGreenlet under AsyncSession)."""

from datetime import datetime, timezone
from types import SimpleNamespace

from app.modules.jobs_portal.services.career_roadmap_service import (
    _pick_roadmap_by_slug,
    _to_out,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class LazyBoom(SimpleNamespace):
    """Attribute access on missing names should not be used by _to_out for relations."""

    def __getattribute__(self, name: str):
        if name in {"milestones", "resources"}:
            raise RuntimeError(f"lazy load attempted for {name}")
        return object.__getattribute__(self, name)


def test_to_out_uses_dict_loaded_relations_only():
    resource = SimpleNamespace(
        id="r1",
        title="Intro",
        type="video",
        url="https://example.com",
        platform="YouTube",
    )
    milestone = LazyBoom(
        id="m1",
        title="Basics",
        description="Learn basics",
        estimated_time="1 week",
        difficulty="beginner",
        skills=["python"],
        stage_title="Foundation",
    )
    # Relations only via __dict__ (as after selectinload).
    milestone.__dict__["resources"] = [resource]

    row = LazyBoom(
        id="rm1",
        target_role="Python Developer",
        slug="python-developer",
        category="Technology",
        current_level="Beginner",
        short_description="Learn Python",
        long_description="Full Python path",
        skills_to_develop=["python"],
        estimated_duration="3 months",
        salary_lpa="6-10 LPA",
        openings_count="1000+",
        cover_image_url=None,
        is_published=True,
        is_featured=False,
        is_trending=False,
        sort_order=1,
        created_at=NOW,
        updated_at=NOW,
    )
    row.__dict__["milestones"] = [milestone]

    out = _to_out(row)
    assert out.title == "Python Developer"
    assert out.steps
    assert out.steps[0].sub_steps
    assert out.steps[0].sub_steps[0].resources[0].title == "Intro"


def test_to_out_tolerates_missing_relations():
    row = LazyBoom(
        id="rm2",
        target_role="Data Analyst",
        slug="data-analyst",
        category="Technology",
        current_level="Intermediate",
        short_description=None,
        long_description=None,
        skills_to_develop=[],
        estimated_duration=None,
        salary_lpa=None,
        market_based_salary=None,
        openings_count=None,
        cover_image_url=None,
        is_published=True,
        is_featured=False,
        is_trending=False,
        sort_order=2,
        created_at=NOW,
        updated_at=NOW,
        steps=[],
        resources=[],
        faqs=[],
        insights={},
    )
    # No milestones key in __dict__ — must not call lazy loader.
    out = _to_out(row)
    assert out.title == "Data Analyst"
    assert out.steps == [] or isinstance(out.steps, list)


def test_pick_roadmap_prefers_exact_slug():
    a = SimpleNamespace(slug="full-stack-engineer", target_role="Full Stack Engineer")
    b = SimpleNamespace(slug="full-stack-developer", target_role="Full Stack Developer")
    picked = _pick_roadmap_by_slug(
        [a, b],
        clean_slug="full-stack-developer",
        slug="full-stack-developer",
    )
    assert picked is b


def test_pick_roadmap_falls_back_to_title():
    a = SimpleNamespace(slug="legacy-1", target_role="Other Role")
    b = SimpleNamespace(slug="legacy-2", target_role="Full Stack Developer")
    picked = _pick_roadmap_by_slug(
        [a, b],
        clean_slug="full-stack-developer",
        slug="full-stack-developer",
    )
    assert picked is b


def test_pick_roadmap_null_slug_hyphenated_title():
    """List API invents slugify(title) when DB slug is NULL — detail must resolve it."""
    row = SimpleNamespace(slug=None, target_role="Relationship Manager - Retail Banking")
    picked = _pick_roadmap_by_slug(
        [row],
        clean_slug="relationship-manager-retail-banking",
        slug="relationship-manager-retail-banking",
    )
    assert picked is row
