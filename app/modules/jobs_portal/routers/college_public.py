from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.modules.super_admin.models.college_models import (
    College, CollegeCourse, CollegeSpecialization, CollegeApproval,
    CollegeEmiLoan, CollegeAdmissionExam, CollegePlacementPartner
)
from app.modules.super_admin.schemas.college_schemas import (
    CollegeCompareItem, CollegeCompareResponse, CollegeDetailOut,
    CollegeListItem, CollegeListResponse
)
from app.modules.super_admin.services.university_catalog_service import build_public_explore
from app.modules.super_admin.services.university_course_offers import build_course_offers

router = APIRouter(prefix="/api/v1/public/colleges", tags=["Public - Colleges & Comparison"])


@router.get("", response_model=CollegeListResponse)
async def list_public_colleges(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    course: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Public listing of colleges and universities."""
    query = select(College).where(College.is_active == True)

    if search:
        s = f"%{search.strip()}%"
        query = query.where(
            or_(
                College.name.ilike(s),
                College.city.ilike(s),
                College.state.ilike(s),
                College.approvals_summary.ilike(s)
            )
        )
    if state:
        query = query.where(College.state.ilike(f"%{state.strip()}%"))
    if city:
        query = query.where(College.city.ilike(f"%{city.strip()}%"))
    if type:
        query = query.where(College.type.ilike(f"%{type.strip()}%"))

    if course:
        # Filter colleges that offer this course
        c_sub = select(CollegeCourse.college_id).where(
            func.lower(CollegeCourse.course_name) == course.strip().lower()
        )
        query = query.where(College.id.in_(c_sub))

    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    import math
    total_pages = max(1, math.ceil(total / limit)) if limit > 0 else 1
    offset = (page - 1) * limit

    query = query.order_by(desc(College.cv_rating), desc(College.total_courses), College.name).offset(offset).limit(limit)
    res = await db.execute(query)
    colleges = res.scalars().all()

    items = [CollegeListItem.model_validate(c) for c in colleges]
    return CollegeListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.get("/explore")
async def get_university_explore(db: AsyncSession = Depends(get_db)):
    """Course categories and the universities section for /universities. Counts are live."""
    return await build_public_explore(db)


@router.get("/course-offers")
async def get_course_offers(
    course: str = Query(..., min_length=1),
    specialization: Optional[str] = Query(None),
    fee_min: Optional[float] = Query(None),
    fee_max: Optional[float] = Query(None),
    wants_emi: Optional[bool] = Query(None),
    sort: str = Query("reviews"),
    db: AsyncSession = Depends(get_db),
):
    """Universities offering one course, for the shortlist after the counselling questions."""
    return await build_course_offers(
        db,
        course=course,
        specialization=specialization,
        fee_min=fee_min,
        fee_max=fee_max,
        wants_emi=wants_emi,
        sort=sort if sort in {"reviews", "roi", "emi", "placements"} else "reviews",
    )


@router.get("/courses-list")
async def get_distinct_courses(db: AsyncSession = Depends(get_db)):
    """Returns distinct list of all course names available across colleges with count."""
    stmt = (
        select(CollegeCourse.course_name, func.count(distinct(CollegeCourse.college_id)))
        .group_by(CollegeCourse.course_name)
        .order_by(desc(func.count(distinct(CollegeCourse.college_id))))
    )
    res = await db.execute(stmt)
    rows = res.all()
    return [{"course_name": r[0], "colleges_count": r[1]} for r in rows if r[0]]


@router.get("/compare", response_model=CollegeCompareResponse)
async def compare_colleges(
    course_name: str = Query(..., description="Course name to compare, e.g. MBA, MCA"),
    college_ids: str = Query(..., description="Comma-separated list of college IDs"),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare 2 to 4 universities for a specific course side-by-side:
    Fees, duration, EMI, approvals, exam mode, placement partners.
    """
    ids = [i.strip() for i in college_ids.split(",") if i.strip()]
    if not ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No college IDs provided for comparison")

    stmt = (
        select(College)
        .where(College.id.in_(ids))
        .options(
            selectinload(College.courses).selectinload(CollegeCourse.specializations),
            selectinload(College.specializations),
            selectinload(College.approvals),
            selectinload(College.emi_loan),
            selectinload(College.admission_exam),
            selectinload(College.placement),
        )
    )
    res = await db.execute(stmt)
    colleges = res.scalars().all()

    items: List[CollegeCompareItem] = []

    for c in colleges:
        # Match course
        matched_course = next(
            (cr for cr in c.courses if cr.course_name.lower() == course_name.strip().lower()),
            None
        )
        if not matched_course and c.courses:
            # Loose partial match
            matched_course = next(
                (cr for cr in c.courses if course_name.lower() in cr.course_name.lower()),
                None
            )

        # Get specializations for this course
        specs = [
            s.specialization_name for s in c.specializations
            if s.course_name.lower() == course_name.strip().lower()
        ]
        if not specs and matched_course and matched_course.specializations:
            specs = [s.specialization_name for s in matched_course.specializations]

        item = CollegeCompareItem(
            college_id=c.id,
            college_name=c.name,
            college_slug=c.slug,
            logo_image=c.logo_image,
            city=c.city,
            state=c.state,
            cv_rating=c.cv_rating,
            type=c.type,
            whatsapp=c.whatsapp,
            helpline=c.helpline,
            official_admission_link=c.official_admission_link,
            prospectus_pdf=c.prospectus_pdf,
            # Course details
            course_name=matched_course.course_name if matched_course else course_name,
            display_name=matched_course.display_name if matched_course else course_name,
            duration=matched_course.duration if matched_course else None,
            duration_months=matched_course.duration_months if matched_course else None,
            base_total_fee=float(matched_course.base_total_fee) if matched_course and matched_course.base_total_fee else None,
            base_per_semester_fee=float(matched_course.base_per_semester_fee) if matched_course and matched_course.base_per_semester_fee else None,
            base_annual_fee=float(matched_course.base_annual_fee) if matched_course and matched_course.base_annual_fee else None,
            one_time_fee=float(matched_course.one_time_fee) if matched_course and matched_course.one_time_fee else None,
            est_monthly_emi=float(matched_course.est_monthly_emi) if matched_course and matched_course.est_monthly_emi else None,
            specializations_count=len(specs),
            specializations=specs,
            # Approvals
            approvals_list=c.approvals.approvals_list if c.approvals and c.approvals.approvals_list else [],
            ugc_deb=c.approvals.ugc_deb if c.approvals else None,
            aicte=c.approvals.aicte if c.approvals else None,
            naac=c.approvals.naac if c.approvals else None,
            nirf=c.approvals.nirf if c.approvals else None,
            wes=c.approvals.wes if c.approvals else None,
            # Loan / EMI
            no_cost_emi_available=c.emi_loan.no_cost_emi_available if c.emi_loan else None,
            loan_sanction_time=c.emi_loan.loan_sanction_time if c.emi_loan else None,
            lending_partners=c.emi_loan.lending_partners if c.emi_loan and c.emi_loan.lending_partners else [],
            bank_visit_required=c.emi_loan.bank_visit_required if c.emi_loan else None,
            # Admission & Exams
            examination_pattern_mode=c.admission_exam.examination_pattern_mode if c.admission_exam else None,
            admission_procedure=c.admission_exam.admission_procedure if c.admission_exam else None,
            important_dates_cutoffs=c.admission_exam.important_dates_cutoffs if c.admission_exam else None,
            # Placement
            hiring_companies=c.placement.hiring_companies if c.placement and c.placement.hiring_companies else [],
            placement_assistance_overview=c.placement.placement_assistance_overview if c.placement else None,
            highest_package=c.placement.highest_package if c.placement else None,
            average_package=c.placement.average_package if c.placement else None,
        )
        items.append(item)

    return CollegeCompareResponse(
        course_name=course_name,
        items=items
    )


@router.get("/{id_or_slug}", response_model=CollegeDetailOut)
async def get_public_college_detail(id_or_slug: str, db: AsyncSession = Depends(get_db)):
    """Public detail page of a single college/university."""
    stmt = (
        select(College)
        .where(or_(College.id == id_or_slug, College.slug == id_or_slug))
        .options(
            selectinload(College.courses).selectinload(CollegeCourse.specializations),
            selectinload(College.specializations),
            selectinload(College.approvals),
            selectinload(College.emi_loan),
            selectinload(College.admission_exam),
            selectinload(College.placement),
            selectinload(College.faculty),
        )
    )
    res = await db.execute(stmt)
    college = res.scalar_one_or_none()
    if not college or not college.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")

    return CollegeDetailOut.model_validate(college)
