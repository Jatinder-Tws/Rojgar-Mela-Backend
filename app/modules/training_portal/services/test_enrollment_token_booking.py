from datetime import datetime
from types import SimpleNamespace

from app.modules.training_portal.services.enrollment_token_booking import (
    apply_token_booking_fields,
    release_expired_token_seat,
)


def test_apply_token_booking_sets_canonical_status():
    enrollment = SimpleNamespace(
        status="active",
        payment_status="partially_paid",
        token_amount=None,
        token_paid_at=None,
        venue_visit_deadline=None,
        updated_at=None,
        paid_amount=2000,
    )

    apply_token_booking_fields(
        enrollment,
        2000,
        venue_visit_days=5,
        now=datetime(2026, 11, 5),
    )
    assert enrollment.status == "token_booked"
    assert enrollment.payment_status == "token_paid"
    assert enrollment.token_amount == 2000
    assert enrollment.token_paid_at == datetime(2026, 11, 5)
    assert enrollment.venue_visit_deadline is not None
    assert enrollment.paid_amount == 2000


def test_release_expired_token_seat_clears_batch_keeps_history():
    enrollment = SimpleNamespace(
        token_expired=False,
        batch_id="batch-1",
        batch_name="Morning",
        notes="Seat booking",
        paid_amount=2000,
        updated_at=None,
    )

    cleared = release_expired_token_seat(enrollment, now=datetime(2026, 11, 5))
    assert cleared is True
    assert enrollment.token_expired is True
    assert enrollment.batch_id is None
    assert enrollment.paid_amount == 2000
    assert "Seat released" in enrollment.notes
