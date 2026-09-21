import io
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.super_admin.models.college_models import (
    College, CollegeCourse, CollegeSpecialization, CollegeApproval,
    CollegeEmiLoan, CollegeAdmissionExam, CollegePlacementPartner, CollegeFaculty
)
from app.modules.super_admin.schemas.college_schemas import ExcelImportSummary

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """Generate a clean URL-friendly slug."""
    if not text:
        return ""
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", text)


def parse_numeric(val: Any) -> Optional[float]:
    """Clean monetary or numeric strings like '₹ 1,50,000', '1.5 Lakh' into float."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s or s.lower() in ["na", "n/a", "-", "--", "none", "null"]:
        return None
    # Remove currency symbol and commas
    cleaned = re.sub(r"[₹$,\s]", "", s)
    # Check for lakh/crore if any
    lakh_match = re.match(r"^([\d.]+)\s*lakh", cleaned, re.IGNORECASE)
    if lakh_match:
        try:
            return float(lakh_match.group(1)) * 100000
        except ValueError:
            pass
    # Extract leading float
    num_match = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if num_match:
        try:
            return float(num_match.group(0))
        except ValueError:
            pass
    return None


def parse_months(val: Any) -> Optional[int]:
    """Parse duration like '2 Years' -> 24 or '24 Months' -> 24."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip().lower()
    if "year" in s:
        m = re.search(r"(\d+(\.\d+)?)", s)
        if m:
            try:
                return int(float(m.group(1)) * 12)
            except ValueError:
                pass
    elif "month" in s:
        m = re.search(r"(\d+)", s)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    else:
        m = re.search(r"(\d+)", s)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return None


def parse_list(val: Any) -> List[str]:
    """Parse comma, pipe, or newline delimited strings into clean list of strings."""
    if val is None or pd.isna(val):
        return []
    if isinstance(val, list):
        return [str(item).strip() for item in val if str(item).strip()]
    s = str(val).strip()
    if not s or s.lower() in ["na", "n/a", "-", "none"]:
        return []
    # Split on comma, semicolon, or pipe
    items = re.split(r"[,|;\n]+", s)
    return [item.strip() for item in items if item.strip()]


def clean_col_name(c: str) -> str:
    """Normalize column header for robust matching."""
    return re.sub(r"[\s_()/-]+", "", str(c).lower().strip())


async def import_colleges_excel(file_bytes: bytes, filename: str, db: AsyncSession) -> ExcelImportSummary:
    summary = ExcelImportSummary(success=True, message="Import completed")
    
    # Read excel file (all sheets) or CSV
    dfs: Dict[str, pd.DataFrame] = {}
    is_csv = filename.lower().endswith(".csv")
    
    try:
        if is_csv:
            df = pd.read_csv(io.BytesIO(file_bytes))
            dfs["CSV"] = df
        else:
            excel_file = io.BytesIO(file_bytes)
            xl = pd.ExcelFile(excel_file)
            for sheet_name in xl.sheet_names:
                dfs[sheet_name] = xl.parse(sheet_name)
    except Exception as e:
        logger.error(f"Error parsing uploaded file: {e}")
        return ExcelImportSummary(
            success=False,
            message=f"Failed to read file: {str(e)}",
            errors=[str(e)]
        )

    # In-memory cache of colleges by lowercase name to avoid repeated DB lookups
    colleges_cache: Dict[str, College] = {}
    
    # Pre-fetch existing colleges
    stmt = select(College)
    result = await db.execute(stmt)
    for col in result.scalars().all():
        colleges_cache[col.name.strip().lower()] = col

    async def get_or_create_college(name: str, **kwargs) -> Tuple[College, bool]:
        name_clean = name.strip()
        name_key = name_clean.lower()
        if name_key in colleges_cache:
            college = colleges_cache[name_key]
            # Update fields if provided
            updated = False
            for k, v in kwargs.items():
                if v is not None and not getattr(college, k, None):
                    setattr(college, k, v)
                    updated = True
            return college, False

        # Create new
        base_slug = slugify(name_clean) or "college"
        slug = base_slug
        # Ensure unique slug
        counter = 1
        existing_slugs = {c.slug for c in colleges_cache.values()}
        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1

        college = College(
            name=name_clean,
            slug=slug,
            **kwargs
        )
        db.add(college)
        await db.flush()
        colleges_cache[name_key] = college
        summary.colleges_created += 1
        return college, True

    # -------------------------------------------------------------
    # 1. Process Colleges Overview sheet if present
    # -------------------------------------------------------------
    for sheet_name, df in dfs.items():
        s_clean = sheet_name.lower().replace(" ", "")
        if "overview" in s_clean or "college" in s_clean and "course" not in s_clean and "fee" not in s_clean:
            cols_map = {clean_col_name(col): col for col in df.columns}
            name_col = next((cols_map[c] for c in ["collegename", "universityname", "name", "college"] if c in cols_map), None)
            if not name_col:
                continue

            for _, row in df.iterrows():
                raw_name = row.get(name_col)
                if pd.isna(raw_name) or not str(raw_name).strip():
                    continue
                name_str = str(raw_name).strip()

                id_code = row.get(cols_map.get("collegeid") or cols_map.get("id"))
                ctype = row.get(cols_map.get("type"))
                city = row.get(cols_map.get("city"))
                state = row.get(cols_map.get("state"))
                address = row.get(cols_map.get("fulladdress") or cols_map.get("address"))
                est_year = parse_numeric(row.get(cols_map.get("establishedyear") or cols_map.get("year")))
                cv_rating = parse_numeric(row.get(cols_map.get("cvrating") or cols_map.get("rating")))
                reviews = parse_numeric(row.get(cols_map.get("totalreviews") or cols_map.get("reviews")))
                courses_count = parse_numeric(row.get(cols_map.get("totalcourses") or cols_map.get("coursescount")))
                specs_count = parse_numeric(row.get(cols_map.get("totalspecializations") or cols_map.get("specializationscount")))
                min_fee = parse_numeric(row.get(cols_map.get("minfee") or cols_map.get("minfeeinr")))
                max_fee = parse_numeric(row.get(cols_map.get("maxfee") or cols_map.get("maxfeeinr")))
                approvals_sum = row.get(cols_map.get("approvalssummary") or cols_map.get("approvals"))
                whatsapp = row.get(cols_map.get("whatsapp"))
                helpline = row.get(cols_map.get("helpline") or cols_map.get("phone"))
                adm_link = row.get(cols_map.get("officialadmissionlink") or cols_map.get("admissionurl"))
                prospectus = row.get(cols_map.get("prospectuspdf") or cols_map.get("prospectus"))
                cv_url = row.get(cols_map.get("collegevidyaurl") or cols_map.get("url"))
                about = row.get(cols_map.get("aboutoverview") or cols_map.get("about"))

                college, created = await get_or_create_college(
                    name=name_str,
                    college_id_code=str(id_code).strip() if pd.notna(id_code) else None,
                    type=str(ctype).strip() if pd.notna(ctype) else "Online / Distance",
                    city=str(city).strip() if pd.notna(city) else None,
                    state=str(state).strip() if pd.notna(state) else None,
                    full_address=str(address).strip() if pd.notna(address) else None,
                    established_year=int(est_year) if est_year else None,
                    cv_rating=float(cv_rating) if cv_rating else 0.0,
                    total_reviews=int(reviews) if reviews else 0,
                    total_courses=int(courses_count) if courses_count else 0,
                    total_specializations=int(specs_count) if specs_count else 0,
                    min_fee=min_fee,
                    max_fee=max_fee,
                    approvals_summary=str(approvals_sum).strip() if pd.notna(approvals_sum) else None,
                    whatsapp=str(whatsapp).strip() if pd.notna(whatsapp) else None,
                    helpline=str(helpline).strip() if pd.notna(helpline) else None,
                    official_admission_link=str(adm_link).strip() if pd.notna(adm_link) else None,
                    prospectus_pdf=str(prospectus).strip() if pd.notna(prospectus) else None,
                    college_vidya_url=str(cv_url).strip() if pd.notna(cv_url) else None,
                    about_overview=str(about).strip() if pd.notna(about) else None,
                )
                if not created:
                    summary.colleges_updated += 1

    # -------------------------------------------------------------
    # 2. Process Courses & Fee Structure sheet
    # -------------------------------------------------------------
    for sheet_name, df in dfs.items():
        s_clean = sheet_name.lower().replace(" ", "")
        if "courses" in s_clean and "specialization" not in s_clean:
            cols_map = {clean_col_name(col): col for col in df.columns}
            name_col = next((cols_map[c] for c in ["collegename", "universityname", "college"] if c in cols_map), None)
            course_col = next((cols_map[c] for c in ["coursename", "course"] if c in cols_map), None)
            if not name_col or not course_col:
                continue

            for _, row in df.iterrows():
                raw_name = row.get(name_col)
                raw_course = row.get(course_col)
                if pd.isna(raw_name) or pd.isna(raw_course):
                    continue
                college_name = str(raw_name).strip()
                course_name = str(raw_course).strip()
                if not college_name or not course_name:
                    continue

                college, _ = await get_or_create_college(name=college_name)

                display_name = row.get(cols_map.get("displayname"))
                dur = row.get(cols_map.get("duration"))
                dur_m = parse_months(row.get(cols_map.get("durationmonths")) or dur)
                total_fee = parse_numeric(row.get(cols_map.get("basetotalfeeinr") or cols_map.get("totalfeeinr") or cols_map.get("basetotalfee")))
                sem_fee = parse_numeric(row.get(cols_map.get("basepersemesterfeeinr") or cols_map.get("persemesterfeeinr") or cols_map.get("basepersemesterfee")))
                ann_fee = parse_numeric(row.get(cols_map.get("baseannualfeeinr") or cols_map.get("annualfeeinr") or cols_map.get("baseannualfee")))
                one_time = parse_numeric(row.get(cols_map.get("onetimefeeinr") or cols_map.get("onetimeappfeeinr") or cols_map.get("onetimefee")))
                other_fees = row.get(cols_map.get("otherfeesbreakdown") or cols_map.get("otherfees"))
                emi = parse_numeric(row.get(cols_map.get("estmonthlyemiinr") or cols_map.get("estmonthlyemi")))
                specs_c = parse_numeric(row.get(cols_map.get("specializationscount")))
                course_url = row.get(cols_map.get("courseurl"))

                # Check if course exists for this college
                stmt = select(CollegeCourse).where(
                    CollegeCourse.college_id == college.id,
                    func.lower(CollegeCourse.course_name) == course_name.lower()
                )
                res = await db.execute(stmt)
                course = res.scalar_one_or_none()

                if course:
                    course.display_name = str(display_name).strip() if pd.notna(display_name) else course.display_name
                    course.duration = str(dur).strip() if pd.notna(dur) else course.duration
                    course.duration_months = dur_m or course.duration_months
                    course.base_total_fee = total_fee or course.base_total_fee
                    course.base_per_semester_fee = sem_fee or course.base_per_semester_fee
                    course.base_annual_fee = ann_fee or course.base_annual_fee
                    course.one_time_fee = one_time or course.one_time_fee
                    course.other_fees_breakdown = str(other_fees).strip() if pd.notna(other_fees) else course.other_fees_breakdown
                    course.est_monthly_emi = emi or course.est_monthly_emi
                    course.specializations_count = int(specs_c) if specs_c else course.specializations_count
                    course.course_url = str(course_url).strip() if pd.notna(course_url) else course.course_url
                    summary.courses_updated += 1
                else:
                    course = CollegeCourse(
                        college_id=college.id,
                        course_name=course_name,
                        display_name=str(display_name).strip() if pd.notna(display_name) else course_name,
                        course_slug=slugify(course_name),
                        duration=str(dur).strip() if pd.notna(dur) else None,
                        duration_months=dur_m,
                        base_total_fee=total_fee,
                        base_per_semester_fee=sem_fee,
                        base_annual_fee=ann_fee,
                        one_time_fee=one_time,
                        other_fees_breakdown=str(other_fees).strip() if pd.notna(other_fees) else None,
                        est_monthly_emi=emi,
                        specializations_count=int(specs_c) if specs_c else 0,
                        course_url=str(course_url).strip() if pd.notna(course_url) else None
                    )
                    db.add(course)
                    summary.courses_created += 1

    # -------------------------------------------------------------
    # 3. Process Specializations & Fees sheet
    # -------------------------------------------------------------
    for sheet_name, df in dfs.items():
        s_clean = sheet_name.lower().replace(" ", "")
        if "specialization" in s_clean:
            cols_map = {clean_col_name(col): col for col in df.columns}
            name_col = next((cols_map[c] for c in ["collegename", "universityname", "college"] if c in cols_map), None)
            course_col = next((cols_map[c] for c in ["coursename", "course"] if c in cols_map), None)
            spec_col = next((cols_map[c] for c in ["specializationname", "specialization"] if c in cols_map), None)
            if not name_col or not spec_col:
                continue

            for _, row in df.iterrows():
                raw_name = row.get(name_col)
                raw_spec = row.get(spec_col)
                if pd.isna(raw_name) or pd.isna(raw_spec):
                    continue
                college_name = str(raw_name).strip()
                spec_name = str(raw_spec).strip()
                course_name = str(row.get(course_col) or "").strip() or "General"
                if not college_name or not spec_name:
                    continue

                college, _ = await get_or_create_college(name=college_name)

                # Find associated course
                c_stmt = select(CollegeCourse).where(
                    CollegeCourse.college_id == college.id,
                    func.lower(CollegeCourse.course_name) == course_name.lower()
                )
                c_res = await db.execute(c_stmt)
                course = c_res.scalar_one_or_none()

                dur = row.get(cols_map.get("duration"))
                dur_m = parse_months(row.get(cols_map.get("durationmonths")) or dur)
                total_fee = parse_numeric(row.get(cols_map.get("totalfeeinr") or cols_map.get("totalfee")))
                sem_fee = parse_numeric(row.get(cols_map.get("persemesterfeeinr") or cols_map.get("persemesterfee")))
                ann_fee = parse_numeric(row.get(cols_map.get("annualfeeinr") or cols_map.get("annualfee")))
                one_time = parse_numeric(row.get(cols_map.get("onetimeappfeeinr") or cols_map.get("onetimefeeinr") or cols_map.get("onetimefee")))
                other_fees = row.get(cols_map.get("otherfeesbreakdown") or cols_map.get("otherfees"))
                emi = parse_numeric(row.get(cols_map.get("estmonthlyemiinr") or cols_map.get("estmonthlyemi")))
                spec_url = row.get(cols_map.get("specializationurl"))
                adm_url = row.get(cols_map.get("admissionurl"))

                stmt = select(CollegeSpecialization).where(
                    CollegeSpecialization.college_id == college.id,
                    func.lower(CollegeSpecialization.course_name) == course_name.lower(),
                    func.lower(CollegeSpecialization.specialization_name) == spec_name.lower()
                )
                res = await db.execute(stmt)
                spec = res.scalar_one_or_none()

                if spec:
                    spec.duration = str(dur).strip() if pd.notna(dur) else spec.duration
                    spec.duration_months = dur_m or spec.duration_months
                    spec.total_fee = total_fee or spec.total_fee
                    spec.per_semester_fee = sem_fee or spec.per_semester_fee
                    spec.annual_fee = ann_fee or spec.annual_fee
                    spec.one_time_fee = one_time or spec.one_time_fee
                    spec.other_fees_breakdown = str(other_fees).strip() if pd.notna(other_fees) else spec.other_fees_breakdown
                    spec.est_monthly_emi = emi or spec.est_monthly_emi
                    spec.specialization_url = str(spec_url).strip() if pd.notna(spec_url) else spec.specialization_url
                    spec.admission_url = str(adm_url).strip() if pd.notna(adm_url) else spec.admission_url
                    summary.specializations_updated += 1
                else:
                    spec = CollegeSpecialization(
                        college_id=college.id,
                        college_course_id=course.id if course else None,
                        course_name=course_name,
                        specialization_name=spec_name,
                        specialization_slug=slugify(spec_name),
                        duration=str(dur).strip() if pd.notna(dur) else None,
                        duration_months=dur_m,
                        total_fee=total_fee,
                        per_semester_fee=sem_fee,
                        annual_fee=ann_fee,
                        one_time_fee=one_time,
                        other_fees_breakdown=str(other_fees).strip() if pd.notna(other_fees) else None,
                        est_monthly_emi=emi,
                        specialization_url=str(spec_url).strip() if pd.notna(spec_url) else None,
                        admission_url=str(adm_url).strip() if pd.notna(adm_url) else None,
                    )
                    db.add(spec)
                    summary.specializations_created += 1

    # -------------------------------------------------------------
    # 4. Process "All Data page" (if uploaded as single flat sheet)
    # -------------------------------------------------------------
    for sheet_name, df in dfs.items():
        s_clean = sheet_name.lower().replace(" ", "")
        if "alldata" in s_clean or "sheet1" in s_clean or is_csv:
            cols_map = {clean_col_name(col): col for col in df.columns}
            name_col = next((cols_map[c] for c in ["collegename", "universityname", "college"] if c in cols_map), None)
            course_col = next((cols_map[c] for c in ["coursename", "course"] if c in cols_map), None)
            if not name_col or not course_col:
                continue

            for _, row in df.iterrows():
                raw_name = row.get(name_col)
                raw_course = row.get(course_col)
                if pd.isna(raw_name) or pd.isna(raw_course):
                    continue
                college_name = str(raw_name).strip()
                course_name = str(raw_course).strip()
                if not college_name or not course_name:
                    continue

                city = row.get(cols_map.get("city"))
                state = row.get(cols_map.get("state"))
                rating = parse_numeric(row.get(cols_map.get("cvrating") or cols_map.get("rating")))
                approvals_raw = row.get(cols_map.get("approvals"))
                emi_avail = row.get(cols_map.get("emiavailable"))
                lending_part = parse_list(row.get(cols_map.get("lendingpartners")))
                adm_url = row.get(cols_map.get("admissionurl"))
                cv_url = row.get(cols_map.get("collegevidyaurl"))

                college, _ = await get_or_create_college(
                    name=college_name,
                    city=str(city).strip() if pd.notna(city) else None,
                    state=str(state).strip() if pd.notna(state) else None,
                    cv_rating=float(rating) if rating else None,
                    official_admission_link=str(adm_url).strip() if pd.notna(adm_url) else None,
                    college_vidya_url=str(cv_url).strip() if pd.notna(cv_url) else None,
                )

                # Process Course
                dur = row.get(cols_map.get("duration"))
                dur_m = parse_months(dur)
                total_fee = parse_numeric(row.get(cols_map.get("totalfeeinr") or cols_map.get("totalfee")))
                sem_fee = parse_numeric(row.get(cols_map.get("persemesterfeeinr") or cols_map.get("persemesterfee")))
                ann_fee = parse_numeric(row.get(cols_map.get("annualfeeinr") or cols_map.get("annualfee")))
                one_time = parse_numeric(row.get(cols_map.get("onetimeappfeeinr") or cols_map.get("onetimefeeinr")))
                other_fees = row.get(cols_map.get("otherfees") or cols_map.get("otherfeesbreakdown"))
                emi = parse_numeric(row.get(cols_map.get("estmonthlyemiinr") or cols_map.get("estmonthlyemi")))

                stmt = select(CollegeCourse).where(
                    CollegeCourse.college_id == college.id,
                    func.lower(CollegeCourse.course_name) == course_name.lower()
                )
                res = await db.execute(stmt)
                course = res.scalar_one_or_none()

                if not course:
                    course = CollegeCourse(
                        college_id=college.id,
                        course_name=course_name,
                        display_name=course_name,
                        course_slug=slugify(course_name),
                        duration=str(dur).strip() if pd.notna(dur) else None,
                        duration_months=dur_m,
                        base_total_fee=total_fee,
                        base_per_semester_fee=sem_fee,
                        base_annual_fee=ann_fee,
                        one_time_fee=one_time,
                        other_fees_breakdown=str(other_fees).strip() if pd.notna(other_fees) else None,
                        est_monthly_emi=emi,
                    )
                    db.add(course)
                    await db.flush()
                    summary.courses_created += 1

                # Process Specialization if given
                spec_name_col = cols_map.get("specializationname")
                raw_spec = row.get(spec_name_col) if spec_name_col else None
                if pd.notna(raw_spec) and str(raw_spec).strip():
                    spec_name = str(raw_spec).strip()
                    spec_stmt = select(CollegeSpecialization).where(
                        CollegeSpecialization.college_id == college.id,
                        func.lower(CollegeSpecialization.course_name) == course_name.lower(),
                        func.lower(CollegeSpecialization.specialization_name) == spec_name.lower()
                    )
                    s_res = await db.execute(spec_stmt)
                    if not s_res.scalar_one_or_none():
                        new_spec = CollegeSpecialization(
                            college_id=college.id,
                            college_course_id=course.id,
                            course_name=course_name,
                            specialization_name=spec_name,
                            specialization_slug=slugify(spec_name),
                            duration=str(dur).strip() if pd.notna(dur) else None,
                            duration_months=dur_m,
                            total_fee=total_fee,
                            per_semester_fee=sem_fee,
                            annual_fee=ann_fee,
                            one_time_fee=one_time,
                            other_fees_breakdown=str(other_fees).strip() if pd.notna(other_fees) else None,
                            est_monthly_emi=emi,
                            admission_url=str(adm_url).strip() if pd.notna(adm_url) else None,
                        )
                        db.add(new_spec)
                        summary.specializations_created += 1

                # Process Approvals if given
                if pd.notna(approvals_raw) and str(approvals_raw).strip():
                    apps = parse_list(approvals_raw)
                    app_stmt = select(CollegeApproval).where(CollegeApproval.college_id == college.id)
                    app_res = await db.execute(app_stmt)
                    app_rec = app_res.scalar_one_or_none()
                    if not app_rec:
                        app_rec = CollegeApproval(
                            college_id=college.id,
                            approvals_list=apps,
                            total_approvals=len(apps),
                            ugc_deb="Yes" if any("ugc" in a.lower() for a in apps) else None,
                            aicte="Yes" if any("aicte" in a.lower() for a in apps) else None,
                            naac=next((a for a in apps if "naac" in a.lower()), None),
                        )
                        db.add(app_rec)
                        summary.approvals_synced += 1

                # Process Loan / EMI if given
                if pd.notna(emi_avail) or lending_part:
                    emi_stmt = select(CollegeEmiLoan).where(CollegeEmiLoan.college_id == college.id)
                    emi_res = await db.execute(emi_stmt)
                    emi_rec = emi_res.scalar_one_or_none()
                    if not emi_rec:
                        emi_rec = CollegeEmiLoan(
                            college_id=college.id,
                            no_cost_emi_available=str(emi_avail).strip() if pd.notna(emi_avail) else "Yes",
                            lending_partners=lending_part,
                        )
                        db.add(emi_rec)
                        summary.loans_synced += 1

    # -------------------------------------------------------------
    # 5. Process Approvals & Accreditations sheet
    # -------------------------------------------------------------
    for sheet_name, df in dfs.items():
        s_clean = sheet_name.lower().replace(" ", "")
        if "approval" in s_clean or "accreditation" in s_clean:
            cols_map = {clean_col_name(col): col for col in df.columns}
            name_col = next((cols_map[c] for c in ["collegename", "universityname", "college"] if c in cols_map), None)
            if not name_col:
                continue

            for _, row in df.iterrows():
                raw_name = row.get(name_col)
                if pd.isna(raw_name) or not str(raw_name).strip():
                    continue
                college, _ = await get_or_create_college(name=str(raw_name).strip())

                apps_list = parse_list(row.get(cols_map.get("approvalslist") or cols_map.get("approvals")))
                tot_apps = parse_numeric(row.get(cols_map.get("totalapprovals")))
                ugc = row.get(cols_map.get("ugcdeb") or cols_map.get("ugc"))
                aicte = row.get(cols_map.get("aicte"))
                naac = row.get(cols_map.get("naac"))
                nirf = row.get(cols_map.get("nirf"))
                wes = row.get(cols_map.get("wes"))
                qs = row.get(cols_map.get("qsranking") or cols_map.get("qs"))

                stmt = select(CollegeApproval).where(CollegeApproval.college_id == college.id)
                res = await db.execute(stmt)
                rec = res.scalar_one_or_none()
                if rec:
                    rec.approvals_list = apps_list or rec.approvals_list
                    rec.total_approvals = int(tot_apps) if tot_apps else (len(apps_list) or rec.total_approvals)
                    rec.ugc_deb = str(ugc).strip() if pd.notna(ugc) else rec.ugc_deb
                    rec.aicte = str(aicte).strip() if pd.notna(aicte) else rec.aicte
                    rec.naac = str(naac).strip() if pd.notna(naac) else rec.naac
                    rec.nirf = str(nirf).strip() if pd.notna(nirf) else rec.nirf
                    rec.wes = str(wes).strip() if pd.notna(wes) else rec.wes
                    rec.qs_ranking = str(qs).strip() if pd.notna(qs) else rec.qs_ranking
                else:
                    rec = CollegeApproval(
                        college_id=college.id,
                        approvals_list=apps_list,
                        total_approvals=int(tot_apps) if tot_apps else len(apps_list),
                        ugc_deb=str(ugc).strip() if pd.notna(ugc) else None,
                        aicte=str(aicte).strip() if pd.notna(aicte) else None,
                        naac=str(naac).strip() if pd.notna(naac) else None,
                        nirf=str(nirf).strip() if pd.notna(nirf) else None,
                        wes=str(wes).strip() if pd.notna(wes) else None,
                        qs_ranking=str(qs).strip() if pd.notna(qs) else None,
                    )
                    db.add(rec)
                summary.approvals_synced += 1

    # -------------------------------------------------------------
    # 6. Process EMI & Loan Plans sheet
    # -------------------------------------------------------------
    for sheet_name, df in dfs.items():
        s_clean = sheet_name.lower().replace(" ", "")
        if "loan" in s_clean or "emi" in s_clean and "course" not in s_clean:
            cols_map = {clean_col_name(col): col for col in df.columns}
            name_col = next((cols_map[c] for c in ["collegename", "universityname", "college"] if c in cols_map), None)
            if not name_col:
                continue

            for _, row in df.iterrows():
                raw_name = row.get(name_col)
                if pd.isna(raw_name) or not str(raw_name).strip():
                    continue
                college, _ = await get_or_create_college(name=str(raw_name).strip())

                no_cost = row.get(cols_map.get("nocostemiavailable") or cols_map.get("emiavailable"))
                sanction = row.get(cols_map.get("loansanctiontime"))
                partners = parse_list(row.get(cols_map.get("lendingpartners")))
                bank_visit = row.get(cols_map.get("bankvisitrequired"))
                policy = row.get(cols_map.get("emiloanpolicydetails") or cols_map.get("policydetails"))

                stmt = select(CollegeEmiLoan).where(CollegeEmiLoan.college_id == college.id)
                res = await db.execute(stmt)
                rec = res.scalar_one_or_none()
                if rec:
                    rec.no_cost_emi_available = str(no_cost).strip() if pd.notna(no_cost) else rec.no_cost_emi_available
                    rec.loan_sanction_time = str(sanction).strip() if pd.notna(sanction) else rec.loan_sanction_time
                    rec.lending_partners = partners or rec.lending_partners
                    rec.bank_visit_required = str(bank_visit).strip() if pd.notna(bank_visit) else rec.bank_visit_required
                    rec.policy_details = str(policy).strip() if pd.notna(policy) else rec.policy_details
                else:
                    rec = CollegeEmiLoan(
                        college_id=college.id,
                        no_cost_emi_available=str(no_cost).strip() if pd.notna(no_cost) else "Yes",
                        loan_sanction_time=str(sanction).strip() if pd.notna(sanction) else None,
                        lending_partners=partners,
                        bank_visit_required=str(bank_visit).strip() if pd.notna(bank_visit) else "No",
                        policy_details=str(policy).strip() if pd.notna(policy) else None
                    )
                    db.add(rec)
                summary.loans_synced += 1

    # -------------------------------------------------------------
    # 7. Process Examination & Admissions sheet
    # -------------------------------------------------------------
    for sheet_name, df in dfs.items():
        s_clean = sheet_name.lower().replace(" ", "")
        if "exam" in s_clean or "admission" in s_clean and "course" not in s_clean:
            cols_map = {clean_col_name(col): col for col in df.columns}
            name_col = next((cols_map[c] for c in ["collegename", "universityname", "college"] if c in cols_map), None)
            if not name_col:
                continue

            for _, row in df.iterrows():
                raw_name = row.get(name_col)
                if pd.isna(raw_name) or not str(raw_name).strip():
                    continue
                college, _ = await get_or_create_college(name=str(raw_name).strip())

                pattern = row.get(cols_map.get("examinationpatternmode") or cols_map.get("examinationpattern"))
                procedure = row.get(cols_map.get("admissionprocedure"))
                dates = row.get(cols_map.get("importantdatescutoffs") or cols_map.get("importantdates"))

                stmt = select(CollegeAdmissionExam).where(CollegeAdmissionExam.college_id == college.id)
                res = await db.execute(stmt)
                rec = res.scalar_one_or_none()
                if rec:
                    rec.examination_pattern_mode = str(pattern).strip() if pd.notna(pattern) else rec.examination_pattern_mode
                    rec.admission_procedure = str(procedure).strip() if pd.notna(procedure) else rec.admission_procedure
                    rec.important_dates_cutoffs = str(dates).strip() if pd.notna(dates) else rec.important_dates_cutoffs
                else:
                    rec = CollegeAdmissionExam(
                        college_id=college.id,
                        examination_pattern_mode=str(pattern).strip() if pd.notna(pattern) else None,
                        admission_procedure=str(procedure).strip() if pd.notna(procedure) else None,
                        important_dates_cutoffs=str(dates).strip() if pd.notna(dates) else None
                    )
                    db.add(rec)
                summary.admissions_synced += 1

    # -------------------------------------------------------------
    # 8. Process Placement Partners sheet
    # -------------------------------------------------------------
    for sheet_name, df in dfs.items():
        s_clean = sheet_name.lower().replace(" ", "")
        if "placement" in s_clean or "partner" in s_clean and "lending" not in s_clean:
            cols_map = {clean_col_name(col): col for col in df.columns}
            name_col = next((cols_map[c] for c in ["collegename", "universityname", "college"] if c in cols_map), None)
            if not name_col:
                continue

            for _, row in df.iterrows():
                raw_name = row.get(name_col)
                if pd.isna(raw_name) or not str(raw_name).strip():
                    continue
                college, _ = await get_or_create_college(name=str(raw_name).strip())

                companies = parse_list(row.get(cols_map.get("hiringcompaniespartners") or cols_map.get("hiringcompanies") or cols_map.get("placementpartner")))
                tot_p = parse_numeric(row.get(cols_map.get("totalpartnerslisted") or cols_map.get("totalpartners")))
                overview = row.get(cols_map.get("placementassistanceoverview") or cols_map.get("overview"))

                stmt = select(CollegePlacementPartner).where(CollegePlacementPartner.college_id == college.id)
                res = await db.execute(stmt)
                rec = res.scalar_one_or_none()
                if rec:
                    existing_companies = set(rec.hiring_companies or [])
                    for c in companies:
                        existing_companies.add(c)
                    rec.hiring_companies = list(existing_companies)
                    rec.total_partners_listed = int(tot_p) if tot_p else len(rec.hiring_companies)
                    rec.placement_assistance_overview = str(overview).strip() if pd.notna(overview) else rec.placement_assistance_overview
                else:
                    rec = CollegePlacementPartner(
                        college_id=college.id,
                        hiring_companies=companies,
                        total_partners_listed=int(tot_p) if tot_p else len(companies),
                        placement_assistance_overview=str(overview).strip() if pd.notna(overview) else None
                    )
                    db.add(rec)
                summary.placements_synced += 1

    # -------------------------------------------------------------
    # 9. Process Faculty & Professors sheet
    # -------------------------------------------------------------
    for sheet_name, df in dfs.items():
        s_clean = sheet_name.lower().replace(" ", "")
        if "faculty" in s_clean or "professor" in s_clean:
            cols_map = {clean_col_name(col): col for col in df.columns}
            name_col = next((cols_map[c] for c in ["collegename", "universityname", "college"] if c in cols_map), None)
            
            for _, row in df.iterrows():
                raw_name = row.get(name_col) if name_col else None
                # If college name column isn't present, check if there's only 1 college in context or default to first
                target_college = None
                if raw_name and pd.notna(raw_name) and str(raw_name).strip():
                    target_college, _ = await get_or_create_college(name=str(raw_name).strip())
                elif colleges_cache:
                    target_college = list(colleges_cache.values())[0]

                if not target_college:
                    continue

                prof_name = row.get(cols_map.get("name") or cols_map.get("facultyname"))
                title = row.get(cols_map.get("designationtitle") or cols_map.get("designation") or cols_map.get("title"))
                dept = row.get(cols_map.get("departmentsubtitle") or cols_map.get("department"))
                bio = row.get(cols_map.get("profilebio") or cols_map.get("bio"))
                linkedin = row.get(cols_map.get("linkedinsociallink") or cols_map.get("linkedin"))
                pic = row.get(cols_map.get("profilepictureurl") or cols_map.get("image") or cols_map.get("picture"))

                if pd.isna(prof_name) and pd.isna(title):
                    continue

                fac = CollegeFaculty(
                    college_id=target_college.id,
                    name=str(prof_name).strip() if pd.notna(prof_name) else None,
                    designation_title=str(title).strip() if pd.notna(title) else None,
                    department_subtitle=str(dept).strip() if pd.notna(dept) else None,
                    profile_bio=str(bio).strip() if pd.notna(bio) else None,
                    linkedin_url=str(linkedin).strip() if pd.notna(linkedin) else None,
                    profile_picture_url=str(pic).strip() if pd.notna(pic) else None,
                )
                db.add(fac)
                summary.faculty_synced += 1

    # Recalculate college totals
    await db.flush()
    for college in colleges_cache.values():
        c_count_stmt = select(func.count(CollegeCourse.id)).where(CollegeCourse.college_id == college.id)
        college.total_courses = (await db.execute(c_count_stmt)).scalar() or 0

        s_count_stmt = select(func.count(CollegeSpecialization.id)).where(CollegeSpecialization.college_id == college.id)
        college.total_specializations = (await db.execute(s_count_stmt)).scalar() or 0

        min_f_stmt = select(func.min(CollegeCourse.base_total_fee)).where(CollegeCourse.college_id == college.id)
        college.min_fee = (await db.execute(min_f_stmt)).scalar()

        max_f_stmt = select(func.max(CollegeCourse.base_total_fee)).where(CollegeCourse.college_id == college.id)
        college.max_fee = (await db.execute(max_f_stmt)).scalar()

    await db.commit()
    summary.message = f"Successfully processed {summary.colleges_created + summary.colleges_updated} colleges, {summary.courses_created + summary.courses_updated} courses, {summary.specializations_created + summary.specializations_updated} specializations."
    return summary
