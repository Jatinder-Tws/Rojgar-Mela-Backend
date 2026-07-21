"""Training portal payment integration (Razorpay + dev mock)."""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


def razorpay_configured() -> bool:
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


async def create_razorpay_refund(
    payment_id: str,
    amount_paise: Optional[int] = None,
) -> dict[str, Any]:
    """Refund a captured Razorpay payment (full refund if amount_paise omitted)."""
    if not razorpay_configured() or payment_id.startswith("pay_mock_"):
        return {"id": f"rfnd_mock_{uuid.uuid4().hex[:12]}", "mock": True}

    auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    payload: dict[str, Any] = {}
    if amount_paise is not None:
        payload["amount"] = amount_paise

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://api.razorpay.com/v1/payments/{payment_id}/refund",
            auth=auth,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        data["mock"] = False
        return data


async def create_razorpay_order(amount_paise: int, receipt: str, notes: Optional[dict[str, str]] = None) -> dict[str, Any]:
    if not razorpay_configured():
        return {
            "id": f"order_mock_{uuid.uuid4().hex[:12]}",
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "status": "created",
            "mock": True,
        }

    auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    payload = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
        "notes": notes or {},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.razorpay.com/v1/orders",
            auth=auth,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        data["mock"] = False
        return data


def verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    if not settings.RAZORPAY_KEY_SECRET:
        return True
    body = f"{order_id}|{payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    secret = settings.RAZORPAY_WEBHOOK_SECRET or settings.RAZORPAY_KEY_SECRET
    if not secret:
        return True
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_webhook_payment(payload: dict[str, Any]) -> Optional[dict[str, str]]:
    try:
        event = payload.get("event", "")
        if event not in ("payment.captured", "payment.failed"):
            return None
        entity = payload["payload"]["payment"]["entity"]
        return {
            "event": event,
            "provider_order_id": entity.get("order_id") or "",
            "provider_payment_id": entity.get("id") or "",
            "status": entity.get("status") or "captured",
        }
    except (KeyError, TypeError):
        return None


def mock_payment_ids(order_id: str) -> tuple[str, str]:
    payment_id = f"pay_mock_{uuid.uuid4().hex[:12]}"
    signature = hashlib.sha256(f"{order_id}|{payment_id}".encode()).hexdigest()
    return payment_id, signature
