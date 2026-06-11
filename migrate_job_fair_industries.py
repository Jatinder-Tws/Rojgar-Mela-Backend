import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    statements = [
        "ALTER TABLE job_fairs ADD COLUMN IF NOT EXISTS industries JSON;"
    ]
    print("Starting database migration for job_fairs...")
    async with engine.begin() as conn:
        for sql in statements:
            print(f"Executing: {sql}")
            await conn.execute(text(sql))
    print("Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate())
