import asyncio
from database import init_db, AsyncSessionLocal
from seed_master import seed_master_data

async def run():
    print("Initializing Database tables...")
    await init_db()
    print("Database Initialized. Seeding master data...")
    async with AsyncSessionLocal() as session:
        await seed_master_data(session)
    print("Seeding Complete!")

if __name__ == "__main__":
    asyncio.run(run())
