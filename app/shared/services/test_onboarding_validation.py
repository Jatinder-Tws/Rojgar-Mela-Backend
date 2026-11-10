from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.shared.models.user import UserRole
from app.shared.services.onboarding_validation import resolve_onboarding_role, validate_onboarding_payload


def test_resolve_locks_existing_seeker_role():
    assert resolve_onboarding_role(UserRole.seeker, "seeker") == UserRole.seeker


def test_resolve_rejects_role_flip():
    with pytest.raises(HTTPException) as exc:
        resolve_onboarding_role(UserRole.seeker, "provider")
    assert exc.value.status_code == 400
    assert "cannot be changed" in exc.value.detail


def test_resolve_allows_initial_role_when_unset():
    assert resolve_onboarding_role(None, "provider") == UserRole.provider


def test_seeker_requires_location_and_salary():
    with pytest.raises(HTTPException) as exc:
        validate_onboarding_payload(
            UserRole.seeker,
            SimpleNamespace(preferred_locations=[], salary_range="", job_type="in_office"),
        )
    assert "location" in exc.value.detail.lower()

    with pytest.raises(HTTPException) as exc2:
        validate_onboarding_payload(
            UserRole.seeker,
            SimpleNamespace(preferred_locations=["Mohali, Punjab"], salary_range="  ", job_type="in_office"),
        )
    assert "salary" in exc2.value.detail.lower()


def test_seeker_accepts_valid_payload():
    validate_onboarding_payload(
        UserRole.seeker,
        SimpleNamespace(
            preferred_locations=["Mohali, Punjab"],
            salary_range="3 - 6 LPA",
            job_type="hybrid",
        ),
    )


def test_provider_company_requires_details():
    with pytest.raises(HTTPException) as exc:
        validate_onboarding_payload(
            UserRole.provider,
            SimpleNamespace(
                industry="IT",
                company_type="company",
                company_name="",
                company_location="Mohali, Punjab",
                company_address="Sector 17",
            ),
        )
    assert "company name" in exc.value.detail.lower()


def test_provider_individual_only_needs_industry():
    validate_onboarding_payload(
        UserRole.provider,
        SimpleNamespace(
            industry="Manufacturing",
            company_type="individual",
            company_name=None,
            company_location=None,
            company_address=None,
        ),
    )
