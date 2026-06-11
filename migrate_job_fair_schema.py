"""Add slug + banner_image_url columns to job_fairs (legacy schema alignment)."""
import asyncio
from sqlalchemy import text
from database import engine


async def migrate():
    statements = [
        "ALTER TABLE job_fairs ADD COLUMN IF NOT EXISTS slug VARCHAR(100);",
        "ALTER TABLE job_fairs ADD COLUMN IF NOT EXISTS banner_image_url TEXT;",
        "UPDATE job_fairs SET slug = id::text WHERE slug IS NULL OR slug = '';",
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_job_fairs_slug
        ON job_fairs (slug)
        WHERE slug IS NOT NULL;
        """,
    ]
    print("Migrating job_fairs schema...")
    async with engine.begin() as conn:
        for sql in statements:
            print(f"  {sql.strip()[:80]}...")
            await conn.execute(text(sql))
    print("Done.")


if __name__ == "__main__":
    asyncio.run(migrate())
