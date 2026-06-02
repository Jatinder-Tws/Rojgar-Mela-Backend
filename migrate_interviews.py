import asyncio
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Sync engine for migration
SYNC_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
engine = create_engine(SYNC_URL)

def run_migration():
    with engine.connect() as conn:
        print("Adding interviews table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS interviews (
                id UUID PRIMARY KEY,
                seeker_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                provider_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                job_id UUID NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
                title VARCHAR(200) NOT NULL,
                agenda TEXT,
                scheduled_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_interviews_seeker ON interviews(seeker_id);
            CREATE INDEX IF NOT EXISTS idx_interviews_provider ON interviews(provider_id);
            CREATE INDEX IF NOT EXISTS idx_interviews_job ON interviews(job_id);
        """))
        conn.commit()
        print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
