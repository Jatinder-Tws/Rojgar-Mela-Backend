"""
Migration: Create external_candidate_matches table.

Run once:
    python add_external_candidate_matches.py
"""
import asyncio
from database import engine, Base

# Import the new model so SQLAlchemy registers it
from models.external_candidate_match import ExternalCandidateMatch  # noqa
from models.external_candidate import ExternalCandidate  # noqa
from models.job import JobPosting  # noqa


async def main():
    async with engine.begin() as conn:
        # Create only the new table (won't touch existing tables)
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[ExternalCandidateMatch.__table__],
                checkfirst=True,
            )
        )
    print("✅ external_candidate_matches table created (or already exists).")


if __name__ == "__main__":
    asyncio.run(main())
