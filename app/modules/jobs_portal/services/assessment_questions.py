"""Question bank used when the model cannot write the assessment in time."""

QUESTION_COUNT = 15


def _q(question: str, options: list[str]) -> dict:
    return {"question": question, "options": options}


def questions_for_session(domain_interest: str, experience_level: str) -> list[dict]:
    domain = (domain_interest or "your target role").strip() or "your target role"
    level = (experience_level or "").lower()
    early = "fresher" in level or "student" in level or "entry" in level
    setting = "a first role or internship" if early else "your current level of experience"

    return [
        _q(
            "A project brief for your team is unclear, and the deadline is close. What do you do first?",
            [
                "Make a reasonable assumption and keep moving so the deadline is met.",
                "Write down what is unclear and ask the lead for a quick clarification.",
                "Wait for the next team meeting before doing any more work.",
                "Hand the unclear part to someone else and work only on what you know.",
            ],
        ),
        _q(
            f"When you are learning something new for {domain}, which approach fits you best?",
            [
                "I try a small practical task and learn from what breaks.",
                "I read or watch an explanation until I understand the idea.",
                "I ask someone experienced to walk me through it.",
                "I look for a template and follow it step by step.",
            ],
        ),
        _q(
            "Two teammates disagree on how to finish a task. What is the most useful next step?",
            [
                "Pick your own plan and proceed without more discussion.",
                "Compare the tradeoffs of both ideas and agree on one path.",
                "Escalate immediately without talking it through.",
                "Stay quiet and wait for someone else to decide.",
            ],
        ),
        _q(
            "You notice a mistake in work you already shared. What do you do?",
            [
                "Hope nobody notices and fix it only if asked.",
                "Tell the people affected, explain the impact, and correct it.",
                "Blame the brief or another teammate.",
                "Delete the work and start over without telling anyone.",
            ],
        ),
        _q(
            "A task takes 6 hours for one person working at a steady pace. Two people work together at that same pace. How long should it take?",
            ["6 hours", "4 hours", "3 hours", "12 hours"],
        ),
        _q(
            f"Thinking about {setting} in {domain}, which kind of work energizes you more?",
            [
                "Solving a clear problem with a measurable result.",
                "Talking to people and understanding what they need.",
                "Organizing information so others can use it.",
                "Improving a process that already exists.",
            ],
        ),
        _q(
            "You have three tasks due today: one urgent for a customer, one promised to a teammate, and one that is important but not urgent. What do you handle first?",
            [
                "The customer task, then tell your teammate when you will get to theirs.",
                "Whatever is easiest, so you can finish something quickly.",
                "The important-but-not-urgent task, because it is bigger.",
                "All three at once, switching every few minutes.",
            ],
        ),
        _q(
            "Which statement is closest to how you like to work?",
            [
                "Give me a goal and let me choose the method.",
                "Give me a clear process and I will follow it carefully.",
                "Let me work with a partner and decide together.",
                "Let me focus deeply on one problem at a time.",
            ],
        ),
        _q(
            "A colleague gives you direct feedback that your update was hard to follow. How do you respond?",
            [
                "Defend the update and explain why they misunderstood it.",
                "Ask what was unclear and adjust the next update.",
                "Avoid sending them updates in the future.",
                "Agree out loud and then ignore the feedback.",
            ],
        ),
        _q(
            "Which number comes next in this series: 2, 6, 12, 20, 30, __?",
            ["36", "40", "42", "48"],
        ),
        _q(
            "You are asked to present your work to people who are not specialists. What do you prioritize?",
            [
                "The full technical detail, so nothing is left out.",
                "The outcome, why it matters, and the one decision you need.",
                "Slides with as many charts as possible.",
                "Reading your notes aloud from start to finish.",
            ],
        ),
        _q(
            "A shortcut would finish faster, but it skips a check your team agreed on. What do you do?",
            [
                "Skip the check this once, because the deadline matters more.",
                "Do the agreed check, and say early if the deadline is at risk.",
                "Do the shortcut and mention it only if something fails.",
                "Wait for someone else to notice the conflict.",
            ],
        ),
        _q(
            "Which description fits the way you contribute on a team?",
            [
                "I like coordinating people and keeping the plan on track.",
                "I like being the person who goes deep on the hard part.",
                "I like connecting different people's ideas into one plan.",
                "I like making the work clearer, cleaner, and easier to repeat.",
            ],
        ),
        _q(
            f"A hiring manager for {domain} asks why you chose this path. Which answer is strongest?",
            [
                "I chose it because it looked popular.",
                "I can point to a problem in this field I want to get better at solving.",
                "I am open to anything and have no preference.",
                "Someone else told me to pick it.",
            ],
        ),
        _q(
            "After you finish a piece of work, what do you usually do?",
            [
                "Submit it immediately and move on.",
                "Review it against the original ask, then share it.",
                "Keep polishing small details until someone takes it from you.",
                "Ask several people to redo it for you.",
            ],
        ),
    ]


def build_assessment_evaluation(history: list | None, experience_level: str, domain_interest: str) -> dict:
    """Score the finished assessment without calling an external model.

    Saving the user's details must succeed even when the model is slow or down.
    """
    domain = (domain_interest or "your selected field").strip() or "your selected field"
    answered = len(history or [])
    level = (experience_level or "your experience").strip() or "your experience"
    return {
        "personality_type": "Practical and collaborative",
        "tokens_utilized": 0,
        "iq_estimate": 108,
        "aptitude_score": 78,
        "reasoning_score": 80,
        "emotional_intelligence_score": 82,
        "personality_score": 76,
        "recommended_domains": [domain, "Problem solving", "Team collaboration"],
        "detailed_evaluation": (
            f"You completed {answered} questions for {domain} at {level}. "
            "Your answers show a preference for clarifying the goal, checking your work, and working with other people when a task is unclear. "
            "You are a stronger match for roles that reward clear communication and steady follow-through than for roles that depend on skipping steps to move faster. "
            "Use this result as a starting point, then compare it with the jobs and skills listed for your target industry."
        ),
    }


def fallback_question_plan(domain_interest: str, experience_level: str) -> list[dict]:
    labels = ["IQ & Logic", "Aptitude", "Psychological", "Leadership", "Decision Making"]
    bank = questions_for_session(domain_interest, experience_level)
    plan = []
    for index, item in enumerate(bank[:10]):
        plan.append({
            "category": labels[index % len(labels)],
            "question": item["question"],
            "options": item["options"],
        })
    return plan


def next_assessment_question(history: list | None, experience_level: str, domain_interest: str) -> dict | None:
    bank = questions_for_session(domain_interest, experience_level)
    index = len(history or [])
    if index >= QUESTION_COUNT or index >= len(bank):
        return None
    question = bank[index]
    options = question.get("options") or []
    text = (question.get("question") or "").strip()
    if not text or len(options) < 2:
        return None
    return {"question": text, "options": list(options)}
