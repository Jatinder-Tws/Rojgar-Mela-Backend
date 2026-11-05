"""Regression tests for training portal dashboard fee KPIs."""

from datetime import datetime, date
from types import SimpleNamespace

from app.modules.training_portal.services.training_portal_dashboard import (
    compute_fee_collection,
    _installment_collected_amount,
)


def _tx(*, amount: float, tx_type: str = "payment", status: str = "completed", day: str = "2026-03-01"):
    return SimpleNamespace(
        amount=amount,
        transaction_type=tx_type,
        status=status,
        created_at=datetime.fromisoformat(f"{day}T10:00:00"),
    )


def test_lifetime_fee_collection_uses_paid_amount_not_partial_transactions():
    """
    Repro: Fee Ledger Total Revenue = sum(paid_amount) = 35000, but dashboard
    preferred incomplete transaction rows and showed only 15000.
    """
    enrollments_paid = 2000 + 15000 + 18000  # 35000
    incomplete_txs = [_tx(amount=15000)]

    assert (
        compute_fee_collection(
            enrollments_paid_total=enrollments_paid,
            transactions=incomplete_txs,
            date_from=None,
            date_to=None,
        )
        == 35000.0
    )


def test_lifetime_fee_collection_ignores_transactions_even_when_higher():
    """Lifetime Ledger paid_amount is net-of-refunds source of truth for All period."""
    assert (
        compute_fee_collection(
            enrollments_paid_total=10000,
            transactions=[_tx(amount=50000)],
            date_from=None,
            date_to=None,
        )
        == 10000.0
    )


def test_date_filtered_prefers_transactions_in_range():
    txs = [
        _tx(amount=2000, day="2026-01-10"),
        _tx(amount=15000, day="2026-02-10"),
        _tx(amount=18000, day="2026-03-10"),
    ]
    assert (
        compute_fee_collection(
            enrollments_paid_total=35000,
            transactions=txs,
            date_from=date(2026, 2, 1),
            date_to=date(2026, 2, 28),
        )
        == 15000.0
    )


def test_date_filtered_falls_back_to_paid_amount_when_no_transactions():
    assert (
        compute_fee_collection(
            enrollments_paid_total=35000,
            transactions=[],
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
        )
        == 35000.0
    )


def test_date_filtered_nets_out_refunds():
    txs = [
        _tx(amount=18000, day="2026-03-01"),
        _tx(amount=3000, tx_type="refund", day="2026-03-05"),
    ]
    assert (
        compute_fee_collection(
            enrollments_paid_total=15000,
            transactions=txs,
            date_from=date(2026, 3, 1),
            date_to=date(2026, 3, 31),
        )
        == 15000.0
    )


def test_installment_collected_includes_partial_payments():
    assert _installment_collected_amount({"status": "paid", "amount": 10000, "paidAmount": 10000}) == 10000
    assert _installment_collected_amount({"status": "partially_paid", "amount": 10000, "paidAmount": 2000}) == 2000
    assert _installment_collected_amount({"status": "pending", "amount": 10000, "paidAmount": 0}) == 0
