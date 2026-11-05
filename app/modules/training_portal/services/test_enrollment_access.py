from app.modules.training_portal.services.enrollment_access import (
    has_learning_access,
    is_batch_assignable,
    is_fee_complete,
)


def test_pending_unpaid_blocked():
    assert has_learning_access(status="pending", payment_status="pending", paid_amount=0, balance_due=10000) is False


def test_active_but_pending_payment_blocked():
    """Unpaid pending must not unlock schedule / notes even if status is active."""
    assert has_learning_access(status="active", payment_status="pending", paid_amount=0, balance_due=5000) is False


def test_paid_online_allowed():
    assert has_learning_access(status="active", payment_status="paid_online", paid_amount=10000, balance_due=0) is True


def test_token_paid_blocks_content_keeps_seat_separate():
    """Token reserves the seat but must not unlock schedule / notes."""
    assert has_learning_access(
        status="token_booked",
        payment_status="token_paid",
        paid_amount=2000,
        balance_due=8000,
    ) is False
    assert has_learning_access(
        status="active",
        payment_status="token_paid",
        paid_amount=2000,
        balance_due=8000,
    ) is False


def test_legacy_token_booked_partially_paid_still_blocked():
    """Pre-fix verify left payment_status=partially_paid; status still locks content."""
    assert has_learning_access(
        status="token_booked",
        payment_status="partially_paid",
        paid_amount=2000,
        balance_due=23000,
    ) is False


def test_partially_paid_allowed():
    """Existing active+partial students keep learning access (no production regression)."""
    assert has_learning_access(status="active", payment_status="partially_paid", paid_amount=3000, balance_due=7000) is True


def test_free_allowed():
    assert has_learning_access(status="active", payment_status="free", paid_amount=0, balance_due=0) is True


def test_absconded_and_dropped_blocked():
    assert has_learning_access(status="absconded", payment_status="paid_online", paid_amount=10000, balance_due=0) is False
    assert has_learning_access(status="dropped", payment_status="paid_online", paid_amount=10000, balance_due=0) is False
    assert has_learning_access(status="active", payment_status="refunded", paid_amount=0, balance_due=0) is False


def test_fee_complete_by_amounts():
    """Odd label but fully settled amounts → allow (admin edge)."""
    assert has_learning_access(status="active", payment_status="", paid_amount=5000, balance_due=0) is True


def test_batch_assignable_after_first_emi():
    """First EMI (partially_paid + cash) → admin may assign batch; schedule unlocks once batch_id set."""
    assert is_fee_complete(
        payment_status="partially_paid", paid_amount=3000, balance_due=7000
    ) is False
    assert is_batch_assignable(
        status="active", payment_status="partially_paid", paid_amount=3000, balance_due=7000
    ) is True
    assert has_learning_access(
        status="active", payment_status="partially_paid", paid_amount=3000, balance_due=7000
    ) is True


def test_batch_assignable_full_fee():
    assert is_batch_assignable(
        status="active", payment_status="paid_offline", paid_amount=10000, balance_due=0
    ) is True


def test_batch_assignable_blocks_unpaid_and_token():
    assert is_batch_assignable(
        status="pending", payment_status="pending", paid_amount=0, balance_due=10000
    ) is False
    assert is_batch_assignable(
        status="active", payment_status="token_paid", paid_amount=2000, balance_due=8000
    ) is False
    assert is_batch_assignable(
        status="token_booked", payment_status="partially_paid", paid_amount=3000, balance_due=7000
    ) is False
    assert is_batch_assignable(
        status="dropped", payment_status="partially_paid", paid_amount=3000, balance_due=7000
    ) is False
