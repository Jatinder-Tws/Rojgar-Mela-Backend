from __future__ import annotations

from typing import Optional

import httpx

from app.core.config import settings


async def verify_turnstile(token: Optional[str], ip_address: Optional[str] = None) -> bool:
    secret = (settings.TURNSTILE_SECRET_KEY or "").strip()
    if not secret:
        return True
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": secret,
                    "response": token,
                    "remoteip": ip_address or "",
                },
            )
            data = response.json()
            return bool(data.get("success"))
    except Exception:
        return False


def captcha_configured() -> bool:
    return bool((settings.TURNSTILE_SECRET_KEY or "").strip() and (settings.TURNSTILE_SITE_KEY or "").strip())
