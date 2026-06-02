import asyncio
from sqlalchemy import text
from database import engine

async def update_enum():
    async with engine.begin() as conn:
        print("Updating notificationtype enum...")
        # PostgreSQL doesn't support IF NOT EXISTS for ADD VALUE until 12.0
        # and it cannot be run inside a transaction block in some versions/situations.
        # But engine.begin() starts a transaction.
        # Actually, ALTER TYPE ... ADD VALUE cannot run in a transaction in many PG versions.
        
    # Using connection directly without transaction if needed, but let's try this first
    try:
        async with engine.connect() as conn:
            # Check existing values first
            result = await conn.execute(text("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'notificationtype'"))
            existing_values = [row[0] for row in result]
            print(f"Existing values: {existing_values}")
            
            from models.notification import NotificationType
            new_values = [v.value for v in NotificationType]
            for val in new_values:
                if val not in existing_values:
                    print(f"Adding {val} to notificationtype...")
                    # ALTER TYPE ADD VALUE cannot be executed in a transaction block
                    # SQLAlchemy engine.connect() might still use a transaction depending on isolation level
                    await conn.execute(text(f"ALTER TYPE notificationtype ADD VALUE '{val}'"))
                    print(f"Added {val}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(update_enum())
