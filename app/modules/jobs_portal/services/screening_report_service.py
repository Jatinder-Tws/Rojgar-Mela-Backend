"""CSV / XLSX / PDF report generation for screening batches."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.modules.jobs_portal.models.screening import (
    ScreeningBatch,
    ScreeningBatchResume,
    ScreeningCandidateMatch,
    ScreeningReport,
    ScreeningResumeProfile,
)
from app.modules.jobs_portal.services.screening_storage import write_report_bytes

logger = logging.getLogger(__name__)


def _escape_cell(value: object) -> str:
    """Prevent spreadsheet formula injection."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


async def _load_rows(db, batch: ScreeningBatch) -> List[dict]:
    q = await db.execute(
        select(ScreeningCandidateMatch, ScreeningResumeProfile, ScreeningBatchResume)
        .join(ScreeningBatchResume, ScreeningBatchResume.id == ScreeningCandidateMatch.batch_resume_id)
        .outerjoin(ScreeningResumeProfile, ScreeningResumeProfile.batch_resume_id == ScreeningBatchResume.id)
        .where(ScreeningBatchResume.batch_id == batch.id)
        .order_by(ScreeningCandidateMatch.overall_score.desc())
    )
    jd_map = {str(j.id): j for j in (batch.jds or [])}
    rows = []
    for match, profile, resume in q.all():
        jd = jd_map.get(str(match.screening_jd_id))
        skills = []
        if profile and profile.skills:
            for s in profile.skills:
                if isinstance(s, dict):
                    skills.append(s.get("normalized_name") or s.get("name") or "")
                else:
                    skills.append(str(s))
        rows.append({
            "batch_name": batch.name,
            "job_title": jd.title if jd else "",
            "candidate_name": (profile.candidate_name if profile else None) or "",
            "candidate_email": (profile.candidate_email if profile else None) or "",
            "filename": resume.original_filename,
            "score": match.overall_score,
            "confidence": match.match_confidence or "",
            "data_quality": match.data_quality or "",
            "matched_skills": ", ".join(match.matched_requirements or []),
            "missing_skills": ", ".join(match.missing_requirements or []),
            "experience_years": profile.experience_years if profile else "",
            "skills": ", ".join([s for s in skills if s]),
            "decision": match.recruiter_decision or "none",
            "status": match.matching_status,
            "fit_reason": match.fit_reason or "",
        })
    return rows


def _build_csv(rows: List[dict]) -> bytes:
    buf = io.StringIO()
    fields = [
        "batch_name", "job_title", "candidate_name", "candidate_email", "filename",
        "score", "confidence", "data_quality", "matched_skills", "missing_skills",
        "experience_years", "skills", "decision", "status", "fit_reason",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _escape_cell(row.get(k)) for k in fields})
    return buf.getvalue().encode("utf-8-sig")


def _build_xlsx(rows: List[dict]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Screening Results"
    headers = [
        "Batch", "Job", "Candidate", "Email", "Filename", "Score", "Confidence",
        "Data Quality", "Matched Skills", "Missing Skills", "Experience Years",
        "Skills", "Decision", "Status", "Fit Reason",
    ]
    ws.append(headers)
    keys = [
        "batch_name", "job_title", "candidate_name", "candidate_email", "filename",
        "score", "confidence", "data_quality", "matched_skills", "missing_skills",
        "experience_years", "skills", "decision", "status", "fit_reason",
    ]
    for row in rows:
        ws.append([_escape_cell(row.get(k)) for k in keys])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def _build_pdf(batch: ScreeningBatch, rows: List[dict]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 20 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y, f"AI Resume Screening Report — {batch.name}")
    y -= 8 * mm
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Status: {batch.status} | Files: {batch.total_files} | Matched: {batch.matched_count} | Failed: {batch.failed_count}")
    y -= 8 * mm
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(20 * mm, y, "Scores are decision-support estimates, not hiring guarantees. Always review evidence.")
    y -= 10 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20 * mm, y, "Ranked candidates (top 80 shown)")
    y -= 6 * mm
    c.setFont("Helvetica", 8)
    for row in rows[:80]:
        if y < 20 * mm:
            c.showPage()
            y = height - 20 * mm
            c.setFont("Helvetica", 8)
        line = f"{row.get('score', 0):.1f} | {row.get('job_title', '')[:28]} | {row.get('candidate_name') or row.get('filename', '')[:28]} | {row.get('decision')}"
        c.drawString(20 * mm, y, line[:110])
        y -= 5 * mm
    c.showPage()
    c.save()
    return buf.getvalue()


async def generate_report(report_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ScreeningReport).where(ScreeningReport.id == report_id))
        report = res.scalar_one_or_none()
        if not report:
            return {"ok": False}
        report.status = "generating"
        await db.commit()

        bres = await db.execute(
            select(ScreeningBatch)
            .options(selectinload(ScreeningBatch.jds))
            .where(ScreeningBatch.id == report.batch_id)
        )
        batch = bres.scalar_one_or_none()
        if not batch:
            report.status = "failed"
            report.error_message = "Batch missing"
            await db.commit()
            return {"ok": False}

        try:
            rows = await _load_rows(db, batch)
            if report.report_type == "csv":
                data = _build_csv(rows)
                ext = "csv"
            elif report.report_type == "xlsx":
                data = _build_xlsx(rows)
                ext = "xlsx"
            else:
                data = _build_pdf(batch, rows)
                ext = "pdf"
            key, size = write_report_bytes(str(batch.provider_id), str(batch.id), str(report.id), ext, data)
            report.storage_key = key
            report.file_size = size
            report.status = "ready"
            report.completed_at = datetime.utcnow()
            report.error_message = None
            await db.commit()
            return {"ok": True, "size": size}
        except Exception as exc:
            logger.exception("report generation failed %s", report_id)
            report.status = "failed"
            report.error_message = "Report generation failed."
            await db.commit()
            return {"ok": False, "error": type(exc).__name__}
