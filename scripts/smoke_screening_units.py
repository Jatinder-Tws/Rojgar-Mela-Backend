"""Smoke checks for screening matching without pytest."""

from app.modules.jobs_portal.services.screening_skills import (
    match_skills,
    normalize_skill,
    skill_present_in_text,
)
from app.modules.jobs_portal.services.screening_matching import score_candidate_against_jd
from app.modules.jobs_portal.services.screening_report_service import _escape_cell


def main() -> None:
    assert normalize_skill("js") == "JavaScript"
    assert skill_present_in_text("Java", "Experienced with javascript") is False
    assert skill_present_in_text("Java", "Built in Java and Spring") is True
    matched, partial, missing, pref = match_skills(
        ["Python", "Docker"],
        ["AWS"],
        ["Python"],
        "docker compose on AWS",
    )
    assert "Python" in matched
    assert "Docker" in partial
    assert "AWS" in pref
    assert missing == []
    result = score_candidate_against_jd(
        {
            "skills": [{"normalized_name": "Python"}],
            "experience_years": 3,
            "education": [],
            "raw_text_excerpt": "Python backend developer FastAPI",
            "experience": [{"job_title": "Python Developer"}],
            "extraction": {"quality_status": "good"},
        },
        {
            "title": "Python Developer",
            "required_skills": ["Python"],
            "min_experience_years": 2,
            "description": "Python backend engineer role",
        },
    )
    assert result["overall_score"] > 50

    # Unrelated role must not score high on years alone
    mismatch = score_candidate_against_jd(
        {
            "skills": [{"normalized_name": "React"}, {"normalized_name": "TypeScript"}],
            "experience_years": 7,
            "education": [],
            "raw_text_excerpt": "React TypeScript Next.js frontend engineer Agile Azure",
            "experience": [{"job_title": "Frontend Developer"}],
            "extraction": {"quality_status": "good"},
        },
        {
            "title": "ITI diploma Electrical Wiring",
            "required_skills": ["Electrical Wiring", "Mechanical Assembly"],
            "min_experience_years": 4,
            "description": "ITI electrician and mechanical assembly technician",
        },
    )
    assert mismatch["overall_score"] < 35, mismatch["overall_score"]
    assert mismatch["score_breakdown"]["role_note"] == "role_mismatch"

    from app.modules.jobs_portal.services.screening_extraction import detect_non_resume_document

    aadhaar_text = (
        "Enrolment No.: 2309/18354/74902 Sanjay Kumar S/O: Ram Bahadur "
        "Aadhaar no. issued: 12/10/2014 Digitally signed by DS Unique "
        "Identification Authority of India VID : 9179 5238 6743 0324"
    )
    assert detect_non_resume_document(aadhaar_text) == "identity_document"

    id_score = score_candidate_against_jd(
        {
            "skills": [],
            "experience_years": None,
            "education": [],
            "raw_text_excerpt": aadhaar_text,
            "experience": [],
            "extraction": {
                "quality_status": "failed",
                "method": "identity_document",
                "error": "not_a_resume",
                "document_kind": "identity_document",
            },
            "evidence": {"document_kind": "identity_document"},
        },
        {
            "title": "React Developer",
            "required_skills": ["React", "TypeScript"],
            "min_experience_years": 2,
            "description": "Build React apps",
        },
    )
    assert id_score["overall_score"] <= 3, id_score["overall_score"]
    assert "not a resume" in (id_score.get("fit_reason") or "").lower()

    assert _escape_cell("=CMD()") == "'=CMD()"
    print(
        "unit checks passed",
        result["overall_score"],
        "mismatch",
        mismatch["overall_score"],
        "aadhaar",
        id_score["overall_score"],
    )


if __name__ == "__main__":
    main()
