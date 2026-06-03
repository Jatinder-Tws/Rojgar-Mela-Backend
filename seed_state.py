"""Track one-time master seed completion in PostgreSQL (survives container restarts)."""

from sqlalchemy import text

from database import engine

MASTER_SEED_KEY = "master_data"


async def ensure_seed_state_table() -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS app_seed_state (
                    seed_key VARCHAR(64) PRIMARY KEY,
                    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )


async def is_master_seed_completed() -> bool:
    await ensure_seed_state_table()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM app_seed_state WHERE seed_key = :key LIMIT 1"),
            {"key": MASTER_SEED_KEY},
        )
        return result.first() is not None


async def mark_master_seed_completed() -> None:
    await ensure_seed_state_table()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO app_seed_state (seed_key, completed_at)
                VALUES (:key, NOW())
                ON CONFLICT (seed_key) DO NOTHING
                """
            ),
            {"key": MASTER_SEED_KEY},
        )
