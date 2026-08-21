"""Help desk AI bot — REST endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.shared.models.user import User
from app.core.dependencies import require_seeker_or_provider
from app.modules.super_admin.services.support_bot_knowledge import _support_contact

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support/bot", tags=["help-desk-bot"])


@router.get("/config")
async def bot_config(user: User = Depends(require_seeker_or_provider)):
    role = user.role.value if hasattr(user.role, "value") else str(user.role or "seeker")
    return {
        "modes": [
            {"id": "text", "label": "Text Chat", "description": "Chat with AI HelpDesk assistant"},
        ],
        "user_role": role,
        "support_contact": _support_contact(),
        "gemini_configured": bool(settings.GOOGLE_API_KEY),
    }
