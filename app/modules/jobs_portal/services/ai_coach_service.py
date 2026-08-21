import json
import logging
import re
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.jobs_portal.models.ai_coach import AICoachSession
from app.shared.models.user import User
from app.modules.jobs_portal.services.ai_service import get_ai
from app.modules.jobs_portal.services.ai_coach_redis_service import AICoachRedisService

logger = logging.getLogger(__name__)


class AICoachService:

    @staticmethod
    async def initialize_session(
        db: AsyncSession, seeker_id: str, target_role: str, experience_level: str, focus_area: str
    ) -> AICoachSession:
        session = AICoachSession(
            seeker_id=seeker_id,
            target_role=target_role,
            experience_level=experience_level,
            focus_area=focus_area,
            chat_history=[]
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        # Cache initial session state in Redis
        session_cache = {
            "id": session.id,
            "seeker_id": seeker_id,
            "target_role": target_role,
            "experience_level": experience_level,
            "focus_area": focus_area,
            "status": "in_progress",
            "chat_history": []
        }
        await AICoachRedisService.save_session(session.id, session_cache)
        
        return session

    @staticmethod
    async def get_next_question(db: AsyncSession, session_id: str, user_answer: Optional[str] = None) -> Dict[str, Any]:
        # Fetch from Redis or DB
        cached = await AICoachRedisService.get_session(session_id)
        
        if cached:
            target_role = cached.get("target_role", "Job Role")
            experience_level = cached.get("experience_level", "Mid-level")
            focus_area = cached.get("focus_area", "Mixed")
            history = cached.get("chat_history", [])
            seeker_id = cached.get("seeker_id")
        else:
            res = await db.execute(select(AICoachSession).where(AICoachSession.id == session_id))
            session = res.scalar_one_or_none()
            if not session:
                return {"message": "Session not found.", "rating": None, "feedback": None, "ideal_answer": None, "is_wrapup": False}
                
            target_role = session.target_role
            experience_level = session.experience_level
            focus_area = session.focus_area
            history = list(session.chat_history or [])
            seeker_id = session.seeker_id
            
        res = await db.execute(select(User).where(User.id == seeker_id))
        seeker = res.scalar_one_or_none()
        candidate_name = f"{seeker.first_name if seeker else 'Candidate'} {seeker.last_name if seeker else ''}".strip()
        
        user_messages = [m for m in history if m.get("role") == "user"]
        # Only count turns that were genuine answers - clarifying questions don't advance the interview.
        answered_count = len([m for m in user_messages if not m.get("is_clarification")])
        is_first_question = not user_answer and len(user_messages) == 0
        is_wrapup = False

        last_bot_question = next(
            (m.get("content") for m in reversed(history) if m.get("role") == "bot"), None
        )

        if user_answer:
            history.append({"role": "user", "content": user_answer})

        history_text = "\n".join([
            f"{m['role'].capitalize()}: {m['content']}" for m in history
        ])
        
        if is_first_question:
            system_prompt = f"""
            You are a friendly, encouraging, and highly professional AI Career Coach conducting a practice mock interview.
            
            Parameters:
            - Candidate Name: {candidate_name}
            - Target Role: {target_role}
            - Experience Level: {experience_level}
            - Focus Area: {focus_area}
            
            This is QUESTION 1 of the interview. Welcoming the candidate, ask the very first interview question for a {experience_level} {target_role}.
            Do NOT provide any rating, feedback, or ideal answer since the candidate has not answered anything yet.
            
            Return ONLY a valid JSON object matching this schema:
            {{
              "message": "Welcome {candidate_name}! Let's start our mock interview for {target_role}. Could you please introduce yourself and outline your core technical skills and recent project experience?",
              "is_wrapup": false
            }}
            """
            user_prompt = "Generate Question 1 as JSON."
        else:
            system_prompt = f"""
            You are a friendly, encouraging, and highly professional AI Career Coach conducting a practice mock interview.
            
            Parameters:
            - Candidate Name: {candidate_name}
            - Target Role: {target_role}
            - Experience Level: {experience_level}
            - Focus Area: {focus_area}
            - Current Question Number: Question {answered_count + 1} of 5
            - The Current Question (still awaiting a real answer): {last_bot_question or 'N/A'}

            Your Core Responsibilities on Every Response:
            1. Maintain a warm, encouraging, friendly, and supportive coaching tone.
            2. First, decide whether the Candidate's Last Message is:
               (a) a genuine attempt to answer Question {answered_count + 1}, or
               (b) primarily a clarifying question / request for help understanding the question (e.g. "what is X?", "can you explain?", "not sure what that means") rather than an actual answer.
            3. If (b) - it is a clarifying question:
               - Set "is_clarification": true.
               - Set "rating", "feedback", and "ideal_answer" to null - there is nothing to rate yet since they have not answered.
               - Under "answer_to_user_query", clearly and kindly explain the term/concept they asked about, with a short concrete example if useful.
               - Set "message" to a short encouraging line that invites them to now answer Question {answered_count + 1} (you may briefly restate it). Do NOT ask a new question and do NOT advance the question number.
            4. If (a) - it is a genuine answer:
               - Set "is_clarification": false.
               - Provide a "rating" out of 10 (e.g. "8.5/10" or "9/10" or "7/10").
               - Provide constructive "feedback" highlighting strengths and 1-2 actionable tips to make their answer stronger (mention metrics, STAR method, or technical specifics).
               - Provide an "ideal_answer" (Model Answer): 2-3 concise bullet points or key details that a top candidate should include to achieve a 10/10 score.
               - If they also asked a small side question, answer it briefly under "answer_to_user_query", otherwise set it to null.
               - Ask Question {answered_count + 2} focused on {target_role} and {focus_area} under "message".
               - When this was Question 5 (i.e. the candidate has now answered 5 questions total), set "is_wrapup": true and "message": "This concludes our mock interview session. Great job practicing today! Your session scorecard is now being compiled."

            You MUST return ONLY a valid JSON object matching this schema:
            {{
              "is_clarification": false,
              "rating": "8.5/10",
              "feedback": "Constructive feedback and specific suggestion for improvement",
              "ideal_answer": "Model answer / key points a candidate should include",
              "answer_to_user_query": "Response if candidate asked a question, otherwise null",
              "message": "The text of your next interview question, a clarification reply, or wrap-up message",
              "is_wrapup": false
            }}
            """
            user_prompt = f"Interview Transcript History:\n{history_text}\n\nCandidate's Last Message: {user_answer}\n\nGenerate the structured coaching JSON response."
        
        ai = get_ai()
        try:
            response_raw = await ai.chat_completion(system_prompt, user_prompt)
            
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response_raw)
            if json_match:
                response_raw = json_match.group(1)
            else:
                start_idx = response_raw.find('{')
                end_idx = response_raw.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    response_raw = response_raw[start_idx:end_idx+1]
                    
            response_raw = response_raw.strip()
            
            try:
                data = json.loads(response_raw)
            except json.JSONDecodeError:
                data = {
                    "is_clarification": False,
                    "rating": None if is_first_question else "8/10",
                    "feedback": None if is_first_question else "Good response! Try adding specific quantitative metrics or system architecture details.",
                    "ideal_answer": None if is_first_question else "An ideal answer covers key technical frameworks, quantitative metrics, and STAR method structure.",
                    "answer_to_user_query": None,
                    "message": response_raw,
                    "is_wrapup": False
                }

            bot_msg = data.get("message")
            is_clarification = False if is_first_question else bool(data.get("is_clarification", False))
            rating = None if (is_first_question or is_clarification) else data.get("rating")
            feedback = None if (is_first_question or is_clarification) else data.get("feedback")
            ideal_answer = None if (is_first_question or is_clarification) else data.get("ideal_answer")
            answer_to_user_query = data.get("answer_to_user_query")
            is_wrapup = (
                bool(data.get("is_wrapup", False)) or ("concludes our mock interview" in (bot_msg or "").lower())
            ) and not is_clarification

            # Tag the just-appended user turn so it's excluded from future question-progression counts.
            if user_answer and history and history[-1].get("role") == "user":
                history[-1]["is_clarification"] = is_clarification

            post_answer_count = answered_count if is_clarification else answered_count + 1

            if not bot_msg:
                if is_first_question:
                    bot_msg = f"Welcome {candidate_name}! Let's start our mock interview for {target_role}. Could you please introduce yourself and outline your core technical skills and recent project experience?"
                elif is_clarification:
                    explanation = answer_to_user_query or "Happy to help - feel free to answer in your own words based on your experience."
                    followup = last_bot_question or f"Could you now answer Question {answered_count + 1}?"
                    bot_msg = f"Good question! {explanation} Now, let's continue: {followup}"
                elif post_answer_count == 1:
                    bot_msg = f"Great introduction! For Question 2: In your experience as a {target_role}, how do you approach system architecture design, code optimization, and performance tuning?"
                    rating = rating or "8.5/10"
                    feedback = feedback or "Solid overview of your skills. Highlight specific metrics or production scale for extra impact."
                    ideal_answer = ideal_answer or "An ideal response introduces yourself, highlights your core technical stack (e.g. Python, Django, PostgreSQL, Redis), total experience, and 1-2 major project accomplishments."
                elif post_answer_count == 2:
                    bot_msg = f"Solid technical approach! For Question 3: Tell me about a challenging bug, system outage, or tight deadline you handled as a {target_role}. How did you resolve it (using the STAR framework)?"
                    rating = rating or "8.0/10"
                    feedback = feedback or "Clear technical reasoning. Make sure to structure complex debugging steps step-by-step."
                    ideal_answer = ideal_answer or "An ideal response explains decoupling business logic, using Redis caching for high-read endpoints, query indexing, and circuit-breaker retry mechanisms."
                elif post_answer_count == 3:
                    bot_msg = f"Great problem-solving example! For Question 4: How do you collaborate with cross-functional teams, conduct code reviews, and handle conflicting technical requirements?"
                    rating = rating or "8.5/10"
                    feedback = feedback or "Good STAR method breakdown! Be sure to highlight the final quantitative results achieved."
                    ideal_answer = ideal_answer or "An ideal response outlines Situation (production deadlock), Task (restore uptime < 15 mins), Action (query profiling, lock tuning, hotfix), and Result (99.99% uptime restored)."
                elif post_answer_count == 4:
                    bot_msg = f"Well explained! Final Question: What are your long-term professional goals as a {target_role}, and how do you continuously stay updated with emerging tech stack tools?"
                    rating = rating or "9.0/10"
                    feedback = feedback or "Excellent collaboration principles! Very professional response."
                    ideal_answer = ideal_answer or "An ideal response highlights conducting constructive PR reviews, maintaining OpenAPI docs, enforcing CI/CD linting checks, and mentoring junior devs."
                else:
                    bot_msg = "This concludes our mock interview session. Great job practicing today! Your session scorecard is now being compiled."
                    rating = rating or "9.0/10"
                    feedback = feedback or "Overall strong practice session!"
                    ideal_answer = ideal_answer or "Great responses across technical and behavioral rounds!"
                    is_wrapup = True

            bot_entry = {
                "role": "bot",
                "content": bot_msg,
                "rating": rating,
                "feedback": feedback,
                "ideal_answer": ideal_answer,
                "answer_to_user_query": answer_to_user_query
            }
            history.append(bot_entry)
            
            # Save to Redis
            cached_data = {
                "id": session_id,
                "seeker_id": seeker_id,
                "target_role": target_role,
                "experience_level": experience_level,
                "focus_area": focus_area,
                "status": "completed" if is_wrapup else "in_progress",
                "chat_history": history
            }
            await AICoachRedisService.save_session(session_id, cached_data)
            
            # Async sync to DB
            res_db = await db.execute(select(AICoachSession).where(AICoachSession.id == session_id))
            session_db = res_db.scalar_one_or_none()
            if session_db:
                session_db.chat_history = history
                if is_wrapup:
                    session_db.status = "completed"
                    await AICoachService.evaluate_session(db, session_db)
                await db.commit()
                
            return {
                "message": bot_msg,
                "rating": rating,
                "feedback": feedback,
                "ideal_answer": ideal_answer,
                "answer_to_user_query": answer_to_user_query,
                "is_wrapup": is_wrapup
            }

        except Exception as e:
            logger.error(f"AI Coach Service Error: {e}")
            is_wrapup = False
            answer_to_user_query = None

            # The LLM is unavailable in this path, so there's no way to judge intent here -
            # clarification detection only happens when the AI itself classifies the message.
            if user_answer and history and history[-1].get("role") == "user":
                history[-1]["is_clarification"] = False

            post_answer_count = answered_count + 1

            # Smart turn-based fallback when LLM fails or is in mock mode
            if is_first_question:
                fallback_msg = f"Welcome {candidate_name}! Let's start our mock interview for {target_role}. Could you please introduce yourself and outline your core technical skills and recent project experience?"
                rating = None
                feedback = None
                ideal_answer = None
            elif post_answer_count == 1:
                fallback_msg = f"Great introduction! For Question 2: In your experience as a {target_role}, how do you approach system architecture design, code optimization, and performance tuning?"
                rating = "8.5/10"
                feedback = "Good overview of your background! To make your answer stronger, include specific quantitative metrics or scale from your past projects."
                ideal_answer = "An ideal response introduces yourself, highlights your core technical stack (e.g. Python, Django, PostgreSQL, Redis), total experience, and 1-2 major project accomplishments."
            elif post_answer_count == 2:
                fallback_msg = f"Solid technical approach! For Question 3: Tell me about a challenging bug, production issue, or tight deadline you handled as a {target_role}. How did you resolve it (using the STAR framework)?"
                rating = "8.0/10"
                feedback = "Clear explanation of architecture concepts. Try structuring complex technical solutions step-by-step."
                ideal_answer = "An ideal response explains decoupling business logic, using Redis caching for high-read endpoints, query indexing, and circuit-breaker retry mechanisms."
            elif post_answer_count == 3:
                fallback_msg = f"Great problem-solving example! For Question 4: How do you collaborate with cross-functional teams, conduct code reviews, and handle conflicting technical requirements?"
                rating = "8.5/10"
                feedback = "Good STAR method breakdown! Be sure to emphasize the final measurable business or engineering impact."
                ideal_answer = "An ideal response outlines Situation (production deadlock), Task (restore uptime < 15 mins), Action (query profiling, lock tuning, hotfix), and Result (99.99% uptime restored)."
            elif post_answer_count == 4:
                fallback_msg = f"Well explained! Final Question: What are your primary career goals as a {target_role}, and how do you continuously stay updated with emerging technologies?"
                rating = "9.0/10"
                feedback = "Excellent teamwork and code quality principles! Very professional response."
                ideal_answer = "An ideal response highlights conducting constructive PR reviews, maintaining OpenAPI docs, enforcing CI/CD linting checks, and mentoring junior devs."
            else:
                fallback_msg = "This concludes our mock interview session. Great job practicing today! Your session scorecard is now being compiled."
                rating = "9.0/10"
                feedback = "Overall strong practice session!"
                ideal_answer = "Great responses across technical and behavioral rounds!"
                is_wrapup = True

            bot_entry = {
                "role": "bot",
                "content": fallback_msg,
                "rating": rating,
                "feedback": feedback,
                "ideal_answer": ideal_answer,
                "answer_to_user_query": answer_to_user_query
            }
            history.append(bot_entry)
            
            cached_data = {
                "id": session_id,
                "seeker_id": seeker_id,
                "target_role": target_role,
                "experience_level": experience_level,
                "focus_area": focus_area,
                "status": "completed" if is_wrapup else "in_progress",
                "chat_history": history
            }
            await AICoachRedisService.save_session(session_id, cached_data)
            
            res_db = await db.execute(select(AICoachSession).where(AICoachSession.id == session_id))
            session_db = res_db.scalar_one_or_none()
            if session_db:
                session_db.chat_history = history
                if is_wrapup:
                    session_db.status = "completed"
                    await AICoachService.evaluate_session(db, session_db)
                await db.commit()

            return {
                "message": fallback_msg,
                "rating": rating,
                "feedback": feedback,
                "ideal_answer": ideal_answer,
                "answer_to_user_query": answer_to_user_query,
                "is_wrapup": is_wrapup
            }

    @staticmethod
    async def get_active_room_session(db: AsyncSession, session_id: str, seeker_id: str) -> Dict[str, Any]:
        """Fetch active room session from Redis or DB."""
        cached = await AICoachRedisService.get_session(session_id)
        if cached and cached.get("seeker_id") == seeker_id:
            history = cached.get("chat_history", [])
            last_bot = next((m for m in reversed(history) if m.get("role") == "bot"), {})
            target_role = cached.get('target_role', 'your target role')
            default_q = f"Welcome! Let's start your mock interview for {target_role}. Could you please introduce yourself and outline your core technical skills and recent project experience?"
            return {
                "id": session_id,
                "target_role": target_role,
                "experience_level": cached.get("experience_level"),
                "focus_area": cached.get("focus_area"),
                "status": cached.get("status", "in_progress"),
                "current_question": last_bot.get("content") or default_q,
                "rating": last_bot.get("rating"),
                "feedback": last_bot.get("feedback"),
                "ideal_answer": last_bot.get("ideal_answer"),
                "answer_to_user_query": last_bot.get("answer_to_user_query"),
                "chat_history": history
            }
            
        res = await db.execute(select(AICoachSession).where(AICoachSession.id == session_id))
        session = res.scalar_one_or_none()
        if not session or session.seeker_id != seeker_id:
            return {"error": "Session not found"}
            
        history = list(session.chat_history or [])
        last_bot = next((m for m in reversed(history) if m.get("role") == "bot"), {})
        default_q = f"Welcome! Let's start your mock interview for {session.target_role}. Could you please introduce yourself and outline your core technical skills and recent project experience?"
        
        # Populate Redis cache
        cache_payload = {
            "id": session.id,
            "seeker_id": session.seeker_id,
            "target_role": session.target_role,
            "experience_level": session.experience_level,
            "focus_area": session.focus_area,
            "status": session.status,
            "chat_history": history
        }
        await AICoachRedisService.save_session(session.id, cache_payload)
        
        return {
            "id": session.id,
            "target_role": session.target_role,
            "experience_level": session.experience_level,
            "focus_area": session.focus_area,
            "status": session.status,
            "current_question": last_bot.get("content") or default_q,
            "rating": last_bot.get("rating"),
            "feedback": last_bot.get("feedback"),
            "ideal_answer": last_bot.get("ideal_answer"),
            "chat_history": history
        }

    @staticmethod
    async def evaluate_session(db: AsyncSession, session: AICoachSession):
        ai = get_ai()
        history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in session.chat_history])
        
        system_prompt = f"""
        You are a senior technical interviewer and executive career coach.
        Review the mock interview transcript for the target role of {session.target_role} ({session.experience_level} level, focusing on {session.focus_area}).
        
        Analyze the conversation history and grade the candidate.
        Calculate the following metrics:
        1. content_score (0-100): evaluate technical depth, logic, accuracy, and completeness of their answers.
        2. communication_score (0-100): evaluate clarity, structuring, confidence, and pacing of response.
        3. overall_score (0-100): average of content and communication scores.
        
        In addition, provide:
        - general_feedback: A detailed, encouraging yet constructive summary of their performance.
        - strengths: A list of 3-4 key areas where the candidate performed well.
        - gaps: A list of 3-4 technical or communication areas that need improvement.
        - improvement_steps: A list of 3-4 specific, actionable learning steps, resource recommendations, or practice advice.
        - video_feedback: Construct a simulated critique of visual/body-language presence appropriate to their communication style (e.g. eye contact, pacing, body alignment, confidence signals).
        
        Return the evaluation ONLY as a valid JSON object matching this schema exactly:
        {{
          "overall_score": int,
          "content_score": int,
          "communication_score": int,
          "general_feedback": "string",
          "strengths": ["string", "string", ...],
          "gaps": ["string", "string", ...],
          "improvement_steps": ["string", "string", ...],
          "video_feedback": {{
             "eye_contact": "string feedback on eye contact",
             "posture": "string feedback on posture",
             "delivery": "string feedback on delivery speed and tone"
          }}
        }}
        """
        
        user_prompt = f"Transcript:\n{history_text}\n\nGenerate evaluation JSON."
        try:
            response_raw = await ai.chat_completion(system_prompt, user_prompt)
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response_raw)
            if json_match:
                response_raw = json_match.group(1)
            else:
                start_idx = response_raw.find('{')
                end_idx = response_raw.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    response_raw = response_raw[start_idx:end_idx+1]
            data = json.loads(response_raw.strip())
            
            session.overall_score = data.get("overall_score", 82)
            session.content_score = data.get("content_score", 80)
            session.communication_score = data.get("communication_score", 84)
            session.general_feedback = data.get("general_feedback", "Great mock interview performance!")
            session.strengths = data.get("strengths", ["Strong communication", "Good technical domain knowledge"])
            session.gaps = data.get("gaps", ["Include more quantitative project impact metrics"])
            session.improvement_steps = data.get("improvement_steps", ["Practice system architecture design questions"])
            session.video_feedback = data.get("video_feedback", {})
            session.status = "completed"
            
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to evaluate session: {e}")
            session.overall_score = 82
            session.content_score = 80
            session.communication_score = 84
            session.general_feedback = "Great effort practicing your interview skills!"
            session.strengths = ["Solid communication", "Clear technical explanation"]
            session.gaps = ["Add quantitative project impact metrics"]
            session.improvement_steps = ["Practice STAR method problem-solving responses"]
            session.status = "completed"
            await db.commit()
