from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables and enable pgvector extension."""
    async with engine.begin() as conn:
        await conn.execute(__import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector"))
        from models import user, resume, job, match, application, notification, otp, interview, provider_interview_settings, provider_availability_window, assessment, portfolio, master, ai_interview, roadmap, ai_coach, imported_user_password, attendance, job_fair, email_template, email_campaign  # noqa
        await conn.run_sync(Base.metadata.create_all)


async def patch_email_admin_schema():
    """Add columns missing from older email_templates / email_campaigns tables."""
    from sqlalchemy import text

    statements = [
        "ALTER TABLE email_templates ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE email_templates ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE email_templates ADD COLUMN IF NOT EXISTS created_by_id UUID REFERENCES users(id) ON DELETE SET NULL",
        "ALTER TABLE email_templates ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE email_templates ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE email_templates ADD COLUMN IF NOT EXISTS design_config JSON NOT NULL DEFAULT '{}'::json",
        "ALTER TABLE email_templates ADD COLUMN IF NOT EXISTS category emailtemplatecategory NOT NULL DEFAULT 'custom'",
        "ALTER TABLE email_templates ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE email_templates ALTER COLUMN design_config SET DEFAULT '{}'::json",
        "ALTER TABLE email_templates ALTER COLUMN category SET DEFAULT 'custom'",
        "ALTER TABLE email_templates ALTER COLUMN is_system SET DEFAULT FALSE",
        "ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS job_id VARCHAR(36)",
        "ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS created_by UUID",
        "ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS started_at TIMESTAMP",
        "ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP",
        "ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
    ]
    async with engine.begin() as conn:
        for sql in statements:
            await conn.execute(text(sql))
