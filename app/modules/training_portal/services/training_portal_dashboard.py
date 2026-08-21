"""Training portal admin dashboard aggregates (server-side)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.training_portal.models.training_portal_batch import TrainingPortalBatch
from app.modules.training_portal.models.training_portal_behavior_report import TrainingPortalBehaviorReport
from app.modules.training_portal.models.training_portal_class_session import TrainingPortalClassSession
from app.modules.training_portal.models.training_portal_course import TrainingPortalCourse
from app.modules.training_portal.models.training_portal_enrollment import TrainingPortalEnrollment
from app.modules.training_portal.models.training_portal_internship import TrainingPortalInternship
from app.modules.training_portal.models.training_portal_leave_request import TrainingPortalLeaveRequest
from app.modules.training_portal.models.training_portal_teacher import TrainingPortalTeacher
from app.modules.training_portal.models.training_portal_transaction import TrainingPortalTransaction
from app.modules.training_portal.services.training_portal_class_live import session_occurs_on_date, today_ist


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    raw = str(value).strip()[:10]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _in_range(d: Optional[date], date_from: Optional[date], date_to: Optional[date]) -> bool:
    if d is None:
        return False
    if date_from and d < date_from:
        return False
    if date_to and d > date_to:
        return False
    return True


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())  # Monday


def _week_buckets(weeks: int = 4) -> list[dict[str, Any]]:
    today = today_ist()
    start = _week_start(today) - timedelta(weeks=weeks - 1)
    buckets: list[dict[str, Any]] = []
    for i in range(weeks):
        ws = start + timedelta(weeks=i)
        we = ws + timedelta(days=6)
        buckets.append(
            {
                "key": ws.isoformat(),
                "label": ws.strftime("%d %b"),
                "start": ws,
                "end": we,
                "collected": 0.0,
                "pending": 0.0,
            }
        )
    return buckets


def _find_week_bucket(buckets: list[dict[str, Any]], d: Optional[date]) -> Optional[dict[str, Any]]:
    if d is None:
        return None
    for b in buckets:
        if b["start"] <= d <= b["end"]:
            return b
    return None


async def build_dashboard_summary(
    db: AsyncSession,
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict[str, Any]:
    from_d = _parse_iso_date(date_from)
    to_d = _parse_iso_date(date_to)

    enrollments = list(
        (await db.execute(select(TrainingPortalEnrollment).order_by(TrainingPortalEnrollment.created_at.desc())))
        .scalars()
        .all()
    )
    batches = list((await db.execute(select(TrainingPortalBatch))).scalars().all())
    teachers = list((await db.execute(select(TrainingPortalTeacher))).scalars().all())
    courses_count = int(
        (await db.execute(select(func.count()).select_from(TrainingPortalCourse))).scalar() or 0
    )
    internships_count = int(
        (await db.execute(select(func.count()).select_from(TrainingPortalInternship))).scalar() or 0
    )
    leave_rows = list((await db.execute(select(TrainingPortalLeaveRequest))).scalars().all())
    behavior_rows = list((await db.execute(select(TrainingPortalBehaviorReport))).scalars().all())
    transactions = list(
        (
            await db.execute(
                select(TrainingPortalTransaction).order_by(TrainingPortalTransaction.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    sessions = list((await db.execute(select(TrainingPortalClassSession))).scalars().all())

    seats_rows = (
        await db.execute(
            select(TrainingPortalEnrollment.batch_id, func.count())
            .where(
                TrainingPortalEnrollment.batch_id.is_not(None),
                TrainingPortalEnrollment.status != "dropped",
            )
            .group_by(TrainingPortalEnrollment.batch_id)
        )
    ).all()
    seats_by_batch = {bid: int(cnt) for bid, cnt in seats_rows if bid}

    filtered = [
        e
        for e in enrollments
        if (not from_d and not to_d) or _in_range(_parse_iso_date(e.enrollment_date), from_d, to_d)
    ]

    unique_students = {
        (e.candidate_email or "").strip().lower()
        for e in filtered
        if (e.candidate_email or "").strip()
    }

    status_counts: dict[str, int] = {
        "active": 0,
        "completed": 0,
        "dropped": 0,
        "pending": 0,
        "payment_initiated": 0,
    }
    attendance_sum = 0
    completion_sum = 0
    at_risk = 0
    attendance_compliant = 0
    attendance_below = 0
    outstanding = 0.0
    overdue_count = 0
    cert_eligible = 0
    cert_issued = 0
    paid_status = 0
    pending_status = 0
    overdue_status = 0

    for e in filtered:
        status_counts[e.status] = status_counts.get(e.status, 0) + 1
        attendance_sum += int(e.attendance_percentage or 0)
        completion_sum += int(e.completion_percentage or 0)
        outstanding += float(e.balance_due or 0)
        if e.payment_status == "overdue":
            overdue_count += 1
            overdue_status += 1
        if e.payment_status in {"paid_online", "paid_offline", "free"}:
            paid_status += 1
        elif e.payment_status == "pending":
            pending_status += 1
        if e.attendance_percentage < 85 or e.payment_status == "overdue" or e.status == "dropped":
            at_risk += 1
        if e.attendance_percentage >= 85:
            attendance_compliant += 1
        else:
            attendance_below += 1
        if e.is_certificate_issued:
            cert_issued += 1
        elif e.attendance_percentage >= 85 and e.completion_percentage >= 100:
            cert_eligible += 1

    total_filtered = len(filtered)
    avg_attendance = round(attendance_sum / total_filtered) if total_filtered else 0
    avg_completion = round(completion_sum / total_filtered) if total_filtered else 0

    fee_collection = 0.0
    for tx in transactions:
        if (tx.transaction_type or "").lower() != "payment":
            continue
        if (tx.status or "").lower() not in {"completed", "success", "paid"}:
            continue
        tx_day = tx.created_at.date() if tx.created_at else None
        if (from_d or to_d) and not _in_range(tx_day, from_d, to_d):
            continue
        fee_collection += float(tx.amount or 0)

    if fee_collection <= 0:
        fee_collection = sum(float(e.paid_amount or 0) for e in filtered)

    total_seats = sum(int(b.max_seats or 0) for b in batches)
    filled_seats = sum(seats_by_batch.get(b.id, 0) for b in batches)
    today = today_ist()

    ongoing = 0
    upcoming = 0
    completed_batches = 0
    active_batches = 0
    for b in batches:
        status = (b.status or "").strip().lower()
        start = _parse_iso_date(b.start_date)
        end = _parse_iso_date(b.end_date)
        # Mirror frontend getBatchDisplayStatus: completed by status or end date.
        if status == "completed" or (end and end < today):
            completed_batches += 1
            continue
        active_batches += 1
        if start and end and start <= today <= end:
            ongoing += 1
        elif status == "ongoing":
            ongoing += 1
        else:
            upcoming += 1

    utilization = round((filled_seats / total_seats) * 100) if total_seats else 0

    active_teachers = sum(1 for t in teachers if (t.status or "").lower() == "active")

    today_classes = sum(1 for s in sessions if session_occurs_on_date(s, today))
    total_scheduled_classes = sum(
        1 for s in sessions if not getattr(s, "postponed", False)
    )

    weeks = _week_buckets(4)
    for tx in transactions:
        if (tx.transaction_type or "").lower() != "payment":
            continue
        if (tx.status or "").lower() not in {"completed", "success", "paid"}:
            continue
        tx_day = tx.created_at.date() if tx.created_at else None
        bucket = _find_week_bucket(weeks, tx_day)
        if bucket:
            bucket["collected"] += float(tx.amount or 0)

    if all(b["collected"] <= 0 for b in weeks):
        for e in enrollments:
            installments = e.installments or []
            if installments:
                for ins in installments:
                    if not isinstance(ins, dict):
                        continue
                    if (ins.get("status") or "") == "paid":
                        d = _parse_iso_date(ins.get("paid_date") or ins.get("due_date") or e.enrollment_date)
                        bucket = _find_week_bucket(weeks, d)
                        if bucket:
                            bucket["collected"] += float(ins.get("amount") or 0)
            elif float(e.paid_amount or 0) > 0:
                d = _parse_iso_date(e.enrollment_date)
                bucket = _find_week_bucket(weeks, d)
                if bucket:
                    bucket["collected"] += float(e.paid_amount or 0)

    for e in enrollments:
        installments = e.installments or []
        if installments:
            for ins in installments:
                if not isinstance(ins, dict):
                    continue
                if (ins.get("status") or "") in {"pending", "overdue"}:
                    d = _parse_iso_date(ins.get("due_date") or e.enrollment_date)
                    bucket = _find_week_bucket(weeks, d)
                    if bucket:
                        bucket["pending"] += float(ins.get("amount") or 0)
        elif float(e.balance_due or 0) > 0:
            d = _parse_iso_date(e.enrollment_date)
            bucket = _find_week_bucket(weeks, d)
            if bucket:
                bucket["pending"] += float(e.balance_due or 0)

    weekly_fee = [
        {
            "key": b["key"],
            "label": b["label"],
            "collected": round(b["collected"], 2),
            "pending": round(b["pending"], 2),
        }
        for b in weeks
    ]

    workload_map: dict[str, dict[str, Any]] = {}
    for b in batches:
        name = (b.instructor_name or "Unassigned").strip() or "Unassigned"
        key = (b.instructor_id or name).strip().lower()
        entry = workload_map.get(key) or {
            "teacher_key": key,
            "teacher_name": name,
            "batch_count": 0,
            "ongoing_count": 0,
            "seats_filled": 0,
        }
        entry["batch_count"] += 1
        status = (b.status or "").strip().lower()
        end = _parse_iso_date(b.end_date)
        start = _parse_iso_date(b.start_date)
        is_completed = status == "completed" or (end is not None and end < today)
        is_ongoing = (not is_completed) and (
            status == "ongoing" or (start is not None and end is not None and start <= today <= end)
        )
        if is_ongoing:
            entry["ongoing_count"] += 1
        entry["seats_filled"] += seats_by_batch.get(b.id, 0)
        if entry["teacher_name"] == "Unassigned" and name != "Unassigned":
            entry["teacher_name"] = name
        workload_map[key] = entry

    teacher_workload = sorted(
        workload_map.values(),
        key=lambda x: (-x["ongoing_count"], -x["batch_count"], x["teacher_name"].lower()),
    )[:8]

    course_counts: dict[str, int] = defaultdict(int)
    for e in filtered:
        if e.enrollment_type == "course" and e.item_id:
            course_counts[e.item_id] += 1
    course_enrollment = [
        {"course_id": cid, "count": cnt} for cid, cnt in sorted(course_counts.items(), key=lambda x: -x[1])
    ]

    by_batch_enrollments: dict[str, list[TrainingPortalEnrollment]] = defaultdict(list)
    for e in enrollments:
        if e.batch_id:
            by_batch_enrollments[e.batch_id].append(e)

    batch_performance = []
    for b in batches:
        students = by_batch_enrollments.get(b.id, [])
        n = len(students)
        avg_att = round(sum(int(s.attendance_percentage or 0) for s in students) / n) if n else 0
        avg_comp = round(sum(int(s.completion_percentage or 0) for s in students) / n) if n else 0
        filled = seats_by_batch.get(b.id, 0)
        util = round((filled / b.max_seats) * 100) if b.max_seats else 0
        batch_performance.append(
            {
                "batch_id": b.id,
                "batch_name": b.batch_name,
                "student_count": n,
                "avg_attendance": avg_att,
                "avg_completion": avg_comp,
                "utilization": util,
            }
        )
    batch_performance.sort(key=lambda x: (-x["student_count"], x["batch_name"].lower()))

    leave_pending = sum(1 for l in leave_rows if (l.status or "").lower() == "pending")
    leave_approved = sum(1 for l in leave_rows if (l.status or "").lower() == "approved")
    leave_rejected = sum(1 for l in leave_rows if (l.status or "").lower() == "rejected")

    behavior_avg = {"discipline": 0.0, "participation": 0.0, "performance": 0.0, "overall": 0.0}
    if behavior_rows:
        n = len(behavior_rows)
        discipline = round(sum(float(r.discipline_rating or 0) for r in behavior_rows) / n, 1)
        participation = round(sum(float(r.participation_rating or 0) for r in behavior_rows) / n, 1)
        performance = round(sum(float(r.performance_rating or 0) for r in behavior_rows) / n, 1)
        overall = round((discipline + participation + performance) / 3, 1)
        behavior_avg = {
            "discipline": discipline,
            "participation": participation,
            "performance": performance,
            "overall": overall,
        }

    payment_total = max(total_filtered, 1)

    return {
        "date_from": from_d.isoformat() if from_d else None,
        "date_to": to_d.isoformat() if to_d else None,
        "total_students": len(unique_students),
        "total_enrollments": total_filtered,
        "total_teachers": len(teachers),
        "active_teachers": active_teachers,
        "total_courses": courses_count,
        "total_internships": internships_count,
        "active_batches": active_batches,
        "upcoming_batches": upcoming,
        "completed_batches": completed_batches,
        "total_batches": len(batches),
        "total_seats": total_seats,
        "filled_seats": filled_seats,
        "batch_utilization_percent": utilization,
        "fee_collection": round(fee_collection, 2),
        "pending_fee": round(outstanding, 2),
        "overdue_count": overdue_count,
        "certificates_issued": cert_issued,
        "certificate_eligible": cert_eligible,
        "today_classes_count": today_classes,
        "total_scheduled_classes": total_scheduled_classes,
        "avg_attendance": avg_attendance,
        "avg_completion": avg_completion,
        "at_risk_count": at_risk,
        "attendance_compliant": attendance_compliant,
        "attendance_below_threshold": attendance_below,
        "enrollment_status": {
            "active": status_counts.get("active", 0),
            "completed": status_counts.get("completed", 0),
            "dropped": status_counts.get("dropped", 0),
            "pending": status_counts.get("pending", 0) + status_counts.get("payment_initiated", 0),
        },
        "payment_status": {
            "paid": paid_status,
            "pending": pending_status,
            "overdue": overdue_status,
            "paid_percent": round((paid_status / payment_total) * 100),
            "pending_percent": round((pending_status / payment_total) * 100),
            "overdue_percent": round((overdue_status / payment_total) * 100),
        },
        "leave_stats": {
            "pending": leave_pending,
            "approved": leave_approved,
            "rejected": leave_rejected,
            "total": len(leave_rows),
        },
        "behavior_avg": behavior_avg,
        "weekly_fee": weekly_fee,
        "teacher_workload": teacher_workload,
        "course_enrollment": course_enrollment,
        "batch_performance": batch_performance[:8],
    }
