"""
Live voice interview session service.

Owns everything specific to the "live" (real-time voice) AI Coach mode, kept
separate from ai_coach_service.py which still owns the turn-based text-mode
flow unchanged. Live mode doesn't use the text-mode's per-turn LLM call
(get_next_question) at all -  Live asks the questions itself, driven by
a system instruction built once at session start, and the backend's only job
is relaying audio/transcript between the browser and the  Live session.
"""
import asyncio
import base64
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

import google.genai as genai
from google.genai import types

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.shared.models.user import User
from app.modules.jobs_portal.models.ai_coach import AICoachSession
from app.modules.jobs_portal.services.ai_coach_service import AICoachService
from app.modules.jobs_portal.services.ai_coach_credits_service import AICoachCreditsService

logger = logging.getLogger(__name__)

QUESTION_COUNT = 5

# Unique phrase used strictly at the end of the full interview call.
LIVE_WRAPUP_PHRASE = "interview_completed_wrapup_final_summary"


class _ClientEndedSession(Exception):
    """Raised internally when the browser sends {"type": "end"}."""


class _WrapupDetected(Exception):
    """Raised internally when Gemini's spoken transcript contains the wrap-up phrase."""


def build_live_system_instruction(
    candidate_name: str, target_role: str, experience_level: str, focus_area: str
) -> str:
    return f"""
    You are Zoya, a friendly, highly encouraging, and professional AI Interview Preparation Coach conducting a LIVE SPOKEN practice mock interview over a real-time voice call.

    Parameters:
    - Your Name: Zoya
    - Candidate Name: {candidate_name}
    - Target Role: {target_role}
    - Experience Level: {experience_level}
    - Focus Area: {focus_area}

    Conversation rules:
    1. INITIAL GREETING:
       Introduce yourself clearly: "Hi! My name is Zoya, I'm your AI Interview Preparation Coach. Hello {candidate_name}, how are you today?"
       Briefly explain: "We will be practicing a {QUESTION_COUNT}-question mock interview for the {target_role} position ({focus_area})."
       Then ask Question 1 of {QUESTION_COUNT}.

    2. QUESTION STRUCTURE:
       Ask exactly {QUESTION_COUNT} interview questions, one at a time, focused on {target_role} and {focus_area} at a {experience_level} level.
       Number each question out loud (e.g. "Question 1 of {QUESTION_COUNT}", "Question 2 of {QUESTION_COUNT}", etc.).

    3. AFTER EACH CANDIDATE ANSWER:
       Wait until the candidate finishes speaking their answer to the current question.
       Then provide structured spoken coaching feedback:
       a) Highlight what they did well or how their response can be improved (1-2 sentences).
       b) Provide a brief exemplar / ideal way to structure that specific answer ("For example, a great way to frame your answer would be...").
       c) Seamlessly transition to the next question.

    4. CLARIFICATIONS:
       If the candidate asks a clarifying question instead of answering, answer it briefly and kindly, then invite them to answer the current question.

    5. FINAL CLOSING & WRAP-UP:
       ONLY after the candidate has completed answering Question 5 of 5:
       Provide constructive feedback and an exemplar answer for Question 5, thank the candidate warmly for practicing today, say "That concludes our 5-question mock interview session! Good luck with your upcoming job interviews!", and stop speaking.

    6. Keep your tone warm, conversational, articulate, and natural and in indian accent.
    """.strip()


def _build_live_connect_config(system_instruction: str) -> "types.LiveConnectConfig":
    return types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
            )
        ),
        system_instruction=system_instruction,
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )


class TranscriptAccumulator:
    """Merges consecutive same-role transcript fragments (Gemini streams transcription
    incrementally) into clean {role, content} turns matching the same JSON shape
    AICoachSession.chat_history already uses in text mode, so evaluate_session needs
    zero changes to consume a live-mode transcript."""

    def __init__(self) -> None:
        self._turns: list[dict] = []

    def add(self, role: str, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        if self._turns and self._turns[-1]["role"] == role:
            self._turns[-1]["content"] = f"{self._turns[-1]['content']} {text}".strip()
        else:
            self._turns.append({"role": role, "content": text})

    def to_chat_history(self) -> list[dict]:
        return list(self._turns)

    def contains_wrapup_phrase(self) -> bool:
        user_turns = [t for t in self._turns if t["role"] == "user"]
        bot_turns = [t for t in self._turns if t["role"] == "bot"]

        # The interview has 5 questions. After candidate answers 5 questions (len(user_turns) >= 5)
        # and bot finishes its 6th turn (final feedback & wrap-up closing statement), wrap-up is complete.
        if len(user_turns) >= 5 and len(bot_turns) >= 6:
            return True

        # Secondary check if bot speaks closing phrases after candidate answers at least 4 questions
        if len(user_turns) >= 4 and bot_turns:
            last_bot_text = bot_turns[-1]["content"].lower()
            closing_keywords = [
                "concludes our", "that concludes", "thank you for practicing",
                "good luck with your", "end of our mock interview", "interview is complete",
                "concludes our 5-question"
            ]
            if any(kw in last_bot_text for kw in closing_keywords):
                return True

        return False


def compute_realtime_analytics(turns: list[dict], target_role: str, focus_area: str) -> dict:
    """Computes 15 dynamic real-time voice call telemetry metrics on every turn."""
    user_turns = [t["content"] for t in turns if t["role"] == "user"]
    turn_count = len(user_turns)
    combined_user_text = " ".join(user_turns).lower()
    words = [w.strip(",.!?\"'()[]{}") for w in combined_user_text.split() if w.strip(",.!?\"'()[]{}")]
    total_words = len(words)

    # Turn history tracking for dynamic performance charts
    turn_history = []
    accumulated_text = ""
    for idx, u_text in enumerate(user_turns):
        accumulated_text += " " + u_text.lower()
        t_words = accumulated_text.split()
        t_total = max(len(t_words), 1)
        t_pos = sum(1 for w in t_words if w in {"led", "built", "solved", "created", "designed", "achieved", "managed", "improved", "strong", "great", "responsible"})
        t_fill = sum(1 for w in t_words if w in {"um", "uh", "like", "actually", "basically", "you know", "honestly"})
        t_pos_score = max(40, min(99, int(72 + (t_pos * 4) - (t_fill * 3))))
        t_clarity_score = max(40, min(99, int(96 - ((t_fill / t_total) * 150))))
        turn_history.append({
            "turn": f"Turn {idx + 1}",
            "positivity": t_pos_score,
            "clarity": t_clarity_score,
            "overall": int((t_pos_score + t_clarity_score) / 2)
        })

    if total_words < 5:
        return {
            "type": "analytics_update",
            "positivity": 80,
            "speech_clarity": 88,
            "confidence": 82,
            "stress_level": 15,
            "wpm": 125,
            "filler_count": 0,
            "vocabulary_diversity": 85,
            "star_method_score": 60,
            "concept_coverage": 50,
            "matched_concepts": [],
            "answer_completeness": 65,
            "conciseness": 85,
            "overall_readiness": 78,
            "tone": "Warm Up Phase",
            "turn_history": turn_history,
        }

    # 1. Fillers & Speech Clarity
    fillers = {"um", "uh", "like", "actually", "basically", "you know", "honestly", "sort of", "kind of", "i mean", "so yeah", "right"}
    filler_count = sum(1 for w in words if w in fillers)
    filler_ratio = filler_count / max(total_words, 1)
    speech_clarity = max(40, min(99, int(96 - (filler_ratio * 170))))

    # 2. Positivity & Sentiment Score
    positive_words = {
        "led", "achieved", "built", "implemented", "solved", "created", "designed",
        "optimized", "managed", "improved", "strong", "experience", "successful",
        "good", "great", "effectively", "responsible", "confident", "ensure",
        "collaborated", "deliver", "scale", "solution", "result", "team", "passed",
        "spearheaded", "engineered", "architected", "resolved", "secured"
    }
    hesitant_words = {
        "maybe", "guess", "don't know", "not sure", "hard to say", "confused",
        "failed", "unclear", "doubt", "uhh", "probably not", "forgot", "cant"
    }
    pos_count = sum(1 for w in words if w in positive_words)
    hes_count = sum(1 for w in words if w in hesitant_words)
    positivity = max(35, min(99, int(74 + (pos_count * 4) - (hes_count * 6))))

    # 3. Confidence & Stress Level
    confidence = max(35, min(99, int(70 + (pos_count * 5) - (hes_count * 6) - (filler_count * 2))))
    stress_level = max(8, min(92, int(15 + (filler_count * 7) + (hes_count * 9))))

    # 4. Vocabulary Diversity (Lexical Richness)
    unique_words = len(set(words))
    vocabulary_diversity = max(40, min(99, int((unique_words / max(total_words, 1)) * 100)))

    # 5. Technical Concept Coverage
    tech_pool = [
        "api", "database", "python", "react", "component", "state", "service",
        "function", "async", "sql", "git", "docker", "auth", "rest", "schema",
        "performance", "test", "security", "pipeline", "cache", "model", "view",
        "hook", "frontend", "backend", "cloud", "architecture", "deployment",
        "testing", "agile", "framework", "endpoint", "system", "logic", "scale"
    ]
    role_words = [w for w in f"{target_role} {focus_area}".replace("-", " ").lower().split() if len(w) > 3]
    search_keywords = list(set(tech_pool + role_words))
    matched = [kw for kw in search_keywords if kw in combined_user_text]
    concept_coverage = max(35, min(98, 42 + len(matched) * 9))

    # 6. STAR Method Score (Situation, Task, Action, Result)
    star_sit = any(k in combined_user_text for k in ["situation", "challenge", "problem", "when i", "needed to", "project"])
    star_act = any(k in combined_user_text for k in ["action", "i built", "i used", "i wrote", "i solved", "i created", "i implemented"])
    star_res = any(k in combined_user_text for k in ["result", "outcome", "improved", "increased", "reduced", "saved", "achieved", "percent", "%"])
    star_method_score = max(30, min(98, 35 + (20 if star_sit else 0) + (25 if star_act else 0) + (20 if star_res else 0)))

    # 7. WPM (Words Per Minute Pace)
    avg_words_per_turn = total_words / max(turn_count, 1)
    wpm = max(90, min(175, int(115 + (avg_words_per_turn * 0.45))))

    # 8. Answer Completeness & Conciseness
    answer_completeness = max(40, min(98, int(50 + (avg_words_per_turn * 0.8) + (len(matched) * 4))))
    conciseness = max(40, min(98, int(95 - (filler_ratio * 120) - (max(0, avg_words_per_turn - 120) * 0.3))))

    # 9. Overall Interview Readiness Composite Score
    overall_readiness = int(
        (positivity * 0.2) +
        (speech_clarity * 0.2) +
        (confidence * 0.2) +
        (concept_coverage * 0.2) +
        (star_method_score * 0.2)
    )

    # 10. Dynamic Tone Classification
    if positivity >= 85 and speech_clarity >= 85:
        tone = "Executive & Confident"
    elif concept_coverage >= 75 and star_method_score >= 70:
        tone = "Structured & Technical"
    elif hes_count > 2 or speech_clarity < 65:
        tone = "Hesitant / Soft"
    elif wpm > 155:
        tone = "Fast-Paced & Energetic"
    else:
        tone = "Professional & Clear"

    return {
        "type": "analytics_update",
        "positivity": positivity,
        "speech_clarity": speech_clarity,
        "confidence": confidence,
        "stress_level": stress_level,
        "wpm": wpm,
        "filler_count": filler_count,
        "vocabulary_diversity": vocabulary_diversity,
        "star_method_score": star_method_score,
        "concept_coverage": concept_coverage,
        "matched_concepts": [m.capitalize() for m in matched[:6]],
        "answer_completeness": answer_completeness,
        "conciseness": conciseness,
        "overall_readiness": overall_readiness,
        "tone": tone,
        "turn_history": turn_history,
    }


async def _resolve_candidate_name(seeker_id: str) -> str:
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.id == seeker_id))
        seeker = res.scalar_one_or_none()
    return f"{seeker.first_name if seeker else 'Candidate'} {seeker.last_name if seeker else ''}".strip()


async def run_live_session(
    websocket: WebSocket,
    session_id: str,
    seeker_id: str,
    target_role: str,
    experience_level: str,
    focus_area: str,
) -> None:
    """Owns the Gemini Live connection for the full call duration. Deliberately takes
    no long-lived DB session as an argument (see ai_coach_live_ws.py docstring) -
    opens its own short-lived AsyncSessionLocal() only for the brief finalize step."""
    candidate_name = await _resolve_candidate_name(seeker_id)
    system_instruction = build_live_system_instruction(
        candidate_name, target_role, experience_level, focus_area
    )
    config = _build_live_connect_config(system_instruction)
    transcript = TranscriptAccumulator()

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    try:
        async with client.aio.live.connect(model=settings.GEMINI_LIVE_MODEL, config=config) as gemini_session:
            # Kick off the session by prompting Zoya to introduce herself and ask Question 1
            await gemini_session.send_realtime_input(
                text=f"Hello Zoya! I am candidate {candidate_name}. Please start the session now by introducing yourself as Zoya, asking how I am doing, and asking Question 1 of {QUESTION_COUNT}."
            )

            async def browser_to_gemini() -> None:
                async for raw_msg in websocket.iter_text():
                    try:
                        data = json.loads(raw_msg)
                    except ValueError:
                        continue
                    mtype = data.get("type")
                    if mtype == "audio" and data.get("data"):
                        pcm_bytes = base64.b64decode(data["data"])
                        await gemini_session.send_realtime_input(
                            audio=types.Blob(data=pcm_bytes, mime_type="audio/pcm;rate=16000")
                        )
                    elif mtype == "end":
                        raise _ClientEndedSession()
                    # "ping" keep-alive is a no-op here - it only exists to keep the
                    # browser<->backend socket (and therefore this loop) alive.

            last_analytics_time = 0.0

            async def gemini_to_browser() -> None:
                nonlocal last_analytics_time
                while True:
                    try:
                        async for server_msg in gemini_session.receive():
                            sc = server_msg.server_content
                            if sc is None:
                                continue

                            if sc.interrupted:
                                await websocket.send_json({"type": "bot_interrupted"})

                            if sc.input_transcription and sc.input_transcription.text:
                                transcript.add("user", sc.input_transcription.text)
                                await websocket.send_json({
                                    "type": "transcript", "role": "user", "text": sc.input_transcription.text,
                                })
                                now = asyncio.get_event_loop().time()
                                if now - last_analytics_time > 0.5:
                                    last_analytics_time = now
                                    analytics_data = compute_realtime_analytics(transcript.to_chat_history(), target_role, focus_area)
                                    await websocket.send_json(analytics_data)

                            if sc.output_transcription and sc.output_transcription.text:
                                transcript.add("bot", sc.output_transcription.text)
                                await websocket.send_json({
                                    "type": "transcript", "role": "bot", "text": sc.output_transcription.text,
                                })

                            if sc.model_turn and sc.model_turn.parts:
                                for part in sc.model_turn.parts:
                                    inline = getattr(part, "inline_data", None)
                                    if inline and inline.data:
                                        b64 = base64.b64encode(inline.data).decode()
                                        await websocket.send_json({
                                            "type": "bot_audio", "data": b64, "sample_rate": 24000,
                                        })

                            if sc.turn_complete:
                                await websocket.send_json({"type": "bot_state", "state": "listening"})
                                analytics_data = compute_realtime_analytics(transcript.to_chat_history(), target_role, focus_area)
                                await websocket.send_json(analytics_data)
                                if transcript.contains_wrapup_phrase():
                                    raise _WrapupDetected()
                    except _WrapupDetected:
                        raise
                    except Exception as err:
                        logger.warning("Gemini receive iteration ended: %r", err)
                        break

            async def credit_deduction_loop() -> None:
                # Deduct initial 1.5 credits for Minute 1
                async with AsyncSessionLocal() as db:
                    success, balance = await AICoachCreditsService.deduct_heartbeat_credit(
                        db, seeker_id, session_id, rate=1.5
                    )
                    await websocket.send_json({"type": "credit_update", "balance": balance, "deducted": 1.5})
                    if not success:
                        await websocket.send_json({
                            "type": "error",
                            "message": "⚡ Insufficient credits to continue the live session. Please top up."
                        })
                        raise _ClientEndedSession()

                # Deduct 1.5 credits every 60 seconds of call duration
                while True:
                    await asyncio.sleep(60)
                    async with AsyncSessionLocal() as db:
                        success, balance = await AICoachCreditsService.deduct_heartbeat_credit(
                            db, seeker_id, session_id, rate=1.5
                        )
                        await websocket.send_json({"type": "credit_update", "balance": balance, "deducted": 1.5})
                        if not success:
                            await websocket.send_json({
                                "type": "error",
                                "message": "⚡ Insufficient credits to continue the live session. Please top up."
                            })
                            raise _ClientEndedSession()

            tasks = [
                asyncio.create_task(browser_to_gemini(), name="browser_to_gemini"),
                asyncio.create_task(gemini_to_browser(), name="gemini_to_browser"),
                asyncio.create_task(credit_deduction_loop(), name="credit_deduction_loop"),
            ]
            try:
                done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for t in done:
                    exc = t.exception()
                    logger.warning("LIVE TASK '%s' FINISHED. Exception: %r", t.get_name(), exc)
                    if exc and not isinstance(exc, (_ClientEndedSession, _WrapupDetected, WebSocketDisconnect)):
                        raise exc
            finally:
                for t in tasks:
                    t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("AI Coach live session error (session_id=%s): %s", session_id, e)

    # --- finalize: Gemini session is fully closed at this point. Opens its own
    # short-lived DB session rather than reusing one held across the whole call. ---
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AICoachSession).where(AICoachSession.id == session_id))
        session = result.scalar_one_or_none()
        if session:
            session.chat_history = transcript.to_chat_history()
            session.status = "completed"
            await db.commit()

            try:
                await AICoachService.evaluate_session(db, session)  # reused unchanged from text mode
            except Exception as e:
                logger.error("AI Coach live evaluate_session failed (session_id=%s): %s", session_id, e)

    try:
        await websocket.send_json({"type": "evaluation_ready", "session_id": session_id})
        await websocket.close()
    except Exception:
        pass
