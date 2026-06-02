import asyncio
from database import engine
from sqlalchemy import text

async def add_company_address_column():
    print("Adding company_address column to users table...")
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN company_address VARCHAR(500);"))
            print("Successfully added company_address column.")
        except Exception as e:
            print(f"Error (column might already exist): {e}")

if __name__ == "__main__":
    asyncio.run(add_company_address_column())
