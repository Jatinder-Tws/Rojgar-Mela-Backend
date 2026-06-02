import asyncio
from sqlalchemy import text
from database import engine

async def update_schema():
    async with engine.begin() as conn:
        print("Updating users table schema...")
        
        # Add is_assessment_done column
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_assessment_done BOOLEAN DEFAULT FALSE NOT NULL"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_pic_url TEXT"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS experience VARCHAR(50)"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS company_size VARCHAR(50)"))
        
        # Resume builder: source column
        await conn.execute(text("ALTER TABLE resumes ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'upload' NOT NULL"))
        
        # Make fields nullable
        await conn.execute(text("ALTER TABLE users ALTER COLUMN first_name DROP NOT NULL"))
        await conn.execute(text("ALTER TABLE users ALTER COLUMN last_name DROP NOT NULL"))
        await conn.execute(text("ALTER TABLE users ALTER COLUMN email DROP NOT NULL"))
        await conn.execute(text("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL"))
        
        print("Schema update complete.")

if __name__ == "__main__":
    asyncio.run(update_schema())
