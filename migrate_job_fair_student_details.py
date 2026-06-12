import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    statements = [
        "ALTER TABLE external_candidates ADD COLUMN IF NOT EXISTS year_of_passing VARCHAR(50)",
        "ALTER TABLE external_candidates ADD COLUMN IF NOT EXISTS skills TEXT",
    ]
    print("Running migration for external_candidates table columns...")
    async with engine.begin() as conn:
        for sql in statements:
            try:
                await conn.execute(text(sql))
                print(f"Executed: {sql}")
            except Exception as e:
                print(f"Failed to execute {sql}: {e}")
    print("Migration finished successfully.")

if __name__ == "__main__":
    asyncio.run(migrate())
