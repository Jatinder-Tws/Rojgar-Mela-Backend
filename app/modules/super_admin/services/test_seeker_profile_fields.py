from types import SimpleNamespace

from app.modules.super_admin.schemas.super_admin import AdminSeekerCreate
from app.modules.super_admin.services.seeker_profile_fields import apply_seeker_profile_fields


def test_create_schema_keeps_profile_lists_and_dedupes_locations():
    body = AdminSeekerCreate(
        first_name="Asha",
        last_name="Kaur",
        email="asha@example.com",
        phone="9876543210",
        industry="IT",
        job_role="Developer",
        preferred_locations=["Mohali", " Mohali ", "Chandigarh"],
        skills=[{"name": "Python", "level": "Intermediate"}],
        headline="  Fresher  ",
    )
    assert body.preferred_locations == ["Mohali", "Chandigarh"]
    assert body.headline == "Fresher"
    assert body.skills[0].name == "Python"


def test_apply_writes_user_and_portfolio_and_clears_empty_lists():
    user = SimpleNamespace(
        preferred_locations=["Old City"],
        gender=None,
        father_or_mother_name=None,
        address=None,
        highest_qualification=None,
        stream_specialization=None,
        college_institute_name=None,
        preferred_job_sector=None,
    )
    portfolio = SimpleNamespace(
        headline=None,
        bio=None,
        date_of_birth=None,
        gender=None,
        city=None,
        state=None,
        linkedin_url=None,
        github_url=None,
        website_url=None,
        current_company=None,
        current_role=None,
        total_experience_years=None,
        skills=[{"name": "Old"}],
        work_experiences=None,
        education=None,
        certifications=None,
        languages=None,
        projects=None,
    )

    apply_seeker_profile_fields(
        user,
        portfolio,
        {
            "preferred_locations": ["Mohali", "Chandigarh"],
            "gender": "Female",
            "headline": "Fresher",
            "city": "Mohali",
            "total_experience_years": 1.5,
            "skills": [],
            "education": [{"institution": "PEC", "degree": "B.Tech"}],
        },
    )

    assert user.preferred_locations == ["Mohali", "Chandigarh"]
    assert user.gender == "Female"
    assert portfolio.gender == "Female"
    assert portfolio.headline == "Fresher"
    assert portfolio.city == "Mohali"
    assert portfolio.total_experience_years == 1.5
    assert portfolio.skills == []
    assert portfolio.education[0]["degree"] == "B.Tech"
    assert portfolio.bio is None


def test_apply_leaves_fields_that_were_not_sent():
    user = SimpleNamespace(gender="Male", preferred_locations=["Pune"])
    portfolio = SimpleNamespace(headline="Keep me", gender="Male")

    apply_seeker_profile_fields(user, portfolio, {"headline": "Updated"})

    assert portfolio.headline == "Updated"
    assert user.gender == "Male"
    assert user.preferred_locations == ["Pune"]
