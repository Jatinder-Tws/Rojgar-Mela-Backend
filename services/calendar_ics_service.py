"""Build RFC 5545 iCalendar (.ics) invites for training class sessions.

Emitting a VEVENT with METHOD:REQUEST and the recipient as an ATTENDEE makes
Gmail / Google Calendar surface an "add to calendar" card automatically, so
students and teachers see scheduled classes in their own Google Calendar
without any OAuth connection. METHOD:CANCEL removes a previously sent event.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence

from models.training_portal_class_session import TrainingPortalClassSession
from models.training_portal_batch import TrainingPortalBatch
from services import class_calendar_common as cc

# Timezone definition embedded so clients render IST correctly (India has no DST).
_VTIMEZONE = "\r\n".join([
    "BEGIN:VTIMEZONE",
    f"TZID:{cc.IANA_TZ}",
    "BEGIN:STANDARD",
    "DTSTART:19700101T000000",
    "TZOFFSETFROM:+0530",
    "TZOFFSETTO:+0530",
    "TZNAME:IST",
    "END:STANDARD",
    "END:VTIMEZONE",
])


def _escape(text: str) -> str:
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """Fold lines longer than 75 octets per RFC 5545."""
    if len(line) <= 75:
        return line
    chunks = [line[:75]]
    rest = line[75:]
    while rest:
        chunks.append(" " + rest[:74])
        rest = rest[74:]
    return "\r\n".join(chunks)


def build_class_ics(
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
    *,
    organizer_name: str,
    organizer_email: str,
    attendees: Sequence[tuple[str, str]],  # (name, email)
    method: str = "REQUEST",  # REQUEST | CANCEL
    sequence: int = 0,
    sender_domain: str = "rojgarmela.ai",
) -> Optional[str]:
    """Return an .ics document string, or None if the session times are unparseable."""
    dts = cc.session_datetimes(session, batch)
    if not dts:
        return None
    start_dt, end_dt = dts

    cancelled = method.upper() == "CANCEL"
    uid = cc.event_uid(session.id, sender_domain)
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fmt = "%Y%m%dT%H%M%S"

    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//RojgarMela//Training Portal//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        f"METHOD:{method.upper()}",
        _VTIMEZONE,
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"SEQUENCE:{sequence}",
        f"DTSTART;TZID={cc.IANA_TZ}:{start_dt.strftime(fmt)}",
        f"DTEND;TZID={cc.IANA_TZ}:{end_dt.strftime(fmt)}",
        f"SUMMARY:{_escape(cc.event_summary(session))}",
        f"DESCRIPTION:{_escape(cc.event_description(session, batch))}",
        f"LOCATION:{_escape(cc.event_location(session, batch))}",
        f"ORGANIZER;CN={_escape(organizer_name)}:mailto:{organizer_email}",
        f"STATUS:{'CANCELLED' if cancelled else 'CONFIRMED'}",
        "TRANSP:OPAQUE",
    ]

    rrule = cc.recurrence_rule(session, batch)
    if rrule:
        lines.append(f"RRULE:{rrule}")

    for name, email in attendees:
        if not email:
            continue
        part_stat = "NEEDS-ACTION"
        lines.append(
            f"ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;"
            f"PARTSTAT={part_stat};RSVP=TRUE;CN={_escape(name)}:mailto:{email}"
        )

    if not cancelled:
        # Two reminders mirroring the in-app 30 / 15 minute tiers.
        for minutes in (30, 15):
            lines.extend([
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"DESCRIPTION:{_escape(cc.event_summary(session))}",
                f"TRIGGER:-PT{minutes}M",
                "END:VALARM",
            ])

    lines.extend(["END:VEVENT", "END:VCALENDAR"])

    folded = "\r\n".join(_fold(line) for line in "\r\n".join(lines).split("\r\n"))
    return folded + "\r\n"
