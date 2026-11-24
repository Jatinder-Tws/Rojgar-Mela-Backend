"""
Assessment evaluation and question retrieval service.
Delegates to app.modules.jobs_portal.data.assessment_question_bank for offline/fallback questions.
"""

from app.modules.jobs_portal.data.assessment_question_bank import (
    get_curated_question_plan,
    classify_tier,
    classify_domain,
)


def _norm(text) -> str:
    return " ".join(str(text or "").strip().lower().split())


def fallback_question_plan(domain_interest: str, experience_level: str) -> list[dict]:
    """Generates a randomized, level- and domain-tailored 10-question assessment plan."""
    return get_curated_question_plan(domain_interest, experience_level)


# Role-specific career recommendations for evaluation
DOMAIN_CAREER_RECOMMENDATIONS = {
    "tech": [
        "Full Stack & Backend Engineering",
        "Cloud & DevOps Architecture",
        "Systems Engineering & Performance Tuning",
    ],
    "data": [
        "Data Analytics & Business Intelligence",
        "Machine Learning & AI Engineering",
        "Quantitative Data Modeling",
    ],
    "business_sales": [
        "Enterprise B2B Sales & Account Management",
        "Growth Marketing & Demand Generation",
        "Commercial Strategy & Client Success",
    ],
    "finance": [
        "Financial Planning & Analysis (FP&A)",
        "Corporate Treasury & Risk Advisory",
        "Auditing & Financial Compliance",
    ],
    "operations_hr": [
        "Operations Management & Supply Chain",
        "Talent Acquisition & People Operations",
        "Process Optimization & Program Delivery",
    ],
    "general": [
        "Strategic Project Delivery",
        "Operational Problem Solving",
        "Cross-Functional Team Coordination",
    ],
}


def build_assessment_evaluation(history: list | None, experience_level: str, domain_interest: str) -> dict:
    """Evaluates assessment results dynamically based on candidate's answers, domain, and tier."""
    domain = (domain_interest or "your selected field").strip() or "your selected field"
    level = (experience_level or "Fresher / No Experience").strip()
    tier = classify_tier(level)
    domain_key = classify_domain(domain)
    history_items = list(history or [])

    # Score objective questions (IQ & Logic and Aptitude)
    logic_total = 0
    logic_correct = 0
    apt_total = 0
    apt_correct = 0

    for item in history_items:
        cat = item.get("category", "")
        corr = item.get("correct_answer")
        ans = item.get("answer")
        if corr:
            is_right = _norm(ans) == _norm(corr)
            if cat == "IQ & Logic":
                logic_total += 1
                if is_right:
                    logic_correct += 1
            elif cat == "Aptitude":
                apt_total += 1
                if is_right:
                    apt_correct += 1

    # Ratios
    logic_ratio = (logic_correct / logic_total) if logic_total > 0 else 0.75
    apt_ratio = (apt_correct / apt_total) if apt_total > 0 else 0.75

    reasoning_score = round(45 + 50 * logic_ratio)
    aptitude_score = round(45 + 50 * apt_ratio)
    iq_estimate = round(92 + 28 * ((logic_ratio + apt_ratio) / 2))

    # Tier-aligned heuristic traits
    tier_base_eq = {"fresher": 78, "junior": 82, "mid": 86, "senior": 90}
    tier_base_pers = {"fresher": 75, "junior": 80, "mid": 84, "senior": 88}

    emotional_intelligence_score = tier_base_eq.get(tier, 80)
    personality_score = tier_base_pers.get(tier, 78)

    personality_types = {
        "fresher": "Eager Learner & Collaborative Problem Solver",
        "junior": "Action-Oriented & Methodical Builder",
        "mid": "Pragmatic Executor & Strategic Communicator",
        "senior": "Visionary Leader & High-Impact Decision Maker",
    }
    personality_type = personality_types.get(tier, "Analytical & Collaborative Professional")

    # Tailored recommendations
    recommended = list(DOMAIN_CAREER_RECOMMENDATIONS.get(domain_key, DOMAIN_CAREER_RECOMMENDATIONS["general"]))
    if domain not in recommended:
        recommended.insert(0, domain)
    recommended = recommended[:3]

    # Detailed evaluation prose
    p1 = (
        f"You demonstrated solid competencies tailored for {domain} at the {level} tier. "
        f"Your logical reasoning performance scored {reasoning_score}%, reflecting strong deductive thinking, "
        f"while your numerical and situational aptitude achieved {aptitude_score}%."
    )
    p2 = (
        f"Your behavioral responses reveal an aptitude for structured problem-solving under pressure. "
        f"You show a consistent inclination toward proactive communication, risk transparency, "
        f"and collaborative resolution over working in silos."
    )
    if tier in ("senior", "mid"):
        p3 = (
            f"Based on your profile, you are well-positioned for roles requiring architectural ownership, "
            f"cross-functional coordination, and high-impact decision making. Continuing to mentor junior peers "
            f"and aligning operational deliverables with strategic business metrics will further elevate your trajectory."
        )
    else:
        p3 = (
            f"As you advance in {domain}, focus on strengthening domain-specific execution through practical hands-on projects. "
            f"Your positive learning agility and team alignment make you a compelling candidate for fast-track progression."
        )

    detailed_evaluation = f"{p1}\n\n{p2}\n\n{p3}"

    return {
        "personality_type": personality_type,
        "tokens_utilized": 0,
        "iq_estimate": iq_estimate,
        "aptitude_score": aptitude_score,
        "reasoning_score": reasoning_score,
        "emotional_intelligence_score": emotional_intelligence_score,
        "personality_score": personality_score,
        "recommended_domains": recommended,
        "detailed_evaluation": detailed_evaluation,
    }


def questions_for_session(domain_interest: str, experience_level: str) -> list[dict]:
    """Legacy helper maintained for backward compatibility."""
    return fallback_question_plan(domain_interest, experience_level)
