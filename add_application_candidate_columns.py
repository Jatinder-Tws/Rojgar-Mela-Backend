import asyncio
from sqlalchemy import text
from database import engine

async def add_candidate_columns():
    async with engine.begin() as conn:
        print("Checking and adding guest candidate columns to applications table...")
        
        # Add candidate_name
        try:
            await conn.execute(text("ALTER TABLE applications ADD COLUMN candidate_name VARCHAR(200)"))
            print("Added candidate_name column")
        except Exception as e:
            print(f"Error adding candidate_name: {e}")

        # Add candidate_email
        try:
            await conn.execute(text("ALTER TABLE applications ADD COLUMN candidate_email VARCHAR(200)"))
            print("Added candidate_email column")
        except Exception as e:
            print(f"Error adding candidate_email: {e}")

        # Add candidate_phone
        try:
            await conn.execute(text("ALTER TABLE applications ADD COLUMN candidate_phone VARCHAR(20)"))
            print("Added candidate_phone column")
        except Exception as e:
            print(f"Error adding candidate_phone: {e}")

        # Add candidate_experience
        try:
            await conn.execute(text("ALTER TABLE applications ADD COLUMN candidate_experience VARCHAR(100)"))
            print("Added candidate_experience column")
        except Exception as e:
            print(f"Error adding candidate_experience: {e}")

        # Add candidate_resume_url
        try:
            await conn.execute(text("ALTER TABLE applications ADD COLUMN candidate_resume_url TEXT"))
            print("Added candidate_resume_url column")
        except Exception as e:
            print(f"Error adding candidate_resume_url: {e}")

        print("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(add_candidate_columns())
