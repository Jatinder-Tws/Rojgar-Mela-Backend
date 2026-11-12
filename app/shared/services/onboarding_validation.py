"""Server-side onboarding rules aligned with the existing FE Onboarding form."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException

from app.shared.models.user import CompanyType, JobType, UserRole


def _role_value(role: Any) -> Optional[str]:
    if role is None:
        return None
    return role.value if hasattr(role, "value") else str(role)


def resolve_onboarding_role(current_role: Any, requested_role: str) -> UserRole:
    """Lock seeker/provider role after registration; reject flips."""
    try:
        requested = UserRole(requested_role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'seeker' or 'provider'") from exc

    if requested not in (UserRole.seeker, UserRole.provider):
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'seeker' or 'provider'")

    current = _role_value(current_role)
    if current in (UserRole.seeker.value, UserRole.provider.value):
        if requested.value != current:
            raise HTTPException(
                status_code=400,
                detail="Role cannot be changed after registration. Complete onboarding with your registered role.",
            )
        return UserRole(current)
    return requested


def validate_onboarding_payload(role: UserRole, body: Any) -> None:
    """Raise 400 if required onboarding fields are missing (matches FE isFormValid)."""
    if role == UserRole.seeker:
        locations = [str(x).strip() for x in (getattr(body, "preferred_locations", None) or []) if str(x).strip()]
        if not locations:
            raise HTTPException(status_code=400, detail="Preferred location is required")
        salary = (getattr(body, "salary_range", None) or "").strip()
        if not salary:
            raise HTTPException(status_code=400, detail="Salary range is required")
        job_type = getattr(body, "job_type", None)
        if job_type:
            try:
                JobType(job_type)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid job type. Must be 'in_office', 'wfh', or 'hybrid'",
                ) from exc
        job_role = getattr(body, "job_role", None)
        if job_role is not None and str(job_role).strip():
            from app.shared.validators.job_role import job_role_error

            error = job_role_error(str(job_role), required=False)
            if error:
                raise HTTPException(status_code=400, detail=error)
        return

    if role == UserRole.provider:
        industry = (getattr(body, "industry", None) or "").strip()
        if not industry:
            raise HTTPException(status_code=400, detail="Industry is required")

        company_type_raw = getattr(body, "company_type", None)
        if not company_type_raw:
            raise HTTPException(status_code=400, detail="Company type is required")
        try:
            company_type = CompanyType(company_type_raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="Invalid company type. Must be 'individual' or 'company'",
            ) from exc

        if company_type == CompanyType.company:
            if not (getattr(body, "company_name", None) or "").strip():
                raise HTTPException(status_code=400, detail="Company name is required")
            if not (getattr(body, "company_location", None) or "").strip():
                raise HTTPException(status_code=400, detail="Company location is required")
            if not (getattr(body, "company_address", None) or "").strip():
                raise HTTPException(status_code=400, detail="Company address is required")
        return

    raise HTTPException(status_code=400, detail="Invalid role. Must be 'seeker' or 'provider'")
