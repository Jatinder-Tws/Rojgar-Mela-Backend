"""Token seat-booking field application (verify + webhook share this).

Does not delete or rewrite historical fee/transactions — only sets booking fields
on the enrollment row after a successful token payment.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def apply_token_booking_fields(
    enrollment: Any,
    token_amount: float,
    *,
    venue_visit_days: int,
    now: datetime | None = None,
) -> None:
    """Canonical post-token state: seat booked, payment_status=token_paid.

    Safe to call on already-booked rows (idempotent for status/payment_status).
    Does not clear paid_amount / transactions.
    """
    when = now or datetime.utcnow()
    amount = float(token_amount or 0)

    enrollment.status = "token_booked"
    enrollment.payment_status = "token_paid"
    enrollment.token_amount = amount
    if not getattr(enrollment, "token_paid_at", None):
        enrollment.token_paid_at = when
    if not getattr(enrollment, "venue_visit_deadline", None):
        enrollment.venue_visit_deadline = enrollment.token_paid_at + timedelta(days=int(venue_visit_days))
    enrollment.updated_at = when


def release_expired_token_seat(
    enrollment: Any,
    *,
    now: datetime | None = None,
) -> bool:
    """Mark token expired and free the batch seat without deleting fee history.

    Returns True if a seat (batch_id) was cleared.
    """
    when = now or datetime.utcnow()
    enrollment.token_expired = True
    enrollment.updated_at = when
    cleared = False
    if getattr(enrollment, "batch_id", None):
        note = "Seat released after venue-visit deadline expiry (fee/token history retained)."
        existing = (getattr(enrollment, "notes", None) or "").strip()
        enrollment.notes = f"{existing} | {note}".strip(" |") if existing else note
        enrollment.batch_id = None
        cleared = True
    return cleared
