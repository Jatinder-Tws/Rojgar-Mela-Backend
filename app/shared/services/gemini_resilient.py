"""Shared Gemini generate_content with API-key rotation, model fallback, and backoff."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable, Sequence

import google.genai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiServiceUnavailable(Exception):
    """Raised when all keys/models are exhausted (typically quota / 429)."""


def gemini_api_keys() -> list[str]:
    keys: list[str] = []
    if settings.GEMINI_API_KEYS:
        keys.extend(k.strip() for k in settings.GEMINI_API_KEYS.split(",") if k.strip())
    if settings.GOOGLE_API_KEY and settings.GOOGLE_API_KEY not in keys:
        keys.insert(0, settings.GOOGLE_API_KEY)
    return keys


def gemini_chat_models() -> list[str]:
    fallbacks = [
        m.strip()
        for m in (settings.GEMINI_CHAT_MODEL_FALLBACKS or "").split(",")
        if m.strip()
    ]
    primary = settings.GEMINI_CHAT_MODEL
    ordered: list[str] = []
    for model in [primary, *fallbacks]:
        if model and model not in ordered:
            ordered.append(model)
    return ordered or [primary or "gemini-2.5-flash"]


def _is_quota_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "429" in text or "quota" in text or "resource exhausted" in text or "rate limit" in text


def _generate_sync(api_key: str, model: str, contents: Sequence[Any], config: dict[str, Any] | None):
    client = genai.Client(api_key=api_key)
    return client.models.generate_content(model=model, contents=list(contents), config=config or {})


async def generate_content_resilient(
    contents: Sequence[Any],
    *,
    config: dict[str, Any] | None = None,
    models: Iterable[str] | None = None,
) -> Any:
    keys = gemini_api_keys()
    if not keys:
        raise GeminiServiceUnavailable("Gemini is not configured. Set GOOGLE_API_KEY or GEMINI_API_KEYS.")

    model_list = list(models) if models is not None else gemini_chat_models()
    last_error: Exception | None = None

    for key_index, api_key in enumerate(keys):
        for model in model_list:
            for attempt in range(2):
                try:
                    return await asyncio.to_thread(
                        _generate_sync,
                        api_key,
                        model,
                        contents,
                        config,
                    )
                except Exception as exc:
                    last_error = exc
                    if _is_quota_error(exc):
                        delay = 1.5 * (attempt + 1)
                        logger.warning(
                            "Gemini quota/rate limit (key=%s model=%s attempt=%s): %s",
                            key_index,
                            model,
                            attempt + 1,
                            exc,
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise
            # try next model on repeated quota for this key
        # try next API key

    raise GeminiServiceUnavailable(
        "AI service is busy, please try again in a minute."
    ) from last_error
