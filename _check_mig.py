from sqlalchemy import create_engine, text
import os
url = os.environ["DATABASE_URL"].replace("+asyncpg", "")
e = create_engine(url)
with e.connect() as c:
    print("alembic:", c.execute(text("select version_num from alembic_version")).fetchall())
    print("indexes:", c.execute(text("select indexname from pg_indexes where tablename='applications' and indexname like '%seeker%'")).fetchall())
