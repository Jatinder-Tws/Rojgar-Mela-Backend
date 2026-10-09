"""Homepage assistant. A real model talks with the visitor and files an enquiry."""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.jobs_portal.controllers.career_enquiry_controller import create_career_enquiry
from app.modules.jobs_portal.models.career_enquiry import CareerEnquiry
from app.modules.jobs_portal.schemas.career_enquiry import CareerEnquiryCreate
from app.modules.jobs_portal.services.ai_service import get_ai

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/landing", tags=["landing-chat"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_QUESTION_RE = re.compile(
    r"[?？]|^(what|how|why|when|where|who|which|can |could |do |does |is |are |"
    r"tell me|kya\b|kaise|kyun|kyu\b|kab\b|kahan|mujhe|batao)\b",
    re.IGNORECASE,
)


class LandingChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(default="", max_length=4000)


class LandingChatIn(BaseModel):
    message: str = Field(default="", max_length=2000)
    language: str = Field(default="english", max_length=40)
    history: List[LandingChatTurn] = Field(default_factory=list)
    start: bool = False
    enquiry_id: Optional[str] = None


class LandingEnquiryFields(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    qualification: str = ""
    domain: str = ""
    preferred_call_time: str = ""
    interests: str = ""
    message: str = ""
    consent_to_contact: Optional[bool] = None
    visitor_query: str = ""


class LandingChatOut(BaseModel):
    reply: str
    options: List[str] = Field(default_factory=list)
    enquiry_id: Optional[str] = None
    saved: bool = False


def _system_prompt(language: str) -> str:
    return f"""You are the Rojgarmela.ai assistant on the public website. You are a person, not a form.
Speak in this language: {language}. If the visitor writes in another language or Hinglish, match them.
Understand what they actually said and answer that first, in your own words. Do not invent fees, salaries, guarantees, or private account data. If you are unsure, say the team will confirm.
Rojgarmela.ai helps people find jobs, helps employers hire, and includes AI job matching, resume and interview tools, courses, training, and job fairs. Support: info@rojgarmela.ai and +91-8968455531.

While you talk, learn enough to file an enquiry. The staff page shows: full name, email, 10-digit mobile, city, qualification, what they want help with, how they prefer to be contacted, interests, their main requirement, consent to contact, and any other question they asked.
Ask for only one missing detail at a time, and only when it fits the conversation. Never dump a list of questions.
Never ask a question you already asked in this chat, and never ask again for a detail the visitor already gave (name, email, phone, city, qualification, program, contact preference, or consent).
Leave visitor_query as an empty string. The server stores their extra questions.
Set ready_to_save to true only when you know name, email, a 10-digit mobile, qualification, what they need, their main requirement, and whether they agree to be contacted.
When ready_to_save is true, reply with only a short thank you and say the team will contact them shortly. Do not ask another question in that reply.
options may be up to 4 short replies they might tap, or an empty list. Leave options empty when you are thanking them.
Return JSON only:
{{
  "reply": "what you say next",
  "options": [],
  "ready_to_save": false,
  "fields": {{
    "full_name": "",
    "email": "",
    "phone": "",
    "location": "",
    "qualification": "",
    "domain": "",
    "preferred_call_time": "",
    "interests": "",
    "message": "",
    "consent_to_contact": null,
    "visitor_query": ""
  }}
}}
"""


def _strip_fence(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_ai(raw: str) -> dict:
    text = _strip_fence(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        data = None
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                data = None
    if not isinstance(data, dict):
        return {"reply": text[:1200], "options": [], "ready_to_save": False, "fields": {}}
    return data


def _clean(value: object, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:limit]


def _fields_from(data: dict) -> LandingEnquiryFields:
    raw = data.get("fields") if isinstance(data.get("fields"), dict) else {}
    consent = raw.get("consent_to_contact")
    if isinstance(consent, str):
        lowered = consent.strip().lower()
        consent = True if lowered in {"yes", "true", "y"} else False if lowered in {"no", "false", "n"} else None
    elif not isinstance(consent, bool):
        consent = None
    phone = re.sub(r"\D", "", _clean(raw.get("phone"), 20))
    if phone.startswith("91") and len(phone) == 12:
        phone = phone[2:]
    if phone.startswith("0") and len(phone) == 11:
        phone = phone[1:]
    return LandingEnquiryFields(
        full_name=_clean(raw.get("full_name"), 150),
        email=_clean(raw.get("email"), 150).lower(),
        phone=phone[:10],
        location=_clean(raw.get("location"), 200),
        qualification=_clean(raw.get("qualification"), 100),
        domain=_clean(raw.get("domain"), 150),
        preferred_call_time=_clean(raw.get("preferred_call_time"), 120),
        interests=_clean(raw.get("interests"), 2000),
        message=_clean(raw.get("message"), 2000),
        consent_to_contact=consent,
        visitor_query=_clean(raw.get("visitor_query"), 4000),
    )


def _ready(fields: LandingEnquiryFields) -> bool:
    phone_ok = len(fields.phone) == 10 and fields.phone[0] in "6789"
    return bool(
        len(fields.full_name) >= 2
        and _EMAIL_RE.match(fields.email)
        and phone_ok
        and fields.qualification
        and fields.domain
        and len(fields.message) >= 2
        and fields.consent_to_contact is not None
    )


_FIELD_ASK_RE = re.compile(
    r"\b(e-?mail|mail id|phone|mobile|whatsapp|number|naam|\bname\b|city|shehar|"
    r"location|qualification|education|degree|padhai|contact)\b",
    re.IGNORECASE,
)
_SLOT_PATTERNS = (
    ("email", re.compile(r"e-?mail|mail id", re.IGNORECASE)),
    ("phone", re.compile(r"phone|mobile|whatsapp|\bnumber\b", re.IGNORECASE)),
    ("name", re.compile(r"your name|full name|aapka naam|\bnaam\b", re.IGNORECASE)),
    ("city", re.compile(r"\bcity\b|location|shehar|kahan", re.IGNORECASE)),
    ("qualification", re.compile(r"qualification|education|degree|padhai", re.IGNORECASE)),
    ("consent", re.compile(r"consent|permission|contact you|sampark", re.IGNORECASE)),
)


def _known_values(fields: LandingEnquiryFields) -> set[str]:
    values = [
        fields.full_name,
        fields.email,
        fields.phone,
        fields.location,
        fields.qualification,
        fields.domain,
        fields.preferred_call_time,
        fields.interests,
        fields.message,
    ]
    return {item.strip().lower() for item in values if item and item.strip()}


def _norm_question(text: str) -> str:
    lowered = re.sub(r"[^a-z0-9\u0900-\u097f ]+", " ", (text or "").lower())
    return re.sub(r"\s+", " ", lowered).strip()


def _sentences(text: str) -> List[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if part.strip()]


def _answer_only(text: str) -> str:
    kept: List[str] = []
    for part in _sentences(text):
        if "?" in part and _FIELD_ASK_RE.search(part):
            break
        kept.append(part)
    answer = " ".join(kept).strip()
    return answer or (text or "").strip()


def _is_extra_question(text: str, known: set[str]) -> bool:
    cleaned = text.strip()
    if not cleaned or cleaned.lower() in known:
        return False
    return bool(_QUESTION_RE.search(cleaned) or len(cleaned.split()) > 8)


def _pairs_from_text(text: str) -> List[tuple[str, str]]:
    found: List[tuple[str, str]] = []
    pattern = re.compile(
        r"(?:^|\n)\s*(?:Q:|User:)\s*(.+?)\s*(?:\n\s*)?(?:A:|Assistant:|Answer:)\s*"
        r"(.+?)(?=(?:\n\s*(?:Q:|User:))|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(text or ""):
        question = re.sub(r"\s+", " ", match.group(1)).strip(" :")
        answer = re.sub(r"\s+", " ", match.group(2)).strip()
        if question and answer:
            found.append((question, answer))
    if found:
        return found
    for chunk in re.split(r"\n\s*\n", (text or "").strip()):
        match = re.match(r"(.+?)\n\s*Answer:\s*(.+)", chunk.strip(), re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        question = re.sub(r"\s+", " ", match.group(1)).strip()
        answer = re.sub(r"\s+", " ", match.group(2)).strip()
        if question and answer:
            found.append((question, answer))
    return found


def _format_pairs(pairs: List[tuple[str, str]]) -> str:
    blocks = [f"{question}\nAnswer: {answer}" for question, answer in pairs if question and answer]
    return "\n\n".join(blocks)[:4000]


def _extra_transcript(
    history: List[LandingChatTurn],
    current: str,
    reply: str,
    fields: LandingEnquiryFields,
) -> str:
    known = _known_values(fields)
    ordered: List[str] = []
    pairs: dict[str, tuple[str, str]] = {}

    def add(question: str, answer: str) -> None:
        key = _norm_question(question)
        answer_text = _answer_only(answer)
        if not key or not answer_text:
            return
        if key not in pairs:
            ordered.append(key)
        pairs[key] = (question.strip(), answer_text)

    pending = ""
    for turn in history:
        content = (turn.content or "").strip()
        if not content:
            continue
        if turn.role == "user":
            pending = content
            continue
        if _is_extra_question(pending, known):
            add(pending, content)
        pending = ""
    if _is_extra_question(current, known):
        add(current, reply)
    for question, answer in _pairs_from_text(fields.visitor_query):
        key = _norm_question(question)
        if key not in pairs:
            add(question, answer)
    return _format_pairs([pairs[key] for key in ordered])


def _asked_slots(history: List[LandingChatTurn]) -> set[str]:
    slots: set[str] = set()
    asked = set()
    for turn in history:
        if turn.role != "assistant":
            continue
        for part in _sentences(turn.content or ""):
            if "?" not in part:
                continue
            asked.add(_norm_question(part))
            for name, pattern in _SLOT_PATTERNS:
                if pattern.search(part):
                    slots.add(name)
    return slots | asked


def _without_repeated_questions(reply: str, history: List[LandingChatTurn]) -> str:
    asked = _asked_slots(history)
    kept: List[str] = []
    for part in _sentences(reply):
        if "?" not in part:
            kept.append(part)
            continue
        if _norm_question(part) in asked:
            continue
        if any(name in asked and pattern.search(part) for name, pattern in _SLOT_PATTERNS):
            continue
        kept.append(part)
    cleaned = " ".join(kept).strip()
    if cleaned:
        return cleaned
    return "I already have that. Tell me if there is anything else you want to know."


def _thanks(language: str) -> str:
    key = (language or "").strip().lower()
    if key == "hindi":
        return "धन्यवाद। आपकी enquiry सेव हो गई है। हम जल्द ही आपसे संपर्क करेंगे।"
    if key == "hinglish":
        return "Thank you. Aapki enquiry save ho gayi hai. Hum aapse jaldi contact karenge."
    return "Thank you. We have saved your enquiry and will contact you shortly."


def _options(data: dict) -> List[str]:
    raw = data.get("options")
    if not isinstance(raw, list):
        return []
    cleaned = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip()[:80])
    return cleaned[:4]


async def _save_or_update(
    fields: LandingEnquiryFields,
    enquiry_id: Optional[str],
    ready: bool,
    db: AsyncSession,
) -> tuple[Optional[str], bool]:
    visitor_query = fields.visitor_query or None
    if enquiry_id:
        try:
            enquiry_uuid = str(uuid.UUID(enquiry_id))
        except ValueError:
            enquiry_uuid = ""
        if enquiry_uuid:
            result = await db.execute(select(CareerEnquiry).where(CareerEnquiry.id == enquiry_uuid))
            row = result.scalar_one_or_none()
            if row:
                if fields.location:
                    row.location = fields.location
                if fields.preferred_call_time:
                    row.preferred_call_time = fields.preferred_call_time
                if fields.interests:
                    row.interests = fields.interests
                if fields.message:
                    row.message = fields.message
                if visitor_query:
                    row.visitor_query = visitor_query
                if fields.consent_to_contact is not None:
                    row.consent_to_contact = fields.consent_to_contact
                await db.commit()
                return row.id, False
    if not ready:
        return enquiry_id, False
    created = await create_career_enquiry(
        CareerEnquiryCreate(
            full_name=fields.full_name,
            email=fields.email,
            phone=fields.phone,
            qualification=fields.qualification,
            domain=fields.domain,
            message=fields.message,
            location=fields.location or None,
            preferred_call_time=fields.preferred_call_time or None,
            interests=fields.interests or None,
            visitor_query=visitor_query,
            consent_to_contact=bool(fields.consent_to_contact),
        ),
        db,
    )
    return created.id, True


@router.post("/chat", response_model=LandingChatOut)
async def landing_chat(
    body: LandingChatIn,
    db: AsyncSession = Depends(get_db),
) -> LandingChatOut:
    language = (body.language or "english").strip() or "english"
    history_lines = []
    for turn in body.history[-12:]:
        content = (turn.content or "").strip()
        if not content:
            continue
        label = "Visitor" if turn.role == "user" else "You"
        history_lines.append(f"{label}: {content[:700]}")
    if body.start:
        visitor = "The visitor just opened the chat. Greet them and ask how you can help."
    else:
        visitor = (body.message or "").strip() or "Hello"
    user_prompt = (
        f"Conversation so far:\n{chr(10).join(history_lines) or '(just started)'}\n\n"
        f"Visitor now: {visitor}\n\n"
        "Respond with JSON."
    )
    try:
        raw = await get_ai().chat_completion(_system_prompt(language), user_prompt)
    except Exception as exc:
        logger.warning("Landing chat AI failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="The AI service rejected this request. The Gemini API key is not valid, so I cannot answer yet.",
        ) from exc
    parsed = _parse_ai(raw)
    reply = _clean(parsed.get("reply"), 2000)
    if not reply:
        reply = "Tell me a bit more so I can help."
    if not body.start:
        reply = _without_repeated_questions(reply, body.history)
    fields = _fields_from(parsed)
    fields.visitor_query = _extra_transcript(
        body.history,
        "" if body.start else visitor,
        reply,
        fields,
    )
    ready = bool(parsed.get("ready_to_save")) and _ready(fields)
    saved_id, created = await _save_or_update(fields, body.enquiry_id, ready, db)
    options = [] if created else _options(parsed)
    if created:
        reply = _thanks(language)
    return LandingChatOut(
        reply=reply,
        options=options,
        enquiry_id=saved_id,
        saved=created,
    )
