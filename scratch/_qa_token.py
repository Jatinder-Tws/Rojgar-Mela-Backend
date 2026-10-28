import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.shared.services.auth_session_service import create_session_and_tokens
from app.shared.models.user import User

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.id == "82113d8d-f797-471e-a5a2-b1c5c03260cc"))
        user = res.scalar_one()
        access, refresh, session = await create_session_and_tokens(
            db, user, ip_address="127.0.0.1", user_agent="QA-Agent",
        )
        await db.commit()
        print("ACCESS=" + access)
        print("REFRESH=" + refresh)

asyncio.run(main())
