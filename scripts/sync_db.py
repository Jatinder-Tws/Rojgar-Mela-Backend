"""
Database synchronization utility for Rojgar Mela.
Adds missing columns and creates any tables defined in SQLAlchemy models.
Usage:
    docker compose exec backend python scripts/sync_db.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import engine, Base
from sqlalchemy import text, inspect


async def sync_database():
    async with engine.begin() as conn:
        print("[*] Synchronizing missing columns across all tables...")
        inspector = await conn.run_sync(lambda sync_conn: inspect(sync_conn))
        db_tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())

        for table_name, table in Base.metadata.tables.items():
            if table_name not in db_tables:
                print(f"[*] Creating missing table '{table_name}'...")
                await conn.run_sync(lambda sync_conn: table.create(sync_conn))
                continue

            columns_in_db = {
                col["name"]
                for col in await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_columns(table_name))
            }

            for col in table.columns:
                if col.name not in columns_in_db:
                    col_type = col.type.compile(engine.dialect)
                    print(f"[*] Adding missing column '{col.name}' ({col_type}) to table '{table_name}'...")
                    sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col.name} {col_type};"
                    await conn.execute(text(sql))

        print("[✓] All tables and columns are 100% synchronized with models!")


if __name__ == "__main__":
    asyncio.run(sync_database())
