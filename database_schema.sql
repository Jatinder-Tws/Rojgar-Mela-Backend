-- ============================================================================
-- ROJGAR MELA DATABASE ARCHITECTURE & COMPLETE SCHEMA DEFINITION
-- Includes 'CREATE TABLE IF NOT EXISTS', 'CREATE INDEX IF NOT EXISTS', and DDL
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ----------------------------------------------------------------------------
-- Table: assessment_sessions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assessment_sessions (
	id UUID NOT NULL, 
	experience_level VARCHAR(50), 
	domain_interest VARCHAR(100), 
	qa_history JSON NOT NULL, 
	status VARCHAR(20), 
	tokens_utilized INTEGER NOT NULL, 
	cost FLOAT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

-- ----------------------------------------------------------------------------
-- Table: career_enquiries
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS career_enquiries (
	id UUID NOT NULL, 
	full_name VARCHAR(150) NOT NULL, 
	email VARCHAR(150) NOT NULL, 
	phone VARCHAR(20) NOT NULL, 
	qualification VARCHAR(100) NOT NULL,
	domain VARCHAR(150) NOT NULL,
	message TEXT,
	status VARCHAR(40) NOT NULL,
	admin_notes TEXT,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);

-- ----------------------------------------------------------------------------
-- Table: contact_inquiries
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contact_inquiries (
	id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	phone VARCHAR(20), 
	subject VARCHAR(200), 
	message TEXT NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	admin_notes TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

-- ----------------------------------------------------------------------------
-- Table: departments
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
	id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

-- ----------------------------------------------------------------------------
-- Table: job_fairs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_fairs (
	id UUID NOT NULL, 
	slug VARCHAR(100) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	location VARCHAR(200) NOT NULL, 
	banner_image_url TEXT, 
	is_active BOOLEAN NOT NULL, 
	industries JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_job_fairs_slug ON job_fairs (slug);

-- ----------------------------------------------------------------------------
-- Table: master_industries
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS master_industries (
	id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

-- ----------------------------------------------------------------------------
-- Table: master_languages
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS master_languages (
	id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

-- ----------------------------------------------------------------------------
-- Table: master_roles
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS master_roles (
	id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

-- ----------------------------------------------------------------------------
-- Table: master_states
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS master_states (
	id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

-- ----------------------------------------------------------------------------
-- Table: otp_records
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS otp_records (
	id UUID NOT NULL, 
	email VARCHAR(255), 
	phone VARCHAR(20), 
	code VARCHAR(6) NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	used BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_otp_records_phone ON otp_records (phone);

CREATE INDEX IF NOT EXISTS ix_otp_records_email ON otp_records (email);

-- ----------------------------------------------------------------------------
-- Table: roadmap_categories
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roadmap_categories (
	id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	icon VARCHAR(50), 
	description TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

-- ----------------------------------------------------------------------------
-- Table: training_portal_candidate_notifications
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_candidate_notifications (
	id VARCHAR(50) NOT NULL, 
	candidate_email VARCHAR(200) NOT NULL, 
	recipient_role VARCHAR(30) NOT NULL, 
	is_read BOOLEAN NOT NULL, 
	notification_type VARCHAR(50) NOT NULL, 
	title VARCHAR(300) NOT NULL, 
	description TEXT NOT NULL, 
	detail TEXT, 
	event_date VARCHAR(50) NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_training_portal_candidate_notifications_candidate_email ON training_portal_candidate_notifications (candidate_email);

CREATE INDEX IF NOT EXISTS ix_training_portal_candidate_notifications_is_read ON training_portal_candidate_notifications (is_read);

CREATE INDEX IF NOT EXISTS ix_training_portal_candidate_notifications_recipient_role ON training_portal_candidate_notifications (recipient_role);

-- ----------------------------------------------------------------------------
-- Table: training_portal_course_categories
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_course_categories (
	id VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	sort_order INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_training_portal_course_categories_name ON training_portal_course_categories (name);

-- ----------------------------------------------------------------------------
-- Table: training_portal_payment_settings
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_payment_settings (
	id VARCHAR(50) NOT NULL, 
	upi BOOLEAN NOT NULL, 
	card BOOLEAN NOT NULL, 
	emi BOOLEAN NOT NULL, 
	offline BOOLEAN NOT NULL, 
	email BOOLEAN NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

-- ----------------------------------------------------------------------------
-- Table: users
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
	id UUID NOT NULL, 
	first_name VARCHAR(50), 
	last_name VARCHAR(50), 
	email VARCHAR(255), 
	phone VARCHAR(15), 
	hashed_password VARCHAR(255), 
	profile_pic_url TEXT, 
	is_super_admin BOOLEAN NOT NULL, 
	is_verified BOOLEAN NOT NULL, 
	onboarding_complete BOOLEAN NOT NULL, 
	is_assessment_done BOOLEAN NOT NULL, 
	totp_secret VARCHAR(32), 
	totp_enabled BOOLEAN NOT NULL, 
	is_first_login BOOLEAN, 
	role userrole, 
	industry VARCHAR(100), 
	job_role VARCHAR(100), 
	job_type jobtype, 
	salary_range VARCHAR(50), 
	experience VARCHAR(50), 
	auto_apply_enabled BOOLEAN NOT NULL, 
	company_type companytype, 
	company_name VARCHAR(200), 
	company_location VARCHAR(200), 
	company_address VARCHAR(500), 
	company_size VARCHAR(50), 
	father_or_mother_name VARCHAR(200), 
	gender VARCHAR(50), 
	address TEXT, 
	highest_qualification VARCHAR(200), 
	stream_specialization VARCHAR(200), 
	college_institute_name VARCHAR(255), 
	preferred_job_sector VARCHAR(200), 
	job_roles_offering TEXT, 
	specific_requirements TEXT, 
	preferred_locations JSON, 
	welcome_email_status VARCHAR(20), 
	welcome_email_error TEXT, 
	registration_ip VARCHAR(45), 
	profile_embedding VECTOR(3072), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_users_created_at ON users (created_at);

CREATE INDEX IF NOT EXISTS ix_users_experience ON users (experience);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);

-- ----------------------------------------------------------------------------
-- Table: ai_coach_sessions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_coach_sessions (
	id UUID NOT NULL, 
	seeker_id UUID NOT NULL, 
	target_role VARCHAR(100) NOT NULL, 
	experience_level VARCHAR(50) NOT NULL, 
	focus_area VARCHAR(50) NOT NULL, 
	chat_history JSON NOT NULL, 
	status VARCHAR(20), 
	overall_score INTEGER, 
	communication_score INTEGER, 
	content_score INTEGER, 
	general_feedback TEXT, 
	strengths JSON, 
	gaps JSON, 
	improvement_steps JSON, 
	video_feedback JSON, 
	total_tokens INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(seeker_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_ai_coach_sessions_seeker_id ON ai_coach_sessions (seeker_id);

-- ----------------------------------------------------------------------------
-- Table: assessment_results
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assessment_results (
	id UUID NOT NULL, 
	session_id UUID, 
	user_id UUID, 
	personality_type VARCHAR(100), 
	personality_score INTEGER, 
	iq_score INTEGER, 
	aptitude_score INTEGER, 
	reasoning_score INTEGER, 
	emotional_intelligence_score INTEGER, 
	recommended_domains JSON NOT NULL, 
	detailed_evaluation VARCHAR, 
	tokens_utilized INTEGER NOT NULL, 
	cost FLOAT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (session_id), 
	FOREIGN KEY(session_id) REFERENCES assessment_sessions (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_assessment_results_user_id ON assessment_results (user_id);

-- ----------------------------------------------------------------------------
-- Table: attendance
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	date DATE NOT NULL, 
	attendance_status VARCHAR NOT NULL, 
	marked_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Table: company_internships
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS company_internships (
	id VARCHAR(50) NOT NULL, 
	provider_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	thumbnail_url VARCHAR(500), 
	brochure_url VARCHAR(500), 
	is_stipend BOOLEAN NOT NULL, 
	stipend_amount VARCHAR(100), 
	duration INTEGER NOT NULL, 
	duration_unit VARCHAR(50) NOT NULL, 
	state VARCHAR(100), 
	city VARCHAR(100), 
	address TEXT, 
	apply_by DATE, 
	start_date VARCHAR(200), 
	company_name VARCHAR(200) NOT NULL, 
	who_can_apply TEXT, 
	skills_required JSON, 
	perks JSON, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(provider_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_company_internships_is_active ON company_internships (is_active);

CREATE INDEX IF NOT EXISTS ix_company_internships_provider_id ON company_internships (provider_id);

-- ----------------------------------------------------------------------------
-- Table: department_jobs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS department_jobs (
	id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	department_id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Table: email_templates
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS email_templates (
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	slug VARCHAR(200) NOT NULL, 
	description TEXT, 
	subject VARCHAR(500) NOT NULL, 
	html_body TEXT NOT NULL, 
	design_config JSON DEFAULT '{}'::json NOT NULL, 
	category emailtemplatecategory DEFAULT 'custom' NOT NULL, 
	placeholders JSON, 
	is_active BOOLEAN DEFAULT true NOT NULL, 
	is_system BOOLEAN DEFAULT false NOT NULL, 
	created_by_id UUID, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_email_templates_slug ON email_templates (slug);

-- ----------------------------------------------------------------------------
-- Table: google_calendar_tokens
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS google_calendar_tokens (
	id VARCHAR(50) NOT NULL, 
	user_id UUID NOT NULL, 
	google_email VARCHAR(255), 
	access_token TEXT, 
	refresh_token TEXT, 
	token_uri VARCHAR(255) NOT NULL, 
	scopes TEXT, 
	expiry TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_google_calendar_tokens_user_id ON google_calendar_tokens (user_id);

-- ----------------------------------------------------------------------------
-- Table: imported_user_passwords
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS imported_user_passwords (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	email VARCHAR(255), 
	plain_password VARCHAR(255) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_imported_user_passwords_email ON imported_user_passwords (email);

-- ----------------------------------------------------------------------------
-- Table: job_fair_companies
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_fair_companies (
	id UUID NOT NULL, 
	job_fair_id UUID NOT NULL, 
	provider_id UUID NOT NULL, 
	department VARCHAR(100), 
	sector VARCHAR(100), 
	vacancy VARCHAR(100), 
	registered_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	company_name VARCHAR(200), 
	email VARCHAR(200), 
	phone VARCHAR(50), 
	website VARCHAR(200), 
	company_size VARCHAR(100), 
	company_address TEXT, 
	contact_person_name VARCHAR(200), 
	contact_person_designation VARCHAR(200), 
	contact_person_phone VARCHAR(50), 
	openings JSON, 
	logo_url VARCHAR(500), 
	state VARCHAR(100), 
	city VARCHAR(100), 
	PRIMARY KEY (id), 
	FOREIGN KEY(job_fair_id) REFERENCES job_fairs (id) ON DELETE CASCADE, 
	FOREIGN KEY(provider_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_job_fair_companies_provider_id ON job_fair_companies (provider_id);

CREATE INDEX IF NOT EXISTS ix_job_fair_companies_job_fair_id ON job_fair_companies (job_fair_id);

-- ----------------------------------------------------------------------------
-- Table: job_fair_seekers
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_fair_seekers (
	id UUID NOT NULL, 
	job_fair_id UUID NOT NULL, 
	seeker_id UUID NOT NULL, 
	is_attending BOOLEAN NOT NULL, 
	registered_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(job_fair_id) REFERENCES job_fairs (id) ON DELETE CASCADE, 
	FOREIGN KEY(seeker_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_job_fair_seekers_seeker_id ON job_fair_seekers (seeker_id);

CREATE INDEX IF NOT EXISTS ix_job_fair_seekers_job_fair_id ON job_fair_seekers (job_fair_id);

-- ----------------------------------------------------------------------------
-- Table: job_postings
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_postings (
	id UUID NOT NULL, 
	provider_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	required_skills JSON, 
	experience_required VARCHAR(100), 
	job_type jobtype, 
	salary_range VARCHAR(100), 
	industry VARCHAR(100), 
	posted_by_name VARCHAR(200), 
	location VARCHAR(200), 
	is_active BOOLEAN NOT NULL, 
	post_count INTEGER NOT NULL, 
	ai_interview_enabled BOOLEAN NOT NULL, 
	selection_threshold INTEGER NOT NULL, 
	shift VARCHAR(20), 
	perks JSON, 
	employment_type VARCHAR(20), 
	embedding VECTOR(3072), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(provider_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_job_postings_created_at ON job_postings (created_at);

CREATE INDEX IF NOT EXISTS ix_job_postings_is_active ON job_postings (is_active);

CREATE INDEX IF NOT EXISTS ix_job_postings_provider_id ON job_postings (provider_id);
CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone);
CREATE INDEX IF NOT EXISTS ix_applications_status ON applications (status);
CREATE INDEX IF NOT EXISTS ix_external_candidates_status ON external_candidates (status);
CREATE INDEX IF NOT EXISTS ix_external_candidates_is_matched ON external_candidates (is_matched);
CREATE INDEX IF NOT EXISTS ix_job_postings_embedding_hnsw ON job_postings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS ix_resumes_embedding_hnsw ON resumes USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS ix_external_candidates_embedding_hnsw ON external_candidates USING hnsw (embedding vector_cosine_ops);

-- ----------------------------------------------------------------------------
-- Table: master_cities
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS master_cities (
	id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	state_id UUID, 
	PRIMARY KEY (id), 
	FOREIGN KEY(state_id) REFERENCES master_states (id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Table: notifications
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	type notificationtype NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	message TEXT NOT NULL, 
	is_read BOOLEAN NOT NULL, 
	related_job_id UUID, 
	related_user_id UUID, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id);

-- ----------------------------------------------------------------------------
-- Table: platform_feedback
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS platform_feedback (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	rating INTEGER NOT NULL, 
	category feedbackcategory NOT NULL, 
	comment TEXT NOT NULL, 
	page_context VARCHAR(100), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_platform_feedback_user_id ON platform_feedback (user_id);

-- ----------------------------------------------------------------------------
-- Table: portfolios
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolios (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	headline VARCHAR(200), 
	bio TEXT, 
	date_of_birth VARCHAR(20), 
	gender VARCHAR(20), 
	city VARCHAR(100), 
	state VARCHAR(100), 
	linkedin_url VARCHAR(500), 
	github_url VARCHAR(500), 
	website_url VARCHAR(500), 
	total_experience_years FLOAT, 
	current_company VARCHAR(200), 
	"current_role" VARCHAR(200), 
	skills JSON, 
	work_experiences JSON, 
	education JSON, 
	certifications JSON, 
	languages JSON, 
	projects JSON, 
	intro_video_path VARCHAR(500), 
	intro_video_filename VARCHAR(255), 
	intro_audio_path VARCHAR(500), 
	intro_audio_filename VARCHAR(255), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_portfolios_user_id ON portfolios (user_id);

-- ----------------------------------------------------------------------------
-- Table: provider_interview_settings
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provider_interview_settings (
	provider_id UUID NOT NULL, 
	auto_schedule_enabled BOOLEAN NOT NULL, 
	slot_duration_minutes INTEGER NOT NULL, 
	buffer_minutes INTEGER NOT NULL, 
	timezone VARCHAR(64) NOT NULL, 
	lookahead_days INTEGER NOT NULL, 
	min_notice_hours INTEGER NOT NULL, 
	default_title VARCHAR(200) NOT NULL, 
	default_interviewer_name VARCHAR(200), 
	default_agenda TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (provider_id), 
	FOREIGN KEY(provider_id) REFERENCES users (id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Table: resumes
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resumes (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	file_path VARCHAR(500) NOT NULL, 
	file_size_bytes INTEGER, 
	source VARCHAR(20) NOT NULL, 
	parsed_text TEXT, 
	parsed_json JSON, 
	embedding VECTOR(3072), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_resumes_user_id ON resumes (user_id);

-- ----------------------------------------------------------------------------
-- Table: roadmap_roles
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roadmap_roles (
	id UUID NOT NULL, 
	category_id UUID NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	description TEXT, 
	level VARCHAR(50), 
	growth VARCHAR(20), 
	salary_range VARCHAR(50), 
	skills VARCHAR[], 
	PRIMARY KEY (id), 
	FOREIGN KEY(category_id) REFERENCES roadmap_categories (id)
);

-- ----------------------------------------------------------------------------
-- Table: roadmaps
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roadmaps (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	target_role VARCHAR(100) NOT NULL, 
	current_level VARCHAR(50) NOT NULL, 
	target_level VARCHAR(50) NOT NULL, 
	skills_to_develop VARCHAR[], 
	current_skills VARCHAR[], 
	estimated_duration VARCHAR(50), 
	market_based_salary JSON, 
	status VARCHAR(20) NOT NULL, 
	ai_prompt_version VARCHAR(20) NOT NULL, 
	generation_preferences JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_roadmaps_user_id ON roadmaps (user_id);

-- ----------------------------------------------------------------------------
-- Table: support_tickets
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS support_tickets (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	ticket_number VARCHAR(32) NOT NULL, 
	category ticketcategory NOT NULL, 
	subject VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	status ticketstatus NOT NULL, 
	priority ticketpriority NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	resolved_at TIMESTAMP WITHOUT TIME ZONE, 
	bot_handled BOOLEAN NOT NULL, 
	escalated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_support_tickets_ticket_number ON support_tickets (ticket_number);

CREATE INDEX IF NOT EXISTS ix_support_tickets_user_id ON support_tickets (user_id);

CREATE INDEX IF NOT EXISTS ix_support_tickets_status ON support_tickets (status);

-- ----------------------------------------------------------------------------
-- Table: training_courses
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_courses (
	id VARCHAR(50) NOT NULL, 
	provider_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	thumbnail_url VARCHAR(500), 
	brochure_url VARCHAR(500), 
	is_paid BOOLEAN NOT NULL, 
	price VARCHAR(100), 
	duration INTEGER NOT NULL, 
	duration_unit VARCHAR(50) NOT NULL, 
	skills_learned JSON, 
	has_certificate BOOLEAN NOT NULL, 
	company_name VARCHAR(200) NOT NULL, 
	state VARCHAR(100), 
	city VARCHAR(100), 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(provider_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_training_courses_provider_id ON training_courses (provider_id);

CREATE INDEX IF NOT EXISTS ix_training_courses_is_active ON training_courses (is_active);

-- ----------------------------------------------------------------------------
-- Table: training_portal_courses
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_courses (
	id VARCHAR(50) NOT NULL, 
	created_by_id UUID, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	category VARCHAR(100) NOT NULL, 
	duration VARCHAR(50) NOT NULL, 
	delivery_mode VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	skill_level VARCHAR(20) NOT NULL, 
	fee FLOAT NOT NULL, 
	emi_fee FLOAT, 
	thumbnail_url VARCHAR(500), 
	prerequisites TEXT, 
	is_featured BOOLEAN, 
	key_highlights JSON NOT NULL, 
	curriculum JSON NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_training_portal_courses_category ON training_portal_courses (category);

CREATE INDEX IF NOT EXISTS ix_training_portal_courses_created_by_id ON training_portal_courses (created_by_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_courses_status ON training_portal_courses (status);

-- ----------------------------------------------------------------------------
-- Table: training_portal_internships
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_internships (
	id VARCHAR(50) NOT NULL, 
	created_by_id UUID, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	duration VARCHAR(50) NOT NULL, 
	is_paid BOOLEAN NOT NULL, 
	fee FLOAT NOT NULL, 
	start_date VARCHAR(50) NOT NULL, 
	end_date VARCHAR(50) NOT NULL, 
	venue VARCHAR(300) NOT NULL, 
	max_seats INTEGER NOT NULL, 
	seats_filled INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	laptop_required BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_training_portal_internships_created_by_id ON training_portal_internships (created_by_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_internships_status ON training_portal_internships (status);

-- ----------------------------------------------------------------------------
-- Table: training_portal_leave_requests
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_leave_requests (
	id VARCHAR(50) NOT NULL, 
	requester_type VARCHAR(20) NOT NULL, 
	candidate_email VARCHAR(200), 
	candidate_name VARCHAR(200), 
	teacher_email VARCHAR(200), 
	teacher_name VARCHAR(200), 
	session_id VARCHAR(50), 
	date VARCHAR(50) NOT NULL, 
	batch_id VARCHAR(50), 
	batch_name VARCHAR(200), 
	reason TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	reviewed_by_id UUID, 
	reviewed_by_role VARCHAR(20), 
	review_note TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reviewed_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_training_portal_leave_requests_requester_type ON training_portal_leave_requests (requester_type);

CREATE INDEX IF NOT EXISTS ix_training_portal_leave_requests_status ON training_portal_leave_requests (status);

CREATE INDEX IF NOT EXISTS ix_training_portal_leave_requests_date ON training_portal_leave_requests (date);

CREATE INDEX IF NOT EXISTS ix_training_portal_leave_requests_candidate_email ON training_portal_leave_requests (candidate_email);

CREATE INDEX IF NOT EXISTS ix_training_portal_leave_requests_teacher_email ON training_portal_leave_requests (teacher_email);

CREATE INDEX IF NOT EXISTS ix_training_portal_leave_requests_batch_id ON training_portal_leave_requests (batch_id);

-- ----------------------------------------------------------------------------
-- Table: training_portal_teachers
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_teachers (
	id VARCHAR(50) NOT NULL, 
	created_by_id UUID, 
	user_id UUID, 
	name VARCHAR(200) NOT NULL, 
	email VARCHAR(200) NOT NULL, 
	phone VARCHAR(50) NOT NULL, 
	bio TEXT NOT NULL, 
	subjects JSON NOT NULL, 
	rating FLOAT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	avatar VARCHAR(500), 
	login_username VARCHAR(100) NOT NULL, 
	login_password VARCHAR(200) NOT NULL, 
	login_active BOOLEAN NOT NULL, 
	last_login_at VARCHAR(50), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_training_portal_teachers_user_id ON training_portal_teachers (user_id);

CREATE UNIQUE INDEX IF NOT EXISTS ix_training_portal_teachers_login_username ON training_portal_teachers (login_username);

CREATE INDEX IF NOT EXISTS ix_training_portal_teachers_created_by_id ON training_portal_teachers (created_by_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_teachers_status ON training_portal_teachers (status);

CREATE UNIQUE INDEX IF NOT EXISTS ix_training_portal_teachers_email ON training_portal_teachers (email);

-- ----------------------------------------------------------------------------
-- Table: applications
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS applications (
	id UUID NOT NULL, 
	seeker_id UUID, 
	job_id UUID NOT NULL, 
	candidate_name VARCHAR(200), 
	candidate_email VARCHAR(200), 
	candidate_phone VARCHAR(20), 
	candidate_experience VARCHAR(100), 
	candidate_resume_url TEXT, 
	status applicationstatus NOT NULL, 
	rejection_reason TEXT, 
	ai_feedback JSON, 
	applied_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(seeker_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(job_id) REFERENCES job_postings (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_applications_seeker_id ON applications (seeker_id);

CREATE INDEX IF NOT EXISTS ix_applications_job_id ON applications (job_id);

CREATE INDEX IF NOT EXISTS ix_applications_applied_at ON applications (applied_at);

-- ----------------------------------------------------------------------------
-- Table: company_internship_applications
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS company_internship_applications (
	id VARCHAR(50) NOT NULL, 
	internship_id VARCHAR(50) NOT NULL, 
	seeker_id UUID NOT NULL, 
	why_join TEXT NOT NULL, 
	career_goals TEXT NOT NULL, 
	why_consider TEXT NOT NULL, 
	resume_url VARCHAR(500) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_internship_seeker_app UNIQUE (internship_id, seeker_id), 
	FOREIGN KEY(internship_id) REFERENCES company_internships (id) ON DELETE CASCADE, 
	FOREIGN KEY(seeker_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_company_internship_applications_internship_id ON company_internship_applications (internship_id);

CREATE INDEX IF NOT EXISTS ix_company_internship_applications_seeker_id ON company_internship_applications (seeker_id);

-- ----------------------------------------------------------------------------
-- Table: email_campaigns
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS email_campaigns (
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	template_id UUID NOT NULL, 
	status campaignstatus NOT NULL, 
	audience_type audiencetype NOT NULL, 
	audience_filter JSON, 
	total_recipients INTEGER NOT NULL, 
	sent_count INTEGER NOT NULL, 
	failed_count INTEGER NOT NULL, 
	job_id VARCHAR(36), 
	created_by UUID, 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(template_id) REFERENCES email_templates (id) ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Table: external_candidates
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS external_candidates (
	id UUID NOT NULL, 
	job_id UUID, 
	full_name VARCHAR(200) NOT NULL, 
	email VARCHAR(200) NOT NULL, 
	phone VARCHAR(20) NOT NULL, 
	state VARCHAR(100), 
	city VARCHAR(100), 
	date_of_birth VARCHAR(100), 
	gender VARCHAR(100), 
	sub_role VARCHAR(100), 
	industries JSON, 
	available_shift VARCHAR(50), 
	total_experience VARCHAR(100), 
	current_ctc VARCHAR(50), 
	current_designation VARCHAR(100), 
	year_of_passing VARCHAR(50), 
	skills TEXT, 
	source VARCHAR(100), 
	resume_url TEXT, 
	salary_slip_url TEXT, 
	experience_letter_url TEXT, 
	profile_picture_url TEXT, 
	status VARCHAR(50), 
	is_matched BOOLEAN DEFAULT 'false' NOT NULL, 
	applied_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	embedding VECTOR(3072), 
	PRIMARY KEY (id), 
	FOREIGN KEY(job_id) REFERENCES job_postings (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_external_candidates_job_id ON external_candidates (job_id);

CREATE INDEX IF NOT EXISTS ix_external_candidates_email ON external_candidates (email);

-- ----------------------------------------------------------------------------
-- Table: matches
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS matches (
	id UUID NOT NULL, 
	seeker_id UUID NOT NULL, 
	job_id UUID NOT NULL, 
	score FLOAT NOT NULL, 
	highlights JSON, 
	gaps JSON, 
	fit_reason VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(seeker_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(job_id) REFERENCES job_postings (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_matches_job_id ON matches (job_id);

CREATE INDEX IF NOT EXISTS ix_matches_score ON matches (score);

CREATE INDEX IF NOT EXISTS ix_matches_created_at ON matches (created_at);

CREATE INDEX IF NOT EXISTS ix_matches_seeker_id ON matches (seeker_id);

-- ----------------------------------------------------------------------------
-- Table: milestones
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS milestones (
	id UUID NOT NULL, 
	roadmap_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	stage_title VARCHAR(100), 
	stage_order INTEGER, 
	order_num INTEGER NOT NULL, 
	skills VARCHAR[], 
	estimated_time VARCHAR(50), 
	difficulty difficultylevel, 
	status milestonestatus NOT NULL, 
	dependencies UUID[], 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(roadmap_id) REFERENCES roadmaps (id)
);

CREATE INDEX IF NOT EXISTS ix_milestones_roadmap_id ON milestones (roadmap_id);

-- ----------------------------------------------------------------------------
-- Table: provider_availability_windows
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provider_availability_windows (
	id UUID NOT NULL, 
	provider_id UUID NOT NULL, 
	day_of_week SMALLINT NOT NULL, 
	start_time TIME WITHOUT TIME ZONE NOT NULL, 
	end_time TIME WITHOUT TIME ZONE NOT NULL, 
	start_period VARCHAR(2), 
	end_period VARCHAR(2), 
	PRIMARY KEY (id), 
	FOREIGN KEY(provider_id) REFERENCES provider_interview_settings (provider_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_provider_availability_windows_provider_id ON provider_availability_windows (provider_id);

-- ----------------------------------------------------------------------------
-- Table: saved_jobs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS saved_jobs (
	id UUID NOT NULL, 
	seeker_id UUID NOT NULL, 
	job_id UUID NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_saved_jobs_seeker_job UNIQUE (seeker_id, job_id), 
	FOREIGN KEY(seeker_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(job_id) REFERENCES job_postings (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_saved_jobs_seeker_id ON saved_jobs (seeker_id);

CREATE INDEX IF NOT EXISTS ix_saved_jobs_job_id ON saved_jobs (job_id);

CREATE INDEX IF NOT EXISTS ix_saved_jobs_created_at ON saved_jobs (created_at);

-- ----------------------------------------------------------------------------
-- Table: ticket_messages
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ticket_messages (
	id UUID NOT NULL, 
	ticket_id UUID NOT NULL, 
	author_id UUID, 
	body TEXT NOT NULL, 
	is_staff_reply BOOLEAN NOT NULL, 
	is_bot_reply BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES support_tickets (id) ON DELETE CASCADE, 
	FOREIGN KEY(author_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_ticket_messages_ticket_id ON ticket_messages (ticket_id);

-- ----------------------------------------------------------------------------
-- Table: training_course_applications
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_course_applications (
	id VARCHAR(50) NOT NULL, 
	course_id VARCHAR(50) NOT NULL, 
	seeker_id UUID NOT NULL, 
	first_name VARCHAR(100) NOT NULL, 
	last_name VARCHAR(100) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	phone VARCHAR(100) NOT NULL, 
	location VARCHAR(200) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_course_seeker_app UNIQUE (course_id, seeker_id), 
	FOREIGN KEY(course_id) REFERENCES training_courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(seeker_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_training_course_applications_seeker_id ON training_course_applications (seeker_id);

CREATE INDEX IF NOT EXISTS ix_training_course_applications_course_id ON training_course_applications (course_id);

-- ----------------------------------------------------------------------------
-- Table: training_modules
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_modules (
	id VARCHAR(50) NOT NULL, 
	course_id VARCHAR(50) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	order_index INTEGER NOT NULL, 
	estimated_hours FLOAT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES training_courses (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_training_modules_course_id ON training_modules (course_id);

-- ----------------------------------------------------------------------------
-- Table: training_portal_batches
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_batches (
	id VARCHAR(50) NOT NULL, 
	course_id VARCHAR(50) NOT NULL, 
	batch_name VARCHAR(200) NOT NULL, 
	instructor_id VARCHAR(50), 
	instructor_name VARCHAR(200) NOT NULL, 
	start_date VARCHAR(50) NOT NULL, 
	end_date VARCHAR(50) NOT NULL, 
	days JSON NOT NULL, 
	time_slot VARCHAR(100) NOT NULL, 
	venue VARCHAR(300) NOT NULL, 
	max_seats INTEGER NOT NULL, 
	delivery_mode VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	covered_topics JSON NOT NULL, 
	created_by_id UUID, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES training_portal_courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_training_portal_batches_course_id ON training_portal_batches (course_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_batches_status ON training_portal_batches (status);

-- ----------------------------------------------------------------------------
-- Table: training_portal_enrollment_requests
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_enrollment_requests (
	id VARCHAR(50) NOT NULL, 
	candidate_user_id UUID, 
	candidate_name VARCHAR(200) NOT NULL, 
	candidate_email VARCHAR(200) NOT NULL, 
	candidate_phone VARCHAR(50), 
	gender VARCHAR(30), 
	qualification VARCHAR(200), 
	address TEXT, 
	course_id VARCHAR(50) NOT NULL, 
	course_title VARCHAR(300) NOT NULL, 
	preferred_batch_id VARCHAR(50), 
	payment_preference VARCHAR(30) NOT NULL, 
	total_fee FLOAT NOT NULL, 
	laptop_confirmed BOOLEAN NOT NULL, 
	attendance_policy_agreed BOOLEAN NOT NULL, 
	certification_policy_agreed BOOLEAN NOT NULL, 
	notes JSON NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	resolved_by_id UUID, 
	resolved_at TIMESTAMP WITHOUT TIME ZONE, 
	enrollment_id VARCHAR(50), 
	requested_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(candidate_user_id) REFERENCES users (id) ON DELETE SET NULL, 
	FOREIGN KEY(course_id) REFERENCES training_portal_courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(resolved_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_training_portal_enrollment_requests_status ON training_portal_enrollment_requests (status);

CREATE INDEX IF NOT EXISTS ix_training_portal_enrollment_requests_candidate_email ON training_portal_enrollment_requests (candidate_email);

CREATE INDEX IF NOT EXISTS ix_training_portal_enrollment_requests_candidate_user_id ON training_portal_enrollment_requests (candidate_user_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_enrollment_requests_course_id ON training_portal_enrollment_requests (course_id);

-- ----------------------------------------------------------------------------
-- Table: ai_interview_sessions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_interview_sessions (
	id UUID NOT NULL, 
	application_id UUID NOT NULL, 
	seeker_id UUID NOT NULL, 
	job_id UUID NOT NULL, 
	chat_history JSON NOT NULL, 
	status VARCHAR(20), 
	score INTEGER, 
	feedback TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE, 
	FOREIGN KEY(seeker_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(job_id) REFERENCES job_postings (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_ai_interview_sessions_application_id ON ai_interview_sessions (application_id);

CREATE INDEX IF NOT EXISTS ix_ai_interview_sessions_seeker_id ON ai_interview_sessions (seeker_id);

CREATE INDEX IF NOT EXISTS ix_ai_interview_sessions_job_id ON ai_interview_sessions (job_id);

-- ----------------------------------------------------------------------------
-- Table: email_campaign_recipients
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS email_campaign_recipients (
	id UUID NOT NULL, 
	campaign_id UUID NOT NULL, 
	user_id UUID, 
	email VARCHAR(255) NOT NULL, 
	recipient_name VARCHAR(200), 
	status recipientstatus NOT NULL, 
	error TEXT, 
	sent_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(campaign_id) REFERENCES email_campaigns (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_email_campaign_recipients_user_id ON email_campaign_recipients (user_id);

CREATE INDEX IF NOT EXISTS ix_email_campaign_recipients_campaign_id ON email_campaign_recipients (campaign_id);

-- ----------------------------------------------------------------------------
-- Table: external_candidate_matches
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS external_candidate_matches (
	id UUID NOT NULL, 
	candidate_id UUID NOT NULL, 
	job_id UUID NOT NULL, 
	score FLOAT NOT NULL, 
	highlights JSON, 
	gaps JSON, 
	fit_reason VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(candidate_id) REFERENCES external_candidates (id) ON DELETE CASCADE, 
	FOREIGN KEY(job_id) REFERENCES job_postings (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_external_candidate_matches_job_id ON external_candidate_matches (job_id);

CREATE INDEX IF NOT EXISTS ix_external_candidate_matches_candidate_id ON external_candidate_matches (candidate_id);

-- ----------------------------------------------------------------------------
-- Table: interviews
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interviews (
	id UUID NOT NULL, 
	seeker_id UUID NOT NULL, 
	provider_id UUID NOT NULL, 
	job_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	agenda TEXT, 
	interview_type interviewtype NOT NULL, 
	meeting_link TEXT, 
	location TEXT, 
	status interviewstatus NOT NULL, 
	scheduled_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	scheduled_period VARCHAR(2), 
	interviewer_name VARCHAR(200) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	application_id UUID, 
	source interviewsource NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(seeker_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(provider_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(job_id) REFERENCES job_postings (id) ON DELETE CASCADE, 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_interviews_seeker_id ON interviews (seeker_id);

CREATE INDEX IF NOT EXISTS ix_interviews_job_id ON interviews (job_id);

CREATE INDEX IF NOT EXISTS ix_interviews_scheduled_at ON interviews (scheduled_at);

CREATE INDEX IF NOT EXISTS ix_interviews_provider_id ON interviews (provider_id);

CREATE INDEX IF NOT EXISTS ix_interviews_application_id ON interviews (application_id);

-- ----------------------------------------------------------------------------
-- Table: resources
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resources (
	id UUID NOT NULL, 
	milestone_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	type resourcetype NOT NULL, 
	url TEXT, 
	platform VARCHAR(100), 
	duration VARCHAR(50), 
	difficulty difficultylevel, 
	description TEXT, 
	is_free BOOLEAN NOT NULL, 
	rating FLOAT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(milestone_id) REFERENCES milestones (id)
);

CREATE INDEX IF NOT EXISTS ix_resources_milestone_id ON resources (milestone_id);

-- ----------------------------------------------------------------------------
-- Table: training_module_topics
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_module_topics (
	id VARCHAR(50) NOT NULL, 
	module_id VARCHAR(50) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	order_index INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(module_id) REFERENCES training_modules (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_training_module_topics_module_id ON training_module_topics (module_id);

-- ----------------------------------------------------------------------------
-- Table: training_portal_class_sessions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_class_sessions (
	id VARCHAR(50) NOT NULL, 
	batch_id VARCHAR(50), 
	item_id VARCHAR(50) NOT NULL, 
	title VARCHAR(300) NOT NULL, 
	instructor_name VARCHAR(200) NOT NULL, 
	date VARCHAR(50) NOT NULL, 
	start_time VARCHAR(50) NOT NULL, 
	end_time VARCHAR(50) NOT NULL, 
	days JSON NOT NULL, 
	venue VARCHAR(300), 
	note TEXT, 
	schedule_type VARCHAR(20) NOT NULL, 
	postponed BOOLEAN NOT NULL, 
	teacher_unavailable BOOLEAN NOT NULL, 
	live_status VARCHAR(20) NOT NULL, 
	live_occurrence_date VARCHAR(50), 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	ended_at TIMESTAMP WITHOUT TIME ZONE, 
	session_report TEXT, 
	covered_topic_ids JSON NOT NULL, 
	attachment_url VARCHAR(500), 
	attachment_filename VARCHAR(255), 
	reminder_sent BOOLEAN NOT NULL, 
	reminder_15_sent BOOLEAN NOT NULL, 
	late_start_reason TEXT, 
	early_end_reason TEXT, 
	attendance_marked BOOLEAN NOT NULL, 
	end_reminder_sent BOOLEAN NOT NULL, 
	created_by_id UUID, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(batch_id) REFERENCES training_portal_batches (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_training_portal_class_sessions_item_id ON training_portal_class_sessions (item_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_class_sessions_live_status ON training_portal_class_sessions (live_status);

CREATE INDEX IF NOT EXISTS ix_training_portal_class_sessions_batch_id ON training_portal_class_sessions (batch_id);

-- ----------------------------------------------------------------------------
-- Table: training_portal_enrollments
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_enrollments (
	id VARCHAR(50) NOT NULL, 
	candidate_user_id UUID, 
	candidate_name VARCHAR(200) NOT NULL, 
	candidate_email VARCHAR(200) NOT NULL, 
	candidate_phone VARCHAR(50), 
	enrollment_type VARCHAR(20) NOT NULL, 
	item_id VARCHAR(50) NOT NULL, 
	batch_id VARCHAR(50), 
	title VARCHAR(300) NOT NULL, 
	batch_name VARCHAR(200), 
	enrollment_date VARCHAR(50) NOT NULL, 
	payment_type VARCHAR(30) NOT NULL, 
	payment_status VARCHAR(30) NOT NULL, 
	payment_mode VARCHAR(30), 
	total_fee FLOAT NOT NULL, 
	paid_amount FLOAT NOT NULL, 
	balance_due FLOAT NOT NULL, 
	installments JSON NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	attendance_percentage INTEGER NOT NULL, 
	completion_percentage INTEGER NOT NULL, 
	is_certificate_issued BOOLEAN NOT NULL, 
	certificate_id VARCHAR(100), 
	certificate_status VARCHAR(30), 
	certificate_reason TEXT, 
	voter_card_url VARCHAR(500), 
	laptop_confirmed BOOLEAN NOT NULL, 
	notes TEXT,
	preferred_batch_id VARCHAR(50),
	token_amount FLOAT NOT NULL DEFAULT 2000.0,
	token_paid_at TIMESTAMP WITHOUT TIME ZONE,
	venue_visit_deadline TIMESTAMP WITHOUT TIME ZONE,
	token_expired BOOLEAN NOT NULL DEFAULT FALSE,
	refunded_at TIMESTAMP WITHOUT TIME ZONE,
	refund_reason TEXT,
	refunded_by_id UUID,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(candidate_user_id) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(batch_id) REFERENCES training_portal_batches (id) ON DELETE SET NULL,
	FOREIGN KEY(preferred_batch_id) REFERENCES training_portal_batches (id) ON DELETE SET NULL,
	FOREIGN KEY(refunded_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_training_portal_enrollments_item_id ON training_portal_enrollments (item_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_enrollments_candidate_user_id ON training_portal_enrollments (candidate_user_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_enrollments_candidate_email ON training_portal_enrollments (candidate_email);

CREATE INDEX IF NOT EXISTS ix_training_portal_enrollments_status ON training_portal_enrollments (status);

CREATE INDEX IF NOT EXISTS ix_training_portal_enrollments_batch_id ON training_portal_enrollments (batch_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_enrollments_payment_status ON training_portal_enrollments (payment_status);

CREATE INDEX IF NOT EXISTS ix_training_portal_enrollments_preferred_batch_id ON training_portal_enrollments (preferred_batch_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_enrollments_enrollment_type ON training_portal_enrollments (enrollment_type);

CREATE INDEX IF NOT EXISTS idx_tpe_token_expired ON training_portal_enrollments (token_expired);

-- ----------------------------------------------------------------------------
-- Table: training_portal_attendance_records
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_attendance_records (
	id VARCHAR(50) NOT NULL, 
	class_session_id VARCHAR(50) NOT NULL, 
	enrollment_id VARCHAR(50) NOT NULL, 
	occurrence_date VARCHAR(50) NOT NULL, 
	batch_id VARCHAR(50), 
	candidate_email VARCHAR(200) NOT NULL, 
	candidate_name VARCHAR(200) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	marked_by_id UUID, 
	marked_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_session_enrollment_occurrence_attendance UNIQUE (class_session_id, enrollment_id, occurrence_date), 
	FOREIGN KEY(class_session_id) REFERENCES training_portal_class_sessions (id) ON DELETE CASCADE, 
	FOREIGN KEY(enrollment_id) REFERENCES training_portal_enrollments (id) ON DELETE CASCADE, 
	FOREIGN KEY(marked_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_training_portal_attendance_records_candidate_email ON training_portal_attendance_records (candidate_email);

CREATE INDEX IF NOT EXISTS ix_training_portal_attendance_records_batch_id ON training_portal_attendance_records (batch_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_attendance_records_enrollment_id ON training_portal_attendance_records (enrollment_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_attendance_records_class_session_id ON training_portal_attendance_records (class_session_id);

-- ----------------------------------------------------------------------------
-- Table: training_portal_behavior_reports
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_behavior_reports (
	id VARCHAR(50) NOT NULL, 
	enrollment_id VARCHAR(50), 
	candidate_name VARCHAR(200) NOT NULL, 
	candidate_email VARCHAR(200) NOT NULL, 
	batch_id VARCHAR(50), 
	batch_name VARCHAR(200), 
	instructor_id VARCHAR(50), 
	instructor_name VARCHAR(200) NOT NULL, 
	teacher_email VARCHAR(200), 
	report_date VARCHAR(50) NOT NULL, 
	discipline_rating INTEGER NOT NULL, 
	participation_rating INTEGER NOT NULL, 
	performance_rating INTEGER NOT NULL, 
	comments TEXT NOT NULL, 
	flagged_for_review BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(enrollment_id) REFERENCES training_portal_enrollments (id) ON DELETE SET NULL, 
	FOREIGN KEY(batch_id) REFERENCES training_portal_batches (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_training_portal_behavior_reports_batch_id ON training_portal_behavior_reports (batch_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_behavior_reports_teacher_email ON training_portal_behavior_reports (teacher_email);

CREATE INDEX IF NOT EXISTS ix_training_portal_behavior_reports_flagged_for_review ON training_portal_behavior_reports (flagged_for_review);

CREATE INDEX IF NOT EXISTS ix_training_portal_behavior_reports_report_date ON training_portal_behavior_reports (report_date);

CREATE INDEX IF NOT EXISTS ix_training_portal_behavior_reports_enrollment_id ON training_portal_behavior_reports (enrollment_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_behavior_reports_candidate_email ON training_portal_behavior_reports (candidate_email);

CREATE INDEX IF NOT EXISTS ix_training_portal_behavior_reports_instructor_id ON training_portal_behavior_reports (instructor_id);

-- ----------------------------------------------------------------------------
-- Table: training_portal_class_calendar_links
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_class_calendar_links (
	id VARCHAR(50) NOT NULL, 
	session_id VARCHAR(50) NOT NULL, 
	user_id UUID NOT NULL, 
	calendar_id VARCHAR(255) NOT NULL, 
	google_event_id VARCHAR(255) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_class_calendar_session_user UNIQUE (session_id, user_id), 
	FOREIGN KEY(session_id) REFERENCES training_portal_class_sessions (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_training_portal_class_calendar_links_user_id ON training_portal_class_calendar_links (user_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_class_calendar_links_session_id ON training_portal_class_calendar_links (session_id);

-- ----------------------------------------------------------------------------
-- Table: training_portal_payment_orders
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_payment_orders (
	id VARCHAR(50) NOT NULL, 
	enrollment_id VARCHAR(50) NOT NULL, 
	candidate_email VARCHAR(200) NOT NULL, 
	amount_paise INTEGER NOT NULL,
	currency VARCHAR(10) NOT NULL,
	payment_method VARCHAR(30) NOT NULL,
	payment_purpose VARCHAR(20) NOT NULL DEFAULT 'full',
	provider VARCHAR(30) NOT NULL,
	provider_order_id VARCHAR(100), 
	provider_payment_id VARCHAR(100), 
	provider_signature VARCHAR(300), 
	status VARCHAR(30) NOT NULL, 
	webhook_payload JSON, 
	paid_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(enrollment_id) REFERENCES training_portal_enrollments (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_training_portal_payment_orders_provider_payment_id ON training_portal_payment_orders (provider_payment_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_payment_orders_enrollment_id ON training_portal_payment_orders (enrollment_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_payment_orders_candidate_email ON training_portal_payment_orders (candidate_email);

CREATE INDEX IF NOT EXISTS ix_training_portal_payment_orders_status ON training_portal_payment_orders (status);

CREATE INDEX IF NOT EXISTS ix_training_portal_payment_orders_provider_order_id ON training_portal_payment_orders (provider_order_id);

-- ----------------------------------------------------------------------------
-- Table: training_portal_refund_requests
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_refund_requests (
	id VARCHAR(50) NOT NULL, 
	enrollment_id VARCHAR(50) NOT NULL, 
	candidate_email VARCHAR(200) NOT NULL, 
	candidate_name VARCHAR(200) NOT NULL, 
	program_title VARCHAR(300) NOT NULL, 
	requested_amount FLOAT NOT NULL, 
	reason TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	admin_notes TEXT, 
	resolved_by_id UUID, 
	requested_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	resolved_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(enrollment_id) REFERENCES training_portal_enrollments (id) ON DELETE CASCADE, 
	FOREIGN KEY(resolved_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_training_portal_refund_requests_enrollment_id ON training_portal_refund_requests (enrollment_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_refund_requests_status ON training_portal_refund_requests (status);

CREATE INDEX IF NOT EXISTS ix_training_portal_refund_requests_candidate_email ON training_portal_refund_requests (candidate_email);

-- ----------------------------------------------------------------------------
-- Table: training_portal_transactions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_portal_transactions (
	id VARCHAR(50) NOT NULL, 
	transaction_id VARCHAR(80) NOT NULL, 
	enrollment_id VARCHAR(50), 
	candidate_email VARCHAR(200) NOT NULL, 
	candidate_name VARCHAR(200) NOT NULL, 
	program_title VARCHAR(300) NOT NULL, 
	transaction_type VARCHAR(30) NOT NULL, 
	amount FLOAT NOT NULL, 
	currency VARCHAR(10) NOT NULL, 
	payment_mode VARCHAR(30), 
	status VARCHAR(30) NOT NULL, 
	provider VARCHAR(30), 
	provider_transaction_id VARCHAR(120), 
	reference_order_id VARCHAR(50), 
	transaction_reference VARCHAR(120), 
	bank_name VARCHAR(150), 
	batch_id VARCHAR(50), 
	batch_name VARCHAR(200), 
	notes TEXT, 
	created_by_id UUID, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(enrollment_id) REFERENCES training_portal_enrollments (id) ON DELETE SET NULL, 
	FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_training_portal_transactions_created_at ON training_portal_transactions (created_at);

CREATE INDEX IF NOT EXISTS ix_training_portal_transactions_candidate_email ON training_portal_transactions (candidate_email);

CREATE UNIQUE INDEX IF NOT EXISTS ix_training_portal_transactions_transaction_id ON training_portal_transactions (transaction_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_transactions_status ON training_portal_transactions (status);

CREATE INDEX IF NOT EXISTS ix_training_portal_transactions_enrollment_id ON training_portal_transactions (enrollment_id);

CREATE INDEX IF NOT EXISTS ix_training_portal_transactions_transaction_type ON training_portal_transactions (transaction_type);

CREATE INDEX IF NOT EXISTS ix_training_portal_transactions_provider_transaction_id ON training_portal_transactions (provider_transaction_id);

-- ----------------------------------------------------------------------------
-- Performance & Dashboard Indexes
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_jobs_provider_id ON jobs (provider_id);
CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications (job_id);
CREATE INDEX IF NOT EXISTS idx_applications_seeker_id ON applications (seeker_id);
CREATE INDEX IF NOT EXISTS idx_matches_job_id ON matches (job_id);
CREATE INDEX IF NOT EXISTS idx_matches_seeker_id ON matches (seeker_id);