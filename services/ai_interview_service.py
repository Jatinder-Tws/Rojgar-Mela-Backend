import json
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.ai_interview import AIInterviewSession
from models.application import Application, ApplicationStatus
from models.job import JobPosting
from models.user import User
from services.ai_service import get_ai

logger = logging.getLogger(__name__)

class AIInterviewService:
    @staticmethod
    async def initialize_session(db: AsyncSession, application_id: str, seeker_id: str, job_id: str) -> AIInterviewSession:
        # Create new session
        session = AIInterviewSession(
            application_id=application_id,
            seeker_id=seeker_id,
            job_id=job_id,
            chat_history=[]
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_next_question(db: AsyncSession, session_id: str, user_answer: Optional[str] = None) -> str:
        res = await db.execute(select(AIInterviewSession).where(AIInterviewSession.id == session_id))
        session = res.scalar_one_or_none()
        if not session:
            return "Session not found."
            
        res = await db.execute(select(JobPosting).where(JobPosting.id == session.job_id))
        job = res.scalar_one_or_none()
        
        res = await db.execute(select(User).where(User.id == session.seeker_id))
        seeker = res.scalar_one_or_none()
        
        ai = get_ai()
        
        # Build Context
        context = f"""
        Job Title: {job.title}
        Job Description: {job.description}
        Candidate Name: {seeker.first_name} {seeker.last_name}
        Candidate Experience Level: {job.experience_required}
        """
        
        # chat_history is JSONB, need to ensure it's mutable/updated correctly
        history = list(session.chat_history or [])
        if user_answer:
            history.append({"role": "user", "content": user_answer})
        
        history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in history])
        
        system_prompt = f"""
        You are a senior technical recruiter. Conduct a professional interview for the following role:
        {context}
        
        Guidelines:
        1. Ask one question at a time.
        2. Adapt based on the candidate's previous answer.
        3. Cover technical skills first, then behavioral fit.
        4. ANTI-CHEAT: If the candidate's answer sounds like a textbook definition or overly formal (like an AI generated it), challenge them. Ask for a very specific, messy, real-world example from their past experience where things went wrong. AI struggles to invent realistic, imperfect anecdotes.
        5. If the interview has reached ~5-6 questions, wrap up and say "Thank you for your time. This concludes the interview."
        
        Return the response ONLY as a valid JSON object with the following schema:
        {{
          "message": "The text of your question or wrap-up message"
        }}
        """
        
        user_prompt = f"Interview History:\n{history_text}\n\nCandidate's last response: {user_answer if user_answer else 'N/A'}\n\nGenerate the next message."
        
        try:
            response_raw = await ai.chat_completion(system_prompt, user_prompt)
            
            import re
            
            # Find JSON block using regex if it's wrapped in markdown
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response_raw)
            if json_match:
                response_raw = json_match.group(1)
            else:
                # Fallback: extract substring from first { to last }
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
            
            # Check for wrap up using regex to catch "concludes the interview", "concludes our interview", etc.
            import re
            if re.search(r"concludes?\s+(?:the|our|this|your)?\s*interview", message.lower()) or "concludes" in message.lower() and "interview" in message.lower() or "thank you for your time" in message.lower():
                session.status = "completed"
                # Trigger Evaluation
                await AIInterviewService.evaluate_and_shortlist(db, session)
            
            await db.commit()
            return message
        except Exception as e:
            logger.error(f"AI Interview Error: {e}")
            return "Could you please elaborate on your experience relevant to this role?"

    @staticmethod
    async def evaluate_and_shortlist(db: AsyncSession, session: AIInterviewSession):
        ai = get_ai()
        res = await db.execute(select(JobPosting).where(JobPosting.id == session.job_id))
        job = res.scalar_one_or_none()
        
        history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in session.chat_history])
        
        system_prompt = f"""
        Evaluate the following interview transcript for the role of {job.title}.
        Base the score on technical depth, communication, and alignment with the job requirements.
        
        CRITICAL ANTI-CHEAT INSTRUCTION:
        Analyze the candidate's tone. If the candidate's responses exhibit clear signs of being generated by an AI (e.g., highly robotic tone, overly sanitized structure, bulleted lists for conversational questions, lack of personal pronouns or real-world messy anecdotes), you MUST drastically reduce their score (e.g., below 40) and explicitly note "AI-generated response suspected" in the feedback.
        
        Return the evaluation ONLY as a valid JSON object:
        {{
          "score": 0-100,
          "feedback": "detailed feedback string. Mention if AI cheating is suspected.",
          "strengths": ["string"],
          "gaps": ["string"]
        }}
        """
        
        application = None
        try:
            res_app = await db.execute(select(Application).where(Application.id == session.application_id))
            application = res_app.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching application: {e}")

        try:
            response_raw = await ai.chat_completion(system_prompt, f"Transcript:\n{history_text}")
            
            import re
            
            # Find JSON block using regex if it's wrapped in markdown
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response_raw)
            if json_match:
                response_raw = json_match.group(1)
            else:
                # Fallback: extract substring from first { to last }
                start_idx = response_raw.find('{')
                end_idx = response_raw.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    response_raw = response_raw[start_idx:end_idx+1]
                    
            try:
                data = json.loads(response_raw.strip())
            except json.JSONDecodeError as json_err:
                logger.warning(f"Failed to parse AI JSON: {json_err}. Attempting regex fallback.")
                data = {}
                # Extract score using regex
                import re
                score_match = re.search(r'"score"\s*:\s*(\d+)', response_raw)
                if score_match:
                    data['score'] = int(score_match.group(1))
                
                # Extract feedback using regex (handles unescaped newlines/quotes better)
                fb_match = re.search(r'"feedback"\s*:\s*"(.*?)"\s*,\s*"strengths"', response_raw, re.DOTALL)
                if fb_match:
                    data['feedback'] = fb_match.group(1).replace('\n', ' ')
                else:
                    fb_match2 = re.search(r'"feedback"\s*:\s*"([^"]*)"', response_raw)
                    if fb_match2:
                        data['feedback'] = fb_match2.group(1)
            
            try:
                score_val = int(data.get("score", 0))
            except (ValueError, TypeError):
                score_val = 0
                
            session.score = score_val
            session.feedback = str(data.get("feedback", "No detailed feedback provided."))
            
            if application:
                threshold = 70
                if job and hasattr(job, "selection_threshold") and job.selection_threshold is not None:
                    try:
                        threshold = int(job.selection_threshold)
                    except (ValueError, TypeError):
                        threshold = 70
                        
                passed = session.score >= threshold
                application.status = ApplicationStatus.shortlisted if passed else ApplicationStatus.rejected
                application.ai_feedback = {
                    "interview_score": session.score,
                    "interview_feedback": session.feedback,
                    "result": "Passed" if passed else "Failed"
                }
                
                if not passed:
                    application.rejection_reason = "Did not meet the AI interview score threshold."
                    
                logger.info(f"Application {application.id} {application.status.value} by AI with score {session.score}")
            
            await db.commit()
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Evaluation Error: {e}\n{error_details}")
            session.status = "failed"
            session.score = 0
            session.feedback = f"AI Evaluation Failed: {str(e)}"
            
            if application:
                application.status = ApplicationStatus.rejected
                application.rejection_reason = "AI Interview evaluation failed."
                application.ai_feedback = {
                    "interview_score": 0,
                    "interview_feedback": f"AI Evaluation Failed due to processing error: {str(e)}",
                    "error_details": str(e),
                    "result": "Failed"
                }
            await db.commit()
