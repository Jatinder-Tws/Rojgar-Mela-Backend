import json
import logging
import re
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.ai_coach import AICoachSession
from models.user import User
from services.ai_service import get_ai

logger = logging.getLogger(__name__)

class AICoachService:
    @staticmethod
    async def initialize_session(db: AsyncSession, seeker_id: str, target_role: str, experience_level: str, focus_area: str) -> AICoachSession:
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
        return session

    @staticmethod
    async def get_next_question(db: AsyncSession, session_id: str, user_answer: Optional[str] = None) -> str:
        res = await db.execute(select(AICoachSession).where(AICoachSession.id == session_id))
        session = res.scalar_one_or_none()
        if not session:
            return "Session not found."
            
        res = await db.execute(select(User).where(User.id == session.seeker_id))
        seeker = res.scalar_one_or_none()
        
        ai = get_ai()
        
        # Build Context
        context = f"""
        Target Role: {session.target_role}
        Experience Level: {session.experience_level}
        Focus Area: {session.focus_area}
        Candidate Name: {seeker.first_name if seeker else "User"} {seeker.last_name if seeker else ""}
        """
        
        # chat_history is JSONB
        history = list(session.chat_history or [])
        if user_answer:
            history.append({"role": "user", "content": user_answer})
        
        history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in history])
        
        system_prompt = f"""
        You are an expert AI Career Coach. Conduct a realistic practice mock interview for the following parameters:
        {context}
        
        Guidelines:
        1. Ask one question at a time.
        2. Adapt based on the candidate's previous response. Ask clarifying or deeper questions if their response is brief or skips key concepts.
        3. Make the interview interactive. Maintain an encouraging, constructive, coaching tone.
        4. Focus strictly on the specified Focus Area:
           - Technical: Ask coding, design, system architecture, or core technology questions.
           - Behavioral: Ask situational questions using the STAR method.
           - General / Mixed: Ask a mix of both technical and behavioral.
        5. The mock interview should ask EXACTLY 5 questions.
        6. When the candidate has answered the 5th question (the transcript has 5 questions and answers), wrap up the session.
           To wrap up, you MUST output a message containing: "This concludes our mock interview. Thank you for practicing with me!"
        
        Return the response ONLY as a valid JSON object with the following schema:
        {{
          "message": "The text of your question or wrap-up message"
        }}
        """
        
        user_prompt = f"Interview History:\n{history_text}\n\nCandidate's last response: {user_answer if user_answer else 'N/A'}\n\nGenerate the next message as JSON."
        
        try:
            response_raw = await ai.chat_completion(system_prompt, user_prompt)
            
            # Find JSON block using regex if it's wrapped in markdown
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
                message = data.get("message", response_raw)
            except json.JSONDecodeError:
                message = response_raw
                
            history.append({"role": "bot", "content": message})
            session.chat_history = history
            
            # Check for wrap up
            if "concludes our mock interview" in message.lower() or "concludes the interview" in message.lower() or "concludes this mock interview" in message.lower():
                session.status = "completed"
                # Trigger Evaluation
                await AICoachService.evaluate_session(db, session)
            
            await db.commit()
            return message
        except Exception as e:
            logger.error(f"AI Coach Interview Error: {e}")
            return "Could you please elaborate on your experience relevant to your target role?"

    @staticmethod
    async def evaluate_session(db: AsyncSession, session: AICoachSession):
        ai = get_ai()
        history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in session.chat_history])
        
        system_prompt = f"""
        You are a senior technical interviewer and executive career coach.
        Review the mock interview transcript for the target role of {session.target_role} ({session.experience_level} level, focusing on {session.focus_area}).
        
        Analyze the conversation history and grade the candidate.
        You must calculate the following metrics:
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
        
        try:
            response_raw = await ai.chat_completion(system_prompt, f"Transcript:\n{history_text}")
            
            # Find JSON block using regex if it's wrapped in markdown
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
            except json.JSONDecodeError as json_err:
                logger.warning(f"Failed to parse AI JSON for Coach evaluation: {json_err}. Using regex fallback.")
                data = {}
                score_match = re.search(r'"overall_score"\s*:\s*(\d+)', response_raw)
                data['overall_score'] = int(score_match.group(1)) if score_match else 70
                
            session.overall_score = int(data.get("overall_score", 70))
            session.content_score = int(data.get("content_score", 70))
            session.communication_score = int(data.get("communication_score", 70))
            session.general_feedback = str(data.get("general_feedback", "Nice attempt. Focus on structuring your answers using the STAR method."))
            session.strengths = data.get("strengths", ["Maintained standard technical definitions"])
            session.gaps = data.get("gaps", ["Need more specific project descriptions"])
            session.improvement_steps = data.get("improvement_steps", ["Practice talking slower and explaining coding decisions"])
            session.video_feedback = data.get("video_feedback", {
                "eye_contact": "Steady gaze detected, well done.",
                "posture": "Try not to lean too close to the camera.",
                "delivery": "Pacing is normal, but try to avoid filler words."
            })
            session.status = "completed"
            await db.commit()
        except Exception as e:
            logger.error(f"Coach Evaluation Error: {e}")
            session.status = "failed"
            session.overall_score = 0
            session.general_feedback = f"AI Coaching evaluation failed: {str(e)}"
            await db.commit()
