import asyncio
from sqlalchemy import text
from database import engine, init_db

async def add_columns():
    async with engine.begin() as conn:
        # Add Seeker Columns
        columns_to_add = [
            ("father_or_mother_name", "VARCHAR(200)"),
            ("gender", "VARCHAR(50)"),
            ("address", "TEXT"),
            ("highest_qualification", "VARCHAR(200)"),
            ("stream_specialization", "VARCHAR(200)"),
            ("college_institute_name", "VARCHAR(255)"),
            ("preferred_job_sector", "VARCHAR(200)"),
            ("job_roles_offering", "TEXT"),
            ("specific_requirements", "TEXT")
        ]

        print("Adding columns to users table...")
        for col_name, col_type in columns_to_add:
            try:
                await conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};"))
                print(f"Added column {col_name} to users table.")
            except Exception as e:
                print(f"Error adding {col_name} (might already exist): {e}")

        # Now run init_db to create any missing tables (like imported_user_passwords)
        print("Running init_db to create imported_user_passwords...")
        # Since we are already in an engine block, init_db() will open another, that's fine.

async def main():
    await add_columns()
    await init_db()

if __name__ == "__main__":
    asyncio.run(main())
