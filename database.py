from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings
from sqlalchemy import text

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
        from models import user, resume, job, saved_job, match, application, notification, otp, interview, provider_interview_settings, provider_availability_window, assessment, portfolio, master, ai_interview, roadmap, ai_coach, imported_user_password, attendance, job_fair, email_template, email_campaign, support_ticket, platform_feedback, contact_inquiry, career_enquiry, company_internship, training_course, training_portal_course, training_portal_category, training_portal_teacher, training_portal_internship, training_portal_batch, training_portal_enrollment, training_portal_class_session, training_portal_payment, training_portal_candidate_notification, training_portal_transaction, training_portal_refund_request, training_portal_attendance, training_portal_leave_request, training_portal_behavior_report, google_calendar_token, training_portal_class_calendar_link  # noqa
        await conn.run_sync(Base.metadata.create_all)


async def patch_interview_application_schema():
    """Add interview lifecycle columns and application status enum values."""
    

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
        "ALTER TYPE audiencetype ADD VALUE IF NOT EXISTS 'csv_import'",
        "ALTER TYPE audiencetype ADD VALUE IF NOT EXISTS 'job_fair_seekers'",
        "ALTER TYPE audiencetype ADD VALUE IF NOT EXISTS 'job_fair_providers'",
    ]
    async with engine.begin() as conn:
        for sql in statements:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass


async def patch_support_bot_schema():
    """Add help desk bot columns to support tables."""
    

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
    """Ensure all training portal tables and columns exist (LMS portal models)."""
    

    statements = [
        # training_portal_courses
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS created_by_id UUID",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS title VARCHAR(200)",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS category VARCHAR(100)",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS duration VARCHAR(50)",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS delivery_mode VARCHAR(20) NOT NULL DEFAULT 'Offline'",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'published'",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS skill_level VARCHAR(20) NOT NULL DEFAULT 'Beginner'",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS fee FLOAT NOT NULL DEFAULT 12000.0",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(500)",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS prerequisites TEXT",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS key_highlights JSON NOT NULL DEFAULT '[]'::json",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS curriculum JSON NOT NULL DEFAULT '[]'::json",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_portal_courses ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE INDEX IF NOT EXISTS idx_tpc_created_by_id ON training_portal_courses(created_by_id)",
        "CREATE INDEX IF NOT EXISTS idx_tpc_category ON training_portal_courses(category)",
        "CREATE INDEX IF NOT EXISTS idx_tpc_status ON training_portal_courses(status)",

        # training_portal_course_categories
        "ALTER TABLE training_portal_course_categories ADD COLUMN IF NOT EXISTS name VARCHAR(100)",
        "ALTER TABLE training_portal_course_categories ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE training_portal_course_categories ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_portal_course_categories ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_tpcc_name ON training_portal_course_categories(name)",

        # training_portal_teachers
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS created_by_id UUID",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS user_id UUID",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS name VARCHAR(200)",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS email VARCHAR(200)",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS phone VARCHAR(50) NOT NULL DEFAULT '+91 00000 00000'",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS bio TEXT NOT NULL DEFAULT 'Qualified physical classroom instructor.'",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS subjects JSON NOT NULL DEFAULT '[]'::json",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS rating FLOAT NOT NULL DEFAULT 5.0",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active'",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS avatar VARCHAR(500)",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS login_username VARCHAR(100)",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS login_password VARCHAR(200)",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS login_active BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS last_login_at VARCHAR(50)",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_portal_teachers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE INDEX IF NOT EXISTS idx_tpt_created_by_id ON training_portal_teachers(created_by_id)",
        "CREATE INDEX IF NOT EXISTS idx_tpt_user_id ON training_portal_teachers(user_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_tpt_email ON training_portal_teachers(email)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_tpt_login_username ON training_portal_teachers(login_username)",
        "CREATE INDEX IF NOT EXISTS idx_tpt_status ON training_portal_teachers(status)",

        # training_portal_internships
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS created_by_id UUID",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS title VARCHAR(200)",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS duration VARCHAR(50)",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS is_paid BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS fee FLOAT NOT NULL DEFAULT 0.0",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS start_date VARCHAR(50)",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS end_date VARCHAR(50)",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS venue VARCHAR(300)",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS max_seats INTEGER NOT NULL DEFAULT 15",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS seats_filled INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active'",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS laptop_required BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_portal_internships ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE INDEX IF NOT EXISTS idx_tpi_created_by_id ON training_portal_internships(created_by_id)",
        "CREATE INDEX IF NOT EXISTS idx_tpi_status ON training_portal_internships(status)",

        # training_portal_batches
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS course_id VARCHAR(50)",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS batch_name VARCHAR(200)",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS instructor_id VARCHAR(50)",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS instructor_name VARCHAR(200)",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS start_date VARCHAR(50)",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS end_date VARCHAR(50)",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS days JSON NOT NULL DEFAULT '[]'::json",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS time_slot VARCHAR(100) NOT NULL DEFAULT 'To be scheduled'",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS venue VARCHAR(300) NOT NULL DEFAULT 'To be scheduled'",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS max_seats INTEGER NOT NULL DEFAULT 20",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS delivery_mode VARCHAR(20) NOT NULL DEFAULT 'Offline'",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'upcoming'",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS covered_topics JSON NOT NULL DEFAULT '[]'::json",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS created_by_id UUID",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_portal_batches ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE INDEX IF NOT EXISTS idx_tpb_course_id ON training_portal_batches(course_id)",
        "CREATE INDEX IF NOT EXISTS idx_tpb_status ON training_portal_batches(status)",

        # training_portal_enrollments
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS candidate_user_id UUID",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS candidate_name VARCHAR(200)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS candidate_email VARCHAR(200)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS candidate_phone VARCHAR(50)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS enrollment_type VARCHAR(20)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS item_id VARCHAR(50)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS batch_id VARCHAR(50)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS title VARCHAR(300)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS batch_name VARCHAR(200)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS enrollment_date VARCHAR(50)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS payment_type VARCHAR(30) NOT NULL DEFAULT 'Full Payment'",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS payment_status VARCHAR(30) NOT NULL DEFAULT 'pending'",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS payment_mode VARCHAR(30)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS total_fee FLOAT NOT NULL DEFAULT 0.0",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS paid_amount FLOAT NOT NULL DEFAULT 0.0",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS balance_due FLOAT NOT NULL DEFAULT 0.0",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS installments JSON NOT NULL DEFAULT '[]'::json",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active'",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS attendance_percentage INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS completion_percentage INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS is_certificate_issued BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS certificate_id VARCHAR(100)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS certificate_status VARCHAR(30)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS certificate_reason TEXT",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS voter_card_url VARCHAR(500)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS laptop_confirmed BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS notes TEXT",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS preferred_batch_id VARCHAR(50)",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_portal_enrollments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE INDEX IF NOT EXISTS idx_tpe_candidate_user_id ON training_portal_enrollments(candidate_user_id)",
        "CREATE INDEX IF NOT EXISTS idx_tpe_candidate_email ON training_portal_enrollments(candidate_email)",
        "CREATE INDEX IF NOT EXISTS idx_tpe_enrollment_type ON training_portal_enrollments(enrollment_type)",
        "CREATE INDEX IF NOT EXISTS idx_tpe_item_id ON training_portal_enrollments(item_id)",
        "CREATE INDEX IF NOT EXISTS idx_tpe_batch_id ON training_portal_enrollments(batch_id)",
        "CREATE INDEX IF NOT EXISTS idx_tpe_payment_status ON training_portal_enrollments(payment_status)",
        "CREATE INDEX IF NOT EXISTS idx_tpe_status ON training_portal_enrollments(status)",
        "CREATE INDEX IF NOT EXISTS idx_tpe_preferred_batch_id ON training_portal_enrollments(preferred_batch_id)",

        # training_portal_class_sessions
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS batch_id VARCHAR(50)",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS item_id VARCHAR(50)",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS title VARCHAR(300)",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS instructor_name VARCHAR(200)",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS date VARCHAR(50)",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS start_time VARCHAR(50)",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS end_time VARCHAR(50)",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS days JSON NOT NULL DEFAULT '[]'::json",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS venue VARCHAR(300)",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS note TEXT",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS schedule_type VARCHAR(20) NOT NULL DEFAULT 'one_time'",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS postponed BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS teacher_unavailable BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS live_status VARCHAR(20) NOT NULL DEFAULT 'scheduled'",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS started_at TIMESTAMP",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS ended_at TIMESTAMP",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS session_report TEXT",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS covered_topic_ids JSON NOT NULL DEFAULT '[]'::json",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS attachment_url VARCHAR(500)",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS attachment_filename VARCHAR(255)",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS reminder_15_sent BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS late_start_reason TEXT",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS early_end_reason TEXT",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS attendance_marked BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS end_reminder_sent BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS created_by_id UUID",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE INDEX IF NOT EXISTS idx_tpcs_batch_id ON training_portal_class_sessions(batch_id)",
        "CREATE INDEX IF NOT EXISTS idx_tpcs_item_id ON training_portal_class_sessions(item_id)",
        "CREATE INDEX IF NOT EXISTS idx_tpcs_live_status ON training_portal_class_sessions(live_status)",

        # training_portal_payment_settings
        "ALTER TABLE training_portal_payment_settings ADD COLUMN IF NOT EXISTS upi BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE training_portal_payment_settings ADD COLUMN IF NOT EXISTS card BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE training_portal_payment_settings ADD COLUMN IF NOT EXISTS emi BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE training_portal_payment_settings ADD COLUMN IF NOT EXISTS offline BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE training_portal_payment_settings ADD COLUMN IF NOT EXISTS email BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE training_portal_payment_settings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",

        # training_portal_payment_orders
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS enrollment_id VARCHAR(50)",
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS candidate_email VARCHAR(200)",
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS amount_paise INTEGER",
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS currency VARCHAR(10) NOT NULL DEFAULT 'INR'",
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR(30) NOT NULL DEFAULT 'upi'",
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS provider VARCHAR(30) NOT NULL DEFAULT 'razorpay'",
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS provider_order_id VARCHAR(100)",
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS provider_payment_id VARCHAR(100)",
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS provider_signature VARCHAR(300)",
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'created'",
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS webhook_payload JSON",
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP",
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_portal_payment_orders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE INDEX IF NOT EXISTS idx_tppo_enrollment_id ON training_portal_payment_orders(enrollment_id)",
        "CREATE INDEX IF NOT EXISTS idx_tppo_candidate_email ON training_portal_payment_orders(candidate_email)",
        "CREATE INDEX IF NOT EXISTS idx_tppo_provider_order_id ON training_portal_payment_orders(provider_order_id)",
        "CREATE INDEX IF NOT EXISTS idx_tppo_provider_payment_id ON training_portal_payment_orders(provider_payment_id)",
        "CREATE INDEX IF NOT EXISTS idx_tppo_status ON training_portal_payment_orders(status)",

        # training_portal_candidate_notifications
        "ALTER TABLE training_portal_candidate_notifications ADD COLUMN IF NOT EXISTS candidate_email VARCHAR(200)",
        "ALTER TABLE training_portal_candidate_notifications ADD COLUMN IF NOT EXISTS recipient_role VARCHAR(30) NOT NULL DEFAULT 'candidate'",
        "ALTER TABLE training_portal_candidate_notifications ADD COLUMN IF NOT EXISTS is_read BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE training_portal_candidate_notifications ADD COLUMN IF NOT EXISTS notification_type VARCHAR(50)",
        "ALTER TABLE training_portal_candidate_notifications ADD COLUMN IF NOT EXISTS title VARCHAR(300)",
        "ALTER TABLE training_portal_candidate_notifications ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE training_portal_candidate_notifications ADD COLUMN IF NOT EXISTS detail TEXT",
        "ALTER TABLE training_portal_candidate_notifications ADD COLUMN IF NOT EXISTS event_date VARCHAR(50)",
        "ALTER TABLE training_portal_candidate_notifications ADD COLUMN IF NOT EXISTS severity VARCHAR(20) NOT NULL DEFAULT 'info'",
        "ALTER TABLE training_portal_candidate_notifications ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE INDEX IF NOT EXISTS idx_tpcn_candidate_email ON training_portal_candidate_notifications(candidate_email)",
        "CREATE INDEX IF NOT EXISTS idx_tpcn_recipient_role ON training_portal_candidate_notifications(recipient_role)",
        "CREATE INDEX IF NOT EXISTS idx_tpcn_is_read ON training_portal_candidate_notifications(is_read)",

        # training_portal_transactions
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS transaction_id VARCHAR(80)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS enrollment_id VARCHAR(50)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS candidate_email VARCHAR(200)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS candidate_name VARCHAR(200)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS program_title VARCHAR(300)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS transaction_type VARCHAR(30)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS amount FLOAT NOT NULL DEFAULT 0.0",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS currency VARCHAR(10) NOT NULL DEFAULT 'INR'",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS payment_mode VARCHAR(30)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'completed'",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS provider VARCHAR(30)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS provider_transaction_id VARCHAR(120)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS reference_order_id VARCHAR(50)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS transaction_reference VARCHAR(120)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS bank_name VARCHAR(150)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS batch_id VARCHAR(50)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS batch_name VARCHAR(200)",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS notes TEXT",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS created_by_id UUID",
        "ALTER TABLE training_portal_transactions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_tptx_transaction_id ON training_portal_transactions(transaction_id)",
        "CREATE INDEX IF NOT EXISTS idx_tptx_enrollment_id ON training_portal_transactions(enrollment_id)",
        "CREATE INDEX IF NOT EXISTS idx_tptx_candidate_email ON training_portal_transactions(candidate_email)",
        "CREATE INDEX IF NOT EXISTS idx_tptx_transaction_type ON training_portal_transactions(transaction_type)",
        "CREATE INDEX IF NOT EXISTS idx_tptx_status ON training_portal_transactions(status)",
        "CREATE INDEX IF NOT EXISTS idx_tptx_provider_transaction_id ON training_portal_transactions(provider_transaction_id)",
        "CREATE INDEX IF NOT EXISTS idx_tptx_created_at ON training_portal_transactions(created_at)",

        # training_portal_refund_requests
        "ALTER TABLE training_portal_refund_requests ADD COLUMN IF NOT EXISTS enrollment_id VARCHAR(50)",
        "ALTER TABLE training_portal_refund_requests ADD COLUMN IF NOT EXISTS candidate_email VARCHAR(200)",
        "ALTER TABLE training_portal_refund_requests ADD COLUMN IF NOT EXISTS candidate_name VARCHAR(200)",
        "ALTER TABLE training_portal_refund_requests ADD COLUMN IF NOT EXISTS program_title VARCHAR(300)",
        "ALTER TABLE training_portal_refund_requests ADD COLUMN IF NOT EXISTS requested_amount FLOAT NOT NULL DEFAULT 0.0",
        "ALTER TABLE training_portal_refund_requests ADD COLUMN IF NOT EXISTS reason TEXT",
        "ALTER TABLE training_portal_refund_requests ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pending'",
        "ALTER TABLE training_portal_refund_requests ADD COLUMN IF NOT EXISTS admin_notes TEXT",
        "ALTER TABLE training_portal_refund_requests ADD COLUMN IF NOT EXISTS resolved_by_id UUID",
        "ALTER TABLE training_portal_refund_requests ADD COLUMN IF NOT EXISTS requested_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_portal_refund_requests ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP",
        "ALTER TABLE training_portal_refund_requests ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_portal_refund_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE INDEX IF NOT EXISTS idx_tprr_enrollment_id ON training_portal_refund_requests(enrollment_id)",
        "CREATE INDEX IF NOT EXISTS idx_tprr_candidate_email ON training_portal_refund_requests(candidate_email)",
        "CREATE INDEX IF NOT EXISTS idx_tprr_status ON training_portal_refund_requests(status)",

        # training_portal_attendance_records
        "ALTER TABLE training_portal_attendance_records ADD COLUMN IF NOT EXISTS class_session_id VARCHAR(50)",
        "ALTER TABLE training_portal_attendance_records ADD COLUMN IF NOT EXISTS enrollment_id VARCHAR(50)",
        "ALTER TABLE training_portal_attendance_records ADD COLUMN IF NOT EXISTS batch_id VARCHAR(50)",
        "ALTER TABLE training_portal_attendance_records ADD COLUMN IF NOT EXISTS candidate_email VARCHAR(200)",
        "ALTER TABLE training_portal_attendance_records ADD COLUMN IF NOT EXISTS candidate_name VARCHAR(200)",
        "ALTER TABLE training_portal_attendance_records ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'present'",
        "ALTER TABLE training_portal_attendance_records ADD COLUMN IF NOT EXISTS marked_by_id UUID",
        "ALTER TABLE training_portal_attendance_records ADD COLUMN IF NOT EXISTS marked_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_portal_attendance_records ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE INDEX IF NOT EXISTS idx_tpar_class_session_id ON training_portal_attendance_records(class_session_id)",
        "CREATE INDEX IF NOT EXISTS idx_tpar_enrollment_id ON training_portal_attendance_records(enrollment_id)",
        "CREATE INDEX IF NOT EXISTS idx_tpar_batch_id ON training_portal_attendance_records(batch_id)",
        "CREATE INDEX IF NOT EXISTS idx_tpar_candidate_email ON training_portal_attendance_records(candidate_email)",
        "ALTER TABLE training_portal_attendance_records ADD COLUMN IF NOT EXISTS occurrence_date VARCHAR(50) NOT NULL DEFAULT ''",
        "ALTER TABLE training_portal_attendance_records DROP CONSTRAINT IF EXISTS uq_session_enrollment_attendance",
        "DROP INDEX IF EXISTS uq_session_enrollment_attendance",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_session_enrollment_occurrence_attendance ON training_portal_attendance_records(class_session_id, enrollment_id, occurrence_date)",
        "ALTER TABLE training_portal_class_sessions ADD COLUMN IF NOT EXISTS live_occurrence_date VARCHAR(50)",

        # training_portal_leave_requests
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS requester_type VARCHAR(20) NOT NULL DEFAULT 'student'",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS candidate_email VARCHAR(200)",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS candidate_name VARCHAR(200)",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS teacher_email VARCHAR(200)",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS teacher_name VARCHAR(200)",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS session_id VARCHAR(50)",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS date VARCHAR(50)",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS batch_id VARCHAR(50)",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS batch_name VARCHAR(200)",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS reason TEXT",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pending'",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS reviewed_by_id UUID",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS reviewed_by_role VARCHAR(20)",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS review_note TEXT",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_portal_leave_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE INDEX IF NOT EXISTS idx_tplr_requester_type ON training_portal_leave_requests(requester_type)",
        "CREATE INDEX IF NOT EXISTS idx_tplr_candidate_email ON training_portal_leave_requests(candidate_email)",
        "CREATE INDEX IF NOT EXISTS idx_tplr_teacher_email ON training_portal_leave_requests(teacher_email)",
        "CREATE INDEX IF NOT EXISTS idx_tplr_date ON training_portal_leave_requests(date)",
        "CREATE INDEX IF NOT EXISTS idx_tplr_batch_id ON training_portal_leave_requests(batch_id)",
        "CREATE INDEX IF NOT EXISTS idx_tplr_status ON training_portal_leave_requests(status)",
    ]
    async with engine.begin() as conn:
        for sql in statements:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass


async def patch_users_registration_schema():
    """Allow nullable phone for providers and store registration IP."""
    from sqlalchemy import text

    statements = [
        "ALTER TABLE users ALTER COLUMN phone DROP NOT NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS registration_ip VARCHAR(45)",
    ]
    async with engine.begin() as conn:
        for sql in statements:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass


async def patch_google_calendar_schema():
    """Ensure Google Calendar sync tables/columns exist."""
    from sqlalchemy import text

    statements = [
        # google_calendar_tokens
        "ALTER TABLE google_calendar_tokens ADD COLUMN IF NOT EXISTS user_id UUID",
        "ALTER TABLE google_calendar_tokens ADD COLUMN IF NOT EXISTS google_email VARCHAR(255)",
        "ALTER TABLE google_calendar_tokens ADD COLUMN IF NOT EXISTS access_token TEXT",
        "ALTER TABLE google_calendar_tokens ADD COLUMN IF NOT EXISTS refresh_token TEXT",
        "ALTER TABLE google_calendar_tokens ADD COLUMN IF NOT EXISTS token_uri VARCHAR(255) NOT NULL DEFAULT 'https://oauth2.googleapis.com/token'",
        "ALTER TABLE google_calendar_tokens ADD COLUMN IF NOT EXISTS scopes TEXT",
        "ALTER TABLE google_calendar_tokens ADD COLUMN IF NOT EXISTS expiry TIMESTAMP",
        "ALTER TABLE google_calendar_tokens ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE google_calendar_tokens ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_gct_user_id ON google_calendar_tokens(user_id)",

        # training_portal_class_calendar_links
        "ALTER TABLE training_portal_class_calendar_links ADD COLUMN IF NOT EXISTS session_id VARCHAR(50)",
        "ALTER TABLE training_portal_class_calendar_links ADD COLUMN IF NOT EXISTS user_id UUID",
        "ALTER TABLE training_portal_class_calendar_links ADD COLUMN IF NOT EXISTS calendar_id VARCHAR(255) NOT NULL DEFAULT 'primary'",
        "ALTER TABLE training_portal_class_calendar_links ADD COLUMN IF NOT EXISTS google_event_id VARCHAR(255)",
        "ALTER TABLE training_portal_class_calendar_links ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE training_portal_class_calendar_links ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "CREATE INDEX IF NOT EXISTS idx_tpccl_session_id ON training_portal_class_calendar_links(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_tpccl_user_id ON training_portal_class_calendar_links(user_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_class_calendar_session_user ON training_portal_class_calendar_links(session_id, user_id)",
    ]
    async with engine.begin() as conn:
        for sql in statements:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass


async def patch_teacher_role_schema():
    """Add teacher to userrole enum and apply training table indexes."""
    
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

