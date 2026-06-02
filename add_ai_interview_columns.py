import asyncio
import asyncpg

async def alter_job_postings():
    conn = await asyncpg.connect("postgresql://jobmatch:secret@localhost:5432/jobmatch_db")
    try:
        # Add ai_interview_enabled
        try:
            await conn.execute('ALTER TABLE job_postings ADD COLUMN ai_interview_enabled BOOLEAN NOT NULL DEFAULT FALSE;')
            print("Added ai_interview_enabled column to job_postings.")
        except asyncpg.exceptions.DuplicateColumnError:
            print("Column ai_interview_enabled already exists.")

        # Add selection_threshold
        try:
            await conn.execute('ALTER TABLE job_postings ADD COLUMN selection_threshold INTEGER NOT NULL DEFAULT 70;')
            print("Added selection_threshold column to job_postings.")
        except asyncpg.exceptions.DuplicateColumnError:
            print("Column selection_threshold already exists.")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(alter_job_postings())
