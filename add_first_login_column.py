import asyncio
from sqlalchemy import text
from database import engine

async def add_column():
    async with engine.begin() as conn:
        print("Adding is_first_login column to users table...")
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN is_first_login BOOLEAN DEFAULT TRUE"))
            print("Successfully added is_first_login column.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("Column is_first_login already exists.")
            else:
                print(f"Error adding column: {e}")

if __name__ == "__main__":
    asyncio.run(add_column())
