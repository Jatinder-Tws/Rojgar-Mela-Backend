import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def update_db():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        print("Creating new mapping tables for assessment...")
        # Since we registered assessment in database.py's init_db, all we need to do is run create_all
        from database import Base, init_db
        await init_db()
        print("Migration done.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(update_db())
