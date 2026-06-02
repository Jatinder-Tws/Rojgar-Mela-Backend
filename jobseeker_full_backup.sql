--
-- PostgreSQL database dump
--

-- Dumped from database version 15.4 (Debian 15.4-2.pgdg120+1)
-- Dumped by pg_dump version 15.4 (Debian 15.4-2.pgdg120+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: applicationstatus; Type: TYPE; Schema: public; Owner: jobmatch
--

CREATE TYPE public.applicationstatus AS ENUM (
    'applied',
    'shortlisted',
    'rejected',
    'auto_applied'
);


ALTER TYPE public.applicationstatus OWNER TO jobmatch;

--
-- Name: companytype; Type: TYPE; Schema: public; Owner: jobmatch
--

CREATE TYPE public.companytype AS ENUM (
    'individual',
    'company'
);


ALTER TYPE public.companytype OWNER TO jobmatch;

--
-- Name: difficultylevel; Type: TYPE; Schema: public; Owner: jobmatch
--

CREATE TYPE public.difficultylevel AS ENUM (
    'beginner',
    'intermediate',
    'advanced'
);


ALTER TYPE public.difficultylevel OWNER TO jobmatch;

--
-- Name: interviewsource; Type: TYPE; Schema: public; Owner: jobmatch
--

CREATE TYPE public.interviewsource AS ENUM (
    'manual',
    'auto'
);


ALTER TYPE public.interviewsource OWNER TO jobmatch;

--
-- Name: jobtype; Type: TYPE; Schema: public; Owner: jobmatch
--

CREATE TYPE public.jobtype AS ENUM (
    'in_office',
    'wfh',
    'hybrid'
);


ALTER TYPE public.jobtype OWNER TO jobmatch;

--
-- Name: milestonestatus; Type: TYPE; Schema: public; Owner: jobmatch
--

CREATE TYPE public.milestonestatus AS ENUM (
    'pending',
    'in_progress',
    'completed'
);


ALTER TYPE public.milestonestatus OWNER TO jobmatch;

--
-- Name: notificationtype; Type: TYPE; Schema: public; Owner: jobmatch
--

CREATE TYPE public.notificationtype AS ENUM (
    'interest',
    'shortlisted',
    'rejected',
    'match',
    'application',
    'auto_match',
    'welcome',
    'general'
);


ALTER TYPE public.notificationtype OWNER TO jobmatch;

--
-- Name: resourcetype; Type: TYPE; Schema: public; Owner: jobmatch
--

CREATE TYPE public.resourcetype AS ENUM (
    'course',
    'article',
    'video',
    'project',
    'certification'
);


ALTER TYPE public.resourcetype OWNER TO jobmatch;

--
-- Name: userrole; Type: TYPE; Schema: public; Owner: jobmatch
--

CREATE TYPE public.userrole AS ENUM (
    'seeker',
    'provider'
);


ALTER TYPE public.userrole OWNER TO jobmatch;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ai_coach_sessions; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.ai_coach_sessions (
    id uuid NOT NULL,
    seeker_id uuid NOT NULL,
    target_role character varying(100) NOT NULL,
    experience_level character varying(50) NOT NULL,
    focus_area character varying(50) NOT NULL,
    chat_history json NOT NULL,
    status character varying(20),
    overall_score integer,
    communication_score integer,
    content_score integer,
    general_feedback text,
    strengths json,
    gaps json,
    improvement_steps json,
    video_feedback json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    total_tokens integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.ai_coach_sessions OWNER TO jobmatch;

--
-- Name: ai_interview_sessions; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.ai_interview_sessions (
    id uuid NOT NULL,
    application_id uuid NOT NULL,
    seeker_id uuid NOT NULL,
    job_id uuid NOT NULL,
    chat_history json NOT NULL,
    status character varying(20),
    score integer,
    feedback text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.ai_interview_sessions OWNER TO jobmatch;

--
-- Name: applications; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.applications (
    id uuid NOT NULL,
    seeker_id uuid,
    job_id uuid NOT NULL,
    status public.applicationstatus NOT NULL,
    rejection_reason text,
    ai_feedback json,
    applied_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    candidate_name character varying(200),
    candidate_email character varying(200),
    candidate_phone character varying(20),
    candidate_experience character varying(100),
    candidate_resume_url text
);


ALTER TABLE public.applications OWNER TO jobmatch;

--
-- Name: assessment_results; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.assessment_results (
    id uuid NOT NULL,
    session_id uuid,
    user_id uuid,
    personality_type character varying(100),
    iq_score integer,
    recommended_domains json NOT NULL,
    detailed_evaluation character varying,
    created_at timestamp without time zone NOT NULL,
    personality_score integer,
    aptitude_score integer,
    reasoning_score integer,
    emotional_intelligence_score integer,
    tokens_utilized integer DEFAULT 0,
    cost double precision,
    quant_score integer,
    verbal_score integer
);


ALTER TABLE public.assessment_results OWNER TO jobmatch;

--
-- Name: assessment_sessions; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.assessment_sessions (
    id uuid NOT NULL,
    experience_level character varying(50),
    domain_interest character varying(100),
    qa_history json NOT NULL,
    status character varying(20),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    tokens_utilized integer DEFAULT 0,
    cost double precision
);


ALTER TABLE public.assessment_sessions OWNER TO jobmatch;

--
-- Name: department_jobs; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.department_jobs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(100) NOT NULL,
    department_id uuid NOT NULL
);


ALTER TABLE public.department_jobs OWNER TO jobmatch;

--
-- Name: departments; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.departments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(100) NOT NULL
);


ALTER TABLE public.departments OWNER TO jobmatch;

--
-- Name: external_candidate_matches; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.external_candidate_matches (
    id uuid NOT NULL,
    candidate_id uuid NOT NULL,
    job_id uuid NOT NULL,
    score double precision NOT NULL,
    highlights json,
    gaps json,
    fit_reason character varying(500),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.external_candidate_matches OWNER TO jobmatch;

--
-- Name: external_candidates; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.external_candidates (
    id uuid NOT NULL,
    job_id uuid,
    full_name character varying(200) NOT NULL,
    email character varying(200) NOT NULL,
    phone character varying(20) NOT NULL,
    state character varying(100),
    city character varying(100),
    department character varying(100),
    sub_role character varying(100),
    industries json,
    available_shift character varying(50),
    total_experience character varying(100),
    current_ctc character varying(50),
    source character varying(100),
    professional_journey text,
    resume_url text,
    salary_slip_url text,
    experience_letter_url text,
    profile_picture_url text,
    status character varying(50),
    applied_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    embedding public.vector(3072),
    is_matched boolean DEFAULT false NOT NULL,
    date_of_birth character varying(100),
    gender character varying(100)
);


ALTER TABLE public.external_candidates OWNER TO jobmatch;

--
-- Name: imported_user_passwords; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.imported_user_passwords (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    email character varying(255),
    plain_password character varying(255) NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.imported_user_passwords OWNER TO jobmatch;

--
-- Name: interviews; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.interviews (
    id uuid NOT NULL,
    seeker_id uuid NOT NULL,
    provider_id uuid NOT NULL,
    job_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    agenda text,
    scheduled_at timestamp without time zone NOT NULL,
    interviewer_name character varying(200) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    scheduled_period character varying(2),
    source character varying(20) DEFAULT 'manual'::character varying NOT NULL,
    application_id uuid
);


ALTER TABLE public.interviews OWNER TO jobmatch;

--
-- Name: job_postings; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.job_postings (
    id uuid NOT NULL,
    provider_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    description text NOT NULL,
    required_skills json,
    experience_required character varying(100),
    job_type public.jobtype,
    salary_range character varying(100),
    industry character varying(100),
    posted_by_name character varying(200),
    location character varying(200),
    is_active boolean NOT NULL,
    post_count integer NOT NULL,
    ai_interview_enabled boolean NOT NULL,
    selection_threshold integer NOT NULL,
    embedding public.vector(3072),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    shift character varying,
    perks text,
    employment_type character varying(100)
);


ALTER TABLE public.job_postings OWNER TO jobmatch;

--
-- Name: master_cities; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.master_cities (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    state_id integer NOT NULL
);


ALTER TABLE public.master_cities OWNER TO jobmatch;

--
-- Name: master_cities_id_seq; Type: SEQUENCE; Schema: public; Owner: jobmatch
--

CREATE SEQUENCE public.master_cities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.master_cities_id_seq OWNER TO jobmatch;

--
-- Name: master_cities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jobmatch
--

ALTER SEQUENCE public.master_cities_id_seq OWNED BY public.master_cities.id;


--
-- Name: master_industries; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.master_industries (
    id integer NOT NULL,
    name character varying(100) NOT NULL
);


ALTER TABLE public.master_industries OWNER TO jobmatch;

--
-- Name: master_industries_id_seq; Type: SEQUENCE; Schema: public; Owner: jobmatch
--

CREATE SEQUENCE public.master_industries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.master_industries_id_seq OWNER TO jobmatch;

--
-- Name: master_industries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jobmatch
--

ALTER SEQUENCE public.master_industries_id_seq OWNED BY public.master_industries.id;


--
-- Name: master_languages; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.master_languages (
    id integer NOT NULL,
    name character varying(100) NOT NULL
);


ALTER TABLE public.master_languages OWNER TO jobmatch;

--
-- Name: master_languages_id_seq; Type: SEQUENCE; Schema: public; Owner: jobmatch
--

CREATE SEQUENCE public.master_languages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.master_languages_id_seq OWNER TO jobmatch;

--
-- Name: master_languages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jobmatch
--

ALTER SEQUENCE public.master_languages_id_seq OWNED BY public.master_languages.id;


--
-- Name: master_roles; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.master_roles (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    industry_id integer
);


ALTER TABLE public.master_roles OWNER TO jobmatch;

--
-- Name: master_roles_id_seq; Type: SEQUENCE; Schema: public; Owner: jobmatch
--

CREATE SEQUENCE public.master_roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.master_roles_id_seq OWNER TO jobmatch;

--
-- Name: master_roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jobmatch
--

ALTER SEQUENCE public.master_roles_id_seq OWNED BY public.master_roles.id;


--
-- Name: master_states; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.master_states (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    code character varying(10),
    name_hi character varying(100),
    name_pa character varying(100)
);


ALTER TABLE public.master_states OWNER TO jobmatch;

--
-- Name: master_states_id_seq; Type: SEQUENCE; Schema: public; Owner: jobmatch
--

CREATE SEQUENCE public.master_states_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.master_states_id_seq OWNER TO jobmatch;

--
-- Name: master_states_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jobmatch
--

ALTER SEQUENCE public.master_states_id_seq OWNED BY public.master_states.id;


--
-- Name: matches; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.matches (
    id uuid NOT NULL,
    seeker_id uuid NOT NULL,
    job_id uuid NOT NULL,
    score double precision NOT NULL,
    highlights json,
    gaps json,
    fit_reason character varying(500),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.matches OWNER TO jobmatch;

--
-- Name: milestones; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.milestones (
    id uuid NOT NULL,
    roadmap_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    description text,
    order_num integer NOT NULL,
    skills character varying[],
    estimated_time character varying(50),
    status public.milestonestatus NOT NULL,
    dependencies uuid[],
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    stage_title character varying(100),
    stage_order integer DEFAULT 1,
    difficulty character varying(20) DEFAULT 'intermediate'::character varying
);


ALTER TABLE public.milestones OWNER TO jobmatch;

--
-- Name: notifications; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.notifications (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    type public.notificationtype NOT NULL,
    title character varying(200) NOT NULL,
    message text NOT NULL,
    is_read boolean NOT NULL,
    related_job_id uuid,
    related_user_id uuid,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.notifications OWNER TO jobmatch;

--
-- Name: otp_records; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.otp_records (
    id uuid NOT NULL,
    email character varying(255),
    phone character varying(20),
    code character varying(6) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.otp_records OWNER TO jobmatch;

--
-- Name: portfolios; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.portfolios (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    headline character varying(200),
    bio text,
    date_of_birth character varying(20),
    gender character varying(20),
    city character varying(100),
    state character varying(100),
    linkedin_url character varying(500),
    github_url character varying(500),
    website_url character varying(500),
    total_experience_years double precision,
    current_company character varying(200),
    "current_role" character varying(200),
    skills json,
    work_experiences json,
    education json,
    certifications json,
    languages json,
    projects json,
    intro_video_path character varying(500),
    intro_video_filename character varying(255),
    intro_audio_path character varying(500),
    intro_audio_filename character varying(255),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.portfolios OWNER TO jobmatch;

--
-- Name: provider_availability_windows; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.provider_availability_windows (
    id uuid NOT NULL,
    provider_id uuid NOT NULL,
    day_of_week smallint NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    start_period character varying(2) DEFAULT 'AM'::character varying,
    end_period character varying(2) DEFAULT 'AM'::character varying,
    period character varying(2) DEFAULT NULL::character varying
);


ALTER TABLE public.provider_availability_windows OWNER TO jobmatch;

--
-- Name: provider_interview_settings; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.provider_interview_settings (
    provider_id uuid NOT NULL,
    auto_schedule_enabled boolean NOT NULL,
    slot_duration_minutes integer NOT NULL,
    buffer_minutes integer NOT NULL,
    timezone character varying(64) NOT NULL,
    lookahead_days integer NOT NULL,
    min_notice_hours integer NOT NULL,
    default_title character varying(200) NOT NULL,
    default_interviewer_name character varying(200),
    default_agenda text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.provider_interview_settings OWNER TO jobmatch;

--
-- Name: resources; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.resources (
    id uuid NOT NULL,
    milestone_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    type public.resourcetype NOT NULL,
    url text,
    platform character varying(100),
    duration character varying(50),
    difficulty public.difficultylevel,
    description text,
    is_free boolean NOT NULL,
    rating double precision,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.resources OWNER TO jobmatch;

--
-- Name: resumes; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.resumes (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    filename character varying(255) NOT NULL,
    file_path character varying(500) NOT NULL,
    file_size_bytes integer,
    source character varying(20) NOT NULL,
    parsed_text text,
    parsed_json json,
    embedding public.vector(3072),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.resumes OWNER TO jobmatch;

--
-- Name: roadmap_categories; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.roadmap_categories (
    id uuid NOT NULL,
    name character varying(100) NOT NULL,
    icon character varying(50),
    description text
);


ALTER TABLE public.roadmap_categories OWNER TO jobmatch;

--
-- Name: roadmap_roles; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.roadmap_roles (
    id uuid NOT NULL,
    category_id uuid NOT NULL,
    title character varying(100) NOT NULL,
    description text,
    level character varying(50),
    growth character varying(20),
    salary_range character varying(50),
    skills character varying[]
);


ALTER TABLE public.roadmap_roles OWNER TO jobmatch;

--
-- Name: roadmaps; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.roadmaps (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    target_role character varying(100) NOT NULL,
    current_level character varying(50) NOT NULL,
    target_level character varying(50) NOT NULL,
    skills_to_develop character varying[],
    estimated_duration character varying(50),
    status character varying(20) NOT NULL,
    ai_prompt_version character varying(20) NOT NULL,
    generation_preferences json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    current_skills text,
    market_based_salary json
);


ALTER TABLE public.roadmaps OWNER TO jobmatch;

--
-- Name: users; Type: TABLE; Schema: public; Owner: jobmatch
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    first_name character varying(50),
    last_name character varying(50),
    email character varying(255),
    phone character varying(15) NOT NULL,
    hashed_password character varying(255),
    profile_pic_url text,
    is_verified boolean NOT NULL,
    onboarding_complete boolean NOT NULL,
    is_assessment_done boolean NOT NULL,
    totp_secret character varying(32),
    totp_enabled boolean NOT NULL,
    is_first_login boolean,
    role public.userrole,
    industry character varying(100),
    job_role character varying(100),
    job_type public.jobtype,
    salary_range character varying(50),
    experience character varying(50),
    auto_apply_enabled boolean NOT NULL,
    company_type public.companytype,
    company_name character varying(200),
    company_location character varying(200),
    company_size character varying(50),
    preferred_locations json,
    profile_embedding public.vector(3072),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    father_or_mother_name character varying(200),
    gender character varying(50),
    address text,
    highest_qualification character varying(200),
    stream_specialization character varying(200),
    college_institute_name character varying(255),
    preferred_job_sector character varying(200),
    job_roles_offering text,
    specific_requirements text,
    company_address character varying(500),
    is_super_admin boolean DEFAULT false NOT NULL
);


ALTER TABLE public.users OWNER TO jobmatch;

--
-- Name: master_cities id; Type: DEFAULT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.master_cities ALTER COLUMN id SET DEFAULT nextval('public.master_cities_id_seq'::regclass);


--
-- Name: master_industries id; Type: DEFAULT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.master_industries ALTER COLUMN id SET DEFAULT nextval('public.master_industries_id_seq'::regclass);


--
-- Name: master_languages id; Type: DEFAULT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.master_languages ALTER COLUMN id SET DEFAULT nextval('public.master_languages_id_seq'::regclass);


--
-- Name: master_roles id; Type: DEFAULT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.master_roles ALTER COLUMN id SET DEFAULT nextval('public.master_roles_id_seq'::regclass);


--
-- Name: master_states id; Type: DEFAULT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.master_states ALTER COLUMN id SET DEFAULT nextval('public.master_states_id_seq'::regclass);


--
-- Data for Name: ai_coach_sessions; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.ai_coach_sessions (id, seeker_id, target_role, experience_level, focus_area, chat_history, status, overall_score, communication_score, content_score, general_feedback, strengths, gaps, improvement_steps, video_feedback, created_at, updated_at, total_tokens) FROM stdin;
\.


--
-- Data for Name: ai_interview_sessions; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.ai_interview_sessions (id, application_id, seeker_id, job_id, chat_history, status, score, feedback, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: applications; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.applications (id, seeker_id, job_id, status, rejection_reason, ai_feedback, applied_at, updated_at, candidate_name, candidate_email, candidate_phone, candidate_experience, candidate_resume_url) FROM stdin;
\.


--
-- Data for Name: assessment_results; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.assessment_results (id, session_id, user_id, personality_type, iq_score, recommended_domains, detailed_evaluation, created_at, personality_score, aptitude_score, reasoning_score, emotional_intelligence_score, tokens_utilized, cost, quant_score, verbal_score) FROM stdin;
08e29334-fb6e-41fb-bc12-a1e087d584cb	2a8d59ac-cff0-4c01-8d34-e1a6f078a6b6	\N	Pragmatic, Analytical, and Collaborative	110	["Entry-level Business Analyst", "Junior Project Coordinator", "Technical Support Specialist"]	The candidate demonstrates a highly structured and pragmatic approach to learning and problem-solving. They are adept at information gathering, moving efficiently from theoretical understanding to practical application through hands-on projects. Their responses consistently highlight a strong analytical mindset, particularly evident in their systematic approach to troubleshooting roadblocks, identifying root causes, and iteratively adjusting solutions. Furthermore, the candidate shows a clear preference for collaboration, actively seeking diverse perspectives and advice from others, and a commendable desire to share knowledge and learnings, indicating a team-oriented individual who values collective success and continuous improvement.\n\nWhile generally strong, the candidate's motivation for sharing knowledge appears to be significantly driven by external validation, specifically "receiving appreciation and positive feedback." This suggests a potential over-reliance on external recognition rather than a purely intrinsic drive for impact or a deeper understanding through the act of teaching itself. For a 'Fresher / No Experience' candidate, this is not a critical flaw but indicates an area for growth in developing more intrinsic motivation and focusing on the broader, self-driven impact of their contributions. Some initial answers, while correct, were foundational and lacked unique depth, which is typical for a fresher but worth noting.\n\nOverall, this candidate is well-suited for roles that require systematic thinking, practical application, and collaborative problem-solving. Their methodical approach to learning and troubleshooting, combined with a willingness to seek and offer help, makes them a valuable asset in team-based environments. They would excel in positions where processes need to be understood, problems diagnosed, and solutions implemented iteratively. While their drive for external appreciation should be a point of awareness, their pragmatic and analytical disposition, coupled with a collaborative spirit, suggests a strong potential for growth and contribution in structured, team-oriented roles.	2026-05-18 06:04:48.569024	\N	\N	\N	\N	0	\N	\N	\N
a8d4f641-b3af-451f-87b7-8ae686c3f10a	d346d400-bf1f-44ed-9fd5-5b1901b23736	\N	Analytical/Balanced	105	["Information Technology - Frontend Developer", "General Tech"]	Based on the input provided, you show a balanced capability matching your selected domain.	2026-05-11 05:06:23.79003	\N	\N	\N	\N	0	\N	\N	\N
4d8b2066-2d22-4b95-b657-ff2aed99ff9c	16985dec-f2fe-4268-86c3-488396258ad8	\N	Analytical/Balanced	105	["Information Technology - Backend Developer", "General Tech"]	Based on the input provided, you show a balanced capability matching your selected domain.	2026-05-15 07:21:53.618446	\N	\N	\N	\N	0	\N	\N	\N
210115d1-874d-4453-81ab-87d5218242a3	e7279fe8-2cfc-437c-80e0-2df8d79a9ca6	\N	Analytical/Balanced	105	["Information Technology - Backend Developer", "General Tech"]	Based on the input provided, you show a balanced capability matching your selected domain.	2026-05-15 09:23:20.381635	\N	\N	\N	\N	0	\N	\N	\N
66941ea2-6378-4972-8129-9ea382c02ec9	3419b265-f122-4b37-b5c8-0b22982d6eb7	\N	Pragmatic, Harmony-Oriented, Indirect Communicator	98	["Data Entry/Analysis (entry-level)", "Research Assistant (supporting role)", "Technical Writer (entry-level)"]	The candidate demonstrates a foundational understanding of problem-solving, starting with a logical approach to breaking down complex issues into manageable parts and a willingness to seek external input when stuck. They show an ability to reflect and learn from past experiences, as evidenced by their shift from a purely trial-and-error approach (Q3) to a more analytical one (Q4) after an initial setback, and their articulate summary of the importance of direct communication (Q13) after a project crisis. Furthermore, they understand the value of leveraging diverse skills in a team setting (Q7).\n\nHowever, significant weaknesses emerge in their approach to collaboration, conflict resolution, and direct communication. Their initial preference for trying suggestions without thorough analysis (Q3) indicates a lack of critical evaluation. A major concern is their reaction to a colleague offering a better solution post-implementation (Q6), where they propose focusing solely on improving their own skills to avoid needing external suggestions. This response is highly individualistic, defensive, and fundamentally misinterprets the essence of collaborative teamwork, suggesting a potential for arrogance or insecurity that hinders effective team integration. Throughout the scenario, the candidate consistently prioritizes team harmony over effectiveness (Q8), leading to passive-aggressive and indirect communication strategies, such as waiting for others to realize problems (Q9), subtly leaving reports (Q10), and only resorting to direct communication under extreme pressure (Q11). Even after articulating the importance of direct communication (Q13), they fail to apply this lesson when addressing a struggling peer (Q14, Q15), instead consistently deferring the uncomfortable conversation to the team lead. This highlights a significant gap between theoretical understanding and practical application, particularly in interpersonal challenges.\n\nOverall, while the candidate possesses basic problem-solving skills and a capacity for self-reflection, their strong conflict aversion, indirect communication style, and individualistic tendencies present substantial hurdles for success in dynamic, collaborative professional environments. They would likely struggle in roles requiring proactive communication, assertiveness, constructive disagreement, or direct peer feedback. Their current profile suggests a better fit for roles that are more structured, allow for independent work, and minimize direct interpersonal conflict, where their reflective learning ability can be leveraged without requiring them to navigate complex team dynamics or challenging conversations.	2026-05-18 09:37:33.30726	45	65	60	50	0	\N	\N	\N
f6418e26-a949-4b74-b650-6576364f4b54	c75ac0e3-a22c-4c40-9c63-94abe95d10f2	\N	Pragmatic, Lacks Situational Judgment	95	["Junior Research Assistant", "Technical Documentation Specialist", "Entry-Level Business Analyst Support"]	The candidate demonstrates a commendable initial drive for independent research and a willingness to seek help when encountering difficulties. They show good reflective capacity, particularly when guided to analyze past failures and develop systematic plans (Q6). Their collaborative skills are a significant strength; they actively listen, synthesize diverse viewpoints, and strive for consensus, ensuring team members feel heard (Q11-14). The initiative to document lessons learned and contribute to a collective knowledge base is also positive (Q9-10). They appear committed to agreed-upon team plans, even if personal preferences differ (Q14).\n\nHowever, several critical weaknesses undermine the candidate's overall profile. Their initial problem-solving approach is notably shallow and impulsive, as evidenced by "trying a few different solutions quickly without much planning, hoping one of them works" (Q4). This indicates a lack of structured analytical thinking under pressure. Furthermore, their initial understanding of plan execution is flawed, with an stated intent to "strictly follow the plan step-by-step without deviation... and only report once the entire plan is complete" (Q7), which demonstrates a significant lack of adaptability and understanding of continuous feedback loops in project management. The most concerning weakness, however, is their response to identifying an optimization opportunity: "Immediately implement the optimization if it seems straightforward, assuming it will clearly benefit the project" (Q15). This reveals a severe lack of situational judgment, process adherence, and understanding of risk management. For a fresher, acting unilaterally on "optimizations" without consultation or proper vetting is highly problematic and could lead to significant project disruptions or errors. This suggests a potential for overconfidence and a disregard for established protocols and team communication.\n\nWhile the candidate possesses valuable collaborative and learning-oriented traits, their significant lapses in judgment regarding structured problem-solving, process adherence, and unilateral decision-making make them a high-risk candidate for roles requiring independent execution or critical thinking in dynamic environments. Their strengths are primarily in supportive, collaborative, and documentation-heavy tasks where decisions are made collectively and processes are strictly defined. They would require extensive mentorship and close supervision to mitigate the risks associated with their impulsive tendencies and lack of understanding of organizational impact. They are not a strong fit for roles demanding high autonomy or critical decision-making without prior consultation.	2026-05-21 06:42:48.698106	65	60	60	70	35016	0.0122556	\N	\N
5d65d381-0621-4db8-9592-330b170008c7	56f3e417-c4f9-43c6-8d0f-e25fe83aa0b4	\N	Research-Oriented, Dependent, Self-Aware	98	["Junior Technical Support Engineer", "Junior QA Analyst", "Technical Documentation Assistant"]	The candidate, a fresher interested in backend development, demonstrates a mixed profile with notable strengths in self-awareness and research, but significant weaknesses in independent problem-solving and decision-making. Initially, their approach to performance issues was highly dependent, immediately seeking "exact steps" from a senior team member (Q2, Q4). This indicates a strong reluctance to take initiative or ownership of problem investigation. Even after successfully reproducing an issue and gathering detailed notes (Q3), they preferred to hand over findings and wait for solutions rather than proposing their own, which is a shallow response for a budding developer.\n\nHowever, the candidate showed an ability to form a hypothesis when prompted (Q5) and demonstrated strong proactive research skills, identifying common bottlenecks and measurement techniques (Q6). This suggests a capacity for learning and information gathering. Unfortunately, this initiative was short-lived, as they reverted to dependency, asking the senior to choose the next step from their findings (Q7) and explicitly stating a preference for guidance due to lack of experience (Q8). This consistent pattern of deferring decisions, even when encouraged to think independently, is a critical flaw for a developer role, where autonomous critical thinking and problem-solving are paramount.\n\nA significant strength emerged in their self-awareness (Q9), where they accurately identified a lack of a clear framework for prioritizing and comparing potential solutions. This insight, coupled with their proactive commitment to independently research structured problem-solving methodologies like '5 Whys' (Q10), indicates a strong desire for self-improvement and a practical approach to skill development. While these later responses show potential, the overall interview history reveals a candidate who, despite being capable of research and self-reflection, struggles significantly with independent critical thinking, initiative, and decision-making in a technical context. They would require substantial mentorship and a highly structured environment to overcome their dependency and develop into an autonomous contributor.	2026-05-15 12:28:20.102794	\N	\N	\N	\N	0	\N	\N	\N
4c9041fc-0be3-451f-aafc-c5f43eac1c2e	60b65568-5492-489c-977c-cab306e22e9b	\N	Inconsistent	90	["Data Collection & Entry Specialist", "Structured Apprenticeship Program Participant", "Junior Manual QA Tester"]	The candidate demonstrates a proactive and hands-on approach to learning new fields, preferring practical projects and tutorials, which is a positive trait for a fresher. They also show an initial willingness to research and consult peers when facing challenges, and a capacity for self-reflection and analysis when a path proves unsuitable (Q13, Q14). Their inclination to network extensively to understand daily experiences and company culture (Q15) indicates a practical and socially aware approach to career exploration.\n\nHowever, the candidate exhibits significant and concerning inconsistencies in their decision-making and problem-solving abilities. They swing between immediately pivoting to a colleague's suggestion (Q4, Q7) and stubbornly sticking to their own solution due to time invested (Q5, Q6), demonstrating a clear susceptibility to the sunk-cost fallacy and a lack of consistent critical evaluation. Their reasoning is often shallow; for instance, arguing a solution is "good enough" based on time invested rather than objective merit (Q6). Furthermore, they show an inability to make decisions under uncertainty, preferring endless research (Q10) or relying entirely on an expert's recommendation (Q11), rather than synthesizing information and exercising independent judgment. This dependency extends to impulsively abandoning a path (Q12) without sufficient perseverance.\n\nGiven these observations, the candidate's overall fit for roles requiring independent initiative, adaptability, or robust critical thinking is poor. While their interest in 'Career Discovery' aligns with their exploratory nature, their demonstrated lack of conviction, inconsistent logical reasoning, and tendency to either blindly trust or stubbornly resist change would hinder their progress in dynamic environments. They would likely excel in highly structured roles with clear, predefined tasks, where adherence to protocols and strong, consistent mentorship are paramount, rather than roles demanding significant self-direction or complex problem-solving.	2026-05-18 10:15:00.895327	45	45	40	55	40422	\N	\N	\N
2f2e53c4-5d79-433c-b0e9-53545c967652	475f9488-7a28-4cdc-9227-a2bffe341830	\N	Pragmatic, Task-Oriented, Structured Learner	105	["Technical Documentation Writer", "Specialized Tool Administrator", "Structured Data Analyst (Entry-Level)"]	The candidate demonstrates an initial proactive approach to learning new tasks by researching and experimenting (Q1). Once committed to a new tool or process, they show strong dedication to mastering it, proactively exploring features, seeking tutorials, and practicing to become an expert user (Q9). Furthermore, when finally engaged in assisting a struggling colleague, they exhibit excellent pedagogical skills, breaking down tasks logically, explaining the 'why' behind steps, and guiding practice for true understanding (Q15). They also understand the importance of knowledge sharing within a team (Q4) and can articulate problems clearly (Q3). They are aware of project impact and can escalate issues to management when necessary (Q13).\n\nSignificant weaknesses include a low tolerance for frustration and a tendency to give up quickly, waiting for others to provide answers when initial attempts fail (Q2). A major concern is their strong resistance to feedback, new methods, and process improvements, preferring to stick to their own working methods even when more efficient alternatives are suggested (Q5, Q6) or new tools are introduced (Q7, Q8). This indicates a lack of adaptability and openness to change, which is critical in dynamic environments. Their approach to team collaboration is also problematic; they are reluctant to proactively assist struggling colleagues, initially offering minimal help (Q10) and then deflecting responsibility (Q11, Q12) until the issue impacts project progress and requires managerial intervention (Q13, Q14). This suggests a self-focused orientation rather than a strong team-player mindset.\n\nWhile the candidate possesses a commendable capacity for individual learning and structured problem-solving once fully committed, their overall fit for roles requiring high adaptability, proactive collaboration, and continuous improvement is questionable. Their resistance to change and reluctance to engage in direct peer support until external pressure mounts are significant drawbacks. They would likely excel in highly structured environments with well-defined processes and minimal change, where deep individual mastery of specific tools or tasks is prioritized over rapid innovation or extensive teamwork. Their potential is hampered by a rigid mindset and underdeveloped emotional intelligence in team settings.	2026-05-21 07:06:20.933893	60	70	65	55	32955	0.011534250000000001	\N	\N
976d1840-26da-4040-a81c-212e64237c37	827d8cf1-d869-4455-8faf-c8bab3b6a1fd	\N	Methodical (when guided), Reactive	90	["Data Entry/Verification", "Junior QA Tester (Manual)", "Support Role (Tier 1, Scripted)"]	The candidate demonstrates a foundational understanding of problem identification and a willingness to initiate research when faced with new challenges. They exhibit a commendable ability to employ structured analytical tools, such as a comparison matrix, when explicitly prompted to evaluate multiple solutions. Furthermore, their commitment to thoroughness in the later stages of problem resolution, including root cause analysis of complications and systematic testing against various scenarios, indicates a capacity for methodical execution and quality assurance within a defined process.\n\nHowever, the candidate's problem-solving approach is significantly hampered by critical flaws in judgment and proactive thinking. Their initial decision to select a solution based solely on popularity rather than critical evaluation is a major weakness, compounded by an alarming tendency to persist with a demonstrably failing solution, indicating a lack of adaptability and self-correction. There is also a notable absence of foresight, as evidenced by immediately implementing a solution without prior planning or validation. Beyond problem resolution, the candidate consistently displays a reactive and transactional mindset regarding teamwork and knowledge sharing. Responses like "await your next assignment," "only if they specifically ask," and documenting primarily "to avoid being repeatedly asked" reveal a limited understanding of collaborative contribution, organizational learning, and proactive value creation. Their approach to documentation for new team members also suggests a lack of empathy for the user's learning curve, prioritizing exhaustive detail over clarity and accessibility.\n\nOverall, this candidate appears to be a task-oriented individual who can perform well when provided with clear instructions and a structured framework. They possess some analytical capabilities, particularly in the execution phase of problem-solving. However, their significant deficiencies in critical thinking, independent judgment, proactivity, and a collaborative mindset make them unsuitable for roles requiring high autonomy, strategic decision-making, or innovative problem-solving. They would require substantial guidance and supervision, particularly in the initial stages of problem analysis and in contributing to broader team and organizational goals. Their fit would be best in highly procedural environments where adherence to established methods is paramount.	2026-05-21 08:51:02.002337	45	55	50	45	38918	0.0136213	\N	\N
eb7c10d1-9724-4c51-b1f3-46704795ee9a	664cd5b3-924a-4e29-b8cf-a573359e3217	\N	Collaborative Learner, Action-Oriented, but Impulsive	92	["Junior Support Role", "Process Documentation/Analysis (Entry-Level)", "Quality Assurance (Manual Testing)"]	The candidate demonstrates a commendable willingness to help teammates and shows an ability to learn from initial missteps, as seen in their progression from doing a teammate's task (Q1) to understanding the importance of empowering them with knowledge (Q2, Q3). They also exhibit a proactive approach in identifying inefficiencies (Q12) and systematically observing and documenting processes (Q13). Their capacity to seek managerial guidance when overwhelmed (Q11) indicates a developing sense of self-awareness and professional communication. The proposal of a standardized template (Q7) shows an understanding of systemic solutions, albeit after several less effective initial attempts.\n\nA significant weakness lies in the candidate's initial problem-solving approach, which often tends to be superficial, reactive, and focused on symptoms rather than root causes. For instance, their first approach to recurring errors was a generic reminder to 'be more careful' (Q4), and later suggesting a senior review (Q6) rather than addressing the underlying process flaws directly. Their self-management and prioritization skills are also questionable, as evidenced by their initial attempt to cope with workload by 'working extra hours' (Q9) and then making the poor strategic decision to 'reduce effort on the learning module' (Q10), which is critical for long-term growth. The most critical flaw is demonstrated in the final question (Q15), where they immediately jump to 'researching and proposing advanced automation software' as the ultimate solution without further analysis, feasibility studies, or considering simpler, more practical alternatives. This reveals a concerning lack of critical thinking, a tendency to oversimplify complex problems, and a potential overestimation of their technical understanding for a fresher role.\n\nWhile the candidate possesses a collaborative spirit and a demonstrable capacity for learning, their interview history reveals significant gaps in critical thinking, strategic problem-solving, and practical judgment. They tend to offer quick, sometimes impulsive solutions, and struggle with deep root-cause analysis. For a fresher, the willingness to learn is valuable, but the consistent pattern of suboptimal initial responses and the particularly concerning leap to an unverified, complex solution in the final question suggest they would require substantial guidance and oversight in roles demanding independent problem-solving or strategic input. They would likely fit best in structured environments where tasks are clearly defined, and there is ample mentorship to guide their decision-making and develop their analytical skills.	2026-05-21 11:59:02.460758	65	60	55	75	45697	0.01599395	\N	\N
4cfc9564-9b2f-441f-9211-380c55ff2c70	9f9a6dbe-8211-4408-8763-57cdb54797e8	\N	Dependent, Avoidant, and Initially Pragmatic	90	["Technical Documentation Assistant", "Junior Support Engineer (Tier 1)", "UI/UX Assistant (non-coding focus)"]	The candidate initially demonstrated several positive traits, including clear communication, a structured approach to identifying and reporting issues (Q1, Q2), and a proactive mindset in seeking workarounds (Q3). Their ability to document required adjustments (Q4) and prepare for technical discussions by reviewing existing resources and compiling questions (Q6, Q7, Q9, Q10) is commendable for an entry-level professional. These responses suggest a candidate who can follow processes, communicate effectively within a team, and perform diligent preparatory work.\n\nHowever, the candidate's performance significantly deteriorated when faced with actual technical challenges and the need for independent problem-solving. Their response to a syntax error (Q11) by "spending the remaining 30 minutes trying various random fixes, hoping one will work, to show initiative" is a critical flaw. This indicates a severe lack of systematic debugging skills, poor judgment, and a tendency towards inefficient, trial-and-error approaches under pressure. This is further compounded by their repeated and consistent choice (Q13, Q14, Q15) to "focus on other tasks" and "let the senior developer guide the discussion on the bug" when preparing for a meeting about an unresolved issue. This demonstrates a profound lack of ownership, a passive learning style, and a failure to leverage senior expertise effectively by coming prepared with specific attempts, roadblocks, and targeted questions.\n\nOverall, while the candidate exhibits basic communication and organizational skills, their core technical problem-solving aptitude, critical thinking, and proactive learning approach are severely underdeveloped. Their tendency to avoid direct engagement with difficult technical problems and rely entirely on others for solutions makes them a poor fit for a role that requires independent initiative, systematic debugging, and effective collaboration in resolving complex issues, even at an entry level. They would require significant mentorship and direct guidance to overcome these fundamental weaknesses.	2026-05-28 11:24:52.820221	45	40	40	50	51993	0.01819755	\N	\N
3d73d1bd-0487-4232-bc4c-92618576f928	b5d2cfa8-77f0-4547-9d8a-0f71d1346de6	\N	Adaptive Problem-Solver	92	["Junior Project Coordinator", "Team Support Specialist", "Process Improvement Analyst (Entry-Level)"]	The candidate demonstrates a commendable capacity for learning and self-correction, particularly in interpersonal and team-based scenarios. Initially, they showed a tendency to escalate issues (Q1) and adopt a formal, potentially alienating communication style (Q2). However, they quickly adapted, recognizing the importance of empathy and direct, informal communication (Q3, Q4). Their proactive approach to understanding team members' working styles (Q5) and their innovative suggestions for encouraging participation (Q6, Q7) highlight strong collaborative instincts and an ability to propose structured solutions for team effectiveness. The candidate also showed excellent analytical recovery when prompted to justify ideas using a scoring matrix (Q9), indicating an ability to apply structured decision-making frameworks.\n\nA significant concern lies in the candidate's foundational logical reasoning and quantitative accuracy. They made multiple errors in straightforward aptitude questions, including miscounting (Q11), simple pattern recognition (Q12, Q14), and a fundamental flaw in syllogistic deduction (Q15). These errors suggest a lack of precision and attention to detail in analytical tasks. Furthermore, their initial judgment in problem-solving was weak, exemplified by prematurely escalating an issue (Q1) and proposing a superficial prioritization method (Q8 – "quick team vote" based on popularity, lacking robust criteria). While they demonstrated learning, these initial missteps and consistent analytical inaccuracies are critical weaknesses for any professional role requiring independent logical thought or data interpretation.\n\nAs a fresher, the candidate shows potential in roles that emphasize teamwork, communication, and process adherence, especially where they can learn from established frameworks and receive clear guidance. Their adaptability and willingness to learn from feedback are valuable assets. However, their current analytical precision and independent problem-solving abilities are underdeveloped. They would likely struggle in roles requiring high levels of independent critical analysis, complex data interpretation, or robust decision-making without significant oversight. They would benefit from a structured environment that allows them to build their analytical skills while leveraging their strengths in collaboration and interpersonal communication.	2026-05-28 09:10:09.67284	65	35	60	75	40652	0.0142282	\N	\N
\.


--
-- Data for Name: assessment_sessions; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.assessment_sessions (id, experience_level, domain_interest, qa_history, status, created_at, updated_at, tokens_utilized, cost) FROM stdin;
d346d400-bf1f-44ed-9fd5-5b1901b23736	Fresher / No Experience	Information Technology - Frontend Developer	[{"question": "As a fresher interested in Frontend Development, which of the following aspects most appeals to you?", "answer": "Creating visually appealing and interactive user interfaces that users directly experience."}, {"question": "Which of the following best describes your approach to learning new concepts?", "answer": "Reading documentation"}, {"question": "You've read the documentation for a new CSS property, but when you try to implement it, it doesn't work as expected on your webpage. What's your primary approach to resolve this?", "answer": "Search for solutions and explanations on developer forums or search engines like Google and Stack Overflow."}, {"question": "Imagine you've spent time designing and implementing a new UI component. A colleague reviews it and suggests significant changes to improve its user-friendliness. What's your initial reaction and approach?", "answer": "Thank them for the feedback, ask for specific examples, and discuss potential alternative solutions together."}, {"question": "You're working on a new feature and have a brilliant, visually unique design idea. However, implementing it perfectly would require a lot of complex code, potentially impacting page load speed and making it less accessible for users with certain needs. How would you approach this situation?", "answer": "Simplify the design to ensure optimal performance and accessibility, even if it means losing some of the unique visual flair."}, {"question": "You've discovered a new best practice for structuring your HTML and CSS to make it more maintainable and accessible. What's your most appropriate next step in a team project?", "answer": "Apply this best practice only to the new features you develop from this point forward."}, {"question": "You've noticed a small but significant opportunity to improve an existing piece of frontend code (e.g., making it more accessible, slightly more performant, or cleaner) that isn't part of your current assigned task. What would be your most appropriate action?", "answer": "Go ahead and implement the improvement yourself, as it's a clear benefit to the project."}, {"question": "You've just completed implementing a new feature or component that you were assigned. What is your most appropriate next step before considering it 'done'?", "answer": "Thoroughly test your implementation yourself to ensure it works as expected across different scenarios."}, {"question": "You've been trying to fix a complex frontend bug for a significant amount of time, and you've exhausted your usual troubleshooting methods (checking documentation, searching forums, debugging tools). What is your most appropriate next action in a team environment?", "answer": "Take a short break to clear your head, then return to the problem with a fresh perspective."}, {"question": "Which of the following best describes your approach to learning new concepts?", "answer": "Reading documentation"}]	completed	2026-05-11 05:02:46.384239	2026-05-11 05:05:12.570267	0	\N
16985dec-f2fe-4268-86c3-488396258ad8	Fresher / No Experience	Information Technology - Backend Developer	[{"question": "Imagine you're given a new programming task or concept you've never encountered before. What's your typical first step?", "answer": "Try to break it down into smaller, more manageable parts and experiment with each."}, {"question": "You've broken down a complex problem into smaller parts and experimented with each, but you're still stuck on a particular section. What's your next move?", "answer": "Consult online resources, documentation, or tutorials for similar problems and solutions."}, {"question": "You've tried breaking down a problem, experimenting, and consulting online resources, but you're still stuck on a particular coding challenge. What would be your next step?", "answer": "Document the problem and your attempts, then ask a more experienced colleague or mentor for help."}, {"question": "Which of the following best describes your approach to learning new concepts?", "answer": "Reading documentation"}, {"question": "You've just successfully implemented a new feature after spending time understanding its documentation. A new team member is struggling with the same feature. How would you typically assist them?", "answer": "Offer to pair program with them to work through the problem together."}, {"question": "You've completed a coding task and submitted it for review. A team member suggests an alternative approach that you hadn't considered. What's your typical response?", "answer": "Immediately acknowledge their suggestion and start implementing it without further discussion."}, {"question": "You've accepted a team member's suggestion for an alternative approach. However, after a bit more thought, you identify potential advantages in your original solution or possible drawbacks in their suggestion. What would you do?", "answer": "Implement the suggested alternative, but secretly try to prove your original idea was better."}, {"question": "You've implemented a team member's suggested alternative, but after working with it, you're convinced your original solution was more robust or efficient. What's the most constructive way to proceed?", "answer": "Continue with the suggested alternative, but quietly start working on your original solution in your spare time to demonstrate its superiority."}, {"question": "You've implemented a team-agreed approach for a feature, but after further thought and observation, you've identified a potential improvement based on your original idea that could make the feature more robust or efficient. How would you best introduce this to the team?", "answer": "Wait for a bug or performance issue to arise with the current implementation, then suggest your improvement as a fix."}, {"question": "Following your decision to wait for a bug before suggesting your improvement, the feature has been stable for several weeks without any issues. However, you remain convinced that your alternative approach offers significant long-term benefits in terms of maintainability or efficiency. What would be your most constructive next step?", "answer": "Quietly implement your improved version in a separate branch and present it to the team as a 'proof of concept' when it's ready."}]	completed	2026-05-15 07:18:13.476831	2026-05-15 07:20:52.07769	0	\N
56f3e417-c4f9-43c6-8d0f-e25fe83aa0b4	Fresher / No Experience	Information Technology - Backend Developer	[{"question": "As a fresher interested in backend development, what aspect of building the 'behind-the-scenes' logic of an application excites you the most?", "answer": "Ensuring the application can handle many users without slowing down."}, {"question": "You've developed a simple backend feature, and users start reporting that it's occasionally slow. As a fresher, what would be your initial approach to investigate this performance issue?", "answer": "Ask a senior team member to tell you exactly what to do."}, {"question": "You've noticed the application is occasionally slow, and you're about to ask a senior team member for help. Before you do, what would be your preferred initial step to prepare for that discussion?", "answer": "Try to reproduce the slowness and note down specific scenarios or any error messages."}, {"question": "You've successfully reproduced the slowness and noted down specific scenarios and any error messages. When you approach your senior team member for help, which of these best describes your approach to the discussion?", "answer": "Hand over your detailed notes and wait for them to provide you with the exact steps to fix the problem."}, {"question": "Your senior team member reviews your detailed notes about the slowness and instead of giving you the exact steps, asks, \\"Based on what you've observed, what's your initial thought or hypothesis about what might be causing this slowness?\\" How would you most likely respond?", "answer": "\\"Based on my observations, I think it might be related to X because Y. Is that a reasonable direction to investigate further?\\""}, {"question": "Your senior team member agrees that your hypothesis about the slowness (e.g., 'it might be related to X because Y') is a reasonable direction. What would be your most proactive next step to investigate this specific area?", "answer": "Research common performance bottlenecks related to 'X' and look for tools or techniques to measure its impact."}, {"question": "You've researched common performance bottlenecks related to 'X' and identified several potential causes and measurement techniques. What would be your most effective next step to narrow down the actual cause of the slowness?", "answer": "Present all your findings to your senior team member and ask them to choose the next step."}, {"question": "You've presented all your findings to your senior team member. After reviewing them, they say, 'Excellent research! Based on what you've found, what do *you* believe is the most promising next step to take to pinpoint the actual cause of the slowness?' How would you most effectively respond?", "answer": "\\"All the findings seem important, so I'd still prefer you to tell me which one to investigate first, as you have more experience.\\""}, {"question": "Your senior team member acknowledges your preference for their guidance but wants to help you build your independent decision-making skills. They ask, 'What specifically makes it challenging for you to identify the *most promising* next step from your research findings on the slowness?' How would you most likely respond?", "answer": "I lack a clear framework or criteria to objectively compare and prioritize the different potential causes and investigation methods."}, {"question": "You've identified that you lack a clear framework to objectively compare and prioritize potential causes for issues. What would be your most proactive next step to start building this crucial skill?", "answer": "Independently research and study established problem-solving methodologies like '5 Whys' or 'Ishikawa diagrams' to understand structured thinking."}]	completed	2026-05-15 12:24:48.045048	2026-05-15 12:27:05.072499	0	\N
e7279fe8-2cfc-437c-80e0-2df8d79a9ca6	Fresher / No Experience	Information Technology - Backend Developer	[{"question": "As someone new to the IT field, imagine you're given a task to understand how a simple web application works behind the scenes. What would be your primary approach to learning and tackling this challenge?", "answer": "Try to break down the application into its core components (database, server, client) and understand their interactions."}, {"question": "After successfully breaking down the web application into its core components, you begin to dive deeper into how the server processes requests. You encounter a specific function or module that seems overly complex and you're struggling to understand its purpose and interaction, even after reviewing it a few times. What would be your primary course of action?", "answer": "Immediately reach out to a more experienced team member for a direct explanation and guidance."}, {"question": "You've received a helpful explanation from your experienced team member about the complex function. While you grasp the main idea, you want to ensure you truly understand it and can apply it independently. What would be your most effective next step?", "answer": "Attempt to build a very small, isolated piece of code that uses or interacts with this specific function to see it in action."}, {"question": "Which of the following best describes your approach to learning new concepts?", "answer": "Watching videos"}, {"question": "You've just finished watching a series of videos that clearly explained a new backend concept or tool. Shortly after, a fellow fresher on your team approaches you, struggling with a task where this newly learned concept could be very helpful. What would be your primary approach to assisting them?", "answer": "Share the video links and suggest they watch them, offering to answer questions afterward."}, {"question": "You shared the video links with your fellow fresher, and they watched them. However, they come back to you with specific questions, indicating they're still finding it hard to connect the concepts to their current task. What would be your most effective next step to help them bridge this gap?", "answer": "Ask them to identify the exact parts of the videos they found confusing and suggest they re-watch those sections."}, {"question": "Despite re-watching the confusing sections, your fellow fresher is still struggling to apply the concept to their task. They express frustration and feel stuck. What would be your most effective next step to help them overcome this hurdle?", "answer": "Suggest they try explaining the concept to you in their own words, so you can identify where their understanding might be breaking down."}, {"question": "Which of the following best describes your approach to learning new concepts?", "answer": "Reading documentation"}, {"question": "Which of the following best describes your approach to learning new concepts?", "answer": "Reading documentation"}, {"question": "You've just implemented a small feature in a backend service, following the documentation and tutorials you've studied. However, when you test it, you notice an unexpected error message appearing intermittently, even though your code seems correct based on what you learned. What would be your primary approach to diagnose this issue?", "answer": "Re-read the relevant sections of the documentation and re-watch the tutorials, looking for any subtle details you might have missed."}]	completed	2026-05-15 09:19:04.59046	2026-05-15 09:22:00.147845	0	\N
ef79758c-5458-4eec-9f86-4529d89af456	Fresher / No Experience	Career Discovery	[{"question": "Imagine you're faced with a completely new and complex problem that you've never encountered before. What's your most likely first step?", "answer": "Research the problem thoroughly online, read articles, and look for existing solutions."}, {"question": "After thoroughly researching a new and complex problem and identifying several potential solutions, what would be your most likely next step?", "answer": "Carefully evaluate the pros and cons of each potential solution, considering their feasibility and potential impact."}, {"question": "After thoroughly researching a new and complex problem and carefully evaluating potential solutions, you've identified one that seems most promising. What would be your most likely next step before moving forward with implementation?", "answer": "Develop a detailed action plan outlining the steps, resources, and timeline required to implement the solution."}, {"question": "You've developed a detailed action plan for your promising solution and started implementing it. Suddenly, you encounter an unexpected major obstacle that wasn't accounted for in your plan, threatening to derail the entire process. What's your most likely next step?", "answer": "Pause implementation, thoroughly analyze the new obstacle, and adapt your plan or seek expert advice to overcome it."}, {"question": "You've successfully analyzed the unexpected obstacle, adapted your plan, and perhaps even sought expert advice. Now, before fully resuming implementation, what's your most likely next step concerning your team or stakeholders?", "answer": "Proactively communicate the obstacle, the revised plan, and the rationale to relevant team members and stakeholders to ensure alignment."}, {"question": "You've proactively communicated your revised plan to your team and stakeholders. However, a key team member expresses strong reservations, believing the new approach has significant flaws. What's your most likely next step?", "answer": "Immediately revert to the original plan or search for an entirely new solution to avoid conflict."}, {"question": "You've proactively communicated your revised plan to your team and stakeholders. However, a key team member expresses strong reservations, believing the new approach has significant flaws. Considering the importance of team alignment and effective problem-solving, what would be your most constructive next step?", "answer": "Re-evaluate your plan independently to see if the team member's concerns have any merit before discussing further."}, {"question": "You've independently re-evaluated your plan and, while making some minor adjustments based on the team member's feedback, you still believe your revised approach is the most effective. How would you now approach the key team member who initially expressed strong reservations to foster alignment and move forward?", "answer": "Schedule a meeting to explain your re-evaluation process, highlight the adjustments made, and collaboratively discuss any remaining concerns they might have."}, {"question": "You've successfully aligned with your key team member on the revised plan, and the team is ready to move forward. However, during the initial stages of implementation, you observe that another team member, who was present during the discussions but didn't voice strong opinions, seems disengaged and is not contributing effectively to their assigned tasks. What's your most likely next step?", "answer": "Directly inform your manager or team lead about the team member's lack of contribution."}, {"question": "You've noticed a team member seems disengaged and isn't contributing effectively to their assigned tasks. Before escalating the issue to your manager, what would be your most constructive first step to address this situation?", "answer": "Continue observing their behavior for a few more days, assuming they might eventually re-engage on their own."}, {"question": "You've observed the disengaged team member for a few days, and their lack of contribution persists. What would be your most constructive next step to address the situation before considering escalation?", "answer": "Focus solely on your own tasks, as it's not your place to intervene directly."}, {"question": "You've observed the disengaged team member for a few days, and their lack of contribution persists, now noticeably impacting the team's progress. While you're hesitant to directly confront them or immediately escalate, you recognize the need for a constructive approach. What would be your most appropriate next step?", "answer": "Discreetly approach the team member and offer support or ask if they're facing any challenges with their tasks."}, {"question": "You discreetly approached the disengaged team member, and they confided in you that they are struggling with a particular aspect of their assigned task, feeling overwhelmed and unsure how to proceed. What would be your most constructive next step to help them and the team?", "answer": "Suggest they immediately inform the manager about their difficulties so the task can be reassigned to someone else."}, {"question": "Your team member has confided in you that they are struggling with a particular aspect of their assigned task, feeling overwhelmed and unsure how to proceed. You want to help them overcome this challenge and contribute effectively. What would be your most constructive next step?", "answer": "Advise them to take a short break to clear their mind, then suggest they try to find online tutorials or resources independently."}, {"question": "You advised your struggling team member to take a break and look for online resources. However, they still seem overwhelmed and unable to make significant progress on their task. What would be your most constructive next step to help them overcome this challenge and contribute effectively?", "answer": "Suggest they reach out to a more experienced team member or a subject matter expert for direct guidance."}, {"question": "You suggested your struggling team member reach out to an experienced colleague for guidance. They did, but the experienced colleague is currently swamped and can only offer limited help, and your team member still feels overwhelmed. What would be your most constructive next step to support them?", "answer": "Offer to sit down with them, review the problem together, and try to break it down into smaller, more manageable parts, even if you don't have all the answers."}, {"question": "You've sat down with your struggling team member, and together you've broken down the problem into smaller, more manageable parts. Despite your collaborative efforts, the core issue remains elusive, and your team member is still feeling stuck and overwhelmed. What would be your most constructive next step?", "answer": "Take ownership of the most difficult part of the task yourself to ensure progress, even if it means extra work for you."}, {"question": "You've taken on the most difficult part of your struggling team member's task to help ensure progress. While doing so, how would you most effectively balance your own workload and ensure your team member still learns and grows from the experience, rather than becoming dependent?", "answer": "Work collaboratively on that difficult section, explaining your approach and guiding them through it, gradually empowering them to take over."}, {"question": "You've successfully helped your team member by collaboratively working on a difficult section of their task. However, this has significantly increased your own workload, and you're starting to feel the pressure, potentially impacting your ability to meet your own deadlines. What's your most constructive next step?", "answer": "Discreetly reduce effort on some of your less critical tasks to balance the load, hoping it won't be noticed."}]	in_progress	2026-05-18 09:07:50.346212	2026-05-18 09:15:16.29761	0	\N
2a8d59ac-cff0-4c01-8d34-e1a6f078a6b6	Fresher / No Experience	Career Discovery	[{"question": "Imagine you're exploring a completely new field or subject for the first time. What approach would you most likely take to understand it better?", "answer": "Read books, articles, and watch documentaries to gather as much information as possible."}, {"question": "After you've gathered a lot of information about a new topic through reading and documentaries, what's your preferred way to deepen your understanding and explore different perspectives?", "answer": "Seek out discussions with friends, family, or mentors to exchange ideas and insights."}, {"question": "After you've learned about a new topic and discussed it with others, what's your most likely next step to truly internalize the knowledge and make it your own?", "answer": "Look for a small project or activity where you can apply some of the new concepts."}, {"question": "When you're working on that small project and hit a roadblock or a problem you can't immediately solve, what's your typical first reaction or approach?", "answer": "Seek advice or help from friends, mentors, or online communities who might have faced similar issues."}, {"question": "You've gathered several pieces of advice for your project roadblock. What's your primary approach to deciding which solution to pursue?", "answer": "I'd carefully compare all the suggestions, thinking about their potential impact and how well they fit my project's overall purpose."}, {"question": "You've carefully chosen and implemented a solution for your project roadblock. If the outcome isn't exactly what you expected, what's your most likely next course of action?", "answer": "Analyze what went wrong with the implemented solution and try to identify the root cause."}, {"question": "You've analyzed what went wrong and identified the root cause of the unexpected outcome. What's your primary approach to getting your project back on track and achieving the desired outcome?", "answer": "Systematically adjust your current solution based on the identified root cause and re-evaluate its effectiveness."}, {"question": "You've systematically adjusted your solution, re-evaluated, and successfully achieved your project's desired outcome. Looking back at the entire journey of tackling that roadblock, what's your most significant focus or next step?", "answer": "Sharing your successful approach and learnings with others who might benefit."}, {"question": "After successfully sharing your approach and learnings, what outcome would you find most rewarding or impactful from that sharing?", "answer": "Receiving appreciation and positive feedback from those who found your insights helpful."}, {"question": "You've received appreciation for your helpful insights. Beyond this positive feedback, what truly drives your motivation to engage in new projects or learning opportunities?", "answer": "The desire to collaborate with others and contribute to a shared team success."}]	completed	2026-05-18 05:56:05.051178	2026-05-18 05:59:43.707878	0	\N
273c66e2-2e34-42c3-95ef-96f16f804397	Fresher / No Experience	Career Discovery	[{"question": "When faced with a new and unfamiliar task, what is your typical first approach?", "answer": "I break it down into smaller, manageable parts and tackle them one by one."}, {"question": "You're working on a team assignment and encounter a challenging problem that you can't immediately solve. What's your typical approach?", "answer": "Research possible solutions, try a few different approaches, and then discuss with a teammate if still unresolved."}, {"question": "You are part of a volunteer team organizing a community event. Two key team members have strong, conflicting ideas about the main activity, causing a standstill. What would be your most constructive approach?", "answer": "Try to understand the core of each person's idea and propose a compromise or a new idea that incorporates elements from both."}, {"question": "You have three containers. One contains only red balls, one contains only blue balls, and one contains a mix of red and blue balls. All three containers are incorrectly labeled. You can only take out and look at one ball from one container. Which container would you choose to take a ball from to correctly label all three containers?", "answer": "The container labeled 'Blue Balls'"}, {"question": "You are tasked with arranging 100 books on a shelf. You can arrange books at a consistent rate of 20 books per hour. If you start at 9:00 AM and take a 15-minute break after every 40 books arranged, what time will you finish arranging all the books?", "answer": "2:15 PM"}, {"question": "You are volunteering to set up a small local event, and just an hour before it starts, you realize there aren't enough chairs for all the expected attendees. What would be your most effective immediate action?", "answer": "Ask some attendees to stand or share chairs, making do with what's available."}, {"question": "You are organizing a free educational workshop for underprivileged children. With limited budget and volunteer time, which area would you prioritize to ensure the workshop has the most positive and lasting impact on the children?", "answer": "Designing highly interactive and hands-on learning activities."}, {"question": "You have a 3-liter jug and a 5-liter jug. How can you measure exactly 4 liters of water, assuming you have an unlimited supply of water and can pour water between jugs?", "answer": "Fill both jugs completely, then pour the water from the 3-liter jug into the 5-liter jug. This will give you 8 liters."}, {"question": "You are planning a small event with three main activities: setting up decorations (1 hour), preparing refreshments (2 hours), and registering guests (3 hours). The refreshments must be prepared before guests can register. Setting up decorations can happen at any time. What is the minimum total time required from start to finish to complete all three activities?", "answer": "4 hours"}, {"question": "You are preparing a presentation for a client. The tasks involved are:\\n1.  Gathering data (2 hours)\\n2.  Creating slides (3 hours) - requires data to be gathered\\n3.  Writing speaker notes (1 hour) - can be done after data is gathered, even while slides are being created.\\n4.  Reviewing and practicing (1 hour) - requires slides and notes to be complete.\\n\\nYou have yourself and one assistant. You both can work on different tasks simultaneously, but only one person can work on a specific task at a time. What is the minimum total time required to complete the entire presentation?", "answer": "6 hours"}]	completed	2026-05-18 06:12:14.793992	2026-05-18 06:16:32.27393	0	\N
7b65919f-15c9-4b48-85be-bc1ccb2215b4	Fresher / No Experience	Career Discovery	[]	in_progress	2026-05-18 07:47:50.686165	2026-05-18 07:47:50.686169	0	\N
0fe16675-5ba8-408a-b7a6-256747b1fadc	Fresher / No Experience	Career Discovery	[{"question": "Imagine you're part of a new team tasked with organizing a community event, and you've never done anything like it before. What's your most likely first step?", "answer": "Start brainstorming ideas independently and prepare to share them with the team."}, {"question": "You've independently brainstormed several ideas for the community event. When the team gathers to discuss everyone's suggestions, what's your main priority?", "answer": "Actively listen to everyone's ideas, identify common themes, and look for ways to combine different suggestions."}, {"question": "After successfully combining several ideas, your team now has 2-3 strong concepts for the community event. Resources (time, budget, volunteers) are limited. What's your primary approach to help the team make the final decision on which concept to pursue?", "answer": "Suggest evaluating each concept against a set of criteria like feasibility, impact, and resource requirements, then scoring them."}, {"question": "After evaluating the concepts, your team has decided on the top-scoring idea for the community event. However, shortly after, you discover a significant, unexpected obstacle (e.g., a key location is unavailable, or a crucial partner pulls out). What's your immediate reaction and proposed next step?", "answer": "Initiate a discussion with the team to brainstorm alternative ways to overcome the obstacle for the chosen concept."}, {"question": "Your team has successfully brainstormed several alternative solutions to overcome the unexpected obstacle for the community event. Now, with limited time remaining, how do you help the team choose the best alternative to move forward?", "answer": "Propose evaluating each alternative against the original event goals and available resources to find the most suitable one."}, {"question": "Your team has decided on the best alternative solution and is now moving into the planning phase for the community event. You realize that two crucial tasks, both essential for the event's success, require the same limited resource (e.g., a specific skill set from a volunteer, a unique piece of equipment) at the exact same time. What's your most effective approach to resolve this conflict?", "answer": "Suggest that the team try to complete both tasks simultaneously, even if it means compromising quality on both."}, {"question": "Your team decided to attempt both crucial tasks simultaneously, even if it meant compromising quality. However, a key stakeholder informs you that compromising quality on *either* of these tasks would severely undermine the entire event's purpose and success. With the limited resource still only able to support one task at high quality at a time, what's your most effective next step?", "answer": "Lead a discussion to prioritize one task as absolutely essential for the event's core function, focusing the limited resource there, and deferring or simplifying the other."}, {"question": "Your team successfully prioritized one critical task, ensuring its high quality, while simplifying or deferring another. A key volunteer, passionate about the simplified task, expresses disappointment, feeling their contribution is undervalued and that the event might suffer. What's your most effective approach to address their concerns?", "answer": "Listen empathetically to their concerns and reiterate the critical importance of the prioritized task for the event's overall success."}, {"question": "Think about a time when you put significant effort into learning a new skill or completing a personal project, but the outcome wasn't what you hoped for, or you received feedback indicating it needed major improvements. What was your primary response?", "answer": "Immediately try to justify your approach and explain why the outcome was reasonable given the circumstances."}, {"question": "Following your experience of justifying your approach, imagine you're working on a team project and a senior team member provides feedback that directly contradicts your initial idea, suggesting a completely different direction. What's your most constructive response?", "answer": "Acknowledge their feedback, then quietly continue exploring your original idea, hoping to find a way to integrate it later."}, {"question": "You've quietly continued exploring your original idea for a project, even after a senior team member suggested a different direction. After some time, it becomes clear that the senior's suggested approach is yielding better results and is gaining more support from the rest of the team. What's your most constructive next step?", "answer": "Double down on your original idea, trying to find new ways to make it work and prove its value."}]	in_progress	2026-05-18 07:56:36.317335	2026-05-18 08:03:24.51059	0	\N
9fc08917-c1e3-4b67-a7b7-e46837ac7de4	Fresher / No Experience	Career Discovery	[]	in_progress	2026-05-18 08:57:15.631153	2026-05-18 08:57:15.631156	0	\N
3419b265-f122-4b37-b5c8-0b22982d6eb7	Fresher / No Experience	Career Discovery	[{"question": "Imagine you're faced with a completely new and complex problem you've never encountered before. How would you typically begin to approach it?", "answer": "I'd try to break the problem down into smaller, manageable parts and tackle them one by one."}, {"question": "You've successfully broken down a complex problem into smaller parts. As you start working on one of these parts, you realize you're completely stuck and can't find a way forward. What would be your most likely next step?", "answer": "Reach out to a peer, mentor, or someone with more experience for their insights or a different perspective."}, {"question": "After reaching out for help, you receive several different suggestions from various people, some of which might even seem to contradict each other. What would be your next step?", "answer": "B) Try out each suggestion one by one, starting with the one that seems most straightforward, to see which one works."}, {"question": "You've tried the \\"most straightforward\\" suggestion, but it only partially solved the problem, or introduced new minor issues. You still have other suggestions from various people, some of which seem more complex or even contradictory. How would you decide your next course of action?", "answer": "Take a step back to analyze all remaining suggestions, considering their potential pros and cons, and try to understand why the first one didn't fully work before choosing the next."}, {"question": "After much effort, you've successfully implemented a solution to the complex problem. A colleague then approaches you and suggests an alternative approach, explaining how it might have been more efficient or robust. What would be your most likely reaction?", "answer": "B) Thank them for their input, but internally feel a bit frustrated that they didn't offer it earlier when you were seeking suggestions."}, {"question": "You've internally felt frustrated by a colleague offering a more efficient solution *after* you've already implemented yours. To prevent similar situations and foster better collaboration in future projects, what would be your most constructive approach?", "answer": "B) Focus on improving your own problem-solving skills so you don't need external suggestions in the first place."}, {"question": "You're part of a new team project that requires a diverse set of skills, and you realize that no single person, including yourself, possesses all the expertise needed for its successful completion. What would be your most effective approach?", "answer": "Proactively identify team members with complementary skills and initiate collaborative efforts to leverage everyone's strengths."}, {"question": "You've initiated a collaborative project, leveraging diverse skills. During a critical phase, a team member whose expertise is vital proposes an approach that you genuinely believe is less effective or efficient than an alternative you have in mind. What would be your most likely course of action?", "answer": "Go along with their suggestion to maintain team harmony, even if you have reservations about its effectiveness."}, {"question": "You decided to go along with a team member's suggestion for the sake of harmony, even though you had reservations. Now, as the project progresses, it becomes clear that their approach is indeed leading to significant problems and delays. What would be your most constructive next step?", "answer": "B) Wait for the team member or the team lead to realize the problem on their own, then offer your solution when asked."}, {"question": "You decided to go along with a team member's suggestion for the sake of harmony, but now the project is significantly behind schedule and key deadlines are at risk because of it. No one has yet asked you for your alternative solution. What would be your most constructive next step?", "answer": "Prepare a detailed report outlining the problems and your alternative solution, then subtly leave it where the team lead might find it."}, {"question": "You subtly left the detailed report for the team lead, hoping they would find it and act. However, a week has passed, the project is still significantly behind, and there's no indication the team lead has seen or acted on your report. The deadline is now critically close. What would be your most constructive next step?", "answer": "Schedule a private meeting with the team lead to directly present your report and discuss the urgency of the situation."}, {"question": "You've had your private meeting with the team lead. They acknowledge the severity of the problem and the validity of your proposed solution. However, they also express concern that you waited until the last minute to directly address the issue, suggesting you should have spoken up sooner. What would be your most likely reaction?", "answer": "Explain that you were trying to maintain team harmony and avoid conflict, which is why you initially tried more subtle approaches."}, {"question": "After reflecting on the entire project situation \\u2013 where you prioritized team harmony, leading to delays and a last-minute intervention \\u2013 what is the most valuable lesson you would take away about effective communication and teamwork in a professional setting?", "answer": "Direct and timely communication of concerns, even if uncomfortable, is crucial for project success and long-term team effectiveness."}, {"question": "You notice a new colleague consistently struggling with a specific task, making small errors that could accumulate into larger issues for the team. Remembering your recent experience about the importance of direct and timely communication, what would be your most constructive approach?", "answer": "Inform your team lead about the colleague's struggles, suggesting they provide guidance."}, {"question": "Your team lead acknowledges your concern about the struggling colleague but is currently overwhelmed with other urgent tasks and asks you to 'keep an eye on things.' Soon after, the colleague makes a mistake that directly impacts a part of the project you are responsible for, potentially delaying your work. What would be your most constructive next step?", "answer": "Re-inform the team lead about this new, specific mistake and its impact on your work, asking them to intervene directly with the colleague."}]	completed	2026-05-18 09:27:37.92702	2026-05-18 09:32:10.082525	0	\N
ab687c08-0166-4c65-bfb0-a9a044b6dbc8	Fresher / No Experience	Information Technology - Frontend Developer	[{"question": "Imagine you're tasked with creating a simple personal portfolio website. Which aspect of this project would you find most exciting and engaging?", "answer": "Ensuring the website is easy to use and navigate for visitors, focusing on user experience."}, {"question": "Following up on your focus on user experience, imagine a visitor to your portfolio website tells you they struggled to find your contact information, even though you thought it was clearly placed. What would be your first step to address this feedback?", "answer": "Ask the visitor specific questions about where they looked and what they expected to find."}]	in_progress	2026-05-21 05:16:39.341222	2026-05-21 05:17:53.472542	4162	0.0014567
ece37bf1-317f-4e2d-8d9a-4a7f6c87efdd	Fresher / No Experience	General - Freshers	[{"question": "You've just started a new role and are assigned a task you've never done before. What's your most likely first approach?", "answer": "I'd immediately search online for tutorials and examples to understand the basics."}]	in_progress	2026-05-21 06:29:24.906352	2026-05-21 06:29:40.740661	2153	0.00075355
def90178-46f0-4f5c-aa42-ed91081adb5a	Fresher / No Experience	General - Freshers	[{"question": "You're assigned a new project or task that you have no prior experience with. What's your most likely first approach?", "answer": "Seek guidance from a team member or mentor to understand the requirements and best practices."}]	in_progress	2026-05-21 06:11:24.468841	2026-05-21 06:11:57.996058	2550	0.0008925
86124447-4fad-49fe-bdf8-1aed5b640af8	Fresher / No Experience	General - Freshers	[{"question": "As a fresher, you'll often encounter new tools or concepts. When faced with something completely new, what's your preferred approach to understanding it?", "answer": "I'd first try to find relevant tutorials or documentation online to learn independently."}]	in_progress	2026-05-21 06:29:56.817188	2026-05-21 06:30:17.450766	2597	0.00090895
2b046c51-dd88-4f05-914a-dca4f967b1bb	Fresher / No Experience	General - Freshers	[{"question": "When faced with a new task or problem you've never encountered before, what's your typical first step?", "answer": "Immediately look for someone experienced to guide me through it."}, {"question": "You've tried to find an experienced person for guidance on a new task, but they are currently unavailable. What would be your next course of action?", "answer": "Wait patiently for them to become available, as their expertise is essential for me to proceed correctly."}]	in_progress	2026-05-21 06:21:17.891973	2026-05-21 06:23:36.113938	4244	0.0014854
60b65568-5492-489c-977c-cab306e22e9b	Fresher / No Experience	Career Discovery	[{"question": "Imagine you're tasked with learning about a completely new field or technology that you know nothing about. How would you typically begin your learning process?", "answer": "Look for practical projects or hands-on tutorials to learn by doing and experimenting."}, {"question": "You're actively engaged in a hands-on project, and you encounter a significant technical challenge that you can't immediately resolve. What's your typical next step?", "answer": "Step back, research alternative approaches, and consult available resources or peers."}, {"question": "You've researched and discussed a technical challenge with peers, and now you have a potential solution. How do you typically approach sharing this solution with your team or mentor?", "answer": "Share it as a well-researched proposal, actively seeking feedback and alternative perspectives."}, {"question": "You've shared your proposed solution with your team, and a colleague offers constructive criticism, suggesting a different path. How do you typically respond?", "answer": "Immediately pivot to their suggestion, assuming they might know better."}, {"question": "You've spent considerable time researching and developing a solution to a problem. When you present it, a respected colleague suggests an entirely different approach, which also seems valid. How do you typically respond in this situation?", "answer": "Thank them for the input, but stick firmly to your original solution, as you've already invested time in it."}, {"question": "You've invested significant time developing a solution for a team project. Just before the final presentation, a teammate discovers a new, demonstrably superior method that would require you to completely rework your part. How do you typically respond?", "answer": "Object to the change, arguing that your current solution is 'good enough' given the time invested."}, {"question": "You've been working on a small project for a few weeks, following a plan you developed. However, progress is slower than expected, and a teammate suggests a completely different approach that seems more efficient but would require you to abandon your current work and start fresh. What is your most likely response?", "answer": "Immediately switch to the new approach, trusting your teammate's judgment without much evaluation."}, {"question": "You've just switched to a new project approach based on a teammate's suggestion, trusting their judgment. A few days later, another colleague proposes yet another different method, claiming it's even more efficient. What's your most likely next step?", "answer": "Politely decline, stating you've just committed to the previous new approach and don't want to switch again."}, {"question": "You're exploring potential career paths, and you receive conflicting advice from two different mentors. One suggests a path known for stability and clear progression, while the other advocates for a more innovative and passion-driven route with higher risk. How would you evaluate this conflicting advice to make an informed choice?", "answer": "I would research the pros and cons of each path independently, looking for objective facts and trends."}, {"question": "You've thoroughly researched two potential career paths, gathering objective facts and trends for each. While you have a good understanding of both, neither path stands out as definitively superior based solely on the data, and both have their own unique challenges and rewards. How would you make your final decision?", "answer": "Continue researching until you find a clear, data-driven reason to choose one path over the other, even if it takes more time."}, {"question": "You've followed your plan to continue researching, but after significant additional effort, the objective data for both career paths still remains balanced, with no clear 'winner.' You're now at a point where a decision needs to be made. How would you proceed?", "answer": "Seek out a highly respected expert or career counselor and rely on their ultimate recommendation."}, {"question": "You've followed the advice of a highly respected expert and committed to a specific career path. After a few months, you find that while the path has its merits, it also presents unexpected challenges and doesn't fully align with your initial expectations. What would be your most likely next step?", "answer": "Immediately start researching entirely new career paths, assuming this one is not for you."}, {"question": "You've decided to explore new career paths because your current one didn't align with expectations. Before fully diving into new options, what would be your most crucial step to ensure you don't repeat similar misalignments?", "answer": "Thoroughly analyze what specific aspects of the previous path caused the misalignment."}, {"question": "After thoroughly analyzing the specific aspects that caused misalignment in your previous career exploration, how would you primarily use these insights to guide your search for a more suitable career path?", "answer": "To articulate a clear vision of your ideal work environment, personal values, and what truly motivates you."}, {"question": "You've articulated a clear vision of your ideal work environment, personal values, and what truly motivates you. To practically test if a potential career path truly aligns with this vision, what would be your most crucial next step?", "answer": "Network extensively with people in that career path, asking specific questions about their daily experiences and company culture."}]	completed	2026-05-18 10:08:00.566497	2026-05-18 10:15:00.900223	40422	\N
5cb4ef00-5b67-4f28-8473-bcf5c69507da	Fresher / No Experience	General - Freshers	[{"question": "As a fresher, you'll often encounter new tools and concepts. When faced with learning a completely new skill or technology, what is your typical first approach?", "answer": "I prefer to dive straight in, experiment, and learn by doing, even if I make mistakes."}]	in_progress	2026-05-21 06:23:36.141003	2026-05-21 06:23:50.514164	2204	0.0007714
e22dfffd-06a5-465f-b6a5-1f07c9a82513	Fresher / No Experience	General - Freshers	[{"question": "Imagine you're given a completely new project or task at work. What's your most likely first approach?", "answer": "Dive straight in and learn by doing, making adjustments as I go."}]	in_progress	2026-05-21 06:27:49.775124	2026-05-21 06:28:04.630055	2105	0.00073675
c75ac0e3-a22c-4c40-9c63-94abe95d10f2	Fresher / No Experience	General - Freshers	[{"question": "When faced with a completely new task or problem, what is your typical first approach?", "answer": "I prefer to research and understand the problem independently before seeking help."}, {"question": "You've spent time researching a new problem independently, but you're still struggling to find a complete solution. What would be your next course of action?", "answer": "Approach a team member or mentor to discuss the problem and ask for their insights."}, {"question": "You've discussed a challenging problem with a team member or mentor and gained valuable insights. What is your primary approach after receiving their input?", "answer": "Reflect on their insights, compare them with my own understanding, and then develop a refined approach."}, {"question": "After developing your refined approach, you begin to implement it, but you encounter an unexpected obstacle that makes the original plan difficult to execute. What is your immediate next step?", "answer": "Try a few different solutions quickly without much planning, hoping one of them works."}, {"question": "You tried a few different solutions quickly without much planning, but none of them fully resolved the unexpected obstacle. What is your next course of action?", "answer": "Immediately consult with a team member or mentor, sharing the obstacle and the outcomes of my quick attempts."}, {"question": "After consulting with your team member/mentor again, sharing your quick attempts and the obstacle, they've provided more specific guidance. What is your primary focus as you move forward?", "answer": "Take time to thoroughly understand the new guidance, analyze why previous quick attempts failed, and develop a detailed, systematic plan."}, {"question": "You've taken the time to thoroughly understand the new guidance, analyzed past attempts, and developed a detailed, systematic plan. As you begin to implement this plan, what is your primary focus?", "answer": "Strictly follow the plan step-by-step without deviation, assuming the detailed analysis has covered all possibilities, and only report once the entire plan is complete."}, {"question": "You've developed a detailed, systematic plan and are now implementing it. Midway through, you encounter a minor discrepancy or a new piece of information that wasn't explicitly accounted for in your initial analysis. What is your primary course of action?", "answer": "Briefly pause to assess the potential impact of the discrepancy. If it seems minor, make a small, logical adjustment to continue, and immediately send a quick message to your team member/mentor about the change."}, {"question": "You've successfully made a minor adjustment to your plan and informed your team member/mentor about it. What is your primary focus after this immediate action?", "answer": "Take a moment to document the discrepancy, the adjustment made, and the lesson learned for future reference."}, {"question": "You've taken the initiative to document a valuable lesson learned from a recent challenge. What is your primary motivation for documenting and potentially sharing such insights within your team?", "answer": "To contribute to the team's collective knowledge base, helping others learn and improve from my experience."}, {"question": "You've shared your documented insights or a suggestion for improvement with your team. Some team members express different opinions or propose alternative ways of doing things. What is your primary reaction?", "answer": "Actively listen to their viewpoints, ask questions to understand their reasoning, and consider how their ideas might improve my own."}, {"question": "After actively listening to different viewpoints and considering various ideas from your team members, how do you typically proceed to finalize a solution or approach?", "answer": "Synthesize the strongest elements from different suggestions, including my own, to formulate a comprehensive and improved approach."}, {"question": "You've successfully synthesized the strongest elements from various team suggestions into a comprehensive and improved approach. When presenting this refined approach to the team, what is your primary goal?", "answer": "To facilitate a final discussion, ensuring all team members feel heard and understand how their input shaped the comprehensive approach."}, {"question": "After a comprehensive approach has been finalized through team discussion and consensus, and it's time to execute, what is your primary focus, especially if some aspects of the final plan differed from your initial preferences?", "answer": "Fully commit to the agreed-upon plan, actively contributing to its success, and putting aside personal preferences."}, {"question": "The team's agreed-upon plan is progressing smoothly, and you are actively contributing to its execution. During this process, you identify a potential opportunity to significantly optimize a part of the workflow or improve an outcome, even though it wasn't explicitly part of the original detailed plan. What is your primary course of action?", "answer": "Immediately implement the optimization if it seems straightforward, assuming it will clearly benefit the project."}]	completed	2026-05-21 06:38:47.11706	2026-05-21 06:42:48.706812	35016	0.0122556
475f9488-7a28-4cdc-9227-a2bffe341830	Fresher / No Experience	General - Freshers	[{"question": "When you encounter a new and unfamiliar task, what is your typical first approach?", "answer": "I immediately start researching online and trying out different solutions."}, {"question": "That's a very proactive approach! When your initial online research and attempts don't immediately solve a new problem, what's your next step?", "answer": "I'd feel frustrated and wait for someone to provide the answer."}, {"question": "It's understandable to feel frustrated when stuck. In a professional setting, if you've tried initial solutions and are feeling frustrated, what would be your most constructive next step *before* someone else provides the answer?", "answer": "Clearly articulate the problem and the steps I've already taken, then ask a colleague or mentor for guidance."}, {"question": "After successfully resolving a challenging task with guidance from a colleague, what's your primary focus regarding the team's overall progress?", "answer": "Share the solution and your learning experience with the team to prevent others from facing the same issue."}, {"question": "After sharing your solution and learning experience with the team, what is your reaction if a colleague suggests an alternative or even more efficient approach?", "answer": "Acknowledge their suggestion, but stick to my method since it already worked."}, {"question": "After acknowledging a colleague's suggestion for a more efficient approach to a task you've already completed, what would be your primary motivation or action?", "answer": "Politely thank them, but prioritize moving on to the next task rather than re-evaluating."}, {"question": "Imagine your team introduces a new software tool or process that promises to significantly improve efficiency for tasks you regularly perform. You've already developed a comfortable and effective way of doing these tasks. What would be your primary reaction?", "answer": "Stick to your current method unless explicitly told to switch, as your way already works."}, {"question": "Your team has decided to standardize on a new software tool for a critical project, and your manager has clearly communicated that everyone must use it to ensure seamless collaboration and project success. Considering your previous comfort with your own method, what would be your primary response?", "answer": "Politely explain your efficiency with the old method to your manager, but agree to switch if there's no other option."}, {"question": "Now that you've agreed to switch to the new software tool for the critical project, what would be your primary approach to ensuring you become proficient and contribute effectively with it?", "answer": "Proactively explore all its features, seek out tutorials, and practice regularly to become an expert user."}, {"question": "Now that you've proactively become proficient with the new software tool, what would be your primary action if you observe a colleague struggling to perform a common task using it?", "answer": "Briefly explain a quick tip or trick you learned, then continue with your work."}, {"question": "After you've given a quick tip to your struggling colleague, what would be your next step if you notice they are still having difficulty performing a common task using the new tool?", "answer": "Suggest they look up tutorials or documentation, as that's how you learned."}, {"question": "If, after you've suggested tutorials, your colleague still appears to be struggling significantly with a common task using the new tool, what would be your most constructive next step?", "answer": "Recommend they seek help from another team member who might have more free time."}, {"question": "If your colleague's continued struggle with the new tool begins to noticeably slow down the team's overall progress on the critical project, what would be your most constructive next step?", "answer": "Privately inform your manager about the situation, explaining the impact on the project and suggesting they intervene."}, {"question": "After you've privately informed your manager about your colleague's struggle impacting the project, what if the manager acknowledges your concern but suggests you continue to monitor the situation, and the problem with your colleague's progress persists?", "answer": "Offer to dedicate some time to sit down with your colleague and provide direct, hands-on assistance."}, {"question": "Having offered to provide direct, hands-on assistance to your struggling colleague, what would be your primary approach to ensure they not only complete the immediate task but also develop a solid understanding of the new tool for future independence?", "answer": "Break down the task into smaller, logical components, explain the 'why' behind each step, and then guide them through practicing each component until they feel confident."}]	completed	2026-05-21 07:02:09.909986	2026-05-21 07:06:20.936973	32955	0.011534250000000001
33df3fe7-1270-418f-ab4b-b27d8481c251	Fresher / No Experience	General - Freshers	[]	in_progress	2026-05-21 08:00:30.91096	2026-05-21 08:00:38.073455	1118	0.00039129999999999997
827d8cf1-d869-4455-8faf-c8bab3b6a1fd	Fresher / No Experience	General - Freshers	[{"question": "Imagine you're faced with a completely new problem or task that you've never encountered before. What is your typical first step to tackle it?", "answer": "I immediately start researching online or looking for resources to understand the problem better."}, {"question": "You've researched a new problem and found several potential solutions online, but some of them seem to contradict each other or offer different approaches. What would be your primary next step?", "answer": "Choose the solution that appears most frequently across different sources, assuming it's the most popular."}, {"question": "You decided to implement the most frequently appearing solution for the new problem. However, after trying it for a while, you notice it's not fully resolving the issue, or it's creating new, unexpected complications. What would be your next course of action?", "answer": "Continue using the chosen solution, assuming it just needs more time to show results."}, {"question": "You've given the chosen solution more time, but the problem persists, and it's clear this approach isn't working. What would be your next primary step?", "answer": "Go back to your initial research and critically re-evaluate all the potential solutions you found earlier."}, {"question": "After deciding to go back and critically re-evaluate all the potential solutions, you now have a clearer picture of their different approaches. What would be your primary method to decide which one is truly the most suitable for your specific problem?", "answer": "Create a detailed comparison matrix, weighing the specific advantages and disadvantages of each solution against the problem's requirements and constraints."}, {"question": "You've meticulously used your comparison matrix to identify what you believe is the most suitable solution for the problem. Before you start implementing it, what would be your primary next step?", "answer": "Immediately begin implementing the solution to see if it works as expected."}, {"question": "You've immediately implemented the solution you identified. After a short period, you observe that while it addresses the original problem, it has introduced new, unexpected complications or hasn't fully met expectations. What would be your primary next step?", "answer": "Analyze the new complications thoroughly to understand their root cause and attempt to modify the current solution."}, {"question": "After analyzing the new complications and implementing modifications to the solution, what is your primary next step to ensure the problem is truly resolved and no new issues have been introduced?", "answer": "Systematically test the modified solution against various scenarios, including edge cases, in a controlled environment."}, {"question": "You've systematically tested the modified solution, and it consistently performs well across all scenarios, effectively resolving the original problem and its complications. What is your primary next step to ensure the successful completion and sustainability of this solution?", "answer": "Inform your supervisor that the problem is resolved and await your next assignment."}, {"question": "You've successfully resolved a complex problem and informed your supervisor. To ensure the long-term benefit of your effort and learning from this experience, what would be your primary next step?", "answer": "Proactively seek out a new, unrelated task to demonstrate your initiative."}, {"question": "You've successfully resolved a complex problem and are ready for your next assignment. Considering the effort and learning involved, what would be the most impactful way to leverage this experience for your team or future projects?", "answer": "Briefly explain the solution to a colleague only if they specifically ask for help with a similar problem."}, {"question": "You've successfully resolved a complex problem and are ready for your next assignment. To ensure the knowledge gained from this experience benefits not just you, but also your team and future projects, what would be your most impactful next step?", "answer": "Wait for a similar problem to arise within the team, then offer your expertise to solve it."}, {"question": "You've successfully resolved a complex problem. While waiting for a similar problem to arise to offer your expertise, you realize that documenting your solution could prevent future issues or help others solve them faster. What is the primary reason to proactively document your solution, even if no one has asked for it yet?", "answer": "To avoid being repeatedly asked the same questions by colleagues."}, {"question": "You've decided to document your solution to a complex problem. Beyond just avoiding repeated questions, what is the most impactful long-term benefit of creating comprehensive and clear documentation for your team and organization?", "answer": "It helps new team members quickly onboard and understand common issues without constant supervision."}, {"question": "You've recognized the importance of creating comprehensive documentation for a complex solution to help new team members onboard quickly. When you start writing this documentation, what would be your primary focus to make it most effective for them?", "answer": "Including every technical detail and internal process, assuming new members will need all information eventually."}]	completed	2026-05-21 08:10:11.642099	2026-05-21 08:51:02.005087	38918	0.0136213
a4c6b9e9-2a5f-41b6-8848-924381b1958c	Fresher / No Experience	General - Freshers	[]	in_progress	2026-05-21 10:10:16.865029	2026-05-21 10:10:16.865032	0	\N
6c1df29d-8b05-4f50-8eb4-17f862a2511d	Fresher / No Experience	General - Freshers	[]	in_progress	2026-05-21 10:11:21.194391	2026-05-21 10:11:21.194396	0	\N
14773ab6-f5d8-413a-b305-b79dc390ed1e	Fresher / No Experience	General - Freshers	[]	in_progress	2026-05-21 10:11:37.85582	2026-05-21 10:11:37.855824	0	\N
1311ce5f-d386-4cf2-9460-7762933313f6	Fresher / No Experience	General - Freshers	[]	in_progress	2026-05-21 10:12:03.560596	2026-05-21 10:12:03.560599	0	\N
f1c1c070-1cf0-42d9-869f-2ce656fac882	Fresher / No Experience	General - Freshers	[]	in_progress	2026-05-21 10:12:17.713601	2026-05-21 10:12:17.713604	0	\N
0273a26c-13fb-414b-9cd1-63808ddff3b1	Fresher / No Experience	General - Freshers	[]	in_progress	2026-05-21 10:55:26.094585	2026-05-21 10:55:26.094589	0	\N
0876ddc4-9d57-45c1-8705-31b1647c4606	Fresher / No Experience	General - Freshers	[]	in_progress	2026-05-21 10:55:32.655391	2026-05-21 10:55:32.655394	0	\N
5ee7788d-8b21-4445-a121-d0503e26ff7a	Fresher / No Experience	General - Freshers	[]	in_progress	2026-05-21 10:58:45.091367	2026-05-21 10:58:51.254748	1230	0.0004305
3cc55a49-ce25-4d44-a21f-bd191b4b981e	Fresher / No Experience	General - Freshers	[]	in_progress	2026-05-21 11:04:27.696603	2026-05-21 11:04:36.504184	1708	0.0005978
3e428559-95fd-47ef-a6b8-1138f2772410	Fresher / No Experience	General - Freshers	[]	in_progress	2026-05-21 11:17:18.231533	2026-05-21 11:17:26.5558	1462	0.0005117
9dd75626-9837-406d-9bf7-c0b840239f5c	Fresher / No Experience	General - Freshers	[{"question": null, "answer": "I want to upgrade my profile"}]	in_progress	2026-05-21 11:26:19.892745	2026-05-21 11:26:47.0373	2561	0.00089635
19d46b0f-4809-4838-b6cf-4263486e00dc	Fresher / No Experience	General - Freshers	[{"question": null, "answer": "I want to be a successful software developer"}, {"question": null, "answer": "I want to be a successful software developer"}, {"question": null, "answer": "I want to be a successful software developer"}, {"question": "You've just joined a new team for a project, and you encounter a problem you don't immediately know how to solve. What is your most likely first step?", "answer": "Immediately ask a senior team member for the solution to avoid wasting time."}, {"question": "You're working on a new task and encounter a technical issue you don't understand. Your assigned mentor is currently unavailable for the next few hours. What is your most appropriate next step?", "answer": "Search for solutions using online resources, documentation, or internal knowledge bases."}, {"question": "You're trying to solve a technical problem and find multiple potential solutions online, some of which seem to contradict each other. What is your most appropriate next step?", "answer": "Systematically try each solution one by one until you find one that works."}, {"question": "You're troubleshooting a software bug and find three potential solutions online. Solution A is simple and widely suggested but has a warning about potential performance impact. Solution B is more complex, involving a code change, but claims to be the most robust. Solution C is a quick fix that bypasses the issue but doesn't resolve the underlying problem. What is your most appropriate next step?", "answer": "Carefully analyze all three solutions, considering their pros, cons, and potential long-term effects, before deciding."}, {"question": "You've successfully resolved a complex technical issue on your own. A few days later, a new teammate approaches you, struggling with a very similar problem. What is your most appropriate response?", "answer": "Offer to sit with them and debug their code together until the issue is resolved."}, {"question": "You're working on two tasks simultaneously. Task X is a minor bug fix that you know how to do, but it's not urgent. Task Y is a new feature request that is due sooner and requires you to learn a new tool. How would you prioritize your work?", "answer": "Complete Task X first to get it out of the way, then start Task Y."}, {"question": "You've been assigned a new project with a tight deadline. A crucial component of this project requires you to use a software tool you've never encountered before. How would you approach this situation?", "answer": "Immediately ask a senior colleague to teach you everything about the tool, relying on their expertise."}, {"question": "You've been assigned a task that requires using a new programming library or framework you've never encountered before. Your team lead is currently in an urgent meeting and won't be available for the next few hours. What is your most appropriate first step?", "answer": "Start by searching for official documentation, online tutorials, and examples to understand the basics yourself."}, {"question": "You have three tasks for the day: Task A is a small bug fix that needs to be deployed by end of day (urgent, known solution). Task B is to research and prototype a new feature for a project due next week (important, requires learning, not immediately urgent). Task C is to attend a mandatory team meeting to discuss project progress (scheduled for mid-day). How would you plan your workday to manage these tasks effectively?", "answer": "Attend the team meeting first to be fully present, then tackle Task A, and dedicate the rest of the day to Task B."}, {"question": "You've planned your workday to focus on learning a new skill for an upcoming project. Suddenly, an urgent, critical bug is reported in a live system that needs immediate attention. You haven't worked on this specific part of the system before, but you have general programming knowledge. What is your most appropriate first step?", "answer": "Inform your team lead about the urgent bug and ask them to assign it to someone more familiar with that system."}, {"question": "You're curious about a complex technical concept (e.g., how a specific data structure works internally) that isn't immediately required for your current tasks but would significantly enhance your foundational knowledge. How would you approach learning it in your free time?", "answer": "Search for a quick summary or a simple explanation online to get a basic idea and move on."}, {"question": "You need to explain a complex technical concept (e.g., how a search engine works at a high level) to a non-technical friend who is curious. What is your most effective approach?", "answer": "Provide a detailed, step-by-step technical explanation, assuming they will grasp it eventually."}, {"question": "You've been assigned a new, moderately complex task that requires understanding a concept you've only briefly encountered. Your team lead, an expert in this area, is in the office and available, but currently focused on their own work. What is your most appropriate first step?", "answer": "Spend some time researching the concept independently using documentation and online resources, then formulate specific questions for your team lead if needed."}, {"question": "You're testing a simple web application you've built. When you click a specific button, nothing happens, and there's no error message displayed in the browser console. What is your most logical first step to investigate this issue?", "answer": "Check if the button's click event handler is correctly defined and linked in the code."}, {"question": "A small software team has 5 members: Alice, Bob, Carol, David, and Eve. You are given the following information:\\n- Alice is faster than Carol.\\n- Bob is slower than David.\\n- Eve is faster than Bob.\\n- Carol is slower than Eve.\\nWho is the fastest among them?", "answer": "David"}, {"question": "You need to explain the concept of 'cloud computing' to a non-technical family member who is curious but has limited technical understanding. What is your most effective approach?", "answer": "Use simple analogies like 'renting a computer in a giant building' or 'storing your photos in a digital locker accessible from anywhere'."}, {"question": "You start your workday with these items:\\n1.  **Mandatory Team Stand-up:** In 30 minutes.\\n2.  **Urgent Bug:** A minor visual bug reported on a live system, needs fixing today. You know how to fix it.\\n3.  **Code Review Request:** A colleague asked you to review their small code change by end of day.\\n4.  **Personal Learning:** You planned to spend an hour learning a new feature in your development environment that could improve your efficiency.\\n\\nHow would you prioritize your morning tasks?", "answer": "Start by learning the new development environment feature to improve efficiency, then attend the stand-up, and address the bug and code review afterwards."}, {"question": "You're in the middle of an online tutorial for a new skill you're eager to learn, which you believe will be valuable for future projects. A new team member approaches you, struggling with a basic setup issue that's preventing them from starting their first task. Your team lead is currently unavailable. What is your most appropriate response?", "answer": "Offer to help them immediately, even if it means pausing your tutorial, and guide them through the setup."}, {"question": "You start your workday with the following tasks:\\n1.  **Critical Customer Bug:** A live website feature is completely broken for a small but important group of users. This needs immediate attention.\\n2.  **Team Lead 1-on-1:** A scheduled meeting with your team lead in 2 hours to discuss your performance and upcoming goals.\\n3.  **Code Review Request:** A colleague needs your review on a small, non-urgent code change by the end of the day.\\n4.  **Personal Skill Development:** You planned to spend an hour learning a new tool that could improve your long-term efficiency.\\n\\nHow would you prioritize your morning?", "answer": "Attend your Team Lead 1-on-1 first to ensure you're prepared, then tackle the Critical Customer Bug, followed by the Code Review and Personal Skill Development."}]	completed	2026-05-21 11:28:47.897583	2026-05-21 11:41:10.043789	74096	0.025933600000000005
044a7adf-80fb-4c28-a240-f77b918a9b96	Fresher / No Experience	General - Freshers	[{"question": "You are working on a group project, and one team member consistently misses deadlines, impacting the overall progress. What would be your first approach?", "answer": "Take over their tasks to ensure the project is completed on time."}, {"question": "Considering your approach to ensure project completion by taking over tasks, what would be your *next* step if you noticed a team member consistently struggling with their assigned work, even after your initial intervention?", "answer": "Schedule a private conversation with the team member to understand their challenges and offer support."}, {"question": "You've had a private conversation and understand your team member's challenges. However, the issues are complex and still significantly impacting their ability to contribute effectively to the project. What would be your next logical step?", "answer": "Inform the project lead about the team member's personal issues so they can handle it."}, {"question": "You've identified that a team member's complex challenges are significantly impacting the project, and you've decided to involve the project lead. When communicating this to the lead, which approach best balances project needs with professional conduct?", "answer": "Detail all the personal issues the team member shared with you so the lead has the full picture."}, {"question": "You've detailed all the personal issues the team member shared with you to the project lead. What is the most likely *negative* outcome of this approach?", "answer": "The team member might feel betrayed and lose trust in you."}, {"question": "After realizing that detailing a team member's personal issues to the project lead could lead to a loss of trust, what would be a more appropriate way to communicate the situation to the lead?", "answer": "Encourage the team member to share their personal challenges directly with the project lead."}, {"question": "You've encouraged your team member to speak directly with the project lead about their challenges. However, they express significant hesitation or discomfort in doing so. What would be your next best step to support both the team member and the project?", "answer": "Offer to accompany them to the meeting with the project lead, providing moral support without speaking for them."}, {"question": "You've offered to accompany your team member to meet the project lead, but they still refuse, and their performance continues to significantly impact the project. What would be your next best course of action?", "answer": "Inform the project lead about the team member's continued refusal and the ongoing impact on the project, without disclosing personal details."}, {"question": "You've successfully navigated a complex team situation, balancing project needs with professional conduct. Reflecting on this experience, what is the most valuable lesson you would take forward regarding effective teamwork and problem-solving?", "answer": "Maintaining open communication with team members is key, even if it means disclosing their personal issues to management."}, {"question": "You've stated that maintaining open communication, even if it means disclosing personal issues to management, is a key lesson. Considering the importance of team cohesion and individual privacy, what is the most critical *negative* consequence of consistently sharing team members' personal challenges with management without their explicit consent?", "answer": "It could lead to a loss of trust and create an environment of fear among team members."}, {"question": "A team member confides in you about a personal challenge affecting their work and explicitly asks for confidentiality. Despite this, their performance is now noticeably impacting the project timeline. What is your most appropriate next step to balance trust and project needs?", "answer": "Inform the project lead about the performance impact and the need for support, carefully avoiding any personal details shared in confidence."}, {"question": "You've informed the project lead about a team member's performance impact and the need for support, carefully avoiding personal details. The project lead then asks you directly, \\"Can you tell me more about *why* they are struggling? Any personal issues I should be aware of?\\" What is your most appropriate response?", "answer": "Provide a general statement like \\"They are going through some personal difficulties\\" without elaborating further."}, {"question": "You are tasked with organizing a small internal workshop for 20 colleagues. You need to ensure everyone has a seat, a pen, and a notepad. You have 3 tables, each seating 8 people. You also have 2 boxes of pens (10 pens per box) and 3 packs of notepads (6 notepads per pack). What is the *first* problem you need to address to ensure the workshop runs smoothly for all 20 colleagues?", "answer": "You don't have enough notepads for everyone."}, {"question": "You've successfully acquired the additional notepads needed for the 20 colleagues. Now, you need to arrange the seating. You have 3 tables, each capable of seating 8 people. To ensure the *most balanced* distribution of colleagues across the 3 tables, how would you arrange them?", "answer": "7 colleagues at two tables, and 6 colleagues at the remaining table."}, {"question": "You are setting up a display for the workshop. You decide to arrange items in a specific pattern: Red, Blue, Green, Red, Blue, Green... If you continue this pattern, what color will the 10th item be?", "answer": "Red"}, {"question": "You are organizing a sequence of tasks for the workshop. The tasks are numbered in a specific order: 1, 4, 7, 10, ... What will be the 6th task number in this sequence?", "answer": "16"}, {"question": "You have three opaque boxes. One box contains only apples, another contains only oranges, and the third contains both apples and oranges. Each box has a label, but *all* labels are incorrect. You are allowed to pick and look at only *one* fruit from *one* box. Which box should you pick a fruit from to be able to correctly label all three boxes?", "answer": "The box currently labeled \\"Apples\\""}]	completed	2026-05-21 11:44:42.584637	2026-05-21 11:53:49.531254	46080	0.016127999999999997
664cd5b3-924a-4e29-b8cf-a573359e3217	Fresher / No Experience	General - Freshers	[{"question": "You've just joined a new team, and you notice a fellow fresher struggling to understand a task that you've recently grasped. What would be your first approach?", "answer": "B) Immediately offer to do a part of their task for them to help them catch up."}, {"question": "Following up on your previous approach, imagine you've helped your teammate by doing a part of their task, but they still seem to struggle with similar issues on subsequent tasks. What would be your next step to ensure they truly grasp the concept?", "answer": "B) Sit down with them to understand their specific difficulties, breaking down the task and explaining the underlying concepts in detail."}, {"question": "Reflecting on your experience helping your teammate, where you initially did part of their task and then later explained concepts in detail, what key lesson did you learn about supporting team members effectively?", "answer": "Understanding the root cause of a teammate's difficulty and empowering them with knowledge leads to more sustainable learning."}, {"question": "Your team frequently encounters a specific type of error in project submissions, causing delays. While individual team members often fix these errors when they appear, they keep reoccurring. Based on your experience, what would be your most effective approach to address this recurring problem?", "answer": "Schedule a team meeting to discuss the errors and remind everyone to be more careful."}, {"question": "Following your team meeting where you reminded everyone to be more careful about the recurring errors, you observe that the errors, though slightly reduced, still persist. What would be your *next* most effective step to tackle this persistent issue?", "answer": "Individually approach team members who frequently make errors to offer personal coaching."}, {"question": "Following your individual coaching efforts, you notice that while the recurring errors have reduced, they still occasionally appear. What would be your *next* most effective step to prevent these errors from happening altogether in the future?", "answer": "B) Suggest to the team lead that a more experienced team member should review all final submissions."}, {"question": "You've suggested a senior review for recurring errors, but the team lead indicates this isn't a sustainable long-term solution due to workload. To truly prevent these errors from happening at their source, what would be your *next* most effective step?", "answer": "Propose creating a standardized template or checklist that highlights common pitfalls for all team members to follow."}, {"question": "You've successfully proposed a standardized template/checklist to prevent recurring errors. What would be your *most effective next step* to ensure this new tool is consistently adopted and used by all team members?", "answer": "B) Present the template in a team meeting, explain its benefits, and demonstrate how to use it."}, {"question": "You've just started using the new template for project submissions, and it's helping reduce errors. However, you've also been assigned a new, complex learning module that requires significant time and focus, and you're finding it hard to balance this with your regular tasks. What would be your *most effective* first step?", "answer": "Try to work extra hours every day to complete everything, even if it means sacrificing personal time."}, {"question": "You've been working extra hours for a few weeks to manage your regular tasks and the new complex learning module. While you're keeping up, you're starting to feel burnt out and less focused. What would be your *next* most effective step?", "answer": "B) Reduce your effort on the learning module to free up time for regular tasks."}, {"question": "You've decided to reduce your effort on the important learning module to cope with burnout. Considering the long-term importance of this module for your career growth, what would be your *most effective* next step to manage your workload and well-being sustainably?", "answer": "Schedule a discussion with your team lead or manager to explain your situation, discuss workload prioritization, and explore potential solutions."}, {"question": "You've successfully managed your workload by discussing it with your manager. Now, you observe that a routine data entry process your team uses is quite manual and prone to small errors, taking up significant time. You believe there might be a more efficient way. What would be your *first* most effective step to address this observation?", "answer": "Discuss your observation with a senior team member to get their perspective and advice."}, {"question": "Following your discussion with a senior team member about the manual data entry process, they encourage you to explore potential solutions. What would be your *next* most effective step to find a more efficient way to handle this routine task?", "answer": "Observe the current process in detail, document its steps, and brainstorm simpler improvements or alternative manual methods."}, {"question": "You've observed and documented the manual data entry process, identifying repetitive steps and common error points, especially when data is manually copied. What would be your *most effective next step* to move towards a more efficient solution?", "answer": "Prepare a comprehensive presentation detailing all inefficiencies and potential cost savings for the management."}, {"question": "You're preparing a comprehensive presentation for management detailing the inefficiencies and potential cost savings of the manual data entry process. Before finalizing and presenting it, what would be your *most effective next step* to ensure your proposal includes actionable and well-considered solutions?", "answer": "Immediately start researching and proposing advanced automation software, assuming it's the ultimate solution."}]	completed	2026-05-21 11:54:03.587878	2026-05-21 11:59:02.464965	45697	0.01599395
b5d2cfa8-77f0-4547-9d8a-0f71d1346de6	Fresher / No Experience	General - Freshers	[{"question": "You are working on a group project, and a team member consistently misses deadlines, impacting the overall progress. What would be your first approach?", "answer": "Report the issue directly to the project lead or manager."}, {"question": "Following up on the previous scenario, after reporting the issue to the project lead, they suggest you first try to communicate directly with your team member about their missed deadlines. How would you approach this conversation?", "answer": "Send a formal email outlining their missed deadlines and the need for immediate improvement."}, {"question": "Following your formal email to your team member about their missed deadlines, they respond by saying they felt targeted and demotivated, and their performance hasn't improved. What would be your next step?", "answer": "Schedule a brief, informal one-on-one meeting to understand their perspective and offer support."}, {"question": "Reflecting on the scenario where your formal email led to a team member feeling demotivated, what is the most important lesson you would apply to future team communications?", "answer": "It's essential to understand a team member's situation and perspective before choosing a communication approach."}, {"question": "Based on your recent experience with team communication, when you join a new team or project, what is the most important step you would take to ensure effective collaboration and prevent potential misunderstandings?", "answer": "Proactively seek to understand each team member's working style and communication preferences."}, {"question": "After successfully understanding your new team's communication styles, you notice that during brainstorming sessions for a new project, some team members are very quiet and don't share their ideas openly, even though you suspect they have valuable input. What would be your most effective approach to encourage their participation?", "answer": "Suggest a method where ideas are first written down individually and then discussed in smaller groups or anonymously."}, {"question": "Your team is tasked with developing a truly innovative solution, but initial brainstorming sessions are yielding only conventional ideas. Building on your understanding of effective collaboration, what structured approach would you propose to encourage more 'out-of-the-box' thinking?", "answer": "Ask each team member to individually research and present a 'wild card' idea from a different industry."}, {"question": "After successfully generating many innovative ideas using your proposed 'wild card' approach, your team now has a wealth of potential solutions. However, you have limited time and resources. What would be your most effective approach to prioritize which ideas to pursue first?", "answer": "Conduct a quick team vote to select the most popular ideas."}, {"question": "Following your team's vote on the most popular ideas, the project lead asks for a more robust justification, considering feasibility, potential impact, and resource requirements for each. What would be your most effective next step?", "answer": "Create a simple scoring matrix with predefined criteria like 'Impact', 'Feasibility', and 'Resource Needs' to objectively evaluate and rank the ideas."}, {"question": "After presenting your scoring matrix and the ranked ideas to the project lead, they agree with the top two choices but ask you to prepare a brief summary for senior management. This summary needs to highlight the *key reasons* why these two ideas were selected over others. What would be your primary focus in preparing this summary?", "answer": "Detailing the specific scores from the matrix for each criterion (Impact, Feasibility, Resources) for the top two ideas."}, {"question": "You are organizing a small event and need to arrange 24 chairs in rows. Each row must have the same number of chairs, and there must be at least 3 chairs per row but no more than 10 chairs per row. How many different ways can you arrange the chairs?", "answer": "3 ways"}, {"question": "If 'APPLE' is coded as 'BQQMF' and 'GRAPE' is coded as 'HSBQG', how would 'MANGO' be coded using the same logic?", "answer": "NBOGP"}, {"question": "What comes next in the sequence: 3, 5, 9, 15, 23, ?", "answer": "33"}, {"question": "If 'CAT' is coded as '3120', and 'DOG' is coded as '4157', how would 'FOX' be coded using the same logic?", "answer": "61523"}, {"question": "Consider the following statements:\\n1. All dogs are mammals.\\n2. Some mammals are pets.\\n3. All pets are friendly.\\n\\nWhich of the following conclusions can be logically drawn?", "answer": "Some dogs are pets."}]	completed	2026-05-28 09:04:36.229527	2026-05-28 09:10:09.679016	40652	0.0142282
3123711d-db50-4eda-83c4-e88d1af9873d	Fresher / No Experience	General - Freshers	[{"question": "Imagine you're part of a new team working on a project. During a brainstorming session, one team member proposes an idea that you believe is not feasible or well-thought-out. How would you most likely respond?", "answer": "Immediately point out the flaws in their idea and suggest a better approach."}, {"question": "You've just presented an idea to your team, and a colleague immediately points out several flaws, similar to how you might have responded in the previous scenario. How would you most likely react?", "answer": "Listen carefully to their points, ask clarifying questions, and consider their perspective."}, {"question": "You've identified a recurring inefficiency in a team process and have a clear, better solution. How would you most effectively present this to your team or supervisor?", "answer": "Wait for a team meeting, then clearly state the problem and your solution, explaining why it's superior."}, {"question": "You've developed a new, more efficient way to complete a routine task, but a senior team member, who has been doing it the old way for years, is hesitant to change. How would you most effectively approach this situation?", "answer": "Respect their experience and continue with the old method, hoping they'll eventually see the inefficiency."}, {"question": "You've identified a potential improvement to a team process that could save significant time, but your team lead seems too busy to give it immediate attention. What would be your next step?", "answer": "B. Implement the change on your own tasks to demonstrate its effectiveness without formal approval."}, {"question": "You successfully implemented a new method for your tasks, demonstrating its efficiency. However, a colleague later mentions that this change inadvertently created a minor bottleneck or extra step for their part of the process. How would you most effectively address this?", "answer": "Explain the benefits of your new method and suggest they adapt their workflow to accommodate it."}, {"question": "Your team is working on a project with a tight deadline. You've completed your part, but a critical subsequent task depends on a colleague who seems to be struggling and falling behind, potentially jeopardizing the entire project timeline. What would be your most likely response?", "answer": "Offer to help your colleague directly, even if it means temporarily pausing your own next task."}, {"question": "Following your successful implementation of a new method for your tasks, which initially caused a minor bottleneck for a colleague, you've now had a chance to reflect. Your team lead suggests finding a way to integrate your efficient method without negatively impacting anyone else's workflow. What would be your most effective approach?", "answer": "Schedule a meeting with the affected colleague to brainstorm solutions together, focusing on how to adapt the overall process collaboratively."}, {"question": "Your team is working on a new project, and during a critical planning phase, two team members present conflicting approaches for a key task. Both ideas have strong points and potential drawbacks, and the discussion is reaching a stalemate. As a fresher, how would you most effectively contribute to moving the team forward?", "answer": "Research similar projects or best practices to find an external, objective solution to present to the team."}, {"question": "You've been assigned to research a new software tool for your team. You find a lot of information online, including conflicting reviews and complex technical details. Your supervisor asks for a concise summary by the end of the day. What is your most effective approach?", "answer": "Focus only on the positive reviews and features, presenting the tool in the best possible light to impress your supervisor."}, {"question": "You've been tasked with researching two different approaches to solve a technical problem. Approach X is faster to implement but has a known security vulnerability that requires extra mitigation steps. Approach Y is slower to implement but inherently more secure. Your team is under pressure to deliver quickly. How would you most effectively present your findings to your team lead?", "answer": "Present a comprehensive overview of both approaches, clearly detailing the pros and cons of each, including the security vulnerability of Approach X and the time investment for Approach Y."}, {"question": "You've successfully implemented a new process that you designed, and it's been praised for its initial efficiency. However, after a few weeks, you discover a subtle but significant flaw in the process that could cause issues in the long term, though no one else has noticed it yet. What would be your most effective next step?", "answer": "B. Immediately prepare a detailed report on the flaw, including its potential impact and proposed solutions, and present it to your supervisor."}, {"question": "You've been working on a small internal tool for your team, and it's been well-received initially. However, while reviewing the code, you discover a minor bug that, under specific rare conditions, could lead to incorrect data being displayed. No one has reported it yet, and fixing it would require a small amount of extra work and a re-deployment. How would you most effectively handle this situation?", "answer": "Fix the bug immediately and silently deploy the update without mentioning it, as it's minor."}, {"question": "You've completed a small report for your team lead, summarizing some data. Just before submitting it, you notice a minor calculation error in one section. It doesn't drastically change the overall conclusion, but it's technically incorrect. Your team lead is very busy and expects quick, accurate submissions. What would be your most effective next step?", "answer": "Submit the report as is, assuming the error is too small to be noticed or to matter significantly."}, {"question": "You're asked to quickly review a colleague's draft of a short, data-driven presentation before they finalize it for a team meeting. You notice a minor inconsistency in one of the charts \\u2013 a label is slightly off, or a percentage doesn't add up to exactly 100% due to rounding, though the overall trend and conclusion remain valid. Your colleague is rushing to finish. What would be your most effective next step?", "answer": "Briefly point out the minor inconsistency to your colleague and offer to help them fix it quickly."}, {"question": "You're asked to quickly review a colleague's draft of a short, data-driven presentation before they finalize it for a team meeting. You notice a minor inconsistency in one of the charts \\u2013 a label is slightly off, or a percentage doesn't add up to exactly 100% due to rounding, though the overall trend and conclusion remain valid. Your colleague is rushing to finish. What would be your most effective next step?", "answer": "Briefly point out the minor inconsistency to your colleague and offer to help them fix it quickly."}, {"question": "You're asked to quickly review a colleague's draft of a short, data-driven presentation before they finalize it for a team meeting. You notice a minor inconsistency in one of the charts \\u2013 a label is slightly off, or a percentage doesn't add up to exactly 100% due to rounding, though the overall trend and conclusion remain valid. Your colleague is rushing to finish. What would be your most effective next step?", "answer": "Quietly correct the inconsistency yourself in the draft to ensure accuracy without bothering your colleague."}, {"question": "You're asked to quickly review a colleague's draft of a short, data-driven presentation before they finalize it for a team meeting. You notice a minor inconsistency in one of the charts \\u2013 a label is slightly off, or a percentage doesn't add up to exactly 100% due to rounding, though the overall trend and conclusion remain valid. Your colleague is rushing to finish. What would be your most effective next step?", "answer": "Quietly correct the inconsistency yourself in the draft to ensure accuracy without bothering your colleague."}, {"question": "You're asked to quickly review a colleague's draft of a short, data-driven presentation before they finalize it for a team meeting. You notice a minor inconsistency in one of the charts \\u2013 a label is slightly off, or a percentage doesn't add up to exactly 100% due to rounding, though the overall trend and conclusion remain valid. Your colleague is rushing to finish. What would be your most effective next step?", "answer": "Briefly point out the minor inconsistency to your colleague and offer to help them fix it quickly."}]	completed	2026-05-27 05:28:19.903515	2026-05-27 05:33:26.858769	47252	0.0165382
9f9a6dbe-8211-4408-8763-57cdb54797e8	Entry Level (1-2 years)	Information Technology - Frontend Developer	[{"question": "You're working on a team project, and you discover a bug in a shared UI component that another team member recently contributed. This bug is impacting your feature. What is your first course of action?", "answer": "Report the bug to your team lead or the original author and wait for them to provide instructions or a fix."}, {"question": "The bug you reported in the shared UI component is still unresolved after a day, and your feature development is blocked. What would be your next step?", "answer": "Ping the team lead or the original author again for an update and ask if there's anything you can do to help."}, {"question": "The bug in the shared UI component is still blocking your feature, and the original author is now out of office for the day. Your team lead suggests you try to make progress on your own. What would be your *first* step?", "answer": "Look for an alternative existing UI component or library that could serve as a temporary replacement."}, {"question": "You've found an alternative UI component, but it requires minor styling adjustments and a small data transformation to fully integrate into your feature. What would be your *first* step?", "answer": "Document the required adjustments and present them to your team lead, asking for their input on the best approach or if a senior developer can assist."}, {"question": "Your team lead reviews your documentation for the alternative component and says, \\"Good job identifying these. For the styling, try to match our existing design system. For the data transformation, a simple utility function should work. Go ahead and implement it, and let me know if you hit any major roadblocks.\\" What would be your *first* step in proceeding?", "answer": "Schedule a quick meeting with a senior developer to get a detailed walkthrough of how to implement the styling and data transformation."}, {"question": "You've scheduled the meeting with the senior developer, but it's not until tomorrow afternoon. You have a few hours free this morning. What would be the most productive use of your time *before* the meeting to prepare for implementing the styling and data transformation?", "answer": "Thoroughly review the existing design system documentation and look for examples of similar data transformations in the codebase."}, {"question": "You've thoroughly reviewed the existing design system documentation and looked for examples of similar data transformations in the codebase. You still have a few hours free this morning before your scheduled meeting with the senior developer tomorrow afternoon. What would be the *most productive* next step to maximize your learning and preparation for implementing the styling and data transformation?", "answer": "Compile a detailed list of specific questions and potential solutions based on your review, ready to discuss with the senior developer."}, {"question": "You've compiled your detailed list of questions and potential solutions, and you still have a few hours free this morning before your scheduled meeting with the senior developer tomorrow afternoon. What would be the *most productive* next step to further your progress on the styling and data transformation tasks?", "answer": "Reach out to the senior developer via chat or email to see if they can quickly answer a few of your most pressing questions before the meeting."}, {"question": "The senior developer quickly responds to your chat, providing concise answers to two of your most pressing questions. They also suggest a specific documentation link for the styling and a common utility function pattern for the data transformation. You now have about an hour left before lunch, and the meeting is still tomorrow afternoon. What would be your *first* step?", "answer": "Thoroughly review the suggested documentation and utility function pattern, trying to understand the underlying principles."}, {"question": "You've thoroughly reviewed the suggested documentation for styling and the utility function pattern for data transformation. You have about an hour left before lunch, and your meeting with the senior developer is still tomorrow afternoon. What would be your *first* step to practically apply this new knowledge and make progress?", "answer": "Start writing pseudocode for the utility function and outline the styling changes in a separate document."}, {"question": "You've started implementing the utility function based on your pseudocode and the senior developer's guidance. You encounter a syntax error or a logical issue that you can't immediately resolve after a quick online search. You still have about 30 minutes before lunch. What would be your *first* step?", "answer": "Spend the remaining 30 minutes trying various random fixes, hoping one will work, to show initiative."}, {"question": "You've spent 30 minutes trying various random fixes for a syntax error or logical issue without success, and it's now time for lunch. You still have a meeting with the senior developer tomorrow afternoon. What would be your *most productive* first step *after* lunch to resolve this issue?", "answer": "Take a break, then systematically review the relevant code, documentation, and examples, trying to understand the error's root cause."}, {"question": "You've systematically reviewed the code and documentation, and while you have a better understanding of the error, you haven't fully resolved the syntax or logical issue. You still have the meeting with the senior developer tomorrow afternoon. What would be your *first* step in preparing for that meeting to ensure you get the most out of it regarding this specific issue?", "answer": "Focus on other tasks, assuming the senior developer will walk you through the solution from scratch during the meeting."}, {"question": "Given that you still have an unresolved syntax or logical issue and a meeting with a senior developer tomorrow afternoon, what would have been the *most effective* way to prepare for that meeting to maximize your learning and problem-solving?", "answer": "Focus on other tasks to ensure you have other progress to show, and let the senior developer guide the discussion on the bug."}, {"question": "You have an unresolved syntax or logical issue, and a meeting with a senior developer is scheduled for tomorrow afternoon. Reflecting on how to maximize your learning and problem-solving from this meeting, which of the following would be the *most effective* way to prepare and engage?", "answer": "Focus on other tasks to ensure you have other progress to show, and let the senior developer guide the discussion on the bug."}]	completed	2026-05-28 11:13:52.934124	2026-05-28 11:24:52.822847	51993	0.01819755
e81b56bd-edf8-4140-8c23-cdb510acb968	Fresher / No Experience	General - Freshers	[{"question": "You are part of a small team working on a college project. One team member consistently misses deadlines, impacting the overall progress. What would be your first approach?", "answer": "Take over their tasks to ensure the project is completed on time."}, {"question": "Following your decision to take over a struggling team member's tasks, you notice the project is on track but the team member's engagement hasn't improved. What is your next most important consideration?", "answer": "Scheduling a private conversation with the team member to understand their challenges."}, {"question": "You've scheduled a private conversation with the team member who has been missing deadlines. What is your primary goal for this discussion?", "answer": "To actively listen and understand their perspective, challenges, or any underlying issues they might be facing."}, {"question": "You've actively listened to your team member and now understand their challenges. What is the most constructive next step you would take during this conversation?", "answer": "Suggest a few specific strategies or tools they could use to improve their situation."}, {"question": "You've suggested specific strategies to your team member to help them improve their performance. What is your most important next step to ensure their progress and continued team success?", "answer": "Trust them to implement the strategies independently and only intervene if deadlines are missed again."}, {"question": "Despite your suggested strategies, the team member is still struggling, and the project deadline is now very close. What is your most important next step?", "answer": "Offer to take over their remaining critical tasks to ensure the project is completed on time."}, {"question": "You successfully completed the project by taking over your struggling team member's critical tasks. Looking back, what is the most significant potential drawback of this approach for the team's long-term development?", "answer": "The struggling team member may not have fully learned how to manage similar challenges independently."}, {"question": "Reflecting on the situation where you repeatedly took over tasks for a struggling team member, what is the most important lesson you would apply to a *future* similar team project?", "answer": "Focus more on documenting the team member's failures for future reference."}, {"question": "You mentioned that in a future similar project, your most important lesson would be to 'focus more on documenting the team member's failures for future reference.' What is the most significant potential negative consequence of this specific approach on team morale and future collaboration?", "answer": "It could lead to an excessive amount of paperwork and administrative burden for the team."}, {"question": "Given your concern about 'excessive paperwork' from documenting team member failures, which of the following is a *more critical* potential negative consequence for team morale and future collaboration that you might have overlooked?", "answer": "It might make it harder to find storage space for all the documents."}, {"question": "You've decided to document a struggling team member's failures for future reference. If this team member were to accidentally discover your detailed documentation about their performance issues, what would be the most likely immediate impact on your working relationship and their motivation?", "answer": "They might feel betrayed, demotivated, and less trusting of you and the team."}, {"question": "Given your understanding that documenting a team member's failures could lead to feelings of betrayal and demotivation, what would be a more constructive and supportive approach to manage a struggling team member in a future project, while still ensuring accountability?", "answer": "Schedule regular, private check-ins to offer support, discuss progress, and collaboratively adjust strategies."}, {"question": "Despite your regular check-ins and collaborative strategy adjustments, the team member is still significantly struggling, and the project deadline is now critically close. What is your most appropriate next step to ensure project success while continuing to support the team member?", "answer": "Inform the team lead or manager about the situation, providing context and seeking their guidance on how to proceed."}, {"question": "You've decided to inform your team lead or manager about the struggling team member and the critically close project deadline. What is your most important responsibility during this discussion with the lead?", "answer": "Focus on how your own efforts to help were unsuccessful."}, {"question": "You've decided to inform your team lead about a struggling team member. Beyond mentioning your own efforts, what is the *most crucial* information you should prioritize sharing with your team lead to ensure an effective resolution?", "answer": "The specific impact the team member's struggles are having on the project timeline and deliverables."}]	completed	2026-05-30 07:39:00.353945	2026-05-30 07:42:14.868603	34191	0.011966849999999998
\.


--
-- Data for Name: department_jobs; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.department_jobs (id, name, department_id) FROM stdin;
bb2f2a27-f624-40a9-9d22-cf75bcfe86a4	Benefits Administrator	2b890dca-cda8-4d9d-b0e8-b093e371bbeb
48d5f515-784f-4f85-a75f-0c76b93670ee	Compensation Manager	2b890dca-cda8-4d9d-b0e8-b093e371bbeb
1cca6135-f307-43f5-b956-2de8ecfa7e21	Total Rewards Manager	2b890dca-cda8-4d9d-b0e8-b093e371bbeb
e4233f65-0a4a-4237-bc11-16f066139d28	Payroll Executive	286647e9-abad-4196-afc0-7df8922cf632
dfb160e8-2aca-4625-93a3-ed5037cd076b	Payroll Specialist	286647e9-abad-4196-afc0-7df8922cf632
137355dc-ca1f-4d29-91f4-2409bb16dd42	Payroll Manager	286647e9-abad-4196-afc0-7df8922cf632
b85e97ca-ff0f-40d3-ba5d-cfe32ff2adf3	Compensation Processor	286647e9-abad-4196-afc0-7df8922cf632
f59de41f-1df8-4d1e-98fb-a94d93d722e3	Salary Administrator	286647e9-abad-4196-afc0-7df8922cf632
b2806416-400e-4acb-a3e2-42e4fd90f1f1	Operations Executive	c65513da-8aad-4132-a33e-a156f3c7b02c
ae8f00a3-d273-4f06-8a63-7f27959e5583	Business Operations Analyst	c65513da-8aad-4132-a33e-a156f3c7b02c
2ae3fa8d-9211-4f6d-acf5-113ce505ba0d	General Manager	0be2a2d9-e20b-4f17-8f64-48745644426d
eec6a122-2e15-4a3d-8336-2fde04a444a0	Operations Manager	0be2a2d9-e20b-4f17-8f64-48745644426d
2f81932e-2c56-4649-97f8-66eab85b7c85	Business Manager	0be2a2d9-e20b-4f17-8f64-48745644426d
2a1df87d-55c7-425a-bbc4-18d075c4410d	Assistant Manager	0be2a2d9-e20b-4f17-8f64-48745644426d
23f7fef8-d283-473d-a070-d704fcd85935	Management Trainee	0be2a2d9-e20b-4f17-8f64-48745644426d
e91c1fbe-7bda-43e6-a945-2f5cf826540c	Chief Executive Officer (CEO)	4791dd21-36c7-455b-9aa9-93535535bbff
b211964f-6052-4ebd-bc7b-8231172d84cc	Chief Operating Officer (COO)	4791dd21-36c7-455b-9aa9-93535535bbff
578eb4f5-bab4-410a-a141-d9a2726e6f75	Chief Financial Officer (CFO)	4791dd21-36c7-455b-9aa9-93535535bbff
131749ea-828a-4490-894a-6e3d45052a9f	Executive Assistant	4791dd21-36c7-455b-9aa9-93535535bbff
682e1466-6082-4d40-8c46-5278ad21a9ec	Office Coordinator	4791dd21-36c7-455b-9aa9-93535535bbff
e71fbf40-93b2-4379-9813-7f13971bb505	Software Engineer	7eb97478-ab30-4ca9-82aa-3fac952b60e8
340b9e12-d95f-4fb0-a497-f5b9a2c9728e	Senior Software Engineer	7eb97478-ab30-4ca9-82aa-3fac952b60e8
6f7fdfc6-6e7f-40d6-a578-82221270ba05	Backend Developer	7eb97478-ab30-4ca9-82aa-3fac952b60e8
9fdf00df-0dad-423c-b33b-bc94f8aafe34	Full Stack Developer	7eb97478-ab30-4ca9-82aa-3fac952b60e8
078d4052-90e4-476a-8382-94f2f7dd47c5	Application Developer	7eb97478-ab30-4ca9-82aa-3fac952b60e8
9b90b2aa-0206-4b5e-871a-adb6fd68a02d	Frontend Developer	30ed85cd-9da7-4dcf-8410-b412b9569f6e
c7a8f9a4-db42-414e-aacc-4e53200d02c6	Web Developer	30ed85cd-9da7-4dcf-8410-b412b9569f6e
2bc0ebfc-c6dc-4382-a03f-dff7c914f281	React Developer	30ed85cd-9da7-4dcf-8410-b412b9569f6e
fc7d2bb8-8bb5-45b1-94a4-2592ccb88946	Angular Developer	30ed85cd-9da7-4dcf-8410-b412b9569f6e
048b1f53-012d-48e5-9f9b-f3cc5743c3ef	PHP Developer	30ed85cd-9da7-4dcf-8410-b412b9569f6e
2fb2ac79-16ae-4d8d-952d-0f47ae069012	iOS Developer	8ee1b7a5-f46a-48a5-801b-964b39a62294
8b4d4b3e-5035-4501-82d7-d8632b70732f	Strategy Manager	0a565916-be74-4044-a363-91a6b3a3da79
c2cf3161-f2ce-47ac-8e41-d10769f54700	Business Strategy Analyst	0a565916-be74-4044-a363-91a6b3a3da79
62dc1f4f-7036-429e-b9e6-2e61547e2f89	Strategic Planner	0a565916-be74-4044-a363-91a6b3a3da79
0e7707b5-bead-4d30-9b11-96e37c85b254	Corporate Strategist	0a565916-be74-4044-a363-91a6b3a3da79
e8045c24-ce87-47e2-b303-06ebb6cd2871	Growth Strategy Consultant	0a565916-be74-4044-a363-91a6b3a3da79
e8d89135-ccf2-435a-be5e-7a449846b79b	Corporate Planning Manager	281e940b-c398-4730-a2d7-cf30bc54d5ae
b4db6603-4af7-4f9d-9a37-414b14427e36	Business Planning Analyst	281e940b-c398-4730-a2d7-cf30bc54d5ae
e54f2f8a-358d-45dc-b81e-c7725652e4e1	Planning Coordinator	281e940b-c398-4730-a2d7-cf30bc54d5ae
ee83cc69-c2cd-4891-80d8-808b6a7ccb43	Forecasting Analyst	281e940b-c398-4730-a2d7-cf30bc54d5ae
f6a611b2-0ba5-424a-af52-4061fa5dc724	Budget Planning Manager	281e940b-c398-4730-a2d7-cf30bc54d5ae
4ae6b83b-6305-4341-ade3-ae3ca5574719	Board Secretary	df00a405-c5da-4dd7-a086-8388d54c2325
2bba8be1-6d02-4b52-83ad-68fb969cd19f	Governance Coordinator	df00a405-c5da-4dd7-a086-8388d54c2325
d23ff8e4-c8ab-4d2a-852d-22d0055b856d	Operations Coordinator	c65513da-8aad-4132-a33e-a156f3c7b02c
b1babe41-aa09-4186-bbc4-6fbfd592b514	Operations Supervisor	c65513da-8aad-4132-a33e-a156f3c7b02c
40de3bf5-2f0d-448a-9c2c-e642853f9482	Process Manager	83f9c3b8-5f99-4fd2-9f6c-ce7adf809803
47b058cd-5179-4ed7-89cf-75fe3936a860	Business Process Analyst	83f9c3b8-5f99-4fd2-9f6c-ce7adf809803
19b1af41-cb05-42d1-8c98-ebf80a7314ab	Process Improvement Specialist	83f9c3b8-5f99-4fd2-9f6c-ce7adf809803
7ee9bd78-826f-4444-9cda-7b50b19832d4	Lean Consultant	83f9c3b8-5f99-4fd2-9f6c-ce7adf809803
f4d1df27-b68d-48b5-a3d2-58b61891680a	Process Coordinator	83f9c3b8-5f99-4fd2-9f6c-ce7adf809803
ddfe356b-0365-4b96-b0b8-27df18aaecb4	Service Delivery Manager	6a171a6c-12b9-44ac-a7e5-f267a3b44810
f98892d1-fc2b-4642-8937-7be990d7ad00	Service Delivery Executive	6a171a6c-12b9-44ac-a7e5-f267a3b44810
f79c7448-89a6-4034-92e1-f452ccc33359	Client Delivery Manager	6a171a6c-12b9-44ac-a7e5-f267a3b44810
4da8199d-be41-4d4e-abfe-d453bceba39c	Delivery Coordinator	6a171a6c-12b9-44ac-a7e5-f267a3b44810
b47dfc9f-d305-482a-a5eb-406132e84d38	Service Operations Analyst	6a171a6c-12b9-44ac-a7e5-f267a3b44810
7b096887-948d-4d10-bca5-5442dc3ccbf1	Resource Manager	01cb55d6-64ea-4cc0-aa92-465417c5bcf6
02125ce0-a6f1-4513-af78-f29ddd44f43d	Workforce Planner	01cb55d6-64ea-4cc0-aa92-465417c5bcf6
c0e4712d-207a-405b-8129-e52e0abc38ee	Capacity Planning Analyst	01cb55d6-64ea-4cc0-aa92-465417c5bcf6
f466d90f-33ad-47eb-8c4e-04cdf234de7c	Staffing Coordinator	01cb55d6-64ea-4cc0-aa92-465417c5bcf6
748773eb-983c-4866-b33b-5ec71a399e80	Resource Allocation Specialist	01cb55d6-64ea-4cc0-aa92-465417c5bcf6
24fb061d-69fd-4af0-8ded-8f4cacb249c1	Administrative Officer	1c6a31f1-6543-4a49-87e0-ff02eb88d048
3f555ea5-a6e9-4245-bf54-436586e162e5	Office Administrator	1c6a31f1-6543-4a49-87e0-ff02eb88d048
b275be7c-7524-47a6-b63d-0d7f90491d4c	Enterprise Risk Specialist	bf318e26-ee76-41f9-ad4f-0d97cca4c13b
7d2d376c-3e3e-4b0d-af13-7db15a044e06	Operational Risk Analyst	bf318e26-ee76-41f9-ad4f-0d97cca4c13b
3fa4d33f-f3b1-4788-8bf5-28e5e43be1cb	Credit Risk Manager	bf318e26-ee76-41f9-ad4f-0d97cca4c13b
ee0393c5-fdca-49b2-a2f3-911084a78ce9	Corporate Governance Officer	a137060a-824f-4cb3-968e-57998cd8d136
aae8353c-58c9-419d-a688-fb0450584d19	Governance Analyst	a137060a-824f-4cb3-968e-57998cd8d136
ee7ed316-914d-428b-9d52-414b294549c9	Infrastructure Engineer	d88005e4-0477-4a66-8098-5ce139977a52
f440b514-89b1-4e11-abe8-0a840dcb9a52	Systems Engineer	d88005e4-0477-4a66-8098-5ce139977a52
24d6dd73-4cf5-4829-9600-75693e25768e	Sales Executive	72b81592-f48a-4753-87aa-25142749660f
0514fcde-a54b-4e89-95a5-5c37cdeaef02	Sales Manager	72b81592-f48a-4753-87aa-25142749660f
1a97e4d1-e6c4-4718-b5e2-d47490cd1649	Regional Sales Manager	72b81592-f48a-4753-87aa-25142749660f
730702a6-b74f-488e-ae73-b10198b97fc3	Territory Sales Officer	72b81592-f48a-4753-87aa-25142749660f
8dc85e07-b2b9-4940-9276-c6c434947448	Sales Representative	72b81592-f48a-4753-87aa-25142749660f
18ce29b7-eb54-472e-97cf-b06be3498f2e	Business Development Executive	866c8990-75fc-4408-8d32-c4ac18b709a6
3def3fea-5c54-449f-b8b7-5d47b678ad0c	Business Development Manager	866c8990-75fc-4408-8d32-c4ac18b709a6
cea685c2-6942-43ff-abd5-be1a2d505f3d	Partnership Manager	866c8990-75fc-4408-8d32-c4ac18b709a6
4ed7884b-c066-4854-b527-c224fe8e04cd	Growth Executive	866c8990-75fc-4408-8d32-c4ac18b709a6
cb867a06-3c4a-4133-b3c4-d83c6b7ce6eb	Market Development Manager	866c8990-75fc-4408-8d32-c4ac18b709a6
a16a12ad-ad51-4eed-a94e-c5aad845c69c	Account Manager	56c22dfc-50f7-4bec-89f1-e42cdc83aee6
ef336950-e181-4ea2-acbc-434bbbd07dee	Key Account Manager	56c22dfc-50f7-4bec-89f1-e42cdc83aee6
1e174fe5-a16f-434d-917e-9f732c5c6588	Client Relationship Manager	56c22dfc-50f7-4bec-89f1-e42cdc83aee6
fd038829-bacd-4ec8-ac39-dbce737c7706	People Operations Specialist	17917313-19b3-4d64-9c18-387af7a4f2af
7996624c-52d5-45ff-bf07-228252d5feca	HR Administrator	29e5e8d0-380d-46f0-939c-88e54635307e
fa6e9d9e-0851-4eca-ab38-d2fba40bbc84	HR Coordinator	29e5e8d0-380d-46f0-939c-88e54635307e
6843e3f0-64a9-45de-9a66-627060dafeb5	Personnel Administrator	29e5e8d0-380d-46f0-939c-88e54635307e
8cef1893-8677-416a-bb8d-4f397a34324a	HR Operations Executive	29e5e8d0-380d-46f0-939c-88e54635307e
958be91d-eb8c-4c8e-b836-a473d5e47d19	Employee Records Specialist	29e5e8d0-380d-46f0-939c-88e54635307e
d314e913-445a-40fe-a203-d28e370e800d	Talent Acquisition Specialist	0b4eae8a-7f8a-4b37-861c-ac0970ab0be8
54e6e40a-822d-436b-a940-8a3eb33256e3	Talent Acquisition Executive	0b4eae8a-7f8a-4b37-861c-ac0970ab0be8
5290114b-c577-428f-afec-724f2b6d16be	Talent Acquisition Manager	0b4eae8a-7f8a-4b37-861c-ac0970ab0be8
3254ac95-6005-4538-85bc-eb80e803530a	Sourcing Specialist	0b4eae8a-7f8a-4b37-861c-ac0970ab0be8
db56c46f-8459-45a9-bab1-9b8f6e2a9549	Candidate Experience Coordinator	0b4eae8a-7f8a-4b37-861c-ac0970ab0be8
790df9fb-7f1d-4550-bc83-bbcb6f971b30	Recruiter	3f325aea-7ea9-48c4-8f79-9b679b64dd10
376afe96-56b5-408b-b1af-4ef2d1196e4e	Recruitment Executive	3f325aea-7ea9-48c4-8f79-9b679b64dd10
b6634243-1438-48db-a89a-e4d93d30934d	Recruitment Consultant	3f325aea-7ea9-48c4-8f79-9b679b64dd10
d4f7f574-2d72-4ef4-812e-063b392e44c6	Technical Recruiter	3f325aea-7ea9-48c4-8f79-9b679b64dd10
9b82225c-9715-411a-b8c3-f132f1647270	Senior Recruiter	3f325aea-7ea9-48c4-8f79-9b679b64dd10
b92f5c6b-486e-49c7-9e9c-47afb866cb53	Learning and Development Specialist	380525a9-6c6f-4fa2-9900-511c9bf5b0d3
1afd5aaf-e45e-4028-9986-241d44e25eac	Training Manager	380525a9-6c6f-4fa2-9900-511c9bf5b0d3
16701e92-a4af-4e37-a75e-19975d5e9405	Instructional Designer	380525a9-6c6f-4fa2-9900-511c9bf5b0d3
4a14d1ae-b92d-4a10-a59e-74aa67778954	Corporate Trainer	380525a9-6c6f-4fa2-9900-511c9bf5b0d3
a6fe7175-4621-405e-b333-f864848c5f43	Training Coordinator	380525a9-6c6f-4fa2-9900-511c9bf5b0d3
2d92afd0-f01c-45a4-b63e-8ae2dd21ffae	Employee Relations Specialist	f0261df9-c25b-48fa-8530-a5daafb1b9f4
b74d656a-ad24-42ee-8137-e02dd0dbeda2	Employee Engagement Manager	f0261df9-c25b-48fa-8530-a5daafb1b9f4
6b9e4d7f-e75a-4f05-a91c-952c8f0bb5e1	Labor Relations Officer	f0261df9-c25b-48fa-8530-a5daafb1b9f4
f300fc9b-e3e0-49b2-9822-3ef00803f709	HR Relations Executive	f0261df9-c25b-48fa-8530-a5daafb1b9f4
28516e52-cc8b-4371-bb0e-58dd64fd2f01	Conflict Resolution Specialist	f0261df9-c25b-48fa-8530-a5daafb1b9f4
9f14b531-61da-4805-b048-46be390f7a4e	Compensation and Benefits Analyst	2b890dca-cda8-4d9d-b0e8-b093e371bbeb
69d9d214-d581-4960-8d57-05946a029801	Retention Manager	b91681aa-8e4f-44fc-aa1c-d160e1e17657
3e79f691-7565-452a-9221-e4da75e95431	Call Center Executive	1edfa9b9-bc5b-4ca5-bdd9-326a1cdfd67d
f4ebbec0-7ce2-4610-a174-630a141f5cdd	Call Center Agent	1edfa9b9-bc5b-4ca5-bdd9-326a1cdfd67d
85650da5-0648-442e-a740-dc6836926c8b	Contact Center Supervisor	1edfa9b9-bc5b-4ca5-bdd9-326a1cdfd67d
62cc9348-940f-4eda-8edb-d6be23d404fe	Voice Process Associate	1edfa9b9-bc5b-4ca5-bdd9-326a1cdfd67d
8911f61e-321a-4447-a74a-2bf5b5fb0ab8	Help Desk Technician	78b12cac-9856-42a2-b713-29e377e27adb
52de7b50-ba08-42c6-ad50-a4e86cc8e687	Service Desk Analyst	78b12cac-9856-42a2-b713-29e377e27adb
03d2a9ea-45b8-4d2b-9b14-0f5d3ee2bc78	Help Desk Support Engineer	78b12cac-9856-42a2-b713-29e377e27adb
6798d5e0-0c67-4c97-8f40-91b22195cfe1	IT Help Desk Specialist	78b12cac-9856-42a2-b713-29e377e27adb
1b116a84-eb4b-425c-bd67-eb8152114044	Support Desk Coordinator	78b12cac-9856-42a2-b713-29e377e27adb
c2efcd0a-f33d-4388-8836-93c8e507d2ce	Finance Manager	685d76db-b251-4db9-9eb2-1a067fb0ea3e
fac0717f-214f-4329-be49-236b7e19567c	Financial Analyst	685d76db-b251-4db9-9eb2-1a067fb0ea3e
256b17de-640e-461c-b100-d4fea898cfd3	Rewards Specialist	2b890dca-cda8-4d9d-b0e8-b093e371bbeb
7fd00675-288f-4b57-9659-6ce59f557481	Administrative Assistant	1c6a31f1-6543-4a49-87e0-ff02eb88d048
64bb3197-5563-46fe-8e2c-61334402cb03	Facility Coordinator	1c6a31f1-6543-4a49-87e0-ff02eb88d048
d93505d6-c0c9-4740-9dcb-a68fc346dc7d	Office Manager	1c6a31f1-6543-4a49-87e0-ff02eb88d048
1b302b19-5d0e-44bf-81a1-1db7a18cd202	Customer Support Executive	ab54422a-2bc0-4ad7-ae4f-070b50302e28
df241266-2810-4166-bcdc-b465c7848cf8	Customer Service Representative	ab54422a-2bc0-4ad7-ae4f-070b50302e28
6f934f24-f9e7-48fe-aea5-5f1141182865	Support Associate	ab54422a-2bc0-4ad7-ae4f-070b50302e28
4ec3c6d8-ac6c-4212-b710-300604361b78	Customer Care Specialist	ab54422a-2bc0-4ad7-ae4f-070b50302e28
9b343705-d78e-4918-8871-e4ba148de333	Service Desk Representative	ab54422a-2bc0-4ad7-ae4f-070b50302e28
fe84d12c-c54f-4e15-b506-daa47eadaa03	Customer Success Manager	b91681aa-8e4f-44fc-aa1c-d160e1e17657
a671cc59-ab6c-4a09-a5a9-397d4f36cebc	Customer Success Executive	b91681aa-8e4f-44fc-aa1c-d160e1e17657
30a54dc4-658f-4a82-b14d-1952e5477b9b	Client Success Specialist	b91681aa-8e4f-44fc-aa1c-d160e1e17657
2acee7b4-e92e-45ef-b0e8-da1c8b15e022	Onboarding Specialist	b91681aa-8e4f-44fc-aa1c-d160e1e17657
5d95f725-aade-43f5-8887-036c86af2233	Telecaller	1edfa9b9-bc5b-4ca5-bdd9-326a1cdfd67d
ef6dffd8-3e5d-4cc3-bd76-48c40fac85dc	Accounts Receivable Manager	484cd0b4-e8b8-4b54-9061-c5c8f692263a
01b3d6e5-3a9b-49ac-9dea-effbd6f55e3b	Treasury Analyst	1b815285-c97e-410d-89ac-adceb1647b18
a9547563-bd26-4bd8-bfe8-9a7953b50117	Cash Manager	1b815285-c97e-410d-89ac-adceb1647b18
301e9ff2-3bdc-4f56-a9ee-1da7830d2959	Treasury Executive	1b815285-c97e-410d-89ac-adceb1647b18
8c37003d-0f86-4543-b2a3-a615401c290b	Liquidity Manager	1b815285-c97e-410d-89ac-adceb1647b18
e4802159-e083-41ab-9358-2d4898e7f657	Treasurer	1b815285-c97e-410d-89ac-adceb1647b18
7f515568-61bd-42dd-8d1e-86756794cfe3	Tax Analyst	ab695966-9235-4a89-8fea-e7837dbfac53
feeb3ff2-36fb-4e02-9bfd-2b79132c8ec6	Tax Consultant	ab695966-9235-4a89-8fea-e7837dbfac53
24af53b5-d31a-4e1a-873f-fae4cd643c1e	Tax Manager	ab695966-9235-4a89-8fea-e7837dbfac53
ecb75606-20f7-4e74-ba1b-3a6764a61436	GST Specialist	ab695966-9235-4a89-8fea-e7837dbfac53
453b2516-8136-46ab-a179-6c126dc8dc8a	Corporate Tax Executive	ab695966-9235-4a89-8fea-e7837dbfac53
2db2adc5-80dc-485d-8743-dcb26df5084b	Internal Auditor	66e70f8f-cdd3-4833-bc13-c43b00020850
0c9c8cba-007f-4188-9c76-db911edf1baf	Audit Executive	66e70f8f-cdd3-4833-bc13-c43b00020850
edcb8dfc-8405-4bb4-9f5a-28a6f28a6785	Audit Manager	66e70f8f-cdd3-4833-bc13-c43b00020850
81fb0eff-742f-4820-ae9b-bd2bad61fde1	Compliance Auditor	66e70f8f-cdd3-4833-bc13-c43b00020850
0dfd6b8f-c0b9-42e3-a10d-934a528e61ed	Risk Auditor	66e70f8f-cdd3-4833-bc13-c43b00020850
f3e5e507-afa5-4b45-8597-03bc20e4e7a3	FP&A Analyst	bdf6a7fb-161c-497d-9d74-30c73e3f582f
58c6282d-4cdd-4375-9fc1-333556d3c9b7	Financial Planning Analyst	bdf6a7fb-161c-497d-9d74-30c73e3f582f
9a92b7a4-ce6e-41cc-a723-dd92ada6292b	Budgeting Manager	bdf6a7fb-161c-497d-9d74-30c73e3f582f
95f8f53b-8db0-4dce-8309-40074f6ee235	FP&A Manager	bdf6a7fb-161c-497d-9d74-30c73e3f582f
2de8df4f-5959-45d0-aa65-478502953954	Warehouse Manager	db36d674-53d3-4198-8de5-939e89b89118
32e4df18-ea94-425b-9334-f636499cc3f0	Store Keeper	db36d674-53d3-4198-8de5-939e89b89118
3c623d7e-28a3-45fe-bd63-bdf42ca39fb0	Warehouse Associate	db36d674-53d3-4198-8de5-939e89b89118
2c516991-1791-445d-b841-045f7bce7aa1	Inventory Warehouse Coordinator	db36d674-53d3-4198-8de5-939e89b89118
467ae070-7a96-4ab2-95e7-b92e5e7c6ea8	Production Supervisor	d5a251e1-f4bf-477d-8cfe-f213811330b6
3655f5f3-bc2e-4ff6-8967-5fa0798b21cc	Production Manager	d5a251e1-f4bf-477d-8cfe-f213811330b6
e430d082-5a11-4343-96d9-dba1705ac881	Production Engineer	d5a251e1-f4bf-477d-8cfe-f213811330b6
56432ee8-fbd9-47b3-ae29-63d75756c261	Shift Supervisor	d5a251e1-f4bf-477d-8cfe-f213811330b6
2a080703-87d2-475c-8bf0-08b2bcb8514f	Production Planner	d5a251e1-f4bf-477d-8cfe-f213811330b6
be6ccb6e-4832-49b0-91d6-f0ad493fd02e	Manufacturing Engineer	f065a9a8-5eb8-4f21-ba73-4cad30d35727
8c10db40-d080-4516-a66e-ab12327f82d1	Manufacturing Supervisor	f065a9a8-5eb8-4f21-ba73-4cad30d35727
1bc5435b-3ac0-4b0f-9bd0-a5bd39180e8d	Manufacturing Manager	f065a9a8-5eb8-4f21-ba73-4cad30d35727
190f76e6-edfe-4008-8be4-bdbefbf06752	Process Engineer	f065a9a8-5eb8-4f21-ba73-4cad30d35727
446497d6-72cd-4809-bbf6-b99455ea5b29	Assembly Technician	f065a9a8-5eb8-4f21-ba73-4cad30d35727
f49ca21a-b798-492c-a539-e186693d864d	Quality Control Inspector	4af11899-18be-4a9e-aed4-187eb4ad4f13
e7b06dda-0dec-4d90-a030-f0b42bf31f7e	QC Analyst	4af11899-18be-4a9e-aed4-187eb4ad4f13
b6c467b9-9e80-4726-8d6d-f682a051e2e2	Quality Engineer	4af11899-18be-4a9e-aed4-187eb4ad4f13
ebba3ebc-e43b-4487-91b5-cea40a5ff231	Quality Control Manager	4af11899-18be-4a9e-aed4-187eb4ad4f13
fa43741e-bf5f-4e0f-982b-f798f6b648c5	Testing Technician	4af11899-18be-4a9e-aed4-187eb4ad4f13
7aac5cbb-cde8-4ee6-9d42-ccaba5781fd4	Maintenance Technician	7468d9fb-c35c-46e6-8a58-f7a7611d5411
8aa3b447-f5b9-4d02-89bc-365413c248ca	Maintenance Engineer	7468d9fb-c35c-46e6-8a58-f7a7611d5411
1a15eb1f-68cd-425b-875a-37a1fdfa2a3c	Maintenance Supervisor	7468d9fb-c35c-46e6-8a58-f7a7611d5411
bc65beee-45df-44be-922e-ec212bedff82	Facility Maintenance Manager	7468d9fb-c35c-46e6-8a58-f7a7611d5411
28427897-39ec-4c59-afff-218625752288	Equipment Technician	7468d9fb-c35c-46e6-8a58-f7a7611d5411
4239e467-9b21-4ab9-b554-7cc9d2793fa3	Industrial Engineer	32ba180f-541e-45fc-88a8-f1f798a99026
533d99ee-f96c-49a2-a1af-76f4a193a9df	Process Improvement Engineer	32ba180f-541e-45fc-88a8-f1f798a99026
6334e89c-321d-4b55-9fd7-b4782be17a85	Lean Manufacturing Engineer	32ba180f-541e-45fc-88a8-f1f798a99026
b1a230eb-7504-4dc6-852f-d47d0bf8d9f2	Operations Excellence Engineer	32ba180f-541e-45fc-88a8-f1f798a99026
ccfd1d7e-49a3-45f0-97b4-40af5ba0385c	Methods Engineer	32ba180f-541e-45fc-88a8-f1f798a99026
e8caeb50-6934-40f3-b5ce-bd5727d73366	Research Scientist	4d3c38f4-782f-4001-be30-b21a156fba66
335ae47e-2ee4-4328-9027-b3ffc32ca275	R&D Engineer	4d3c38f4-782f-4001-be30-b21a156fba66
4d86cd67-f58d-4882-ac34-16a162aeb2c2	Product Research Analyst	4d3c38f4-782f-4001-be30-b21a156fba66
9b79e69b-96e3-42d4-aefe-37e24eb18744	Innovation Researcher	4d3c38f4-782f-4001-be30-b21a156fba66
a7ca36b2-02e0-44ea-8408-ab48a4359688	R&D Manager	4d3c38f4-782f-4001-be30-b21a156fba66
87654351-2d99-4a37-b0ad-f2c2920a35ff	Innovation Specialist	460c3fe1-b417-43f4-8769-6d966515de34
718942d1-3310-46bb-a246-ebf6fcad768f	Innovation Manager	460c3fe1-b417-43f4-8769-6d966515de34
789e6ac8-d85b-461c-92bf-24bc6d969b0d	Prototype Engineer	460c3fe1-b417-43f4-8769-6d966515de34
fa60f2c6-a07d-4047-b842-6ba7262c291e	Research Innovator	460c3fe1-b417-43f4-8769-6d966515de34
32c70f76-ad4c-4761-8083-8d358be98517	Innovation Program Lead	460c3fe1-b417-43f4-8769-6d966515de34
458af587-3ede-4f87-b0b7-f0ddbd1c1c35	Product Engineer	6ffa2b41-f770-4951-b5c7-4be5be7bba7f
345b3376-143a-435c-8929-0131ae940ca9	Design Engineer	6ffa2b41-f770-4951-b5c7-4be5be7bba7f
8e9d59d1-70b4-48e5-ae1e-b2e8e66c9c57	Product Development Engineer	6ffa2b41-f770-4951-b5c7-4be5be7bba7f
f90939b9-22e9-4c6f-bbac-d6aa359ac889	Mechanical Design Engineer	6ffa2b41-f770-4951-b5c7-4be5be7bba7f
45458f3a-1038-4c76-8724-777049aa0b9b	Product Engineering Manager	6ffa2b41-f770-4951-b5c7-4be5be7bba7f
a1172d0a-e21d-4bab-bf73-e53cd02e97fe	Data Scientist	a85a6137-4345-4551-8831-883f4f5f98d5
56a65b50-311b-4a7d-9fab-824f92952a19	Senior Data Scientist	a85a6137-4345-4551-8831-883f4f5f98d5
fcf6399e-90f3-490b-841b-128c03555d47	Applied Scientist	a85a6137-4345-4551-8831-883f4f5f98d5
92ec9c2c-8f34-4640-afea-d3dcb5c1085a	Research Data Scientist	a85a6137-4345-4551-8831-883f4f5f98d5
efb9a1a7-5446-4057-a793-d1a1677a70a1	Machine Learning Scientist	a85a6137-4345-4551-8831-883f4f5f98d5
ac7b0a34-e76e-4268-bf24-a79758b66797	Business Analyst	42330e1e-d85e-44b1-b839-abe1ab9ab9b2
27a90fb1-5476-46c6-9ef5-83a78c4eacca	Data Analyst	42330e1e-d85e-44b1-b839-abe1ab9ab9b2
c89d4bcb-ae14-42d3-ab4d-8a340fdf7700	Analytics Consultant	42330e1e-d85e-44b1-b839-abe1ab9ab9b2
2c5478d3-1c92-40d2-89a9-202a01e9444e	Insights Analyst	42330e1e-d85e-44b1-b839-abe1ab9ab9b2
68b92078-3c85-4c05-b062-0af1e762f8d7	Analytics Manager	42330e1e-d85e-44b1-b839-abe1ab9ab9b2
09fe1102-717d-4148-b777-6d550f0947e0	MIS Executive	be34a9dd-dd0d-4b89-94a8-cf849af2a9d4
3c9d160a-7950-4a0d-8331-59ae4cc553e1	Report Developer	be34a9dd-dd0d-4b89-94a8-cf849af2a9d4
11681b67-4c83-4f6d-af08-dbaef6e9d3ca	Dashboard Analyst	be34a9dd-dd0d-4b89-94a8-cf849af2a9d4
e4ff229e-15ec-4173-b1d1-e32aeecdc420	Reporting Manager	be34a9dd-dd0d-4b89-94a8-cf849af2a9d4
0a07da1d-dbbf-4275-8c14-2affe8184f1c	Data Governance Analyst	e9084bda-57e4-4720-949b-f14e097bad34
26cb54b9-adf9-41f1-b934-09fb5adffe1a	Data Steward	e9084bda-57e4-4720-949b-f14e097bad34
b4378a7d-8eef-4b69-8190-37d7b6b247bb	Master Data Specialist	e9084bda-57e4-4720-949b-f14e097bad34
5eb4bc58-3709-4069-b88f-246d6a077746	Data Quality Manager	e9084bda-57e4-4720-949b-f14e097bad34
a4792145-7e14-4fbb-8568-9af8ff176a92	Governance Lead	e9084bda-57e4-4720-949b-f14e097bad34
54059be2-f967-411c-9457-57030edab264	Product Manager	1a348e2b-282c-4f23-977f-ca8b456cf789
c1bcbe2b-b40f-4717-84dc-bc8cd5849564	Associate Product Manager	1a348e2b-282c-4f23-977f-ca8b456cf789
399b62a4-3999-417e-88ce-c5b4b6fed221	Technical Product Manager	1a348e2b-282c-4f23-977f-ca8b456cf789
b10f883e-96b1-4096-8804-e8f5186ed479	Senior Product Manager	1a348e2b-282c-4f23-977f-ca8b456cf789
54a6dca6-f95a-41f6-a617-77e9948d4e7b	Product Owner	1a348e2b-282c-4f23-977f-ca8b456cf789
13cf4619-948e-4eb8-8021-a851687b9cab	Product Strategist	371374b9-a600-470f-9f8b-b019dbbd8096
da6cd187-a533-4da4-a4f3-fe0d72099d22	Product Strategy Manager	371374b9-a600-470f-9f8b-b019dbbd8096
809fcdd5-c5ea-4f80-bc88-463fd180dee0	Market Strategy Analyst	371374b9-a600-470f-9f8b-b019dbbd8096
087f3692-4fae-42e8-b045-a4d08ef44fa7	Go-to-Market Strategist	371374b9-a600-470f-9f8b-b019dbbd8096
b4982c48-2502-4ac4-8b31-b0095a17c166	Portfolio Strategy Manager	371374b9-a600-470f-9f8b-b019dbbd8096
914b1055-d32a-4668-a4a9-1ee15cda0b16	Product Operations Manager	ce4697b7-aedd-4897-89bd-f3777b884f8a
a10978a0-4457-4fde-965e-c841431aaadd	Product Operations Specialist	ce4697b7-aedd-4897-89bd-f3777b884f8a
ea290d6e-2335-4dc9-898d-a6b00a0c5428	Product Analyst	ce4697b7-aedd-4897-89bd-f3777b884f8a
96dce118-b31f-4d4f-b6f0-ee435a56725d	Operations Program Manager	ce4697b7-aedd-4897-89bd-f3777b884f8a
4f3956cc-090f-45d1-86cd-525462007deb	Product Coordinator	ce4697b7-aedd-4897-89bd-f3777b884f8a
1400d886-9c4f-4a79-8d00-09b5cfb4388e	Registered Nurse	d5b775b8-3f2a-4dfb-b63c-2247add904ab
bc32ec81-1812-4fe2-821b-0ca71d495c94	Staff Nurse	d5b775b8-3f2a-4dfb-b63c-2247add904ab
01ad4b1d-f812-4a25-9a14-480823a5fb6f	Nurse Practitioner	d5b775b8-3f2a-4dfb-b63c-2247add904ab
85743fae-3a9d-4ecc-b9b1-0e07bf5c78c0	Charge Nurse	d5b775b8-3f2a-4dfb-b63c-2247add904ab
1a395ee7-b942-4874-870d-b5c882488d46	Clinical Nurse Specialist	d5b775b8-3f2a-4dfb-b63c-2247add904ab
f9b3a7bc-138e-4ca4-96a6-88c5bdea1cde	Medical Administrator	b2589ef6-b91f-46d0-b849-d578bad4ee4d
359d8127-687c-42d5-8439-e4b71b83abf4	Hospital Administrator	b2589ef6-b91f-46d0-b849-d578bad4ee4d
9da9d3e6-2e29-4d60-8b0e-0b9b7680c587	Healthcare Operations Manager	b2589ef6-b91f-46d0-b849-d578bad4ee4d
8fc6e2de-6a3c-4c42-b119-b187addc8f9c	Medical Office Manager	b2589ef6-b91f-46d0-b849-d578bad4ee4d
342094f2-3297-4778-9c72-171155aa24a9	Patient Services Manager	b2589ef6-b91f-46d0-b849-d578bad4ee4d
1d7da6f0-7418-4167-916d-38cd5d4195a6	Lab Technician	113e90d2-12c7-4a76-8953-1a243c0e15dc
8bbdd205-1f0f-4548-9dd0-00844a519f22	Medical Laboratory Scientist	113e90d2-12c7-4a76-8953-1a243c0e15dc
ca28c232-390f-46b8-b5bb-280f97a02ae1	Pathology Technician	113e90d2-12c7-4a76-8953-1a243c0e15dc
bc4767a9-6db0-4a08-8a85-ee0039a0957b	Lab Supervisor	113e90d2-12c7-4a76-8953-1a243c0e15dc
766a5d13-5395-4d23-bb1a-c24f211e0b5e	Clinical Laboratory Technologist	113e90d2-12c7-4a76-8953-1a243c0e15dc
570b29a7-e35c-4f66-a8c2-db2001b2cd67	Pharmacist	e5f7b741-f815-46a4-93ea-163aeb322f2a
da4b449b-e550-4d5b-882f-21e6915aceb4	Clinical Pharmacist	e5f7b741-f815-46a4-93ea-163aeb322f2a
de463511-45a8-4a05-8ed5-cc7eb7fa7a93	Pharmacy Technician	e5f7b741-f815-46a4-93ea-163aeb322f2a
02c63919-652a-4359-8d60-b987ce8152c1	Pharmacy Manager	e5f7b741-f815-46a4-93ea-163aeb322f2a
22daf26a-018a-4bd7-931d-17f8276aedba	Retail Pharmacist	e5f7b741-f815-46a4-93ea-163aeb322f2a
b270266e-ea7f-4f28-b1b2-2b6f0dc26258	Clinical Operations Manager	7d837164-3df5-4188-ad8d-4f63edb198c1
9c071ccb-cc97-46cf-a4af-ef948ec1069e	Clinical Coordinator	7d837164-3df5-4188-ad8d-4f63edb198c1
da1f3ed7-b247-4868-9049-8c967c67526a	Clinical Research Associate	7d837164-3df5-4188-ad8d-4f63edb198c1
7f67f8f7-56e8-4411-b8ab-48ab5625c19b	Patient Care Coordinator	7d837164-3df5-4188-ad8d-4f63edb198c1
08d26d88-7a2a-4e33-b0e8-58be458cf11d	Clinical Program Manager	7d837164-3df5-4188-ad8d-4f63edb198c1
73f20558-8dfc-4096-b490-8e98807baef0	Academic Affairs Manager	f665285a-3964-40fd-9827-23ac6fcda87d
72e94fe4-f3b3-4554-a39d-1c715cad4668	Academic Coordinator	f665285a-3964-40fd-9827-23ac6fcda87d
97ecdea2-93ec-4fa6-87f4-e341dec63916	Curriculum Specialist	f665285a-3964-40fd-9827-23ac6fcda87d
03338eca-a03d-4ed0-b2bb-d7f5ec6b3270	Academic Dean Assistant	f665285a-3964-40fd-9827-23ac6fcda87d
16f6b388-05da-48b9-adec-d32b08cffd48	Education Program Manager	f665285a-3964-40fd-9827-23ac6fcda87d
23d8f5e0-f548-45ff-8adc-1c8acc771675	Admissions Counselor	806886c9-242c-4546-837f-a0c313bb6257
1f47aeff-de65-4d76-8072-9ba3cbb84796	Admissions Officer	806886c9-242c-4546-837f-a0c313bb6257
ae317f06-31e5-429e-b20e-f03beca083c1	Enrollment Specialist	806886c9-242c-4546-837f-a0c313bb6257
7098ec21-1119-413a-a6a0-0643a92af7d4	Admissions Coordinator	806886c9-242c-4546-837f-a0c313bb6257
f90c252a-b908-47c0-a385-0d6933660b0e	Student Recruitment Officer	806886c9-242c-4546-837f-a0c313bb6257
d43e16e3-4694-4611-9904-4c61b56f8b41	Student Services Coordinator	bf679d4a-b027-4fa3-804a-b743eecec630
59ab762e-b50f-48d1-afb2-afbd53904f11	Academic Advisor	bf679d4a-b027-4fa3-804a-b743eecec630
4202efa2-4c60-42b9-9358-8553059a3092	Student Support Specialist	bf679d4a-b027-4fa3-804a-b743eecec630
5cb1e265-5bef-4c89-b47b-4ad519d536cc	Career Counselor	bf679d4a-b027-4fa3-804a-b743eecec630
d894b98c-0360-4216-ba37-384c80605019	Student Affairs Officer	bf679d4a-b027-4fa3-804a-b743eecec630
cf6cbd0f-8827-4f5f-aaf0-0c17abe83b03	Faculty Administrator	ec430ec2-b51b-4a8d-b150-68a149fe953c
3fd87ab9-9f94-4d9d-8aaf-b17de7f0fd7f	Faculty Coordinator	ec430ec2-b51b-4a8d-b150-68a149fe953c
d16a72dd-d7fb-4bab-acaa-c55984368500	Academic HR Specialist	ec430ec2-b51b-4a8d-b150-68a149fe953c
18cdd057-3acf-412f-b034-19a04f32c48f	Faculty Affairs Manager	ec430ec2-b51b-4a8d-b150-68a149fe953c
e296caed-3ca1-4f0f-813a-bdcd1057edab	Department Administrator	ec430ec2-b51b-4a8d-b150-68a149fe953c
2dfdc873-3149-4882-ba37-4e19a08ea5e1	Underwriter	ec7d05c3-bd8a-43a8-9763-0014bd3835a3
dfafbccf-7fdb-47d0-becb-b528df3b0bd3	Senior Underwriter	ec7d05c3-bd8a-43a8-9763-0014bd3835a3
8e954391-ecce-4e06-8992-4343b01f2dbc	Insurance Risk Analyst	ec7d05c3-bd8a-43a8-9763-0014bd3835a3
b8ae4a60-4f36-4ee6-ace4-a0507f0f636d	Loan Underwriter	ec7d05c3-bd8a-43a8-9763-0014bd3835a3
10a49e33-f8b4-42ad-8662-4f6f390ae66a	Underwriting Manager	ec7d05c3-bd8a-43a8-9763-0014bd3835a3
efe7947b-a6a1-46f1-a3ea-676aa27ab4ac	Claims Adjuster	7d613a69-1563-4e6b-9fc8-1b781bc70434
7d4e7315-5398-4d5a-bea1-5e48f861a9b3	Claims Analyst	7d613a69-1563-4e6b-9fc8-1b781bc70434
03c0e0c9-43c9-4bf7-94ac-9eb6e3697fa2	Claims Processor	7d613a69-1563-4e6b-9fc8-1b781bc70434
92cdacce-35d8-4816-9295-3e4d7bf37378	Claims Manager	7d613a69-1563-4e6b-9fc8-1b781bc70434
e9797286-6237-41e4-8c98-d463a9036725	Insurance Claims Specialist	7d613a69-1563-4e6b-9fc8-1b781bc70434
4d4d73d0-9994-4ec0-bf7f-55bfa50ec05d	Loan Processor	d0b9d8e8-3788-444d-bd8c-788e98174713
a533f6ae-3fcc-4ebc-a47e-8a5957787029	Mortgage Processor	d0b9d8e8-3788-444d-bd8c-788e98174713
bd4b735f-3a56-4429-bdb1-8e7eb09fdc7f	Loan Documentation Specialist	d0b9d8e8-3788-444d-bd8c-788e98174713
ab9ee767-0d4c-4740-94ae-052a0826ff6c	Loan Operations Executive	d0b9d8e8-3788-444d-bd8c-788e98174713
9990920c-06b0-4d4f-8fe0-5d3dca29234c	Senior Loan Processor	d0b9d8e8-3788-444d-bd8c-788e98174713
b048688a-dbef-4ca4-b6cb-6ca3b70227b5	Credit Analyst	d04c60d7-0df4-4784-9ea9-8756d3d6b53b
02589087-eb77-4802-98e0-006987933f69	Senior Credit Analyst	d04c60d7-0df4-4784-9ea9-8756d3d6b53b
0896af66-4c91-4aea-9d05-392d71e933dd	Commercial Credit Analyst	d04c60d7-0df4-4784-9ea9-8756d3d6b53b
53613bb9-57b3-4709-92f7-e740e9b534e9	Risk Assessment Analyst	d04c60d7-0df4-4784-9ea9-8756d3d6b53b
be4f9658-9780-49ff-9227-0144731d32fa	Credit Manager	d04c60d7-0df4-4784-9ea9-8756d3d6b53b
9cbd5a59-ae01-4971-8e0b-a9e2ff7462b0	Civil Engineer	4144aff0-5d87-4182-b117-569003ecdfd6
55ce3974-460c-40a9-8e76-199438494517	Structural Engineer	4144aff0-5d87-4182-b117-569003ecdfd6
9ff8e229-76a9-4994-9f04-c02394629c42	Design Engineer	4144aff0-5d87-4182-b117-569003ecdfd6
be323c1d-09c0-4637-ae73-d26fead5d316	Construction Engineer	4144aff0-5d87-4182-b117-569003ecdfd6
f142a156-eec4-47e3-8044-9286ab6ce60a	Senior Civil Engineer	4144aff0-5d87-4182-b117-569003ecdfd6
7f8cc05e-7382-4713-92a9-d0d6fe781422	Site Engineer	7f743eac-413d-4972-a9aa-2a0e505adc9b
4794bc3c-275d-4c19-8669-d772565bd3fb	Site Supervisor	7f743eac-413d-4972-a9aa-2a0e505adc9b
5bbbe9ea-67a6-4d47-aa33-a2f46bda6194	Construction Supervisor	7f743eac-413d-4972-a9aa-2a0e505adc9b
63bd6341-49de-4b1d-99ee-87681c0c992b	Field Operations Manager	7f743eac-413d-4972-a9aa-2a0e505adc9b
84ea6b2a-761f-44ee-91b3-415d25a2aa5f	Site Coordinator	7f743eac-413d-4972-a9aa-2a0e505adc9b
84209e79-b3b1-4598-a931-f57e399987b9	Safety Officer	d9d04cc0-b587-46c9-882e-e9e279b0a89c
afc7dcd8-30df-4153-af2c-8e443b7a0172	Safety Engineer	d9d04cc0-b587-46c9-882e-e9e279b0a89c
4f16c5bf-c5f4-45fa-9ce5-8e2108109852	HSE Coordinator	d9d04cc0-b587-46c9-882e-e9e279b0a89c
666ecdc2-820d-44cc-88fe-6f58f7d92e2f	Occupational Safety Specialist	d9d04cc0-b587-46c9-882e-e9e279b0a89c
890c4ee7-3a6b-4194-a529-47fc3f86f8a0	Safety Manager	d9d04cc0-b587-46c9-882e-e9e279b0a89c
47ec2333-9145-4948-998a-fe0bbe8b6640	Project Manager	4a9d8686-7c78-4410-9040-1f36638eddd8
f2cf110e-30d4-48c7-8de6-b0c3365186dd	Program Manager	4a9d8686-7c78-4410-9040-1f36638eddd8
46a003ef-2a2c-4d27-9fdb-2aa21cd684d0	Project Coordinator	4a9d8686-7c78-4410-9040-1f36638eddd8
c70338fe-9bd1-446f-9a22-63ef11e53f08	PMO Analyst	4a9d8686-7c78-4410-9040-1f36638eddd8
bb0cfe54-fefc-4bf9-ac1c-d9e4ece70a32	Scrum Master	4a9d8686-7c78-4410-9040-1f36638eddd8
219d2486-b5b6-4dc7-a36e-6df6e555cafa	Security Officer	756dd23b-5847-4549-b98c-6a0b0af2f846
1a1daca7-a048-4114-9794-d633d34dcca4	Security Supervisor	756dd23b-5847-4549-b98c-6a0b0af2f846
f24fc8a0-3c2d-49c0-9297-c9c88f9bd935	Loss Prevention Manager	756dd23b-5847-4549-b98c-6a0b0af2f846
ee5c0ad8-47d7-47ac-a9d9-4a643d052bdb	Security Operations Manager	756dd23b-5847-4549-b98c-6a0b0af2f846
360fcfad-bfab-4242-baa4-764140adfc8a	Access Control Specialist	756dd23b-5847-4549-b98c-6a0b0af2f846
ddc2736c-7c99-41bd-808a-089212482a16	Finance Executive	685d76db-b251-4db9-9eb2-1a067fb0ea3e
f38d22bc-225d-4665-9060-4b2efd34f886	Budget Analyst	685d76db-b251-4db9-9eb2-1a067fb0ea3e
c2202c17-5448-4cb5-9231-5ee82a8a5800	Security Architect	b7b4e68a-052c-4bec-b5ce-cb87dc0cc4f2
2f619f04-ce49-425c-ab35-8897de4fa430	Information Security Manager	b7b4e68a-052c-4bec-b5ce-cb87dc0cc4f2
979ecdde-f5b0-4ae8-98aa-0b4c4b38613e	CSR Executive	228e90ae-216e-4bb1-a160-c9f4cdd97d40
253e78f5-cffb-474e-931d-3888f35ea9df	CSR Manager	228e90ae-216e-4bb1-a160-c9f4cdd97d40
865d1ef8-9ced-49ba-875e-a7b693aa83a9	Community Relations Specialist	228e90ae-216e-4bb1-a160-c9f4cdd97d40
7598070e-2d17-4d9a-aa47-456d1b7ffc9f	Social Impact Analyst	228e90ae-216e-4bb1-a160-c9f4cdd97d40
5b1bd37b-e025-4294-aedb-c766d349b066	Sustainability Program Coordinator	228e90ae-216e-4bb1-a160-c9f4cdd97d40
9a8027cd-0524-4755-902c-63f7346a86b7	EHS Officer	4a1f10b4-1e84-4973-934c-9f5a0f9096bf
ef91190c-14bd-4a29-85d7-930db68001c4	EHS Manager	4a1f10b4-1e84-4973-934c-9f5a0f9096bf
3487c71a-dd10-40e3-bcce-636d95c9020e	Environmental Specialist	4a1f10b4-1e84-4973-934c-9f5a0f9096bf
1e25205e-ce63-49a5-8756-cdcdd7804fd8	Health and Safety Coordinator	4a1f10b4-1e84-4973-934c-9f5a0f9096bf
8c158348-5f64-4493-91fe-1d966fec3227	Compliance Safety Officer	4a1f10b4-1e84-4973-934c-9f5a0f9096bf
3e85a367-1e85-4c98-8264-5b590219e4c1	Sustainability Analyst	1f871f6c-402f-4b4b-9a8c-3d4ec207b0b9
35634b0f-11e0-42b6-9f59-b2eccd87fbaa	Sustainability Manager	1f871f6c-402f-4b4b-9a8c-3d4ec207b0b9
520ee44f-8c5c-4029-b296-e50c36aa2aab	ESG Specialist	1f871f6c-402f-4b4b-9a8c-3d4ec207b0b9
2c968eb8-b77b-434f-b4ee-7497a7616cb0	Environmental Consultant	1f871f6c-402f-4b4b-9a8c-3d4ec207b0b9
c142eec1-1652-4780-826e-4af11c9eb68a	Carbon Accounting Analyst	1f871f6c-402f-4b4b-9a8c-3d4ec207b0b9
bd310d17-f568-422c-b14d-e96a7743ddc4	Facilities Manager	4e031ab6-440e-4416-bc05-5a29512ffb79
8daa5c30-be2f-4b5b-9321-55e1d239ab3c	Facilities Coordinator	4e031ab6-440e-4416-bc05-5a29512ffb79
d713a805-6c69-4fe6-9467-396731f96589	Building Maintenance Supervisor	4e031ab6-440e-4416-bc05-5a29512ffb79
3f534400-74e1-4003-a6f2-1422bacfbb04	Facilities Engineer	4e031ab6-440e-4416-bc05-5a29512ffb79
5d141fa0-cbfb-46db-832e-839ab1dd0d5b	Property Manager	4e031ab6-440e-4416-bc05-5a29512ffb79
2179362d-a324-4cf8-938b-c8c2ed97a66f	Housekeeping Supervisor	11d0a86f-7a24-4296-afeb-927ef6b2e49e
d9f295e3-1bb0-41ab-bfe5-beb237dfd606	Housekeeping Manager	11d0a86f-7a24-4296-afeb-927ef6b2e49e
7c6e4977-1327-4388-8e7b-67a2617b10c1	Room Attendant	11d0a86f-7a24-4296-afeb-927ef6b2e49e
cf5a89c3-ce11-418c-84d3-6d336e357e70	Cleaning Staff	11d0a86f-7a24-4296-afeb-927ef6b2e49e
bc2dbbcf-961b-43e2-bfb7-75eb0163d457	Janitorial Supervisor	11d0a86f-7a24-4296-afeb-927ef6b2e49e
b0086ae8-ebbb-4b44-8ecf-71c0623de240	Technical Writer	6c2376e3-daf5-47a9-96a3-bd02154ae95c
05d91324-3ef5-45f9-b1f7-38117968b9a1	Documentation Specialist	6c2376e3-daf5-47a9-96a3-bd02154ae95c
06803067-4c9a-40be-bea9-68e836411ba2	API Documentation Writer	6c2376e3-daf5-47a9-96a3-bd02154ae95c
64b16723-b5dc-4884-8310-927f78d0cd8e	Content Developer	6c2376e3-daf5-47a9-96a3-bd02154ae95c
9c8d686d-a46b-42e7-bc27-af1f1eea15cf	Technical Editor	6c2376e3-daf5-47a9-96a3-bd02154ae95c
ff45fa5e-5472-4272-bbd7-ea3fcb936957	Documentation Executive	5d0c501b-00de-43c0-ac4a-9856a9037e93
6b914dac-ee7a-47c2-a1ca-4df00585088c	Document Controller	5d0c501b-00de-43c0-ac4a-9856a9037e93
7df37cf0-d6ed-457a-9813-d6b6396042ac	Records Management Specialist	5d0c501b-00de-43c0-ac4a-9856a9037e93
935cfa2e-1f37-4dde-8bd8-b085297bb386	Document Coordinator	5d0c501b-00de-43c0-ac4a-9856a9037e93
e878e967-64d5-403f-908e-5f4d303946ea	Documentation Manager	5d0c501b-00de-43c0-ac4a-9856a9037e93
d05c5428-c7a8-4774-b4b6-7f985048667d	Knowledge Manager	4e2696a1-9aae-4b20-83df-0971a67066bd
163dbcc2-8355-4233-9b0e-95b804cec666	Knowledge Analyst	4e2696a1-9aae-4b20-83df-0971a67066bd
9cdbeb9e-cbdc-4056-988f-2db4a9f3b76f	Content Librarian	4e2696a1-9aae-4b20-83df-0971a67066bd
a78372f3-01e7-4a3f-a65a-f9f93ab5663f	Knowledge Base Administrator	4e2696a1-9aae-4b20-83df-0971a67066bd
3234f501-4c1a-4a58-8991-190e1e70409a	Information Architect	4e2696a1-9aae-4b20-83df-0971a67066bd
07283873-5e40-4a93-ab68-0f9ab1e82b13	Android Developer	8ee1b7a5-f46a-48a5-801b-964b39a62294
00312c8c-e2ca-4c08-b884-4ca7225583a0	Flutter Developer	8ee1b7a5-f46a-48a5-801b-964b39a62294
c6671a48-8b62-4782-a044-e4d9bf5fc817	React Native Developer	8ee1b7a5-f46a-48a5-801b-964b39a62294
9b040f6e-609b-4b34-be28-de14305b20e9	Mobile App Developer	8ee1b7a5-f46a-48a5-801b-964b39a62294
33766bad-2964-4904-badf-c9349ca9b294	DevOps Engineer	a970f973-42c1-4dcf-a3ec-352d648268d0
ac15f824-a5b0-43be-9e64-4cdfef4eb432	Site Reliability Engineer	a970f973-42c1-4dcf-a3ec-352d648268d0
05e52b41-5909-4cd8-b1e2-203083dc3e9c	CI/CD Engineer	a970f973-42c1-4dcf-a3ec-352d648268d0
d1789a81-0955-41a5-a7e1-50cc26a63884	Release Engineer	a970f973-42c1-4dcf-a3ec-352d648268d0
b4c2ed02-8260-46a9-bf40-b4d2901fac0f	Automation Engineer	a970f973-42c1-4dcf-a3ec-352d648268d0
b97919c9-432d-47aa-9618-c5f4084c1d0e	Cloud Engineer	f27c80a1-a8f1-4e0b-b9e2-23c88697c87d
ff8826dc-2884-4859-8ec4-c428ed7309d1	AWS Engineer	f27c80a1-a8f1-4e0b-b9e2-23c88697c87d
683a24c0-0404-44df-8076-3bba8983ed77	Azure Engineer	f27c80a1-a8f1-4e0b-b9e2-23c88697c87d
ebb88849-4a88-49b3-85e1-d81299c6f545	Google Cloud Engineer	f27c80a1-a8f1-4e0b-b9e2-23c88697c87d
76d8b601-bf42-4017-a1f0-ce0c82f181b2	Cloud Solutions Architect	f27c80a1-a8f1-4e0b-b9e2-23c88697c87d
e42c4914-753e-4ae4-987a-e53ade1b4286	Operations Manager	c65513da-8aad-4132-a33e-a156f3c7b02c
9ae91c74-2015-4988-a0e0-004fe2e7352d	Board Administrator	df00a405-c5da-4dd7-a086-8388d54c2325
181a7f77-78b4-4681-95b5-16a502ba859a	Compliance Secretary	df00a405-c5da-4dd7-a086-8388d54c2325
df371487-b59c-45e4-8529-b2563e32930d	Executive Governance Officer	df00a405-c5da-4dd7-a086-8388d54c2325
1e6944c7-80e3-45f8-8904-e4f91370136a	Custom Application Developer	212c3db8-351e-4de9-bb16-a9f90408df68
49d31c4b-03f6-4574-8c16-318d829debb1	Solutions Developer	212c3db8-351e-4de9-bb16-a9f90408df68
de3b948a-1709-4b04-a024-8c6e8c6eca09	Enterprise Developer	212c3db8-351e-4de9-bb16-a9f90408df68
f08a4013-af2e-497d-acec-e4535d544109	Technical Consultant	212c3db8-351e-4de9-bb16-a9f90408df68
9ab9fca7-0fa3-45c0-88ad-161d19b2337f	Integration Developer	212c3db8-351e-4de9-bb16-a9f90408df68
e0876b6e-2c78-494a-a319-278cc294be08	Forecasting Analyst	bdf6a7fb-161c-497d-9d74-30c73e3f582f
5b9a89fe-c751-4eb8-9b79-a37143bb5ea4	Infrastructure Architect	d88005e4-0477-4a66-8098-5ce139977a52
0b3e24d8-70fa-4689-9a89-d4a6fc4950dd	Server Administrator	d88005e4-0477-4a66-8098-5ce139977a52
fc986254-04c8-439a-94cb-86a948289043	Data Center Engineer	d88005e4-0477-4a66-8098-5ce139977a52
9764b274-0dae-4770-8f6b-bcbef579afce	Network Administrator	e9ee5dbf-bd7d-4a97-a3e4-9a63801feba1
fd3968f3-d234-43ed-bf2e-fa8aa2b08524	Network Engineer	e9ee5dbf-bd7d-4a97-a3e4-9a63801feba1
6b941698-de35-4050-92fb-8a204758bcac	NOC Engineer	e9ee5dbf-bd7d-4a97-a3e4-9a63801feba1
05effc65-2814-4c71-bf0f-fed35eafa06f	Network Security Engineer	e9ee5dbf-bd7d-4a97-a3e4-9a63801feba1
6c0fdcef-9f1f-4a4c-92c4-e847e5db68db	Wireless Network Engineer	e9ee5dbf-bd7d-4a97-a3e4-9a63801feba1
4d34ce54-9379-40b3-b8dd-c2e75464b075	Database Administrator	ff18b43b-5db7-4418-a6aa-5fd379c6858c
a9ab4834-8689-480b-ab4b-51328eb34a14	SQL Developer	ff18b43b-5db7-4418-a6aa-5fd379c6858c
9645b01a-ce37-4ac0-85c9-a5b11cbd9e49	Oracle DBA	ff18b43b-5db7-4418-a6aa-5fd379c6858c
9ec951fc-107f-4ce3-befb-c3e501f7d776	PostgreSQL DBA	ff18b43b-5db7-4418-a6aa-5fd379c6858c
78a583e8-74d2-4fd3-9be7-c11715c0dcfb	Database Engineer	ff18b43b-5db7-4418-a6aa-5fd379c6858c
cfad51fa-a1b8-475f-9341-10ebcfa1700b	Cybersecurity Analyst	da017d77-3c9d-4389-8d35-5e7e687e7d2f
825d6dd4-83ed-4615-98d2-4a503c2b8c81	Security Engineer	da017d77-3c9d-4389-8d35-5e7e687e7d2f
f7880af4-9d9b-47a8-8446-0081e6a42e39	Penetration Tester	da017d77-3c9d-4389-8d35-5e7e687e7d2f
f946ca56-f9f5-4d25-b8cd-9b0c178736b8	SOC Analyst	da017d77-3c9d-4389-8d35-5e7e687e7d2f
f071fa00-36a6-428e-8eb3-9a58f99840de	Information Security Analyst	da017d77-3c9d-4389-8d35-5e7e687e7d2f
cf09dab1-0528-4672-9218-38e8541f2ee4	IT Support Specialist	c531c355-e375-4fac-acc3-137c41f8f661
c5dd510d-edd5-4dff-8f64-73d05adbc40c	Desktop Support Engineer	c531c355-e375-4fac-acc3-137c41f8f661
a3c8e540-065d-4ebd-9608-ec326826a0e9	System Support Analyst	c531c355-e375-4fac-acc3-137c41f8f661
2211d6f8-70f3-4d41-83f7-87229befe32c	IT Helpdesk Technician	c531c355-e375-4fac-acc3-137c41f8f661
d26329be-9e42-49df-9952-a7c53198b628	Technical Support Engineer	c531c355-e375-4fac-acc3-137c41f8f661
c0c505fd-f57c-42c6-a75f-b05e397f48f6	Technical Support Executive	78ea9553-3e24-468f-8390-9d06fe55c05a
1cb5cc86-f18e-43a7-920b-cc664181b90f	Support Engineer	78ea9553-3e24-468f-8390-9d06fe55c05a
9e73b067-26e7-4284-9a61-6b542bdf35d7	Customer Technical Specialist	78ea9553-3e24-468f-8390-9d06fe55c05a
6aa0a2f4-4908-4c3d-a886-a5dcbba73460	Product Support Analyst	78ea9553-3e24-468f-8390-9d06fe55c05a
99f2adb6-284b-432e-9194-6d632568334b	Troubleshooting Specialist	78ea9553-3e24-468f-8390-9d06fe55c05a
3e9455c5-06fe-47e9-beb5-300024901581	QA Engineer	204c0d65-7116-4860-bc76-38999cb8d6fc
3c920132-f3cd-45f4-91d0-fa11966a0000	Software Tester	204c0d65-7116-4860-bc76-38999cb8d6fc
1f5b34a3-bc12-4c43-99ff-68d3aafccd7d	Automation Test Engineer	204c0d65-7116-4860-bc76-38999cb8d6fc
9f9889d8-bd1c-4d08-8b9d-7da550a99ac4	Manual Tester	204c0d65-7116-4860-bc76-38999cb8d6fc
f9a2f9bd-5eb3-43f6-bf40-474090f1c1d8	Quality Assurance Analyst	204c0d65-7116-4860-bc76-38999cb8d6fc
2d1dc249-ff3e-48ce-8abc-a884b4be4380	Data Engineer	1b8aee27-60cb-49ed-9c9e-3cf747ebdf4c
41cc2ef3-30ff-444a-8562-6bf1dff38e0d	Big Data Engineer	1b8aee27-60cb-49ed-9c9e-3cf747ebdf4c
a7b379ba-9273-40f6-a50c-74dc954b7129	ETL Developer	1b8aee27-60cb-49ed-9c9e-3cf747ebdf4c
8d08f59b-6d54-457d-b92d-cc8a72b0403a	Data Pipeline Engineer	1b8aee27-60cb-49ed-9c9e-3cf747ebdf4c
3209a691-578a-4a6d-965a-bd217339a7d9	Analytics Engineer	1b8aee27-60cb-49ed-9c9e-3cf747ebdf4c
2793f5f0-8a92-4327-bcfc-01d2926cd9c6	Machine Learning Engineer	9bb6c08e-f7f6-4040-b924-e2715b475064
5cb30198-0943-4b2c-b965-c194d46d4053	AI Engineer	9bb6c08e-f7f6-4040-b924-e2715b475064
57cc9a95-85d5-474f-aee7-b7432faffca2	Deep Learning Engineer	9bb6c08e-f7f6-4040-b924-e2715b475064
6af487b0-b917-4e5d-b6e1-8d435ddeaf43	NLP Engineer	9bb6c08e-f7f6-4040-b924-e2715b475064
eed58c7d-93f4-4e8e-a712-83456747140a	Computer Vision Engineer	9bb6c08e-f7f6-4040-b924-e2715b475064
3488e6c6-6061-47a7-a8d3-6cd73a0ac4f1	BI Developer	f1b93702-98e9-4a98-8b77-ec2152ae3b1b
796aadc6-faee-44b4-9c16-f6f3cbfe016f	Business Intelligence Analyst	f1b93702-98e9-4a98-8b77-ec2152ae3b1b
f521ae7d-8207-4a0e-a513-1042c13644a2	Power BI Developer	f1b93702-98e9-4a98-8b77-ec2152ae3b1b
42d079a7-e894-4c4c-b4ce-19549992b101	Tableau Developer	f1b93702-98e9-4a98-8b77-ec2152ae3b1b
c0399ad6-2beb-4da1-aa48-5e66f4f3f232	Reporting Analyst	f1b93702-98e9-4a98-8b77-ec2152ae3b1b
c63769fb-72b1-4cd9-b409-8e4bc3328855	Creative Designer	dd5c1ea8-0ff7-442f-94ac-9629914d9916
61f9cc0f-6495-4b16-aa1c-4ba1b820ab6d	Visual Designer	dd5c1ea8-0ff7-442f-94ac-9629914d9916
d0906aba-8629-46b6-90d8-60784afd01d0	Design Lead	dd5c1ea8-0ff7-442f-94ac-9629914d9916
b5721fcb-cd12-4dba-8926-6a4682c5d0a9	Art Director	dd5c1ea8-0ff7-442f-94ac-9629914d9916
f17e4ef5-edd3-40dd-ab3d-8072ee426b1b	Design Coordinator	dd5c1ea8-0ff7-442f-94ac-9629914d9916
a0045185-76d1-46a7-8e4c-42bb691f92a1	UI Designer	5de73471-a308-4c1a-a59f-6982d8b2a0b2
58802e84-68d0-4fe9-bba0-16ddbcbba743	UX Designer	5de73471-a308-4c1a-a59f-6982d8b2a0b2
4095f843-14e9-4f5c-a6ae-9a9066757e29	Product Designer	5de73471-a308-4c1a-a59f-6982d8b2a0b2
e7bd2b11-31ed-4d5f-8aa9-a7856d41a648	UX Researcher	5de73471-a308-4c1a-a59f-6982d8b2a0b2
3ef2be0f-3717-47a1-8059-161c7f860fd0	Interaction Designer	5de73471-a308-4c1a-a59f-6982d8b2a0b2
a132cfe2-7961-44f6-8f59-f8cd78f83844	Graphic Designer	2afa6ca0-3ecb-40b7-82ff-8ddc65fb27b9
bbfb328e-9e0d-41e2-b4a6-cbf6a502d110	Senior Graphic Designer	2afa6ca0-3ecb-40b7-82ff-8ddc65fb27b9
37c75e98-6b77-4f73-a1f0-fa6491cac0ba	Brand Designer	2afa6ca0-3ecb-40b7-82ff-8ddc65fb27b9
7ef9ec55-ddcb-4508-a8c1-ac16a9c51a31	Illustrator	2afa6ca0-3ecb-40b7-82ff-8ddc65fb27b9
0be0e653-0ab5-40fe-9be6-e0d9cc628165	Print Designer	2afa6ca0-3ecb-40b7-82ff-8ddc65fb27b9
dc53f45b-c4f8-4cab-a56c-5977c6688104	Product Designer	a9b34308-bc4e-4561-873c-7064a8229474
6cd19dab-c720-4850-a0e7-9a5aa41306f3	Industrial Designer	a9b34308-bc4e-4561-873c-7064a8229474
893dade2-9865-42c0-aedd-44b99285632c	Design Strategist	a9b34308-bc4e-4561-873c-7064a8229474
efbc662f-1fc4-4765-83d4-270bcbb72f06	Prototype Designer	a9b34308-bc4e-4561-873c-7064a8229474
74b470ba-43ae-4ccb-88de-6f5e3f3671bc	Concept Designer	a9b34308-bc4e-4561-873c-7064a8229474
b0f7e4fb-44eb-4462-8c9a-3be497dbccaa	Video Editor	dbf6dc9e-87ab-4bdd-9be4-285e797ba53a
1f9d1c79-893c-4f6a-b894-5e1b42138c8c	Motion Graphics Designer	dbf6dc9e-87ab-4bdd-9be4-285e797ba53a
257b49a6-2895-4d59-a389-ec6786a6a265	Videographer	dbf6dc9e-87ab-4bdd-9be4-285e797ba53a
30ebd050-cefb-4123-9041-8286ef4598ac	Post Production Specialist	dbf6dc9e-87ab-4bdd-9be4-285e797ba53a
13ab7bff-c5e8-404e-9dcf-d268fec87716	Animation Artist	dbf6dc9e-87ab-4bdd-9be4-285e797ba53a
0442436a-44be-4313-ba5b-7c0509d468af	Content Writer	7ad5f191-11dd-411e-b88b-fdda71e915e0
c577a618-72be-474f-98bb-76c9b9f916f5	Copywriter	7ad5f191-11dd-411e-b88b-fdda71e915e0
df5a7373-6f22-4d40-8169-a5642e2ffd6c	Content Strategist	7ad5f191-11dd-411e-b88b-fdda71e915e0
7d2bf201-4199-4434-93db-3acfd94d68dd	Blog Writer	7ad5f191-11dd-411e-b88b-fdda71e915e0
590f74dd-5b94-479e-8d11-37872cbe02eb	Technical Content Writer	7ad5f191-11dd-411e-b88b-fdda71e915e0
5f4b8820-409a-4172-95da-453f0ae7c64a	Reporting Analyst	be34a9dd-dd0d-4b89-94a8-cf849af2a9d4
a4737a94-6ccd-450f-9a81-1731c8ebdb20	Information Security Analyst	b7b4e68a-052c-4bec-b5ce-cb87dc0cc4f2
58ca4fd3-5ed3-4f2d-964d-1b35e95d4ec5	Security Engineer	b7b4e68a-052c-4bec-b5ce-cb87dc0cc4f2
b37bdd7f-fb00-43f0-8160-4ad252f9a11d	SOC Analyst	b7b4e68a-052c-4bec-b5ce-cb87dc0cc4f2
550867e0-1aeb-4ea1-b570-d75cab59f36c	Account Executive	56c22dfc-50f7-4bec-89f1-e42cdc83aee6
6633cc22-bbca-4906-9751-1605a8321ead	Customer Success Manager	56c22dfc-50f7-4bec-89f1-e42cdc83aee6
304dab9a-265b-4459-8247-c62e4a5858db	Inside Sales Executive	ba206b67-67de-497a-89fe-d70c3be4a076
b8ef9ff0-0d86-4a72-9063-41e79a2eee41	Inside Sales Representative	ba206b67-67de-497a-89fe-d70c3be4a076
a5c51f48-35cb-4f9a-bd2f-1d8b1860c83b	Tele Sales Executive	ba206b67-67de-497a-89fe-d70c3be4a076
95b8b2e4-2551-4b45-8f17-b98d163aae99	Lead Generation Executive	ba206b67-67de-497a-89fe-d70c3be4a076
c2a757bd-b81d-409b-9d5b-4a069114e05d	Sales Development Representative	ba206b67-67de-497a-89fe-d70c3be4a076
31aa190d-1a6c-4015-91e0-68c5310a1488	Field Sales Executive	d1663ee3-8c19-40c3-a694-4d9745b09944
3d87c602-28ab-4ac1-843d-e65d5b37f637	Territory Sales Executive	d1663ee3-8c19-40c3-a694-4d9745b09944
19957219-ad6d-4ff3-bf1e-aa9bc994541b	Area Sales Manager	d1663ee3-8c19-40c3-a694-4d9745b09944
9c6362ca-e88b-41dd-a11f-b0592c1dffdb	Retail Sales Officer	d1663ee3-8c19-40c3-a694-4d9745b09944
42563ab7-4bea-480a-8dba-02b89a0cfbcf	Channel Sales Executive	d1663ee3-8c19-40c3-a694-4d9745b09944
be03aa88-db6f-4d2a-a71f-24a52692f950	Pre-Sales Consultant	9aff532f-c7d6-4184-8aca-b9e431fac301
df294209-1134-4348-9952-8f6dcf6f974a	Solutions Consultant	9aff532f-c7d6-4184-8aca-b9e431fac301
fc3ab0e4-b048-4b03-955d-63aa8d8bfaa7	Technical Pre-Sales Engineer	9aff532f-c7d6-4184-8aca-b9e431fac301
b297b37b-0d68-4463-9aa0-47816f181131	Proposal Specialist	9aff532f-c7d6-4184-8aca-b9e431fac301
26ce16b7-3437-440d-b8dd-6a6d0cfbed4d	Demo Specialist	9aff532f-c7d6-4184-8aca-b9e431fac301
b8b1a807-a238-452b-b868-88d9029ee2d8	Customer Acquisition Executive	94d70619-4abc-4169-a8e4-e753f66f029d
832397af-6f88-4e31-aab7-9432947f5758	Growth Marketing Executive	94d70619-4abc-4169-a8e4-e753f66f029d
b9411b58-97d5-461d-b88e-888248f827dc	Lead Acquisition Specialist	94d70619-4abc-4169-a8e4-e753f66f029d
db6a7324-0a9a-46b9-af38-5127e0d784ef	User Acquisition Manager	94d70619-4abc-4169-a8e4-e753f66f029d
cf333740-37a0-4534-b1bf-21e27bf64aa9	Acquisition Analyst	94d70619-4abc-4169-a8e4-e753f66f029d
aca1483f-b36a-4403-a364-a918bc71834a	Digital Marketing Executive	788a60ee-04a4-4814-88ac-34db4f46a683
d5017694-5fb2-4e2d-9d3f-7c669566f649	Digital Marketing Manager	788a60ee-04a4-4814-88ac-34db4f46a683
a703fb57-c01e-48c3-8337-83227e53d270	Online Marketing Specialist	788a60ee-04a4-4814-88ac-34db4f46a683
6da78379-fada-412d-8964-c1b815b037c5	Campaign Manager	788a60ee-04a4-4814-88ac-34db4f46a683
9a08acce-a102-4d21-8510-2fac53fe6f05	Marketing Analyst	788a60ee-04a4-4814-88ac-34db4f46a683
c3bade6f-a3b1-486b-832f-17465f02d990	Brand Manager	9a19173e-fcdd-4d43-a6b8-ab5f36ef98e1
687ce713-ff37-4a30-a876-7ce74b68a4aa	Brand Executive	9a19173e-fcdd-4d43-a6b8-ab5f36ef98e1
452e8d02-c274-413a-b68a-ef2ddd7fec6d	Brand Strategist	9a19173e-fcdd-4d43-a6b8-ab5f36ef98e1
e618f4be-0bc0-4538-80ef-0ab4bd467f56	Marketing Communications Manager	9a19173e-fcdd-4d43-a6b8-ab5f36ef98e1
56d39e0b-6ec8-4c2f-9d5c-3ff659f22d09	Brand Analyst	9a19173e-fcdd-4d43-a6b8-ab5f36ef98e1
ff38cbaf-034a-4cfc-abbd-5e446c2ecf8e	Performance Marketing Executive	420f8434-c908-4017-9989-099acc6d4390
fcd97969-f9fd-4f69-8f74-fda648234a5c	PPC Specialist	420f8434-c908-4017-9989-099acc6d4390
f1611631-d07d-45cf-988d-dac22c25e226	Paid Media Manager	420f8434-c908-4017-9989-099acc6d4390
54bcb5df-5f73-4d97-9021-66706bb39745	Campaign Optimization Specialist	420f8434-c908-4017-9989-099acc6d4390
5f336098-5487-44c7-88c0-a6ebd69e2c33	Growth Marketing Manager	420f8434-c908-4017-9989-099acc6d4390
63a60f40-7a68-4a9f-a25c-b8b90b437bfe	SEO Executive	454ea24f-2708-4493-bb0a-6eaad34977d2
d571c594-1f43-491f-9b2a-808d6cded7d3	SEO Specialist	454ea24f-2708-4493-bb0a-6eaad34977d2
ef4ced22-3432-47ee-afec-893fd7da8107	SEO Analyst	454ea24f-2708-4493-bb0a-6eaad34977d2
3e4a7255-485f-4247-bd95-1d89ebcd9a60	Search Engine Optimization Manager	454ea24f-2708-4493-bb0a-6eaad34977d2
94bc5170-ea5c-4335-9683-833636bc68b0	Organic Growth Specialist	454ea24f-2708-4493-bb0a-6eaad34977d2
54e6da8b-a5dd-45f8-ac46-194f6dcb901d	Social Media Executive	2203bbf9-9bff-435c-a38e-18aad0f2293d
5c976e12-db30-4578-a3b8-a45196302061	Social Media Manager	2203bbf9-9bff-435c-a38e-18aad0f2293d
ccb6382e-ff69-4748-a545-df91881a1ecb	Community Manager	2203bbf9-9bff-435c-a38e-18aad0f2293d
602404e7-c9da-4945-a0bf-cb9cbcc75c93	Content Creator	2203bbf9-9bff-435c-a38e-18aad0f2293d
2c525672-d75d-49d0-9364-64808cd4b49f	Influencer Marketing Specialist	2203bbf9-9bff-435c-a38e-18aad0f2293d
9b08e9fc-270a-4cd6-881b-69bb25f58d20	Product Marketing Manager	3efc496a-754c-4038-b137-2cf2191fa7dc
bccfb87a-825e-4515-997d-3230e749c557	Go-to-Market Specialist	3efc496a-754c-4038-b137-2cf2191fa7dc
2ac52de4-a793-41c3-b1b2-abf2dca7b436	Product Marketing Executive	3efc496a-754c-4038-b137-2cf2191fa7dc
9740eee9-1ccf-4cd6-9ef7-2a6c3a1d6950	Market Research Analyst	3efc496a-754c-4038-b137-2cf2191fa7dc
b522d3c0-5b5e-4c6d-abfe-ee5f1e4ff204	Product Positioning Specialist	3efc496a-754c-4038-b137-2cf2191fa7dc
a5556dd8-7e38-4835-a3b3-af9003ec000f	Public Relations Executive	ab2131cb-c15e-4057-bbbc-2b993b021810
50c2d2a7-b9a0-4b24-b89f-70d7d8e08c6c	PR Manager	ab2131cb-c15e-4057-bbbc-2b993b021810
57a15487-2701-48e7-887a-f3b3646d140c	Media Relations Specialist	ab2131cb-c15e-4057-bbbc-2b993b021810
8999402d-15b4-4e25-96ab-a9825a471c90	Corporate Affairs Executive	ab2131cb-c15e-4057-bbbc-2b993b021810
aa26612d-d295-461b-85bf-361a47cc0fd2	Press Coordinator	ab2131cb-c15e-4057-bbbc-2b993b021810
37897121-a660-4833-84c7-0bdf4526d1db	Communications Manager	913ea625-b960-49e0-b206-36f472c18870
1ea60301-eff8-4de3-9dd9-1082a98a9c75	Corporate Communications Executive	913ea625-b960-49e0-b206-36f472c18870
0b0133a6-e68b-487e-8710-6d287b1e58a2	Internal Communications Specialist	913ea625-b960-49e0-b206-36f472c18870
1a08ffc5-df2d-4724-98d4-87ef66c454ab	Communications Coordinator	913ea625-b960-49e0-b206-36f472c18870
84dfcdf2-dd6b-4e36-bb1d-b94cb59e4d30	Content Communications Specialist	913ea625-b960-49e0-b206-36f472c18870
9f2d32e4-faba-476a-9767-7f18c9cba8fc	HR Manager	17917313-19b3-4d64-9c18-387af7a4f2af
c8a66530-971a-4487-9584-bc358794b163	HR Executive	17917313-19b3-4d64-9c18-387af7a4f2af
16b1e403-8bdf-43cb-a1bd-cc39b3cc15b8	HR Generalist	17917313-19b3-4d64-9c18-387af7a4f2af
c5141407-e7fa-4879-87f9-565c4a3d2fab	HR Business Partner	17917313-19b3-4d64-9c18-387af7a4f2af
c6c7e134-2553-4a21-8c87-8de857c5247d	Finance Controller	685d76db-b251-4db9-9eb2-1a067fb0ea3e
10e32ae2-a0ed-430d-817c-b11c1c3f2b71	Accountant	891a1118-11f8-4642-b1b4-cdf247fbc834
050fa80a-ca98-4fec-aaef-c78604b0726d	Senior Accountant	891a1118-11f8-4642-b1b4-cdf247fbc834
d534ab2a-c9d7-44ea-8b0a-1c153a3ac391	Accounting Executive	891a1118-11f8-4642-b1b4-cdf247fbc834
a0bdc9cf-6b59-4bd6-812e-a329bc7e4f51	General Ledger Accountant	891a1118-11f8-4642-b1b4-cdf247fbc834
09fa7e81-221f-4e1f-82a4-ee96488add9a	Accounting Manager	891a1118-11f8-4642-b1b4-cdf247fbc834
3288bf0f-2d91-4791-8d39-e85bf409016c	Accounts Payable Executive	ccc1acaa-dc00-4b15-af95-c43dc364e5d6
a9e091a1-474f-4803-adda-66c8f55ecd13	AP Specialist	ccc1acaa-dc00-4b15-af95-c43dc364e5d6
79445daa-e22a-4c54-88b6-07e7614e2cdf	Invoice Processing Executive	ccc1acaa-dc00-4b15-af95-c43dc364e5d6
0f830283-a44e-48a0-a281-60c57488719a	Vendor Payments Coordinator	ccc1acaa-dc00-4b15-af95-c43dc364e5d6
a2c35298-e072-455d-9425-95ffadbf11a3	Accounts Payable Manager	ccc1acaa-dc00-4b15-af95-c43dc364e5d6
2bd091f0-148b-4aa7-b697-4120ae438437	Accounts Receivable Executive	484cd0b4-e8b8-4b54-9061-c5c8f692263a
02a10a3e-e664-4160-adaa-64af661abebb	AR Specialist	484cd0b4-e8b8-4b54-9061-c5c8f692263a
d5abd536-65f6-417c-9d9a-053774e025fe	Billing Executive	484cd0b4-e8b8-4b54-9061-c5c8f692263a
0daebf46-6f8f-461f-9b18-9c2b7f37c806	Collections Analyst	484cd0b4-e8b8-4b54-9061-c5c8f692263a
7a461a7a-22c4-4fe5-b15c-e7770d5a3ad0	Legal Counsel	4a119284-dd82-46ba-bf1a-1a718bb93eb8
cb675f7f-8d3f-4d3f-b1de-0d2751bb4e41	Legal Executive	4a119284-dd82-46ba-bf1a-1a718bb93eb8
16dba4bf-1ed8-4477-9cc0-3c8dcb2143c9	Corporate Lawyer	4a119284-dd82-46ba-bf1a-1a718bb93eb8
4ec31d12-e628-49a5-8b13-afc1fb96942d	Contract Specialist	4a119284-dd82-46ba-bf1a-1a718bb93eb8
d45d2b34-e3c7-4481-aaf0-1f29d1d0ba18	Legal Manager	4a119284-dd82-46ba-bf1a-1a718bb93eb8
4b12963d-c508-4db4-ad15-5ebdd32e8081	Compliance Officer	3731b5ce-d647-482b-a85b-e126e0187ce2
657cf8ef-4831-48f4-8abe-f14582f8eccd	Compliance Analyst	3731b5ce-d647-482b-a85b-e126e0187ce2
67e0ad45-fe90-4a93-b1b2-3937dbc04485	Regulatory Affairs Specialist	3731b5ce-d647-482b-a85b-e126e0187ce2
897207ec-9915-4c54-8d26-a4e0afb7f11c	Compliance Manager	3731b5ce-d647-482b-a85b-e126e0187ce2
66e1d83f-c225-464e-b89e-3eb9d0277c44	Governance Risk and Compliance (GRC) Analyst	3731b5ce-d647-482b-a85b-e126e0187ce2
90feff2b-a3ea-4958-afbb-530c8598e4b7	Risk Analyst	bf318e26-ee76-41f9-ad4f-0d97cca4c13b
1283a9b1-b3df-476f-8758-284ca80e9c53	Risk Manager	bf318e26-ee76-41f9-ad4f-0d97cca4c13b
780cad69-3880-4251-b590-9445b5c0e4c7	Board Governance Specialist	a137060a-824f-4cb3-968e-57998cd8d136
d79ed004-58e8-49ff-bde6-a7bc69cb4621	Corporate Secretary	a137060a-824f-4cb3-968e-57998cd8d136
c7f2c2b9-43b3-43a3-a4b1-1e0fad46fcd2	Governance Manager	a137060a-824f-4cb3-968e-57998cd8d136
3d444824-7d20-45c5-bb79-38cf3a05e2e3	Procurement Executive	6ca07d3e-b4d1-49b1-a049-d9759bc07162
cda0fca7-7842-4d8f-a94f-88d22e30be5f	Procurement Specialist	6ca07d3e-b4d1-49b1-a049-d9759bc07162
abc906d8-a9d9-4818-9131-e98569f678d4	Procurement Manager	6ca07d3e-b4d1-49b1-a049-d9759bc07162
d986dcab-adf5-41f9-aa90-0c4b90e6becd	Strategic Sourcing Specialist	6ca07d3e-b4d1-49b1-a049-d9759bc07162
35ba378a-e2bb-4cd4-a8d1-8cffe31e979e	Category Manager	6ca07d3e-b4d1-49b1-a049-d9759bc07162
d8533f3a-0929-4ed1-a6bd-0feaeaa6cfd1	Purchasing Officer	ecc0d440-8806-4882-854a-0dcbb9d4f77d
82b4fe7a-4272-4b77-b199-81108288b5a2	Buyer	ecc0d440-8806-4882-854a-0dcbb9d4f77d
4e6f0cfb-b9a5-44a8-9128-d11b3b0a33d8	Purchasing Executive	ecc0d440-8806-4882-854a-0dcbb9d4f77d
971220c9-395b-470b-a2a7-15df1e8fd624	Senior Buyer	ecc0d440-8806-4882-854a-0dcbb9d4f77d
d9764652-f62e-4b42-b6ca-b3b4da24b0dc	Purchasing Manager	ecc0d440-8806-4882-854a-0dcbb9d4f77d
58f2df4d-a0d8-47a0-838c-d45a185fea2a	Supply Chain Analyst	4ad51c6d-b5cf-4bb3-b7cd-ece577f11ebf
66543ee5-91bf-4669-9aa7-6f64d76129db	Supply Chain Manager	4ad51c6d-b5cf-4bb3-b7cd-ece577f11ebf
ee39b2ec-3d34-459b-b8d2-5db71078a4e6	Supply Planner	4ad51c6d-b5cf-4bb3-b7cd-ece577f11ebf
84f99abb-bc86-465b-8e27-7dc3c16e2454	Demand Planner	4ad51c6d-b5cf-4bb3-b7cd-ece577f11ebf
241f0949-ba77-4cef-a248-edff3b8d9037	Supply Chain Coordinator	4ad51c6d-b5cf-4bb3-b7cd-ece577f11ebf
7963bc9f-22d6-46ff-bba8-cc3e03bfde35	Logistics Coordinator	b63c2bb7-dfba-4c43-927f-90bda1478694
53effb58-612b-4f22-a949-964a1c99e365	Logistics Executive	b63c2bb7-dfba-4c43-927f-90bda1478694
f93a11e5-1b20-4185-a2a2-0f4c8486869d	Transportation Manager	b63c2bb7-dfba-4c43-927f-90bda1478694
309edcb4-3ec3-4411-a9d1-e5673ac8033a	Freight Specialist	b63c2bb7-dfba-4c43-927f-90bda1478694
8caa0aa0-894d-466c-a9f7-1c3f0279b4e7	Logistics Manager	b63c2bb7-dfba-4c43-927f-90bda1478694
9315d6d8-a439-47dd-9921-66b93855dd70	Inventory Analyst	d7df1933-1f09-4809-8846-832b70ec6762
a8da40ef-c348-4543-bb80-61265811fcc0	Inventory Controller	d7df1933-1f09-4809-8846-832b70ec6762
c6de9cc9-5b53-4182-8b59-f02f86893da6	Stock Manager	d7df1933-1f09-4809-8846-832b70ec6762
f787c9c1-cb2f-4394-aa02-390f7a3530f0	Inventory Coordinator	d7df1933-1f09-4809-8846-832b70ec6762
602b8c49-7690-40aa-ae8c-54ad97c1db14	Materials Planner	d7df1933-1f09-4809-8846-832b70ec6762
14620c5d-3968-478e-b898-8774c9acd5d8	Vendor Manager	9eebe634-82ef-4c54-92f2-221f10394289
41eccd7a-187b-4864-93c9-67c2d12a3b09	Supplier Relationship Manager	9eebe634-82ef-4c54-92f2-221f10394289
d36efb92-a574-41e4-98b8-6a97210695fe	Vendor Coordinator	9eebe634-82ef-4c54-92f2-221f10394289
e5411965-e5b0-40ac-971d-895af52f2273	Supplier Performance Analyst	9eebe634-82ef-4c54-92f2-221f10394289
4863788c-5f29-4c6d-b75c-3ea1dcc4712f	Vendor Compliance Specialist	9eebe634-82ef-4c54-92f2-221f10394289
839ea879-7e2a-4770-a401-baa50f8bee60	Warehouse Supervisor	db36d674-53d3-4198-8de5-939e89b89118
\.


--
-- Data for Name: departments; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.departments (id, name) FROM stdin;
806886c9-242c-4546-837f-a0c313bb6257	Admissions
bf679d4a-b027-4fa3-804a-b743eecec630	Student Services
ec430ec2-b51b-4a8d-b150-68a149fe953c	Faculty Administration
ec7d05c3-bd8a-43a8-9763-0014bd3835a3	Underwriting
7d613a69-1563-4e6b-9fc8-1b781bc70434	Claims
d0b9d8e8-3788-444d-bd8c-788e98174713	Loan Processing
d04c60d7-0df4-4784-9ea9-8756d3d6b53b	Credit Analysis
4144aff0-5d87-4182-b117-569003ecdfd6	Civil Engineering
7f743eac-413d-4972-a9aa-2a0e505adc9b	Site Operations
d9d04cc0-b587-46c9-882e-e9e279b0a89c	Safety
4a9d8686-7c78-4410-9040-1f36638eddd8	Project Management
756dd23b-5847-4549-b98c-6a0b0af2f846	Physical Security
b7b4e68a-052c-4bec-b5ce-cb87dc0cc4f2	Information Security
228e90ae-216e-4bb1-a160-c9f4cdd97d40	Corporate Social Responsibility
4a1f10b4-1e84-4973-934c-9f5a0f9096bf	Environmental Health & Safety
1f871f6c-402f-4b4b-9a8c-3d4ec207b0b9	Sustainability
4e031ab6-440e-4416-bc05-5a29512ffb79	Facilities
11d0a86f-7a24-4296-afeb-927ef6b2e49e	Housekeeping
6c2376e3-daf5-47a9-96a3-bd02154ae95c	Technical Writing
5d0c501b-00de-43c0-ac4a-9856a9037e93	Documentation
4e2696a1-9aae-4b20-83df-0971a67066bd	Knowledge Management
0be2a2d9-e20b-4f17-8f64-48745644426d	Management
4791dd21-36c7-455b-9aa9-93535535bbff	Executive Office
0a565916-be74-4044-a363-91a6b3a3da79	Strategy
281e940b-c398-4730-a2d7-cf30bc54d5ae	Corporate Planning
d5b775b8-3f2a-4dfb-b63c-2247add904ab	Nursing
df00a405-c5da-4dd7-a086-8388d54c2325	Board Administration
7eb97478-ab30-4ca9-82aa-3fac952b60e8	Software Development
212c3db8-351e-4de9-bb16-a9f90408df68	Custom Development
30ed85cd-9da7-4dcf-8410-b412b9569f6e	Web Development
8ee1b7a5-f46a-48a5-801b-964b39a62294	Mobile Development
a970f973-42c1-4dcf-a3ec-352d648268d0	DevOps
f27c80a1-a8f1-4e0b-b9e2-23c88697c87d	Cloud Engineering
d88005e4-0477-4a66-8098-5ce139977a52	Infrastructure
e9ee5dbf-bd7d-4a97-a3e4-9a63801feba1	Network Administration
ff18b43b-5db7-4418-a6aa-5fd379c6858c	Database Administration
da017d77-3c9d-4389-8d35-5e7e687e7d2f	Cybersecurity
c531c355-e375-4fac-acc3-137c41f8f661	IT Support
78ea9553-3e24-468f-8390-9d06fe55c05a	Technical Support
204c0d65-7116-4860-bc76-38999cb8d6fc	QA / Testing
1b8aee27-60cb-49ed-9c9e-3cf747ebdf4c	Data Engineering
9bb6c08e-f7f6-4040-b924-e2715b475064	Artificial Intelligence / Machine Learning
f1b93702-98e9-4a98-8b77-ec2152ae3b1b	Business Intelligence
dd5c1ea8-0ff7-442f-94ac-9629914d9916	Designing Team
5de73471-a308-4c1a-a59f-6982d8b2a0b2	UI/UX Design
2afa6ca0-3ecb-40b7-82ff-8ddc65fb27b9	Graphic Design
a9b34308-bc4e-4561-873c-7064a8229474	Product Design
dbf6dc9e-87ab-4bdd-9be4-285e797ba53a	Video Production
7ad5f191-11dd-411e-b88b-fdda71e915e0	Content Creation
72b81592-f48a-4753-87aa-25142749660f	Sales Team
866c8990-75fc-4408-8d32-c4ac18b709a6	Business Development
56c22dfc-50f7-4bec-89f1-e42cdc83aee6	Account Management
ba206b67-67de-497a-89fe-d70c3be4a076	Inside Sales
d1663ee3-8c19-40c3-a694-4d9745b09944	Field Sales
9aff532f-c7d6-4184-8aca-b9e431fac301	Pre-Sales
94d70619-4abc-4169-a8e4-e753f66f029d	Customer Acquisition
788a60ee-04a4-4814-88ac-34db4f46a683	Digital Marketing
9a19173e-fcdd-4d43-a6b8-ab5f36ef98e1	Brand Marketing
420f8434-c908-4017-9989-099acc6d4390	Performance Marketing
454ea24f-2708-4493-bb0a-6eaad34977d2	SEO
2203bbf9-9bff-435c-a38e-18aad0f2293d	Social Media Marketing
3efc496a-754c-4038-b137-2cf2191fa7dc	Product Marketing
ab2131cb-c15e-4057-bbbc-2b993b021810	Public Relations
913ea625-b960-49e0-b206-36f472c18870	Communications
17917313-19b3-4d64-9c18-387af7a4f2af	Human Resources
29e5e8d0-380d-46f0-939c-88e54635307e	HR Administration
0b4eae8a-7f8a-4b37-861c-ac0970ab0be8	Talent Acquisition
3f325aea-7ea9-48c4-8f79-9b679b64dd10	Recruitment
380525a9-6c6f-4fa2-9900-511c9bf5b0d3	Learning & Development
f0261df9-c25b-48fa-8530-a5daafb1b9f4	Employee Relations
2b890dca-cda8-4d9d-b0e8-b093e371bbeb	Compensation & Benefits
286647e9-abad-4196-afc0-7df8922cf632	Payroll
c65513da-8aad-4132-a33e-a156f3c7b02c	Operations
83f9c3b8-5f99-4fd2-9f6c-ce7adf809803	Process Management
6a171a6c-12b9-44ac-a7e5-f267a3b44810	Service Delivery
01cb55d6-64ea-4cc0-aa92-465417c5bcf6	Resource Management
1c6a31f1-6543-4a49-87e0-ff02eb88d048	Administration
ab54422a-2bc0-4ad7-ae4f-070b50302e28	Customer Support
b91681aa-8e4f-44fc-aa1c-d160e1e17657	Customer Success
1edfa9b9-bc5b-4ca5-bdd9-326a1cdfd67d	Call Center
78b12cac-9856-42a2-b713-29e377e27adb	Help Desk
685d76db-b251-4db9-9eb2-1a067fb0ea3e	Finance
891a1118-11f8-4642-b1b4-cdf247fbc834	Accounting
ccc1acaa-dc00-4b15-af95-c43dc364e5d6	Accounts Payable
484cd0b4-e8b8-4b54-9061-c5c8f692263a	Accounts Receivable
1b815285-c97e-410d-89ac-adceb1647b18	Treasury
ab695966-9235-4a89-8fea-e7837dbfac53	Taxation
66e70f8f-cdd3-4833-bc13-c43b00020850	Audit
bdf6a7fb-161c-497d-9d74-30c73e3f582f	Financial Planning & Analysis
4a119284-dd82-46ba-bf1a-1a718bb93eb8	Legal
3731b5ce-d647-482b-a85b-e126e0187ce2	Compliance
bf318e26-ee76-41f9-ad4f-0d97cca4c13b	Risk Management
a137060a-824f-4cb3-968e-57998cd8d136	Corporate Governance
6ca07d3e-b4d1-49b1-a049-d9759bc07162	Procurement
ecc0d440-8806-4882-854a-0dcbb9d4f77d	Purchasing
4ad51c6d-b5cf-4bb3-b7cd-ece577f11ebf	Supply Chain
b63c2bb7-dfba-4c43-927f-90bda1478694	Logistics
d7df1933-1f09-4809-8846-832b70ec6762	Inventory Management
9eebe634-82ef-4c54-92f2-221f10394289	Vendor Management
db36d674-53d3-4198-8de5-939e89b89118	Warehouse
d5a251e1-f4bf-477d-8cfe-f213811330b6	Production
f065a9a8-5eb8-4f21-ba73-4cad30d35727	Manufacturing
4af11899-18be-4a9e-aed4-187eb4ad4f13	Quality Control
7468d9fb-c35c-46e6-8a58-f7a7611d5411	Maintenance
32ba180f-541e-45fc-88a8-f1f798a99026	Industrial Engineering
4d3c38f4-782f-4001-be30-b21a156fba66	Research and Development (R&D)
460c3fe1-b417-43f4-8769-6d966515de34	Innovation Lab
6ffa2b41-f770-4951-b5c7-4be5be7bba7f	Product Engineering
a85a6137-4345-4551-8831-883f4f5f98d5	Data Science
42330e1e-d85e-44b1-b839-abe1ab9ab9b2	Analytics
be34a9dd-dd0d-4b89-94a8-cf849af2a9d4	Reporting
e9084bda-57e4-4720-949b-f14e097bad34	Data Governance
1a348e2b-282c-4f23-977f-ca8b456cf789	Product Management
371374b9-a600-470f-9f8b-b019dbbd8096	Product Strategy
ce4697b7-aedd-4897-89bd-f3777b884f8a	Product Operations
b2589ef6-b91f-46d0-b849-d578bad4ee4d	Medical Administration
113e90d2-12c7-4a76-8953-1a243c0e15dc	Laboratory
e5f7b741-f815-46a4-93ea-163aeb322f2a	Pharmacy
7d837164-3df5-4188-ad8d-4f63edb198c1	Clinical Operations
f665285a-3964-40fd-9827-23ac6fcda87d	Academic Affairs
\.


--
-- Data for Name: external_candidate_matches; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.external_candidate_matches (id, candidate_id, job_id, score, highlights, gaps, fit_reason, created_at) FROM stdin;
\.


--
-- Data for Name: external_candidates; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.external_candidates (id, job_id, full_name, email, phone, state, city, department, sub_role, industries, available_shift, total_experience, current_ctc, source, professional_journey, resume_url, salary_slip_url, experience_letter_url, profile_picture_url, status, applied_at, updated_at, embedding, is_matched, date_of_birth, gender) FROM stdin;
\.


--
-- Data for Name: imported_user_passwords; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.imported_user_passwords (id, user_id, email, plain_password, created_at) FROM stdin;
\.


--
-- Data for Name: interviews; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.interviews (id, seeker_id, provider_id, job_id, title, agenda, scheduled_at, interviewer_name, created_at, updated_at, scheduled_period, source, application_id) FROM stdin;
\.


--
-- Data for Name: job_postings; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.job_postings (id, provider_id, title, description, required_skills, experience_required, job_type, salary_range, industry, posted_by_name, location, is_active, post_count, ai_interview_enabled, selection_threshold, embedding, created_at, updated_at, shift, perks, employment_type) FROM stdin;
38206023-d55d-40f0-9182-9fc8caca6519	abcf2d6b-b1e9-4a83-a2f0-5443768ef727	Python developer	<ul><li>We are seeking a dedicated Python Developer with 1 to 4 years of professional experience to join our full-time, in-office team in Moga, Punjab</li><li>This day shift role requires strong proficiency in Python, Django, Flask, SQL, Git, and REST APIs</li><li>Candidates must demonstrate a solid understanding of Unit Testing, Data Structures, Algorithms, and Object-Oriented Programming, coupled with excellent Problem Solving and Communication skills</li><li>Experience with Docker, AWS, and Agile methodologies is highly desirable</li><li>We offer a competitive salary in the range of 1-4 LPA, along with attractive perks including Flexible Working Hours, Weekly Payout, and Overtime Pay.</li></ul>	["Python", "Django", "Flask", "SQL", "Git", "REST APIs", "Unit Testing", "Problem Solving", "Communication", "Data Structures", "Algorithms", "OOP", "Docker", "AWS", "Agile"]	1-4 years	in_office	1-4 LPA	\N	Michael Johnson	Moga, Punjab	t	10	t	80	[-0.010632811,-0.015212549,0.019917225,-0.053631186,-0.0009901947,0.015649494,0.009972137,0.024558712,0.010531701,-0.00902793,-0.02306149,-0.0062746983,-0.004398813,0.0055808634,0.12332128,0.0030451638,-0.009071896,-0.008780813,0.014798023,-0.0047060326,-0.020501653,0.020751705,0.025422232,-0.030557457,-0.0052871923,-0.028965205,0.0018911085,0.00433498,0.059521813,-0.0100028515,-0.0049120365,-0.009805457,0.021455778,0.04387331,-0.018870523,-0.004751189,0.024732437,-0.002378127,0.00035709437,0.020639578,-0.025165303,0.016116887,-0.007616931,-0.005239153,-0.01463705,0.0074936063,-0.01407365,-0.015771074,-0.013421768,0.01803344,-0.018340364,-0.00789356,-0.029626964,-0.1819152,-0.016600069,0.0013186396,-0.004105647,-0.009448085,-0.001543802,-0.022602798,0.0022602715,0.04173468,-0.03365732,0.006246837,-0.010661013,-0.008983937,0.012995119,-0.0031373003,0.017878348,-0.023313453,0.013907727,0.007869004,-0.01874921,-0.046789087,-0.01133959,-0.01874019,-0.024258452,-0.017130766,0.007973561,0.0053330837,0.0072923875,-0.015413581,-0.008331645,0.0010957881,-0.00539543,-0.012206232,0.004695095,0.016712397,0.031608876,-0.014046442,0.00262812,0.021277893,0.0011364787,0.044172425,-0.027969785,0.0036602053,0.008968387,-0.0074767745,0.017419055,-6.441123e-05,-0.013525774,-0.021883912,0.010944198,-0.010230873,-0.018335313,0.00108246,0.012269397,-0.016228585,-0.03153023,-0.006125203,-0.011689109,-0.01333317,-0.010933316,0.043733858,0.01410882,-0.14127953,0.01462034,-0.013496093,-0.0006827802,0.016292104,0.0054638586,0.008503069,0.017005313,0.034489293,-0.0019749997,0.0045593097,0.020433791,-0.0140251815,0.0023540126,-0.0055104466,-0.0033955395,-0.019664852,0.032697532,-0.0019226081,0.00618873,0.011963757,-0.017108446,0.009677951,-0.03242644,-0.011418345,-0.027180834,0.029225599,-0.0011623817,-0.0018978319,-0.012199857,0.015850538,0.010731667,0.0026815056,0.012035457,-0.0052483794,0.014425629,-0.03253666,0.027964948,0.0075670746,-0.021142213,-0.026076462,0.017444998,0.009462984,0.00023732072,0.0026275322,-0.026103005,-0.018515179,0.014834432,0.003389354,-0.0038032488,-0.001967111,-0.018287601,0.03291319,0.018495314,0.0050646914,-0.022713963,0.020871311,-0.004967102,0.023481423,0.025121586,-0.010640666,0.0077232076,0.0040159356,0.01725558,-0.035873134,0.024422368,-0.0026802786,0.0093666315,0.023317248,-0.025156096,-0.019857882,-0.018130088,0.0060135364,0.010599389,-0.02072077,-0.0016317635,-0.004851396,0.010017008,-0.020720594,-0.007377875,-0.04798481,-0.018025609,-0.0075222566,0.0017617748,0.02897293,0.008360973,0.009448289,-0.0059080375,-0.018890787,0.019409128,-0.010453021,0.0057463585,-0.006430399,-0.021379158,0.008279978,0.015932899,0.010394206,0.028558709,-0.0037184174,0.002051981,-0.0069205323,0.015509377,-0.013346789,-0.015589981,0.008002947,0.0022518272,0.011463198,-0.0015931837,0.015259312,0.006183631,-0.0049969256,0.02628595,0.0147049595,-0.00070546335,0.012911995,0.012704224,-0.015753342,-0.036174614,-0.0028792473,-0.005543498,-0.017196568,0.019184723,0.021576313,0.0012652772,0.014287464,-0.00071181194,0.014649772,-0.01677166,0.0034193373,0.00657383,0.009015485,-0.019838022,0.005451614,0.026309863,-0.025807848,-0.03334051,-0.030948281,-0.0153787825,-0.013964418,-0.008009517,-0.014955858,-0.010021754,0.0016866559,0.019216105,0.007489561,0.005560141,-0.0031514785,-0.016859662,-0.030512273,0.024114408,0.0008443956,-0.0047621927,0.0033032866,-0.0049447203,0.037972644,-0.0034970955,0.01942121,0.023303485,-0.001386542,0.009892753,-0.015127369,-0.0113964835,0.03027335,0.0017474755,-0.018084586,0.0051496644,0.022461176,-0.0118776215,-0.031524003,0.017718779,0.013930581,0.013853508,-0.0234605,0.023019034,-0.005322236,-0.001504545,-0.016089011,0.006402533,-0.04351929,0.025846591,-0.00026941716,-0.020086732,-0.02922885,-0.002014865,0.0020781616,-0.0022810565,-0.036845397,0.014049058,0.04274764,0.0301531,0.0006446591,-0.0037687044,0.045167927,0.014577942,0.012988817,0.024306947,-0.010595727,-0.00666332,-0.02293729,-0.017651789,0.0052166753,0.023400549,-0.0067927693,0.013433822,0.02616867,-0.011200707,0.006822405,-0.018769983,0.036059268,-0.0040133605,-0.006885854,-0.0074802707,0.032667737,0.0363126,-0.011558038,0.010299543,-0.0041814414,0.0017837413,-0.015581122,0.0067325435,0.023796456,0.03793033,-0.011010467,-0.013509202,0.019015219,-0.007924966,-0.0071450355,0.01388127,-0.024072133,0.002421691,0.0045337686,0.0044288235,-0.01822928,0.01613211,-0.0072139814,0.00248136,0.0046979324,-0.008968999,-0.036544222,-0.0026029418,0.02025203,0.017923716,-0.011282145,0.0070147053,0.03308983,-0.011985037,0.020694528,-0.0025026489,0.011638121,-0.009532474,-0.0053603947,0.0030919053,-0.00434867,-0.005230117,-0.002980591,0.000393543,-0.023934325,0.013261834,-0.012479674,-0.008857528,-0.016649079,-0.030793423,-0.008055965,-0.029427346,0.015732579,-0.025240187,0.032284286,0.003138549,0.022155412,0.014804558,0.016728861,0.027323954,0.0046784603,-0.00323266,0.00423676,-0.0041209855,-0.008682652,-0.014527947,-0.010450631,-0.003872321,-0.013632059,-0.014296766,-0.0014516986,-0.034679618,0.002823412,-0.013663336,0.020313341,-0.003645216,-0.005112793,-0.0043811915,0.0102643985,-0.019679029,-0.0053378586,-0.017380165,-0.010005501,0.015710149,0.0038299074,0.033627454,0.00082554994,0.015282891,0.002355548,0.008985073,-0.0064269244,0.03301064,0.0045607886,-0.0072121257,0.03787195,-0.02794522,-0.004671501,-0.012752173,-0.005769715,-0.066030405,-0.00015635436,-0.012409688,-0.01963661,-0.017881343,0.007445705,-0.011108523,0.011628329,-0.01300872,-0.0040557017,-0.0056310133,-0.012180093,-0.0064754705,-0.022908766,0.020641293,-0.004162431,-0.0032757209,-0.015241044,0.030689912,-0.0022795126,0.004716714,-0.016668536,-0.014604267,-0.015530046,-0.0009267913,0.03210585,-0.0024153946,-0.021858167,0.0017905018,0.0004883986,0.0049608033,0.00058159954,-0.024268989,0.028103173,-0.013178804,0.013610928,-0.008950008,0.022616953,-0.018566169,0.005796127,0.015521797,-0.0033025662,-0.00934701,0.020096082,-0.013626222,0.00511978,-0.030713793,-0.00030166926,0.006585138,0.01865159,0.018769918,-0.033089142,-0.0066325697,-0.021693887,-0.0076501723,0.0035647175,-0.017114475,-0.012405587,-0.001556549,0.0068680895,-0.014972492,-0.008034234,0.034504704,0.0067796325,-0.0018948818,0.045595665,0.007518145,-0.025127271,0.0074631856,-0.028670738,-0.012747995,0.0036520374,-0.012729216,0.003763422,-0.02263541,0.004019042,-0.02075705,0.012516109,-0.009894379,-0.014740007,-0.0012518596,-0.0032985886,-0.0021959944,0.010016071,-0.021843262,0.013775182,0.018886572,-0.00090113207,-0.006118144,0.013400946,0.016119275,-0.028594133,-0.039161783,-0.030157829,0.012037346,0.008482132,0.009615548,0.008348063,-0.0034880075,-0.0053363084,0.0054391157,0.01548371,0.010406318,-0.0037211834,-0.0049908846,0.03187247,-0.005633913,0.015671406,-0.005667147,0.010321007,0.020081995,-0.0061060246,-0.0074539143,0.021098565,-0.019523935,-0.025855433,-0.009946174,-0.009294252,0.02230885,-0.07030894,0.0031498768,-0.012548945,0.009253653,-0.008225219,-0.018069591,0.001122408,-0.03193256,0.010154597,0.009360597,0.0067728003,-0.0051678363,-0.0027412798,0.004351333,-0.012009417,-0.027984492,-0.006870687,0.026425837,0.0035115688,-0.024291944,0.014498701,0.019859849,-0.006944288,0.019947493,-0.0071295397,0.005744029,0.014649337,-0.021042429,0.002107135,0.018123461,-0.025786808,0.0044070743,-0.012072512,0.042616244,0.012079086,-0.017506251,-0.011724069,-0.006563073,-0.022196816,0.01891575,-0.0077542365,-0.0012401941,-0.032491956,0.013851471,0.015113752,0.0056343377,0.0014019329,-0.0048126685,-0.014148651,-0.014167353,-0.04393542,-0.016543444,-0.007925543,-0.0013630219,0.00237903,0.0035608627,-0.005514499,-0.0014222633,0.010995913,0.01050832,-0.031025488,0.0017117377,0.029766673,0.031302817,-0.0015790056,0.013655279,0.013704197,0.009099799,-0.011396703,-0.0023245362,0.0054622185,-0.010019409,-0.012429687,0.016238473,0.00963268,0.0087175565,-0.014493735,0.007250319,0.0015625515,-0.017730126,-0.030713856,0.0065051424,-0.04207613,-0.0016335361,0.030903067,-0.022150198,0.0019169612,0.030548947,0.03355435,-0.0061900318,-0.0006242589,-0.007934909,-0.003632682,-0.00020220068,0.017711597,-0.008249325,-0.0070887017,0.02293823,0.037665185,0.016429776,-0.014198704,-0.029808823,0.0071978746,-0.009027807,-0.008054463,-0.002339269,0.008320859,0.008503939,-0.010057003,0.021644263,-0.0014316377,-0.0071084113,0.022948701,-0.19167596,-0.011107159,0.0061031664,-0.0071847397,0.01221849,0.00989691,0.00633327,-0.0018372744,-0.020833593,-0.018767107,0.0395495,-0.014318549,-0.027119659,-0.011724498,0.012279479,0.09748698,0.010720634,-0.02001579,-0.0056487448,-0.007766188,-0.011443843,-0.016389187,-0.0305471,-0.018492453,-0.022707837,-0.029121801,0.00024908458,0.007215193,-0.003921729,0.017893942,0.02032071,-0.0048164777,-0.013505632,-0.022741077,-0.025877595,-0.0037728725,0.022081647,-0.0054701087,0.0032317976,-0.0020572918,0.020834662,0.0011129698,-0.018473566,-0.0056516076,0.04123866,-0.014199108,-0.009507771,0.0043671383,-0.0011787298,0.00881527,-0.012060213,-0.06897376,0.020676829,0.009403297,0.00081543054,0.010132792,0.008356575,0.0027069808,0.0039223973,0.011548653,0.0064766756,0.020450223,0.0020605873,0.01776352,0.00492307,-0.019359872,0.019419288,-0.0031350972,0.010839636,-0.0019036555,-0.0076522725,-0.016679887,0.016697973,0.0031761567,-0.0063055907,0.008877003,-0.02277221,0.020214656,-0.012096555,-0.0070791985,-0.023293773,0.023693746,-0.0032338211,-0.029787485,-0.03231942,-0.028697405,-0.003784187,-0.0016083849,-0.003937647,0.007651033,-0.011644371,0.018196369,-0.008287484,-0.008242149,0.029375535,-0.008388188,-0.0024771127,0.020431688,0.020907823,0.0030487606,0.008953048,-0.03452763,0.012021903,-0.025476534,-5.1417886e-05,-0.012662591,0.030898934,0.021062072,0.04390418,0.021101583,0.0025278148,-0.003319649,-0.006967254,-0.008271093,0.010914833,0.005822855,-0.0022110275,-0.024530668,0.001245797,-0.011130973,-0.003121419,-0.0010843202,-0.0021971546,0.00066512486,0.0026000007,0.0054464005,-0.001591704,-0.00041349162,-0.000858079,-0.01453948,-0.00072619546,0.0010171052,0.010985826,-0.011985962,-0.019958932,0.0057849726,0.0060136984,0.005774889,0.009609261,-0.02212488,0.01745679,-0.01024985,0.0016174132,-0.017938316,0.0048498693,-0.0038149825,0.0009840735,-0.004177717,-0.009134921,-0.008081543,0.009060236,-0.030374177,0.004300393,0.012993561,0.0085405335,0.01816102,0.0018362238,0.010104749,0.0045189853,-0.009882095,-0.008770949,0.0017024432,-0.008528206,-0.01870393,-0.012570391,0.022539107,-0.0015001433,-0.0083881775,0.00024717674,0.018366678,-0.002183784,-0.002332216,-0.0023004545,-0.022459846,0.016836561,0.0050981333,0.014975387,-0.00024066794,-0.015406699,0.009232283,-0.032310717,0.0032248474,0.012873959,0.005080371,0.004894714,0.014166492,0.00561973,-0.008430212,0.005807007,0.016067406,0.002047588,-0.029272318,0.017247716,-0.007964244,0.0013275249,0.0021350153,-0.0116171,-0.012994559,-0.003651269,0.009240996,-0.00011367012,0.005846023,0.0021617888,-0.0024344327,-0.014665285,0.0028369273,9.763639e-05,0.0089066895,0.011400037,0.0013949645,0.0017734064,0.0029508963,0.005778209,0.01318405,-0.0123717915,0.022042159,0.003111789,0.0002571537,0.0061803446,-0.014188084,-0.012287546,-0.007587947,-0.0019680338,0.0039140405,0.0046705008,-0.0071594343,0.0018749343,-0.006893539,0.0010116962,-0.007164217,0.0012103833,0.0056248326,0.0055894423,0.00750941,-0.0024621307,0.002380586,0.0028544012,-0.0007493471,0.007440661,0.008430807,0.009913003,0.018945893,0.005325268,-0.00032480265,0.0013441404,0.00031999615,0.013459414,0.0019805576,-0.007274169,0.007535241,-0.003142828,0.011164294,0.014646178,0.013393172,-0.004107857,0.0024801076,0.006069684,0.014009974,-0.0077451807,0.0026698657,0.0072877104,-0.007441621,-0.0030395663,-0.007161344,0.022613576,0.0044967243,-0.006562177,0.02122279,0.004650696,0.010928687,0.006571363,0.003492581,0.019107006,0.0060355924,-0.011537976,-0.014308696,-0.010784386,-0.0072579975,-0.000501208,-0.0050195768,0.011794929,0.0037794048,-0.024124242,-0.003447874,0.0064883265,0.0034209285,0.0150733795,-0.0081657935,-0.0056432807,-0.01806897,0.01110273,0.0095679555,-0.018091004,0.013620512,-0.005169137,0.01917784,0.0017998271,0.0016836035,0.0035559193,-0.0018610264,0.0067673405,-0.0028373448,-0.000703016,0.00018547755,0.030288901,-0.025278946,0.0105451625,0.0059522693,0.017023694,-0.00065666094,0.11007653,0.015885467,-0.00519798,0.003177394,-0.013434472,0.025944158,0.00029978724,-0.036685906,0.007834695,-0.0053060493,-0.0053173257,0.0030003071,-0.0042674867,-0.017247133,0.006044403,0.0007433933,-0.0089616915,0.008411865,-0.012540287,-0.0014320717,-0.018854914,0.0049016667,-0.016774813,0.0036725025,0.012991259,-0.009761595,-0.0018470769,0.0052440036,-0.008220683,0.017245663,0.007050316,0.0065753227,-0.0105745075,0.0032651639,-0.013805549,-0.0032496513,-0.018439172,0.024253517,-0.008771228,0.010651912,-0.00642601,-0.0036390568,-0.0019909495,0.017150473,0.002221437,0.01806987,-0.010643111,-0.0022467724,-0.018590042,5.8285514e-05,0.009604265,-0.00060486596,0.0046035857,0.0042178994,-0.011411094,-0.012028145,0.0007261432,0.007929909,0.0073377984,0.0030212132,-0.003644601,0.016318347,0.0015604672,0.0018432133,-0.011782229,-0.028529782,0.002090373,-0.015653322,0.004789403,0.010095354,-0.002166192,-0.016414631,0.005222972,0.0064861383,0.028392028,0.009955115,-0.0071411827,-0.0026574228,-0.01741946,-0.0026654496,-0.0038314469,-0.0076302006,-0.033533257,0.007186287,-0.0104686525,-0.0067696185,-0.014400031,-0.00999146,0.0043599,0.00029385864,-0.0038671724,-0.015398685,0.013838877,-0.006876744,-0.010588572,0.0077579482,0.027145697,0.006910854,-0.026996497,0.014709169,0.006381792,0.002830874,0.0050151534,0.0012821159,0.013374655,0.012340576,0.017522011,-0.015184117,0.006699176,-0.00012198775,-0.0079467185,-0.004864136,0.0059769847,-0.0055915555,-0.007846535,-0.011973217,-0.0005707881,0.0010288903,-0.009768589,0.011436738,0.017543763,-0.00045979265,-0.008977927,0.016637405,0.0023325426,0.014526938,-0.0028356838,-0.011080049,0.0057838466,0.003347125,-0.0027967365,-0.004099489,-0.0050863004,0.0018577236,0.006570433,0.0074280677,0.018332144,-0.00019764421,0.022429863,-0.002521208,-0.013039199,-0.0024357191,-0.0046718675,-0.008685016,-0.0070690415,0.0043059406,0.006137851,0.016633214,-0.009653278,-0.025584238,0.0025238898,0.0025066093,0.0046439148,0.03164399,-0.0010281028,-0.009164715,0.006745981,-0.008691099,0.0008126327,0.00875048,-0.010349034,-0.0048131538,-5.8182733e-05,0.005376264,0.0047378163,-0.00960015,-0.005505783,0.009066122,-0.017655432,0.025256617,-0.0016202976,-0.017366128,0.0140515175,-0.010111219,-0.0030533038,0.015678471,-0.0036832227,-0.005239554,-7.0410584e-05,0.012963447,-0.016475629,0.006410009,-0.020761805,0.0021508909,-0.0020615682,-0.013943869,-0.00067842216,-0.005237095,0.009219077,-0.018090762,0.008030866,-0.014840944,0.006484947,-0.013255131,0.0016985068,0.008452833,0.0049165296,0.008705865,0.0044365837,-0.013793377,0.010890193,0.0068376963,0.0071686227,-0.0052880924,0.020694412,0.0013823212,-0.00016514273,-0.009857924,0.0054046,-0.008895794,-0.009844656,-0.01985917,0.0051617967,0.0070358706,0.0050540725,-0.016027587,0.0048326775,-0.018230291,-0.018230913,-0.0012123799,-0.009703359,-0.011275408,-0.0013059237,-0.00023087827,0.014411964,-0.012122755,-0.0052984403,0.013233232,-0.017890349,0.014586004,-0.001381062,0.00803021,-0.011265984,-0.0077779973,-0.00063712744,-0.0065133683,0.011210578,-0.018532591,0.008693998,0.0015849614,-0.008115953,-0.0025286372,-0.008798829,-0.005572123,-0.0050327047,-0.010076041,-0.004994489,0.015114585,0.012047568,-0.0035305037,-0.0035811863,-0.011620571,0.0017723589,0.0029278947,0.0012701068,-0.0042555416,0.010710593,-0.04357163,0.00032061327,0.006684586,0.0048156455,-0.00056387956,-0.015899003,-0.012614634,0.019049728,-0.0051493593,-0.002290892,0.0028527167,-0.009461079,-0.006770809,-0.013781522,-0.002564062,0.0062347106,-0.0074635283,0.013479973,-0.0019024689,-0.009279375,-0.022563666,0.0027723298,-0.009135639,0.0009540928,-0.006285129,-0.014235294,-0.0075999857,-0.004488045,-0.0030781173,0.0003586972,-0.0057855453,-0.0009674576,-0.019311618,0.0039359434,-0.014098018,0.010198166,0.012887231,-0.0052135363,0.014191368,-0.018411323,0.004572776,0.011508007,0.0024203204,0.0051355143,-0.010476258,-0.003729223,-0.007836415,0.0024732952,0.0109301815,-0.005923613,-0.002061271,0.016171908,-0.0037314154,0.019210005,-0.0035605044,-0.0031678325,0.0065571824,-0.0028096423,-0.0038051482,0.0050882758,0.0029264782,0.008082863,-0.011535367,-0.0016898669,-0.016928026,-0.013320961,0.025871988,-0.024858028,-0.0057265135,0.012384051,0.0048198537,-0.0025293187,-0.0051884195,0.006649694,-0.011716837,0.0041772,0.011013532,0.014197383,0.001773592,-0.0026383095,-0.009641454,0.005810268,0.0039978214,-0.009266834,-0.006099223,0.012424804,-0.015000473,0.002368998,-0.015009788,-0.0042979554,0.009543589,-0.010276332,0.007480256,-0.016554518,-0.011440111,0.01108694,-0.009045539,0.008550473,0.0009690631,0.012833221,-0.0063206498,0.0043299,0.012911979,0.009626301,-0.020245006,0.013555893,-0.0036359099,-0.0035287454,-0.00013480001,0.004524648,-0.006552729,0.0013457531,0.0075871223,-0.0015652007,0.011015662,0.0009953835,-0.003655383,0.0018991746,-0.0035333983,0.0071526165,-0.027449647,0.010240843,-0.0011603002,-0.014418149,0.012120851,0.0051989113,0.0033876118,0.0059859273,-0.008332011,-0.005269177,-0.0029314372,-0.0004535644,-0.008004419,0.011718526,0.009343121,0.009073751,0.027125007,-0.013143395,0.0019674622,0.0039925505,0.026763642,0.00785452,-0.020332552,0.0036192017,-0.010587057,0.0034603039,-0.012778895,-0.0069113243,-0.0068454524,0.010081627,0.003955915,0.016265009,-0.0057361475,0.0008741225,-0.0040515857,-0.012497265,0.021739403,-0.011465236,-0.0036429595,-0.02036677,-0.0044230414,0.0056743687,0.008496516,-0.005329417,-0.010251435,-0.011308268,-0.01715751,0.0028656907,-0.01814434,-0.0069434075,0.0013583078,0.006042034,0.00845358,0.013098694,0.012152408,0.010582594,0.023741994,0.0034787895,0.008854034,-0.011883366,0.006561064,0.00030101903,0.010925893,0.0016693288,0.013413186,-0.010178538,-0.0157391,-0.00022319444,0.0068874876,0.01085875,-0.009195574,4.6978654e-05,-0.004367374,0.002088427,-0.001779364,-0.00022970367,0.00073301926,-0.0046523525,-0.0008476897,-0.006845369,-0.0045483806,-0.010761267,0.010267167,-0.013096116,-0.0016654296,-0.08872603,-0.006000949,-0.0051309504,0.0059325453,0.0045525352,0.0029504676,-0.0131142475,-0.009736374,-0.019242935,0.0007969722,-0.0064910133,-0.010014152,0.0024437355,-0.02041947,-0.0070509254,-0.03546167,0.0052024736,-0.002385056,-0.015247423,-0.005691623,0.021539282,-0.0015762785,-0.0037899255,0.015942398,-0.00450857,-0.002697166,-0.031225469,-0.021136206,-0.0040648994,-0.0021078507,-0.0050097303,-0.021537345,0.0023117848,0.018548096,0.029016547,-0.012354082,0.009762468,0.0075311256,-0.13569923,-0.0170667,-0.0007503931,-0.002106034,-0.005370394,-0.006564198,0.012046997,-0.0021481314,-0.0063181235,-0.006486183,-0.025929766,-0.005673559,-0.0056413794,-0.0018614827,-0.00020543173,0.008806205,-0.0006631259,0.01166187,0.008872896,-0.00039836287,0.0048094178,-0.015217615,-0.01238645,0.014518978,0.0013505233,0.010687575,-0.0003742264,0.0062107877,0.012388391,0.009430361,0.03669458,0.0007542061,0.0012072937,0.005975409,0.0004896978,0.016925296,4.8382055e-05,-0.0034029349,-0.009652382,-0.0016399954,0.010837329,0.004017079,0.016686501,0.005229318,0.016364757,-0.0016365749,0.009182255,0.0022566323,0.017964331,0.009921736,0.009915552,-0.0072371163,-0.0128325615,0.005408365,0.0025845303,-0.007893272,0.015852813,0.009758508,-0.022391075,0.014469343,-0.026486019,-0.015643159,-0.019655598,-0.0010857098,0.007108279,0.008381432,0.015694963,0.011728212,-0.024221698,-0.0027083845,0.0059833857,0.05501952,-0.012182161,0.015653454,0.009406454,-0.015943948,7.594433e-05,0.003318996,-0.0055398294,-0.01112858,-0.0051254975,-0.019689297,-0.004025311,0.0050876313,0.012578178,-0.0021462152,-0.004291759,-0.010116701,-0.0058596567,-0.04194216,0.012177461,0.010126623,-0.014592526,-0.0028621822,-0.006150785,0.008615581,0.009540542,0.008089441,0.008383361,-0.004923127,0.0011916326,0.004208792,-0.0016642442,0.01698198,0.005829124,0.011667987,-0.015905298,-0.011154323,0.010504265,-0.007729076,-0.019956835,-0.02035375,0.013368971,-0.009763564,-0.011493755,0.0146180205,0.0021296954,-0.0068002674,-0.006035211,0.0003690922,0.022045417,-0.0082705105,0.010471817,-0.0070330394,0.017858492,-0.0020839556,0.0025389907,-0.013973905,0.0005096722,0.035584465,-0.012094766,0.029399939,0.008912941,-0.019528225,-0.0025167724,0.010838564,0.00090080505,0.0038690327,-0.013690696,-0.016093368,-0.0070411162,-0.016938252,-0.010250091,0.0004669764,-0.028231163,-0.024065256,0.020455912,0.019980244,-0.010905798,0.01669039,-0.023485558,0.0043377653,-0.007409283,0.008204931,0.004068795,-0.020969626,0.009691283,-0.011524537,0.0012168881,-0.0050953887,0.008413326,-0.002114729,-0.012675636,0.0006019508,-0.01756201,-0.0011534635,-0.004797067,-0.007552625,0.009518268,0.0025556267,0.023303239,-0.010088235,0.0023858522,0.011330456,-0.0030760828,0.016010208,-0.00020254416,0.016386036,0.010725269,0.007870269,-0.03150027,-0.01818888,0.008943611,-0.01744897,0.020452963,-0.0013734985,-0.0040749307,-0.011206932,-0.030791355,0.016442992,0.01455099,-0.017590811,0.008673917,-0.0070162495,-0.03111815,0.01191465,-0.02257903,-0.0047857156,0.0030296294,0.020657359,-0.004080727,0.020632068,0.0070620705,-0.17980239,0.012652234,0.0011115841,0.017141942,0.015230951,-0.011370845,-0.017195692,0.010603366,0.02628064,-0.0005038232,-0.0062139235,-0.0035891654,-0.012470282,-0.0026584489,0.0041811955,-0.0018309733,-0.0039002446,0.011070157,-0.0013829231,-0.008738455,-9.6965e-05,-0.0024346244,0.008887841,0.012516755,-0.017930891,-0.003455331,-0.0055090287,0.009047409,-0.027502995,-0.024218583,-0.00869635,-0.0074266233,0.014179429,0.0008760223,0.009478791,0.013114609,-0.013695879,0.006806369,0.021488627,0.0132704945,-0.012239633,-0.0080349585,-0.028512191,-0.012713092,-0.0067748507,0.009803737,-0.032334223,-0.018142123,-0.030158183,-0.007562451,0.016681071,-0.016855283,0.018334955,-0.011022064,0.0067877523,-0.022195974,0.005313749,-0.020769212,0.0029329287,-0.009482509,-0.015868274,-0.0125563415,0.037795503,-0.018607879,-0.00034732162,-0.0070776236,0.010927232,0.16113105,0.009300028,0.0030395254,0.008452913,0.0036496518,0.027558258,-0.0020593987,-0.0059871166,-0.019631222,0.0014384158,0.00956279,-0.013870685,-0.0293226,-0.009655762,0.009808208,-0.02982863,0.0037977686,0.016183563,-0.011828021,0.008530397,0.0014528563,6.408176e-05,0.02651786,-0.002739122,0.019939942,0.011456644,-0.0029952773,0.0030549073,-0.011675452,0.012257593,0.0104670385,-0.025641354,-0.017383646,0.012704732,0.016742509,-0.0015758291,-0.0053248247,-0.0032480285,0.0026969328,-0.0025933264,0.017883778,0.028444445,0.02028431,0.021694569,-0.008984672,-0.0056530526,0.010714406,0.015536923,0.014538084,-0.0124031715,-0.017679136,-0.014510183,0.010013154,-0.0042871577,0.0012157337,0.016478844,-0.0005351597,-0.035514917,-0.008552355,0.002945124,-0.0033707544,0.00018438771,-0.01176828,0.0038569302,0.020029923,-0.012304653,0.023980862,-0.02210149,-0.008092732,-0.096370794,-0.002455175,-0.016743166,-0.0027399664,0.01950245,0.016793564,0.018175527,0.004099565,-0.024322549,0.01370211,-0.011716699,-0.0060433224,-0.00035171612,0.00054949115,0.0040753265,0.00093822496,0.020228738,-0.027012106,0.043487977,-0.005005123,-0.0031976048,-0.0004922846,-0.0014458146,-0.020397257,-0.0060126134,0.009222025,-0.021481188,0.003194883,0.0037533096,0.007123811,0.010794566,0.01793424,-0.013857684,0.018571435,0.0019389525,0.0016924768,0.0134241115,0.003615629,0.014651016,-0.004856285,0.006213174,0.016904462,0.009675361,0.013491231,0.0050915666,-0.003727904,0.014086839,-0.019723715,-0.0036271038,-0.012426972,-0.018417092,-0.002344207,0.006606595,0.018628826,-0.00018854107,0.011295506,-0.004336817,-0.024802862,0.0059996904,-0.01689929,0.0023721068,0.00020730842,0.00840493,0.0067332597,0.0035876213,-0.01844431,-0.0027288229,-0.027211353,0.013087693,-0.006646225,-0.012876234,-0.009089552,0.0009292642,0.0034543,0.00861505,-0.004936415,-0.00023621158,0.02404978,-0.012305723,0.0061016055,-0.0066410364,-0.020002551,-0.005230933,-0.017404823,0.05149072,-0.012621155,-0.015241671,-0.004448655,-0.0025899769,-0.0021789838,0.0037892757,0.024154823,-0.0062019094,0.020621965,-0.008360816,-0.0001222002,0.013705827,0.007740597,0.001524013,-0.01719817,0.015986977,-0.011700355,0.0048446264,-0.008680237,-0.009671273,-0.014190415,0.003599184,0.01137564,-0.0015146083,-0.016076686,0.002411891,-0.0103441505,-0.028118243,0.0036211018,-0.0043802015,0.01766906,0.006359681,-0.017873975,-0.006473243,-0.005542972,0.002911697,-0.0025242441,0.0011631221,-0.018289315,-0.0074584326,-0.027240483,0.0019720166,-0.02167866,-0.007253098,-0.00668304,0.028243506,-0.018529046,0.016620122,0.022011785,0.026052805,-0.00085354346,0.014194068,-0.0024775588,-0.010527357,0.0077574346,-0.020141872,0.0068209977,-0.013413459,0.019632094,-0.0005611932,-0.0024871526,0.0043277587,0.019420918,0.0042676097,0.0126618035,0.016608775,0.0042717205,-0.029566111,0.015331117,0.012748858,0.013680335,-0.0059271255,0.0025353516,-0.01010703,0.007505392,-0.013150732,0.021887837,-0.026801597,0.018914688,0.0029034803,0.00035731183,-0.007473024,0.0055164965,0.004271516,-0.007987177,0.008715031,-0.023864267,0.013604231,-0.0086656455,-0.0012813465,0.0012316055,-0.017502407,0.0097495895,0.009506033,-0.07674664,0.021648431,0.013538708,-0.02192022,-0.0009980119,0.00077668944,0.0096748,-0.0037104113,-0.009978672,0.00073051744,0.024492294,-0.015806178,0.01770833,0.04140263,-0.024082776,0.010859552,-0.026789235,0.0054255263,0.016116008,-0.00018350764,0.012025022,-0.0050136605,-0.011509898,-0.0065074787,-0.02008845,-0.01493828,-0.008009075,-0.004675546,0.009741544,-0.01239424,0.011492543,-0.02502866,0.00017371109,0.001951919,-0.015312085,-0.026416684,-0.0028627622,-0.01583216,-0.001696071,0.0023285009,0.004322188,0.006805976,-0.06713747,0.008487897,0.0061470326,0.00079140445,0.00424879,-0.008004717,-0.001312672,-0.014339511,0.0046312087,-0.00014091005,0.010584602,0.0060334858,-0.0017657884,-0.01913621,0.0039109844,0.008871868,-0.008059921,0.011402967,-0.013998479,-0.01641044,-0.0113090575,-0.0120620495,-0.006572552,0.01819745,-0.018272584,0.010555922,0.0008141336,0.026955169,-0.0006629019,-0.004452601,-0.010568027,-0.006705885,-0.019298939,0.016389456,0.014845445,-0.009353827,0.012064664,0.024069194,0.0029438832,0.032448307,-0.0047511533,0.015329738,0.014638297,-0.0010252935,0.008679409,-0.1052024,-0.01930363,-0.006634208,-0.0014724196,0.006739009,0.019771578,-0.004652397,0.020614238,0.005262892,-0.033818066,0.009186368,0.009202665,-0.002428445,0.0068640667,-0.021379579,-0.011610305,0.012483699,-0.005993038,-0.0012840541,0.011909997,0.011549432,-0.0107415095,-0.004838265,-0.020760113,0.022587264,-0.030609855,-0.008740534,-0.028365644,0.010279865,0.018249031,0.02174041,0.015176284,-0.0015733633,0.00080535014,0.012417185,0.0072262525,0.014693941,0.006357356,-0.009764037,-0.01127432,-0.012452056,-0.019543624,-0.0068010604,0.012287665,-0.011266173,-0.00035693374,-0.006619013,0.0035466214,-0.008542899,-0.01857327,0.019552855,-0.0061665443,0.0058430084,-0.008135075,0.022761466,-0.009220318,-0.0085694,2.5600048e-05,0.019336054,0.0010113838,0.009932386,-0.0028268013,0.01856725,-0.0081270635,-0.031385563,-0.006989352,-0.008458669,-0.020022111,-0.0024876466,0.0069688093,-0.018247634,0.004394672,0.0215221,0.01878934,0.0180936,0.020102587,0.03171006,0.011794093,-0.008000146,-0.008745928,-0.008375289,-0.012986363,-0.004207489,0.0077138864,0.0065515647,-0.0022225855,-0.0068524317,0.022565953,-0.00025582695,-1.1027891e-05,0.014928638,-0.035186104,0.008157859,0.023331193,-0.0010624119,0.0064746696,-0.017964264,-0.030442767,0.023703663,-0.016886098,-0.0027027517,0.011575925,0.0036175535,-0.005501764,-0.0102810655,0.012627907,0.0030401142,-0.00010400548,0.007518496,0.008741207,-0.008043551,-0.0066622617,-0.022885006,0.011089771,-0.011286007,-0.0015137237,0.0023427277,-0.0074434797,0.012183566,-0.020532476,0.0070218425,-0.027221778,0.010478889,-0.029141458,-0.0012234147,-0.008219783,0.006012166,0.00013933067,0.010915464,0.0057813697,0.022264166,0.010965857,0.015390145,0.0003674314,0.019270407,-0.014204959,-0.015556221,0.020894056,-0.021799574,0.02179166,-0.0076739276,-0.0025379825,0.015163019,-0.00803718,-0.0022291525,-0.0030299367,0.015802955,0.01942952,-0.007458466,-0.005869608,0.0123962015,0.009352437,0.0031968239,-0.01972882,-0.00011328871,0.004595831,-0.016537448,-0.018329358,0.02987542,0.0016887685,0.0010123724,0.004034311,-0.00314415,-0.011901875,-0.0013172979,-0.024281891,0.0044557885,0.006572065,0.014090952,0.00588144,0.028818067,0.006373006,0.002492055,-0.015091162,0.052354805,-0.0285237,-0.010932506,0.021824257,-0.003179481,-0.006984997,0.0069797216,-0.0017689114,-0.007008968,-0.013254161,-0.009154939,-0.013300171,-0.006057934,-0.016819289,0.022411507,-0.008508757,0.008098387,0.008210102,0.013573167,0.004810248,-0.01775083,-0.0022854642,-0.002416579,0.017516946,0.012769345,0.02023269,0.0032318702,0.011880564,-0.00084081903,0.0054609044,0.002230386,0.007889981,-0.06667301,-0.01074643,-0.0154960845,0.020521425,0.020533355,0.011184875,-0.0036266518,0.004221461,0.0046777274,0.013118903,0.016498877,0.0028898795,-0.008372909,0.018678382,-0.00030798352,0.018261312,-0.018502215,0.0043015806,-0.012430096,-0.005452941,-0.0031279586,-0.019360492,0.01653776,0.011402288,0.003485299,0.0015527391,0.009108697,0.00036123127,0.006929964,0.0049237427,-0.004882236,-0.0120111,-0.0030242512,0.021456564,0.012364793,-0.017952558,0.0038130553,0.020894937,-0.031645384,-0.019984739,-0.00783461,-0.03097911,-0.016838647,0.00159629,0.023024973,-0.0051684952,-0.011934737,-0.0006752768,-0.01630574,-0.0031133466,-0.0024239493,0.011328301,0.023087379,-0.011763361,0.012776869,-0.0029336321,-0.010824006,-0.0032426754,-0.024311906,-0.015809784,0.007769871,0.0042208266,-0.02188919,-0.0035692784,0.010077629,-0.009349846,-0.009089771,0.0070557776,-0.0011334497,0.00084690494,-0.020693196,0.012329064,-0.00087523396,0.021268057,-0.008171281,-0.008071898,0.018510409,-0.018446714,0.005169616,0.0014687129,-0.02196241,-0.011857574,0.014619823,-0.0074025304,-0.0047054794,0.004621988,0.012942412,0.007565546,0.009566702,0.007122523,-0.0011202679,0.014553467,0.008609732,-0.0067054746,0.03280639,-0.017262576,-0.012228494,-0.005744945,-0.011445693,-0.010748792,0.020079264,-0.024140917,-0.010740813,0.015167314,-0.017664567,0.0061643096,0.0074744495,0.024196936,-0.004259883,0.006468178,-0.0033875185,0.007883625,-0.0172354,-0.00010451091,-0.027428906,0.025919763,-0.008209444,0.0061618905,-0.006476155,0.008514286,0.012692248,0.0020677596,-0.0018545316,5.7866837e-06,0.011434354,-0.009429812,0.008830305,-0.017075,0.017935019,-0.011613635,0.017682737,-0.0014426822,-0.004518485,0.006371347,0.00462636,0.023296183,0.023305697,0.0005733462,0.0076176412,0.004036918,0.0054710587,-0.0083247535,0.028656812,0.0012722709,-0.03648197,-0.010910374,-0.0026352387,0.021450749,-0.00540091,-0.040054508,-0.0002752203,-0.012798797,0.0009147468,-0.0010181058,-0.009409679,0.018501991,-0.017227456,0.019242566,-0.0014100947,0.009023855,0.0041082734,-0.0332324,-0.020541709,0.021273809,-0.0039192066,0.0058132517,0.003861556,0.008811358,-0.00868454,0.0077683497,0.00506841,0.022537291,-0.0002284035,-0.024145242,-0.013037396,-0.004744104,0.00025345996,0.0043895277,-0.009410471,0.0004996138,-0.0063320934,-0.003997689,-0.0065506985,-0.02735753,-0.018120779,-0.0019557097,0.014064222,-0.01369771,-0.0041659772,-0.001897143,-0.004719389,-0.0027132265,0.019573608,0.011595442,-0.013688471,-0.0011770051,0.005354636,-0.005082729,-0.00300314,0.021368679,-0.0073102056,0.0065200464,-0.017542692,-0.01017749,0.0134561695,0.005914605,-0.0034221553,0.0155004505,-0.016629642,0.020643596,0.007814338,0.009437445,0.011367381,-0.009114718,-0.014868279,-0.0042557744,0.00012077311,-0.013826649,-2.189294e-05,-0.002123589,-0.002620016,0.014314658,-0.0015477185,0.0034617593,-0.0087929005,-0.0010880365,0.0067677656,-0.010732878,-0.01682325,-0.006812777,-0.00815666,-0.012844643,0.0032932376,0.031775974,-0.006361064,0.006513866,-0.0033748595,0.014075319,-0.0064194375,0.0048547136,-0.032638088,0.00073844375,-0.0062989113,0.0045298897,-0.008863403,-0.020906236,-0.0057391473,-0.026860297,0.009526664,-0.010016266,-0.004873728,-0.0056456816,0.01552006,-0.0002182005,-0.010718784,-0.0017568776,-0.0078083705,0.021196608,-0.020063892,-0.0014381217,-0.009909297,-0.019635312,-0.022319717,-0.0004944429,0.0008406406,0.015399915,-0.03936724,0.0051693586,-0.0014029492,-0.0147526,0.01353564,-0.009586326,-0.0061519267,-0.04797028,0.01165752,0.01671314,0.00014840535,0.003134239,0.010884422,0.014424476,0.0015422835,-0.0051246863,0.0055710943,0.011652772,-0.00489273,-0.0040484183,-0.040580913,0.0048977253,0.012533517,0.016336631,0.008231204,0.004271877,0.01396127,-0.0013754562,0.018572828,-0.0013839519,-0.017579118,-0.0059397123,-0.0051885745,0.012917278,-0.0031729173,0.0003836016,-0.037283365,-0.037946064,-0.017865058,-0.008114683,0.012523899,-0.009695937,0.0013416992,-0.01172257,0.00025749364,0.012168165,0.005315631,0.0038996537,-0.02530126,0.009820257,-0.0013364695,0.014951019,-0.0048926715,-0.010411265,0.001063199,0.009623952,0.001016048,0.00059923955,0.029413614,0.0044089067,-0.021173706,0.017446816,0.011996345,0.00820634,-0.005984679,-0.013611579,-0.01650535,-0.007605445,0.0025649976,0.00180917,0.006848942,-0.016987065,0.0046016523,-0.00063321786,-8.057844e-05,-0.008112175,-0.0069552464,-0.0074130977,0.004977693,0.021516388,-0.016851768,-0.03423358,0.00499021,0.011664716,0.007931375,-0.0031455816,0.02013577,-0.0032223081,-0.0064752796,0.008623749,-0.027584437,0.0016314925,-0.03338213,0.0031200903,0.0001317456,0.029287532,-0.016296742,0.022468757,-0.0021583498,-0.0071369978,0.009975269,-0.008700545,0.00096501387,-0.01109598,-0.00086461,0.0012226605,0.012848261,-0.0027592133,-0.00042141616,-0.021427954,-0.0058354777,0.01856292,0.0016670768,-0.026227249,0.0044408734,-0.011193285,-0.008778395,0.017308913,-0.0035909312,-0.028823473,-0.0021815258,0.003704787,0.013374592,-0.013054439,0.012938901,-2.887024e-05,0.010762512,-0.019808177,0.0028561507,-0.007014311,0.007345206,-0.0154345445,0.012215775,0.0012417842,0.03103995,-0.015545267,-0.008655606,-0.0063378033,-0.009197609,0.013638874,-0.0134347845,-0.013015056,0.017061252,0.00530974,0.0044851545,-0.005705869,0.007457857,0.0011855289,-0.005267018,-0.0014154955,0.0035469942,0.0018500583,-0.003654083,-0.00081665436,0.0030541797,-0.015535656,-0.027800517,-0.0036948936,-0.0033639737,0.010833235,0.0008648632,0.010558328,-0.0068327403,0.026533617,-0.011308929,0.000859452,0.0129553,-0.01723938,0.034261804,0.02163641,0.0033610743,0.010788491,0.007946718,-0.0023011318,0.0030454535,-0.010237322,0.005512835,-0.008820725,0.010909117,-0.015089657,-0.0070976857,-0.01784223,-0.007836813,0.015467162,0.025023907,-0.0028379334,0.026226383,0.032307673,0.010954831,-0.028913174,-0.0135947475,-0.028930137,0.0011078336,0.0001723396,-0.01675828,0.008023414,0.0005022954,-0.0018677032,0.005297633,0.004140278,-0.016907154,0.015426099,0.004776034,-0.003627229,0.009665175,0.025892397,-0.0016945616,-0.018900972,-0.012191347,0.0136407325,-0.010470363,-0.010193123,0.0016450201,0.019025601,0.17983733,0.121058784,-0.005847738,-0.006712593,0.01308201,-0.014268343,-0.030888865,0.008365073,0.009501728,-0.015416292,0.00012345178,0.0024771695,0.0018566935,0.0010222801,-0.002230187,-0.008348986,0.033735696,-0.014880709,-0.009528725,-0.0064087696,-0.0033953828,0.0065238173,0.007854998,-0.0032744429,-0.004988041,0.013096093,-0.014185712,-0.019434227,0.0237101,-0.008060976,-0.010783178,-0.0061529214,-0.007899051,-0.0021308803,0.004496598,0.00069644424,-0.020101614,-0.0006494537,0.020251242,-0.012221947,-0.008330116,0.006149089,0.023335094,-0.014777822,-0.0026474404,-0.0044075064,0.0142108835,-0.0005933767,0.011128701,0.011488161,-0.011938438,0.007043868,-0.011037694,0.004644178,-0.03051463,-0.019229455,0.0072408533,0.014390035,-0.02435296,0.02043487,0.0055786935,0.02021379,0.003047144,0.013053725,-0.022338849,0.0077265976,-0.01597177,0.0024837763,-0.009402595,0.0005225216,-0.012167788,-0.0050611612,0.015803441,-0.00617371,0.010425713,-0.015073901,-0.0067202854,-0.02053979,0.003422619,-0.0035297878,-0.018701015,-0.016617902,-0.014314335,0.020058017,-0.0010194912,0.018335182,0.00795429,0.043218225,0.07332464,0.0013126809,-0.0036688393,-0.02929877,-0.0023124022,-0.023200067,-0.011531536,0.013425555,0.01616779,0.022114577,0.02161394,0.014565457,0.015306675,-0.011598397,0.00621683,0.018746354,-0.0029335066,0.024561021,0.0020691874,0.0036886868,-0.010045888,0.016415184,0.006525106,-0.011449253,0.0070283827,-0.010251222,0.0032915906,-0.000881743,-0.002429824,0.010807817,-0.09864949,-0.0036789791,-0.007990372,-0.015261145,-0.001513843,0.011398418,0.03466345,0.006264021,0.0024471341,0.006444256,-0.0072866,0.0006788698,0.017874843,-0.021876246,-0.024294224,-0.013749198,0.0024668549,0.004008516,0.0049061603,0.0151517205,-0.005508569,0.0068335645,-0.016095202,0.011144112,0.004506208,0.024015123,-0.006694578,-0.008298515,0.025237711,0.007284451,0.00658802,0.021793464,-0.002255887,0.0033206907,0.0048961327,0.009910918,0.0026880833,0.013628918,0.020809676,-0.019856602,0.010311854,-0.028197333,0.015343623,-0.02269153,0.006891856,-0.0057185157,0.026814455,-0.0034177308,-0.0143750245,0.0004874625,0.025853178,0.024872309,-0.011275694,0.007828135,0.00051168614,-0.015384862,0.006410666,0.010589358,-0.02514243,-0.0016172015,0.014286539,0.01144803,0.010546208,0.012253838,-0.032834776,0.00023020466,-0.027146125,-0.004821132,0.009187816,0.000320361,-0.016907977,0.012601203,0.015261526,-0.02318283,-0.018826071,0.010759074,-0.020921731,0.014546166,-0.013639836,-0.0031223628,0.005245768,-0.008973759,-0.00573097,0.12679902,0.016110275,0.011515245,-0.017448805,0.0134639535,0.011481834,0.011022039,0.02151307,0.0052546794,0.00082031736,0.010404748,0.016197542,0.008196779,0.002707183,0.003653066,-0.0010186229,0.021275908,-0.003349763,0.007886622,-0.012398772,-0.0076124696,-0.012239337,0.0017500198,-0.019132476,-0.016529566,0.0023497678,-0.004517892,-0.010986653,-0.025755743,-0.009175262,-0.012996891,-0.013479368,0.0052604084,-0.01742089,-0.0041986634,0.0048988224,0.0023031095,-0.016492043,-0.026352942,-0.0003129857,0.0087100975,-0.0054478054,-0.002105391,0.023957789,-0.05225964,0.21061768,0.0010621401,-0.00726592,-0.0075934017,-0.005201538,0.004377874,-0.0043666237,0.004337291,-0.01154585,0.004326853,-0.01162961,0.0073757516,0.009871133,-0.0039482205,-0.009333441,0.0018492804,0.0008150544,0.016980754,0.0011772494,0.0027223122,0.014463657,-0.0069573186,0.021839943,-0.01038739,-0.023184504,0.011137543,-0.0134094125,-0.0066986596,-0.013910508,0.0036637376,0.00051522756,0.0022523801,-0.012228104,-0.012328875,0.009080291,-0.0054855826,0.013708094,0.0057810037,0.0004500555,-0.0036173125,-0.021552924,0.026490325,0.0041665994,0.016683962,-0.015985074,-0.020247767,-0.01681084,0.008015359,-0.008604846,0.009079111,0.02254447,-8.273143e-06,-0.001206975,0.031179119,-0.016269933,0.012648745,-0.032230522,0.011584005,0.0030547115,-0.014373901,0.017445153,-0.008417224,0.014304332,-0.011334879,-0.0117553845,0.0014705391,-0.0108659845]	2026-06-01 07:15:03.201972	2026-06-01 07:15:03.201973	day	["Flexible Working Hours", "Weekly Payout", "Overtime Pay"]	full_time
\.


--
-- Data for Name: master_cities; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.master_cities (id, name, state_id) FROM stdin;
40	Mumbai	11
41	Pune	11
42	Nagpur	11
43	Nashik	11
44	Thane	11
45	Aurangabad	11
46	Bengaluru	12
47	Mysuru	12
48	Hubli	12
49	Mangaluru	12
50	Belagavi	12
51	New Delhi	13
52	Dwarka	13
53	Rohini	13
54	Saket	13
55	Chennai	14
56	Coimbatore	14
57	Madurai	14
58	Salem	14
59	Tiruchirappalli	14
60	Hyderabad	15
61	Warangal	15
62	Nizamabad	15
63	Karimnagar	15
64	Ahmedabad	16
65	Surat	16
66	Vadodara	16
67	Rajkot	16
68	Bhavnagar	16
69	Kolkata	17
70	Howrah	17
71	Durgapur	17
72	Siliguri	17
73	Asansol	17
74	Lucknow	18
75	Kanpur	18
76	Varanasi	18
77	Agra	18
78	Noida	18
79	Jaipur	19
80	Udaipur	19
81	Jodhpur	19
82	Kota	19
83	Ajmer	19
84	Bhopal	20
85	Indore	20
86	Gwalior	20
87	Jabalpur	20
88	Thiruvananthapuram	21
89	Kochi	21
90	Kozhikode	21
91	Thrissur	21
92	Ludhiana	22
93	Amritsar	22
94	Jalandhar	22
95	Patiala	22
96	Gurugram	23
97	Faridabad	23
98	Panipat	23
99	Ambala	23
100	Patna	24
101	Gaya	24
102	Muzaffarpur	24
103	Bhagalpur	24
104	Bhubaneswar	25
105	Cuttack	25
106	Rourkela	25
107	Puri	25
108	Guwahati	26
109	Dibrugarh	26
110	Silchar	26
111	Ranchi	27
112	Jamshedpur	27
113	Dhanbad	27
114	Raipur	28
115	Bhilai	28
116	Bilaspur	28
117	Dehradun	29
118	Haridwar	29
119	Nainital	29
120	Shimla	30
121	Manali	30
122	Dharamshala	30
123	Panaji	31
124	Margao	31
125	Vasco da Gama	31
126	Agartala	32
127	Shillong	33
128	Imphal	34
129	Kohima	35
130	Dimapur	35
131	Aizawl	36
132	Gangtok	37
133	Itanagar	38
134	Bathinda	22
135	Mohali	22
136	Hoshiarpur	22
137	Batala	22
138	Pathankot	22
139	Moga	22
140	Abohar	22
141	Malerkotla	22
142	Khanna	22
143	Phagwara	22
144	Hisar	23
145	Karnal	23
146	Rohtak	23
147	Sonipat	23
148	Yamunanagar	23
149	Panchkula	23
150	Bhiwani	23
151	Sirsa	23
152	Rewari	23
153	Kurukshetra	23
154	Darbhanga	24
155	Purnia	24
156	Arrah	24
157	Begusarai	24
158	Katihar	24
159	Munger	24
160	Chapra	24
161	Saharsa	24
162	Samastipur	24
163	Motihari	24
164	Sambalpur	25
165	Berhampur	25
166	Balasore	25
167	Jharsuguda	25
168	Baripada	25
169	Jeypore	25
170	Bhadrak	25
171	Jorhat	26
172	Tezpur	26
173	Nagaon	26
174	Tinsukia	26
175	Sivasagar	26
176	Bongaigaon	26
177	Bokaro	27
178	Hazaribagh	27
179	Deoghar	27
180	Giridih	27
181	Ramgarh	27
182	Chaibasa	27
183	Korba	28
184	Jagdalpur	28
185	Rajnandgaon	28
186	Raigarh	28
187	Ambikapur	28
188	Durg	28
189	Rishikesh	29
190	Roorkee	29
191	Haldwani	29
192	Rudrapur	29
193	Almora	29
194	Pithoragarh	29
195	Solan	30
196	Mandi	30
197	Kullu	30
198	Hamirpur	30
199	Bilaspur	30
200	Chamba	30
201	Mapusa	31
202	Ponda	31
203	Bicholim	31
204	Canacona	31
205	Udaipur	32
206	Dharmanagar	32
207	Kailasahar	32
208	Belonia	32
209	Tura	33
210	Jowai	33
211	Nongpoh	33
212	Baghmara	33
213	Thoubal	34
214	Bishnupur	34
215	Churachandpur	34
216	Ukhrul	34
217	Mokokchung	35
218	Tuensang	35
219	Wokha	35
220	Zunheboto	35
221	Lunglei	36
222	Champhai	36
223	Serchhip	36
224	Kolasib	36
225	Namchi	37
226	Gyalshing	37
227	Mangan	37
228	Singtam	37
229	Naharlagun	38
230	Tawang	38
231	Pasighat	38
232	Ziro	38
233	Bomdila	38
234	Roing	38
\.


--
-- Data for Name: master_industries; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.master_industries (id, name) FROM stdin;
23	Information Technology
24	Healthcare
25	Finance
26	Education
27	Manufacturing
28	Retail
29	Real Estate
30	Entertainment
31	Consulting
32	Telecommunications
33	Marketing & Advertising
34	E-commerce
35	Logistics & Supply Chain
36	Automotive
37	Banking
38	Insurance
39	Pharmaceuticals
40	Biotechnology
41	Construction
42	Energy & Utilities
43	Oil & Gas
44	Agriculture
45	Food & Beverage
46	Hospitality
47	Travel & Tourism
48	Media & Publishing
49	Legal Services
50	Government & Public Sector
51	Non-Profit
52	Human Resources
53	Cybersecurity
54	Artificial Intelligence & Machine Learning
55	Cloud Computing
56	Semiconductors
57	Aerospace & Defense
58	Mining & Metals
59	Textiles & Apparel
60	Consumer Goods
61	Electronics
62	Television & Broadcasting
63	Sports & Fitness
64	Environmental Services
65	Waste Management
66	Marine & Shipping
67	Architecture & Planning
68	Design Services
69	Research & Development
70	Event Management
71	Gaming
72	Animation & VFX
73	EdTech
74	FinTech
75	HealthTech
76	InsurTech
77	PropTech
78	AgriTech
79	CleanTech
80	Robotics
81	IoT (Internet of Things)
82	Blockchain
83	Digital Marketing
84	BPO & KPO
85	Staffing & Recruitment
86	Procurement
87	Import & Export
88	Luxury Goods
89	Jewelry
90	Furniture & Home Decor
91	Printing & Packaging
92	Music Industry
93	Film Production
94	Social Media
95	Data Analytics
96	Venture Capital & Private Equity
97	Accounting & Auditing
98	Corporate Training
99	Security Services
100	Facilities Management
101	Pet Care
102	Beauty & Cosmetics
103	Wellness & Mental Health
104	Translation & Localization
105	Open Source Software
106	Mobile Applications
107	SaaS (Software as a Service)
108	Hardware
109	Networking
110	Quantum Computing
111	Space Technology
112	Renewable Energy
113	Drones
114	3D Printing
\.


--
-- Data for Name: master_languages; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.master_languages (id, name) FROM stdin;
24	Hindi
25	English
26	Assamese
27	Bengali
28	Bodo
29	Dogri
30	Gujarati
31	Kannada
32	Kashmiri
33	Konkani
34	Maithili
35	Malayalam
36	Manipuri (Meitei)
37	Marathi
38	Nepali
39	Odia
40	Punjabi
41	Sanskrit
42	Santali
43	Sindhi
44	Tamil
45	Telugu
46	Urdu
\.


--
-- Data for Name: master_roles; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.master_roles (id, name, industry_id) FROM stdin;
191	Software Engineer	23
192	Frontend Developer	23
193	Backend Developer	23
194	Full Stack Developer	23
195	DevOps Engineer	23
196	UI/UX Designer	23
197	Data Analyst	23
198	Data Scientist	23
199	Business Analyst	23
200	Product Manager	23
201	Project Manager	23
202	QA Engineer	23
203	Mobile App Developer	23
204	Cloud Engineer	23
205	Healthcare Data Analyst	24
206	Clinical Research Associate	24
207	Medical Writer	24
208	Regulatory Affairs Specialist	24
209	Pharmacovigilance Specialist	24
210	Healthcare Project Manager	24
211	Healthcare Business Analyst	24
212	Hospital Administrator	24
213	Medical Coder	24
214	Financial Analyst	25
215	Investment Analyst	25
216	Risk Analyst	25
217	Compliance Officer	25
218	Accountant	25
219	Auditor	25
220	Finance Data Analyst	25
221	Finance Business Analyst	25
222	Treasury Analyst	25
223	Teacher	26
224	Professor	26
225	Instructional Designer	26
226	Curriculum Developer	26
227	Education Product Manager	26
228	EdTech Software Engineer	26
229	Academic Coordinator	26
230	Industrial Engineer	27
231	Mechanical Engineer	27
232	Manufacturing Engineer	27
233	Quality Assurance Engineer	27
234	Supply Chain Analyst	27
235	Procurement Specialist	27
236	Operations Manager	27
237	Plant Manager	27
238	Sales Executive	28
239	Store Manager	28
240	Merchandiser	28
241	Inventory Manager	28
242	Retail Marketing Manager	28
243	Retail Data Analyst	28
244	Retail Product Manager	28
245	Category Manager	28
246	Real Estate Consultant	29
247	Property Manager	29
248	Real Estate Sales Executive	29
249	Real Estate Marketing Manager	29
250	Real Estate Business Analyst	29
251	Graphic Designer	30
252	Animator	30
253	Video Producer	30
254	Film Editor	30
255	Entertainment UI/UX Designer	30
256	Entertainment Marketing Manager	30
257	Content Creator	30
258	Consultant	31
259	Management Consultant	31
260	Strategy Consultant	31
261	Consulting Business Analyst	31
262	Consulting Data Analyst	31
263	Consulting Project Manager	31
264	Network Engineer	32
265	Telecommunications Engineer	32
266	Telecom Backend Developer	32
267	Telecom DevOps Engineer	32
268	Telecom Data Analyst	32
269	RF Engineer	32
270	Marketing Manager	33
271	Digital Marketing Specialist	33
272	SEO Specialist	33
273	Social Media Manager	33
274	Copywriter	33
275	Graphic Designer	33
276	Advertising Sales Executive	33
277	Brand Manager	33
278	E-commerce Manager	34
279	Catalog Manager	34
280	E-commerce Product Manager	34
281	E-commerce Data Analyst	34
282	E-commerce Frontend Developer	34
283	Marketplace Specialist	34
284	Logistics Coordinator	35
285	Warehouse Manager	35
286	Supply Chain Manager	35
287	Procurement Specialist	35
288	Operations Executive	35
289	Transportation Manager	35
290	Automotive Engineer	36
291	Vehicle Design Engineer	36
292	Automotive Quality Engineer	36
293	Automotive Project Manager	36
294	Service Engineer	36
295	Banking Operations Executive	37
296	Relationship Manager	37
297	Credit Analyst	37
298	Banking Risk Analyst	37
299	Loan Officer	37
300	Insurance Advisor	38
301	Claims Analyst	38
302	Underwriter	38
303	Actuary	38
304	Policy Administrator	38
305	Pharmacist	39
306	Pharmaceutical Research Scientist	39
307	Drug Safety Associate	39
308	Regulatory Affairs Manager	39
309	Quality Control Analyst	39
310	Biotechnologist	40
311	Research Scientist	40
312	Lab Technician	40
313	Clinical Data Manager	40
314	Bioinformatics Analyst	40
315	Civil Engineer	41
316	Architect	41
317	Site Engineer	41
318	Quantity Surveyor	41
319	Construction Project Manager	41
320	Energy Analyst	42
321	Power Systems Engineer	42
322	Utility Operations Manager	42
323	Electrical Engineer	42
324	Renewable Energy Engineer	42
325	Petroleum Engineer	43
326	Drilling Engineer	43
327	Reservoir Engineer	43
328	HSE Officer	43
329	Process Engineer	43
330	Agronomist	44
331	Agricultural Engineer	44
332	Farm Manager	44
333	Soil Scientist	44
334	Crop Analyst	44
335	Food Technologist	45
336	Quality Assurance Manager	45
337	Production Supervisor	45
338	Food Safety Officer	45
339	Supply Chain Manager	45
340	Hotel Manager	46
341	Front Office Executive	46
342	Housekeeping Manager	46
343	Restaurant Manager	46
344	Guest Relations Executive	46
345	Travel Consultant	47
346	Tour Manager	47
347	Reservation Executive	47
348	Destination Specialist	47
349	Operations Coordinator	47
350	Editor	48
351	Journalist	48
352	Content Writer	48
353	Publishing Manager	48
354	Proofreader	48
355	Lawyer	49
356	Legal Associate	49
357	Paralegal	49
358	Compliance Officer	49
359	Contract Specialist	49
360	Policy Analyst	50
361	Public Administrator	50
362	Program Officer	50
363	Government Project Manager	50
364	Research Officer	50
365	Program Manager	51
366	Fundraising Manager	51
367	Community Outreach Coordinator	51
368	Grant Writer	51
369	Volunteer Coordinator	51
370	HR Executive	52
371	HR Manager	52
372	Recruiter	52
373	Talent Acquisition Specialist	52
374	Learning and Development Specialist	52
375	Cybersecurity Analyst	53
376	Security Engineer	53
377	Penetration Tester	53
378	SOC Analyst	53
379	Incident Response Specialist	53
380	AI Engineer	54
381	Machine Learning Engineer	54
382	Prompt Engineer	54
383	Research Scientist	54
384	MLOps Engineer	54
385	Cloud Engineer	55
386	Cloud Architect	55
387	Site Reliability Engineer	55
388	DevOps Engineer	55
389	Infrastructure Engineer	55
390	Semiconductor Engineer	56
391	Chip Design Engineer	56
392	Verification Engineer	56
393	Process Engineer	56
394	Test Engineer	56
395	Aerospace Engineer	57
396	Avionics Engineer	57
397	Systems Engineer	57
398	Defense Analyst	57
399	Quality Engineer	57
400	Mining Engineer	58
401	Metallurgical Engineer	58
402	Geologist	58
403	Safety Officer	58
404	Operations Manager	58
405	Textile Engineer	59
406	Fashion Designer	59
407	Production Merchandiser	59
408	Quality Inspector	59
409	Sourcing Manager	59
410	Brand Manager	60
411	Category Manager	60
412	Sales Manager	60
413	Supply Chain Analyst	60
414	Product Manager	60
415	Electronics Engineer	61
416	Embedded Systems Engineer	61
417	Hardware Design Engineer	61
418	PCB Design Engineer	61
419	Electronics Test Engineer	61
420	Broadcast Engineer	62
421	Video Editor	62
422	TV Producer	62
423	Camera Operator	62
424	Broadcast Technician	62
425	Fitness Trainer	63
426	Sports Coach	63
427	Sports Nutritionist	63
428	Gym Manager	63
429	Sports Analyst	63
430	Environmental Engineer	64
431	Sustainability Analyst	64
432	Environmental Consultant	64
433	Ecologist	64
434	Compliance Specialist	64
435	Waste Management Specialist	65
436	Recycling Coordinator	65
437	Environmental Compliance Officer	65
438	Operations Supervisor	65
439	Safety Officer	65
440	Marine Engineer	66
441	Ship Operations Manager	66
442	Logistics Coordinator	66
443	Port Manager	66
444	Naval Architect	66
445	Architect	67
446	Urban Planner	67
447	Landscape Architect	67
448	Draftsman	67
449	Planning Consultant	67
450	Graphic Designer	68
451	UI/UX Designer	68
452	Product Designer	68
453	Interior Designer	68
454	Creative Director	68
455	Research Scientist	69
456	R&D Engineer	69
457	Innovation Manager	69
458	Lab Technician	69
459	Prototype Engineer	69
460	Event Manager	70
461	Event Coordinator	70
462	Wedding Planner	70
463	Production Manager	70
464	Sponsorship Manager	70
465	Game Developer	71
466	Game Designer	71
467	Game Artist	71
468	Level Designer	71
469	QA Tester	71
470	Animator	72
471	VFX Artist	72
472	3D Modeler	72
473	Compositor	72
474	Motion Graphics Designer	72
475	EdTech Product Manager	73
476	Instructional Designer	73
477	Learning Experience Designer	73
478	Education Software Engineer	73
479	Academic Content Developer	73
480	FinTech Product Manager	74
481	Financial Software Engineer	74
482	Payments Analyst	74
483	Risk Analyst	74
484	Compliance Officer	74
485	HealthTech Product Manager	75
486	Healthcare Software Engineer	75
487	Clinical Data Analyst	75
488	Medical Informatics Specialist	75
489	Healthcare UX Designer	75
490	InsurTech Product Manager	76
491	Insurance Data Analyst	76
492	Insurance Software Engineer	76
493	Underwriting Analyst	76
494	Claims Automation Specialist	76
495	PropTech Product Manager	77
496	Real Estate Software Engineer	77
497	Property Data Analyst	77
498	GIS Analyst	77
499	Real Estate UX Designer	77
500	AgriTech Product Manager	78
501	Agricultural Data Analyst	78
502	Precision Agriculture Engineer	78
503	Farm Automation Specialist	78
504	Agronomist	78
505	CleanTech Product Manager	79
506	Renewable Energy Engineer	79
507	Carbon Analyst	79
508	Sustainability Consultant	79
509	Energy Data Analyst	79
510	Robotics Engineer	80
511	Automation Engineer	80
512	Control Systems Engineer	80
513	ROS Developer	80
514	Mechatronics Engineer	80
515	IoT Engineer	81
516	Embedded Systems Engineer	81
517	Firmware Engineer	81
518	IoT Solutions Architect	81
519	Sensor Integration Engineer	81
520	Blockchain Developer	82
521	Smart Contract Engineer	82
522	Web3 Developer	82
523	Cryptography Engineer	82
524	Tokenomics Analyst	82
525	Digital Marketing Manager	83
526	SEO Specialist	83
527	PPC Specialist	83
528	Content Strategist	83
529	Email Marketing Specialist	83
530	Customer Support Executive	84
531	Process Associate	84
532	Operations Analyst	84
533	Quality Analyst	84
534	Team Leader	84
535	Recruiter	85
536	Talent Acquisition Specialist	85
537	Sourcing Specialist	85
538	Recruitment Manager	85
539	HR Consultant	85
540	Procurement Specialist	86
541	Category Buyer	86
542	Vendor Manager	86
543	Strategic Sourcing Manager	86
544	Contract Manager	86
545	Import Export Manager	87
546	Customs Compliance Specialist	87
547	Trade Analyst	87
548	Documentation Executive	87
549	International Logistics Coordinator	87
550	Luxury Brand Manager	88
551	Visual Merchandiser	88
552	Retail Sales Consultant	88
553	Product Specialist	88
554	Store Manager	88
555	Jewelry Designer	89
556	Gemologist	89
557	Production Manager	89
558	Sales Consultant	89
559	Quality Inspector	89
560	Furniture Designer	90
561	Interior Designer	90
562	Product Development Manager	90
563	Visual Merchandiser	90
564	Sales Consultant	90
565	Packaging Engineer	91
566	Print Production Manager	91
567	Prepress Specialist	91
568	Graphic Designer	91
569	Quality Control Inspector	91
570	Music Producer	92
571	Sound Engineer	92
572	Artist Manager	92
573	Music Marketing Manager	92
574	A&R Manager	92
575	Film Producer	93
576	Director	93
577	Screenwriter	93
578	Cinematographer	93
579	Production Coordinator	93
580	Social Media Manager	94
581	Content Creator	94
582	Community Manager	94
583	Influencer Marketing Specialist	94
584	Social Media Analyst	94
585	Data Analyst	95
586	Business Intelligence Analyst	95
587	Analytics Engineer	95
588	Data Visualization Specialist	95
589	Reporting Analyst	95
590	Investment Associate	96
591	Due Diligence Analyst	96
592	Portfolio Manager	96
593	Deal Sourcing Analyst	96
594	Financial Modeling Analyst	96
595	Accountant	97
596	Auditor	97
597	Tax Consultant	97
598	Forensic Accountant	97
599	Internal Audit Manager	97
600	Corporate Trainer	98
601	Learning and Development Specialist	98
602	Training Manager	98
603	Instructional Designer	98
604	Facilitator	98
605	Security Officer	99
606	Security Supervisor	99
607	Risk Consultant	99
608	Surveillance Operator	99
609	Security Manager	99
610	Facilities Manager	100
611	Maintenance Supervisor	100
612	Building Operations Manager	100
613	Asset Manager	100
614	Space Planner	100
615	Veterinary Assistant	101
616	Pet Groomer	101
617	Pet Trainer	101
618	Veterinary Technician	101
619	Pet Care Manager	101
620	Cosmetologist	102
621	Beauty Consultant	102
622	Makeup Artist	102
623	Skincare Specialist	102
624	Cosmetic Product Manager	102
625	Mental Health Counselor	103
626	Psychologist	103
627	Wellness Coach	103
628	Therapist	103
629	Clinical Program Manager	103
630	Translator	104
631	Interpreter	104
632	Localization Specialist	104
633	Localization Project Manager	104
634	Language Quality Analyst	104
635	Open Source Developer	105
636	Community Manager	105
637	Maintainer	105
638	Developer Advocate	105
639	Technical Writer	105
640	Mobile App Developer	106
641	Android Developer	106
642	iOS Developer	106
643	React Native Developer	106
644	Flutter Developer	106
645	SaaS Product Manager	107
646	Customer Success Manager	107
647	Software Engineer	107
648	DevOps Engineer	107
649	Solutions Architect	107
650	Hardware Engineer	108
651	Embedded Systems Engineer	108
652	Firmware Engineer	108
653	PCB Design Engineer	108
654	Hardware Test Engineer	108
655	Network Engineer	109
656	Network Administrator	109
657	Network Architect	109
658	Systems Engineer	109
659	NOC Engineer	109
660	Quantum Researcher	110
661	Quantum Software Engineer	110
662	Quantum Algorithm Developer	110
663	Quantum Physicist	110
664	Research Scientist	110
665	Space Systems Engineer	111
666	Aerospace Engineer	111
667	Satellite Engineer	111
668	Mission Operations Engineer	111
669	Propulsion Engineer	111
670	Renewable Energy Engineer	112
671	Solar Engineer	112
672	Wind Energy Technician	112
673	Energy Analyst	112
674	Project Manager	112
675	Drone Operator	113
676	UAV Engineer	113
677	Flight Test Engineer	113
678	Drone Software Developer	113
679	Payload Integration Engineer	113
680	Additive Manufacturing Engineer	114
681	3D Printing Technician	114
682	CAD Designer	114
683	Prototype Engineer	114
684	Materials Engineer	114
\.


--
-- Data for Name: master_states; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.master_states (id, name, code, name_hi, name_pa) FROM stdin;
11	Maharashtra	MAHARASHTR	महाराष्ट्र	ਮਹਾਰਾਸ਼ਟਰ
12	Karnataka	KARNATAKA	कर्नाटक	ਕਰਨਾਟਕ
13	Delhi	DELHI	दिल्ली	ਦਿੱਲੀ
14	Tamil Nadu	TAMILNADU	तमिलनाडु	ਤਮਿਲਨਾਡੂ
15	Telangana	TELANGANA	तेलंगाना	ਤੇਲੰਗਾਨਾ
16	Gujarat	GUJARAT	गुजरात	ਗੁਜਰਾਤ
17	West Bengal	WESTBENGAL	पश्चिम बंगाल	ਪੱਛਮੀ ਬੰਗਾਲ
18	Uttar Pradesh	UTTARPRADE	उत्तर प्रदेश	ਉੱਤਰ ਪ੍ਰਦੇਸ਼
19	Rajasthan	RAJASTHAN	राजस्थान	ਰਾਜਸਥਾਨ
20	Madhya Pradesh	MADHYAPRAD	मध्य प्रदेश	ਮੱਧ ਪ੍ਰਦੇਸ਼
21	Kerala	KERALA	केरल	ਕੇਰਲ
22	Punjab	PUNJAB	पंजाब	ਪੰਜਾਬ
23	Haryana	HARYANA	हरियाणा	ਹਰਿਆਣਾ
24	Bihar	BIHAR	बिहार	ਬਿਹਾਰ
25	Odisha	ODISHA	ओडिशा	ਓਡੀਸ਼ਾ
26	Assam	ASSAM	असम	ਅਸਾਮ
27	Jharkhand	JHARKHAND	झारखंड	ਝਾਰਖੰਡ
28	Chhattisgarh	CHHATTISGA	छत्तीसगढ़	ਛੱਤੀਸਗੜ੍ਹ
29	Uttarakhand	UTTARAKHAN	उत्तराखंड	ਉੱਤਰਾਖੰਡ
30	Himachal Pradesh	HIMACHALPR	हिमाचल प्रदेश	ਹਿਮਾਚਲ ਪ੍ਰਦੇਸ਼
31	Goa	GOA	गोवा	ਗੋਆ
32	Tripura	TRIPURA	त्रिपुरा	ਤ੍ਰਿਪੁਰਾ
33	Meghalaya	MEGHALAYA	मेघालय	ਮੇਘਾਲਯਾ
34	Manipur	MANIPUR	मणिपुर	ਮਣੀਪੁਰ
35	Nagaland	NAGALAND	नागालैंड	ਨਾਗਾਲੈਂਡ
36	Mizoram	MIZORAM	मिज़ोरम	ਮਿਜ਼ੋਰਮ
37	Sikkim	SIKKIM	सिक्किम	ਸਿੱਕਿਮ
38	Arunachal Pradesh	ARUNACHALP	अरुणाचल प्रदेश	ਅਰੁਣਾਚਲ ਪ੍ਰਦੇਸ਼
\.


--
-- Data for Name: matches; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.matches (id, seeker_id, job_id, score, highlights, gaps, fit_reason, created_at) FROM stdin;
eb4155a9-b706-46f5-b187-2531851c660a	7cafedbb-8887-46d4-ada6-557084d6caae	38206023-d55d-40f0-9182-9fc8caca6519	45	["Proficient in Python programming", "Experience with Django framework", "Experience with FastAPI (implies REST APIs)", "Python Developer role alignment"]	["Flask experience not mentioned", "SQL experience not mentioned", "Git experience not mentioned", "Unit Testing, Data Structures, Algorithms, and OOP experience not mentioned", "Problem Solving and Communication skills not mentioned", "Docker, AWS, and Agile experience missing", "Years of experience not specified (job requires 1-4 years)"]	Strong foundational match with Python, Django, and REST API experience. However, the profile lacks explicit mention of several other core technical skills, soft skills, and desirable technologies required by the job description. Years of experience are also not specified.	2026-06-01 07:36:15.728107
\.


--
-- Data for Name: milestones; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.milestones (id, roadmap_id, title, description, order_num, skills, estimated_time, status, dependencies, started_at, completed_at, created_at, updated_at, stage_title, stage_order, difficulty) FROM stdin;
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.notifications (id, user_id, type, title, message, is_read, related_job_id, related_user_id, created_at) FROM stdin;
\.


--
-- Data for Name: otp_records; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.otp_records (id, email, phone, code, expires_at, used, created_at) FROM stdin;
13874252-4f8f-4e20-907b-b7318e778e30	sumeshsharma@gmail.com	\N	590783	2026-05-26 08:00:25.540509	f	2026-05-26 07:50:25.542073
8b2d3bb9-b0e7-47ca-aa9d-cb51bf54b2e5	karankumar123@yopmail.com	\N	165837	2026-05-26 08:16:09.930533	f	2026-05-26 08:06:09.931021
d4d2ff96-eed2-43c1-bda3-418f2406c421	roberthook@yopmail.com	\N	719886	2026-05-26 09:08:49.818804	f	2026-05-26 08:58:49.819262
8de40593-0725-4576-810b-50b979749f6e	roberthook@yopmail.com	\N	676225	2026-05-26 09:18:16.906861	f	2026-05-26 09:08:16.907591
e852fbbc-f2dd-40df-ae3d-f1a98b03bfb6	pradeepk.tws@gmail.com	\N	286839	2026-05-26 09:20:58.774533	f	2026-05-26 09:10:58.775208
cabca0d2-5171-41fc-acad-9dcf22194a97	pradeepk.tws@gmail.com	\N	360540	2026-05-26 09:23:29.231929	f	2026-05-26 09:13:29.233423
334bdaaa-c18c-4eab-9951-01441290bba2	pradeep.tws@tekkiwebsolutions.com	\N	679116	2026-05-26 09:25:06.540843	t	2026-05-26 09:15:06.541082
ce2c9105-5840-4702-b2ef-eafd9da6bd53	pradeepkumar29798@gmail.com	\N	439270	2026-05-28 09:35:56.903346	f	2026-05-28 09:25:56.908092
600e446b-5de1-44ac-a325-eabd2a6ee385	pradeepkumar29798@gmail.com	\N	569734	2026-05-28 09:36:53.63215	f	2026-05-28 09:26:53.63279
a80c25ab-dacb-48ea-9b0c-51cc6f962540	learnpath79@gmail.com	\N	766154	2026-05-28 09:43:16.815812	f	2026-05-28 09:33:16.816136
0b3581d8-a626-4dc8-a685-4ac943faecb6	sehajpreetdhillon14@gmail.com	\N	592628	2026-05-30 04:25:24.452774	f	2026-05-30 04:15:24.453629
bbac8dcf-b134-4912-82b6-1cc62c125745	sehajpreetdhillon14@gmail.com	\N	083210	2026-05-30 04:29:00.940294	t	2026-05-30 04:19:00.941208
6720b58d-08b1-40ea-b2e9-fb4f284711dc	pradeep.tws@tekkiwebsolutions.com	\N	965492	2026-05-30 04:39:12.220032	f	2026-05-30 04:29:12.221068
b7600a79-85ff-49b2-8f0c-ec3c38a270bc	pradeep.tws@tekkiwebsolutions.com	\N	792614	2026-05-30 04:39:55.507952	t	2026-05-30 04:29:55.508466
45c1ea8c-ba9a-4146-8ed3-b724ff9adb9c	pradeep.tws@tekkiwebsolutions.com	\N	402030	2026-05-30 04:47:36.406528	f	2026-05-30 04:37:36.407742
07377cf0-7d4b-4d36-baab-b5db568a86ce	pradeep.tws@tekkiwebsolutions.com	\N	170082	2026-05-30 04:52:24.350755	f	2026-05-30 04:42:24.352059
49a31bc1-1460-4c7e-a3da-0cc497df4637	pradeep.tws@tekkiwebsolutions.com	\N	129329	2026-05-30 04:55:15.09912	t	2026-05-30 04:45:15.101086
e07e0d0d-8703-4044-b6d6-a4b77840e02c	pradeepkumar29798@gmail.com	\N	453943	2026-05-30 05:12:44.284829	t	2026-05-30 05:02:44.28552
d4c471d3-068e-4506-b32f-83e63f726285	shivkumar32334@gmail.com	\N	501726	2026-05-30 08:25:22.381783	f	2026-05-30 08:15:22.382735
d061b69f-a026-44fc-b887-ce858a35eb3d	harshdevarya96@gmail.com	\N	847886	2026-05-30 08:32:51.455084	f	2026-05-30 08:22:51.455309
35c80017-5e22-4820-978e-da0be218c03d	samparnsahani@gmail.com	\N	452416	2026-06-01 04:59:29.041847	t	2026-06-01 04:49:29.042696
235a2932-24fc-4e27-9ce4-93216f7f7c81	hr@moonlightautomat.com	\N	320858	2026-06-01 05:18:39.475689	t	2026-06-01 05:08:39.475921
\.


--
-- Data for Name: portfolios; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.portfolios (id, user_id, headline, bio, date_of_birth, gender, city, state, linkedin_url, github_url, website_url, total_experience_years, current_company, "current_role", skills, work_experiences, education, certifications, languages, projects, intro_video_path, intro_video_filename, intro_audio_path, intro_audio_filename, created_at, updated_at) FROM stdin;
55872b18-be06-43e5-b009-24e52e37030e	7cafedbb-8887-46d4-ada6-557084d6caae	Python Developer	Python Developer experience in django and fastapi 	2008-01-01	Male	Ludhiana	Punjab	\N	\N	\N	2	\N	\N	[{"name": "Python ", "level": "Intermediate"}, {"name": "Django", "level": "Intermediate"}, {"name": "FastApi", "level": "Intermediate"}, {"name": "", "level": "Intermediate"}]	[{"company": "Tekki web solutions", "role": "", "start_date": "2024-01", "end_date": "2026-01", "description": "skill in python programming", "is_current": false}]	[{"institution": "LPU", "degree": "B.TECH", "field": "COMPUTER SCIENCE", "start_year": "2019", "end_year": "2023"}]	[{"name": "PCEP", "issuer": "", "date": "2025-01", "url": ""}]	[{"language": "English", "proficiency": "Conversational"}, {"language": "Hindi", "proficiency": "Conversational"}]	[]	\N	\N	\N	\N	2026-06-01 07:05:54.565625	2026-06-01 07:11:03.980839
\.


--
-- Data for Name: provider_availability_windows; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.provider_availability_windows (id, provider_id, day_of_week, start_time, end_time, start_period, end_period, period) FROM stdin;
\.


--
-- Data for Name: provider_interview_settings; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.provider_interview_settings (provider_id, auto_schedule_enabled, slot_duration_minutes, buffer_minutes, timezone, lookahead_days, min_notice_hours, default_title, default_interviewer_name, default_agenda, created_at, updated_at) FROM stdin;
6adffb4d-7db5-4ed5-88c1-2da3b405900b	f	30	0	UTC	14	24	Interview	\N	\N	2026-06-01 05:32:58.042851	2026-06-01 05:32:58.042853
abcf2d6b-b1e9-4a83-a2f0-5443768ef727	f	30	0	UTC	14	24	Interview	\N	\N	2026-06-01 07:15:40.322083	2026-06-01 07:15:40.322088
\.


--
-- Data for Name: resources; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.resources (id, milestone_id, title, type, url, platform, duration, difficulty, description, is_free, rating, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: resumes; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.resumes (id, user_id, filename, file_path, file_size_bytes, source, parsed_text, parsed_json, embedding, created_at, updated_at) FROM stdin;
07f1faf9-99aa-4d6c-bad4-07e790be7d18	7cafedbb-8887-46d4-ada6-557084d6caae	resume_built_fe49e77a.pdf	uploads/resumes/resume_built_fe49e77a.pdf	24060	builder	**Alice Johnson**\nalice.johnson@example.com | 9876500001 | Ludhiana, Punjab\n\n**Professional Headline**\nPython Developer\n\n**Professional Summary**\nResults-driven Python Developer with practical experience in Django and FastAPI frameworks. Proficient in Python programming, adept at developing robust and scalable applications. Eager to leverage technical skills in a dynamic development environment.\n\n**Technical Skills**\n*   **Programming Languages:** Python\n*   **Web Frameworks:** Django, FastAPI\n\n**Work Experience**\n\n**Python Developer** | Tekki Web Solutions | January 2024 – January 2026\n*   Applied Python programming skills in the development and implementation of web solutions.\n\n**Education**\n\n**Bachelor of Technology in Computer Science** | Lovely Professional University (LPU) | 2023\n\n**Certifications**\n\n**PCEP – Certified Entry-Level Python Programmer** | January 2025\n\n**Languages**\n*   English (Conversational)\n*   Hindi (Conversational)	{"name": "Alice Johnson", "email": "alice.johnson@example.com", "phone": "9876500001", "skills": ["Python ", "Django", "FastApi", ""], "experience": [{"title": "", "company": "Tekki web solutions", "start_date": "Jan 2024", "end_date": "Jan 2026", "description": "skill in python programming"}], "education": [{"degree": "B.TECH", "institution": "LPU", "field": "COMPUTER SCIENCE", "graduation_date": "2023"}], "summary": "Python Developer experience in django and fastapi "}	[-0.008408835,-0.005317772,0.005627162,-0.042373914,-0.006078114,0.027740706,0.01581161,0.008355079,0.013633809,-0.005835666,-0.033935003,-0.009754525,-0.0016522756,0.026702916,0.11804215,-0.005339378,-0.019140033,0.014658164,0.0051713204,-0.009638532,-0.018716753,0.03625123,0.012208425,-0.01120669,-0.010175388,-0.03876882,0.052997943,0.02496891,0.031706452,-0.008662193,-0.0031903044,-0.008284448,-0.023595817,0.013534943,-0.0071005337,0.019078715,9.853572e-05,-0.0056267707,-0.0033786313,0.008254717,-0.015220097,0.020801947,-0.014130158,-0.019175459,-0.0005702231,-0.0024225332,0.020217868,-0.0013464778,-0.026202817,0.02311928,-0.012679506,0.0024275125,-0.03174686,-0.18660562,-0.0067757354,0.017018603,0.002202495,0.0056666834,0.008054301,-0.027229805,-0.010613191,0.028463686,-0.02422425,0.0021649357,-0.0031383175,-0.017124392,0.02050295,0.0062464387,-0.006632233,-0.012621534,0.01668905,-0.006509728,-0.017693775,-0.033298466,-0.004991276,-0.033728577,0.01077625,-0.023425587,-0.008106102,0.0074359057,-0.0165592,-0.014520219,0.010988321,0.0010588181,0.0046569793,-0.030815445,0.008237632,-0.0070431433,0.008934791,-0.01143325,-0.009944575,0.023295319,0.002541663,0.028469363,-0.01838898,-0.012857998,-0.005678518,-0.00836979,-0.0025472685,0.007840507,-0.0108426,-0.031966135,0.004790236,-0.023554144,-0.014648208,-0.0030931414,0.02066635,-0.025828745,-0.03278355,-0.022633148,-0.0074150944,-0.014235198,-0.011191339,0.018968498,0.006252436,-0.15441427,-0.00061884755,-0.036970135,0.004305289,-0.008407326,-0.0072206673,0.02392375,0.0015154389,0.044671815,-0.030976856,0.0048137056,0.035468943,-0.017068796,-0.012365084,-0.009847542,-0.004662157,-0.019621506,0.025587391,-0.0030714897,0.0067550307,0.014192452,-0.00038975783,-0.015644765,-0.016381927,-0.009696962,0.0035370446,0.02552892,0.0029820234,0.010339539,0.0031822997,-0.0073412685,-0.009152776,-0.026594095,-0.024313664,-0.013113711,0.0043862415,-0.011070919,0.011570026,-0.020085631,0.007979594,-0.028852817,0.028205443,0.012616807,0.0022900887,-0.011083086,-0.017262852,-0.034955602,0.024316344,-0.0016654057,-0.0013379144,0.01835599,-0.00886163,0.011385382,0.007993688,0.018984592,-0.045946747,-0.006605887,0.019010562,0.01819085,-0.00032015872,-0.010142283,-0.017335312,0.027505124,0.03478338,-0.021695897,0.0065000565,0.00414933,0.006665219,0.00953564,-0.026412228,-0.0010931181,-0.031712648,0.0140908975,0.03744066,0.011931364,0.009212833,-0.0020328797,-0.016947538,-0.010448839,0.017107224,-0.026431449,0.0010064571,-0.009826426,-0.0018692815,-0.013152977,0.0017137361,0.009437603,-0.010874294,-0.008344592,0.003355585,0.0031097166,-0.009059562,-0.01857061,0.007909653,-0.012628639,0.0018956811,0.0036835733,0.028979402,-0.008106261,-0.016375344,-0.008979309,0.0017944186,0.021882745,-0.0046209586,0.0023153035,-0.0031134475,-0.00029807247,-0.0038304036,0.019989254,-0.02457077,-0.010147318,0.009984965,-0.004924383,0.006384492,0.00082224124,0.016922336,-0.0074727596,-0.01031022,0.0048853788,0.004301088,-0.026174108,0.008953143,0.0051865224,0.031153578,-0.0059688436,0.01275581,0.018687503,-0.013861351,0.020268511,0.030255452,0.0052626403,0.009115286,0.03701918,-0.0031582536,-0.022479188,-0.020691667,-0.027589988,0.03472109,-0.0073979483,0.011287106,-0.016775765,-0.012389906,0.0103334235,-0.015873516,0.02921331,-0.004551937,-0.010431777,0.0018075263,-0.013474928,-0.0077386564,-0.0145447645,0.019413767,0.011101873,0.010972869,0.00956987,0.0059202886,0.015573522,0.018844638,-0.006166518,0.016200455,-0.016444067,-0.055949267,0.0019653873,0.0130524775,-0.02892297,0.010109254,0.038555577,-0.009735027,-0.03194311,-0.0048698513,0.009597419,0.019766647,-0.019318776,0.0006466054,0.0007992939,-0.008135802,-0.011429862,-0.019570002,-0.0004962554,0.017467296,-0.027459139,-0.0064047296,-0.01601417,0.00623185,-0.0048273676,0.002941251,-0.008111366,0.025842387,0.055444352,0.027511712,-0.008557506,-0.028554568,0.042272504,-2.3060615e-05,-0.0058941557,-0.008548181,-0.004070279,0.015751036,-0.03568919,-0.005600093,0.004881039,0.01557434,-0.00872638,-0.0150340265,-0.0031147273,0.000716135,-0.0015352364,0.0029178262,0.017715514,-0.013018355,0.008611885,-0.024501696,0.016965376,0.036812264,-0.013257038,0.00040297414,0.03124738,-0.020276612,-0.016077094,-0.0036404582,0.011170568,0.012541553,-0.0014942626,-0.011714328,-0.00698557,-0.02278383,0.0035510275,0.014330542,-0.0030127016,-0.008733456,-0.007823267,0.005054915,-0.020706508,0.014164381,-0.0016904278,-0.014391917,0.015472784,-0.025150187,-0.040642407,-6.96292e-05,0.0042426274,0.008645854,0.010292699,0.008715484,0.024621498,0.0071702455,0.004314857,-0.0063406215,0.002417968,-0.012424467,-0.004696402,0.030957537,0.013650261,-0.031072808,-0.020268993,-0.008098609,0.00044736115,0.011309426,-0.0012875377,-0.04224985,0.0016228582,-0.026139745,0.001331,-0.013156444,0.008064829,-0.035403028,-0.011157065,0.025551345,0.013818659,0.01874684,0.011372059,0.031834006,0.010624546,-0.010251672,0.0040877745,-0.01027196,0.032395765,-0.0006830413,0.024002397,-0.0013287681,-0.029936593,-0.01434821,-0.009379415,-0.03469164,0.007176538,0.0033620293,0.024068518,-0.017258728,-0.017757101,0.0046963035,-0.005792434,0.023475986,-0.003423854,-0.0037440276,0.033087138,-0.0055344678,-0.0032380188,0.027126597,0.014878326,-0.0033316365,0.01976077,0.014888423,0.0007177221,0.016412638,0.01661197,-0.017703207,0.018023323,-0.01821236,0.002546575,0.018317983,-0.0010102753,-0.02091839,0.010265468,-0.0065639447,0.0011489798,-0.029159088,-0.004647346,-0.013263727,-0.015800746,-0.014823366,-0.007888796,0.0010889762,-0.013181618,0.0007948469,-0.013665181,0.014513221,-0.00786219,0.01861956,-0.01461661,0.011878504,-0.01652962,-0.016409555,-0.005161914,-0.025831696,-0.001420211,-0.0018151986,0.0179337,0.016623767,-0.003451865,0.004478036,0.017427726,-0.0038181618,0.020978179,-0.00718574,0.03108723,-0.033835147,0.011811729,-0.012270911,0.03097145,-0.02355218,0.00018611857,0.011017716,0.014734279,-0.033248954,0.030756265,-0.008541932,-0.0072595556,-0.014337043,-0.0027864985,0.014710803,-0.00022241483,0.021790346,-0.02875621,-0.016315343,0.0028799037,0.015678251,-0.003011435,-0.028618624,0.0038159462,0.014227268,0.037423894,-0.008118613,-0.019793171,0.031845108,0.013274391,0.017656038,0.031818114,0.003353072,0.0048075095,0.0051581245,-0.031223265,-0.0036950458,-0.003252606,-0.0100733135,0.0059767435,-0.026471555,0.012595799,-0.0057982644,0.016922696,0.0150066,-0.017974015,0.009283578,0.0005716449,0.014530904,0.0036757619,0.0109359,-0.030526115,0.0053208387,-0.014016485,-0.020590091,0.012920056,-0.017381469,-0.016829088,0.0013224521,-0.04639772,0.025145723,-0.031861857,-0.010335966,0.002855053,0.0023922506,0.032294642,0.028267024,0.0026149235,0.0025982936,0.006203104,0.0011634118,0.0323463,0.005157418,-0.008633511,0.012447894,0.0019168641,0.010985156,0.011131114,-0.017928582,0.020784464,0.010063892,-0.021902066,-0.012963628,-0.030244531,0.008978972,-0.07439696,-0.012786067,-0.0076360353,-0.015583379,-0.012981401,-0.0056262105,-0.003561387,-0.010823726,-0.019835573,0.01948129,-0.0059738797,-0.018467288,0.0015417067,0.00278224,-0.020958748,0.0022359025,-0.012438066,0.03163171,0.007323022,-0.041013833,-0.0062605087,0.0071763434,-0.0013470287,0.0013936274,-0.008191559,-0.005273505,0.011155709,0.01253125,0.024949055,0.02443759,-0.023500824,0.0016394475,-0.0042199614,0.022615472,-0.014014604,-0.020998765,-0.0041643004,-0.017487826,-0.006359072,-0.0031938925,0.00795038,-0.008414484,0.009636165,-0.00080230815,-0.018676367,0.028576676,-0.0070024943,-0.012267587,-0.009330158,0.008297251,-0.047189612,-0.010307443,0.0062460694,0.010913463,-0.004020992,-0.0028932036,-0.017574755,-0.00199878,0.007272985,0.0034658466,-0.017020838,0.0152365,0.017775938,0.018570337,0.004027973,0.02842403,0.0076227523,0.026004015,-0.014163192,-0.011279141,-0.009700769,-0.0031617843,-0.022426127,0.014985588,0.00053093705,0.01241728,-0.004364273,0.035907764,0.017829515,-0.01690625,-0.033860408,0.0064369645,-0.027836295,-0.0029336005,0.0036641248,-0.026455872,-0.0013519058,-0.00062631676,0.005152718,-0.03814044,-0.0044664037,-0.031605776,-0.014265262,-0.036206417,0.01875964,-0.014008836,-0.0140254935,0.014515444,-0.0010374761,0.015870782,-0.00999764,-0.012262795,0.015724307,0.019091789,0.004424552,-0.0007744191,0.0033442643,-0.008584501,0.0011616873,0.011480337,-0.003942923,-0.008830989,0.014743975,-0.18477952,-0.009103848,0.012581535,-0.01370608,0.041274212,0.026340451,-0.022114864,0.024419054,-0.025068711,-0.03805673,0.014608358,-0.0017931836,-0.034940924,-0.010515051,-0.009572759,0.087771475,-0.0004287847,-0.013478089,-0.0280544,-0.029381521,0.00405808,-0.014629264,-0.025230747,0.015214253,0.003674108,-0.014565127,-0.026109286,0.004382668,-0.010375197,-0.019883048,-0.00615286,-0.0045070173,-0.0039626253,0.003714836,0.0108341025,0.013757032,0.02011544,0.002429496,0.026127737,0.0062187095,0.031027824,0.011831826,-0.0343256,0.024554165,-0.000312423,-0.0018208086,-0.024606872,-0.0023148549,-0.021668442,0.0077652396,-0.013351977,-0.070397906,-0.020123197,0.006065943,0.0047192904,0.017180644,0.004988904,0.021911291,0.0070623793,0.024763485,-0.029044848,0.016688533,-0.0016422193,0.011854646,0.0042234696,0.0020089452,0.015415126,-0.011272975,-0.0220822,0.0075128,0.0051256763,0.0066351467,-0.0004923828,0.00058558653,0.004743604,0.008240259,-0.02880398,0.017203288,-0.014016073,0.00044627782,-0.009530498,0.026530597,-0.020560784,-0.020719815,0.00037578325,-0.015654473,-0.0053033074,-0.0079829935,0.007394364,0.007949748,-0.008596457,0.018385569,-0.010753318,0.00055143004,0.01194734,-0.010755806,-0.010480178,0.0020750589,0.0126722865,-0.011173451,-0.017351536,-0.037013344,0.0071019647,-0.031157034,0.0021729376,0.012035419,0.0355932,-0.0045813243,0.0355343,0.023082096,-0.0037561704,0.014667644,-0.0087755425,-0.0033204756,0.013599171,0.004162391,0.003497689,-0.0026711822,-0.0073263873,-0.018921463,0.012139156,-0.0054651718,-0.011559069,-0.0086519215,-0.00060426333,-0.009792608,-0.006587965,0.0004512453,0.0010895643,-0.012204834,-0.00096141425,-0.013115137,0.006783602,-0.007944516,-0.019835595,0.0133483,-0.0044386797,-0.0098685315,-0.00329349,-0.016805684,0.026850788,-0.006224705,0.005804808,-0.00067236053,0.006347738,-0.015235539,0.0018081143,0.0051531694,-0.011681918,-0.00039863543,0.0057807853,-0.0335257,0.010084963,0.011934757,0.010159328,0.0089488,0.0037647262,0.0026556016,-2.7988142e-05,-0.014434,-0.0083458675,-0.0011951424,0.0039976826,-0.023331251,0.006043935,0.013580544,0.008546308,-0.015018246,-0.00030276238,-0.007554899,0.006849788,0.0014841604,-0.010580438,-0.004365578,0.021120368,0.0005925758,-0.0015166721,-0.0069749826,-0.01267038,0.013729712,-0.023904994,0.01265998,0.005133608,-0.008626897,-0.007056281,0.012663449,0.008014279,-0.0012732524,-0.006998533,0.004622432,0.0028912395,-0.027972594,0.0012952321,-0.012148989,0.009604058,-0.0021183742,-0.017473172,0.0020709827,-0.017792024,0.0033859538,0.003724068,0.012529011,-0.0018931963,0.004266257,-0.018975064,-0.003224107,0.0047009615,0.019157557,0.005327446,0.0082927765,-0.0038020238,-0.009137876,0.008909238,0.0130225355,-0.008852614,0.012014436,-0.013892492,-0.00042586427,-0.0022136876,0.0025445076,-0.0169479,-0.0015609588,0.005107587,0.0065395553,0.020334851,-0.0055424417,0.010691591,0.0074855313,0.0054553947,-0.0024632763,0.0046752444,0.008545301,0.010926731,0.01060336,4.9359787e-05,0.005651987,0.015898159,-0.007769458,0.005228099,0.012386144,0.0116308965,0.026663987,-0.0044953115,-0.017909087,0.001546411,-0.00048963143,0.016932018,0.0019837928,-0.01194858,0.0048375754,-0.005525606,0.008990441,0.02535076,-0.0047743064,-0.006496486,0.0005390952,-0.006045035,0.0079757795,0.00080678996,-0.011247597,0.013409315,-0.00492772,-0.017188659,-0.0031456824,0.023723165,-0.013768446,0.00053037645,0.009765995,0.008316481,0.0055216714,0.0063582594,-0.011746841,-0.00061501,0.012476166,-0.0051113768,-0.0009526822,-0.00827463,-0.0075395848,-0.0036204518,-0.008701824,0.0027085703,-0.009037881,-0.020279737,0.0039944323,0.0036031867,0.013118553,0.027032206,-0.016343985,-0.0075508025,-0.015018604,-0.00351072,-0.00094107096,-0.009051403,0.01762626,-0.029730985,0.014561877,-0.0026527916,-0.015886249,0.008805831,-0.011334316,0.00043223432,0.011168969,-0.0045830514,-0.0037912454,0.017818809,-0.00787527,-0.01000545,-0.0033449575,0.023265876,0.0109805865,0.11664588,0.009552788,0.0034156807,-0.00789738,-0.024071423,0.00953971,0.011906578,-0.01684179,-0.00033472417,-0.015880384,-0.009501584,-0.0011903407,-0.006413392,0.0020112924,0.0021385653,-0.0062205684,0.0065480354,0.015124223,-0.005517914,-0.0004749798,-0.012269117,0.007843485,-0.010204222,0.002587246,0.014529567,-0.0031425653,0.0008729962,0.007945177,-0.011589912,0.016739875,0.005359074,0.014907515,-0.01939947,-0.0113308765,-0.0007168118,-0.0241392,-0.022619408,-0.0040122513,-0.003874885,0.026850976,0.00056143233,0.007710488,0.001364271,-0.0010548191,0.0077652633,0.019182084,-0.02284622,0.006925586,-0.031178333,-0.007889454,-0.0021820744,0.0009748138,0.007902724,0.01678839,-0.0070108636,-0.017798511,-0.0043533104,-0.010877941,0.0073783468,-0.005880754,-0.0134556815,-0.0025058116,-0.017107258,-0.027086623,-0.0007239394,-0.016874017,0.009509127,-0.026830902,0.004272069,0.0037588922,0.0024139574,-0.0076538054,-0.005314796,0.011084229,0.015681457,-0.012581781,0.0019714937,0.008926151,0.004450192,-0.00065792,-0.010083981,-0.0012633143,-0.017083514,0.0007026863,0.0012014029,-0.013665758,-0.0046698716,0.0020945084,0.016670091,-0.00042441933,0.020682985,0.002737697,-0.014571037,-0.008544237,-0.009330673,0.015776668,0.039824706,0.004352348,-0.0032136012,0.016175002,-0.0012425012,-0.004782347,-0.013517739,-0.0071431515,0.018232109,0.010538824,-0.006141087,-0.021715831,0.016713057,0.0037616617,-0.0046094074,0.005072037,0.0050131064,0.003992152,-0.00718072,-0.005224195,-0.005124884,0.018013442,0.0032519973,0.0052560302,0.0236802,-0.013287668,-0.020694418,0.008391443,0.012341904,0.0071351593,-0.0027955682,-0.021621546,0.0074494714,-0.003961359,0.0046904036,-0.013822393,0.019148994,0.009658265,0.0047526974,0.026392577,0.0021321634,0.0016622351,0.0042972974,-0.000180999,-0.011749508,-0.009781799,-0.013474743,0.014904166,-0.015230381,0.024962269,0.005131962,0.006939336,0.010873764,-0.009355904,-0.008221927,-0.0059758197,0.0069141835,0.019213215,-0.008681101,-0.000676223,0.001873113,0.009061983,-0.011289174,0.014157675,-0.013421223,0.009474945,-0.006119548,0.00095421146,-0.008181164,-0.005723178,-0.010978511,0.011309104,-0.008320566,0.01493409,-0.0055890298,-0.01705275,0.0035708605,-0.0136020845,-0.005583415,-0.00053262204,0.0077288616,0.00026838915,0.007576979,0.004553132,-0.0027047584,0.011521373,-0.022277517,-0.009640907,-0.0051391996,0.003743778,-2.9172235e-05,-0.0047263233,-0.0027030322,-0.021974796,0.0021760713,-0.008315538,0.007010448,-0.0006038381,0.017152628,0.0061953044,0.018716827,-0.00074665464,-0.0018470682,-0.0024712277,0.011504452,0.008063859,-4.9775503e-05,-0.009616763,0.010204274,-0.0068207853,-0.01596955,-0.01023626,-0.0065413187,-0.0014268322,-0.024966933,-0.021366239,0.0101144165,-0.013189454,-0.004740692,0.0051936163,0.009045517,-0.010915612,-0.0030442127,-0.0020831234,-0.01028914,-0.017259387,0.005722097,0.0016748579,0.00613748,0.00059715135,0.0163263,0.02485178,-0.012436274,0.015700985,-0.010872171,0.010252922,-0.0105627,0.0067383572,-0.0061038435,-0.008053408,-0.011783373,-0.030789688,-0.0042383107,-0.009731591,-0.0061515076,0.00015054688,-0.0073378496,-0.008403785,-0.014385271,-0.009145685,-0.01479271,0.004314302,-0.012696623,0.007355155,0.010583187,-0.0019996357,-0.0050233547,0.020570518,0.014079158,0.0026764076,0.005484195,-0.04396245,0.0094032055,0.011746964,0.010688619,0.00033639354,-0.017113345,0.003218995,0.011242795,-0.004561078,-0.0032402854,0.006313233,0.0005202975,0.0067205955,0.0049866773,-0.009229855,-0.0076947515,-0.0011317157,0.009274403,0.010284059,-0.018464921,-0.005122792,-0.010512642,-0.009193323,-0.0039031138,-0.013361998,-0.021670613,-0.022900417,0.00096183165,0.007819784,-0.015973262,-0.007463159,-0.0036742808,-0.014911865,-0.000106696934,-0.015350644,0.00048069895,0.0019719983,0.005716475,0.008226554,-0.021397654,0.015658738,-2.6787677e-05,0.00377011,-0.0050466703,-0.001205419,0.0010580816,0.0032624183,-0.006480541,0.018086644,0.023268163,0.003937064,0.012600881,-3.1031563e-05,0.005332407,0.00041044937,-0.002919504,0.011565283,0.0022397304,-0.0064623426,0.0145383915,-0.0062808185,0.006894865,0.00021182702,-0.0016290375,-0.014529491,-0.0015343194,0.014968833,-0.0059950924,-0.015143857,0.03145928,0.0010127396,0.021790111,0.001912388,-0.006132278,-0.0058763553,0.01275448,0.011746915,0.018944798,-0.0048492714,0.0035775797,-0.0036064251,0.009028094,-0.00912096,-0.010531193,-0.0064531267,0.0051532527,-0.0015702855,-0.0034982313,-0.014673148,0.0056628683,0.0063644135,-0.010363235,0.010088855,-0.011785343,0.0040397933,0.020497864,0.0012027352,-0.0013419385,0.00456566,0.015389411,-0.001875883,-0.0131435925,0.0014393228,0.008558115,-0.028578477,0.021479297,-0.016495228,0.008403509,0.0014849555,-0.010738559,0.002457801,0.0024873565,0.0077639516,-0.0067377375,0.010249152,-0.008757623,-0.0047863494,-0.005790151,0.0033780946,0.017310498,-0.03115311,-0.01270952,-0.021049779,-0.009538241,0.009518745,0.0013993529,-0.0077579287,0.0042297635,-0.0025975592,-0.0013619625,0.004853733,-0.0039062765,0.0017721907,0.010511025,-0.00059222983,0.018165853,0.016315358,0.0009312295,-0.0027303828,-0.0042393706,0.015216981,0.017411944,0.0072394144,-0.014209106,3.1409003e-05,0.005955341,-0.010249093,0.0029269732,-0.01969465,0.012569166,0.010898062,0.008068074,0.0046834657,0.0078819785,0.000995068,0.019296795,0.016167844,-0.004111308,0.00056487974,-0.018901693,0.002375908,0.010109001,-0.010449421,0.0056598186,-0.0050539514,-0.000869727,-0.014374075,0.017040953,-0.008032337,-0.002659689,-0.0056713996,-0.0111302575,0.0063847005,0.00024603747,0.011274651,0.013464892,0.0058351257,-0.0036192895,-0.0073911143,-0.006474267,-0.0053045712,-0.0042128004,0.00035180402,-0.0042551276,0.024604557,0.0051441356,0.0040726312,-0.0037169894,-0.0038959004,-0.0048825643,0.0071935835,-0.0043011284,0.0055598454,-0.00094131153,-0.004603129,0.01229215,0.004533204,-0.011651545,-0.0008776675,0.0051108827,-0.01605644,-0.007044474,0.013507994,-0.00885523,-0.018118354,-0.09343825,-0.016059572,-0.00074706,0.0074258097,0.00972868,0.00074055174,-0.021862369,-0.010348991,-0.019669557,0.008096823,-0.009407922,0.004996566,-0.004241898,-0.027223038,-0.0064382977,-0.024534458,-0.0020370313,-0.0050379313,-0.0025726,-0.0058979965,0.013550206,0.013327412,-0.010390518,0.013264883,-0.023225188,0.0077193826,-0.026812095,-0.009874023,-0.011433926,0.007523011,-0.0040272577,-0.018777447,0.0067906934,0.006734256,0.0009066933,-0.0029169482,0.0120966,0.0065226797,-0.12778558,-0.010436907,-0.0095357485,-0.0026310498,-0.0035623896,-0.018879354,0.0019714825,-0.005797053,-0.0026072424,0.009750923,-0.0069821607,-0.008132986,-0.008830266,-0.017830465,0.0064938925,0.0059785605,-0.004587033,0.006152157,0.008963055,-0.0012251069,-0.010326657,-0.0032207845,0.000111142814,-0.011332576,0.0029029779,0.0065163644,-0.0020326453,0.008742199,-0.002727465,-0.0034083736,0.016861975,0.00494218,0.011331328,0.0020014755,0.008455279,0.010138345,0.0014799307,0.0015046945,-0.006770948,0.004894105,0.0032920022,0.0024401806,0.0064228782,-0.0011144583,0.025072575,0.0015528038,0.0031903149,-0.005266139,0.0041352077,0.0049274163,-0.00075453246,-0.013453825,0.0046529085,9.369271e-05,0.002122927,0.0012341398,0.0006850037,0.011579019,-0.017454004,0.002484214,-0.0027990656,0.00018957589,0.002164707,-0.008785781,0.016510682,0.013206043,0.015592366,0.012535573,0.007832248,0.0143964905,0.013593067,0.013219433,-0.010208375,-0.012959686,0.005102729,-0.02134883,-0.014651924,-0.0073197894,-0.014817032,-0.015651992,-0.008463022,-0.011182254,-0.0071946876,0.009080248,0.0072217477,-0.016329015,-0.0047974302,-0.019628761,0.009166596,-0.03928546,0.018780477,0.00042247682,-0.002449132,-0.0041987407,-0.009671822,0.010072303,0.009520766,0.0133802295,0.0007119945,0.011521713,-0.00038717792,-0.002838719,-0.018852506,-0.0012971425,0.015258585,-0.0066304966,-0.02411129,-0.008331411,0.014503269,-0.0031060532,-0.018914713,-0.009054064,0.0025399637,0.011070399,-0.022745753,0.008135965,0.019442847,0.010330355,-0.009253558,-0.008763908,0.013644868,-0.0014977674,-0.0063869245,-0.003809148,0.0056295884,-0.006757004,0.015213223,-0.0035151339,-0.00040756082,0.013514916,-0.001973441,0.001258877,0.016157642,-0.0010908255,0.0003727009,-0.00014839452,-0.010309707,-0.0078152,0.0132532315,0.011967425,0.0018843429,-0.015034234,-0.000385256,0.008402615,0.02017397,-0.011159974,0.003910026,0.0130929,0.0017031839,0.020205405,-0.017655028,0.0026092494,-0.0066524786,0.00585438,-0.0002833465,0.0025490415,0.027989505,-0.021264253,-0.0072280085,0.007045549,0.0056063854,-0.0012518755,0.006296636,-0.01613199,0.002357798,-0.004391966,0.021128582,-0.012864073,0.027550085,0.0017363334,0.011185979,0.0053705676,-0.00042658288,0.011354026,-0.011082808,-0.005646123,-0.013876797,0.001965032,0.0006396575,0.007488489,-0.049778406,-0.014577489,-0.0011175354,-0.022829492,0.025957128,-0.002140463,-0.0026785694,-0.0028586667,-0.018442407,-0.016329724,0.017186401,-0.024388263,0.009334442,-0.00525451,-0.008220234,0.0125572095,-0.0033247087,-0.01585297,0.0046014534,0.023888264,-0.0068681818,0.013852728,-0.0028024842,-0.17119433,0.0019038032,0.008825373,0.019026507,0.010227428,-0.002551094,0.0019584391,0.0038469257,0.01691184,-0.01012357,-0.0048284116,0.0035409865,0.008096389,-0.004627602,-0.004713555,-0.010731895,-0.010239667,-0.004300825,-0.0038980076,-0.007190114,-0.0023526778,0.0131698055,0.0026168062,0.0055885734,-0.022740388,0.0035119595,0.006002681,0.013104436,-0.018920261,-0.024186343,-0.016149148,0.0073736887,0.021194214,-0.00674444,0.005184327,-0.017993568,-0.00950966,-0.0017044473,0.032377306,0.015710067,-0.013249096,0.008485325,-0.022970391,0.008272553,-0.007326768,-0.0026896943,-0.019180538,-0.017162103,-0.018923007,-0.011519489,0.010796173,-0.028402075,0.020391151,-0.0058957757,0.019083073,-0.031339966,0.019064229,-0.03964766,-0.0028958386,0.005833004,-0.01303618,-0.042701468,0.015025329,-0.0023145017,0.0215944,-0.013396112,0.013443328,0.15374056,-0.0014727381,0.024853257,-0.010153421,0.027034627,0.032680407,0.001862115,-0.023269864,-0.019125368,0.007810395,0.0062409597,-0.015647408,-0.0048475564,0.0015385014,-0.014021651,-0.0158938,0.008623347,0.018497117,0.004795577,-0.004046129,0.002273843,-0.009712165,0.013746093,-0.018776076,0.04293951,0.009690731,0.006363497,0.008432131,0.0027018925,0.017650448,-0.009040292,-0.013772363,0.0014165043,-0.0030649118,-0.009340291,0.0113387145,-0.005726725,-0.008155778,0.01652896,0.01833768,0.021165488,0.027232446,-0.008049471,-0.008281894,0.004523507,-0.002069203,-0.00033554088,0.015044004,0.0053033466,-0.0065718573,-0.01477744,-0.029958434,0.014036597,-0.003088908,0.021191048,-0.010805258,-0.007911748,-0.016526328,-0.010116812,-0.013205238,-0.0069315988,0.0018090568,-0.023063732,0.0028981236,0.024471208,-0.0019847946,0.017403804,0.00025708365,-0.0026562875,-0.10564005,-0.0028924486,-0.024572968,-0.016815728,0.00066757173,0.010153271,0.02739599,-0.014697619,0.006595035,-0.00060844474,-0.013172245,0.0101150945,0.009106262,0.010721867,-0.015803171,-0.0017390844,-0.0014121281,-0.016115453,0.04182478,-0.010033876,-0.014659087,0.0008075242,-0.01289732,-0.01582326,0.004152333,0.019074842,-0.027623245,-0.011514177,0.016463073,-0.0134968525,0.031105837,0.017225983,-0.0026486139,0.024101272,0.00432222,-0.018217387,0.0044404957,0.022750888,0.006947161,-0.00022496002,-0.004210875,0.009841609,-0.0010036859,0.011113637,0.009527644,-3.2861684e-05,0.024192601,-0.006436608,0.002123761,0.0006109413,-0.014020728,0.0020277894,-0.00038075124,-0.0046459273,-0.025050797,0.016390288,-0.017760584,-0.006585388,0.005063914,-0.015767174,0.008716737,-0.002752335,0.0008525622,0.004002457,0.017901497,-0.021046396,-0.009087783,-0.013820222,0.014092375,-0.01276596,-0.009848644,-0.0066154688,0.008112669,0.011386925,0.0013965628,-0.005895187,0.0034770677,0.001338783,-0.02211425,-0.0042424183,0.0032777544,-0.015841302,0.015309313,-0.0074896277,0.04610022,-0.012889291,-0.006909733,-0.012129809,-0.0047055166,-0.009557033,-0.0006489265,0.0018135012,-0.011228347,0.016429607,-0.0060083456,-0.0047315783,0.005823332,-0.01110021,0.0015356409,-0.018099826,0.009073443,0.009398311,0.021454455,0.0049587996,-0.00056023564,-0.010861661,0.008348041,-0.010349364,-0.02338554,-0.016883614,-0.008308764,-0.011927844,-0.0040930314,-0.003404611,-0.0011200293,0.010059049,-0.004247398,-0.026011549,-0.015289683,-0.0070182797,0.0034456684,0.004364513,0.013761635,-0.0042600553,-0.019073958,-0.019868514,0.02463594,0.0009225708,0.0014459736,-0.020706456,0.00622814,-0.0058782715,-0.0003663147,0.01599094,0.03294331,-0.0011931027,0.026155977,0.008032025,-0.011023303,0.019618198,-0.005030872,-0.00437105,0.009507174,0.0045184945,-0.00011428756,-0.004885241,0.015058765,0.02354255,0.0035561346,-7.442265e-05,0.0042312415,0.007725586,-0.0097812675,0.0125075765,0.01303351,0.008446325,-0.010245264,-0.005649834,-0.015261746,-0.008619341,-0.015124982,0.03076421,-0.021586007,0.0032546136,0.0065807723,-0.012700819,0.0009648933,-0.010180949,0.008356118,-0.02232523,-0.01730703,0.0061656125,0.008283901,-0.0204388,-0.008782773,-0.01762511,0.0019934243,0.0075860596,-0.0042281845,-0.068616666,0.017392633,-0.005101919,-0.011031257,-0.0019592796,0.0038144167,-0.019957336,5.3926688e-05,-0.019214483,-0.020960579,-0.0045172735,-0.0068652774,0.0022402704,0.026184767,0.0024036935,-0.00545633,-0.018097611,-0.0012790607,-0.0059006526,0.01079978,0.017196478,0.00042699062,-0.016898511,-0.008524647,-0.024292946,-0.015803192,-0.01575406,0.007673369,0.01665472,-0.014334237,0.0063023292,-0.015119034,0.016080096,-0.00565244,-0.011104078,-0.009389984,0.010021634,-0.012936613,0.009231196,-0.009390443,0.022929436,0.008980801,-0.06889598,-0.010304861,0.0062623355,-0.011719898,0.022781327,0.022475513,0.004374298,-0.012012752,0.012495574,-0.005870138,-0.0007225239,0.01257297,0.0048178458,-0.025620816,0.013306311,-0.005021153,-0.020122556,0.026817545,-0.01657322,0.012989649,-0.007478043,0.012696165,0.015308862,0.011326059,-0.00075499265,0.023875214,-0.012566732,0.029128823,0.0024278099,-0.01759462,-0.017942235,-0.019130353,-0.018648727,-0.006465081,0.012476934,-0.010578447,0.0001989104,0.026920618,-0.00167803,0.024919808,-0.011940859,0.009902965,0.010978818,-0.0029343385,0.0052672895,-0.117727295,-0.022314109,0.005133564,-0.0024511272,0.009338252,0.0024793851,-0.0062784944,0.04397318,0.013702063,-0.038096596,-0.014813715,0.00010411038,-0.0026278968,0.007855086,-0.028563796,-0.008032204,0.01535362,0.0012786314,0.007095427,0.029448394,0.012113648,-0.02081167,0.0115281055,-0.0034251986,0.018605568,-0.02786308,-0.0084774345,-0.01642659,0.005270846,-0.0035382207,-0.0073539945,0.015749678,0.00034773003,-0.008048861,-0.007498398,0.013172711,-0.013183299,-0.01705245,0.017847674,0.005773951,-0.010325344,-0.010043268,0.008184081,0.0069573307,-0.028871823,0.01441969,0.007306548,-0.0017455119,-0.021912279,-0.012521993,-0.0032776317,-0.0040512225,0.0015060974,-0.022031823,0.033672173,0.0054203104,0.0013378916,-0.0034163452,0.0097352,-0.0001763091,-0.0042507364,-0.0010695285,0.013763074,-0.01888137,-0.03326955,0.005370794,-0.0070751756,-0.02308372,-0.009811625,-0.009677548,-0.0047667646,0.0015363953,0.0282702,0.009855076,0.00062094716,-0.0016934352,-0.0034566668,0.014116262,-0.026044415,-0.0035492044,-0.018509017,0.00973007,-0.00066872686,0.0029109744,0.00065516686,-0.010214227,-0.0020386816,0.010125672,-0.0134226745,-0.006932366,-0.002247021,-0.033436522,0.025802828,0.025831977,-0.002206411,-0.004434904,-0.011822539,-0.021100435,0.012007036,-0.021466615,-0.0016159174,-0.003597462,-0.019585313,-0.018713262,-0.012834671,0.0010833008,0.0036862567,0.016694222,0.0037917497,-0.0024787842,0.00439488,0.0020890234,-0.029671276,0.026731154,-0.0095132915,1.5704501e-05,-0.0007470175,0.00631625,0.009861375,-0.012410984,-0.00064351043,-0.034164697,0.010802342,-0.017136276,-0.008610174,-0.0027064125,-0.013115071,0.003737175,0.013903308,0.025515033,0.02853542,0.027629342,0.013377504,0.017837638,0.002389704,-0.011018459,-0.014586811,0.005390472,-0.01641436,-0.006920614,-0.018901948,0.003416654,0.021727245,0.003352431,-0.006303595,-0.0056406246,0.00249116,0.0071246824,0.0037814009,-0.03149562,-0.0015858759,0.012576538,0.0064694937,0.004686735,-0.031101702,-0.0016392318,-0.020042626,-0.0038058837,0.011111502,0.010026638,0.0057779592,0.019962825,-0.0063461442,0.00598107,0.013779398,-0.015432015,0.015218896,0.002563711,0.027448343,0.0014503807,0.016237851,0.0066917343,-0.011680397,-0.004256984,0.024093341,-0.029120319,0.011118025,0.020121275,-0.024897177,-0.005972375,0.0075945565,-0.0009514073,-0.018395675,0.012993389,-0.022824582,-0.026800998,0.004640598,0.001002182,0.01516416,-0.0048096334,0.0012388469,0.0042186393,0.024075052,0.0098513905,-0.011717895,-0.004991077,0.0017117736,0.03196281,0.011483731,0.026718032,0.005293993,-0.014143305,-0.008343847,0.004673946,-0.0028974565,0.00032949462,-0.03515362,-0.0045540025,-0.020172318,0.0069759977,0.014658386,-0.010616008,0.008886928,-0.0009137691,-0.007980033,0.0029672545,-0.0050886306,-0.012378459,0.01816118,0.029367365,0.005688883,0.02456807,-0.00084660586,0.0164168,0.017479116,0.008263991,0.0098102335,-0.008079191,-0.0026295197,0.0045005055,0.0012179718,-0.015044864,-0.014500769,-0.0013433695,0.010935356,0.0034901688,0.0055514546,-0.017175442,0.010020702,0.01193914,0.02594164,0.018009044,0.029163565,0.033963468,-0.012039019,-0.017493479,-0.01535278,-0.012362352,-0.018465579,0.007164073,0.016410634,-0.00944752,-0.009112026,0.00055438443,0.0014822925,-0.01159385,-0.0017338645,0.0019355792,0.011828731,-0.02142539,0.01974276,0.0051764534,-0.0015192718,-0.011441594,-0.014005895,-0.006061288,0.00028341688,0.015269879,0.006584082,-0.0051164078,0.02075992,-0.004963306,-0.01390211,0.009879986,-0.0072542652,0.008770133,-0.008120158,-0.0030933614,-0.01765493,0.020797616,0.021529716,0.004327333,0.009234766,0.009865056,0.024216542,0.0027761979,0.0036053825,0.008565396,0.0015810177,-0.013457074,0.0035283451,-0.0056496533,0.0017493645,-0.0032796243,-0.0016093774,-0.009355749,-0.008952566,-0.007994,-0.0035952246,-0.00018512542,0.033062916,-0.012558933,-0.0061143753,-0.010837689,0.013526447,-0.018624535,0.025282696,-0.016438892,0.013724973,0.0009172114,0.007757282,-0.0014755096,0.0006828081,0.0276657,-0.02185725,0.01942974,-0.02819592,-0.0027969647,-0.010876675,-0.02502752,-0.0004704439,0.019248733,-0.0050523896,-0.00022295113,0.0003724867,0.00488371,-0.0058880276,-0.010466265,0.0068069114,-0.0115049435,0.004042963,0.0008966095,-0.003241106,0.00041650524,-0.00849814,0.0036834744,0.0021218385,0.0064755096,-0.015621585,0.0015713801,-0.017891383,0.019771112,0.018595878,0.012191171,0.008208708,-0.012193017,0.013560442,-0.009154313,0.011695085,-0.013225025,-0.024021843,-0.00089961884,0.01433,0.01161407,-0.014837272,-0.005787015,0.0006312425,-0.0074192304,0.015736923,-0.010542414,-0.010348074,0.023976099,0.0017199644,0.025760587,-0.005707672,-0.0034759229,-0.019020218,-0.026994888,-0.016677182,0.014378647,0.016917568,0.030517222,0.0041511734,0.00082885596,-0.002350823,0.0069045294,-0.0057833646,-0.0020021703,0.010069833,-0.0055978335,0.002955508,-0.0008993308,-0.0031067359,0.019126346,0.0018729612,-0.0061345585,0.0024730805,0.006080826,0.021417944,-0.017247172,0.0060677086,-0.002120464,0.017331954,-0.0135192,0.0012683048,0.0014302182,-0.01036938,0.003927547,-0.0049821343,0.011288304,0.0048485827,0.010878504,0.021150617,-0.013139303,0.011987779,-0.0067924145,-0.011690876,0.0033382953,-0.023564672,-0.007588878,0.0059182947,0.0023869008,-0.0066661285,0.013483385,-0.01339085,-0.00058136764,-0.0076029743,0.004058933,0.0017556994,-0.0085581215,-0.0016786434,0.012455936,-0.017888797,0.013364039,0.0049290643,0.002049977,0.0006545573,0.013670008,0.007598935,0.002126953,-0.019914696,0.0003156719,-0.0002958752,-0.013048667,-0.0065176263,-0.018300964,-0.0015622947,-0.009359418,0.008473086,0.019088384,-0.021141425,-0.0008242723,0.0051177777,0.012683172,0.009067666,-0.026896745,-0.01112655,0.01306192,0.003023819,0.0014592396,0.000999528,-0.0064804424,-0.04101223,-0.028562943,-0.0011591848,0.0024536306,0.0013620143,-0.013213682,-0.009845796,0.014761598,0.0059393616,0.009492574,0.015854003,-0.004498633,-0.018989956,-0.019607712,0.005323008,-0.032749202,0.0020193418,-0.008040985,-0.011953769,0.015963484,-0.04595471,0.0059957006,0.013185742,-0.019483637,0.0034983952,-0.0021708407,-0.008049515,-0.03876859,0.027059942,0.012272784,-0.009523178,0.0039277477,0.0075956173,0.0008680421,-0.013647632,0.009445033,0.005902827,0.0048287823,0.0030747184,-0.008224967,-0.015738634,-0.010816036,0.008044033,0.014988633,-0.008648228,-0.007939772,0.016993051,-8.300866e-05,0.009870325,-0.008977178,-0.0033051756,-0.008748407,-0.015218051,0.011484986,0.021539923,0.003312432,-0.037262585,-0.01661609,-0.021380318,-0.0012341707,-0.018016756,-0.02058032,-0.014289833,-0.010473414,0.0012410705,0.0013490304,0.010100054,-0.013307773,-0.02123394,0.00620426,-0.017215645,0.0030680392,0.015394062,-0.0126790805,-0.010297067,0.00929788,-0.027126718,-0.016828265,0.016238226,0.022805177,-0.014435185,0.017367125,0.015447872,-0.00019727786,0.022165135,-0.013467611,-0.008166923,-0.032313053,-0.014208188,0.013181872,0.0065771043,-0.015200336,0.000827194,-0.019774955,-0.037962344,0.003180595,-0.013396986,-0.0029506055,-0.0016889382,0.011016844,-0.012986618,-0.029052993,-0.0284679,0.014106605,-0.013308722,-0.0025635823,0.024965422,0.0024496182,0.0042338804,0.010712577,-0.038410004,-0.0073066414,-0.040951386,0.01216239,-0.002091258,0.04187819,-0.020575712,0.036548004,0.0077861724,-0.01679941,0.012064809,0.00548923,0.020021075,0.0024867817,-0.022929115,-0.010944136,-0.017161109,-0.003283695,0.0147197675,-0.007315597,0.0030455962,-0.0061130156,-0.009724367,-0.02917409,-0.0021149754,-0.023069689,0.0009471417,0.022796897,0.0026735975,-0.013233406,0.0008377513,-0.0047113276,0.014431197,-0.0041269218,-0.002179306,0.00196589,-0.0020378102,-0.006618979,0.0048031365,0.004872633,0.016192941,0.0059415037,0.00046332338,-0.004544792,0.032191884,-0.017370991,0.02073735,-0.007347628,-0.0019928208,0.051691163,-0.0083622495,0.0012950841,0.01882171,0.011185188,0.0014190327,-0.02343238,0.026491405,0.0022103419,0.0040414473,0.010272232,0.0015724251,0.00030993554,-0.0046105804,-0.0043222546,0.007725314,-0.011093262,-0.017674888,-0.0032026372,-0.00980962,0.009890315,-0.0005221349,0.026586706,0.018280962,0.030519906,0.003813178,-0.021236885,0.0008837225,-0.015370911,-0.008418586,-0.0031576338,-0.0013673303,-0.0042886236,0.007931398,0.022327457,0.0060456204,0.002833359,-0.008719687,-0.007536566,-0.0057281395,-0.008490248,-0.01716579,-0.02811305,-0.0060324427,0.013628937,0.015158705,-0.0020919472,0.009979185,0.012920305,0.0009993429,-0.025543349,-0.011642694,-0.017232109,-0.008125993,-0.017802585,0.002089252,-0.0017973542,-0.0019847162,0.0063522127,0.009315402,-0.00818318,0.0005036405,0.012433837,0.012610801,-0.036910303,0.015069784,0.017917363,0.001596952,-0.018960968,-0.026522191,-0.0031744572,-0.010874397,0.012861428,0.019606559,0.0028369452,0.17757118,0.12788203,0.03080897,0.0029273855,-0.002719637,0.0055703493,-0.00845688,-0.01361078,-0.016645396,-0.00596075,0.010435209,-0.02454813,-0.003428606,0.006293434,-0.00820304,0.012155666,0.0261512,-0.020509318,-0.007156602,0.0008883049,-0.02365279,0.004927815,0.0075471317,0.0051061367,-0.015058238,-0.0019177116,0.0013603327,-0.020228162,0.0014633836,0.018669844,-0.010531772,0.019286921,-0.015845189,-0.014102826,0.00095311145,-0.02634204,-0.020577572,0.027063377,0.021706639,-0.0066719134,-0.0052942983,0.018932717,0.0016208754,-0.010675534,0.014179636,0.0037711954,0.013211523,-0.006534345,0.007855282,-0.0014959576,0.010766496,-0.0026990233,-0.0055606,0.0048851995,-0.022026721,0.0042895344,0.0079651605,0.0031305128,-0.024128221,0.026373263,-0.0018891677,0.025702553,-0.010710837,0.008446824,-0.017145937,-0.0032034542,-0.0016464184,0.006053991,-0.015716221,0.01746752,0.0044956296,-0.0059222267,-0.009371369,-0.0021136338,-0.0071459864,-0.010295275,-0.008024141,-0.005930236,0.002426981,-0.02175261,-0.013750406,2.9182855e-05,0.005530588,0.016585067,-0.0061719147,0.006250321,-0.013237275,0.021502925,0.07523378,0.009556078,-0.0042534196,-0.020116692,-0.0044298307,-0.013847119,-0.00890389,0.025386669,0.0060888687,0.014977637,0.009369524,0.006698,0.0037420064,-0.0128107825,0.014563776,0.0028931256,0.014947994,0.02352578,0.020381952,0.014597004,-0.013574395,-0.0030780707,0.025069403,0.0042894543,-0.0008541038,-0.0051482203,-0.006840681,0.0030767785,0.0074951313,0.013292142,-0.09418996,-0.0020618003,-0.002569393,0.0014682517,-0.023303377,0.022491852,0.027306154,0.0011328914,0.005505506,0.0008912173,-0.006394318,-0.01871243,0.0024871056,-0.009277565,-0.02115839,0.009983389,0.013643341,0.00096420944,0.01284771,0.026417192,-0.022279227,-0.0074547655,-3.2225278e-05,-0.00029410468,0.017046405,0.027435508,-0.012687307,0.012142355,0.018121108,-0.012004892,-0.0017547848,0.02884301,0.00579244,0.009222968,0.0007874052,0.016371094,0.0008746476,0.014369848,0.02045946,-0.015036974,0.0076585365,-0.02369958,0.0047415723,-0.002443921,0.024881309,-0.0023281246,0.012702635,0.005721701,-0.030891782,0.0039424314,0.039252166,0.0015618725,-0.0056924927,0.003594758,0.0019507067,-0.015573131,-0.0023133773,0.0028550078,-0.016952416,0.0014976467,0.0028589377,0.011652604,0.021219982,0.002445314,0.0010992788,-0.00013917123,0.0019370989,-0.031677954,0.024436777,0.0034372064,-0.024396488,0.002041471,-0.0097793555,-0.01689544,-0.012376353,0.0050445353,-0.01055901,-0.013854256,-0.002754554,0.0227674,-0.01010783,0.007652154,-0.014176957,0.11858899,0.0077645234,0.0013000523,-0.013924084,0.015243963,-0.012113246,0.0009774017,0.022856757,-0.008345881,0.013626969,0.0023036131,0.017018585,-0.0016523866,0.013848935,0.0043601054,-0.016292978,0.01978331,-0.010976021,0.010690492,-0.016467793,-0.006824302,-0.021036373,-0.0074125966,-0.0013110864,0.0034682117,0.011697085,-0.0056052147,-0.0011609286,-0.020533351,-0.03091499,-0.0027978106,-0.0119438395,0.0039566723,-0.0055583664,-0.016282907,0.013261712,-0.008813077,0.0056261094,-0.005206479,-0.0042414656,-0.0031881316,-0.0110033145,0.019878028,0.0087832175,-0.044127963,0.21158476,0.0043198094,0.0012359745,-0.0036082773,0.0024672495,-0.005409074,-0.00034645724,0.0025298258,-0.02393277,0.005916624,0.00022975895,0.01341585,0.0148081845,-0.0024398423,0.008840027,-0.018471839,0.015512107,0.012013205,-0.010197292,0.017401222,0.01736407,0.0032452,0.026315374,0.0022568859,-0.010172317,0.024689002,-0.020498965,-0.0038203087,-0.004203908,0.01934562,-0.0018054511,-0.004025522,-0.0072532133,-0.017450323,-0.010291571,0.01083942,0.0015941652,0.024694642,-0.010613144,-0.015667928,-0.008123552,0.013378927,0.004156903,-0.0017977359,-0.0015510829,-0.0058594877,-0.025293408,-0.0042316695,-0.01995209,0.01151759,0.0011651564,0.009580913,0.00046022356,0.014347002,-0.0060707517,-0.00205641,-0.031159408,0.012081021,0.0092681525,0.0023583493,0.007819047,0.0149227595,0.01940541,-0.0015271024,-0.00054999895,-0.0019892687,-0.011910677]	2026-06-01 07:11:48.909862	2026-06-01 07:11:48.909864
\.


--
-- Data for Name: roadmap_categories; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.roadmap_categories (id, name, icon, description) FROM stdin;
\.


--
-- Data for Name: roadmap_roles; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.roadmap_roles (id, category_id, title, description, level, growth, salary_range, skills) FROM stdin;
\.


--
-- Data for Name: roadmaps; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.roadmaps (id, user_id, target_role, current_level, target_level, skills_to_develop, estimated_duration, status, ai_prompt_version, generation_preferences, created_at, updated_at, current_skills, market_based_salary) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.users (id, first_name, last_name, email, phone, hashed_password, profile_pic_url, is_verified, onboarding_complete, is_assessment_done, totp_secret, totp_enabled, is_first_login, role, industry, job_role, job_type, salary_range, experience, auto_apply_enabled, company_type, company_name, company_location, company_size, preferred_locations, profile_embedding, created_at, updated_at, father_or_mother_name, gender, address, highest_qualification, stream_specialization, college_institute_name, preferred_job_sector, job_roles_offering, specific_requirements, company_address, is_super_admin) FROM stdin;
ac1eee65-7f71-4e5d-b13e-ab390d8f28e4	James	Anderson	james.anderson@example.com	9876500006	$2b$12$Y3050gcRlIiyasOvW85V6OsqvxshSgmAJpLTH5bK6wQ6bWJOTMJyy	\N	t	t	t	\N	f	t	seeker	Marketing	SEO Specialist	in_office	4-6 LPA	2 years	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:49.243176	2026-06-01 07:01:49.243178	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
700e7cd5-e27a-4958-b9f7-7fc7e4a5879f	Shakti	Saini	hr@moonlightautomat.com	9781129037	$2b$12$uX/PRLtICQ.6pJA42l/swuCyQmcvzsO4GDOuiaq3YDHy0/lZoK6ji	\N	t	t	f	TP254RXNPDGJAQZIT4VXLTX4XHYXPKH6	f	t	provider	Manufacturing		\N	\N	\N	f	company	Moonlight Automat pvt ltd 	Ludhiana, Punjab	\N	\N	\N	2026-06-01 05:08:39.472271	2026-06-01 05:23:10.666164	\N	\N	\N	\N	\N	\N	\N	\N	\N	C-177/178 Phase-5, Focal Point ludhiana Punjab 	f
6adffb4d-7db5-4ed5-88c1-2da3b405900b	Samparn	Sahani	samparnsahani@gmail.com	9876114287	$2b$12$/tefBOF2TLVKgfkT2f48ae3gsXOX5D8uCx6itOpGT2/1m2/3nFBF6	\N	t	t	f	ECZ5AXXH6ZOYYHUKGAA7QF5HPUVMEWY2	f	t	provider	Manufacturing		\N	\N	\N	f	company	Mitter Fasteners	Ludhiana, Punjab	\N	\N	\N	2026-06-01 04:49:29.030681	2026-06-01 05:25:05.699121	\N	\N	\N	\N	\N	\N	\N	\N	\N	3184/2, Street No: 14, New Janta Nagar, Gill Road, Ludhiana-141003. (INDIA).	f
7f54007b-199c-4578-8b07-25fb5a068843	Super	Admin	superadmin@hirely.com	9999999999	$2b$12$S28thJfIbDN8GxDQMK.B7uEdUj6GdFY/UY5RoUZsBUde.9czMQpLG	\N	t	t	f	\N	f	t	\N	\N	\N	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	2026-06-01 06:19:23.78305	2026-06-01 06:19:23.783053	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	t
a8f7b4f4-9266-43a3-a57e-21e12f17aeb3	Emily	Davis	emily@innovatex.com	9876543202	$2b$12$1lAZ56BS/.55FyFyGkFxjufiFEwGxevXhtmxT0sZIs2YlAdyg5ahG	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	InnovateX Labs	Hyderabad	200-500	\N	\N	2026-06-01 06:57:54.919746	2026-06-01 06:57:54.919749	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
dc2c24b3-39e5-4dc0-92f9-e1a0a385cab0	David	Wilson	david@nexora.com	9876543203	$2b$12$D3f3TI1p1fdmmiCFBh9Sqe8V9G4sJEtL21CwlNhxtvHiNnLYBGj4q	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	Nexora Systems	Pune	50-200	\N	\N	2026-06-01 06:57:55.152714	2026-06-01 06:57:55.152717	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
af23ac13-54f8-4f6f-a0f5-b727a6f67e94	Sarah	Brown	sarah@cloudpeak.com	9876543204	$2b$12$OKhDGHBuw3AjXgdIPw5ceeQFfuJrf0YtawLCee2QlqHiLqJlt9jvq	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	CloudPeak Technologies	Mumbai	500-1000	\N	\N	2026-06-01 06:57:55.37912	2026-06-01 06:57:55.379123	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
23c60853-194d-4b42-bdb5-2af4b30b1a6e	James	Taylor	james@vertexcorp.com	9876543205	$2b$12$RuKUMXY4JHm2npO6rXNVouTUxXIqhf6wA0GAtBa0sC5bEEcMqbJpK	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	Vertex Corp	Delhi	200-500	\N	\N	2026-06-01 06:57:55.59885	2026-06-01 06:57:55.598853	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
e3f96d99-f4b1-4719-bb4e-02eae4ea5bf0	Olivia	Anderson	olivia@brightpath.com	9876543206	$2b$12$xbZfIQrOZdtqFz/A4gj9p.Fej6NEkn55XtgZTp2FHc1yiwXscC.z2	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	BrightPath Ventures	Chennai	50-200	\N	\N	2026-06-01 06:57:55.826203	2026-06-01 06:57:55.826206	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
8c824fbc-b71f-4165-8d6f-96d53d8b8759	Daniel	Thomas	daniel@codefusion.com	9876543207	$2b$12$lbTxk.YKOqFhJ2qGXjQaj.wf2s2HO1.SgE7FI/9meyBqolJSBNRV6	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	CodeFusion Pvt Ltd	Noida	50-200	\N	\N	2026-06-01 06:57:56.056544	2026-06-01 06:57:56.056546	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
c61657d4-da8d-4500-83c8-4cb6abe8a054	Sophia	Martin	sophia@futuregrid.com	9876543208	$2b$12$CMVRIHaqYpZuzFaKI9Y8xOsyfeTMw.oN.xymmD/87WH/ugYh6Nd2m	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	FutureGrid Solutions	Gurgaon	200-500	\N	\N	2026-06-01 06:57:56.274987	2026-06-01 06:57:56.27499	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
d1c5c760-11cf-49d1-bc91-7a6b0feb4b77	Matthew	Lee	matthew@skylineit.com	9876543209	$2b$12$rl44XNNyR8oXCZ7Mz9YNser/9TRB2NSVlPZX/udG0XhkA3vhGqywi	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	Skyline IT	Ahmedabad	50-200	\N	\N	2026-06-01 06:57:56.497823	2026-06-01 06:57:56.497826	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
a1ff5365-a785-43d0-9a53-41dcc7bae266	Ava	White	ava@alphaworks.com	9876543210	$2b$12$ZPW2hTC6XXwH506Pp0Ygq.GFpqFA1uz4oUEGE/6nbiYQu/eNjGana	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	AlphaWorks	Kolkata	200-500	\N	\N	2026-06-01 06:57:56.722415	2026-06-01 06:57:56.722417	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
dd58cd20-d234-4bad-b2cd-7660e9d2faf1	Christopher	Harris	chris@bytebridge.com	9876543211	$2b$12$LUNyXN.WHYe74.2x3ToIeOm.0g3GVybQswSJEnWwtHaccF07n0Bkm	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	ByteBridge Technologies	Jaipur	50-200	\N	\N	2026-06-01 06:57:56.943995	2026-06-01 06:57:56.943998	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
61d9b2f0-abe6-4a92-be22-0cfe90c9f1e4	Mia	Clark	mia@quantumedge.com	9876543212	$2b$12$EREfYoBKu/k8a/wL0pexseK2EnbkyEsff.DsoOFvjO5f85JrjArPK	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	QuantumEdge	Indore	50-200	\N	\N	2026-06-01 06:57:57.1673	2026-06-01 06:57:57.167302	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
4261e589-8abe-4db0-a955-1abc76211f7b	Andrew	Lewis	andrew@zenithsoft.com	9876543213	$2b$12$1Km3RT20YUMu3.OCRHpmTekRbc1vgHqwco3Acd.zSgJ2rFS6NzCja	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	ZenithSoft	Lucknow	200-500	\N	\N	2026-06-01 06:57:57.393455	2026-06-01 06:57:57.393458	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
30d8c32e-5489-4083-9d79-fe5e6a65ad10	Olivia	Thomas	olivia.thomas@example.com	9876500007	$2b$12$gkx9nENxOv4rJjCeeDgjH.ICoymXjUbylh2uMQNNrHdkjWOLULa62	\N	t	t	t	\N	f	t	seeker	IT	QA Engineer	hybrid	4-7 LPA	2 years	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:49.46682	2026-06-01 07:01:49.466822	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
bf0d6e8a-ed76-406b-a2be-369a695db93d	Charlotte	Walker	charlotte@infiniteloop.com	9876543214	$2b$12$0SbhHluQLhCMdGgkie9JaOUzMVEJhjVGdGz0h7rFPA0rwsI4yR1ui	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	Infinite Loop Systems	Kochi	50-200	\N	\N	2026-06-01 06:57:57.614296	2026-06-01 06:57:57.614299	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
4f450d6e-2158-4b61-ac74-a67af1394f81	Daniel	Jackson	daniel.jackson@example.com	9876500008	$2b$12$t68WmyjTZP.ezWqXvye.NO3TxjUyGQHtyOR1U/.GGtnXJLqyMjuX.	\N	t	t	t	\N	f	t	seeker	Education	Trainer	in_office	3-5 LPA	1 year	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:49.694208	2026-06-01 07:01:49.69421	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
1f709b73-210e-4902-9334-b0e400cbfd60	Joseph	Hall	joseph@visionarytech.com	9876543215	$2b$12$DdXrAjSLAm9vWqdUwQRbbueRg87ltfpy.5l7UWUj0gNgpJ/jugTIa	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	Visionary Tech	Chandigarh	50-200	\N	\N	2026-06-01 06:57:57.837856	2026-06-01 06:57:57.837858	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
90c8359d-e264-456c-a0e8-5ad85082f5bd	Amelia	Allen	amelia@primecore.com	9876543216	$2b$12$IX66RYaL4F9W3CougiYK5uW4czDgyLIeNeXMNzPTKPwINetKdYFF6	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	PrimeCore Solutions	Surat	200-500	\N	\N	2026-06-01 06:57:58.053192	2026-06-01 06:57:58.053194	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
60611cfc-0c57-4adb-9636-c3f2282d6f20	Benjamin	Young	ben@digitalnest.com	9876543217	$2b$12$BlYicYSYDNozdWSKbJObFeUOzwESFNynISrOqpybn18EkuE/8PUkC	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	DigitalNest	Nagpur	50-200	\N	\N	2026-06-01 06:57:58.275118	2026-06-01 06:57:58.27512	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
a04b2ad7-9035-4a9f-890f-a1e5953425e6	Harper	King	harper@elevatecorp.com	9876543218	$2b$12$U8tN8u1rGACn0uiR9wOm3.wrfCuMIZ4BvgyWOk6R4DdCYOPqukX1q	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	Elevate Corp	Bhopal	50-200	\N	\N	2026-06-01 06:57:58.500704	2026-06-01 06:57:58.500711	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
33f28bbe-5989-4b6b-ae7d-808b674ad4a2	Lucas	Wright	lucas@smartwave.com	9876543219	$2b$12$hisCMS16m.NOKOSVT4mZYeByVAEDZWTRsvqy5RRHOTDKdZBhZnXcG	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	SmartWave Technologies	Patna	200-500	\N	\N	2026-06-01 06:57:58.722613	2026-06-01 06:57:58.722615	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
b6f57992-66ea-4d9d-b944-188a76d1eda4	Evelyn	Scott	evelyn@nextgenlabs.com	9876543220	$2b$12$O50nP3YUo7cBP77Q/dmdMOyJLGCWJRZcYFndUSO3hp5aQ/Nj.GUEC	\N	t	t	f	\N	f	t	provider	\N	\N	\N	\N	\N	f	company	NextGen Labs	Coimbatore	50-200	\N	\N	2026-06-01 06:57:58.936293	2026-06-01 06:57:58.936295	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
7cafedbb-8887-46d4-ada6-557084d6caae	Alice	Johnson	alice.johnson@example.com	9876500001	$2b$12$e71eKijRmG/Pmoyc3xH6W.Gu9rr1HeSdOoH1J8GK0lyuzwAHJG.Fa	\N	t	t	t	\N	f	t	seeker	IT	Frontend Developer	in_office	4-6 LPA	2 years	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:48.128391	2026-06-01 07:01:48.128394	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
d668d557-b424-4392-8dd5-b30597d01baa	Emma	Brown	emma.brown@example.com	9876500003	$2b$12$5ZoDQGLfdVBCfRx/yvp2xORWALglv5jNJMCuXmAYMqwtXDFagmSTG	\N	t	t	t	\N	f	t	seeker	Finance	Accountant	in_office	3-5 LPA	1 year	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:48.569671	2026-06-01 07:01:48.569678	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
0d3b007e-20cd-4839-92ed-af3965a26d6b	David	Wilson	david.wilson@example.com	9876500004	$2b$12$RdtN/Bd4Hp855nwwq7QfFOh51uZeiPBifRhKOjCZloDbx/3Aa8x5q	\N	t	t	t	\N	f	t	seeker	Healthcare	Data Analyst	hybrid	5-7 LPA	2 years	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:48.793934	2026-06-01 07:01:48.793936	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
a14be692-30d2-4d86-a240-79dad0934e61	William	Harris	william.harris@example.com	9876500010	$2b$12$8MVilKiH6vjbJMNymYneYuWcPOzJoSHAXqH/j5U7mFFe6wBRxEZYW	\N	t	t	t	\N	f	t	seeker	Logistics	Operations Executive	in_office	4-6 LPA	2 years	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:50.137936	2026-06-01 07:01:50.137939	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
f57a67fb-84bf-4f2d-9656-9d98a19420d6	Mia	Martin	mia.martin@example.com	9876500011	$2b$12$nNiWBTLYteljvNMATkAZI.NjjMRj3T.czWutFwYeAT5rF1P6Lnke6	\N	t	t	t	\N	f	t	seeker	IT	DevOps Engineer	hybrid	7-10 LPA	4 years	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:50.361359	2026-06-01 07:01:50.361362	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
06ab38f2-4d3e-465e-89ee-9c9070c6d68d	Benjamin	Thompson	ben.thompson@example.com	9876500012	$2b$12$j.0IslzEPfBt8iqbeVU36.0FmBjBdourvjuT70ySD7rN/yfbB3Yo6	\N	t	t	t	\N	f	t	seeker	Retail	Store Manager	in_office	5-7 LPA	3 years	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:50.579112	2026-06-01 07:01:50.579115	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
4581d471-5eec-41e3-8df2-fc2d9a47ef99	Lucas	Martinez	lucas.martinez@example.com	9876500014	$2b$12$rwAjT4mdOj3zbSUESb8FB.Sa/oDJzJp0IEE8gK0Ya98pQhsGEMSui	\N	t	t	t	\N	f	t	seeker	Manufacturing	Production Engineer	in_office	5-8 LPA	3 years	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:51.02502	2026-06-01 07:01:51.025023	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
ce803b50-9ad2-4a14-91ff-9239c942bde1	Amelia	Robinson	amelia.robinson@example.com	9876500015	$2b$12$5e7Hc6xK4cEc1CFWRqadvOScA91U28eUceGKRaQz8tB/sIb0mrgwa	\N	t	t	t	\N	f	t	seeker	IT	Project Coordinator	hybrid	5-7 LPA	2 years	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:51.248116	2026-06-01 07:01:51.248118	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
4f008593-1273-4f6c-8e1e-0aa1ad43a90b	Evelyn	Rodriguez	evelyn.rodriguez@example.com	9876500017	$2b$12$sgVoRWRrRp0R6Uw4mncb..3AFtNBSGuLsw3zYp59bvymTpXfKt/I2	\N	t	t	t	\N	f	t	seeker	IT	Mobile App Developer	in_office	6-9 LPA	3 years	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:51.707899	2026-06-01 07:01:51.707902	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
45c9e317-f26b-4e86-8aca-9d62c7ebd51e	Alexander	Lewis	alex.lewis@example.com	9876500018	$2b$12$Tj74gS4o7qrjh05PyIKEXuq.XK/sYhfpO3t.WGCMKiiuXrKgsZO1u	\N	t	t	t	\N	f	t	seeker	Healthcare	System Administrator	hybrid	5-8 LPA	3 years	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:51.932006	2026-06-01 07:01:51.932009	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
54540bb4-7e91-4a36-bb84-e91d8d882066	Jacob	Walker	jacob.walker@example.com	9876500020	$2b$12$82Ms3FnEZPsId10unuJP7.o6yakjJWMLE2WDlwWKUO.RXKs7ov5D6	\N	t	t	t	\N	f	t	seeker	IT	Cloud Engineer	hybrid	8-12 LPA	5 years	f	\N	\N	\N	\N	\N	\N	2026-06-01 07:01:52.379285	2026-06-01 07:01:52.37929	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f
abcf2d6b-b1e9-4a83-a2f0-5443768ef727	Michael	Johnson	michael@techsphere.com	9876543201	$2b$12$qZJpRV.x6JYGM/54637WGebdTdG.QrhPKiTSK5jcO8Hy5wzSCdXSm	\N	t	t	f	\N	f	t	provider	Information Technology		\N	\N	\N	f	company	TechSphere Solutions	Bangalore, Karnataka	50-200	\N	\N	2026-06-01 06:57:54.668884	2026-06-01 07:35:57.323146	\N	\N	\N	\N	\N	\N	\N	\N	\N	REGD OFFICE-D141/142, PH V FOCAL POINT LUDHIANA PB	f
\.


--
-- Name: master_cities_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jobmatch
--

SELECT pg_catalog.setval('public.master_cities_id_seq', 234, true);


--
-- Name: master_industries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jobmatch
--

SELECT pg_catalog.setval('public.master_industries_id_seq', 114, true);


--
-- Name: master_languages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jobmatch
--

SELECT pg_catalog.setval('public.master_languages_id_seq', 46, true);


--
-- Name: master_roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jobmatch
--

SELECT pg_catalog.setval('public.master_roles_id_seq', 684, true);


--
-- Name: master_states_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jobmatch
--

SELECT pg_catalog.setval('public.master_states_id_seq', 38, true);


--
-- Name: ai_coach_sessions ai_coach_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.ai_coach_sessions
    ADD CONSTRAINT ai_coach_sessions_pkey PRIMARY KEY (id);


--
-- Name: ai_interview_sessions ai_interview_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.ai_interview_sessions
    ADD CONSTRAINT ai_interview_sessions_pkey PRIMARY KEY (id);


--
-- Name: applications applications_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_pkey PRIMARY KEY (id);


--
-- Name: assessment_results assessment_results_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT assessment_results_pkey PRIMARY KEY (id);


--
-- Name: assessment_results assessment_results_session_id_key; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT assessment_results_session_id_key UNIQUE (session_id);


--
-- Name: assessment_sessions assessment_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.assessment_sessions
    ADD CONSTRAINT assessment_sessions_pkey PRIMARY KEY (id);


--
-- Name: department_jobs department_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.department_jobs
    ADD CONSTRAINT department_jobs_pkey PRIMARY KEY (id);


--
-- Name: departments departments_name_key; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_name_key UNIQUE (name);


--
-- Name: departments departments_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_pkey PRIMARY KEY (id);


--
-- Name: external_candidate_matches external_candidate_matches_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.external_candidate_matches
    ADD CONSTRAINT external_candidate_matches_pkey PRIMARY KEY (id);


--
-- Name: external_candidates external_candidates_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.external_candidates
    ADD CONSTRAINT external_candidates_pkey PRIMARY KEY (id);


--
-- Name: imported_user_passwords imported_user_passwords_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.imported_user_passwords
    ADD CONSTRAINT imported_user_passwords_pkey PRIMARY KEY (id);


--
-- Name: imported_user_passwords imported_user_passwords_user_id_key; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.imported_user_passwords
    ADD CONSTRAINT imported_user_passwords_user_id_key UNIQUE (user_id);


--
-- Name: interviews interviews_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.interviews
    ADD CONSTRAINT interviews_pkey PRIMARY KEY (id);


--
-- Name: job_postings job_postings_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.job_postings
    ADD CONSTRAINT job_postings_pkey PRIMARY KEY (id);


--
-- Name: master_cities master_cities_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.master_cities
    ADD CONSTRAINT master_cities_pkey PRIMARY KEY (id);


--
-- Name: master_industries master_industries_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.master_industries
    ADD CONSTRAINT master_industries_pkey PRIMARY KEY (id);


--
-- Name: master_languages master_languages_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.master_languages
    ADD CONSTRAINT master_languages_pkey PRIMARY KEY (id);


--
-- Name: master_roles master_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.master_roles
    ADD CONSTRAINT master_roles_pkey PRIMARY KEY (id);


--
-- Name: master_states master_states_code_key; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.master_states
    ADD CONSTRAINT master_states_code_key UNIQUE (code);


--
-- Name: master_states master_states_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.master_states
    ADD CONSTRAINT master_states_pkey PRIMARY KEY (id);


--
-- Name: matches matches_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_pkey PRIMARY KEY (id);


--
-- Name: milestones milestones_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.milestones
    ADD CONSTRAINT milestones_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: otp_records otp_records_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.otp_records
    ADD CONSTRAINT otp_records_pkey PRIMARY KEY (id);


--
-- Name: portfolios portfolios_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.portfolios
    ADD CONSTRAINT portfolios_pkey PRIMARY KEY (id);


--
-- Name: provider_availability_windows provider_availability_windows_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.provider_availability_windows
    ADD CONSTRAINT provider_availability_windows_pkey PRIMARY KEY (id);


--
-- Name: provider_interview_settings provider_interview_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.provider_interview_settings
    ADD CONSTRAINT provider_interview_settings_pkey PRIMARY KEY (provider_id);


--
-- Name: resources resources_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.resources
    ADD CONSTRAINT resources_pkey PRIMARY KEY (id);


--
-- Name: resumes resumes_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.resumes
    ADD CONSTRAINT resumes_pkey PRIMARY KEY (id);


--
-- Name: roadmap_categories roadmap_categories_name_key; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.roadmap_categories
    ADD CONSTRAINT roadmap_categories_name_key UNIQUE (name);


--
-- Name: roadmap_categories roadmap_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.roadmap_categories
    ADD CONSTRAINT roadmap_categories_pkey PRIMARY KEY (id);


--
-- Name: roadmap_roles roadmap_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.roadmap_roles
    ADD CONSTRAINT roadmap_roles_pkey PRIMARY KEY (id);


--
-- Name: roadmaps roadmaps_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.roadmaps
    ADD CONSTRAINT roadmaps_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_provider_availability_provider; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX idx_provider_availability_provider ON public.provider_availability_windows USING btree (provider_id);


--
-- Name: ix_ai_coach_sessions_seeker_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_ai_coach_sessions_seeker_id ON public.ai_coach_sessions USING btree (seeker_id);


--
-- Name: ix_ai_interview_sessions_application_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_ai_interview_sessions_application_id ON public.ai_interview_sessions USING btree (application_id);


--
-- Name: ix_ai_interview_sessions_job_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_ai_interview_sessions_job_id ON public.ai_interview_sessions USING btree (job_id);


--
-- Name: ix_ai_interview_sessions_seeker_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_ai_interview_sessions_seeker_id ON public.ai_interview_sessions USING btree (seeker_id);


--
-- Name: ix_applications_job_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_applications_job_id ON public.applications USING btree (job_id);


--
-- Name: ix_applications_seeker_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_applications_seeker_id ON public.applications USING btree (seeker_id);


--
-- Name: ix_assessment_results_user_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_assessment_results_user_id ON public.assessment_results USING btree (user_id);


--
-- Name: ix_external_candidate_matches_candidate_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_external_candidate_matches_candidate_id ON public.external_candidate_matches USING btree (candidate_id);


--
-- Name: ix_external_candidate_matches_job_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_external_candidate_matches_job_id ON public.external_candidate_matches USING btree (job_id);


--
-- Name: ix_external_candidates_email; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_external_candidates_email ON public.external_candidates USING btree (email);


--
-- Name: ix_external_candidates_job_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_external_candidates_job_id ON public.external_candidates USING btree (job_id);


--
-- Name: ix_imported_user_passwords_email; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_imported_user_passwords_email ON public.imported_user_passwords USING btree (email);


--
-- Name: ix_interviews_job_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_interviews_job_id ON public.interviews USING btree (job_id);


--
-- Name: ix_interviews_provider_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_interviews_provider_id ON public.interviews USING btree (provider_id);


--
-- Name: ix_interviews_seeker_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_interviews_seeker_id ON public.interviews USING btree (seeker_id);


--
-- Name: ix_job_postings_provider_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_job_postings_provider_id ON public.job_postings USING btree (provider_id);


--
-- Name: ix_master_cities_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_master_cities_id ON public.master_cities USING btree (id);


--
-- Name: ix_master_cities_name; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_master_cities_name ON public.master_cities USING btree (name);


--
-- Name: ix_master_industries_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_master_industries_id ON public.master_industries USING btree (id);


--
-- Name: ix_master_industries_name; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE UNIQUE INDEX ix_master_industries_name ON public.master_industries USING btree (name);


--
-- Name: ix_master_languages_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_master_languages_id ON public.master_languages USING btree (id);


--
-- Name: ix_master_languages_name; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE UNIQUE INDEX ix_master_languages_name ON public.master_languages USING btree (name);


--
-- Name: ix_master_roles_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_master_roles_id ON public.master_roles USING btree (id);


--
-- Name: ix_master_roles_name_industry; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE UNIQUE INDEX ix_master_roles_name_industry ON public.master_roles USING btree (name, industry_id);


--
-- Name: ix_master_states_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_master_states_id ON public.master_states USING btree (id);


--
-- Name: ix_master_states_name; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE UNIQUE INDEX ix_master_states_name ON public.master_states USING btree (name);


--
-- Name: ix_matches_job_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_matches_job_id ON public.matches USING btree (job_id);


--
-- Name: ix_matches_seeker_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_matches_seeker_id ON public.matches USING btree (seeker_id);


--
-- Name: ix_milestones_roadmap_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_milestones_roadmap_id ON public.milestones USING btree (roadmap_id);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


--
-- Name: ix_otp_records_email; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_otp_records_email ON public.otp_records USING btree (email);


--
-- Name: ix_otp_records_phone; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_otp_records_phone ON public.otp_records USING btree (phone);


--
-- Name: ix_portfolios_user_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE UNIQUE INDEX ix_portfolios_user_id ON public.portfolios USING btree (user_id);


--
-- Name: ix_provider_availability_windows_provider_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_provider_availability_windows_provider_id ON public.provider_availability_windows USING btree (provider_id);


--
-- Name: ix_resources_milestone_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_resources_milestone_id ON public.resources USING btree (milestone_id);


--
-- Name: ix_resumes_user_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_resumes_user_id ON public.resumes USING btree (user_id);


--
-- Name: ix_roadmaps_user_id; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE INDEX ix_roadmaps_user_id ON public.roadmaps USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: jobmatch
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ai_coach_sessions ai_coach_sessions_seeker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.ai_coach_sessions
    ADD CONSTRAINT ai_coach_sessions_seeker_id_fkey FOREIGN KEY (seeker_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: ai_interview_sessions ai_interview_sessions_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.ai_interview_sessions
    ADD CONSTRAINT ai_interview_sessions_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- Name: ai_interview_sessions ai_interview_sessions_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.ai_interview_sessions
    ADD CONSTRAINT ai_interview_sessions_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job_postings(id) ON DELETE CASCADE;


--
-- Name: ai_interview_sessions ai_interview_sessions_seeker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.ai_interview_sessions
    ADD CONSTRAINT ai_interview_sessions_seeker_id_fkey FOREIGN KEY (seeker_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: applications applications_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job_postings(id) ON DELETE CASCADE;


--
-- Name: applications applications_seeker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_seeker_id_fkey FOREIGN KEY (seeker_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: assessment_results assessment_results_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT assessment_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.assessment_sessions(id) ON DELETE CASCADE;


--
-- Name: assessment_results assessment_results_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT assessment_results_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: department_jobs department_jobs_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.department_jobs
    ADD CONSTRAINT department_jobs_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id) ON DELETE CASCADE;


--
-- Name: external_candidate_matches external_candidate_matches_candidate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.external_candidate_matches
    ADD CONSTRAINT external_candidate_matches_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.external_candidates(id) ON DELETE CASCADE;


--
-- Name: external_candidate_matches external_candidate_matches_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.external_candidate_matches
    ADD CONSTRAINT external_candidate_matches_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job_postings(id) ON DELETE CASCADE;


--
-- Name: external_candidates external_candidates_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.external_candidates
    ADD CONSTRAINT external_candidates_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job_postings(id) ON DELETE SET NULL;


--
-- Name: imported_user_passwords imported_user_passwords_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.imported_user_passwords
    ADD CONSTRAINT imported_user_passwords_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: interviews interviews_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.interviews
    ADD CONSTRAINT interviews_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job_postings(id) ON DELETE CASCADE;


--
-- Name: interviews interviews_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.interviews
    ADD CONSTRAINT interviews_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: interviews interviews_seeker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.interviews
    ADD CONSTRAINT interviews_seeker_id_fkey FOREIGN KEY (seeker_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: job_postings job_postings_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.job_postings
    ADD CONSTRAINT job_postings_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: master_cities master_cities_state_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.master_cities
    ADD CONSTRAINT master_cities_state_id_fkey FOREIGN KEY (state_id) REFERENCES public.master_states(id) ON DELETE CASCADE;


--
-- Name: matches matches_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job_postings(id) ON DELETE CASCADE;


--
-- Name: matches matches_seeker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_seeker_id_fkey FOREIGN KEY (seeker_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: milestones milestones_roadmap_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.milestones
    ADD CONSTRAINT milestones_roadmap_id_fkey FOREIGN KEY (roadmap_id) REFERENCES public.roadmaps(id);


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: portfolios portfolios_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.portfolios
    ADD CONSTRAINT portfolios_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: provider_availability_windows provider_availability_windows_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.provider_availability_windows
    ADD CONSTRAINT provider_availability_windows_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.provider_interview_settings(provider_id) ON DELETE CASCADE;


--
-- Name: provider_interview_settings provider_interview_settings_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.provider_interview_settings
    ADD CONSTRAINT provider_interview_settings_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: resources resources_milestone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.resources
    ADD CONSTRAINT resources_milestone_id_fkey FOREIGN KEY (milestone_id) REFERENCES public.milestones(id);


--
-- Name: resumes resumes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.resumes
    ADD CONSTRAINT resumes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: roadmap_roles roadmap_roles_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.roadmap_roles
    ADD CONSTRAINT roadmap_roles_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.roadmap_categories(id);


--
-- Name: roadmaps roadmaps_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jobmatch
--

ALTER TABLE ONLY public.roadmaps
    ADD CONSTRAINT roadmaps_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

