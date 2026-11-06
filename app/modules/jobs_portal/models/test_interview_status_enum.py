"""Regression for interviews.status enum comparison.

Before migration b4c5d6e7f8a9 the column was varchar while SQLAlchemy bound
InterviewStatus as interviewstatus. PostgreSQL then rejected:

    operator does not exist: character varying = interviewstatus
"""

import asyncio
import os

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine, import_all_models
from app.modules.jobs_portal.models.interview import Interview, InterviewStatus


def test_interview_status_filter_matches_postgres_enum():
    if not os.environ.get("DATABASE_URL"):
        return

    import_all_models()

    async def _run():
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Interview.id).where(
                        Interview.status.in_(
                            [InterviewStatus.scheduled, InterviewStatus.completed]
                        )
                    )
                )
                return result.scalars().all()
        finally:
            await engine.dispose()

    rows = asyncio.run(_run())
    assert isinstance(rows, list)
