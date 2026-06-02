"""Background CSV bulk import for super admin."""
import io
import re
from typing import List

from sqlalchemy import or_, select

from config import settings
from database import AsyncSessionLocal
from models.user import CompanyType, JobType, User, UserRole
from services.auth_service import hash_password
from services.email_service import send_job_fair_welcome_email
from services.import_job_store import update_job, get_job
from services.super_admin_utils import normalize_phone, password_from_csv_row


import pandas as pd


def _normalize_header(header: str) -> str:
    """
    Normalize sheet headers so variants like:
    - "Father’s / Mother’s Name:"
    - "Father's / Mother's Name"
    map to the same key.
    """
    text = str(header or "").strip().lower()
    text = text.replace("’", "'")
    text = text.replace("/", " ")
    text = text.replace("-", " ")
    text = text.replace(":", "")
    text = re.sub(r"[^a-z0-9\s_']", " ", text)
    text = text.replace("'", "")
    text = re.sub(r"\s+", "_", text).strip("_")
    return text


def _pick_first_value(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _split_full_name(full_name: str) -> tuple[str, str]:
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])

async def run_bulk_import_job(job_id: str, content: bytes, role: UserRole) -> None:
    try:
        await _run_bulk_import_job_inner(job_id, content, role)
    except Exception as exc:
        update_job(job_id, status="failed", message=str(exc), progress=100)


async def _run_bulk_import_job_inner(job_id: str, content: bytes, role: UserRole) -> None:
    job = get_job(job_id)
    filename = job.get("filename", "").lower() if job else ""
    
    try:
        if filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(content), dtype=str)
        else:
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = content.decode("iso-8859-1")
            df = pd.read_csv(io.StringIO(text), dtype=str)
            
        # Normalize column names for flexible header mapping.
        df.columns = [_normalize_header(c) for c in df.columns]
        
        df = df.where(pd.notnull(df), None)
        rows: List[dict] = df.to_dict('records')
    except Exception as e:
        update_job(job_id, status="failed", message=f"Invalid file format: {str(e)}", progress=100)
        return

    if not rows:
        update_job(job_id, status="failed", message="File has no data", progress=100)
        return
    total = len(rows)
    update_job(
        job_id,
        status="processing",
        total=total,
        message=f"Importing {total} rows…",
        progress=0,
    )

    created = 0
    failed = 0
    errors: list[str] = []
    email_sent = 0
    email_failed = 0
    email_logs: list[str] = []

    async with AsyncSessionLocal() as db:
        for idx, row in enumerate(rows):
            row_num = idx + 2
            try:
                full_name = _pick_first_value(row, "full_name", "candidate_name", "name")
                first = _pick_first_value(row, "first_name", "firstname", "first")
                last = _pick_first_value(row, "last_name", "lastname", "last")
                if full_name and not first:
                    first, parsed_last = _split_full_name(full_name)
                    last = last or parsed_last

                email = _pick_first_value(row, "email", "email_address")
                phone = normalize_phone(
                    _pick_first_value(row, "phone", "mobile_number", "mobile", "contact_number")
                )
                if not all([first, last, email, phone]) or len(phone) != 10:
                    raise ValueError("first_name, last_name, email, phone (10 digits) required")

                existing = await db.execute(
                    select(User).where(or_(User.email == email, User.phone == phone))
                )
                if existing.scalar_one_or_none():
                    raise ValueError("duplicate email or phone")

                pwd, pwd_err = password_from_csv_row(row)
                if pwd_err:
                    raise ValueError(pwd_err)
                effective_password = pwd if pwd else phone

                # Fallback to phone number if password is empty in CSV
                plain_password = pwd if pwd else phone
                hashed_pwd = hash_password(plain_password)

                user = User(
                    first_name=first,
                    last_name=last,
                    email=email,
                    phone=phone,
                    hashed_password=hashed_pwd,
                    role=role,
                    is_verified=True,
                    onboarding_complete=True,
                    is_assessment_done=(role == UserRole.seeker),
                )
                if role == UserRole.seeker:
                    user.industry = _pick_first_value(row, "industry") or None
                    user.job_role = _pick_first_value(
                        row, "job_role", "preferred_job_sector", "preferred_job", "preferred_sector"
                    ) or None
                    jt = _pick_first_value(row, "job_type")
                    if jt:
                        user.job_type = JobType(jt)
                    user.salary_range = _pick_first_value(row, "salary_range") or None
                    user.experience = _pick_first_value(
                        row, "experience", "total_experience", "total_experience_years"
                    ) or None

                    # Extended seeker profile columns from super-admin import sheet.
                    user.father_or_mother_name = _pick_first_value(
                        row,
                        "father_or_mothers_name",
                        "father_mothers_name",
                        "fathers_mothers_name",
                        "father_or_mother_name",
                    ) or None
                    user.gender = _pick_first_value(row, "gender") or None
                    user.address = _pick_first_value(row, "address") or None
                    user.highest_qualification = _pick_first_value(
                        row, "highest_qualification"
                    ) or None
                    user.stream_specialization = _pick_first_value(
                        row, "stream_specialization", "stream", "specialization", "stream_specialization_"
                    ) or None
                    user.college_institute_name = _pick_first_value(
                        row, "college_institute_name", "college_name", "institute_name"
                    ) or None
                    user.preferred_job_sector = _pick_first_value(
                        row, "preferred_job_sector", "preferred_job", "preferred_sector"
                    ) or None
                else:
                    user.company_name = _pick_first_value(row, "company_name") or None
                    ct = _pick_first_value(row, "company_type")
                    if ct:
                        user.company_type = CompanyType(ct)
                    user.company_location = _pick_first_value(row, "company_location") or None
                    user.company_size = _pick_first_value(row, "company_size") or None

                db.add(user)
                await db.commit()
                created += 1

                # Send Job Fair welcome email for seekers
                if role == UserRole.seeker:
                    try:
                        seeker_name = f"{first} {last}".strip()
                        profile_link = f"{settings.FRONTEND_URL}/login"
                        await send_job_fair_welcome_email(
                            to_email=email,
                            seeker_name=seeker_name,
                            password=effective_password,
                            profile_link=profile_link,
                        )
                        email_sent += 1
                        if len(email_logs) < 500:
                            email_logs.append(f"Row {row_num} ({email}): sent")
                    except Exception as email_exc:
                        email_failed += 1
                        reason = str(email_exc)
                        if len(email_logs) < 500:
                            email_logs.append(f"Row {row_num} ({email}): failed - {reason}")
                        print(f"[EMAIL ERROR] Row {row_num}: Failed to send email to {email}: {email_exc}")
            except Exception as exc:
                await db.rollback()
                failed += 1
                if len(errors) < 50:
                    errors.append(f"Row {row_num}: {exc}")

            processed = idx + 1
            progress = int((processed / total) * 100) if total else 100
            update_job(
                job_id,
                processed=processed,
                progress=progress,
                created=created,
                failed=failed,
                errors=errors,
                email_sent=email_sent,
                email_failed=email_failed,
                email_logs=email_logs,
                message=f"Processed {processed} of {total} rows…",
            )

    update_job(
        job_id,
        status="completed",
        progress=100,
        created=created,
        failed=failed,
        errors=errors,
        email_sent=email_sent,
        email_failed=email_failed,
        email_logs=email_logs,
        message=f"Done — {created} created, {failed} failed, {email_sent} emails sent, {email_failed} emails failed",
    )
