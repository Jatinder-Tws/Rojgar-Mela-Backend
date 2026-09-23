"""Universities that offer one course, with the fields the public shortlist needs."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.super_admin.models.college_models import (
    College,
    CollegeApproval,
    CollegeCourse,
    CollegeEmiLoan,
    CollegePlacementPartner,
    CollegeSpecialization,
)


def _money(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return amount if amount > 0 else None


def _approval_names(raw: Any, summary: Optional[str]) -> list[str]:
    if isinstance(raw, list) and raw:
        names = [str(item).strip() for item in raw if str(item).strip()]
        if names:
            return names[:8]
    text = (summary or "").strip()
    if not text:
        return []
    return [part.strip() for part in text.replace("|", ",").split(",") if part.strip()][:8]


async def build_course_offers(
    db: AsyncSession,
    *,
    course: str,
    specialization: Optional[str] = None,
    fee_min: Optional[float] = None,
    fee_max: Optional[float] = None,
    wants_emi: Optional[bool] = None,
    sort: str = "reviews",
) -> dict[str, Any]:
    course_name = course.strip()
    empty = {
        "course_name": course_name,
        "total": 0,
        "specializations": [],
        "states": [],
        "items": [],
    }
    if not course_name:
        return empty

    course_rows = (
        await db.execute(
            select(
                College.id,
                College.name,
                College.slug,
                College.logo_image,
                College.city,
                College.state,
                College.cv_rating,
                College.total_reviews,
                College.total_courses,
                College.established_year,
                College.approvals_summary,
                CollegeCourse.duration,
                CollegeCourse.base_total_fee,
                CollegeCourse.base_per_semester_fee,
            )
            .join(CollegeCourse, CollegeCourse.college_id == College.id)
            .where(
                College.is_active.is_(True),
                CollegeCourse.course_name == course_name,
            )
        )
    ).all()
    if not course_rows:
        return empty

    college_ids = [row.id for row in course_rows]
    spec_rows = (
        await db.execute(
            select(CollegeSpecialization.college_id, CollegeSpecialization.specialization_name).where(
                CollegeSpecialization.college_id.in_(college_ids),
                CollegeSpecialization.course_name == course_name,
            )
        )
    ).all()
    approval_rows = (
        await db.execute(
            select(CollegeApproval.college_id, CollegeApproval.approvals_list, CollegeApproval.naac).where(
                CollegeApproval.college_id.in_(college_ids)
            )
        )
    ).all()
    emi_rows = (
        await db.execute(
            select(CollegeEmiLoan.college_id, CollegeEmiLoan.no_cost_emi_available).where(
                CollegeEmiLoan.college_id.in_(college_ids)
            )
        )
    ).all()
    placement_rows = (
        await db.execute(
            select(
                CollegePlacementPartner.college_id,
                CollegePlacementPartner.highest_package,
                CollegePlacementPartner.average_package,
                CollegePlacementPartner.hiring_companies,
            ).where(CollegePlacementPartner.college_id.in_(college_ids))
        )
    ).all()

    specs_by_college: dict[str, list[str]] = {}
    spec_names: set[str] = set()
    for college_id, name in spec_rows:
        cleaned = (name or "").strip()
        if not cleaned:
            continue
        spec_names.add(cleaned)
        specs_by_college.setdefault(college_id, [])
        if cleaned not in specs_by_college[college_id]:
            specs_by_college[college_id].append(cleaned)

    approvals_by_college = {row.college_id: row for row in approval_rows}
    emi_by_college = {row.college_id: (row.no_cost_emi_available or "").strip() for row in emi_rows}
    placement_by_college = {row.college_id: row for row in placement_rows}

    wanted_spec = (specialization or "").strip()
    if wanted_spec.lower() in {"", "help me decide"}:
        wanted_spec = ""

    items: list[dict[str, Any]] = []
    for row in course_rows:
        specs = specs_by_college.get(row.id, [])
        if wanted_spec and wanted_spec.lower() not in {name.lower() for name in specs}:
            continue

        total_fee = _money(row.base_total_fee)
        semester_fee = _money(row.base_per_semester_fee)
        comparable_fee = total_fee if total_fee is not None else semester_fee
        if comparable_fee is not None:
            if fee_min is not None and comparable_fee < fee_min:
                continue
            if fee_max is not None and comparable_fee > fee_max:
                continue

        emi_text = emi_by_college.get(row.id, "")
        has_emi = bool(emi_text) and emi_text.lower() not in {"no", "n", "false", "0"}
        approval = approvals_by_college.get(row.id)
        placement = placement_by_college.get(row.id)
        placement_score = 0
        if placement and (placement.highest_package or placement.average_package or placement.hiring_companies):
            placement_score = 1

        highlights: list[str] = []
        if specs:
            highlights.append(f"{len(specs)} specializations in this course")
        if row.total_courses:
            highlights.append(f"{int(row.total_courses)} courses listed")
        if approval and approval.naac:
            highlights.append(f"NAAC {approval.naac}")
        if placement and placement.highest_package:
            highlights.append(f"Highest package {placement.highest_package}")
        elif placement and placement.average_package:
            highlights.append(f"Average package {placement.average_package}")
        if emi_text:
            highlights.append(f"EMI: {emi_text}")
        if row.established_year:
            highlights.append(f"Established {row.established_year}")

        items.append(
            {
                "id": row.id,
                "name": row.name,
                "slug": row.slug,
                "logo_image": row.logo_image,
                "city": row.city,
                "state": row.state,
                "approvals": _approval_names(
                    approval.approvals_list if approval else None,
                    row.approvals_summary,
                ),
                "rating": row.cv_rating or 0,
                "reviews": row.total_reviews or 0,
                "per_semester_fee": semester_fee,
                "total_fee": total_fee,
                "duration": row.duration,
                "emi_available": has_emi,
                "emi_label": emi_text or None,
                "highlights": highlights[:4],
                "specializations": specs[:12],
                "_fee": comparable_fee if comparable_fee is not None else 10**12,
                "_placement": placement_score,
            }
        )

    if wants_emi is True:
        with_emi = [item for item in items if item["emi_available"]]
        if with_emi:
            items = with_emi

    if sort == "roi":
        items.sort(key=lambda item: (item["_fee"], -(item["rating"] or 0), item["name"].lower()))
    elif sort == "emi":
        items.sort(key=lambda item: (not item["emi_available"], -(item["rating"] or 0), item["name"].lower()))
    elif sort == "placements":
        items.sort(key=lambda item: (-item["_placement"], -(item["rating"] or 0), -item["reviews"], item["name"].lower()))
    else:
        items.sort(key=lambda item: (-(item["rating"] or 0), -item["reviews"], item["name"].lower()))

    for item in items:
        item.pop("_fee", None)
        item.pop("_placement", None)

    states = sorted({item["state"] for item in items if item.get("state")})
    return {
        "course_name": course_name,
        "total": len(items),
        "specializations": sorted(spec_names, key=str.lower),
        "states": states,
        "items": items,
    }
