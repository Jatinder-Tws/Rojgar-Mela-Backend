import io
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.super_admin.models.college_models import (
    College, CollegeCourse, CollegeSpecialization, CollegeApproval,
    CollegeEmiLoan, CollegeAdmissionExam, CollegePlacementPartner, CollegeFaculty
)
from app.modules.super_admin.schemas.college_schemas import ExcelImportSummary

logger = logging.getLogger(__name__)

# Scraper/placeholder rows that are not real courses
_SKIP_COURSE_NAMES = {
    "only for course page creation",
    "n/a",
    "na",
    "-",
    "--",
    "none",
    "null",
}


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

    # In-memory caches so same-batch duplicates never violate unique constraints
    colleges_cache: Dict[str, College] = {}
    # (college_id, course_name.lower()) -> CollegeCourse
    courses_cache: Dict[Tuple[str, str], CollegeCourse] = {}
    # (college_id, course_name.lower(), specialization_name.lower()) -> CollegeSpecialization
    specs_cache: Dict[Tuple[str, str, str], CollegeSpecialization] = {}
    # one-row-per-college side tables
    approvals_cache: Dict[str, CollegeApproval] = {}
    loans_cache: Dict[str, CollegeEmiLoan] = {}
    admissions_cache: Dict[str, CollegeAdmissionExam] = {}
    placements_cache: Dict[str, CollegePlacementPartner] = {}

    # Pre-fetch existing colleges and related rows
    stmt = select(College)
    result = await db.execute(stmt)
    for col in result.scalars().all():
        colleges_cache[col.name.strip().lower()] = col

    existing_courses = (await db.execute(select(CollegeCourse))).scalars().all()
    for course in existing_courses:
        courses_cache[(course.college_id, course.course_name.strip().lower())] = course

    existing_specs = (await db.execute(select(CollegeSpecialization))).scalars().all()
    for spec in existing_specs:
        specs_cache[(
            spec.college_id,
            (spec.course_name or "").strip().lower(),
            spec.specialization_name.strip().lower(),
        )] = spec

    for rec in (await db.execute(select(CollegeApproval))).scalars().all():
        approvals_cache[rec.college_id] = rec
    for rec in (await db.execute(select(CollegeEmiLoan))).scalars().all():
        loans_cache[rec.college_id] = rec
    for rec in (await db.execute(select(CollegeAdmissionExam))).scalars().all():
        admissions_cache[rec.college_id] = rec
    for rec in (await db.execute(select(CollegePlacementPartner))).scalars().all():
        placements_cache[rec.college_id] = rec

    def _is_valid_course_name(name: str) -> bool:
        cleaned = name.strip().lower()
        return bool(cleaned) and cleaned not in _SKIP_COURSE_NAMES

    def _apply_fields(obj: Any, fields: Dict[str, Any], *, overwrite: bool = True) -> None:
        for k, v in fields.items():
            if v is None:
                continue
            if overwrite or not getattr(obj, k, None):
                setattr(obj, k, v)

    async def get_or_create_college(name: str, **kwargs) -> Tuple[College, bool]:
        name_clean = name.strip()
        name_key = name_clean.lower()
        if name_key in colleges_cache:
            college = colleges_cache[name_key]
            # Update fields if provided
            for k, v in kwargs.items():
                if v is not None and not getattr(college, k, None):
                    setattr(college, k, v)
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

    def _apply_course_fields(course: CollegeCourse, fields: Dict[str, Any], *, overwrite: bool = False) -> None:
        _apply_fields(course, fields, overwrite=overwrite)

    async def get_or_create_course(
        college: College,
        course_name: str,
        *,
        fields: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[CollegeCourse], bool]:
        """Upsert a course using cache so duplicate rows in one import are safe."""
        name_clean = course_name.strip()
        if not _is_valid_course_name(name_clean):
            return None, False

        # Enforce DB column length early to avoid silent truncation collisions
        name_clean = name_clean[:150]
        key = (college.id, name_clean.lower())
        fields = fields or {}

        if key in courses_cache:
            course = courses_cache[key]
            _apply_course_fields(course, fields, overwrite=True)
            return course, False

        course = CollegeCourse(
            college_id=college.id,
            course_name=name_clean,
            display_name=fields.get("display_name") or name_clean,
            course_slug=fields.get("course_slug") or slugify(name_clean),
            duration=fields.get("duration"),
            duration_months=fields.get("duration_months"),
            base_total_fee=fields.get("base_total_fee"),
            base_per_semester_fee=fields.get("base_per_semester_fee"),
            base_annual_fee=fields.get("base_annual_fee"),
            one_time_fee=fields.get("one_time_fee"),
            other_fees_breakdown=fields.get("other_fees_breakdown"),
            est_monthly_emi=fields.get("est_monthly_emi"),
            specializations_count=fields.get("specializations_count") or 0,
            course_url=fields.get("course_url"),
        )
        db.add(course)
        await db.flush()
        courses_cache[key] = course
        return course, True

    async def get_or_create_specialization(
        college: College,
        course_name: str,
        spec_name: str,
        *,
        course: Optional[CollegeCourse] = None,
        fields: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[CollegeSpecialization], bool]:
        course_clean = (course_name or "General").strip()[:150]
        spec_clean = spec_name.strip()[:255]
        if not course_clean or not spec_clean:
            return None, False
        if not _is_valid_course_name(course_clean) and course_clean.lower() != "general":
            return None, False

        key = (college.id, course_clean.lower(), spec_clean.lower())
        fields = fields or {}

        if key in specs_cache:
            spec = specs_cache[key]
            _apply_fields(spec, fields, overwrite=True)
            if course and not spec.college_course_id:
                spec.college_course_id = course.id
            return spec, False

        spec = CollegeSpecialization(
            college_id=college.id,
            college_course_id=course.id if course else None,
            course_name=course_clean,
            specialization_name=spec_clean,
            specialization_slug=fields.get("specialization_slug") or slugify(spec_clean),
            duration=fields.get("duration"),
            duration_months=fields.get("duration_months"),
            total_fee=fields.get("total_fee"),
            per_semester_fee=fields.get("per_semester_fee"),
            annual_fee=fields.get("annual_fee"),
            one_time_fee=fields.get("one_time_fee"),
            other_fees_breakdown=fields.get("other_fees_breakdown"),
            est_monthly_emi=fields.get("est_monthly_emi"),
            specialization_url=fields.get("specialization_url"),
            admission_url=fields.get("admission_url"),
        )
        db.add(spec)
        await db.flush()
        specs_cache[key] = spec
        return spec, True

    async def upsert_approval(college: College, fields: Dict[str, Any]) -> CollegeApproval:
        rec = approvals_cache.get(college.id)
        if rec:
            # Merge approvals lists when both exist
            incoming = fields.get("approvals_list")
            if incoming:
                merged = list(dict.fromkeys([*(rec.approvals_list or []), *incoming]))
                fields = {**fields, "approvals_list": merged, "total_approvals": fields.get("total_approvals") or len(merged)}
            _apply_fields(rec, fields, overwrite=True)
            return rec

        rec = CollegeApproval(college_id=college.id, **{k: v for k, v in fields.items() if v is not None})
        if rec.total_approvals is None and rec.approvals_list:
            rec.total_approvals = len(rec.approvals_list)
        db.add(rec)
        await db.flush()
        approvals_cache[college.id] = rec
        return rec

    async def upsert_loan(college: College, fields: Dict[str, Any]) -> CollegeEmiLoan:
        rec = loans_cache.get(college.id)
        if rec:
            incoming_partners = fields.get("lending_partners")
            if incoming_partners:
                merged = list(dict.fromkeys([*(rec.lending_partners or []), *incoming_partners]))
                fields = {**fields, "lending_partners": merged}
            _apply_fields(rec, fields, overwrite=True)
            return rec

        rec = CollegeEmiLoan(college_id=college.id, **{k: v for k, v in fields.items() if v is not None})
        db.add(rec)
        await db.flush()
        loans_cache[college.id] = rec
        return rec

    async def upsert_admission(college: College, fields: Dict[str, Any]) -> CollegeAdmissionExam:
        rec = admissions_cache.get(college.id)
        if rec:
            _apply_fields(rec, fields, overwrite=True)
            return rec

        rec = CollegeAdmissionExam(college_id=college.id, **{k: v for k, v in fields.items() if v is not None})
        db.add(rec)
        await db.flush()
        admissions_cache[college.id] = rec
        return rec

    async def upsert_placement(college: College, fields: Dict[str, Any]) -> CollegePlacementPartner:
        rec = placements_cache.get(college.id)
        if rec:
            incoming = fields.get("hiring_companies")
            if incoming:
                merged = list(dict.fromkeys([*(rec.hiring_companies or []), *incoming]))
                fields = {
                    **fields,
                    "hiring_companies": merged,
                    "total_partners_listed": fields.get("total_partners_listed") or len(merged),
                }
            _apply_fields(rec, fields, overwrite=True)
            return rec

        rec = CollegePlacementPartner(college_id=college.id, **{k: v for k, v in fields.items() if v is not None})
        if rec.total_partners_listed is None and rec.hiring_companies:
            rec.total_partners_listed = len(rec.hiring_companies)
        db.add(rec)
        await db.flush()
        placements_cache[college.id] = rec
        return rec

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

                course, created = await get_or_create_course(
                    college,
                    course_name,
                    fields={
                        "display_name": str(display_name).strip() if pd.notna(display_name) else course_name,
                        "duration": str(dur).strip() if pd.notna(dur) else None,
                        "duration_months": dur_m,
                        "base_total_fee": total_fee,
                        "base_per_semester_fee": sem_fee,
                        "base_annual_fee": ann_fee,
                        "one_time_fee": one_time,
                        "other_fees_breakdown": str(other_fees).strip() if pd.notna(other_fees) else None,
                        "est_monthly_emi": emi,
                        "specializations_count": int(specs_c) if specs_c else None,
                        "course_url": str(course_url).strip() if pd.notna(course_url) else None,
                    },
                )
                if not course:
                    continue
                if created:
                    summary.courses_created += 1
                else:
                    summary.courses_updated += 1

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

                # Ensure parent course exists when a real course name is present
                course = None
                if _is_valid_course_name(course_name):
                    course, course_created = await get_or_create_course(college, course_name)
                    if course_created:
                        summary.courses_created += 1

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

                spec, created = await get_or_create_specialization(
                    college,
                    course_name,
                    spec_name,
                    course=course,
                    fields={
                        "duration": str(dur).strip() if pd.notna(dur) else None,
                        "duration_months": dur_m,
                        "total_fee": total_fee,
                        "per_semester_fee": sem_fee,
                        "annual_fee": ann_fee,
                        "one_time_fee": one_time,
                        "other_fees_breakdown": str(other_fees).strip() if pd.notna(other_fees) else None,
                        "est_monthly_emi": emi,
                        "specialization_url": str(spec_url).strip() if pd.notna(spec_url) else None,
                        "admission_url": str(adm_url).strip() if pd.notna(adm_url) else None,
                    },
                )
                if not spec:
                    continue
                if created:
                    summary.specializations_created += 1
                else:
                    summary.specializations_updated += 1

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

                course, course_created = await get_or_create_course(
                    college,
                    course_name,
                    fields={
                        "display_name": course_name,
                        "duration": str(dur).strip() if pd.notna(dur) else None,
                        "duration_months": dur_m,
                        "base_total_fee": total_fee,
                        "base_per_semester_fee": sem_fee,
                        "base_annual_fee": ann_fee,
                        "one_time_fee": one_time,
                        "other_fees_breakdown": str(other_fees).strip() if pd.notna(other_fees) else None,
                        "est_monthly_emi": emi,
                    },
                )
                if not course:
                    continue
                if course_created:
                    summary.courses_created += 1
                else:
                    summary.courses_updated += 1

                # Process Specialization if given
                spec_name_col = cols_map.get("specializationname")
                raw_spec = row.get(spec_name_col) if spec_name_col else None
                if pd.notna(raw_spec) and str(raw_spec).strip():
                    spec_name = str(raw_spec).strip()
                    spec, spec_created = await get_or_create_specialization(
                        college,
                        course_name,
                        spec_name,
                        course=course,
                        fields={
                            "duration": str(dur).strip() if pd.notna(dur) else None,
                            "duration_months": dur_m,
                            "total_fee": total_fee,
                            "per_semester_fee": sem_fee,
                            "annual_fee": ann_fee,
                            "one_time_fee": one_time,
                            "other_fees_breakdown": str(other_fees).strip() if pd.notna(other_fees) else None,
                            "est_monthly_emi": emi,
                            "admission_url": str(adm_url).strip() if pd.notna(adm_url) else None,
                        },
                    )
                    if spec:
                        if spec_created:
                            summary.specializations_created += 1
                        else:
                            summary.specializations_updated += 1

                # Process Approvals if given
                if pd.notna(approvals_raw) and str(approvals_raw).strip():
                    apps = parse_list(approvals_raw)
                    await upsert_approval(college, {
                        "approvals_list": apps,
                        "total_approvals": len(apps),
                        "ugc_deb": "Yes" if any("ugc" in a.lower() for a in apps) else None,
                        "aicte": "Yes" if any("aicte" in a.lower() for a in apps) else None,
                        "naac": next((a for a in apps if "naac" in a.lower()), None),
                    })
                    summary.approvals_synced += 1

                # Process Loan / EMI if given
                if pd.notna(emi_avail) or lending_part:
                    await upsert_loan(college, {
                        "no_cost_emi_available": str(emi_avail).strip() if pd.notna(emi_avail) else "Yes",
                        "lending_partners": lending_part or None,
                    })
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

                await upsert_approval(college, {
                    "approvals_list": apps_list or None,
                    "total_approvals": int(tot_apps) if tot_apps else (len(apps_list) or None),
                    "ugc_deb": str(ugc).strip() if pd.notna(ugc) else None,
                    "aicte": str(aicte).strip() if pd.notna(aicte) else None,
                    "naac": str(naac).strip() if pd.notna(naac) else None,
                    "nirf": str(nirf).strip() if pd.notna(nirf) else None,
                    "wes": str(wes).strip() if pd.notna(wes) else None,
                    "qs_ranking": str(qs).strip() if pd.notna(qs) else None,
                })
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

                await upsert_loan(college, {
                    "no_cost_emi_available": str(no_cost).strip() if pd.notna(no_cost) else "Yes",
                    "loan_sanction_time": str(sanction).strip() if pd.notna(sanction) else None,
                    "lending_partners": partners or None,
                    "bank_visit_required": str(bank_visit).strip() if pd.notna(bank_visit) else "No",
                    "policy_details": str(policy).strip() if pd.notna(policy) else None,
                })
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

                await upsert_admission(college, {
                    "examination_pattern_mode": str(pattern).strip() if pd.notna(pattern) else None,
                    "admission_procedure": str(procedure).strip() if pd.notna(procedure) else None,
                    "important_dates_cutoffs": str(dates).strip() if pd.notna(dates) else None,
                })
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

                await upsert_placement(college, {
                    "hiring_companies": companies or None,
                    "total_partners_listed": int(tot_p) if tot_p else (len(companies) or None),
                    "placement_assistance_overview": str(overview).strip() if pd.notna(overview) else None,
                })
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
    try:
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
    except IntegrityError as e:
        await db.rollback()
        err_msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        logger.error(f"College Vidya import IntegrityError: {err_msg}")
        return ExcelImportSummary(
            success=False,
            message="Import failed due to duplicate related college data (approvals/courses/EMI). Please retry — upserts should merge duplicates.",
            errors=[err_msg],
        )

    summary.message = (
        f"Successfully processed {summary.colleges_created + summary.colleges_updated} colleges, "
        f"{summary.courses_created + summary.courses_updated} courses, "
        f"{summary.specializations_created + summary.specializations_updated} specializations."
    )
    return summary
