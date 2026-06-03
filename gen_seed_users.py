import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import json
from datetime import datetime
import os

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, '__str__') and not isinstance(obj, str):
            return str(obj)
        return super().default(obj)

async def main():
    engine = create_async_engine(os.environ.get('DATABASE_URL', "postgresql+asyncpg://jobmatch:secret@postgres:5432/jobmatch_db"))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(text("SELECT * FROM users"))
        rows = result.mappings().all()
        
    users_data = []
    for row in rows:
        d = dict(row)
        if 'id' in d and d['id']:
            d['id'] = str(d['id'])
        users_data.append(d)
        
    users_json = json.dumps(users_data, indent=4, cls=CustomEncoder)
    
    seeder_code = f"""import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User
from database import AsyncSessionLocal
import json
from datetime import datetime

USERS_DATA = {users_json}

async def seed_users_data():
    async with AsyncSessionLocal() as session:
        for u_data in USERS_DATA:
            if 'created_at' in u_data and u_data['created_at']:
                u_data['created_at'] = datetime.fromisoformat(u_data['created_at'])
            if 'updated_at' in u_data and u_data['updated_at']:
                u_data['updated_at'] = datetime.fromisoformat(u_data['updated_at'])
                
            existing = await session.execute(select(User).where(User.email == u_data.get('email')))
            if not existing.scalars().first():
                user = User(**u_data)
                session.add(user)
        await session.commit()
        print("Users seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_users_data())
"""
    with open("seed_users.py", "w", encoding="utf-8") as f:
        f.write(seeder_code)
    print("seed_users.py created")

if __name__ == "__main__":
    asyncio.run(main())
