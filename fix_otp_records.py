import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def update_otp_records():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        print("Adding phone column to otp_records...")
        await conn.execute(text("ALTER TABLE otp_records ADD COLUMN IF NOT EXISTS phone VARCHAR(20);"))
        await conn.execute(text("ALTER TABLE otp_records ALTER COLUMN email DROP NOT NULL;"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_otp_records_phone ON otp_records(phone);"))
        print("Migration done.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(update_otp_records())
