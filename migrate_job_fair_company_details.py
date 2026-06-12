import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    statements = [
        "ALTER TABLE job_fair_companies ADD COLUMN IF NOT EXISTS company_name VARCHAR(200)",
        "ALTER TABLE job_fair_companies ADD COLUMN IF NOT EXISTS email VARCHAR(200)",
        "ALTER TABLE job_fair_companies ADD COLUMN IF NOT EXISTS phone VARCHAR(50)",
        "ALTER TABLE job_fair_companies ADD COLUMN IF NOT EXISTS website VARCHAR(200)",
        "ALTER TABLE job_fair_companies ADD COLUMN IF NOT EXISTS company_size VARCHAR(100)",
        "ALTER TABLE job_fair_companies ADD COLUMN IF NOT EXISTS company_address TEXT",
        "ALTER TABLE job_fair_companies ADD COLUMN IF NOT EXISTS contact_person_name VARCHAR(200)",
        "ALTER TABLE job_fair_companies ADD COLUMN IF NOT EXISTS contact_person_designation VARCHAR(200)",
        "ALTER TABLE job_fair_companies ADD COLUMN IF NOT EXISTS contact_person_phone VARCHAR(50)",
        "ALTER TABLE job_fair_companies ADD COLUMN IF NOT EXISTS openings JSON",
        "ALTER TABLE job_fair_companies ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500)",
        "ALTER TABLE job_fair_companies ADD COLUMN IF NOT EXISTS state VARCHAR(100)",
        "ALTER TABLE job_fair_companies ADD COLUMN IF NOT EXISTS city VARCHAR(100)",
    ]
    print("Running migration for job_fair_companies table columns...")
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
