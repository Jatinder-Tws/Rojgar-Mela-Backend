import asyncio
from sqlalchemy import text
from database import engine


async def add_market_based_salary_column():
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                ALTER TABLE roadmaps
                ADD COLUMN IF NOT EXISTS market_based_salary JSON;
                """
            )
        )
    print("market_based_salary column added (or already exists).")


if __name__ == "__main__":
    asyncio.run(add_market_based_salary_column())
