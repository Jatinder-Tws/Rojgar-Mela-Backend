"""
Job Fair DB Migration Script
=============================
Creates all three job fair tables (job_fairs, job_fair_companies, job_fair_seekers)
with their indexes and foreign keys.

Also adds the banner_image_url column to an existing job_fairs table
using ALTER TABLE … IF NOT EXISTS (safe to run on an already-migrated DB).

Usage:
    python add_job_fair_banner_image.py
"""

import asyncio
from database import engine
from sqlalchemy import text


CREATE_JOB_FAIRS = """
CREATE TABLE IF NOT EXISTS job_fairs (
    id          UUID        PRIMARY KEY,
    slug        VARCHAR(100) NOT NULL,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    date        TIMESTAMP   NOT NULL,
    location    VARCHAR(200) NOT NULL,
    banner_image_url TEXT,
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);
"""

CREATE_IDX_JOB_FAIRS_SLUG = """
CREATE UNIQUE INDEX IF NOT EXISTS ix_job_fairs_slug
    ON job_fairs (slug);
"""

CREATE_JOB_FAIR_COMPANIES = """
CREATE TABLE IF NOT EXISTS job_fair_companies (
    id              UUID        PRIMARY KEY,
    job_fair_id     UUID        NOT NULL REFERENCES job_fairs(id) ON DELETE CASCADE,
    provider_id     UUID        NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    department      VARCHAR(100),
    sector          VARCHAR(100),
    vacancy         VARCHAR(100),
    registered_at   TIMESTAMP   NOT NULL DEFAULT NOW()
);
"""

CREATE_IDX_JF_COMPANIES_JOB_FAIR_ID = """
CREATE INDEX IF NOT EXISTS ix_job_fair_companies_job_fair_id
    ON job_fair_companies (job_fair_id);
"""

CREATE_IDX_JF_COMPANIES_PROVIDER_ID = """
CREATE INDEX IF NOT EXISTS ix_job_fair_companies_provider_id
    ON job_fair_companies (provider_id);
"""

CREATE_JOB_FAIR_SEEKERS = """
CREATE TABLE IF NOT EXISTS job_fair_seekers (
    id              UUID        PRIMARY KEY,
    job_fair_id     UUID        NOT NULL REFERENCES job_fairs(id) ON DELETE CASCADE,
    seeker_id       UUID        NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    is_attending    BOOLEAN     NOT NULL DEFAULT TRUE,
    registered_at   TIMESTAMP   NOT NULL DEFAULT NOW()
);
"""

CREATE_IDX_JF_SEEKERS_JOB_FAIR_ID = """
CREATE INDEX IF NOT EXISTS ix_job_fair_seekers_job_fair_id
    ON job_fair_seekers (job_fair_id);
"""

CREATE_IDX_JF_SEEKERS_SEEKER_ID = """
CREATE INDEX IF NOT EXISTS ix_job_fair_seekers_seeker_id
    ON job_fair_seekers (seeker_id);
"""

# Adds banner_image_url to an already-existing job_fairs table.
# Safe to run even if the column already exists (PostgreSQL 9.6+).
ALTER_ADD_BANNER = """
ALTER TABLE job_fairs
    ADD COLUMN IF NOT EXISTS banner_image_url TEXT;
"""


async def run_migration():
    async with engine.begin() as conn:

        # ── 1. Create job_fairs ──────────────────────────────────────
        print("Creating table: job_fairs ...")
        await conn.execute(text(CREATE_JOB_FAIRS))
        await conn.execute(text(CREATE_IDX_JOB_FAIRS_SLUG))
        print("  ✓ job_fairs")

        # ── 2. Create job_fair_companies ─────────────────────────────
        print("Creating table: job_fair_companies ...")
        await conn.execute(text(CREATE_JOB_FAIR_COMPANIES))
        await conn.execute(text(CREATE_IDX_JF_COMPANIES_JOB_FAIR_ID))
        await conn.execute(text(CREATE_IDX_JF_COMPANIES_PROVIDER_ID))
        print("  ✓ job_fair_companies")

        # ── 3. Create job_fair_seekers ───────────────────────────────
        print("Creating table: job_fair_seekers ...")
        await conn.execute(text(CREATE_JOB_FAIR_SEEKERS))
        await conn.execute(text(CREATE_IDX_JF_SEEKERS_JOB_FAIR_ID))
        await conn.execute(text(CREATE_IDX_JF_SEEKERS_SEEKER_ID))
        print("  ✓ job_fair_seekers")

        # ── 4. Add banner_image_url column (ALTER TABLE, idempotent) ──
        print("Adding column banner_image_url to job_fairs (if not exists) ...")
        await conn.execute(text(ALTER_ADD_BANNER))
        print("  ✓ banner_image_url column ready")

    print("\nAll job fair migrations applied successfully.")


if __name__ == "__main__":
    asyncio.run(run_migration())
