"""
AI Service – modular adapter pattern.
Swap OpenAI for any custom model by implementing AIProvider protocol.
GPT calls are batched to minimize API hits and token usage.
"""

from __future__ import annotations
import asyncio
import json
from typing import List, Optional, Protocol, runtime_checkable

from openai import AsyncOpenAI
import google.genai as genai
from config import settings


@runtime_checkable
class AIProvider(Protocol):
    async def embed(self, text: str) -> List[float]: ...
    async def chat_completion(self, system: str, user: str) -> str: ...
    async def chat_completion_with_usage(self, system: str, user: str) -> tuple[str, int]: ...


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

    async def chat_completion(self, system: str, user: str) -> str:
        combined_prompt = f"{system}\n\n{user}"
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._client.models.generate_content(
                    model=settings.GEMINI_CHAT_MODEL,
                    contents=[combined_prompt],
                    config={
                        "temperature": 0.2,
                        "max_output_tokens": 8192,
                        "response_mime_type": "application/json",
                    },
                )
                return response.text or ""
            except Exception as e:
                print(f"Gemini API Error (Attempt {attempt+1}): {e}")
                if attempt < max_retries - 1 and ("503" in str(e) or "quota" in str(e).lower()):
                    await asyncio.sleep(2)
                    continue
                raise

    async def chat_completion_with_usage(self, system: str, user: str) -> tuple[str, int]:
        combined_prompt = f"{system}\n\n{user}"
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._client.models.generate_content(
                    model=settings.GEMINI_CHAT_MODEL,
                    contents=[combined_prompt],
                    config={
                        "temperature": 0.2,
                        "max_output_tokens": 8192,
                        "response_mime_type": "application/json",
                    },
                )
                tokens = 0
                if response.usage_metadata:
                    tokens = response.usage_metadata.total_token_count
                return (response.text or ""), tokens
            except Exception as e:
                print(f"Gemini API Error (Attempt {attempt+1}): {e}")
                if attempt < max_retries - 1 and ("503" in str(e) or "quota" in str(e).lower()):
                    await asyncio.sleep(2)
                    continue
                raise


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

    async def chat_completion(self, system: str, user: str) -> str:
        response = await self._client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=8192,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""

    async def chat_completion_with_usage(self, system: str, user: str) -> tuple[str, int]:
        response = await self._client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
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

    async def chat_completion(self, system: str, user: str) -> str:
        try:
            return await self._gemini.chat_completion(system, user)
        except Exception:
            # Fallback to OpenAI
            return await self._openai.chat_completion(system, user)

    async def chat_completion_with_usage(self, system: str, user: str) -> tuple[str, int]:
        try:
            return await self._gemini.chat_completion_with_usage(system, user)
        except Exception:
            return await self._openai.chat_completion_with_usage(system, user)


class MockAIAdapter:
    """Mock adapter for local dev – no API calls."""

    async def embed(self, text: str) -> List[float]:
        import hashlib, struct

        h = hashlib.sha256(text.encode()).digest()
        # Produce deterministic 1536-dim vector from hash (repeated)
        base = [struct.unpack("f", h[i % 32 : i % 32 + 4])[0] for i in range(1536)]
        magnitude = sum(v**2 for v in base) ** 0.5 or 1.0
        return [v / magnitude for v in base]

    async def chat_completion(self, system: str, user: str) -> str:
        # Return mock JSON that downstream parsers expect
        return json.dumps(
            {
                "question": "If you have 8 apples and give away 3, then receive double the remaining amount, how many apples do you have now?",
                "options": ["5", "10", "8", "12"],
                "second_question": "A train travels 60 km/h for 2 hours and then 80 km/h for 1.5 hours. What is the average speed of the train?",
                "second_options": ["70 km/h", "75 km/h", "80 km/h", "85 km/h"]
            }
        )

    async def chat_completion_with_usage(self, system: str, user: str) -> tuple[str, int]:
        text = await self.chat_completion(system, user)
        return text, 100


def get_ai_provider() -> AIProvider:
    mode = settings.AI_MODE
    print(
        f"AI_MODE: {mode}, GOOGLE_API_KEY: {bool(settings.GOOGLE_API_KEY)}, OPENAI_API_KEY: {bool(settings.OPENAI_API_KEY)}"
    )
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
) -> List[dict]:
    ai = get_ai()

    print(ai)
    # Determine focus based on experience level and domain interest
    if (
        ("Student" in experience_level or "Fresher" in experience_level or "Entry" in experience_level)
        and domain_interest == "Career Discovery"
    ):
        # Include reasoning and aptitude questions for freshers interested in career discovery
        focus = (
            "Focus on social orientation, work style, creative expression, analytical thinking, helping orientation, achievements, basic domain knowledge, AND include reasoning/aptitude, personality trait, and emotional intelligence related questions such as logical puzzles, situational judgement, self-awareness scenarios, and basic quantitative reasoning. Do NOT ask highly technical or advanced interview questions."
        )
    elif ("Student" in experience_level or "Fresher" in experience_level or "Entry" in experience_level):
        focus = "Focus primarily on social orientation, work style, creative expression, analytical thinking, helping orientation, achievements, basic domain knowledge, AND include reasoning/aptitude, logical puzzles, situational judgement, self-awareness scenarios, and basic quantitative reasoning. Do NOT ask highly technical or advanced interview questions."
    else:
        focus = "Focus strictly on advanced technical concepts, system design, architectural decisions, and in-depth domain knowledge appropriate for their experience level."
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

    print(user_prompt)

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
            # fallback default questions
            default_qs = [
                {
                    "question": "If you have 8 apples and give away 3, then receive double the remaining amount, how many apples do you have now?",
                    "options": ["5", "10", "8", "12"]
                },
                {
                    "question": "A train travels at 60 km/h for 2 hours and then 80 km/h for 1.5 hours. What is the average speed of the train?",
                    "options": ["70 km/h", "75 km/h", "80 km/h", "85 km/h"]
                }
            ]
            data = default_qs
        return data, tokens
    except Exception as e:
        print(f"Error generating question: {e}")
        return [
            {
                "question": "If you have 8 apples and give away 3, then receive double the remaining amount, how many apples do you have now?",
                "options": ["5", "10", "8", "12"]
            },
            {
                "question": "A train travels at 60 km/h for 2 hours and then 80 km/h for 1.5 hours. What is the average speed of the train?",
                "options": ["70 km/h", "75 km/h", "80 km/h", "85 km/h"]
            }
        ], 0
    ai = get_ai()

    print(ai)
    # Determine focus based on experience level and domain interest
    if (
        ("Student" in experience_level or "Fresher" in experience_level or "Entry" in experience_level)
        and domain_interest == "Career Discovery"
    ):
        # Include reasoning and aptitude questions for freshers interested in career discovery
        focus = (
            "Focus on social orientation, work style, creative expression, analytical thinking, helping orientation, achievements, basic domain knowledge, AND include reasoning/aptitude, personality trait, and emotional intelligence related questions such as logical puzzles, situational judgement, self-awareness scenarios, and basic quantitative reasoning. Do NOT ask highly technical or advanced interview questions."
        )
    elif ("Student" in experience_level or "Fresher" in experience_level or "Entry" in experience_level):
        focus = "Focus primarily on social orientation, work style, creative expression, analytical thinking, helping orientation, achievements, basic domain knowledge, AND include reasoning/aptitude, logical puzzles, situational judgement, self-awareness scenarios, and basic quantitative reasoning. Do NOT ask highly technical or advanced interview questions."
    else:
        focus = "Focus strictly on advanced technical concepts, system design, architectural decisions, and in-depth domain knowledge appropriate for their experience level."
    system_prompt = f"""
    You are an expert technical interviewer and career counselor.
    The candidate has an experience level of '{experience_level}' and is interested in the '{domain_interest}' domain.
    {focus}
    Based on the previous conversation history, generate the NEXT question to assess their fit.
    ALL questions must be Multiple Choice Questions (MCQs) with exactly 4 options.
    Ensure questions progressively adapt based on their previous answers.
    
    Return the response ONLY as a valid JSON object matching this schema exactly:
    {{
      "question": "The question text here",
      "options": ["Option A", "Option B", "Option C", "Option D"]
    }}
    """

    history_text = "\n".join(
        [
            f"Q: {item.get('question_text', item.get('question', ''))}\nA: {item.get('answer', '')}"
            for item in history
        ]
    )
    user_prompt = f"History:\n{history_text}\n\nGenerate the next question as JSON."

    print(user_prompt)

    try:
        response, tokens = await ai.chat_completion_with_usage(system_prompt, user_prompt)
        # Clean up markdown if included
        response = response.strip()
        print(response)
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        data = json.loads(response.strip())
        print(data)
        return json.dumps(data), tokens
    except Exception as e:
        print(f"Error generating question: {e}")
        return json.dumps(
            [
                {
                    "question": "If you have 8 apples and give away 3, then receive double the remaining amount, how many apples do you have now?",
                    "options": ["5", "10", "8", "12"]
                },
                {
                    "question": "A train travels at 60 km/h for 2 hours and then 80 km/h for 1.5 hours. What is the average speed of the train?",
                    "options": ["70 km/h", "75 km/h", "80 km/h", "85 km/h"]
                }
            ]
        ), 0


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
