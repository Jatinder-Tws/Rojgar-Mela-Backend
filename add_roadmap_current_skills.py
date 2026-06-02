import asyncio
from sqlalchemy import text
from database import engine

async def add_column():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE roadmaps ADD COLUMN current_skills TEXT[];"))
            print("Successfully added current_skills column to roadmaps table.")
        except Exception as e:
            if "already exists" in str(e):
                print("Column current_skills already exists.")
            else:
                print(f"Error adding column: {e}")

if __name__ == "__main__":
    asyncio.run(add_column())
