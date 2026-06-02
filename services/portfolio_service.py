from models.user import User
from models.portfolio import Portfolio

def calculate_completion(portfolio: Portfolio, user: User) -> tuple[int, list[str], list[str]]:
    """Calculate portfolio completion percentage and list filled/missing sections."""
    sections = {
        "Personal Details": bool(user.first_name and user.last_name and user.email),
        "Headline": bool(portfolio.headline),
        "Bio / About Me": bool(portfolio.bio),
        "Location": bool(portfolio.city or portfolio.state),
        "Skills": bool(portfolio.skills and len(portfolio.skills) > 0),
        "Work Experience": bool(portfolio.work_experiences and len(portfolio.work_experiences) > 0),
        "Education": bool(portfolio.education and len(portfolio.education) > 0),
        "Social Links": bool(portfolio.linkedin_url or portfolio.github_url or portfolio.website_url),
        "Certifications": bool(portfolio.certifications and len(portfolio.certifications) > 0),
        "Languages": bool(portfolio.languages and len(portfolio.languages) > 0),
        "Projects": bool(portfolio.projects and len(portfolio.projects) > 0),
        "Intro Video / Audio": bool(portfolio.intro_video_path or portfolio.intro_audio_path),
        "AI Assessment": bool(user.is_assessment_done),
    }
    filled = [k for k, v in sections.items() if v]
    missing = [k for k, v in sections.items() if not v]
    pct = int((len(filled) / len(sections)) * 100) if sections else 0
    return pct, filled, missing
