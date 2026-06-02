import asyncio
from database import engine
from sqlalchemy import text

async def nullify_company_address():
    print("Setting company_address to NULL for all users...")
    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("UPDATE users SET company_address = NULL;"))
            print(f"Successfully updated rows. company_address is now NULL for all users.")
        except Exception as e:
            print(f"Error executing update: {e}")

if __name__ == "__main__":
    asyncio.run(nullify_company_address())
