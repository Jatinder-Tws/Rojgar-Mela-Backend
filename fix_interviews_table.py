import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def ensure_table():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        print("Creating interviews table...")
        # Create table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS interviews (
                id VARCHAR(36) PRIMARY KEY,
                seeker_id VARCHAR(36) NOT NULL,
                provider_id VARCHAR(36) NOT NULL,
                job_id VARCHAR(36) NOT NULL,
                title VARCHAR(200) NOT NULL,
                agenda TEXT,
                scheduled_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # Add foreign keys if they don't exist (simplified for this fix)
        # Add indexes
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_interviews_seeker ON interviews(seeker_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_interviews_provider ON interviews(provider_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_interviews_job ON interviews(job_id)"))
        print("Migration done.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(ensure_table())
