"""
Add is_matched column to external_candidates table.

Run: python add_external_candidate_is_matched.py
"""
import asyncio
from sqlalchemy import text
from database import AsyncSessionLocal


async def migrate():
    async with AsyncSessionLocal() as db:
        # Check if column already exists
        result = await db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'external_candidates' AND column_name = 'is_matched'"
            )
        )
        if result.fetchone():
            print("[MIGRATION] Column 'is_matched' already exists — skipping")
            return

        # Add the column
        await db.execute(
            text(
                "ALTER TABLE external_candidates "
                "ADD COLUMN is_matched BOOLEAN NOT NULL DEFAULT false"
            )
        )
        await db.commit()
        print("[MIGRATION] Added 'is_matched' column to external_candidates")


if __name__ == "__main__":
    asyncio.run(migrate())
