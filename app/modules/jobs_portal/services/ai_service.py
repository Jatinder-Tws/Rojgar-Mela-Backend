"""
AI Service – modular adapter pattern.
Swap OpenAI for any custom model by implementing AIProvider protocol.
GPT calls are batched to minimize API hits and token usage.
"""

from __future__ import annotations
import asyncio
import json
import logging
import random
import re
import uuid

from typing import List, Optional, Protocol, runtime_checkable

from openai import AsyncOpenAI
import google.genai as genai
from app.core.config import settings
from app.shared.services.gemini_resilient import GeminiServiceUnavailable, generate_content_resilient

logger = logging.getLogger(__name__)


@runtime_checkable
class AIProvider(Protocol):
    async def embed(self, text: str) -> List[float]: ...
    async def chat_completion(self, system: str, user: str, temperature: float | None = None) -> str: ...
    async def chat_completion_with_usage(
        self, system: str, user: str, temperature: float | None = None
    ) -> tuple[str, int]: ...


DEFAULT_TEMPERATURE = 0.2


class GeminiAdapter:
    """Google Gemini adapter for embeddings and chat completion."""

    def __init__(self):
        self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    async def embed(self, text: str) -> List[float]:
        text = text[:6000]
        response = self._client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=text,
        )
        return response.embeddings[0].values

    async def chat_completion(self, system: str, user: str, temperature: float | None = None) -> str:
        text, _ = await self.chat_completion_with_usage(system, user, temperature)
        return text

    async def chat_completion_with_usage(
        self, system: str, user: str, temperature: float | None = None
    ) -> tuple[str, int]:
        combined_prompt = f"{system}\n\n{user}"
        response = await generate_content_resilient(
            [combined_prompt],
            config={
                "temperature": DEFAULT_TEMPERATURE if temperature is None else temperature,
                "max_output_tokens": 8192,
                "response_mime_type": "application/json",
            },
        )
        tokens = 0
        if response.usage_metadata:
            tokens = response.usage_metadata.total_token_count or 0
        return (response.text or ""), tokens


class OpenAIAdapter:
    """OpenAI adapter – text-embedding-3-small for embeddings, gpt-4o for ranking."""

    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def embed(self, text: str) -> List[float]:
        # Truncate to safe token count (~6k chars ≈ ~1500 tokens)
        text = text[:6000]
        response = await self._client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text,
        )
        return response.data[0].embedding

    async def chat_completion(self, system: str, user: str, temperature: float | None = None) -> str:
        text, _ = await self.chat_completion_with_usage(system, user, temperature)
        return text

    async def chat_completion_with_usage(
        self, system: str, user: str, temperature: float | None = None
    ) -> tuple[str, int]:
        response = await self._client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=DEFAULT_TEMPERATURE if temperature is None else temperature,
            max_tokens=8192,
            response_format={"type": "json_object"},
        )
        tokens = 0
        if response.usage:
            tokens = response.usage.total_tokens
        return (response.choices[0].message.content or ""), tokens


class HybridAIAdapter:
    """Hybrid adapter that prefers Gemini, falls back to OpenAI on failure."""

    def __init__(self):
        self._gemini = GeminiAdapter()
        self._openai = OpenAIAdapter()

    async def embed(self, text: str) -> List[float]:
        try:
            return await self._gemini.embed(text)
        except Exception:
            # Fallback to OpenAI
            return await self._openai.embed(text)

    async def chat_completion(self, system: str, user: str, temperature: float | None = None) -> str:
        try:
            return await self._gemini.chat_completion(system, user, temperature)
        except Exception:
            # Fallback to OpenAI
            return await self._openai.chat_completion(system, user, temperature)

    async def chat_completion_with_usage(
        self, system: str, user: str, temperature: float | None = None
    ) -> tuple[str, int]:
        try:
            return await self._gemini.chat_completion_with_usage(system, user, temperature)
        except Exception as e:
            logger.warning("Gemini failed, falling back to OpenAI: %s", e)
            return await self._openai.chat_completion_with_usage(system, user, temperature)


def get_default_questions(domain_interest: str) -> List[dict]:
    # Professional defaults tailored by domain
    domain = (domain_interest or "").lower()
    if any(k in domain for k in ["software", "tech", "comput", "develop", "program"]):
        return [
            {
                "question": "Which of the following data structures operates on a Last-In, First-Out (LIFO) basis?",
                "options": ["Queue", "Stack", "Singly Linked List", "Binary Search Tree"]
            },
            {
                "question": "In Object-Oriented Programming, what is the process of wrapping code and data together into a single unit called?",
                "options": ["Inheritance", "Polymorphism", "Encapsulation", "Abstraction"]
            }
        ]
    elif any(k in domain for k in ["data", "analy", "science"]):
        return [
            {
                "question": "In statistics and machine learning, what does 'overfitting' refer to?",
                "options": [
                    "A model that performs poorly on both training and unseen test data.",
                    "A model that learns the training data too well, including noise, and performs poorly on unseen test data.",
                    "A model that has too few parameters to capture the underlying pattern of the data.",
                    "A model that is trained on an extremely large dataset."
                ]
            },
            {
                "question": "Which SQL clause is used to filter the results of a GROUP BY query based on an aggregate condition?",
                "options": ["WHERE", "HAVING", "ORDER BY", "FILTER"]
            }
        ]
    elif any(k in domain for k in ["marketing", "business", "sales"]):
        return [
            {
                "question": "What does the marketing metric 'CAC' stand for?",
                "options": [
                    "Customer Acquisition Cost",
                    "Customer Lifetime Value",
                    "Click‑Through Rate",
                    "Cohort Analysis Cycle"
                ]
            },
            {
                "question": "Which of the following best describes the concept of a 'Value Proposition'?",
                "options": [
                    "The price point at which a product is sold.",
                    "The summary of why a consumer should buy a product or service.",
                    "A discount code offered to repeat buyers.",
                    "The total cost to manufacture a product."
                ]
            }
        ]
    # Default high-quality general aptitude/reasoning/situational questions
    return [
        {
            "question": "A team has a task that takes 6 hours to complete for one person. If two people work together at the same constant rate, how many hours will it take?",
            "options": ["3 hours", "4 hours", "6 hours", "1.5 hours"]
        },
        {
            "question": "Which of the following is the most effective way to resolve a disagreement with a team member on a project approach?",
            "options": [
                "Ignore the disagreement and proceed with your own plan.",
                "Discuss the pros and cons of both approaches calmly and seek common ground or guidance.",
                "Escalate the issue immediately to the department head without talking to the teammate.",
                "Wait for the other person to concede their point."
            ]
        }
    ]


class MockAIAdapter:
    """Mock adapter for local dev – no API calls."""

    async def embed(self, text: str) -> List[float]:
        import hashlib, struct

        h = hashlib.sha256(text.encode()).digest()
        # Produce deterministic 1536-dim vector from hash (repeated)
        base = [struct.unpack("f", h[i % 32 : i % 32 + 4])[0] for i in range(1536)]
        magnitude = sum(v**2 for v in base) ** 0.5 or 1.0
        return [v / magnitude for v in base]

    async def chat_completion(self, system: str, user: str, temperature: float | None = None) -> str:
        # If the request is for assessment evaluation
        if "personality_type" in system or "evaluate" in system.lower():
            return json.dumps({
                "personality_type": "Analytical/Balanced",
                "iq_estimate": 110,
                "aptitude_score": 85,
                "reasoning_score": 88,
                "emotional_intelligence_score": 90,
                "personality_score": 82,
                "recommended_domains": ["Software Engineering", "System Architecture", "Web Development"],
                "detailed_evaluation": "The candidate demonstrates clear logical thinking and structured problem‑solving. Answers show strong fundamental knowledge and pragmatic team collaboration mindset."
            })

        # Try to extract domain interest from system or user prompt
        domain = ""
        match = re.search(r"interested in the '([^']+)' domain", system)
        if match:
            domain = match.group(1)

        return json.dumps(get_default_questions(domain))

    async def chat_completion_with_usage(
        self, system: str, user: str, temperature: float | None = None
    ) -> tuple[str, int]:
        text = await self.chat_completion(system, user, temperature)
        return text, 100


def get_ai_provider() -> AIProvider:
    mode = settings.AI_MODE
    if mode == "mock":
        return MockAIAdapter()
    if settings.GOOGLE_API_KEY and settings.OPENAI_API_KEY:
        return HybridAIAdapter()
    if settings.GOOGLE_API_KEY:
        return GeminiAdapter()
    if settings.OPENAI_API_KEY:
        return OpenAIAdapter()
    return MockAIAdapter()


# Singleton
_ai_provider: Optional[AIProvider] = None


def get_ai() -> AIProvider:
    global _ai_provider
    if _ai_provider is None:
        _ai_provider = get_ai_provider()
    return _ai_provider


async def generate_next_assessment_question(
    history: List[dict], experience_level: str, domain_interest: str
) -> tuple[List[dict], int]:
    ai = get_ai()

    print(ai)
    # Determine focus based on experience level and domain interest
    if domain_interest == "Career Discovery":
        focus = (
            "Focus on social orientation, work style, creative expression, analytical thinking, learning agility, and situational collaboration scenario questions. "
            "Assess their core interests, workplace values, and cognitive problem-solving approaches to help determine suitable domains. "
            "Do NOT ask highly technical interview questions."
        )
    elif ("Student" in experience_level or "Fresher" in experience_level or "Entry" in experience_level):
        focus = (
            f"Focus on assessing basic {domain_interest} concepts, general analytical reasoning, and practical situational team dynamics. "
            "Avoid advanced architecture or deep technical tools, but do NOT ask childish logical puzzles or simple math riddles. "
            "Keep the questions professional, engaging, and relevant to an entry-level candidate in this field."
        )
    else:
        focus = (
            f"Focus strictly on advanced {domain_interest} concepts, system design, architectural decisions, and in-depth domain knowledge appropriate for their experience level."
        )
    # Build system prompt without raw JSON braces to avoid f-string formatting issues
    json_schema = '[ {"question": "The question text here", "options": ["Option A", "Option B", "Option C", "Option D"]}, {"question": "Second question", "options": ["Option A", "Option B", "Option C", "Option D"]} ]'
    system_prompt = f"""
    You are an expert technical interviewer and career counselor.
    The candidate has an experience level of '{experience_level}' and is interested in the '{domain_interest}' domain.
    {focus}
    Based on the previous conversation history, generate TWO QUESTIONS to assess their fit.
    ALL questions must be Multiple Choice Questions (MCQs) with exactly 4 options each.
    Ensure questions progressively adapt based on their previous answers.

    Return the response ONLY as a valid JSON array where each element is an object with keys "question" (string) and "options" (list of four strings).
    {json_schema}
    """

    history_text = "\n".join(
        [
            f"Q: {item.get('question_text', item.get('question', ''))}\nA: {item.get('answer', '')}"
            for item in history
        ]
    )
    user_prompt = f"History:\n{history_text}\n\nGenerate the next two questions as JSON."

    try:
        response, tokens = await ai.chat_completion_with_usage(system_prompt, user_prompt)
        # Clean up markdown if included
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        data = json.loads(response.strip())
        # Ensure we have exactly two questions; if not, pad with defaults
        if not isinstance(data, list) or len(data) < 2:
            data = get_default_questions(domain_interest)
        return data, tokens
    except Exception as e:
        print(f"Error generating question: {e}")
        return get_default_questions(domain_interest), 0


async def generate_assessment_evaluation(
    history: List[dict], experience_level: str, domain_interest: str
) -> dict:
    ai = get_ai()
    system_prompt = f"""
    You are an expert HR evaluator and strict technical assessor.
    Review the candidate's interview history. The candidate's experience is '{experience_level}' and domain interest is '{domain_interest}'.
    Based strictly on the accuracy, depth, and logic of their answers, analyze the following:
    1. Personality type (e.g., Analytical, Creative, Pragmatic, Leadership-oriented, Detail-Oriented, etc.)
    2. Estimated IQ score (an integer between 85 and 140). BE HARSH AND REALISTIC. Average answers should score around 95-105. Good answers 105-115. Only truly exceptional answers with deep reasoning should score 120+. If answers are short, incorrect, or generic, score below 100. Do not default to high scores like 125.
    3. Aptitude score (1-100) assessing logical reasoning and problem‑solving ability.
    4. Reasoning score (1-100) assessing the quality of argumentation and critical thinking.
    5. Emotional intelligence score (1-100) assessing self‑awareness, empathy and situational judgement.
    6. Personality score (1-100) overall assessment of traits alignment with the role.
    7. Recommended specific job domains/roles they would excel in (list of 3 strings). Be specific to their actual demonstrated skills.
    8. A detailed 2‑3 paragraph evaluation of their strengths, weaknesses, and overall fit. Be highly critical. Explicitly point out any incorrect answers, shallow responses, or generic guesses. Do not flatter the candidate.
    
    Return the response ONLY as a valid JSON object matching this schema exactly:
    {{
      "personality_type": "string",
      "iq_estimate": int,
      "aptitude_score": int,
      "reasoning_score": int,
      "emotional_intelligence_score": int,
      "personality_score": int,
      "recommended_domains": ["string", "string", "string"],
      "detailed_evaluation": "string"
    }}
    """

    history_text = "\n".join(
        [
            f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}"
            for item in history
        ]
    )
    user_prompt = f"History:\n{history_text}\n\nEvaluate the candidate."

    try:
        response, tokens = await ai.chat_completion_with_usage(system_prompt, user_prompt)

        # Clean up in case markdown formatting is included
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        data = json.loads(response.strip())
        return {
            "personality_type": data.get("personality_type", "Unknown"),
            "tokens_utilized": tokens,
            "iq_estimate": data.get("iq_estimate", 100),
            "aptitude_score": data.get("aptitude_score"),
            "reasoning_score": data.get("reasoning_score"),
            "emotional_intelligence_score": data.get("emotional_intelligence_score"),
            "personality_score": data.get("personality_score"),
            "recommended_domains": data.get("recommended_domains", [domain_interest]),
            "detailed_evaluation": data.get(
                "detailed_evaluation", "Evaluation generated based on your answers."
            ),
        }
    except Exception as e:
        print(f"Error generating evaluation: {e}")
        return {
            "personality_type": "Analytical/Balanced",
            "tokens_utilized": 0,
            "iq_estimate": 105,
            "aptitude_score": None,
            "reasoning_score": None,
            "emotional_intelligence_score": None,
            "personality_score": None,
            "recommended_domains": [domain_interest, "General Tech"],
            "detailed_evaluation": "Based on the input provided, you show a balanced capability matching your selected domain.",
        }


def _strip_json_fence(response: str) -> str:
    text = (response or "").strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _question_items(data) -> list:
    if isinstance(data, dict):
        for key in ("questions", "items", "assessment"):
            if isinstance(data.get(key), list):
                return data[key]
        return []
    return data if isinstance(data, list) else []


# ---------- Difficulty control ----------
DIFFICULTY_RULES = {
    "fresher": (
        "VERY EASY. Written for a fresh graduate with zero work experience. "
        "Use everyday college/home/team situations. IQ & Logic and Aptitude must be "
        "simple (basic number series, simple percentage, odd-one-out, easy pattern or "
        "common-sense reasoning) solvable in under 20 seconds. No jargon."
    ),
    "junior": (
        "EASY. For someone with 1-3 years of experience. Simple workplace situations. "
        "Logic/aptitude should be basic and solvable in under 30 seconds."
    ),
    "mid": (
        "EASY TO MEDIUM. For someone with 3-7 years of experience. Realistic but "
        "short workplace situations. Logic/aptitude solvable in under 40 seconds."
    ),
    "senior": (
        "MEDIUM. For someone with 7+ years of experience. Realistic workplace "
        "situations, but still short and clear. Never puzzle-style or tricky."
    ),
}


def _difficulty_key(level: str) -> str:
    l = (level or "").lower()
    if any(k in l for k in ("student", "fresher", "entry", "no experience", "intern")):
        return "fresher"
    if any(k in l for k in ("senior", "lead", "manager", "head")):
        return "senior"
    nums = [int(n) for n in re.findall(r"\d+", l)]
    if nums:
        lo = min(nums)
        if lo == 0:
            return "fresher"
        if lo <= 2:
            return "junior"
        if lo <= 6:
            return "mid"
        return "senior"
    if "mid" in l:
        return "mid"
    if "junior" in l:
        return "junior"
    return "fresher"  # safe default = easiest


# ---------- Variety control ----------
CATEGORY_FOCUS_POOL = {
    "IQ & Logic": [
        "number series", "odd one out", "simple percentage or ratio", "letter/word pattern",
        "simple direction or ranking puzzle", "basic cause-and-effect reasoning",
        "simple calendar/time calculation", "common-sense deduction",
    ],
    "Aptitude": [
        "basic arithmetic in a work context", "reading a tiny table or schedule",
        "prioritising 3 small tasks", "estimating time or quantity",
        "spotting a simple mistake in a short statement", "basic verbal reasoning",
    ],
    "Psychological": [
        "handling stress or pressure", "reaction to criticism", "working alone vs in a team",
        "dealing with a boring or repetitive task", "handling a change of plan",
        "staying motivated after a failure", "meeting new people",
    ],
    "Leadership": [
        "a teammate not doing their work", "taking initiative without being asked",
        "helping a new joiner", "a conflict between two colleagues",
        "owning a mistake", "motivating a tired team", "sharing credit",
    ],
    "Decision Making": [
        "two tasks due at the same time", "a small ethical choice at work",
        "limited information, quick decision needed", "choosing between speed and quality",
        "asking for help vs figuring it out", "a customer or manager asking for something unrealistic",
    ],
}

CATEGORY_ORDER = [
    "IQ & Logic", "Aptitude", "Psychological", "Leadership", "Decision Making",
    "IQ & Logic", "Aptitude", "Psychological", "Leadership", "Decision Making",
]
OBJECTIVE_CATEGORIES = ("IQ & Logic", "Aptitude")


def _build_focus_plan() -> str:
    """Pick a different sub-topic per slot so each test differs, with no repeats inside one test."""
    used: dict[str, set] = {}
    lines = []
    for i, cat in enumerate(CATEGORY_ORDER, start=1):
        pool = [f for f in CATEGORY_FOCUS_POOL[cat] if f not in used.get(cat, set())]
        focus = random.choice(pool)
        used.setdefault(cat, set()).add(focus)
        lines.append(f"Q{i} - {cat}: focus on '{focus}'")
    return "\n".join(lines)


def public_questions(questions: list[dict]) -> list[dict]:
    """Frontend ko bhejne se pehle call karo: correct_answer hata deta hai."""
    return [{k: v for k, v in q.items() if k != "correct_answer"} for q in questions]


async def generate_career_question_set(
    experience_level: str,
    domain_interest: str,
    avoid_questions: list[str] | None = None,
) -> tuple[list[dict], int]:
    """One model call for the whole test: easy, short, different every attempt.

    IQ & Logic / Aptitude items carry a server-side 'correct_answer'.
    Use public_questions() before sending to the frontend.
    """
    from app.modules.jobs_portal.services.assessment_questions import fallback_question_plan

    ai = get_ai()
    domain = (
        "a career of their choice"
        if (domain_interest or "") in ("", "Career Discovery")
        else domain_interest
    )
    level = experience_level or "Fresher / No Experience"
    difficulty = DIFFICULTY_RULES[_difficulty_key(level)]
    focus_plan = _build_focus_plan()
    seed = uuid.uuid4().hex[:8]

    avoid_block = ""
    if avoid_questions:
        recent = "\n".join(f"- {q[:120]}" for q in avoid_questions[:20])
        avoid_block = (
            "\nThe person has already seen these questions. Do NOT repeat them or "
            f"write close variations:\n{recent}\n"
        )

    system_prompt = f"""
    You are a friendly career counsellor writing a SHORT, EASY multiple-choice assessment.
    The person is '{level}' and wants to work in '{domain}'.

    DIFFICULTY: {difficulty}
    This is NOT an interview or an IQ exam. Nobody should feel stuck. If in doubt, make it easier.

    Write exactly 10 questions in this exact order, using these focus areas:
    {focus_plan}

    Hard rules:
    - Each question: ONE short, punchy sentence, maximum 12-14 words. Fast to read in 8 seconds.
    - Each option: maximum 4-6 words. Exactly 4 options per question. Concise and clear.
    - IQ & Logic and Aptitude: exactly one clearly correct answer, no trick options.
      For these two categories also include "correct_index" (0-3): the position of the correct option.
      Double-check the answer is truly correct. Do not include "correct_index" for other categories.
    - Psychological, Leadership, Decision Making: all 4 options should be reasonable
      work styles (no obviously wrong answer), so they reveal personality.
    - Situations should feel relevant to '{domain}' but need NO technical or
      domain knowledge. Logic and aptitude questions may be general.
    - No long stories, no multi-step calculations, no jargon, no interview trivia.
    - Be creative and unusual: use different names, settings and numbers than the
      most obvious examples. Variation seed: {seed}
    {avoid_block}
    Return ONLY a JSON object: {{"questions": [ ... ]}}.
    Each item has "category", "question", "options" (and "correct_index" where required).
    """
    user_prompt = f"Write the 10 questions now. Keep them short and easy. (seed {seed})"

    try:
        response, tokens = await asyncio.wait_for(
            ai.chat_completion_with_usage(system_prompt, user_prompt, temperature=0.9),
            timeout=35,
        )
        data = json.loads(_strip_json_fence(response))
        cleaned: list[dict] = []
        for item in _question_items(data):
            if len(cleaned) >= 10:
                break
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or "").strip()
            raw_opts = item.get("options") or []
            options = [str(o).strip() for o in raw_opts if str(o).strip()]
            if not question or len(options) < 4:
                continue
            options = options[:4]

            # Category: model ki value valid ho to wahi, warna position se
            category = str(item.get("category") or "").strip()
            if category not in CATEGORY_FOCUS_POOL:
                category = CATEGORY_ORDER[len(cleaned)]

            entry = {"category": category, "question": question, "options": options}

            if category in OBJECTIVE_CATEGORIES:
                ci = item.get("correct_index")
                if isinstance(ci, int) and not isinstance(ci, bool) and 0 <= ci < 4:
                    correct_text = options[ci]
                    shuffled = options[:]
                    random.shuffle(shuffled)  # LLM aksar sahi answer pehle/doosre option mein rakhta hai
                    entry["options"] = shuffled
                    entry["correct_answer"] = correct_text
            cleaned.append(entry)

        if len(cleaned) < 8:
            logger.warning("Assessment generation returned only %d valid questions; using fallback", len(cleaned))
            return fallback_question_plan(domain_interest, experience_level), 0
        return cleaned[:10], tokens
    except Exception as e:
        logger.warning("Error generating assessment questions: %s", e)
        return fallback_question_plan(domain_interest, experience_level), 0


# ---------- Evaluation ----------
def _norm(text) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _objective_scores(history: list) -> dict:
    def tally(cat: str) -> tuple[int, int]:
        items = [h for h in history if h.get("category") == cat and h.get("correct_answer")]
        right = sum(1 for h in items if _norm(h.get("answer")) == _norm(h["correct_answer"]))
        return right, len(items)

    return {"logic": tally("IQ & Logic"), "aptitude": tally("Aptitude")}


def _ratio_to_score(right: int, total: int, default: int = 60) -> int:
    if total == 0:
        return default
    return round(35 + 65 * right / total)  # 0% -> 35, 100% -> 100


def _iq_from_ratio(right: int, total: int) -> int:
    if total == 0:
        return 100
    return round(88 + 32 * right / total)  # 88 to 120


async def generate_career_evaluation(history: list, experience_level: str, domain_interest: str) -> dict:
    """Objective scores computed in code; the model writes personality, roles and advice.

    history items need: category, question, options, answer, correct_answer (for IQ/Aptitude).
    Raises on failure so the caller can use a local fallback.
    """
    ai = get_ai()
    domain = domain_interest or "their chosen field"
    level = experience_level or "their experience"

    obj = _objective_scores(history or [])
    logic_r, logic_t = obj["logic"]
    apt_r, apt_t = obj["aptitude"]
    reasoning_score = _ratio_to_score(logic_r, logic_t)
    aptitude_score = _ratio_to_score(apt_r, apt_t)
    iq_estimate = _iq_from_ratio(logic_r + apt_r, logic_t + apt_t)

    system_prompt = f"""
    You are a supportive career counselor. The person is '{level}' and chose '{domain}'.
    Read their answers to the work-style questions (Psychological, Leadership, Decision Making).
    Objective result already computed: logic {logic_r}/{logic_t} correct, aptitude {apt_r}/{apt_t} correct.
    Do NOT recompute these. Mention them only when talking about strengths or areas to improve.

    Scoring rules:
    - emotional_intelligence_score (1-100): from how they handle people, stress and feedback
      in the Psychological and Leadership answers. Typical range 45-90. Use the full range, avoid 70 by default.
    - personality_score (1-100): how well their work style matches the day-to-day of '{domain}'.
      Typical range 45-90.
    - Scores must reflect the actual choices. Two people with different answers must get different scores.

    Other rules:
    - personality_type: a short, positive label (2-3 words) based on their dominant style.
    - recommended_domains: 3 specific job roles in or close to '{domain}', suitable for a '{level}' person.
      Entry-level roles for freshers, never senior titles.
    - career_roadmap: 4 concrete, practical steps (skills, courses, projects) for '{level}' in '{domain}'.
    - detailed_evaluation: 3 short paragraphs in simple English: their work style, why they fit the first role,
      what to improve. Encouraging but honest. Never claim a medical or psychological diagnosis.

    Return ONLY JSON:
    {{
      "personality_type": "string",
      "emotional_intelligence_score": 0,
      "personality_score": 0,
      "recommended_domains": ["role", "role", "role"],
      "career_roadmap": ["step", "step", "step", "step"],
      "detailed_evaluation": "string"
    }}
    """

    history_text = "\n".join(
        f"[{h.get('category', 'Question')}] Q: {h.get('question', '')}\n"
        f"Options: {' | '.join(str(o) for o in (h.get('options') or []))}\n"
        f"Chosen: {h.get('answer', '')}"
        for h in (history or [])
        if h.get("category") not in OBJECTIVE_CATEGORIES
    )

    response, tokens = await asyncio.wait_for(
        ai.chat_completion_with_usage(
            system_prompt, f"Answers:\n{history_text}\n\nEvaluate.", temperature=0.4
        ),
        timeout=35,
    )
    data = json.loads(_strip_json_fence(response))
    if not isinstance(data, dict):
        raise ValueError("Evaluation was not an object")

    roadmap = data.get("career_roadmap") or []
    if isinstance(roadmap, str):
        roadmap = [roadmap]
    roadmap = [str(s).strip() for s in roadmap if str(s).strip()]
    evaluation = str(data.get("detailed_evaluation") or "").strip()
    if roadmap:
        steps = "\n".join(f"{i}. {s}" for i, s in enumerate(roadmap, start=1))
        evaluation = f"{evaluation}\n\nCareer roadmap:\n{steps}".strip()

    roles = data.get("recommended_domains") or [domain]
    if isinstance(roles, str):
        roles = [roles]
    roles = [str(r).strip() for r in roles if str(r).strip()] or [domain]

    def score(key: str, default: int) -> int:
        try:
            return max(1, min(100, int(data.get(key, default))))
        except (TypeError, ValueError):
            return default

    return {
        "personality_type": str(data.get("personality_type") or "Balanced").strip() or "Balanced",
        "tokens_utilized": tokens,
        "iq_estimate": iq_estimate,
        "aptitude_score": aptitude_score,
        "reasoning_score": reasoning_score,
        "emotional_intelligence_score": score("emotional_intelligence_score", 65),
        "personality_score": score("personality_score", 65),
        "recommended_domains": roles[:3],
        "detailed_evaluation": evaluation or "Your answers show how you approach work, people, and decisions.",
    }
