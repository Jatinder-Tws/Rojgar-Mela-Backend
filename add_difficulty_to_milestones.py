import asyncio
from sqlalchemy import text
from database import engine

async def add_column():
    async with engine.begin() as conn:
        try:
            # Add difficulty column
            try:
                await conn.execute(text("ALTER TABLE milestones ADD COLUMN difficulty VARCHAR(20) DEFAULT 'intermediate';"))
                print("Successfully added difficulty column to milestones table.")
            except Exception as e:
                if "already exists" in str(e):
                    print("Column difficulty already exists.")
                else:
                    raise e

        except Exception as e:
            print(f"Error adding column: {e}")

if __name__ == "__main__":
    asyncio.run(add_column())