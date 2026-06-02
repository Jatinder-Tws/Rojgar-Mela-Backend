import asyncio
from sqlalchemy import select, update
from database import AsyncSessionLocal
from models.user import User

async def migrate():
    async with AsyncSessionLocal() as session:
        # 1. Set is_first_login = True for all users initially
        # (This is the default, but let's be explicit for existing records)
        print("Initializing is_first_login to True for all users...")
        await session.execute(
            update(User).values(is_first_login=True)
        )
        
        # 2. Set is_first_login = False for users who have totp_enabled = True
        print("Setting is_first_login to False for users with TOTP already enabled...")
        await session.execute(
            update(User).where(User.totp_enabled == True).values(is_first_login=False)
        )
        
        await session.commit()
        print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
