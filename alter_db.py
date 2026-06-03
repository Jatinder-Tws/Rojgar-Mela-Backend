import asyncio
from sqlalchemy import text
from database import AsyncSessionLocal

async def alter_table():
    async with AsyncSessionLocal() as session:
        await session.execute(text("ALTER TABLE master_roles ADD COLUMN IF NOT EXISTS department_id VARCHAR(36) REFERENCES departments(id) ON DELETE CASCADE;"))
        await session.commit()
        print("Table altered successfully!")

if __name__ == "__main__":
    asyncio.run(alter_table())
