import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    statements = [
        "ALTER TABLE external_candidates DROP COLUMN IF EXISTS department;",
        "ALTER TABLE external_candidates DROP COLUMN IF EXISTS professional_journey;",
        "ALTER TABLE external_candidates ADD COLUMN IF NOT EXISTS current_designation VARCHAR(100);",
        "ALTER TABLE external_candidates ADD COLUMN IF NOT EXISTS profile_picture_url TEXT;"
    ]
    print("Starting database migration for external_candidates...")
    async with engine.begin() as conn:
        for sql in statements:
            print(f"Executing: {sql}")
            await conn.execute(text(sql))
    print("Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate())
