import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.jobs_portal.models.industrial_visit import (
    ATTENDANCE_PENDING,
    ATTENDANCE_PRESENT,
    CERTIFICATE_FAILED,
    CERTIFICATE_PENDING,
    CERTIFICATE_SENT,
    DEFAULT_VISIT_SLUG,
    DEFAULT_VISIT_TITLE,
    DEFAULT_VISIT_VENUE,
    PLACEHOLDER_VISIT_TITLES,
    PLACEHOLDER_VISIT_VENUES,
    IndustrialVisit,
    IndustrialVisitStudent,
    generate_check_in_slug,
)
from app.modules.jobs_portal.schemas.industrial_visit import (
    IndustrialVisitAdminListResponse,
    IndustrialVisitAdminOut,
    IndustrialVisitAttendanceUpdate,
    IndustrialVisitCertificateVerifyOut,
    IndustrialVisitCheckIn,
    IndustrialVisitCheckInOut,
    IndustrialVisitCheckInPublicOut,
    IndustrialVisitCreate,
    IndustrialVisitPublicOut,
    IndustrialVisitRegister,
    IndustrialVisitRegisterOut,
    IndustrialVisitSendCertificatesOut,
    IndustrialVisitStats,
    IndustrialVisitStudentListResponse,
    IndustrialVisitStudentOut,
    IndustrialVisitUpdate,
)
from app.modules.jobs_portal.services.industrial_visit_certificate import (
    format_visit_date,
    generate_participation_certificate_pdf,
)

logger = logging.getLogger(__name__)

IST_TZ = timezone(timedelta(hours=5, minutes=30))
INDIAN_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return digits


def _validate_indian_mobile(phone: str) -> str:
    digits = _normalize_phone(phone)
    if not INDIAN_MOBILE_RE.match(digits):
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit Indian mobile number")
    return digits


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return (slug[:80] or "industrial-visit")


def _public_origin() -> str:
    return settings.FRONTEND_URL.rstrip("/")


def _registration_url(slug: str) -> str:
    origin = _public_origin()
    if slug == DEFAULT_VISIT_SLUG:
        return f"{origin}/industrial-visit"
    return f"{origin}/industrial-visit/{slug}"


def _check_in_url(check_in_slug: str) -> str:
    return f"{_public_origin()}/industrial-visit/in/{check_in_slug}"


def _certificate_verify_url(certificate_id: str) -> str:
    return f"{_public_origin()}/industrial-visit/certificate/{certificate_id}"


def _format_visit_date_display(visit_date: datetime) -> str:
    if visit_date.tzinfo is None:
        visit_date = visit_date.replace(tzinfo=timezone.utc)
    return format_visit_date(visit_date.astimezone(IST_TZ))


async def _visit_stats(db: AsyncSession, visit_id: str) -> IndustrialVisitStats:
    total = int(
        (
            await db.execute(
                select(func.count()).select_from(IndustrialVisitStudent).where(
                    IndustrialVisitStudent.visit_id == visit_id
                )
            )
        ).scalar()
        or 0
    )
    present = int(
        (
            await db.execute(
                select(func.count()).select_from(IndustrialVisitStudent).where(
                    IndustrialVisitStudent.visit_id == visit_id,
                    IndustrialVisitStudent.attendance_status == ATTENDANCE_PRESENT,
                )
            )
        ).scalar()
        or 0
    )
    certs = int(
        (
            await db.execute(
                select(func.count()).select_from(IndustrialVisitStudent).where(
                    IndustrialVisitStudent.visit_id == visit_id,
                    IndustrialVisitStudent.certificate_status == CERTIFICATE_SENT,
                )
            )
        ).scalar()
        or 0
    )
    return IndustrialVisitStats(
        registered=total,
        present=present,
        pending=max(total - present, 0),
        certificates_sent=certs,
    )


def _visit_to_admin(visit: IndustrialVisit, stats: Optional[IndustrialVisitStats] = None) -> IndustrialVisitAdminOut:
    return IndustrialVisitAdminOut(
        id=visit.id,
        title=visit.title,
        visit_date=visit.visit_date,
        venue=visit.venue,
        college_name=visit.college_name,
        slug=visit.slug,
        check_in_slug=visit.check_in_slug,
        is_active=visit.is_active,
        certificates_sent_at=visit.certificates_sent_at,
        registration_url=_registration_url(visit.slug),
        check_in_url=_check_in_url(visit.check_in_slug),
        stats=stats or IndustrialVisitStats(),
        created_at=visit.created_at,
        updated_at=visit.updated_at,
    )


def _student_to_out(item: IndustrialVisitStudent) -> IndustrialVisitStudentOut:
    return IndustrialVisitStudentOut.model_validate(item)


def _visit_to_public(visit: IndustrialVisit) -> IndustrialVisitPublicOut:
    return IndustrialVisitPublicOut.model_validate(visit)


async def _unique_slug(db: AsyncSession, title: str, exclude_id: Optional[str] = None) -> str:
    base = _slugify(title)
    slug = base
    for _ in range(8):
        query = select(IndustrialVisit.id).where(IndustrialVisit.slug == slug)
        if exclude_id:
            query = query.where(IndustrialVisit.id != exclude_id)
        exists = (await db.execute(query)).scalar_one_or_none()
        if not exists:
            return slug
        slug = f"{base}-{secrets.token_hex(3)}"
    return f"{base}-{uuid.uuid4().hex[:8]}"


async def _align_placeholder_visit(db: AsyncSession, visit: IndustrialVisit) -> IndustrialVisit:
    dirty = False
    title = (visit.title or "").strip()
    venue = (visit.venue or "").strip()
    if title in PLACEHOLDER_VISIT_TITLES:
        visit.title = DEFAULT_VISIT_TITLE
        dirty = True
    if not venue or venue in PLACEHOLDER_VISIT_VENUES:
        visit.venue = DEFAULT_VISIT_VENUE
        dirty = True
    if dirty:
        visit.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(visit)
    return visit


async def ensure_default_visit(db: AsyncSession) -> IndustrialVisit:
    result = await db.execute(
        select(IndustrialVisit)
        .where(IndustrialVisit.is_active.is_(True))
        .order_by(IndustrialVisit.created_at.asc())
        .limit(1)
    )
    visit = result.scalar_one_or_none()
    if visit:
        return await _align_placeholder_visit(db, visit)

    named = await db.execute(
        select(IndustrialVisit).where(IndustrialVisit.slug == DEFAULT_VISIT_SLUG)
    )
    existing = named.scalar_one_or_none()
    if existing:
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing)
        return await _align_placeholder_visit(db, existing)

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    visit = IndustrialVisit(
        title=DEFAULT_VISIT_TITLE,
        visit_date=today,
        venue=DEFAULT_VISIT_VENUE,
        college_name=None,
        slug=DEFAULT_VISIT_SLUG,
        check_in_slug=generate_check_in_slug(),
        is_active=True,
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)
    logger.info("Created default industrial visit %s", visit.id)
    return visit


async def get_public_visit(slug: str, db: AsyncSession) -> IndustrialVisitPublicOut:
    key = (slug or "").strip().lower()
    if key in {"", "default"}:
        visit = await ensure_default_visit(db)
        return _visit_to_public(visit)

    result = await db.execute(select(IndustrialVisit).where(IndustrialVisit.slug == key))
    visit = result.scalar_one_or_none()
    if not visit or not visit.is_active:
        raise HTTPException(status_code=404, detail="This industrial visit is not available")
    return _visit_to_public(visit)


async def get_check_in_visit(check_in_slug: str, db: AsyncSession) -> IndustrialVisitCheckInPublicOut:
    result = await db.execute(
        select(IndustrialVisit).where(IndustrialVisit.check_in_slug == (check_in_slug or "").strip())
    )
    visit = result.scalar_one_or_none()
    if not visit or not visit.is_active:
        raise HTTPException(status_code=404, detail="This check-in page is not available")
    return IndustrialVisitCheckInPublicOut.model_validate(visit)


async def register_student(
    slug: str,
    body: IndustrialVisitRegister,
    db: AsyncSession,
) -> IndustrialVisitRegisterOut:
    key = (slug or "").strip().lower()
    if key in {"", "default"}:
        visit = await ensure_default_visit(db)
    else:
        result = await db.execute(select(IndustrialVisit).where(IndustrialVisit.slug == key))
        visit = result.scalar_one_or_none()
        if not visit or not visit.is_active:
            raise HTTPException(status_code=404, detail="This industrial visit is not available")

    phone = _validate_indian_mobile(body.phone)
    email = str(body.email).strip().lower()

    existing = await db.execute(
        select(IndustrialVisitStudent).where(
            IndustrialVisitStudent.visit_id == visit.id,
            IndustrialVisitStudent.email == email,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="This email is already registered for this industrial visit",
        )

    student = IndustrialVisitStudent(
        visit_id=visit.id,
        full_name=body.full_name.strip(),
        college_name=body.college_name.strip(),
        department=body.department.strip(),
        year_of_study=body.year_of_study.strip(),
        email=email,
        phone=phone,
        location=body.location.strip(),
        area_of_interest=body.area_of_interest.strip(),
        graduation_year=body.graduation_year.strip(),
        attendance_status=ATTENDANCE_PENDING,
        certificate_status=CERTIFICATE_PENDING,
    )
    db.add(student)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This email is already registered for this industrial visit",
        )
    await db.refresh(student)

    try:
        from app.shared.services.email_service import send_industrial_visit_invite_email

        first_name = (student.full_name or "").strip().split()[0] or "there"
        await send_industrial_visit_invite_email(
            to_email=student.email,
            first_name=first_name,
            visit_title=visit.title,
            visit_date_display=_format_visit_date_display(visit.visit_date),
            venue=visit.venue or "",
        )
    except Exception as exc:
        logger.error("Failed to send industrial visit invitation email to %s: %s", student.email, exc)

    return IndustrialVisitRegisterOut(
        id=student.id,
        full_name=student.full_name,
        email=student.email,
        message="You are registered. An invitation email has been sent. Bring your phone on visit day to scan the office check-in QR.",
    )


async def check_in_student(
    check_in_slug: str,
    body: IndustrialVisitCheckIn,
    db: AsyncSession,
) -> IndustrialVisitCheckInOut:
    result = await db.execute(
        select(IndustrialVisit).where(IndustrialVisit.check_in_slug == (check_in_slug or "").strip())
    )
    visit = result.scalar_one_or_none()
    if not visit or not visit.is_active:
        raise HTTPException(status_code=404, detail="This check-in page is not available")

    email = str(body.email).strip().lower() if body.email else ""
    phone = _normalize_phone(body.phone or "")
    if not email and not phone:
        raise HTTPException(status_code=400, detail="Enter your registered email or 10-digit mobile number")
    if phone and not INDIAN_MOBILE_RE.match(phone) and not email:
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit Indian mobile number")

    query = select(IndustrialVisitStudent).where(IndustrialVisitStudent.visit_id == visit.id)
    if email and phone:
        query = query.where(
            or_(
                IndustrialVisitStudent.email == email,
                IndustrialVisitStudent.phone == phone,
            )
        )
    elif email:
        query = query.where(IndustrialVisitStudent.email == email)
    else:
        query = query.where(IndustrialVisitStudent.phone == phone)

    rows = list((await db.execute(query.order_by(IndustrialVisitStudent.created_at.desc()))).scalars().all())
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="You are not registered for this visit. Please register first using the industrial visit form.",
        )
    if email:
        student = next((row for row in rows if row.email == email), rows[0])
    elif len(rows) > 1:
        raise HTTPException(
            status_code=400,
            detail="Multiple registrations match this number. Please check in with your registered email.",
        )
    else:
        student = rows[0]

    if student.attendance_status == ATTENDANCE_PRESENT:
        return IndustrialVisitCheckInOut(
            already_present=True,
            full_name=student.full_name,
            message="Attendance is already marked Present. You can close this page.",
        )

    student.attendance_status = ATTENDANCE_PRESENT
    student.attended_at = datetime.utcnow()
    student.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(student)
    return IndustrialVisitCheckInOut(
        already_present=False,
        full_name=student.full_name,
        message="Attendance marked Present. Thank you for visiting.",
    )


async def verify_certificate(certificate_id: str, db: AsyncSession) -> IndustrialVisitCertificateVerifyOut:
    result = await db.execute(
        select(IndustrialVisitStudent).where(
            IndustrialVisitStudent.certificate_id == (certificate_id or "").strip()
        )
    )
    student = result.scalar_one_or_none()
    if not student or student.certificate_status != CERTIFICATE_SENT:
        return IndustrialVisitCertificateVerifyOut(valid=False)

    visit_result = await db.execute(select(IndustrialVisit).where(IndustrialVisit.id == student.visit_id))
    visit = visit_result.scalar_one_or_none()
    return IndustrialVisitCertificateVerifyOut(
        valid=True,
        certificate_id=student.certificate_id,
        full_name=student.full_name,
        college_name=student.college_name,
        department=student.department,
        visit_title=visit.title if visit else None,
        visit_date=visit.visit_date if visit else None,
        venue=visit.venue if visit else None,
        issued_at=student.certificate_sent_at,
    )


async def admin_list_visits(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
) -> IndustrialVisitAdminListResponse:
    await ensure_default_visit(db)
    filters = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                IndustrialVisit.title.ilike(term),
                IndustrialVisit.slug.ilike(term),
                IndustrialVisit.venue.ilike(term),
                IndustrialVisit.college_name.ilike(term),
            )
        )
    count_query = select(func.count()).select_from(IndustrialVisit)
    query = select(IndustrialVisit)
    if filters:
        count_query = count_query.where(*filters)
        query = query.where(*filters)
    total = int((await db.execute(count_query)).scalar() or 0)
    offset = (page - 1) * page_size
    rows = list(
        (
            await db.execute(
                query.order_by(IndustrialVisit.visit_date.desc(), IndustrialVisit.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        ).scalars().all()
    )
    items = []
    for visit in rows:
        stats = await _visit_stats(db, visit.id)
        items.append(_visit_to_admin(visit, stats))
    return IndustrialVisitAdminListResponse(items=items, total=total, page=page, page_size=page_size)


async def admin_get_visit(visit_id: str, db: AsyncSession) -> IndustrialVisitAdminOut:
    result = await db.execute(select(IndustrialVisit).where(IndustrialVisit.id == visit_id))
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=404, detail="Industrial visit not found")
    stats = await _visit_stats(db, visit.id)
    return _visit_to_admin(visit, stats)


async def admin_create_visit(body: IndustrialVisitCreate, db: AsyncSession) -> IndustrialVisitAdminOut:
    slug = await _unique_slug(db, body.title)
    visit = IndustrialVisit(
        title=body.title.strip(),
        visit_date=body.visit_date,
        venue=(body.venue or "").strip() or None,
        college_name=(body.college_name or "").strip() or None,
        slug=slug,
        check_in_slug=generate_check_in_slug(),
        is_active=body.is_active,
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)
    return _visit_to_admin(visit, IndustrialVisitStats())


async def admin_update_visit(
    visit_id: str,
    body: IndustrialVisitUpdate,
    db: AsyncSession,
) -> IndustrialVisitAdminOut:
    result = await db.execute(select(IndustrialVisit).where(IndustrialVisit.id == visit_id))
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=404, detail="Industrial visit not found")

    data = body.model_dump(exclude_unset=True)
    if "title" in data and data["title"]:
        visit.title = data["title"].strip()
    if "visit_date" in data and data["visit_date"] is not None:
        visit.visit_date = data["visit_date"]
    if "venue" in data:
        visit.venue = (data["venue"] or "").strip() or None
    if "college_name" in data:
        visit.college_name = (data["college_name"] or "").strip() or None
    if "is_active" in data and data["is_active"] is not None:
        visit.is_active = data["is_active"]
    visit.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(visit)
    stats = await _visit_stats(db, visit.id)
    return _visit_to_admin(visit, stats)


async def admin_delete_visit(visit_id: str, db: AsyncSession) -> None:
    result = await db.execute(select(IndustrialVisit).where(IndustrialVisit.id == visit_id))
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=404, detail="Industrial visit not found")
    await db.delete(visit)
    await db.commit()


def _student_filters(
    visit_id: str,
    search: Optional[str] = None,
    college: Optional[str] = None,
    department: Optional[str] = None,
    attendance: Optional[str] = None,
    certificate: Optional[str] = None,
) -> list:
    filters = [IndustrialVisitStudent.visit_id == visit_id]
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                IndustrialVisitStudent.full_name.ilike(term),
                IndustrialVisitStudent.email.ilike(term),
                IndustrialVisitStudent.phone.ilike(term),
                IndustrialVisitStudent.college_name.ilike(term),
                IndustrialVisitStudent.location.ilike(term),
                IndustrialVisitStudent.area_of_interest.ilike(term),
            )
        )
    if college and college.strip() and college.strip() != "all":
        filters.append(IndustrialVisitStudent.college_name == college.strip())
    if department and department.strip() and department.strip() != "all":
        filters.append(IndustrialVisitStudent.department == department.strip())
    if attendance and attendance.strip() and attendance.strip() != "all":
        filters.append(IndustrialVisitStudent.attendance_status == attendance.strip())
    if certificate and certificate.strip() and certificate.strip() != "all":
        filters.append(IndustrialVisitStudent.certificate_status == certificate.strip())
    return filters


async def admin_list_students(
    visit_id: str,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    college: Optional[str] = None,
    department: Optional[str] = None,
    attendance: Optional[str] = None,
    certificate: Optional[str] = None,
) -> IndustrialVisitStudentListResponse:
    result = await db.execute(select(IndustrialVisit).where(IndustrialVisit.id == visit_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Industrial visit not found")

    filters = _student_filters(visit_id, search, college, department, attendance, certificate)
    count_query = select(func.count()).select_from(IndustrialVisitStudent).where(*filters)
    total = int((await db.execute(count_query)).scalar() or 0)
    offset = (page - 1) * page_size
    rows = list(
        (
            await db.execute(
                select(IndustrialVisitStudent)
                .where(*filters)
                .order_by(IndustrialVisitStudent.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        ).scalars().all()
    )
    stats = await _visit_stats(db, visit_id)
    return IndustrialVisitStudentListResponse(
        items=[_student_to_out(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        stats=stats,
    )


async def admin_update_attendance(
    visit_id: str,
    student_id: str,
    body: IndustrialVisitAttendanceUpdate,
    db: AsyncSession,
) -> IndustrialVisitStudentOut:
    result = await db.execute(
        select(IndustrialVisitStudent).where(
            IndustrialVisitStudent.id == student_id,
            IndustrialVisitStudent.visit_id == visit_id,
        )
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if body.attendance_status == ATTENDANCE_PRESENT:
        student.attendance_status = ATTENDANCE_PRESENT
        student.attended_at = student.attended_at or datetime.utcnow()
    else:
        student.attendance_status = ATTENDANCE_PENDING
        student.attended_at = None
        if student.certificate_status != CERTIFICATE_SENT:
            student.certificate_status = CERTIFICATE_PENDING
            student.certificate_sent_at = None
    student.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(student)
    return _student_to_out(student)


async def admin_export_students_csv(visit_id: str, db: AsyncSession) -> StreamingResponse:
    result = await db.execute(select(IndustrialVisit).where(IndustrialVisit.id == visit_id))
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=404, detail="Industrial visit not found")

    rows = list(
        (
            await db.execute(
                select(IndustrialVisitStudent)
                .where(IndustrialVisitStudent.visit_id == visit_id)
                .order_by(IndustrialVisitStudent.created_at.desc())
            )
        ).scalars().all()
    )
    output = StringIO()
    import csv

    writer = csv.writer(output)
    writer.writerow(
        [
            "Full Name",
            "College",
            "Department",
            "Year of Study",
            "Email",
            "Phone",
            "Location",
            "Area of Interest",
            "Graduation Year",
            "Attendance",
            "Attended At",
            "Certificate Status",
            "Certificate Sent At",
            "Certificate ID",
            "Registered At",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.full_name,
                row.college_name,
                row.department,
                row.year_of_study,
                row.email,
                row.phone,
                row.location,
                row.area_of_interest,
                row.graduation_year,
                row.attendance_status,
                row.attended_at.isoformat() if row.attended_at else "",
                row.certificate_status,
                row.certificate_sent_at.isoformat() if row.certificate_sent_at else "",
                row.certificate_id or "",
                row.created_at.isoformat() if row.created_at else "",
            ]
        )
    filename = f"industrial-visit-{visit.slug}-students.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _new_certificate_id() -> str:
    return secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16].upper()


async def _send_one_certificate(db: AsyncSession, student: IndustrialVisitStudent, visit: IndustrialVisit) -> bool:
    from app.shared.services.email_service import send_industrial_visit_certificate_email

    if student.attendance_status != ATTENDANCE_PRESENT:
        return False
    if student.certificate_status == CERTIFICATE_SENT:
        return False

    if not student.certificate_id:
        student.certificate_id = _new_certificate_id()
        await db.flush()

    pdf_bytes = generate_participation_certificate_pdf(
        full_name=student.full_name,
        college_name=student.college_name,
        department=student.department,
        visit_title=visit.title,
        visit_date=visit.visit_date,
        venue=visit.venue,
        certificate_id=student.certificate_id,
        verify_url=_certificate_verify_url(student.certificate_id),
    )
    try:
        await send_industrial_visit_certificate_email(
            to_email=student.email,
            first_name=student.full_name.split()[0] if student.full_name else "there",
            full_name=student.full_name,
            visit_title=visit.title,
            visit_date_display=_format_visit_date_display(visit.visit_date),
            venue=visit.venue or "",
            certificate_id=student.certificate_id,
            verify_url=_certificate_verify_url(student.certificate_id),
            pdf_bytes=pdf_bytes,
        )
        student.certificate_status = CERTIFICATE_SENT
        student.certificate_sent_at = datetime.utcnow()
        student.updated_at = datetime.utcnow()
        return True
    except Exception as exc:
        logger.error("Certificate email failed for %s: %s", student.email, exc)
        student.certificate_status = CERTIFICATE_FAILED
        student.updated_at = datetime.utcnow()
        return False


async def admin_send_certificates(
    visit_id: str,
    db: AsyncSession,
) -> IndustrialVisitSendCertificatesOut:
    result = await db.execute(select(IndustrialVisit).where(IndustrialVisit.id == visit_id))
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=404, detail="Industrial visit not found")

    rows = list(
        (
            await db.execute(
                select(IndustrialVisitStudent).where(
                    IndustrialVisitStudent.visit_id == visit_id,
                    IndustrialVisitStudent.attendance_status == ATTENDANCE_PRESENT,
                    IndustrialVisitStudent.certificate_status.in_([CERTIFICATE_PENDING, CERTIFICATE_FAILED]),
                )
            )
        ).scalars().all()
    )
    sent = 0
    failed = 0
    for student in rows:
        ok = await _send_one_certificate(db, student, visit)
        if ok:
            sent += 1
        else:
            failed += 1
        await db.commit()

    if sent:
        visit.certificates_sent_at = datetime.utcnow()
        visit.updated_at = datetime.utcnow()
        await db.commit()

    return IndustrialVisitSendCertificatesOut(
        sent=sent,
        failed=failed,
        skipped=0,
        message=f"Sent {sent} certificate(s). {failed} failed." if rows else "No present students with pending certificates.",
    )


async def send_due_certificates(db: AsyncSession) -> dict:
    """Daily 5 PM IST job: email PDFs only to Present + pending students."""
    now_ist = datetime.now(IST_TZ)
    today_start_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = today_start_ist.astimezone(timezone.utc).replace(tzinfo=None)

    visits = list(
        (
            await db.execute(
                select(IndustrialVisit).where(IndustrialVisit.visit_date <= today_start_utc + timedelta(days=1))
            )
        ).scalars().all()
    )
    sent = 0
    failed = 0
    skipped_absent = 0
    for visit in visits:
        rows = list(
            (
                await db.execute(
                    select(IndustrialVisitStudent).where(
                        IndustrialVisitStudent.visit_id == visit.id,
                        IndustrialVisitStudent.attendance_status == ATTENDANCE_PRESENT,
                        IndustrialVisitStudent.certificate_status == CERTIFICATE_PENDING,
                    )
                )
            ).scalars().all()
        )
        skipped_absent += int(
            (
                await db.execute(
                    select(func.count()).select_from(IndustrialVisitStudent).where(
                        IndustrialVisitStudent.visit_id == visit.id,
                        IndustrialVisitStudent.attendance_status != ATTENDANCE_PRESENT,
                    )
                )
            ).scalar()
            or 0
        )
        visit_sent = 0
        for student in rows:
            ok = await _send_one_certificate(db, student, visit)
            if ok:
                sent += 1
                visit_sent += 1
            else:
                failed += 1
            await db.commit()
        if visit_sent:
            visit.certificates_sent_at = datetime.utcnow()
            visit.updated_at = datetime.utcnow()
            await db.commit()

    logger.info(
        "Industrial visit certificates: sent=%s failed=%s skipped_absent=%s",
        sent,
        failed,
        skipped_absent,
    )
    return {"sent": sent, "failed": failed, "skipped_absent": skipped_absent}
