import logging
import math
from typing import Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.super_admin.models.college_models import (
    College, CollegeCourse, CollegeSpecialization, CollegeApproval,
    CollegeEmiLoan, CollegeAdmissionExam, CollegePlacementPartner, CollegeFaculty
)
from app.modules.super_admin.schemas.college_schemas import (
    CollegeCreate, CollegeDetailOut, CollegeListItem, CollegeListResponse,
    CollegeUpdate, ExcelImportSummary
)
from app.modules.super_admin.services.college_importer_service import (
    import_colleges_excel, slugify
)
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


async def list_colleges_ctrl(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    ctype: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> CollegeListResponse:
    query = select(College)

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
    if ctype:
        query = query.where(College.type.ilike(f"%{ctype.strip()}%"))
    if is_active is not None:
        query = query.where(College.is_active == is_active)

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

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


async def get_college_detail_ctrl(db: AsyncSession, id_or_slug: str) -> CollegeDetailOut:
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
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="University/College not found")

    return CollegeDetailOut.model_validate(college)


async def create_college_ctrl(db: AsyncSession, payload: CollegeCreate) -> CollegeDetailOut:
    # Check if college with name exists
    stmt = select(College).where(func.lower(College.name) == payload.name.strip().lower())
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A college with name '{payload.name}' already exists. Use update instead to prevent duplicates."
        )

    slug = payload.slug or slugify(payload.name)
    # Ensure unique slug
    base_slug = slug
    counter = 1
    while True:
        s_stmt = select(College).where(College.slug == slug)
        if not (await db.execute(s_stmt)).scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    college_dict = payload.model_dump(
        exclude={"courses", "specializations", "approvals", "emi_loan", "admission_exam", "placement", "faculty"}
    )
    college_dict["slug"] = slug

    college = College(**college_dict)
    db.add(college)
    await db.flush()

    # Add approvals if provided
    if payload.approvals:
        db.add(CollegeApproval(college_id=college.id, **payload.approvals.model_dump()))
    # Add loan if provided
    if payload.emi_loan:
        db.add(CollegeEmiLoan(college_id=college.id, **payload.emi_loan.model_dump()))
    # Add admission/exams if provided
    if payload.admission_exam:
        db.add(CollegeAdmissionExam(college_id=college.id, **payload.admission_exam.model_dump()))
    # Add placement if provided
    if payload.placement:
        db.add(CollegePlacementPartner(college_id=college.id, **payload.placement.model_dump()))

    # Add courses & specializations
    for c_in in payload.courses or []:
        c_dict = c_in.model_dump(exclude={"specializations"})
        if not c_dict.get("course_slug"):
            c_dict["course_slug"] = slugify(c_dict["course_name"])
        course = CollegeCourse(college_id=college.id, **c_dict)
        db.add(course)
        await db.flush()

        for s_in in c_in.specializations or []:
            s_dict = s_in.model_dump()
            s_dict["course_name"] = course.course_name
            if not s_dict.get("specialization_slug"):
                s_dict["specialization_slug"] = slugify(s_dict["specialization_name"])
            spec = CollegeSpecialization(college_id=college.id, college_course_id=course.id, **s_dict)
            db.add(spec)

    # Standalone specializations if any
    for s_in in payload.specializations or []:
        s_dict = s_in.model_dump()
        if not s_dict.get("specialization_slug"):
            s_dict["specialization_slug"] = slugify(s_dict["specialization_name"])
        spec = CollegeSpecialization(college_id=college.id, **s_dict)
        db.add(spec)

    # Add faculty
    for f_in in payload.faculty or []:
        db.add(CollegeFaculty(college_id=college.id, **f_in.model_dump()))

    await db.commit()
    return await get_college_detail_ctrl(db, college.id)


async def update_college_ctrl(db: AsyncSession, college_id: str, payload: CollegeUpdate) -> CollegeDetailOut:
    stmt = (
        select(College)
        .where(College.id == college_id)
        .options(
            selectinload(College.courses),
            selectinload(College.approvals),
            selectinload(College.emi_loan),
            selectinload(College.admission_exam),
            selectinload(College.placement),
            selectinload(College.faculty),
        )
    )
    res = await db.execute(stmt)
    college = res.scalar_one_or_none()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")

    upd_data = payload.model_dump(exclude_unset=True)

    # Handle sub-entities
    if "approvals" in upd_data:
        app_data = upd_data.pop("approvals")
        if app_data is not None:
            if college.approvals:
                for k, v in app_data.items():
                    setattr(college.approvals, k, v)
            else:
                db.add(CollegeApproval(college_id=college.id, **app_data))

    if "emi_loan" in upd_data:
        loan_data = upd_data.pop("emi_loan")
        if loan_data is not None:
            if college.emi_loan:
                for k, v in loan_data.items():
                    setattr(college.emi_loan, k, v)
            else:
                db.add(CollegeEmiLoan(college_id=college.id, **loan_data))

    if "admission_exam" in upd_data:
        exam_data = upd_data.pop("admission_exam")
        if exam_data is not None:
            if college.admission_exam:
                for k, v in exam_data.items():
                    setattr(college.admission_exam, k, v)
            else:
                db.add(CollegeAdmissionExam(college_id=college.id, **exam_data))

    if "placement" in upd_data:
        plc_data = upd_data.pop("placement")
        if plc_data is not None:
            if college.placement:
                for k, v in plc_data.items():
                    setattr(college.placement, k, v)
            else:
                db.add(CollegePlacementPartner(college_id=college.id, **plc_data))

    if "courses" in upd_data:
        courses_in = upd_data.pop("courses")
        if courses_in is not None:
            # Delete old courses & replace
            for old_c in college.courses:
                await db.delete(old_c)
            await db.flush()
            for c_item in courses_in:
                c_dict = {k: v for k, v in c_item.items() if k != "specializations"}
                if not c_dict.get("course_slug"):
                    c_dict["course_slug"] = slugify(c_dict["course_name"])
                new_c = CollegeCourse(college_id=college.id, **c_dict)
                db.add(new_c)
                await db.flush()
                for s_item in c_item.get("specializations", []):
                    s_item["course_name"] = new_c.course_name
                    if not s_item.get("specialization_slug"):
                        s_item["specialization_slug"] = slugify(s_item["specialization_name"])
                    db.add(CollegeSpecialization(college_id=college.id, college_course_id=new_c.id, **s_item))

    if "faculty" in upd_data:
        fac_in = upd_data.pop("faculty")
        if fac_in is not None:
            for old_f in college.faculty:
                await db.delete(old_f)
            await db.flush()
            for f_item in fac_in:
                db.add(CollegeFaculty(college_id=college.id, **f_item))

    # Update master college fields
    for k, v in upd_data.items():
        if v is not None:
            setattr(college, k, v)

    await db.commit()
    return await get_college_detail_ctrl(db, college.id)


async def delete_college_ctrl(db: AsyncSession, college_id: str) -> dict:
    stmt = select(College).where(College.id == college_id)
    res = await db.execute(stmt)
    college = res.scalar_one_or_none()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")

    await db.delete(college)
    await db.commit()
    return {"success": True, "message": f"University '{college.name}' deleted successfully."}


async def import_colleges_file_ctrl(db: AsyncSession, file: UploadFile) -> ExcelImportSummary:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    
    filename = file.filename or "colleges.xlsx"
    try:
        return await import_colleges_excel(contents, filename, db)
    except IntegrityError as e:
        await db.rollback()
        err_msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Import failed due to duplicate data: {err_msg}",
        )
