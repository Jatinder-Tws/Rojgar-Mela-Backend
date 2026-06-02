from datetime import datetime
from typing import Union
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from database import get_db
from models.user import User
from models.otp import OTPRecord
from schemas.auth import (
    RegisterRequest, RegisterResponse,
    VerifyOtpRequest, ResendOtpRequest,
    LoginRequest, TokenResponse, UserOut, OnboardingRequest, UpdateSettingsRequest, UnverifiedLoginResponse,
    SendPhoneOtpRequest, VerifyPhoneOtpRequest,
    TOTPSetupResponse, TOTPVerifyRequest, LoginResponse, TOTPStatusResponse, TOTPLoginRequest
)


from services.auth_service import (
    hash_password, verify_password, create_access_token,
    generate_otp, otp_expiry, get_current_user, require_verified
)
from services.email_service import send_otp_email, send_welcome_email
from services.totp_service import totp_service


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    # Check duplicate email or phone
    existing = await db.execute(
        select(User).where((User.email == body.email) | (User.phone == body.phone))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="An account with this email or phone already exists")

    # Generate TOTP secret
    secret = totp_service.generate_secret()

    user = User(
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        phone=body.phone,
        role=body.role,
        totp_secret=secret,
        is_verified=False,
        onboarding_complete=False,
        is_assessment_done=(body.role == "seeker") # Assuming and marking if seeker
    )
    if body.password:
        user.hashed_password = hash_password(body.password)

    db.add(user)
    await db.commit()
    await db.refresh(user)

    uri = totp_service.get_provisioning_uri(user.email or user.phone, secret)
    qr_base64 = totp_service.generate_qr_base64(uri)

    return LoginResponse(
        message="Registration initiated. Please scan the QR code to set up TOTP.",
        requires_setup=True,
        qr_code_base64=f"data:image/png;base64,{qr_base64}",
        user=UserOut.model_validate(user)
    )


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(body: VerifyOtpRequest, db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()

    # Find valid OTP
    result = await db.execute(
        select(OTPRecord).where(
            and_(
                OTPRecord.email == body.email,
                OTPRecord.code == body.code,
                OTPRecord.used == False,  # noqa
                OTPRecord.expires_at > now,
            )
        )
    )
    otp_record = result.scalar_one_or_none()
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP code")

    # Mark used
    otp_record.used = True

    # Verify user
    user_result = await db.execute(select(User).where(User.email == body.email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = True
    await db.commit()

    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/send-phone-otp")
async def send_phone_otp(body: SendPhoneOtpRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()
    
    is_new_user = False
    if not user:
        is_new_user = True
        # Create a stub user to store the TOTP secret
        user = User(
            phone=body.phone,
            is_verified=False, 
            onboarding_complete=False,
            is_assessment_done=False,
        )
        db.add(user)
        await db.flush() 
    
    if not user.totp_secret or user.is_first_login:
        # First time or forced first login: generate/show QR code
        if not user.totp_secret:
            secret = totp_service.generate_secret()
            user.totp_secret = secret
            await db.commit()
        else:
            secret = user.totp_secret
        
        uri = totp_service.get_provisioning_uri(user.phone, secret)
        qr_base64 = totp_service.generate_qr_base64(uri)
        
        return LoginResponse(
            message="Please scan the QR code to set up TOTP.",
            requires_setup=True,
            qr_code_base64=f"data:image/png;base64,{qr_base64}",
            requires_otp=not user.is_assessment_done
        )
    else:
        # Subsequent times: just signal that TOTP is needed
        return LoginResponse(
            message="Please enter the code from your authenticator app.",
            requires_totp=True
        )




@router.post("/verify-phone-otp", response_model=TokenResponse)
async def verify_phone_otp(body: VerifyPhoneOtpRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == body.phone))
    print(result)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please initiate login first.")
    
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP not set up for this phone number.")
        
    if totp_service.verify_code(user.totp_secret, body.code):
        user.is_verified = True
        user.totp_enabled = True # Mark enabled once first successful verification happens
        user.is_first_login = False # First login successfully completed
        await db.commit()
        
        token = create_access_token({"sub": user.id})
        return TokenResponse(access_token=token, user=UserOut.model_validate(user))
    else:
        raise HTTPException(status_code=400, detail="Invalid or expired TOTP code")



@router.post("/resend-otp")
async def resend_otp(
    body: ResendOtpRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user_result = await db.execute(select(User).where(User.email == body.email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    otp_code = generate_otp()
    otp_record = OTPRecord(email=body.email, code=otp_code, expires_at=otp_expiry())
    db.add(otp_record)
    await db.commit()

    background_tasks.add_task(send_otp_email, body.email, otp_code, user.first_name)
    return {"message": "OTP resent successfully"}


@router.post("/login")
async def login(body: LoginRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()

        # Check if user exists
        if not user:
            raise HTTPException(status_code=400, detail={"email": "No account found with this email"})
        
        # Check password
        if not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=400, detail={"general": "Incorrect password"})
        
        # If email not verified, send OTP automatically
        if not user.is_verified:
            otp_code = generate_otp()
            otp_record = OTPRecord(email=body.email, code=otp_code, expires_at=otp_expiry())
            db.add(otp_record)
            await db.commit()
            
            # Send OTP email asynchronously
            background_tasks.add_task(send_otp_email, body.email, otp_code, user.first_name)
            
            return LoginResponse(
                message="Email verification required. A new OTP has been sent to your email.",
                requires_otp=True,
                email=body.email
            )

        # Check if TOTP is enabled
        if user.totp_enabled:
            return LoginResponse(
                message="TOTP verification required.",
                requires_totp=True,
                email=body.email
            )

        token = create_access_token({"sub": user.id})
        return LoginResponse(
            access_token=token,
            user=UserOut.model_validate(user)
        )

    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=400, detail={"general": "An error occurred during login. Please try again."})




@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


# ── TOTP Endpoints ─────────────────────────────────────────────────────────

@router.get("/totp/status", response_model=TOTPStatusResponse)
async def get_totp_status(user: User = Depends(get_current_user)):
    return {"enabled": user.totp_enabled}


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def totp_setup(user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    # Generate secret if not exists or if they want to re-setup
    secret = totp_service.generate_secret()
    user.totp_secret = secret
    await db.commit()
    
    uri = totp_service.get_provisioning_uri(user.email, secret)
    qr_base64 = totp_service.generate_qr_base64(uri)
    
    return {
        "secret": secret,
        "qr_code_uri": uri,
        "qr_code_base64": f"data:image/png;base64,{qr_base64}"
    }


@router.post("/totp/enable")
async def totp_enable(body: TOTPVerifyRequest, user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP setup not initiated")
    
    if totp_service.verify_code(user.totp_secret, body.code):
        user.totp_enabled = True
        await db.commit()
        return {"message": "TOTP enabled successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")


@router.post("/totp/disable")
async def totp_disable(body: TOTPVerifyRequest, user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="TOTP is not enabled")
    
    if totp_service.verify_code(user.totp_secret, body.code):
        user.totp_enabled = False
        user.totp_secret = None
        await db.commit()
        return {"message": "TOTP disabled successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")


@router.post("/totp/verify", response_model=LoginResponse)
async def totp_verify(body: TOTPLoginRequest, db: AsyncSession = Depends(get_db)):
    # Verify password again for security or just assume they are in middle of login
    # For simplicity, we check user by email and verify password then TOTP
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
        
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="TOTP is not enabled for this user")
        
    if totp_service.verify_code(user.totp_secret, body.code):
        token = create_access_token({"sub": user.id})
        return LoginResponse(
            access_token=token,
            user=UserOut.model_validate(user)
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")


"""
AI Service – modular adapter pattern.
Swap OpenAI for any custom model by implementing AIProvider protocol.
GPT calls are batched to minimize API hits and token usage.
"""
from __future__ import annotations
import json
from typing import List, Optional, Protocol, runtime_checkable
from openai import AsyncOpenAI
from config import settings


@runtime_checkable
class AIProvider(Protocol):
    async def embed(self, text: str) -> List[float]: ...
    async def chat_completion(self, system: str, user: str) -> str: ...


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
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""


class MockAIAdapter:
    """Mock adapter for local dev – no API calls."""

    async def embed(self, text: str) -> List[float]:
        import hashlib, struct
        h = hashlib.sha256(text.encode()).digest()
        # Produce deterministic 1536-dim vector from hash (repeated)
        base = [struct.unpack("f", h[i % 32: i % 32 + 4])[0] for i in range(1536)]
        magnitude = sum(v ** 2 for v in base) ** 0.5 or 1.0
        return [v / magnitude for v in base]

    async def chat_completion(self, system: str, user: str) -> str:
        # Return mock JSON that downstream parsers expect
        return json.dumps([
            {"index": i, "score": 75 + i, "highlights": ["Strong technical background"], "gaps": ["Missing certification"], "fit_reason": "Good overall match"}
            for i in range(5)
        ])


def get_ai_provider() -> AIProvider:
    if settings.AI_MODE == "mock" or not settings.OPENAI_API_KEY:
        return MockAIAdapter()
    return OpenAIAdapter()


# Singleton
_ai_provider: Optional[AIProvider] = None


def get_ai() -> AIProvider:
    global _ai_provider
    if _ai_provider is None:
        _ai_provider = get_ai_provider()
    return _ai_provider


async def generate_next_assessment_question(history: List[dict], experience_level: str, domain_interest: str) -> str:
    ai = get_ai()
    
    # Adjust prompt based on experience level
    if "Student" in experience_level or "Fresher" in experience_level or "Entry" in experience_level:
        focus = "Focus primarily on social orientation, work style, creative expression, analytical thinking, helping orientation, achievements, and basic domain knowledge. Do NOT ask highly technical or advanced interview questions."
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
    
    history_text = "\n".join([f"Q: {item.get('question_text', item.get('question', ''))}\nA: {item.get('answer', '')}" for item in history])
    user_prompt = f"History:\n{history_text}\n\nGenerate the next question as JSON."
    
    try:
        response = await ai.chat_completion(system_prompt, user_prompt)
        # Clean up markdown if included
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
            
        data = json.loads(response.strip())
        return json.dumps(data)
    except Exception as e:
        print(f"Error generating question: {e}")
        return json.dumps({
            "question": "Which of the following best describes your approach to learning new concepts?",
            "options": ["Reading documentation", "Watching videos", "Building a project", "Taking a course"]
        })


async def generate_assessment_evaluation(history: List[dict], experience_level: str, domain_interest: str) -> dict:
    ai = get_ai()
    system_prompt = f"""
    You are an expert HR evaluator and strict technical assessor.
    Review the candidate's interview history. The candidate's experience is '{experience_level}' and domain interest is '{domain_interest}'.
    Based strictly on the accuracy, depth, and logic of their answers, analyze the following:
    1. Personality type (e.g., Analytical, Creative, Pragmatic, Leadership-oriented, Detail-Oriented, etc.)
    2. Estimated IQ score (an integer between 85 and 140). BE HARSH AND REALISTIC. Average answers should score around 95-105. Good answers 105-115. Only truly exceptional answers with deep reasoning should score 120+. If answers are short, incorrect, or generic, score below 100. Do not default to high scores like 125.
    3. Recommended specific job domains/roles they would excel in (list of 3 strings). Be specific to their actual demonstrated skills.
    4. A detailed 2-3 paragraph evaluation of their strengths, weaknesses, and overall fit. Be highly critical. Explicitly point out any incorrect answers, shallow responses, or generic guesses. Do not flatter the candidate.
    
    Return the response ONLY as a valid JSON object matching this schema exactly:
    {{
      "personality_type": "string",
      "iq_estimate": int,
      "recommended_domains": ["string", "string", "string"],
      "detailed_evaluation": "string"
    }}
    """
    
    history_text = "\n".join([f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}" for item in history])
    user_prompt = f"History:\n{history_text}\n\nEvaluate the candidate."
    
    try:
        response = await ai.chat_completion(system_prompt, user_prompt)
        
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
            "iq_estimate": data.get("iq_estimate", 100),
            "recommended_domains": data.get("recommended_domains", [domain_interest]),
            "detailed_evaluation": data.get("detailed_evaluation", "Evaluation generated based on your answers.")
        }
    except Exception as e:
        print(f"Error generating evaluation: {e}")
        return {
            "personality_type": "Analytical/Balanced",
            "iq_estimate": 105,
            "recommended_domains": [domain_interest, "General Tech"],
            "detailed_evaluation": "Based on the input provided, you show a balanced capability matching your selected domain."
        }



# ai_jobcreation_service.py 


# code with open ai 

import json
from config import settings
from openai import AsyncOpenAI

def get_openai_client():
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_job_descriptions(title: str):
    if not title:
        raise ValueError("title is required")

    client = get_openai_client()

    prompt = f"""
    Generate exactly 2 different job descriptions.

    JOB_TITLE: {title}

    Rules:
    - Infer experience level (Junior / Mid / Senior)
    - Each description should have 10–15 bullet points
    - Keep them different in tone and tools

    Return ONLY valid JSON:
    {{
      "description_1": "string",
      "description_2": "string"
    }}
    """

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a professional technical recruiter."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.4
    )

    content = response.choices[0].message.content

    try:
        data = json.loads(content)

        return {
            "description_1": data.get("description_1", ""),
            "description_2": data.get("description_2", ""),
        }

    except Exception as e:
        print("❌ JSON PARSE ERROR:", str(e))
        print("RAW:", content)

        raise ValueError("Invalid AI response format")
    
async def generate_job_skills(title: str):
    if not title:
        raise ValueError("title is required")

    client = get_openai_client()

    prompt = f"""
    Generate skills for the job.

    JOB_TITLE: {title}

    Rules:
    - Return 10–15 skills
    - Only single keywords (no sentences)
    - Include tools, technologies, and soft skills
    - No explanations

    Return ONLY JSON:
    {{
      "skills": ["skill1", "skill2", "skill3"]
    }}
    """

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a technical hiring expert."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    content = response.choices[0].message.content

    try:
        data = json.loads(content)

        return {
            "skills": data.get("skills", [])
        }

    except Exception as e:
        print("❌ JSON PARSE ERROR:", str(e))
        print("RAW:", content)

        raise ValueError("Invalid AI response format")
    

    # ai_improvement_suggestion_service.py 

import json
from config import settings
from openai import AsyncOpenAI

def get_openai_client():
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

def build_prompt(job_title, job_description, technologies, resume_text):
    return f"""
        Act as a senior technical recruiter.

        Analyze the resume against the job.

        JOB TITLE:
        {job_title}

        JOB DESCRIPTION:
        {job_description}

        TECH STACK:
        {", ".join(technologies)}

        RESUME:
        {resume_text}

        Return ONLY valid JSON with:
        - missing_skills (list)
        - improvements (list)
        - rewritten_bullets (list)
        - ats_keywords (list)
        - score (0-10)
        - futureTechToLearn (list)
        """

# async def analyze_resume(data, resume_text):
#     client = get_openai_client()

#     prompt = build_prompt(
#         data["job_title"],
#         data["job_description"],
#         data["technologies"],
#         resume_text
#     )

#     # ✅ FIX: add await
#     response = await client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[
#             {"role": "system", "content": "You are a professional resume reviewer."},
#             {"role": "user", "content": prompt}
#         ],
#         response_format={"type": "json_object"}
#     )

#     content = response.choices[0].message.content

#     try:
#         return json.loads(content)
#     except Exception:
#         return {
#             "missing_skills": [],
#             "improvements": [content],
#             "rewritten_bullets": [],
#             "ats_keywords": [],
#             "score": 0,
#             "futureTechToLearn":[]
#         }
    
async def analyze_resume_multi(data, resume_text):
    client = get_openai_client()

    prompt = build_prompt(
        data["job_title"],
        data["job_description"],
        data["technologies"],
        resume_text
    )

    # 🚀 Run both models in parallel
    import asyncio

    tasks = [
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a resume reviewer."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        ),
        client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a strict senior recruiter."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
    ]

    responses = await asyncio.gather(*tasks)

    results = []
    for res in responses:
        try:
            results.append(json.loads(res.choices[0].message.content))
        except:
            pass

    return merge_results(results)

def merge_results(results):
    final = {
        "missing_skills": [],
        "improvements": [],
        "rewritten_bullets": [],
        "ats_keywords": [],
        "score": 0,
        "futureTechToLearn": []
    }

    scores = []

    for r in results:
        final["missing_skills"] += r.get("missing_skills", [])
        final["improvements"] += r.get("improvements", [])
        final["rewritten_bullets"] += r.get("rewritten_bullets", [])
        final["ats_keywords"] += r.get("ats_keywords", [])
        final["futureTechToLearn"] += r.get("futureTechToLearn", [])

        if "score" in r:
            scores.append(r["score"])

    # ✅ Remove duplicates
    for key in final:
        if isinstance(final[key], list):
            final[key] = list(set(final[key]))

    # ✅ Average score
    final["score"] = sum(scores) / len(scores) if scores else 0

    return final