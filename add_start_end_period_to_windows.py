import asyncio
import asyncpg

async def alter_provider_availability_windows():
    try:
        conn = await asyncpg.connect("postgresql://jobmatch:secret@postgres:5432/jobmatch_db")
    except Exception:
        conn = await asyncpg.connect("postgresql://jobmatch:secret@localhost:5432/jobmatch_db")
    try:
        # Add start_period
        try:
            await conn.execute('ALTER TABLE provider_availability_windows ADD COLUMN start_period VARCHAR(2) DEFAULT \'AM\';')
            print("Added start_period column to provider_availability_windows.")
        except asyncpg.exceptions.DuplicateColumnError:
            print("Column start_period already exists.")

        # Add end_period
        try:
            await conn.execute('ALTER TABLE provider_availability_windows ADD COLUMN end_period VARCHAR(2) DEFAULT \'AM\';')
            print("Added end_period column to provider_availability_windows.")
        except asyncpg.exceptions.DuplicateColumnError:
            print("Column end_period already exists.")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(alter_provider_availability_windows())
