"""Orchestrates calendar sync when a training class session changes.

Two delivery paths, both best-effort and independent:
  1. ICS email invites to every teacher + student (works without OAuth).
  2. Direct Google Calendar API upsert/delete for attendees who connected their
     Google account (auto-sync, no accept needed).

These run as FastAPI background tasks, so each function opens its own DB session
and never raises into the request path.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parseaddr
from typing import Optional

from sqlalchemy import select, func, or_

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.shared.models.user import User
from app.modules.training_portal.models.training_portal_class_session import TrainingPortalClassSession
from app.modules.training_portal.models.training_portal_batch import TrainingPortalBatch
from app.modules.training_portal.models.training_portal_teacher import TrainingPortalTeacher
from app.modules.training_portal.models.training_portal_enrollment import TrainingPortalEnrollment
from app.modules.training_portal.models.google_calendar_token import GoogleCalendarToken
from app.modules.training_portal.models.training_portal_class_calendar_link import TrainingPortalClassCalendarLink
from app.modules.training_portal.services import calendar_ics_service, google_calendar_service as gcal
from app.modules.training_portal.services import class_calendar_common as cc
from app.shared.services.email_service import send_class_calendar_invite_email

logger = logging.getLogger(__name__)


@dataclass
class Attendee:
    name: str
    email: str
    user_id: Optional[str] = None
    role: str = "student"


@dataclass
class CancelSnapshot:
    """Everything needed to cancel a class after its DB row is gone."""
    class_title: str
    schedule_line: str
    venue: str
    ics_content: Optional[str]
    attendees: list[Attendee] = field(default_factory=list)
    # (user_id, calendar_id, google_event_id)
    links: list[tuple[str, str, str]] = field(default_factory=list)


def _organizer() -> tuple[str, str, str]:
    """Return (name, email, domain) for the calendar organizer."""
    name, email = parseaddr(settings.SMTP_FROM)
    email = email or "noreply@rojgarmela.ai"
    domain = email.split("@", 1)[1] if "@" in email else "rojgarmela.ai"
    return (name or "RojgarMela Training"), email, domain


def _schedule_line(session: TrainingPortalClassSession) -> str:
    if session.schedule_type == "recurring":
        days = ", ".join(session.days or []) or "weekly"
        return f"{days}, {session.start_time} - {session.end_time} (IST)"
    return f"{session.date}, {session.start_time} - {session.end_time} (IST)"


def _sequence_for(session: TrainingPortalClassSession) -> int:
    try:
        delta = (session.updated_at - session.created_at).total_seconds()
        return max(0, int(delta))
    except Exception:  # noqa: BLE001
        return 0


async def _resolve_attendees(
    db, session: TrainingPortalClassSession, batch: Optional[TrainingPortalBatch]
) -> list[Attendee]:
    attendees: list[Attendee] = []
    seen: set[str] = set()

    async def _user_id_for_email(email: str) -> Optional[str]:
        res = await db.execute(select(User.id).where(func.lower(User.email) == email.lower()))
        row = res.first()
        return row[0] if row else None

    # Teacher
    teacher_res = await db.execute(
        select(TrainingPortalTeacher).where(
            func.lower(TrainingPortalTeacher.name) == (session.instructor_name or "").strip().lower()
        )
    )
    teacher = teacher_res.scalar_one_or_none()
    if teacher and teacher.email:
        email = teacher.email.strip().lower()
        if email and email not in seen:
            seen.add(email)
            user_id = str(teacher.user_id) if teacher.user_id else await _user_id_for_email(email)
            attendees.append(Attendee(teacher.name or "Instructor", email, user_id, "teacher"))

    # Students (batch enrollments)
    if batch:
        enr_res = await db.execute(
            select(TrainingPortalEnrollment).where(
                TrainingPortalEnrollment.batch_id == batch.id,
                TrainingPortalEnrollment.status != "dropped",
            )
        )
        for enr in enr_res.scalars().all():
            email = (enr.candidate_email or "").strip().lower()
            if not email or email in seen:
                continue
            seen.add(email)
            user_id = str(enr.candidate_user_id) if enr.candidate_user_id else await _user_id_for_email(email)
            attendees.append(Attendee(enr.candidate_name or "Student", email, user_id, "student"))

    return attendees


async def _load_session_and_batch(db, session_id: str):
    res = await db.execute(
        select(TrainingPortalClassSession).where(TrainingPortalClassSession.id == session_id)
    )
    session = res.scalar_one_or_none()
    if not session:
        return None, None
    batch = None
    if session.batch_id:
        b_res = await db.execute(
            select(TrainingPortalBatch).where(TrainingPortalBatch.id == session.batch_id)
        )
        batch = b_res.scalar_one_or_none()
    return session, batch


async def _send_ics_invites(
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
    attendees: list[Attendee],
    method: str,
) -> None:
    if not settings.GOOGLE_CALENDAR_ICS_ENABLED or not attendees:
        return
    org_name, org_email, domain = _organizer()
    ics = calendar_ics_service.build_class_ics(
        session,
        batch,
        organizer_name=org_name,
        organizer_email=org_email,
        attendees=[(a.name, a.email) for a in attendees],
        method=method,
        sequence=_sequence_for(session) + (1 if method == "CANCEL" else 0),
        sender_domain=domain,
    )
    if not ics:
        return
    schedule_line = _schedule_line(session)
    venue = cc.event_location(session, batch)
    for a in attendees:
        try:
            await send_class_calendar_invite_email(
                a.email,
                a.name,
                session.title,
                schedule_line,
                venue,
                ics,
                method=method,
                role_label="class" if a.role == "student" else "class you teach",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("ICS invite email to %s failed: %s", a.email, exc)


async def _push_google_events(
    db,
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
    attendees: list[Attendee],
) -> None:
    if not gcal.is_configured():
        return
    body = gcal.build_event_body(session, batch)
    if not body:
        return

    for a in attendees:
        if not a.user_id:
            continue
        tok_res = await db.execute(
            select(GoogleCalendarToken).where(GoogleCalendarToken.user_id == a.user_id)
        )
        token = tok_res.scalar_one_or_none()
        if not token or not token.refresh_token:
            continue
        access = await gcal.ensure_access_token(db, token)
        if not access:
            continue

        link_res = await db.execute(
            select(TrainingPortalClassCalendarLink).where(
                TrainingPortalClassCalendarLink.session_id == session.id,
                TrainingPortalClassCalendarLink.user_id == a.user_id,
            )
        )
        link = link_res.scalar_one_or_none()
        try:
            event_id = await gcal.upsert_event(
                access,
                body,
                calendar_id=(link.calendar_id if link else "primary"),
                event_id=(link.google_event_id if link else None),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Google event upsert failed for user %s: %s", a.user_id, exc)
            continue

        if link:
            link.google_event_id = event_id
            link.updated_at = datetime.utcnow()
        else:
            db.add(
                TrainingPortalClassCalendarLink(
                    id=str(uuid.uuid4()),
                    session_id=session.id,
                    user_id=a.user_id,
                    calendar_id="primary",
                    google_event_id=event_id,
                )
            )
    await db.flush()


# ── Public entry points (run as background tasks) ──────────────────────────────

async def _remove_google_events_for_session(db, session_id: str) -> None:
    """Delete any Google events previously created for a session (postpone/cancel)."""
    if not gcal.is_configured():
        return
    links_res = await db.execute(
        select(TrainingPortalClassCalendarLink).where(
            TrainingPortalClassCalendarLink.session_id == session_id
        )
    )
    links = list(links_res.scalars().all())
    for link in links:
        tok_res = await db.execute(
            select(GoogleCalendarToken).where(GoogleCalendarToken.user_id == link.user_id)
        )
        token = tok_res.scalar_one_or_none()
        if token:
            access = await gcal.ensure_access_token(db, token)
            if access:
                try:
                    await gcal.delete_event(access, link.google_event_id, calendar_id=link.calendar_id or "primary")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Google event delete failed: %s", exc)
        await db.delete(link)
    await db.flush()


async def run_class_sync(session_id: str) -> None:
    """Create/update calendar events + send invites for a scheduled class.

    If the session is postponed or the teacher is unavailable, the class is
    removed from calendars instead (cancellation invite).
    """
    try:
        async with AsyncSessionLocal() as db:
            session, batch = await _load_session_and_batch(db, session_id)
            if not session:
                return
            attendees = await _resolve_attendees(db, session, batch)

            if session.postponed or session.teacher_unavailable:
                await _remove_google_events_for_session(db, session_id)
                await _send_ics_invites(session, batch, attendees, "CANCEL")
            else:
                await _push_google_events(db, session, batch, attendees)
                await _send_ics_invites(session, batch, attendees, "REQUEST")
            await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Class calendar sync failed for %s: %s", session_id, exc)


async def build_cancel_snapshot(db, session_id: str) -> Optional[CancelSnapshot]:
    """Capture cancel data BEFORE the session row (and its links) are deleted."""
    session, batch = await _load_session_and_batch(db, session_id)
    if not session:
        return None
    attendees = await _resolve_attendees(db, session, batch)

    org_name, org_email, domain = _organizer()
    ics = calendar_ics_service.build_class_ics(
        session,
        batch,
        organizer_name=org_name,
        organizer_email=org_email,
        attendees=[(a.name, a.email) for a in attendees],
        method="CANCEL",
        sequence=_sequence_for(session) + 1,
        sender_domain=domain,
    )

    links_res = await db.execute(
        select(TrainingPortalClassCalendarLink).where(
            TrainingPortalClassCalendarLink.session_id == session_id
        )
    )
    links = [
        (str(l.user_id), l.calendar_id or "primary", l.google_event_id)
        for l in links_res.scalars().all()
    ]

    return CancelSnapshot(
        class_title=session.title,
        schedule_line=_schedule_line(session),
        venue=cc.event_location(session, batch),
        ics_content=ics,
        attendees=attendees,
        links=links,
    )


async def run_class_cancel(snapshot: CancelSnapshot) -> None:
    """Delete Google events + send cancellation invites for a removed class."""
    try:
        # Remove events from connected users' Google calendars.
        if gcal.is_configured() and snapshot.links:
            async with AsyncSessionLocal() as db:
                for user_id, calendar_id, event_id in snapshot.links:
                    tok_res = await db.execute(
                        select(GoogleCalendarToken).where(GoogleCalendarToken.user_id == user_id)
                    )
                    token = tok_res.scalar_one_or_none()
                    if not token:
                        continue
                    access = await gcal.ensure_access_token(db, token)
                    if not access:
                        continue
                    try:
                        await gcal.delete_event(access, event_id, calendar_id=calendar_id)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Google event delete failed: %s", exc)
                await db.commit()

        # Cancellation emails.
        if settings.GOOGLE_CALENDAR_ICS_ENABLED and snapshot.ics_content:
            for a in snapshot.attendees:
                try:
                    await send_class_calendar_invite_email(
                        a.email,
                        a.name,
                        snapshot.class_title,
                        snapshot.schedule_line,
                        snapshot.venue,
                        snapshot.ics_content,
                        method="CANCEL",
                        role_label="class" if a.role == "student" else "class you teach",
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Cancellation email to %s failed: %s", a.email, exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Class calendar cancel failed: %s", exc)
