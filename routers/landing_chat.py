"""Public landing chat API (no auth) — Gemini answers about Rojgarmela.ai."""

from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from services.landing_chat_service import generate_landing_reply

router = APIRouter(prefix="/landing", tags=["landing-chat"])


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class LandingChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    language: Optional[str] = Field(default="english", max_length=32)
    history: Optional[List[ChatTurn]] = Field(default=None, max_length=16)

    @field_validator("message")
    @classmethod
    def strip_message(cls, v: str) -> str:
        text = (v or "").strip()
        if not text:
            raise ValueError("message cannot be empty")
        return text

    @field_validator("language")
    @classmethod
    def normalize_language(cls, v: Optional[str]) -> str:
        return (v or "english").strip().lower() or "english"


class LandingChatResponse(BaseModel):
    reply: str
    options: List[str] = Field(default_factory=list)


@router.post("/chat", response_model=LandingChatResponse)
async def landing_chat(body: LandingChatRequest):
    try:
        history = [t.model_dump() for t in (body.history or [])]
        result = await generate_landing_reply(body.message, history, body.language)
        return LandingChatResponse(
            reply=result.get("reply") or "",
            options=list(result.get("options") or []),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="AI chat unavailable") from exc
