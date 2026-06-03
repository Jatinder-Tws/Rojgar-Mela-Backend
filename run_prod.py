import asyncio
import os

from database import init_db, AsyncSessionLocal
from seed_master import seed_master_data
from seed_state import is_master_seed_completed, mark_master_seed_completed


async def run():
    print("Initializing Database tables...")
    await init_db()
    force_seed = os.getenv("FORCE_MASTER_SEED", "").lower() in ("1", "true", "yes")
    if not force_seed and await is_master_seed_completed():
        print("Master seed already applied — skipping.")
        return
    print("Database Initialized. Seeding master data...")
    async with AsyncSessionLocal() as session:
        await seed_master_data(session)
    await mark_master_seed_completed()
    print("Seeding Complete!")

if __name__ == "__main__":
    asyncio.run(run())
