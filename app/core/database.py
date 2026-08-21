import os
import pkgutil
import importlib
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_timeout=30,
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
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def import_all_models():
    """Dynamically import all model files in app/ to register on Base.metadata."""
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.dirname(app_dir)
    for root, dirs, files in os.walk(app_dir):
        if os.path.basename(root) == "models":
            rel_path = os.path.relpath(root, root_dir)
            pkg_name = rel_path.replace(os.sep, ".").replace("/", ".")
            for _, mod_name, _ in pkgutil.iter_modules([root]):
                if not mod_name.startswith("__"):
                    try:
                        importlib.import_module(f"{pkg_name}.{mod_name}")
                    except Exception:
                        pass


async def init_db():
    """Create all tables, enable pgvector extension, and apply performance indexes."""
    import_all_models()
    # Explicit imports so create_all always sees social-login tables
    # (import_all_models swallows individual import errors).
    import app.shared.models.oauth_account  # noqa: F401
    import app.shared.models.login_history  # noqa: F401
    import app.shared.models.auth_session  # noqa: F401
    import app.shared.models.auth_provider_settings  # noqa: F401
    import app.shared.models.user  # noqa: F401
    import app.shared.models.user_credit  # noqa: F401

    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.warning(f"Database table creation / extension setup warning: {e}")

    # Columns on existing users table (create_all does not ALTER existing tables).
    # Each ALTER statement runs in its own transaction block so a failure on one does not abort others.
    alters = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_method VARCHAR(32)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(32)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_first_login BOOLEAN DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS registration_ip VARCHAR(45)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS welcome_email_status VARCHAR(20)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS welcome_email_error TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_locations JSON",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS father_or_mother_name VARCHAR(200)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS gender VARCHAR(50)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS highest_qualification VARCHAR(200)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS stream_specialization VARCHAR(200)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS college_institute_name VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_job_sector VARCHAR(200)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS job_roles_offering TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS specific_requirements TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS auto_apply_enabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS company_address VARCHAR(500)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS discount_amount DOUBLE PRECISION DEFAULT 0.0",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS preferred_batch_id VARCHAR(50)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS token_amount DOUBLE PRECISION NOT NULL DEFAULT 2000.0",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS token_paid_at TIMESTAMP",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS venue_visit_deadline TIMESTAMP",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS token_expired BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMP",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS refund_reason TEXT",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS refunded_by_id UUID",
        "ALTER TABLE auth_provider_settings ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 1",
        "ALTER TABLE ai_coach_sessions ADD COLUMN IF NOT EXISTS mode VARCHAR(10) DEFAULT 'text'",
    ]
    for sql in alters:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(sql))
        except Exception as e:
            logger.warning(f"Database migration statement skipped: {sql} ({e})")

    # Performance Dashboard Indexes & HNSW Vector Indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_jobs_provider_id ON job_postings (provider_id)",
        "CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications (job_id)",
        "CREATE INDEX IF NOT EXISTS idx_applications_seeker_id ON applications (seeker_id)",
        "CREATE INDEX IF NOT EXISTS idx_matches_job_id ON matches (job_id)",
        "CREATE INDEX IF NOT EXISTS idx_matches_seeker_id ON matches (seeker_id)",
        "CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)",
        "CREATE INDEX IF NOT EXISTS ix_applications_status ON applications (status)",
        "CREATE INDEX IF NOT EXISTS ix_external_candidates_status ON external_candidates (status)",
        "CREATE INDEX IF NOT EXISTS ix_external_candidates_is_matched ON external_candidates (is_matched)",
        "CREATE INDEX IF NOT EXISTS ix_job_postings_embedding_hnsw ON job_postings USING hnsw (embedding vector_cosine_ops)",
        "CREATE INDEX IF NOT EXISTS ix_resumes_embedding_hnsw ON resumes USING hnsw (embedding vector_cosine_ops)",
        "CREATE INDEX IF NOT EXISTS idx_tpe_token_expired ON training_portal_enrollments (token_expired)",
    ]
    for sql in indexes:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(sql))
        except Exception as e:
            logger.warning(f"Database index creation skipped: {sql} ({e})")

