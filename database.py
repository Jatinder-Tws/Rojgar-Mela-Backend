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
        from models import user, resume, job, match, application, notification, otp, interview, provider_interview_settings, provider_availability_window, assessment, portfolio, master, ai_interview, roadmap, ai_coach, imported_user_password, attendance, job_fair, email_template, email_campaign, support_ticket, platform_feedback, contact_inquiry, company_internship, training_course, training_portal_course, training_portal_category, training_portal_teacher, training_portal_internship, training_portal_batch, training_portal_enrollment, training_portal_class_session, training_portal_payment, training_portal_candidate_notification, training_portal_transaction, training_portal_refund_request, training_portal_attendance  # noqa
        await conn.run_sync(Base.metadata.create_all)


async def patch_interview_application_schema():
    """Add interview lifecycle columns and application status enum values."""
    from sqlalchemy import text

    statements = [
        "ALTER TYPE applicationstatus ADD VALUE IF NOT EXISTS 'interviewing'",
        "ALTER TYPE applicationstatus ADD VALUE IF NOT EXISTS 'selected'",
        "ALTER TABLE interviews ADD COLUMN IF NOT EXISTS interview_type VARCHAR(20) NOT NULL DEFAULT 'video'",
        "ALTER TABLE interviews ADD COLUMN IF NOT EXISTS meeting_link TEXT",
        "ALTER TABLE interviews ADD COLUMN IF NOT EXISTS location TEXT",
        "ALTER TABLE interviews ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'scheduled'",
    ]
    async with engine.begin() as conn:
        for sql in statements:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass


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


async def patch_support_bot_schema():
    """Add help desk bot columns to support tables."""
    from sqlalchemy import text

    statements = [
        "ALTER TABLE support_tickets ADD COLUMN IF NOT EXISTS bot_handled BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE support_tickets ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMP",
        "ALTER TABLE ticket_messages ADD COLUMN IF NOT EXISTS is_bot_reply BOOLEAN NOT NULL DEFAULT FALSE",
    ]
    async with engine.begin() as conn:
        for sql in statements:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass


async def patch_dashboard_indexes():
    """Create indexes for dashboard analytics optimization if they do not exist."""
    from sqlalchemy import text

    statements = [
        "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
        "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_users_is_super_admin ON users(is_super_admin)",
        "CREATE INDEX IF NOT EXISTS idx_users_experience ON users(experience)",
        "CREATE INDEX IF NOT EXISTS idx_matches_score ON matches(score)",
        "CREATE INDEX IF NOT EXISTS idx_matches_created_at ON matches(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_job_postings_is_active ON job_postings(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_job_postings_created_at ON job_postings(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_applications_applied_at ON applications(applied_at)",
        "CREATE INDEX IF NOT EXISTS idx_interviews_scheduled_at ON interviews(scheduled_at)",
    ]
    async with engine.begin() as conn:
        for sql in statements:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass


async def patch_company_internships_schema():
    """Ensure all columns exist for company internships and training course models."""
    from sqlalchemy import text
    statements = [
        # company_internships columns
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS provider_id UUID",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS title VARCHAR(200)",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(500)",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS brochure_url VARCHAR(500)",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS is_stipend BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS stipend_amount VARCHAR(100)",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS duration INTEGER",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS duration_unit VARCHAR(50) NOT NULL DEFAULT 'month'",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS state VARCHAR(100)",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS city VARCHAR(100)",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS address TEXT",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS apply_by DATE",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS start_date VARCHAR(200)",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS company_name VARCHAR(200)",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS who_can_apply TEXT",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS skills_required JSON",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS perks JSON",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE company_internships ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",

        # company_internship_applications columns
        "ALTER TABLE company_internship_applications ADD COLUMN IF NOT EXISTS internship_id VARCHAR(50)",
        "ALTER TABLE company_internship_applications ADD COLUMN IF NOT EXISTS seeker_id UUID",
        "ALTER TABLE company_internship_applications ADD COLUMN IF NOT EXISTS why_join TEXT",
        "ALTER TABLE company_internship_applications ADD COLUMN IF NOT EXISTS career_goals TEXT",
        "ALTER TABLE company_internship_applications ADD COLUMN IF NOT EXISTS why_consider TEXT",
        "ALTER TABLE company_internship_applications ADD COLUMN IF NOT EXISTS resume_url VARCHAR(500)",
        "ALTER TABLE company_internship_applications ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE company_internship_applications ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",

        # training_courses columns
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS provider_id UUID",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS title VARCHAR(200)",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(500)",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS brochure_url VARCHAR(500)",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS is_paid BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS price VARCHAR(100)",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS duration INTEGER",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS duration_unit VARCHAR(50) NOT NULL DEFAULT 'month'",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS skills_learned JSON",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS has_certificate BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS company_name VARCHAR(200)",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS state VARCHAR(100)",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS city VARCHAR(100)",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_courses ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",

        # training_modules columns
        "ALTER TABLE training_modules ADD COLUMN IF NOT EXISTS course_id VARCHAR(50)",
        "ALTER TABLE training_modules ADD COLUMN IF NOT EXISTS title VARCHAR(200)",
        "ALTER TABLE training_modules ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE training_modules ADD COLUMN IF NOT EXISTS order_index INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE training_modules ADD COLUMN IF NOT EXISTS estimated_hours FLOAT",
        "ALTER TABLE training_modules ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_modules ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",

        # training_module_topics columns
        "ALTER TABLE training_module_topics ADD COLUMN IF NOT EXISTS module_id VARCHAR(50)",
        "ALTER TABLE training_module_topics ADD COLUMN IF NOT EXISTS title VARCHAR(200)",
        "ALTER TABLE training_module_topics ADD COLUMN IF NOT EXISTS order_index INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE training_module_topics ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",

        # training_course_applications columns
        "ALTER TABLE training_course_applications ADD COLUMN IF NOT EXISTS course_id VARCHAR(50)",
        "ALTER TABLE training_course_applications ADD COLUMN IF NOT EXISTS seeker_id UUID",
        "ALTER TABLE training_course_applications ADD COLUMN IF NOT EXISTS first_name VARCHAR(100)",
        "ALTER TABLE training_course_applications ADD COLUMN IF NOT EXISTS last_name VARCHAR(100)",
        "ALTER TABLE training_course_applications ADD COLUMN IF NOT EXISTS email VARCHAR(100)",
        "ALTER TABLE training_course_applications ADD COLUMN IF NOT EXISTS phone VARCHAR(100)",
        "ALTER TABLE training_course_applications ADD COLUMN IF NOT EXISTS location VARCHAR(200)",
        "ALTER TABLE training_course_applications ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_course_applications ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()"
    ]
    async with engine.begin() as conn:
        for sql in statements:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass


async def patch_training_portal_schema():
    """Add key_highlights column to training portal courses."""
    from sqlalchemy import text

    statements = [
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS key_highlights JSON NOT NULL DEFAULT '[]'::json",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS live_status VARCHAR(20) NOT NULL DEFAULT 'scheduled'",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS started_at TIMESTAMP",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS ended_at TIMESTAMP",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS session_report TEXT",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS covered_topic_ids JSON NOT NULL DEFAULT '[]'::json",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS attendance_marked BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL",
        "CREATE INDEX IF NOT EXISTS idx_tpt_user_id ON training_portal_teachers(user_id)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS preferred_batch_id VARCHAR(50)",
    ]
    async with engine.begin() as conn:
        for sql in statements:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass


async def patch_teacher_role_schema():
    """Add teacher to userrole enum and apply training table indexes."""
    from sqlalchemy import text
    statements = [
        "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'teacher'",
        "CREATE INDEX IF NOT EXISTS idx_tc_status_created ON training_courses(is_active, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_tca_course_status ON training_course_applications(course_id)",
        "CREATE INDEX IF NOT EXISTS idx_tca_user_status ON training_course_applications(seeker_id)",
    ]
    async with engine.begin() as conn:
        for sql in statements:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass

