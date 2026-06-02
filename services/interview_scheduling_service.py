from __future__ import annotations

from datetime import datetime, timedelta, time as dt_time, timezone
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from models.provider_availability_window import ProviderAvailabilityWindow
from models.provider_interview_settings import ProviderInterviewSettings
from schemas.interview_scheduling import (
    SlotPreviewListOut,
    SlotPreviewOut,
)
from services.interview_scheduling_dbservice import (
    get_or_create_settings,
    load_busy_intervals,
)


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _period_from_local(local_dt: datetime) -> str:
    return "AM" if local_dt.hour < 12 else "PM"


def slots_overlap(
    a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime
) -> bool:
    return a_start < b_end and a_end > b_start


def _generate_day_slots(
    settings: ProviderInterviewSettings,
    day_local: datetime.date,
    windows: List[ProviderAvailabilityWindow],
    tz: ZoneInfo,
) -> List[Tuple[datetime, datetime, str]]:
    """Return list of (utc_naive_start, utc_naive_end, period) for one local day."""
    slots: List[Tuple[datetime, datetime, str]] = []
    duration = timedelta(minutes=settings.slot_duration_minutes)
    step = timedelta(
        minutes=settings.slot_duration_minutes + settings.buffer_minutes
    )

    for window in windows:
        local_start = datetime.combine(day_local, window.start_time, tzinfo=tz)
        local_end = datetime.combine(day_local, window.end_time, tzinfo=tz)
        cursor = local_start
        while cursor + duration <= local_end:
            utc_start = cursor.astimezone(timezone.utc).replace(tzinfo=None)
            utc_end = (cursor + duration).astimezone(timezone.utc).replace(tzinfo=None)
            slots.append((utc_start, utc_end, _period_from_local(cursor)))
            cursor += step

    return slots


def _is_slot_free(
    slot_start: datetime,
    slot_end: datetime,
    busy: List[Tuple[datetime, datetime]],
) -> bool:
    return not any(
        slots_overlap(slot_start, slot_end, b_start, b_end)
        for b_start, b_end in busy
    )


async def find_next_available_slot(
    db: AsyncSession,
    provider_id: str,
    after: Optional[datetime] = None,
    ignore_min_notice: bool = False,
) -> Optional[Tuple[datetime, str]]:
    try:
        settings = await get_or_create_settings(db, provider_id)
        if not settings.availability_windows:
            return None

        try:
            tz = ZoneInfo(settings.timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        now_utc = _utc_now_naive()
        # By default respect provider's min notice; caller can override for immediate scheduling
        if ignore_min_notice:
            min_start = now_utc
        else:
            min_start = now_utc + timedelta(hours=settings.min_notice_hours)
        if after is not None:
            min_start = max(min_start, _to_utc_naive(after))

        search_end = now_utc + timedelta(days=settings.lookahead_days)
        busy = await load_busy_intervals(
            db, provider_id, min_start, search_end, settings.slot_duration_minutes
        )

        windows_by_day: dict[int, List[ProviderAvailabilityWindow]] = {}
        for w in settings.availability_windows:
            windows_by_day.setdefault(w.day_of_week, []).append(w)

        local_now = datetime.now(tz)
        for day_offset in range(settings.lookahead_days + 1):
            day_local = (local_now + timedelta(days=day_offset)).date()
            weekday = day_local.weekday()  # 0=Monday
            day_windows = windows_by_day.get(weekday)
            if not day_windows:
                continue

            for utc_start, utc_end, period in _generate_day_slots(
                settings, day_local, day_windows, tz
            ):
                if utc_start < min_start:
                    continue
                if _is_slot_free(utc_start, utc_end, busy):
                    return utc_start, period

        return None
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error") from e


async def find_available_slots(
    db: AsyncSession,
    provider_id: str,
    limit: int = 10,
    after: Optional[datetime] = None,
) -> SlotPreviewListOut:
    try:
        settings = await get_or_create_settings(db, provider_id)
        if not settings.availability_windows:
            return SlotPreviewListOut(
                slots=[],
                slot_duration_minutes=settings.slot_duration_minutes,
                timezone=settings.timezone,
            )

        try:
            tz = ZoneInfo(settings.timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        now_utc = _utc_now_naive()
        min_start = now_utc + timedelta(hours=settings.min_notice_hours)
        if after is not None:
            min_start = max(min_start, _to_utc_naive(after))

        search_end = now_utc + timedelta(days=settings.lookahead_days)
        busy = await load_busy_intervals(
            db, provider_id, min_start, search_end, settings.slot_duration_minutes
        )

        windows_by_day: dict[int, List[ProviderAvailabilityWindow]] = {}
        for w in settings.availability_windows:
            windows_by_day.setdefault(w.day_of_week, []).append(w)

        found: List[SlotPreviewOut] = []
        local_now = datetime.now(tz)

        for day_offset in range(settings.lookahead_days + 1):
            if len(found) >= limit:
                break
            day_local = (local_now + timedelta(days=day_offset)).date()
            weekday = day_local.weekday()
            day_windows = windows_by_day.get(weekday)
            if not day_windows:
                continue

            for utc_start, utc_end, period in _generate_day_slots(
                settings, day_local, day_windows, tz
            ):
                if utc_start < min_start:
                    continue
                if _is_slot_free(utc_start, utc_end, busy):
                    found.append(
                        SlotPreviewOut(scheduled_at=utc_start, scheduled_period=period)
                    )
                    busy.append((utc_start, utc_end))
                    if len(found) >= limit:
                        break

        return SlotPreviewListOut(
            slots=found,
            slot_duration_minutes=settings.slot_duration_minutes,
            timezone=settings.timezone,
        )
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error") from e


async def preview_available_slots(
    db: AsyncSession,
    provider_id: str,
    limit: int = 10,
    application_id: Optional[str] = None,
) -> SlotPreviewListOut:
    try:
        return await find_available_slots(
            db, provider_id, limit=limit, after=None
        )
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error") from e


async def assert_slot_available(
    db: AsyncSession,
    provider_id: str,
    scheduled_at: datetime,
    duration_minutes: Optional[int] = None,
) -> None:
    try:
        settings = await get_or_create_settings(db, provider_id)
        duration = duration_minutes or settings.slot_duration_minutes
        start = _to_utc_naive(scheduled_at)
        end = start + timedelta(minutes=duration)

        if start < _utc_now_naive():
            raise HTTPException(status_code=400, detail="Cannot schedule an interview in the past")

        busy = await load_busy_intervals(
            db,
            provider_id,
            start - timedelta(days=1),
            end + timedelta(days=1),
            duration,
        )
        if not _is_slot_free(start, end, busy):
            next_slot = await find_next_available_slot(db, provider_id, after=start)
            detail = "This time slot is already booked."
            if next_slot:
                detail += f" Next available: {next_slot[0].isoformat()} UTC ({next_slot[1]})."
            raise HTTPException(status_code=409, detail=detail)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error") from e
