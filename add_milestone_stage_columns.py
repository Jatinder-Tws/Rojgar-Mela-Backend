import asyncio
from sqlalchemy import text
from database import engine

async def add_columns():
    async with engine.begin() as conn:
        try:
            # Add stage_title
            try:
                await conn.execute(text("ALTER TABLE milestones ADD COLUMN stage_title VARCHAR(100);"))
                print("Successfully added stage_title column to milestones table.")
            except Exception as e:
                if "already exists" in str(e):
                    print("Column stage_title already exists.")
                else:
                    raise e

            # Add stage_order
            try:
                await conn.execute(text("ALTER TABLE milestones ADD COLUMN stage_order INTEGER DEFAULT 1;"))
                print("Successfully added stage_order column to milestones table.")
            except Exception as e:
                if "already exists" in str(e):
                    print("Column stage_order already exists.")
                else:
                    raise e
                    
        except Exception as e:
            print(f"Error adding columns: {e}")

if __name__ == "__main__":
    asyncio.run(add_columns())
