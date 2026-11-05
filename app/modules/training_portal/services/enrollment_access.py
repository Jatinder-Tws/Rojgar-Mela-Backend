"""Candidate learning-content access rules for the training portal.

Seat reservation (token_paid / admin batch assign) is separate from content access.
Student-facing schedule and notes unlock only after meaningful fee progress.
Admin/teacher roster and management paths must NOT use this to hide students.
"""

from __future__ import annotations

from typing import Any


# Full / EMI / free / overdue → content. Token-only does NOT unlock content.
LEARNING_PAYMENT_STATUSES = frozenset(
    {
        "paid_online",
        "paid_offline",
        "free",
        "partially_paid",
        "overdue",
    }
)

BLOCKED_STATUSES = frozenset(
    {
        "dropped",
        "absconded",
        "payment_initiated",
        "token_booked",
    }
)

BLOCKED_PAYMENT_STATUSES = frozenset(
    {
        "refunded",
        "initiated",
        "token_paid",
        "pending",
    }
)


def _enrollment_money(
    enrollment: Any = None,
    *,
    status: str | None = None,
    payment_status: str | None = None,
    paid_amount: float | None = None,
    balance_due: float | None = None,
) -> tuple[str, str, float, float]:
    if enrollment is not None:
        status = getattr(enrollment, "status", None)
        payment_status = getattr(enrollment, "payment_status", None)
        paid_amount = getattr(enrollment, "paid_amount", 0)
        balance_due = getattr(enrollment, "balance_due", 0)

    status_value = (status or "").strip().lower()
    payment_value = (payment_status or "").strip().lower()
    try:
        paid = float(paid_amount or 0)
    except (TypeError, ValueError):
        paid = 0.0
    try:
        due = float(balance_due or 0)
    except (TypeError, ValueError):
        due = 0.0
    return status_value, payment_value, paid, due


def is_fee_complete(
    enrollment: Any = None,
    *,
    payment_status: str | None = None,
    paid_amount: float | None = None,
    balance_due: float | None = None,
) -> bool:
    """True when the full fee is settled (not merely first EMI)."""
    _status, payment_value, paid, due = _enrollment_money(
        enrollment,
        payment_status=payment_status,
        paid_amount=paid_amount,
        balance_due=balance_due,
    )
    if payment_value in ("paid_online", "paid_offline", "free"):
        return True
    return due <= 0.01 and paid > 0


def is_batch_assignable(
    enrollment: Any = None,
    *,
    status: str | None = None,
    payment_status: str | None = None,
    paid_amount: float | None = None,
    balance_due: float | None = None,
) -> bool:
    """True when admin may seat the student on a batch.

    Safe rule: full fee OR meaningful partial progress (first EMI / partially_paid /
    overdue with cash received). Token-only and unpaid pending stay blocked.
    """
    status_value, payment_value, paid, due = _enrollment_money(
        enrollment,
        status=status,
        payment_status=payment_status,
        paid_amount=paid_amount,
        balance_due=balance_due,
    )
    if status_value in BLOCKED_STATUSES:
        return False
    if payment_value in ("refunded", "initiated", "pending", "token_paid"):
        return False
    if is_fee_complete(
        payment_status=payment_value,
        paid_amount=paid,
        balance_due=due,
    ):
        return True
    # First EMI / ongoing EMI: cash received, balance remains.
    if payment_value in ("partially_paid", "overdue") and paid > 0.01:
        return True
    return False


def has_learning_access(
    enrollment: Any = None,
    *,
    status: str | None = None,
    payment_status: str | None = None,
    paid_amount: float | None = None,
    balance_due: float | None = None,
) -> bool:
    """Return True when the candidate may view schedule / notes for this enrollment."""
    status_value, payment_value, paid, due = _enrollment_money(
        enrollment,
        status=status,
        payment_status=payment_status,
        paid_amount=paid_amount,
        balance_due=balance_due,
    )

    if status_value in BLOCKED_STATUSES:
        return False
    if payment_value in BLOCKED_PAYMENT_STATUSES:
        return False
    if payment_value in LEARNING_PAYMENT_STATUSES:
        return True

    # Fee settled by amounts even if payment_status label is odd (admin edge cases).
    return due <= 0.01 and paid > 0
