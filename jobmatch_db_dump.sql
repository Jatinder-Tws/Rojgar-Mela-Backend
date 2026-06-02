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
    updated_at timestamp without time zone NOT NULL
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
ba2f4101-04ad-44ed-ba39-a6a627bfd24a	\N	Dhiraj sharma	dhirajsharma@gmail.com	9876543987	Punjab	Ludhiana	Software Development	Software Engineer	["IT / SaaS", "HealthCare", "Supply Chain"]	Day Shift	Fresher	200000	LinkedIn	Designs, develops, and maintains responsive web applications that deliver seamless user experiences.\nBuilds scalable, secure, and high-performance web solutions using modern technologies and best practices.\nTransforms business requirements into functional, user-friendly web applications and digital experiences.\nCreates dynamic websites and web platforms that enhance engagement, accessibility, and performance.	/resumes/guest_88c42fc2/7fb5a4c79cf848fe8c932cd80fe78e57.docx				rejected	2026-05-30 06:54:07.791243	2026-05-30 06:58:34.913975	[0.001500441,0.0008484763,0.0033614603,-0.048655458,-0.017198885,0.042969596,0.016049782,-0.020037781,-0.0274863,-0.0018381029,-0.02875612,-0.013760066,-0.0071221273,0.03816135,0.11872408,8.053743e-06,0.015189367,0.014782413,0.011480076,0.0042335405,-0.0011662778,0.013238703,0.009488727,-0.030735165,-0.008320131,-0.009092428,0.017115412,0.009497942,0.041800816,-0.008901508,-0.009817036,-0.0147989495,-0.020090984,0.019323036,0.0018912479,-0.011301181,0.034982804,-0.013905844,-0.003811476,0.00984533,-0.004644379,0.009815209,-0.015293473,0.0022131086,-0.0255367,-0.0054021026,0.0043304325,0.015014318,0.0012928989,0.0103075765,-0.021017967,-0.0014186843,-0.043763895,-0.17993829,-0.005732209,0.0021501556,-0.00023226201,-0.026828744,0.02868859,-0.008786948,0.00866572,0.026867062,-0.025151437,0.016394606,-0.00637882,-0.019986505,0.028345054,-0.0012647725,-0.013596371,0.004464966,-0.0031832578,-0.019716596,-0.023486478,-0.017285468,0.0071937293,-0.0007216263,-0.037542637,0.011747495,-0.0010185016,0.0043171993,-0.010007243,0.0034144884,0.0023665011,-0.0063448483,-0.0012665932,-0.029902592,-0.0016274819,-0.013589646,0.028978296,-0.009766767,0.014606341,0.01712067,0.008893365,0.024929425,-0.009396072,-0.007468127,-0.005703909,0.007593865,0.024836734,-0.014037837,0.008602581,0.0060679084,0.011201768,0.016920535,0.021560574,0.0124012,0.024892822,-0.04095276,-0.024329992,0.0053567225,0.006118252,-0.0038677684,-0.0060005398,0.024084494,0.015498997,-0.15833682,0.015920684,0.009201231,-0.006796653,-0.013043529,0.004288124,0.015228118,0.0001250121,0.024876378,-0.016384842,-0.011928992,0.025586188,0.004807717,0.022780618,0.004949165,-0.02878057,-0.01786579,0.041378457,-0.011920407,0.010146455,0.0111551285,0.0057165823,-0.002979911,-0.020789256,-0.022251198,-0.016672235,0.035764646,0.0037590968,-0.0068790456,-0.04070325,-0.007164142,-0.0071806703,-0.0040514846,-0.01602003,-0.018217562,0.0061275954,-0.004201399,-0.00467345,0.000470473,0.01450427,-0.010815297,0.018066341,0.02462463,-0.00861119,-0.011470269,-0.027705077,0.003976766,0.034436464,0.007656673,-0.010229238,-0.009534534,-0.025689524,0.009046942,0.027073901,0.012587083,-0.00593674,-0.007748206,-0.011204494,0.006847655,-0.006481906,-0.027071182,-0.00039201093,0.017828252,0.00076326984,-0.040935367,0.004828003,-0.01176774,-0.0037442239,0.0046707317,0.004510733,-0.014551868,-0.013265013,-0.014110097,0.012585731,0.0013415182,-0.0007259671,-0.02394942,-0.017022721,0.009870222,0.011876335,-0.041626763,0.01713165,-0.019423956,0.0031752712,0.0042400556,0.0006907004,0.0046111243,0.0039478946,-0.0022372773,0.0072610127,-0.00052422285,-0.012927718,0.0067986324,-0.00861317,-0.006313595,-0.007904633,-0.011186056,0.056671787,-0.00029253538,-0.0048130536,-0.0120043745,0.0057777925,0.0024818718,-0.008370233,-0.009575653,0.011410794,-0.017332206,0.0077485223,-0.0027717056,0.0008331963,0.011383691,-0.0015586097,0.016210532,0.010334681,-0.011817897,0.0023263798,-0.0015763938,0.0028424822,0.012728597,0.021004338,-0.020356141,0.006573172,-0.012301182,0.0116605675,0.015014617,0.005939536,-0.003931295,-0.019173816,0.0240448,0.053852357,0.026572056,-0.013906501,-0.01123417,0.010569258,-0.020634124,-0.0023475352,-0.026801197,-0.0044757565,-0.00023746157,0.00021347856,-0.017816005,-0.0016479125,-0.009130459,0.0028548164,0.013687851,-0.00032511025,0.0040008803,-0.030878406,-0.0045042033,-0.013094167,-0.0012353391,0.015575761,0.025242794,-0.010738364,-0.0007198143,0.005765596,0.0148279425,0.03360433,-0.008922538,-0.011495852,-0.012700284,-0.042512987,0.009704839,-0.02393371,-0.032204162,0.008699148,-0.016871927,-0.009546905,-0.011766569,-0.004667945,0.022391899,-0.0047425884,-0.03258363,-0.011236238,0.022789111,-0.013712433,-0.019395601,-0.0141370995,-0.005327258,0.014057468,-0.016627545,-0.009250435,-0.025903849,0.009990823,-0.0010668506,-0.0068739853,-0.019375855,0.034503307,0.03786547,0.01315667,-0.0006542232,0.017521927,0.037336204,0.0031421608,-0.011521131,-0.009373868,0.0040675234,-0.0043358724,-0.0035508368,-0.0019478609,-0.015803572,0.02294389,0.0051844604,-0.024540216,0.010350802,0.0024517626,0.0006651042,0.020756744,0.009963265,0.008599158,0.011684732,-0.013960618,0.030440027,0.01435992,-0.031451862,-0.0007101659,0.012485779,-0.008280508,-0.0028160093,0.0010662671,0.016522955,0.04408334,-0.005319973,0.007191151,0.0029702128,0.0037039416,-0.017469738,0.009978197,-0.015661104,0.023229035,-0.010219428,-0.02344806,-0.023431737,0.019106567,-0.030082818,0.00068606046,0.013165352,-0.028636599,-0.021593172,-0.014281567,0.008882171,-0.004656341,-0.0032124599,-0.0024967606,0.024925455,-0.018716555,0.0036994426,-0.013969836,0.013107071,0.00012992177,0.01349534,-0.02123709,0.008075483,-0.029194413,-0.00685073,-0.014474251,0.02813012,0.004431014,-0.019536505,0.027106907,0.017196232,-0.03742373,0.02041482,-0.008501626,-0.002736034,-0.018511184,-0.008726205,0.0073454943,0.016348802,0.0007148371,0.014343341,0.020088121,0.014488734,0.0046266206,0.0025809524,-0.0031146172,-0.0043681418,0.019285677,0.024583353,-0.01458158,-0.0045377864,0.0017802677,-0.003125775,-0.03313638,0.0041642617,-0.028198432,0.011187039,-0.02633621,-0.0068335477,0.008508885,0.027304558,-0.0027004657,0.008042568,0.0070373924,0.014295039,0.015329252,-0.014278388,0.02121563,0.0006394752,-0.0044529308,0.0028157267,-0.0030795361,0.017153675,0.0073365686,-0.009530106,-0.012220818,0.014479787,-0.012642393,-0.0070185275,-0.018063698,0.010918351,-0.025790805,-0.004706009,4.8700582e-05,0.007129628,-0.0012629705,0.0023138637,0.0046340693,-0.016331602,-0.023151323,-0.016845526,-0.009708935,-0.021010049,0.001751445,0.0033213606,-0.0100259585,-0.003092651,0.019974884,-0.028401123,0.016406938,0.00018762966,-0.020794585,-0.037015088,-0.01684135,0.025258143,-0.0048894207,0.027194908,0.010286252,-0.0029039104,0.019581484,0.023258878,-0.013281913,-0.0010341576,-0.02542441,-0.015816102,-0.015071541,0.009710552,-0.009866868,0.004068727,-0.0013144573,-0.017263515,0.024693934,0.011969134,-0.028500367,0.033516012,-0.01034884,0.0074936287,-0.015633352,-0.027742846,-0.007975259,0.0021571605,0.033451848,-0.011478037,0.0024552613,0.0063768723,0.030250767,0.027736265,-0.02870514,0.005120759,0.007978221,0.012026325,-0.020679954,0.005461704,0.00994794,0.0061653582,0.018449193,0.048674606,0.0043149535,-0.03043944,-0.026867481,0.004271595,0.01751967,-0.012364443,-0.004691517,0.001761478,-0.009161146,-0.009251755,0.0047859633,0.030589756,0.01985408,0.010139439,0.019039383,-0.037426,0.0087644495,0.009668449,0.00070115813,-0.019939084,0.0147570595,-0.003530797,-0.001364297,0.0027338562,-0.019919164,-0.004641788,0.0286095,0.0031415331,-0.007933553,-0.0018548775,-0.024629012,0.003912837,-0.009533278,0.0035300967,0.031900488,0.019789582,0.029745659,0.03194454,-0.005835266,0.033823,0.019306103,0.0106738275,-0.04030507,0.004799186,-0.0022812556,0.011032692,0.026117735,0.025314137,-0.0020891756,-0.026642878,-0.023676725,-0.0029377674,-0.014963731,-0.053291578,0.0061872914,-0.012952054,0.0051635285,-0.0029521878,0.01879142,0.018494032,-0.012951377,0.0027728449,-0.009701086,-0.002811685,-0.034266073,-0.009475268,-0.0052933763,-0.021585038,-0.010799702,0.0023036273,0.028807178,-0.0049965116,-0.02795602,0.011273534,0.008172557,0.0020660423,-0.00793608,-0.021736644,0.01581447,0.038733076,-0.005980599,-0.011754201,0.012141502,-0.0235349,0.010840976,0.0034812186,0.03321451,0.017002815,-0.019759312,0.017482989,-0.005896959,-0.0076237563,0.00937545,0.001121324,0.00404654,0.0050542923,0.022820508,-0.015832005,-0.0055048354,-0.0030737752,-0.019674368,-0.009587398,0.00937538,-0.05441248,-0.0061558797,-0.0127543155,-0.00480652,-0.019672073,-0.020314928,-0.0035990486,-0.018519636,0.01200363,-0.0046064723,-0.0071584727,-0.012431101,0.0024673648,0.040249683,-0.008554285,0.016652036,-0.0014644158,0.0077441214,-0.0155060645,0.018389374,-0.038219374,0.003262951,-0.027108334,0.0145559525,-0.007588676,0.04897781,-0.024962345,0.015027058,-0.016220145,0.0036088175,-0.0070319455,0.01720035,-0.03978468,-0.015731743,0.0044666994,-0.030772014,0.006826224,-0.00073064526,0.015541437,0.022764908,0.007790083,-0.008100772,-0.009926814,-0.026053395,-0.020393843,-0.030005815,0.0013963893,0.044758044,0.058871176,-0.0025499312,-0.0021641823,-0.03172116,0.00012158692,0.0035203702,-0.0055163805,-0.011006308,-0.009017832,0.0006018529,-0.0049351333,0.020272713,0.013303822,0.00049826386,0.001605348,-0.16838644,0.010388879,0.0026007947,-0.015153208,0.0051808367,0.018669423,-0.009521743,0.013219926,-0.0116326185,-0.032546356,0.01799721,-0.021425795,-0.01972452,-0.011523249,0.03269883,0.101257436,0.018192422,-0.0069683064,0.00012694277,0.01208817,-0.0009431666,-0.027322914,-0.0091661755,0.024340963,0.018797921,-0.016948387,-0.021083709,0.0009335734,-0.018768128,0.0085531715,0.004941206,0.006259071,-0.032678254,-0.0043181535,0.0038288306,0.0014901591,0.009498045,-0.0072577805,0.0025530155,-0.019617612,0.044127353,0.033135824,-0.024894482,0.0029633134,-0.0028154238,-0.013694417,-0.0032416105,0.0011341019,-0.013990132,0.0017863846,-0.020585945,-0.07942827,-0.02388305,0.03558264,0.006477994,-0.030439755,-0.02033765,0.005734566,-0.019894365,0.0018715141,-0.005012474,-0.0030045658,0.011374339,-0.0010490346,0.0026184395,0.0127324285,0.017907003,-0.0026296591,-0.02154571,-0.013216087,-0.0050186818,-0.0010488735,0.0032622975,0.016617967,-0.0137005085,-0.018252432,-0.010396019,0.029398669,-0.0019901537,-0.025480883,-0.0039879247,0.019394916,0.008277307,-0.019456422,0.011196973,-0.008581747,0.006519452,0.016538879,0.013522728,0.004319538,0.0020020143,-0.0028955727,-0.018301604,0.0001888565,0.001986071,-0.026054187,0.008236313,0.018724669,0.01646495,-0.008922896,-0.012201703,-0.033876464,0.004108868,-0.047435954,-0.0013203023,0.010668558,0.02950937,-0.0015462082,0.024482753,0.0067304196,0.002582221,0.009656412,-0.005152926,-0.007430619,-0.0059264135,0.016690087,-0.0012140692,0.0010942558,0.0018593828,-0.017379848,0.010933108,-0.00046275236,-0.0020538233,-0.012065672,-0.007698509,0.010488963,-0.013234988,0.024141362,-0.017056873,-0.0056241057,0.0041335584,-0.0008408702,-0.006008033,-0.0046468307,-0.0061571323,7.9379606e-05,0.0069864225,-0.006437211,-0.0059746746,-0.010662362,0.010249915,-0.0040639113,-2.9519031e-05,0.0060297404,0.024476472,-0.0009469502,-0.011967785,-0.0020857807,0.0011977864,0.00039886072,0.0029112818,-0.015702143,0.0013855359,-0.0116705205,0.01047628,0.010705485,0.0038831877,0.009348412,-0.0041123633,-0.01274591,-0.0031742104,0.00077575364,0.004692257,-0.005379834,0.014214636,-0.0063652964,-0.0026519722,-0.011439514,0.002569604,0.0067632,0.007657354,-0.016123073,0.010100967,0.011425995,0.0064178365,-0.011223521,-0.0044505233,0.0014506207,-5.2860785e-05,-0.0025996852,-0.009838154,0.014235926,0.012449171,0.004091049,-0.021397322,0.014944875,0.012824706,0.005740952,0.002781688,-0.006879365,-0.01724131,-0.007305876,0.017976,-0.029792955,-0.014088035,-0.00027337534,-0.0031192773,-0.019501999,-0.0019678553,0.0030639728,0.014422117,-0.02569946,0.018895024,0.0068151886,-0.019922629,0.0021643315,0.024796063,0.02273029,0.010975593,0.015021143,-0.0010763354,-0.0023217648,-0.008122144,0.0032855,-0.0076918397,-0.0023792975,0.0013716334,0.0077987406,0.006972421,0.008750683,-0.005202949,0.0020709378,0.0018981829,-0.0068130824,-0.00012413124,-0.018548168,-0.012141671,0.0031647426,-0.009815918,-0.011951625,0.008794607,0.021234356,-0.008995693,-0.00018233187,0.00017826159,0.016874988,0.005525046,-0.013255524,0.013630718,-0.015038952,-0.0009988514,0.007613384,0.015405146,-0.013139159,0.00066437764,0.0043810755,0.022277191,-0.012725737,-0.021722589,0.009323871,-0.0074648904,0.0039243232,0.028066406,-0.0006655123,-0.013069302,-0.0034949132,0.00022349978,-0.008597913,-0.004795445,0.002061459,0.01320536,-0.010110397,0.0010437091,0.006391859,0.0099347085,-0.0015109149,0.003765287,0.0026159955,0.0060755163,0.013009279,-0.0018933878,-0.0017281545,0.0050018644,0.016800085,-0.0030249704,-0.012822144,-0.014936928,0.006164412,0.0130275665,-0.018287448,0.0030108965,0.016049778,-0.011667537,0.0065292297,0.0031118463,0.004063678,0.011091202,0.0038566203,-0.01180416,-0.016790755,-0.011611786,0.0007025604,-0.013870053,0.025977828,-0.017796516,-0.001543578,-0.00054277515,0.007303309,-0.0062801596,-0.009181662,0.0110197775,-0.003672455,0.010788741,-0.0011553988,0.013351677,0.0010263022,0.0056292773,0.007235467,0.014095187,-0.0061525796,0.11339082,0.015404016,-0.0054992633,0.022375707,-0.02458139,0.015428935,0.002474567,-0.01773916,0.018731829,-0.015662799,-0.0104016755,0.011927355,-0.0036788997,0.0036064351,-0.005279918,-0.009853684,-0.012104272,0.015575912,0.0040427768,-0.0029671679,-0.009608788,0.00035634605,-0.012351603,-0.010169075,0.0136931995,-0.014840636,-0.012997589,0.008611008,-0.0071452404,0.031607337,-0.0008446499,0.012913608,-0.00748385,0.001493148,-0.021661393,-0.0064495523,0.001087885,0.005156455,0.0069303336,0.022678228,-0.0030813708,0.011195084,0.00080762047,0.017164152,0.011270742,0.014682129,-0.017539542,0.008640193,-0.0009230556,-0.012943476,-0.006990674,-0.009781711,0.021190407,-0.0019369985,-0.019077577,-0.0057572336,-0.0009466676,0.009376535,0.017310254,0.008767343,-0.010923681,0.007090896,-0.002179026,-0.026175551,-0.003804748,-0.022470793,0.0002901159,-0.017892253,0.00019999842,-0.0002933406,0.010932738,-0.024030795,-0.01108019,0.011766497,0.018969115,-0.003243455,0.0010341636,0.012228406,-8.204125e-05,-0.009298866,0.009621199,-0.0019371823,-0.040253446,-0.00056348374,0.0029738597,-0.016264696,0.005900578,0.0025805214,0.008495016,-0.0012478488,0.00023488568,-0.016518869,0.005381824,-0.0024586702,-0.00071063975,-0.0045016957,0.035292502,0.012656235,-0.01046627,0.0002313688,-0.016991396,0.0017883983,-0.002126162,0.0011806687,0.0361049,0.004959042,-0.0033190837,-0.024265751,0.020358277,0.0054935445,0.0042963596,-0.005772602,-0.0034877076,-0.00485317,-0.0050100354,0.0013974106,-0.0124427695,0.0042749196,-0.00949336,0.00092153763,0.0059453663,-0.012663379,-0.012077407,0.015111418,0.010740636,0.0030413652,-0.009104791,-0.011811516,0.004603208,0.013533522,0.011119213,-0.006929276,0.0029713914,0.015717467,-0.005941306,0.00011580867,0.0063884566,0.0073783547,0.011627818,0.015434326,-0.008203749,-0.008849416,-0.009991449,0.014221152,0.00830224,0.0036713101,0.011640028,0.01916661,-0.0001754786,-0.005312644,-0.005290344,-0.0001031842,0.007025242,0.012665148,-0.02136448,-0.0172818,0.009198944,0.003394729,0.011302587,0.012721675,-0.024009096,-0.0047145416,-0.0006205448,0.009046693,-0.0015224906,-0.026750667,-0.0021867335,0.030674262,0.0032272488,0.011249177,-0.009884914,-0.0020713415,0.010931171,0.0033803263,0.008750244,-0.0018358926,0.010834302,-0.01946264,-0.0048701456,0.0032821211,-0.0033035362,-0.0048449836,-0.012626224,-0.01801205,-0.018447341,-0.017510451,0.0024640716,-0.009481285,0.004595025,-0.00043608772,0.0037378562,-0.0071680383,0.017740266,0.013414902,0.018136542,0.0042185946,0.004875275,-0.0021077846,-0.0018777333,0.008979703,-0.0039104996,-0.0040953998,0.0023962164,-0.005528289,0.002107287,-0.0051758303,-0.010736328,0.011936257,-0.0073643695,-0.0031871367,-0.029335765,-0.013251277,0.0067582927,0.01113153,0.001810546,-0.00078393123,0.0011150045,-0.008117978,-0.0019025959,-0.015406446,0.000688632,0.010082542,0.0058297906,0.008201794,0.012347925,-0.0065791165,0.0049549732,0.005196167,0.01650471,-0.0015191875,-0.02272408,0.007884524,-0.00015613664,0.017925803,-0.007973077,-0.011069697,-0.011807565,0.0020830827,-0.005587102,-0.01010781,-0.005636171,-0.013056945,-0.0022149535,-0.010077146,-0.014837782,0.004731301,-0.0106119225,-0.003422956,-0.013389089,0.0053837183,0.008944551,0.013517947,0.00068778615,0.008798918,-0.010697702,0.0005515984,-0.0010894018,-0.04637506,0.023283163,4.8365437e-05,0.010363392,0.014964771,-0.010178852,0.00472725,0.0018699513,-0.0071333027,0.010401979,-0.004841556,-0.017205501,0.008186409,0.010550934,-0.0029909695,-0.0026088865,-0.005371754,0.017373318,0.001533081,0.0133241,-0.021982811,-0.011813981,-0.011032827,0.009944967,-0.017700365,-0.013268457,0.001746661,0.012841938,0.010995263,-0.0045270906,0.0053174575,0.00918222,0.011942949,0.015470427,-0.003971386,0.010912975,0.0037895513,-0.004360065,0.0025492895,-0.005692687,0.020591207,-0.008776722,-0.0075343424,0.021169132,-0.006477993,-0.0016306113,0.0006177519,-0.0063285823,0.019082854,0.0013247858,0.014304516,0.02567105,0.009305751,0.021772841,-0.0049511334,-0.020563822,0.007796927,0.012397774,-0.0096930675,-0.0013012321,0.0032564397,-0.003427633,-0.005163939,0.0038307463,-0.014356182,-0.005192828,0.0028142296,-0.00785265,-0.009572236,0.03764532,0.0006896299,0.008304985,0.016292198,0.009616499,-0.0074477554,0.009305296,0.018426098,0.0023409643,-0.01770736,-0.0016963414,0.0037032943,0.01905528,-0.009867103,0.009161668,-0.004336594,0.01871435,-0.0015737638,0.0021599468,-0.014934888,-0.0047918544,0.010471143,-0.0026318294,0.0060466253,-0.0044041597,-0.006783601,0.022027772,-0.0014629778,0.021803707,0.014799875,0.0012347717,-0.023571555,0.002795982,-0.0037776006,0.015365858,-0.020522779,0.022652397,-0.0038316557,0.00793119,0.00958669,0.0027830196,-0.0038146328,-0.0041622054,0.012258948,-0.00833914,-0.008452786,0.0004515465,0.008471624,-0.0068161255,-0.0072377496,0.0023620743,-0.02367278,0.0045074793,-0.00086217525,3.872647e-06,-0.0005416175,-0.0012045233,0.0029048903,-0.005526895,0.007832674,-0.026802337,-2.158923e-06,0.00019804353,-0.0059627295,-0.0037065216,-0.0008236663,0.009372056,0.017363094,-0.010384782,0.0033678885,-0.0005365176,0.009581992,-0.008543796,0.015370218,0.004741761,-0.018056387,-0.0023356078,0.019248663,0.0009444112,-0.0069813947,0.0120992735,-0.004724792,0.004585097,-0.0027558731,0.01591475,-0.01555614,0.009607163,0.018801294,-0.0041373023,0.01457213,-0.019166747,0.023358386,0.010946704,0.002760753,0.008399884,0.008750339,0.0077156085,-0.018380126,-0.011655256,-0.006186032,0.0041343365,0.014699527,-0.00082860974,-0.0033601187,0.0005133903,0.011820835,-0.002819575,-0.009537056,-0.0006670591,-0.022912461,-0.0013260759,-0.005104646,0.002836366,0.0058423853,0.014239299,0.018309155,0.01511361,0.0032150035,0.0010479994,0.01618433,0.003651573,0.009461729,0.0007922705,-0.0067452034,-0.011360007,-0.0023203783,0.0024697573,0.02216941,0.009526107,-0.003549866,-0.018560803,-0.0015793836,-0.008834637,0.0002960516,-0.007890925,0.004177172,-0.096825376,-0.00014978663,-0.0010796586,0.019742295,0.005510766,0.0119608315,0.010799245,-0.0007648377,-0.0068832035,0.0020646695,-0.00834625,-0.002115645,0.0074537643,-0.022381019,-0.0025599482,-0.0129519235,-0.015918087,-0.0054052887,-0.0013460306,-0.011830956,0.021588663,0.0011619875,-0.003872371,-0.0005977816,-9.87626e-05,-0.0008265928,-0.021799406,-0.014973959,0.0025794262,-0.006694525,0.016608655,-0.014086256,0.011657567,0.018352648,0.00059672835,-0.00049926434,0.006226465,-0.0013334507,-0.1288446,0.0010236348,-0.008790075,0.013097425,-0.006231166,-0.007494866,-0.005193106,-0.0002165778,0.014238607,0.016699018,-0.01052126,-0.004152179,-0.008336412,-0.0027153566,0.009615777,7.042309e-05,0.018364685,0.010218978,-0.0024347296,0.010159038,-0.0024426873,-0.004796068,0.0024323128,0.0015820918,0.016005702,0.004034915,0.0009891428,0.010497658,0.004821741,-0.0069956523,0.022222256,0.005841722,-0.005173138,0.01432462,-0.01579578,0.001778456,0.013172951,0.010609923,-0.021048134,-7.873102e-05,0.02502568,0.0060388194,-0.002394768,-0.015957905,0.017663404,-0.006626152,-0.011703191,-0.0047228877,0.010297921,-0.0028459018,0.004244047,0.004652794,-0.024431173,-0.0053192247,-0.0063024824,0.008452341,0.0028726489,0.009993564,-0.025530355,0.013238643,-0.009106599,-0.0072810054,0.0026299895,-0.016833745,-0.012413346,0.013406163,0.010026969,-0.008275647,0.011901221,0.03203038,-0.001687108,0.007217189,-0.007231377,-0.0060068904,0.022950528,-0.019743145,0.035092678,-0.002101803,-0.0055780825,0.0007392587,-0.00029618706,0.003731912,0.0053116987,0.012726491,0.016615445,0.0019693978,-0.0007098695,-0.011989623,0.0022653576,-0.04856151,-0.0044091702,-0.0073220097,0.015356192,-0.00051672803,-0.010978428,0.038626198,0.010936225,0.013602985,0.0038595356,0.00803456,0.0025351336,0.0011922448,-0.017386805,-0.0036928586,0.0037448327,-0.012746337,-0.019426242,-0.01154012,-0.008742059,0.0031151806,-0.03269484,-0.004387997,0.03260579,0.017567545,-0.010067463,0.0032674887,0.0023693861,0.010759233,-0.01686742,0.010342372,0.0053144386,-0.004039097,0.003728873,-0.017248193,0.010728691,0.00026249257,0.032342065,0.010389049,0.00072354404,0.017868044,-0.021989228,0.0050287144,0.025009464,-0.010798158,-0.0022235163,0.013110559,0.015624168,0.0147320125,0.017258605,0.009497775,0.005754562,-0.008462595,0.013291726,-0.0023195085,-0.0070000547,-0.013427973,0.006152726,0.004353316,-0.011388697,0.018548502,-0.018478792,-3.1031537e-05,0.0035435848,0.0022958587,0.016479917,-0.004378597,-0.0006727939,-0.004121766,-0.0075353626,-0.010021702,-0.0043248013,-0.0070678047,0.010610988,0.011633105,-0.00072080985,0.019362839,-0.02556462,-0.025581606,0.011830622,0.010264418,0.0013437845,0.010382256,0.008058647,-0.0009758237,0.005166281,-0.009934202,-0.0030473154,0.00084059127,-0.0022654824,-0.005677957,-0.019238913,-0.019345889,-0.007376241,-0.02743401,0.03748285,-0.019598378,0.008789915,-0.006749478,-0.037048675,-0.0055223354,0.013050909,-0.01000211,0.0067230486,-0.010574939,-0.016231101,0.0061930087,0.006393065,-0.0090088565,0.00427157,0.015413074,-0.022932291,0.00072082895,0.0182878,-0.16671848,-0.018393738,-0.0013149059,0.022711148,0.013748555,0.008585448,0.009499616,-0.00071654434,0.006502659,0.0072905025,-0.00020474692,-0.025879385,-0.0057908273,-0.020526368,0.0063472046,0.010499444,0.011021315,0.006676936,0.007985139,0.0037536453,-0.025706865,-0.0040632957,-0.0023950902,0.016283108,-0.012519823,0.0032201067,0.0066951597,0.015073222,-0.01735317,-0.025687201,-0.0099169705,0.01384399,0.012690931,0.018462673,-0.019707406,0.008345278,0.006404902,-0.00397911,-2.1320722e-05,0.018315032,-0.023027994,0.010178661,-0.014248048,-0.010739006,-0.0047453633,-0.010908958,-0.023761796,-0.0034447762,-0.016855814,0.0139414435,0.007016047,-0.02948101,0.044250015,-0.022511711,0.0146579845,-0.027619021,-0.00039370806,-0.015722666,0.0017548776,0.009574735,0.011846396,-0.020866161,0.019997843,-0.0041013747,0.016986942,-0.005775967,0.008962092,0.16585734,0.0043443004,-0.0011599895,-0.0095808115,-0.010921794,0.025671484,-0.016914591,-0.008343184,-0.020814631,-0.0041682427,0.012709981,0.0010146005,-0.013944539,-0.0022975153,-0.020734278,-0.0359916,-0.011760619,-0.01972108,0.007838412,-0.0017789232,-0.0018610908,0.0072320737,-0.0046655685,-0.0021540287,0.014888204,0.0053894217,0.00021693867,0.008612571,-0.0019105572,0.022491632,0.0002710471,-0.026115807,-0.0012721688,-0.007290101,0.015832389,-0.0096336175,0.004158528,0.0048008054,0.0055778315,0.012302758,0.010503486,0.008019851,-0.014996934,-0.005933277,0.007893655,0.015093948,-0.0035052637,-0.0071737967,0.016344057,0.003933644,-0.04349449,-0.022881528,-0.010908242,-0.007092004,0.0006824385,0.013188275,0.0011449567,0.011752309,0.010517474,-0.0021919408,-0.006411303,0.005460514,-0.025429698,-0.014064229,0.009147773,0.013683186,0.046994418,0.016587164,0.0026828374,-0.10772896,-0.010032851,-0.02796578,-0.02431353,0.009939759,0.0050668404,-0.0132374875,0.014807146,0.0038177294,-0.016793841,-0.0011904896,0.01336568,-0.00035152765,0.0046708044,9.9863544e-05,0.0035210988,0.015553848,-0.015285958,0.03296981,-0.015934436,0.0002852292,0.0030368841,-0.020492043,-0.016100297,-0.0044471314,-0.0104821455,-0.008448717,0.008391748,-0.0019421333,-0.00024728983,0.0065836227,0.010627282,-0.006404686,0.012713844,0.0024292215,-0.015874017,0.01820428,0.013278133,-0.0052561043,-0.022406474,0.004299525,-0.0018214309,-0.00013818215,-0.009856946,-0.0054371585,-0.0007291873,-0.006453439,0.0025611175,0.0047306465,-0.004389629,-0.004780021,-0.011969554,-0.01284693,-0.0058168327,-0.005073465,0.023571908,0.0077593545,-0.02349326,0.0017922851,-0.018125914,-0.010318862,-0.0032826685,0.022621363,0.029551882,0.006540359,0.0005382836,-0.006732114,-0.021945829,0.017048217,-0.0074359737,-0.011605385,-0.009929661,-0.009361257,0.007352491,-0.00054524984,-0.017535591,0.008155615,-0.00045145978,-0.029549392,0.0020963913,0.0014513207,-0.03367085,0.018371068,0.0056307595,0.05716627,-0.003708968,-0.0036910744,-0.0054517253,-0.0030839918,-0.011507465,0.012050537,0.00857434,-0.012271062,0.012628293,-0.0047914307,-0.0050471844,0.0046842312,0.012668455,-0.0013832108,0.0023602913,0.0070823813,-0.015120606,0.012743261,0.009367556,-0.00036798525,-0.005047326,-0.007385021,-0.006952149,-0.0094487015,-0.010772887,-0.0045121415,0.0038643822,-0.039412893,-0.0024142487,-0.00922039,0.013643604,0.007966113,0.0073505067,0.011014974,-0.0069368733,0.014145237,-0.017474988,0.0007528508,-0.013518708,0.0029731072,-0.0074476404,0.00045454863,0.02940162,-9.180611e-05,-0.012840084,0.0035422593,-0.015003807,0.02193834,-0.0076211896,0.03821117,-0.002834794,0.020786023,0.02086173,-0.0012477107,0.0191409,-0.02904634,-0.014657611,-0.012933201,0.017590879,-0.0073283263,-0.0040986077,0.014955108,0.022599898,0.0071848147,0.002350603,0.025142211,0.0012765969,-0.01982444,0.006354679,-0.00016009981,0.0058832844,-0.006963326,-0.004895073,0.0026305087,-0.00586825,0.0054275747,0.012300003,-0.0201653,-0.0063662925,0.019639691,-0.0077815284,0.005844665,0.012107672,-0.00028104117,0.0048295413,-0.004675702,-0.002352434,-0.0028551165,-0.01127312,0.0031588038,-0.015299044,0.0026807978,0.0019780484,-0.016669225,-0.07686693,0.027940627,-0.008033394,-0.008106912,0.012156845,0.0062891743,0.0034795415,0.014814103,-0.013049195,0.015506053,0.0035074365,-0.004889395,-0.00841312,0.03305257,-0.011641884,0.011725512,-0.011280758,-0.011978873,-0.0013959092,-0.0016484834,0.035750654,0.01525817,-0.001105129,-0.031192608,-0.021396179,-0.0037688243,-0.019943487,0.004927049,-0.019680599,-0.007907893,-0.007912394,-0.021632764,0.012397823,-0.019126106,-0.0027689978,-0.017661104,-0.013834036,-0.015973262,0.00032083364,-0.013292046,0.009938607,0.0031145778,-0.084857754,0.006413928,0.006137457,-0.01690837,-0.0045967246,-0.01099091,0.020396594,0.0034489366,-0.009141231,0.0011397629,0.019972857,-0.006070133,-0.02483168,0.009985725,0.0013694193,0.0059396825,-0.013409794,-0.011089644,-0.013640079,-0.014721369,-0.016519645,0.008742028,0.009268244,0.017802892,0.0037386098,0.017975869,-0.0075809956,0.022540344,-0.0156137785,-0.005783072,-0.0033149433,0.0019262042,-0.012212375,0.0063712536,0.020312505,-0.02447654,-0.0068450933,0.016266061,-0.011609602,0.00847681,-0.008425263,0.0088488795,0.026273834,0.030399913,-0.020202396,-0.10319142,-0.009027672,0.0059628426,0.0031220287,-0.002313113,0.0103825405,0.01258738,0.045257766,-0.01061624,-0.012556884,-0.005530787,-0.005865573,0.01684341,-0.010272075,-0.01968756,-0.013569385,0.014430748,-0.0054383245,0.0062595364,0.021975832,0.0048198574,-0.012030808,-0.0093736,0.009218483,0.011638845,-0.04227073,-0.009165918,-0.010103864,0.0052153165,0.008288282,0.02716895,0.014527683,0.0103676105,0.008210804,0.0046030814,0.010866909,0.0113309715,-0.0026792723,0.010584302,-0.011528814,-0.018500088,0.0047755796,-0.005163545,0.024630459,-0.016562415,0.023466863,-0.008558939,0.0011917269,-0.018329889,0.002531626,0.010439881,0.016159488,-0.016520832,-0.0010399037,0.018024681,-0.00022197393,-0.000802028,-0.00042554425,0.02364505,-0.0064625256,-0.012204831,-0.0065204604,0.0089202,-0.0018842563,-0.02286281,-0.0007264488,0.0038057435,-0.014069505,-0.010606161,0.0051749237,0.011588508,0.014138994,0.01710191,0.016527686,0.018893031,0.0077288034,-0.007507105,0.031965144,-0.019028846,-0.0047805803,-0.019593243,-0.00037123234,0.014467262,-0.013654403,-0.00016855489,-0.015074778,-0.0125175,0.0025726242,0.007023011,-0.009152889,0.014163502,-0.018306311,-0.0034092336,0.011348222,0.015088154,0.0067584636,-0.016218731,-0.0064224023,0.014760807,-0.0023317651,0.0045614624,-0.00021048264,0.009329645,-0.005180669,-0.006317825,-0.0062087732,0.00012054165,-0.00088235835,-0.006473178,-0.0021673117,0.01366932,-0.004078854,-0.016950982,-0.010674208,0.0076885503,-0.0017653835,0.0011600064,0.00476828,0.008070535,-0.00018179356,-0.006167265,-0.010397882,0.005424812,-0.009200807,8.921567e-05,-0.023099694,-0.01571834,0.022342846,0.033222273,0.023026733,0.017576566,0.009186273,0.012919406,0.001732276,0.010078752,0.0021203822,-0.0032118836,0.0095649315,0.002508974,-0.004394672,-0.008750326,-0.009193353,0.0024861007,-0.002363229,0.0050337734,0.016216962,0.025733648,0.013435242,-0.0020137092,-0.027673587,0.007459053,-0.0058789393,0.0131946,-0.013126776,-0.004089939,0.007843711,-0.0021593522,-0.03255512,0.00747557,0.005577064,0.005156673,0.036746442,-0.01824871,0.0045812195,0.008340891,-0.015559403,0.004913825,-0.006830973,0.01263387,-0.0029467088,0.029199164,-0.021233467,-0.012593448,0.0053684376,0.03562766,-0.01891272,-0.00792741,0.0025134117,0.0092410995,0.0015920685,0.0004628292,-0.0029432282,0.0008626962,-0.01638158,-0.007833085,0.0042596846,0.0010365896,-0.005349702,0.0032923105,0.0029764953,0.0055006756,0.026210994,0.0061946507,-0.017316673,0.0004885005,-0.0020682353,0.0025939278,0.012387597,0.021409703,0.018735139,0.007371351,-0.002121534,0.0051455013,0.011480808,-0.0005412676,0.0014881695,-0.053343758,0.007836919,-0.014588545,0.013920708,0.011907411,-0.0087150475,0.0040931846,-0.0002480769,-0.010632199,0.020744497,-0.009784975,-0.008351061,0.007653746,0.021804143,0.017526774,0.027185127,-0.009444271,-0.0043598562,0.00018228324,0.007122202,0.010014023,-0.005827894,0.01169958,0.011338098,0.0072549493,0.00935892,-0.015114407,0.010990979,-0.0005596781,0.0074150227,-0.004787553,-0.009444966,0.007120509,0.0045091184,0.019899258,-0.006070165,0.0076400554,0.02556437,-0.004804163,-0.027485361,-0.029356685,0.000669587,-0.0057374774,0.014530366,0.0143037345,-0.0056679873,-0.01704444,-0.017962191,-0.020744296,-0.0018802957,0.004692761,0.00463437,0.015483451,-0.0049655247,0.009217709,0.016186157,-0.019968811,-0.007447838,-0.039368335,-0.024908042,-0.0070570647,0.0031624846,-0.008914836,0.005966513,0.020506438,-0.009675563,-3.4781107e-05,0.0054887165,-0.01640844,0.0048884205,-0.0026951744,-0.010355399,-0.008837893,0.012817787,0.001105242,0.018333003,0.013787685,-0.0073643643,0.020435706,0.013816393,-0.011146534,0.013984181,0.00263571,-0.0130378455,0.0073803654,-0.01797809,-0.0004732089,0.011219854,-0.007356989,0.000837202,0.004035732,-0.017628375,-0.0070318547,-0.015103693,0.0152614135,-0.0048088934,0.009736713,-0.03462954,0.0038974094,-0.0013675061,0.025501186,-0.020948885,0.008548119,0.0072676344,-4.9542738e-05,0.019413281,-0.002718623,0.0059902826,-0.013252631,0.019807722,-0.016521236,0.005395028,-0.0009745226,-0.0035968944,-0.009046967,0.0017308985,-0.0053738095,-0.010074872,-0.014530248,0.010391716,0.008743565,-0.003940228,0.0034051773,-0.01698042,-0.0024660015,0.001395402,0.014916964,-0.019264402,0.0026269164,0.0012285784,0.0052861692,0.029138595,0.009469573,0.009227235,0.0048452998,0.031553503,0.008937684,-0.0029732778,0.022574913,0.0002929528,0.011350464,-0.015808988,0.015390211,-0.011530075,-0.013625117,-0.008526706,-0.0021377627,0.016858151,-0.004120617,-0.010534767,0.009659495,-0.036831744,-0.0003086126,0.007854209,0.008018421,0.028682537,-0.0016334687,0.002501906,-0.0102431765,0.008157548,-0.0116339605,-0.031410106,-0.01783779,0.02530839,0.0005854515,0.009200905,-0.003051923,-0.009439886,0.0012279788,0.018879013,0.004704249,0.0053134,-0.009410854,-0.0112396665,-0.0054891733,0.0007979053,0.008650399,-0.0032628078,-0.010915627,0.005458663,-0.008035287,-0.0067593795,0.01831951,-0.021055548,-0.018762935,-0.00037001199,0.017820878,-0.011120019,-0.013042393,0.01201238,-0.0025622568,-0.0076236427,-0.011352406,0.01935489,0.010709142,-0.0074312296,0.013659025,-0.008110818,-0.0039192657,0.01399913,0.0015641474,-0.019046025,-0.01779946,-0.0059139403,0.004389289,-0.016803794,0.00010309911,0.019896796,-0.012378582,0.014833703,0.016026903,-0.004536333,-0.019616397,0.004114554,0.0021012612,0.007955154,-0.010633098,-0.008758885,0.0039660707,-0.0033292947,-0.00022537934,-0.007940709,0.014458209,-0.008936904,-0.029291175,-0.002357941,0.0069757467,0.016994433,0.010847876,-0.009201893,-0.009647785,-0.022478702,-0.008122637,0.02537199,0.011489539,0.009588422,-0.00032316905,0.01516032,0.012263852,-0.009837305,-0.017646918,-0.00014019586,-0.0050618667,0.012178444,-0.008123674,0.00049076433,-0.018093014,-0.013332234,0.019039292,0.0015995837,-0.0108103985,-0.007719713,0.027745413,0.009945831,0.009387363,-0.0133993495,0.012456948,0.006453607,0.0024787977,-0.024825426,-0.0158928,-0.015026363,-0.018639795,0.019684996,-0.005902367,0.014311487,-0.04767847,-0.0039938195,0.034786724,0.0017971944,0.008475008,0.0010203958,0.0007861404,-0.03965708,0.032200813,-0.00069834763,0.006418373,0.017588869,-0.011464069,0.0033221866,-0.0050353585,0.009577782,0.0040000645,-0.021188287,0.014556609,-0.019793032,-0.025439376,-0.008342204,-0.012830796,0.012570675,0.0070919893,-0.026969168,0.0013465012,-0.024365017,0.0059636496,0.0061190883,0.016128872,-0.00502948,-0.0043467493,0.017842708,0.008684087,0.0134997275,-0.023878915,-0.019245768,-0.013356536,0.00058965146,0.0022798763,-0.019836692,0.016254295,-0.022848085,-0.0039408254,0.009493561,0.01561286,0.007745657,-0.006640055,-0.015087224,0.015831627,-0.0009864039,0.02392289,-0.015940983,-0.022872813,0.011032774,-0.014492378,-0.012939718,0.012974013,0.0050670807,-0.011702883,0.015831865,0.0005309041,-0.01888548,0.0074429475,-0.007518739,-9.3984134e-05,-0.016753668,-0.014466394,-0.020148695,0.020802725,0.0076952237,0.0014906083,-0.021227067,-0.010753544,-0.026542772,-0.0058434876,-0.009341217,0.0120545775,0.0075257127,-0.0072358456,-0.017289111,-0.014156456,0.013295275,0.009617664,0.011919864,0.010056935,-0.007816914,0.00534255,0.0061491975,-0.049574118,-0.019768277,-0.038442034,0.00972612,0.027323984,0.022148065,-0.0077727344,0.0029392357,0.0027503786,-0.03199443,0.025431411,-0.011481379,0.019851593,-0.0065096626,-0.0014607062,-0.013748935,0.0069557093,0.027585905,-0.00202162,-0.01745947,-0.013627905,0.02206419,0.005054262,-0.0043787328,0.0033581413,0.014446837,0.005933873,0.014693965,0.007870198,0.012078119,0.013851333,0.0066436427,-0.017323187,-0.01718135,0.009701986,-0.0029899336,0.021807503,-0.01657058,-0.01092524,-0.011114479,0.0071078837,-0.00125983,-0.018509487,-0.0032709707,0.021072,0.0049205534,0.003396354,0.00020525604,-0.012899736,0.01965317,-0.006450477,0.0007071109,-0.0051919604,0.02364671,0.002119605,-0.012190807,0.0066187317,-0.0094460845,0.012416663,-0.0030832805,-0.0012778623,-0.01847647,-0.010380757,0.005514663,0.02035682,-0.0026089554,-0.002377438,0.00014996289,0.010442123,0.004608329,-0.0050043836,0.011688637,-0.0044820737,0.014770342,0.0057242555,-0.0012987946,-0.005250028,-6.9108115e-05,0.015354091,0.0045345826,-0.0067405966,0.0028383392,-0.0038058434,-0.010399034,-0.0026567236,0.0038338827,0.0040937634,-0.011554366,0.0031113378,-0.0007693166,0.0025599573,-0.011887488,0.0013957275,0.004421492,0.02773243,0.00083674444,0.009640197,0.018288702,-0.0011639913,-0.008831084,-0.005527785,-0.0036269687,-0.0072716763,-0.008612366,-0.0011687558,0.004668062,-0.0018844256,-0.0004191975,0.00083947816,-0.004141643,0.010432312,0.009794151,-0.00067306915,0.0011033356,0.004090025,0.036241923,0.010987659,-0.015519747,-0.024680665,0.020286253,-0.005739748,0.0071407696,0.0139983455,-0.0023514424,0.1742115,0.11772743,0.017345142,0.017185306,0.010511673,0.013323345,-0.02744257,0.0031447215,0.023444494,-0.022683553,0.0028781006,-0.0050632427,0.011188505,-0.000118288845,0.016339807,0.020760478,0.0026353514,0.013021476,-0.008151299,-0.006974203,-0.035211504,0.01505589,-0.013782381,-0.00076144584,-0.00976044,0.018161384,-0.0014728175,0.009772127,0.014523843,0.022400336,0.007108365,0.012476835,0.0006756657,-0.0054680435,-0.0129097905,-0.02185819,-0.021982666,0.020097487,0.0155750355,-0.024878744,-0.006879795,0.023817722,0.0017632515,-0.026743408,0.03820668,0.006675974,-0.00031959964,-0.016732754,0.0074960277,0.011791706,-0.019312711,-0.0070196157,-0.011727625,0.006187892,-0.012483978,-0.009165387,0.023190886,0.019889269,0.0028849586,0.017633036,0.016929122,-0.007115687,0.0068472414,-0.005912657,-0.009666954,-0.013890982,-0.019100718,0.007652433,0.006211228,0.00983638,0.0011083359,-0.0054780967,0.008692962,0.01949507,-0.0023470416,-0.009929509,0.020805933,-0.007989801,-0.006530182,-0.0076091895,-0.005534979,-0.009169713,-0.0021269552,0.033538897,-0.01313909,0.0085434085,-0.021992128,0.003807243,0.055217896,0.013276783,-0.013520075,-0.02315039,-0.018585205,0.006387625,-0.005050554,0.0071821846,0.00040107305,0.010373983,0.008515123,-0.013015801,0.020524165,-0.0005547857,0.0060297204,0.01321584,0.03246778,0.028540831,0.030005457,0.016362881,0.0036219093,0.024954386,0.013519555,-0.00078444026,-0.004579123,-0.005222923,-0.0044588405,0.008540726,0.015308741,0.024047533,-0.099704675,-0.00412614,-0.0030689607,0.018369496,-0.009904883,0.02871501,0.039418686,0.0077949204,-0.0032625326,-0.024193348,-0.003236488,-0.0049870107,0.0073408955,-0.020346303,0.006576649,0.013807723,0.029475534,-0.024931267,-0.0029500339,0.0020644807,-0.03090076,0.0041825916,0.0071631307,0.017025854,0.0137594575,0.03488842,-0.008171439,0.010788616,0.013987615,0.009513696,-0.0026759382,0.012947565,-0.012933548,-0.0012708178,0.00010564658,0.015643854,-9.360601e-05,0.010853366,0.024667934,-0.005087387,-0.016333532,-0.023328912,-0.0075423233,-0.019431408,0.016265137,-0.022925004,-0.0066117235,0.0044103265,-0.014231953,-0.00959012,0.012484322,-0.0016022061,-0.0077751293,-0.0050108708,0.0015289083,-0.005134111,-0.0017917441,0.017138977,-0.01309191,-0.00082288834,0.0029974799,0.0023081063,-0.0021297957,-0.017362004,0.010996724,-0.0056918347,-0.007388699,-0.021526031,0.006639627,-0.00028056971,-0.00933754,-0.014287334,-0.0006450027,0.009853645,-0.022925995,0.0070824013,-0.0003250905,0.00095971796,-0.005361804,0.020977898,-0.005238804,-0.017261373,-0.0016329903,0.13363986,-0.0037255047,0.0012356432,-0.008234168,-0.005019357,-0.010174972,0.0065763677,0.023646122,0.009587503,0.009319348,0.02596264,-0.006966675,0.008056153,-0.012464515,0.004138702,-0.02182128,-0.00085466204,-0.014862329,0.02237243,-0.005593609,-0.01584051,0.008673093,0.006111928,-0.005857841,-0.006863344,0.026878377,-0.002255493,0.016496288,-0.006925914,-0.022980873,-0.014311784,-0.014828691,0.004301177,-0.02568528,-0.0076652695,0.015883027,-0.0034408227,-0.008883079,0.011644545,-0.010058512,0.0030473722,0.00082214165,-0.00019412357,0.007002798,-0.06429231,0.21130568,-0.0073582195,0.00024148889,-0.005232683,-0.006123192,-0.0036742284,0.010932932,0.015107673,-0.0102230795,0.011309436,0.018321833,0.010602917,-0.014332615,-0.00848736,0.022350095,-0.0024952893,-0.0009826317,-0.002654708,0.00415027,0.0066082254,0.023246769,-0.019401148,0.0117842285,0.032117147,-0.030537289,0.016027056,-0.0028406137,0.01882452,-0.0032256844,0.005755906,-0.0083149355,-0.001455333,0.0057125054,-0.018460382,-0.008220346,0.0064162854,0.00899792,-0.0112072425,0.01917971,0.0049762917,-0.011938458,0.02098093,-0.003551513,0.014498668,0.002129181,0.001237778,-0.028756697,-0.004143482,0.0048907986,-0.0018342551,0.012574546,0.0023438095,0.0046225903,-0.007466456,0.006532221,0.0034808388,-0.00052935426,-0.0026587665,-0.00787529,0.010531983,0.009581006,-0.017289566,0.000986923,-0.015248525,0.020019537,0.022513252,-0.03732421]	f	2010-01-29	Male
b1e2b3ea-b1a5-4643-880b-13fe8f5d2119	\N	Pradeep Kumar	pradeepkumarcse126@gmail.com	9501459457	Punjab	Ludhiana	Web Development	Frontend Developer	["IT / SaaS", "HealthCare", "Supply Chain"]	Day Shift	Fresher	140000	Instagram	Designs, develops, and maintains responsive web applications that deliver seamless user experiences.\nBuilds scalable, secure, and high-performance web solutions using modern technologies and best practices.\nTransforms business requirements into functional, user-friendly web applications and digital experiences.\nCreates dynamic websites and web platforms that enhance engagement, accessibility, and performance.	/resumes/guest_d912abed/162bdb9b9e2e481e8c214b88833c33e9.pdf			/resumes/guest_336f0f6e/98429fa34c174dbfb471e2de4b447220.png	rejected	2026-05-30 06:00:13.770914	2026-05-30 06:59:22.336294	[0.010792649,0.009370099,0.015997391,-0.04733731,-0.020007182,0.035704263,0.016711118,-0.006900649,-0.010371671,-0.016510468,-0.010090044,-0.009028598,-0.02286115,0.036961116,0.095726244,-0.02207325,-0.0053790607,0.014850905,0.029608948,0.004234506,-0.0050894944,0.022879215,-0.0031859474,-0.01739392,-0.0056633167,-0.015026845,0.029667543,0.0064658266,0.03915766,0.031530913,-0.0108104,-0.021010406,-0.0034133533,0.029192582,0.03166081,-0.0016576671,0.025438903,-0.023635527,-0.009546642,0.011473326,-0.019246023,-0.001016564,-0.0047399285,0.007054932,-0.028976258,-0.0056840577,-0.007136886,-0.0071762167,0.008486968,0.024898622,-0.0030389996,0.017024813,-0.029314972,-0.17972724,-0.0112481965,0.011083296,0.0030093708,-0.010111243,-0.001551514,-0.025637612,0.012111171,0.010942771,-0.017540097,0.009587527,-0.0026904766,-0.012030139,0.019389339,-0.012138969,-0.009649443,-0.0052171326,0.0020861656,-0.006792412,-0.013887997,-0.0053484906,0.0010259227,-0.019543564,-0.0048096455,-0.010734657,-0.025461106,-0.0030474567,-0.021733,0.01854335,-0.018986776,-0.012717121,0.018109862,-0.022628536,-0.018579386,-0.0256894,0.010184893,-0.006766607,0.0065299175,0.035639323,-0.0017304046,0.00788937,-0.023102375,-0.012909809,-0.004762417,-0.008600964,0.011127738,-0.007098206,-0.001349876,0.00036742623,0.023624899,0.017330099,0.004531348,0.017805837,0.00501015,-0.04282166,-0.016411489,0.02644524,0.0038572242,-0.01771937,-0.0024403085,-0.0006807632,0.011390437,-0.16211598,0.009055899,0.014496713,0.0076793437,-0.017013423,-0.01455633,0.015373733,-0.0063480567,0.012116244,-0.02639627,-0.01048663,0.03131186,-8.6651446e-05,0.008247297,0.009686253,-0.0107264165,-0.019688431,0.032464918,-0.020585518,0.014535217,0.019175624,-0.0024662071,-0.017606558,-0.006868835,-0.02436952,-0.023765717,0.010974285,0.010646882,0.011223274,-0.02875037,-0.0080468785,-0.033294816,0.021727756,-0.012308435,-0.020796586,-0.017999476,-0.0015215265,-0.007921418,-0.02165943,-0.015059339,-0.0117324665,0.009485734,0.012942859,0.0007170019,-0.021473963,-0.021543685,0.008954709,0.034810998,0.028753404,-0.003240206,0.01092561,-0.032464284,0.022723682,0.029084295,0.019824186,0.007723307,0.007400228,-0.00415299,0.010487127,-0.009798624,-0.031322997,-0.006434136,0.015802413,-0.0023308878,-0.037218466,0.0049282503,-0.020197205,0.0003612257,0.00083324604,0.0029314873,-0.024553668,-0.031105867,0.0006348891,0.02797499,0.016351022,-0.005607963,-0.021909358,-0.035963196,0.012558851,0.007205508,-0.020070259,0.0033492404,-0.01898968,0.00895552,-0.015695233,0.004942083,-0.014627141,0.011801822,0.014248071,0.0035207856,-0.005664259,-0.010447112,0.028477468,0.011160622,-0.004747715,-0.021566456,-0.00768663,0.035372652,-0.008391597,0.00035311174,-0.0123751415,0.013239486,0.005806759,-0.002823908,0.011417996,0.015399336,-0.0140462145,0.021794515,0.013834976,-0.022378653,0.02496069,0.0062516676,0.00816149,-0.008527857,-0.0066385586,0.010812803,0.011867884,-0.012065644,0.0054478813,0.017486518,-0.012072421,0.027089916,-0.021188881,0.0016769858,-0.0033789019,-0.003101338,0.01271865,-0.02548629,0.008599021,0.028927911,0.008014511,-0.016756564,-0.0053589083,-0.0035625251,0.007099754,-0.024934389,-0.023382299,-0.014953872,-0.008563965,0.006909825,0.0073793987,0.014206392,-0.0107892575,-0.029004814,0.020019026,-0.008353617,0.006790868,-0.029035384,-0.018942222,-0.0075815124,-0.013733656,0.016038116,0.013231561,-0.0073821372,0.012639417,0.004787439,0.014239939,0.029001134,-0.012302797,-0.016103124,-0.02652794,-0.044358738,0.02182224,0.0020098286,-0.018231735,-0.015958942,-0.0054550436,-0.0034450558,-0.0071732453,-0.0074359826,0.03648792,0.0009925242,-0.039526418,-0.0077886875,0.012415706,-0.0043633454,-0.015141451,-0.018508138,-0.0063275862,0.011489429,-0.02453477,-0.007971973,-0.021232944,-0.0014038365,0.016355686,0.0001733775,-0.010972533,0.025453892,0.04314724,0.017326467,-0.014751985,0.013609813,0.040129267,0.00045149148,-0.0009335689,0.013841859,0.000803223,-0.0018858911,0.011273753,-0.007110207,-0.020064726,0.005567327,0.005297482,-0.0056893267,-0.008906644,0.006256596,0.0019311691,0.027702795,0.01657056,-0.004743809,-0.005558086,-0.01894143,0.018393278,0.04202546,-0.023408076,0.013671723,0.022125795,0.008602175,0.008282787,-0.00014934636,0.024576703,0.034895957,0.0015083182,0.0023033114,0.0024307847,0.019879563,-0.01402438,0.011768185,0.0037820293,-0.014376866,-0.0010392831,-0.025284024,-0.020798184,0.011937558,-0.0088597955,-0.012304033,0.012004252,-0.018141063,0.0045306594,-0.012959098,0.017194921,0.0049830703,-0.006609298,0.0026831236,0.0408086,-0.008569576,-0.0053418786,-0.010133825,0.01973711,-0.011067977,0.022428576,0.0013421057,0.0033705148,-0.032096103,0.017851127,-0.015188559,0.030814301,-0.008395628,-0.025447201,0.010894912,0.019649377,0.0010657427,0.0067428327,-0.016381048,0.01842544,-0.022759078,0.011929015,-0.002674327,-0.003504553,0.029718718,0.014818948,0.018966515,0.006875447,0.002053095,-0.0021468045,0.0053141643,0.008037224,0.020614104,0.045809604,-0.03838728,-0.014295137,-0.0031285638,0.010314315,-0.053687368,0.004625854,-0.012880063,-0.0032498885,-0.020326447,-0.01653038,-0.00017946835,0.026304135,-0.0015371465,-0.0018134722,0.00787563,0.021323394,0.018414915,-0.01112589,0.029553693,0.017456636,-0.003233458,-0.001037361,0.0029349558,0.013994881,0.0058462746,-0.0004912616,0.0054116906,0.013913003,-0.032085005,-0.008012317,-0.008256665,0.001993262,-0.015044025,-0.015352382,-0.014601335,0.010192175,-0.009922089,-0.010541848,0.00048787738,-0.032618035,0.0050059734,-0.009870166,-0.023294272,0.004023708,-0.008282893,0.0017377024,1.9827006e-05,0.002214353,0.024024315,-0.006978261,0.015187792,-0.00015626573,-0.037384238,-0.0309024,-0.003749372,0.01485349,-0.0030459168,0.019766904,-0.007106625,-0.010499056,0.0030120437,0.014221416,-0.0077379635,-0.002554077,-0.016720245,-0.0077126483,-0.020330457,-0.021111023,-0.015699327,0.012340569,0.009865208,-0.022654425,0.0138223525,0.021123542,-0.016065843,0.011528899,-0.016255083,0.0052705836,-1.4980353e-05,-0.030980742,0.0034958262,-0.020879144,0.027194675,-0.017267236,0.011623886,-0.0054397346,0.021512778,0.018263862,-0.036341716,-0.004287046,-0.008443564,0.00555798,-0.03192272,-0.0074005714,-0.008183837,-0.00041836363,0.019036246,0.04148727,-0.0013299311,-0.0067153475,-0.026309349,-0.0128606,0.004055358,-0.015570219,-0.015038288,0.024186924,-0.006496941,-0.021785796,-0.0066781766,0.007685011,0.02492167,-0.006806227,0.017749831,-0.035709746,0.037815206,0.015156065,0.011093871,0.000148749,0.0154523505,0.0034641724,-0.0101792505,-0.0011884293,-0.035963017,-0.02870811,0.010477738,-0.009513669,-0.024262443,0.00069727656,-0.029348213,0.019787705,-0.0071461927,-0.0042747124,0.040114023,0.025835376,0.011443049,-0.0028489532,-0.021210307,0.03584078,0.018582452,0.030103048,-0.017156256,-0.0104029775,0.01283384,0.018036814,0.014619871,0.017870873,-0.0056456532,-0.022180188,-0.0130380355,-0.013774321,-0.017067792,-0.042025156,-0.012094862,0.005769431,-0.012107434,-0.005831841,-0.0067663966,0.007937374,-0.0071143946,-0.005050631,0.0064657964,0.0048758206,-0.030493068,0.01926004,-0.00113072,-0.018697124,-0.0059178,-0.0034842684,0.04298875,-0.0024637461,-0.021504639,0.00953048,0.01440335,0.03279611,0.0067984336,-0.0013728042,0.0011486121,0.038171016,-0.018183772,-0.008016969,-0.0110266525,-0.032638438,-0.009468877,0.013148413,0.038949784,0.019586742,-0.016421448,0.0061182682,-0.011146058,-0.011169519,0.0043198704,0.008942937,-0.01950725,0.00832696,0.012942607,-0.008282245,0.009337555,0.0064920112,-0.003311322,0.0132398335,0.03236177,-0.051052585,-0.0050630146,-0.01439829,0.0012235666,-0.022764688,-0.01973,-0.0010406375,-0.033648152,-0.011165303,-0.00030785275,-0.011431593,0.0039334996,0.027898544,0.03460511,0.00041116675,0.008556662,-0.015232491,0.018135088,0.0035314525,0.0015999563,-0.022425344,-0.03789507,-0.02636202,0.015145455,-0.014559539,0.014081195,-0.01789301,0.032296352,-0.015602054,-0.0018459631,-0.020220282,0.017277097,-0.043901633,-0.008866263,0.0032797342,-0.0074677533,-0.0015134682,-0.0016325851,-0.0022965053,-0.011466898,0.021684207,-0.0052748187,-0.011879248,-0.027717322,-0.018273337,-0.032025166,-0.0030761927,0.024874073,0.046582904,0.014976417,-0.022977276,-0.023662629,-0.001156473,0.020745263,-0.022220934,0.014614607,-0.01646337,-0.003619992,-0.021539656,0.008750228,0.013895419,0.0082552545,0.0011452013,-0.18295558,-0.015375052,0.00016040944,0.0042403536,-0.0037921905,0.00873348,-0.01248931,0.019762151,-0.015299058,0.005535927,0.014024087,-0.041895226,-0.025779685,-0.0030183077,0.01957323,0.090267666,0.005609609,-0.02414932,0.010705309,0.011902001,0.014212825,-0.04121282,-0.010021981,0.0020283696,-0.008550926,-0.029813966,-0.0060439864,-0.011505277,-0.025764776,0.013761618,-0.0068455366,-0.018421253,-0.026208308,-0.015212826,-0.009565035,-0.018112207,0.0126092825,0.0027724986,-0.003723235,-0.025506532,0.030014616,0.011935973,-0.036900654,0.0055750166,-0.0017152946,-0.0051430287,0.0061341864,-0.0068075918,-0.019490536,-0.00047755337,-0.027081983,-0.079318,-0.022129953,0.040881716,0.030000398,-0.010753055,-0.0076079606,0.022310248,-0.024079164,-0.004367407,-0.0006039799,-0.013943503,-0.00021913784,0.0059021567,-0.009520135,0.0065282686,0.027379384,0.013251405,-0.03208835,-0.013781964,0.0070615383,-0.010747686,-0.0037631076,0.017765164,-0.023321433,-0.013078797,-0.009235497,0.027476165,0.012650834,-0.014613547,-0.016249832,0.019806799,0.009845038,-0.035832863,-0.00085921143,-0.005118012,-0.001031114,0.022850404,0.014739542,0.0058650733,0.025390359,0.014874203,-0.010774352,0.0030388865,0.017833022,-0.014841102,0.0053941673,0.019609245,-0.00017569364,-0.02928858,0.0069616297,-0.015602584,0.01499273,-0.038538285,0.020519577,0.012290519,0.027782772,-0.015130176,0.022416927,0.0132863615,0.018954584,-0.0023824784,-0.011863639,0.006821089,-0.0113111185,0.01025067,0.0062077846,-0.017220724,0.004323781,-0.02211504,0.018726818,-0.008349499,-0.005821762,-0.016078996,-0.006547508,0.0078096646,-0.002767937,-0.0012173108,-0.02620912,-0.02372919,-0.0039220913,-0.0135501465,-0.0061602527,-0.005603054,0.0007307995,-0.007134945,0.0022706355,-0.0031562448,0.008217259,-0.013253295,0.012877455,-0.0037192656,-0.0017097738,0.0013401912,0.011397704,0.0012760914,-0.014875886,0.0016255586,0.004800461,-0.020582512,0.0067332773,-0.00055217755,0.009563449,-0.004950095,0.0025198301,0.012183637,0.010767371,0.0031992502,0.011143452,-0.0014394823,0.0074632866,0.0037204323,0.004852762,-0.020116387,0.020351797,-0.0030580182,-0.00035137715,0.00649178,-0.0046958416,0.015299702,-0.0034538624,-0.01271443,0.0043128002,0.0029312456,0.023143621,-0.005553075,-0.005774215,0.0003947416,-0.0016237778,-0.0048095006,-0.008617076,0.00023247254,0.020180771,0.007432313,-0.020195879,0.014983031,-0.002164847,0.0056846044,0.0074584577,0.016488068,-0.016355835,-0.013583384,0.008296721,-0.020172356,-0.007656135,-0.0023606373,0.0012944881,-0.0018263805,0.0057741883,0.011673916,0.0019063395,-0.019173998,0.029466467,-0.003734957,-0.024274612,-0.0042297966,0.014961954,0.010824224,0.0047925278,0.01668973,-0.019801715,-0.000382544,0.00385106,0.0006258549,-0.0018812408,0.0044154692,-0.0005526833,-0.0029437672,0.00091046287,0.02081227,-0.01603933,-0.0033314056,0.0051620943,0.0011090841,-0.000872003,-0.01784462,0.005136398,0.01106155,-0.00888455,-0.0006540609,0.0011786459,0.0152759,0.007526329,-0.0080245575,-0.009180586,0.0059683775,0.008634112,-0.011784552,0.021255383,-0.0015581135,0.0031878275,0.008590711,0.008341197,-0.008469533,-0.007924834,-0.00021194365,0.018655023,-0.0040760958,-0.01895797,0.006266274,-0.019619403,0.0074884645,0.025085062,-0.01010235,-0.006495351,-0.003193707,-0.005947469,0.0021657918,-0.015362964,0.014925509,0.012300158,-0.004137495,-0.01053274,-0.008415126,0.011276182,-0.002009837,-0.0075585307,0.009820063,0.012737063,0.017880028,-0.0033203498,0.0012713968,0.0067602103,0.0062749092,-0.007824012,-0.010392552,-0.004825088,-0.008128395,-0.00031710826,-0.012277769,0.0038127797,0.0005152906,-0.012951311,0.0027106153,0.006615929,-0.0010011542,0.0005158733,-0.0051278104,-0.008632044,-0.03145035,-0.017757079,0.0027545986,-0.011458783,0.02676638,-0.021672986,-0.009461368,0.0044595585,0.009696463,0.0040580523,-0.01386437,0.0056468416,-0.0018930306,0.010641919,-0.014071917,0.011735413,-0.0032340747,-0.0049222633,0.0009877253,0.016357299,0.0048127435,0.11039485,0.03003262,-0.008728417,0.018115228,-0.024787469,0.02232028,0.014713874,-0.0118922405,0.015877945,-0.0014350414,-0.01940736,0.0032682049,3.5989833e-05,-0.01633349,-0.0007184768,-0.0017766752,-0.013180512,0.014628262,0.0047219386,0.000978868,-0.021024704,0.020483539,-0.008986933,-0.008252266,-0.0031134607,-0.0069610854,-0.005427857,0.00879154,-0.014565024,0.018435424,-0.0008857101,0.013515932,-0.003618422,-0.015098822,-0.015193135,0.0069456324,-0.006203309,0.0023310478,-0.0048507927,0.018357106,-0.0044714366,0.01094543,0.014861643,0.017309241,0.003922159,0.021972679,-0.010907324,0.017114878,0.00020740386,-0.0177686,0.0016695693,-0.003842188,0.0070798057,0.00848966,-0.025672948,-0.009640644,-0.0065670554,0.004870423,0.006515738,0.0054607624,-0.004048751,0.004092698,-0.018581571,-0.020512505,0.014633018,-0.020665307,0.006589931,-0.01957887,0.007912389,-0.0040441123,-0.0069285454,-0.015514837,-0.021643396,0.017671155,0.02322957,0.0025620286,0.0068003526,0.005920629,-0.0024359701,-0.009552884,0.005061508,-0.0046728957,-0.016320195,-0.00033915805,-0.0057301787,-0.0035599738,-0.0026775966,-0.00942462,0.0041574473,0.007977016,0.006446753,-0.0094493255,0.0026420094,0.015321881,-0.0021059823,0.009497748,0.030295078,0.013081367,-0.014697648,-0.00514077,-0.00864057,-0.004860896,-0.011721522,0.0017179807,0.0312613,-0.009027898,0.005290315,-0.012326899,0.008919319,-0.0034259332,-0.007084302,-0.009249442,0.008442191,0.0018480971,-0.0031604092,0.010540825,-0.0051849764,0.00505307,-0.019285124,0.0020701683,0.011699092,-0.008816916,-0.009567487,0.004137028,0.012698917,0.0031931708,-0.011703203,-0.0062876535,0.016659591,0.0036055155,-0.0034883246,-0.013810128,0.015085066,0.013299477,-0.0008697111,0.0038365864,-0.0034052043,-0.0040186727,-0.0007323529,0.008181626,-0.006515654,-0.010184385,-0.011490919,0.0005349838,0.01066554,0.0061509833,0.016488623,0.009298133,0.0048958478,-0.0016768568,0.0076193544,-0.0031978972,0.01383162,0.0095677255,-0.00844488,-0.007368737,0.0053184982,-0.0038665335,0.0023544654,0.016096685,-0.010993799,0.0031759362,-0.001408286,-0.0026363614,0.014241071,-0.024116537,-0.0086023165,0.028745519,-0.011558022,0.01496141,0.009114321,-0.006500797,0.00067172665,-0.0019697866,0.009341957,0.0033040938,0.005170503,-0.02232051,-0.0014043755,-0.008543113,-0.0024861447,0.015932824,-0.008635829,-0.0010173058,-0.008899393,-0.013029844,0.0048656645,-0.004865729,0.013346001,0.0030900594,0.0088712005,-0.0069516543,0.015617967,0.0007802092,0.019750971,0.008050343,-0.00018676574,-0.012103545,-0.00054684596,0.014070032,-0.011955942,-0.0131158605,0.0044495105,-0.01670831,0.0025311909,0.001986247,-0.011392185,-0.0012160245,-0.018662602,0.0038156284,-0.02441729,-0.026121926,0.01025995,-0.004004252,0.014321575,-0.0024253214,-0.007372672,-0.02203159,-0.009730698,-0.021911323,-0.0037453724,-0.00531893,0.005293711,0.0058398237,0.01686377,-0.0058311583,0.007971708,0.0047818576,0.015566943,0.010780606,-0.0071122395,0.004409537,0.0035493765,0.01406681,-0.012346592,0.0044312878,-0.0018652208,-0.015611584,-0.0023001449,-0.010637264,-0.0036082503,-0.00018174609,0.008180827,-0.015409036,0.00768101,-0.0029012414,-0.0026624824,0.021092754,-0.000526204,-0.00033935223,0.011689713,0.0063029453,-0.0031129818,0.010986604,-0.001712534,-0.0014466627,0.0024187109,-0.0448303,0.007541539,0.0049916883,0.024464667,0.011405893,-0.006222194,-0.00978508,0.0009356096,-0.010184956,0.008201507,0.0039364253,-0.016334068,-0.0050142985,0.0059326016,-0.006721686,-0.0056924773,0.0027101254,0.007995224,-0.009520379,0.0142883165,-0.009458087,-0.012915815,-0.017148245,-0.0072744996,-0.018322064,-0.0016596648,-0.011378922,0.005423645,0.005661551,0.00290826,0.007894901,-4.2950916e-05,0.0052521494,-0.0021087183,-0.010275266,0.014759251,0.002377452,-0.0035603102,0.0033839492,-0.0071576172,0.027653519,-0.012897539,0.01180772,0.017084792,-0.0008943521,-0.0040737977,0.0009975951,-0.0029512856,0.023065876,0.014455833,-0.0035751683,0.020316029,0.00067645696,0.0151496185,-0.005709584,-0.017766444,0.0084740715,0.013546902,0.0022163102,-0.00063270633,0.010070036,0.004816157,-0.015547487,-0.0066180644,-0.012851744,-0.011892052,0.011406573,0.003265409,-0.0013518722,0.02895435,0.0029207235,0.0046742847,-0.0035776997,0.0053184405,-0.0034095668,0.008483796,0.0014269884,-0.0044362745,-0.013261361,-0.005416372,-0.0036904167,0.016709626,-0.0084420955,-0.014441988,-0.011791009,0.012633365,0.002552683,-0.010017044,-0.011123713,0.007920903,0.017984934,-0.0046712765,-0.0004979429,-0.012995436,-0.005748387,0.024863498,-0.0068778433,0.021660794,0.0057592704,0.007304419,-0.011056821,0.007944099,0.0016906022,0.0055811363,-0.02578689,0.013874221,0.0008725569,0.022444068,-0.012393383,-0.0005128728,-0.001278338,-0.006723008,0.0102189295,-0.019042408,-0.005928727,-0.007800886,0.009232919,-0.001259273,-0.017018951,0.007829388,-0.018879084,0.003386597,-0.004515087,0.0007943479,0.007330735,-0.0070171445,-0.003528825,-0.0028391937,0.0080664605,-0.015124248,0.00034095597,0.006496517,0.0005478326,0.0036621147,-0.0048147026,-0.007352544,0.027976163,-0.013090438,-0.003254871,0.016653078,0.0146565735,0.004442426,0.008765014,-0.0076832203,-0.00062021904,0.0018859981,0.011973213,-0.0031366053,-0.0045361775,0.006442301,-0.006470293,0.002660394,0.0020320583,0.01411796,-0.0075608897,0.016729744,0.012169446,-0.0018315932,0.0138159515,-0.017627744,0.029612023,0.0036914835,0.0068753636,-0.009685805,0.014198283,0.0095247645,-0.023197023,-0.011546711,-0.002687326,0.0051275506,0.014235104,0.011946413,0.0014189805,0.009660523,0.014431183,-0.0025398768,-0.006780051,0.007860579,-0.01661361,-0.010199738,-0.0044624824,-0.0097934995,-0.0034914007,0.0135179,0.02161141,0.009049132,-0.02165906,0.002657097,0.015462264,0.0010318583,0.013361444,0.0010851981,-0.012521094,-0.013444065,-0.017948452,-0.00071530585,0.017687695,-0.0064456705,0.00096569245,0.0041337153,-0.01096141,-0.005556827,0.013379289,0.003899963,0.0045311046,-0.09755271,-0.0036899492,0.010607512,0.02222146,0.011829314,0.014555172,-0.0046013007,0.005151913,-0.0059745107,0.0043088947,-0.018238872,0.0043680943,0.010908126,-0.023408262,-0.00052889023,-0.00369882,-0.011357951,-0.0111756325,-0.013561147,-0.0010107666,0.01279067,-0.0072860755,-0.003089591,9.5978336e-05,0.002638684,0.0080964295,-0.016390322,-0.014721804,0.006490523,-0.02033083,0.008451157,-0.008578151,0.014248869,0.010543943,-0.003301309,0.009995005,-0.0036745048,0.00028674284,-0.12972529,0.008885613,-0.0032703332,0.008703079,-0.002784597,0.0017341458,0.003134572,0.0014867012,0.004848889,0.0017156255,-0.0037390995,0.003919197,-0.010438998,0.0022757952,0.016075935,-0.0052819597,-0.0031948916,0.0006549318,0.0007848104,0.014006432,0.0087486105,-0.00036114122,0.011549874,0.012439036,0.013641233,0.0048268377,-0.006474327,0.013374679,-1.0628277e-05,-0.014018646,0.009579276,0.018835463,-0.008755803,0.013142213,-0.005683398,-0.0026203117,-0.00083836773,-0.0020994889,-0.014972957,-1.2591108e-05,0.020769885,0.001098133,0.005316789,-0.011139842,0.00876406,-0.012465453,-0.00850067,0.0065677753,0.010430936,0.007988798,-0.0014995624,-0.0028775334,-0.016434308,-0.00055152376,-0.0019125736,0.0065652053,-0.008612994,0.020449713,-0.013122666,0.016031392,-0.0070856437,-0.010465065,0.016093401,-0.0064904965,-0.0006021207,0.014528692,0.012947257,0.008060539,0.0090980455,0.028640682,-0.0038297442,0.0153531525,-0.0024592185,-0.0035831411,0.014850625,-0.013577666,0.010226888,0.012935398,-0.02130003,0.015336608,0.008784083,0.003687258,-0.0011395768,0.0037779321,0.028289102,-0.01249597,-0.014935108,-0.007928732,-0.0063208193,-0.055996202,-0.005427795,-0.0033886712,0.011899573,0.008761835,-0.006876379,0.0014930748,0.008218162,-0.007298988,0.0064202817,-0.00064296497,0.0045980387,0.0031326225,-0.032134846,0.008279949,-0.0034820617,0.008990346,-0.018822443,-0.020438295,0.0025151926,-0.010373292,-0.032763917,0.0035699923,0.021171486,0.002756228,0.0015826564,0.009782074,0.0014621865,-0.0073030237,-0.026569054,0.010400798,0.005954845,-0.010949089,0.0054805013,-0.015120302,0.007688072,0.0049838186,0.013080142,0.020401582,-0.0005857388,0.017861612,-0.014869531,0.015551941,0.0038521634,-0.012153096,0.0020398442,0.005845736,0.01349029,0.010258724,0.020662343,0.006095448,0.0068349405,0.003556252,0.005514411,0.01040777,-0.0015479979,-0.005808994,-0.000645709,0.015903205,-0.004496281,0.022785962,-0.027401472,0.008569115,0.004853293,-0.015391928,0.010806074,-0.01821695,0.0098025575,-0.008920976,0.0020963405,-0.0063461326,-0.0072555714,-0.0006891913,0.014666571,0.0050221756,-0.0048322114,0.01561501,-0.010872025,-0.0046626376,0.010308407,0.0084533105,-0.0037634543,0.0027623998,0.007264336,0.012050819,-0.0118376855,0.0027730123,0.0069026393,0.00046849443,0.01226499,0.0032725653,-0.035228338,-0.016680587,-0.019056141,-0.032933593,0.041536696,-0.017836466,0.012102101,-0.00843412,-0.039061207,-0.023792356,-0.00062861445,-0.003136361,0.0040960447,-0.0023966169,-0.01441112,0.008970819,-0.0024859786,-0.006851283,0.0053021987,0.011690752,-0.014427654,-0.0055833897,0.013733166,-0.16749765,-0.0021438454,-0.010078293,0.013002491,0.014432043,0.018337492,-0.009082906,0.017670669,0.0029710254,-0.0048870877,0.0076245978,-0.016092394,0.018417953,-0.01584452,0.0016747762,-0.009715965,-0.006543764,0.010998027,0.007549333,0.004409446,-0.011941511,0.0046886834,0.0010110539,0.012635729,-0.012461126,0.009043895,0.0071946983,0.013976359,-0.029363383,-0.018664809,-0.020420255,-0.009224997,0.005021778,0.009128745,-0.00904132,-0.007405199,-0.0014802206,-0.013229469,-0.0012483149,0.028619653,-0.02738321,0.0028399846,-0.01875095,-0.004951006,-0.0029895094,0.0007374671,-0.0113222245,-0.013008762,-0.024912767,0.012624831,0.0200848,-0.01804544,0.034635983,-0.0013380956,0.0028308337,-0.025277255,0.01182345,-0.01998984,-0.014537577,0.0035071035,0.01002152,-0.014049986,0.014560792,-0.00998979,0.024103299,-0.004976016,-0.013927385,0.1662844,0.011749479,-0.0038539325,-0.024234032,-0.005189594,0.035655875,-0.0047853305,-0.013709071,-0.020096995,-0.0046605016,-0.01511136,0.008598274,-0.013428946,0.010538132,-0.03144135,-0.02449546,-0.015729217,0.008355939,-0.0068997582,-0.010351101,0.0015180977,-0.018537756,0.0025420492,0.00046582025,0.027260514,-0.007498252,0.007137709,0.0013559422,0.0081745945,0.034261603,-0.012778647,-0.018678252,-0.007891584,-0.0072882567,0.007112412,-0.006277535,0.0033354666,0.009441375,-0.0024093199,0.008501383,0.007240063,0.025565092,-0.014869256,-0.0065090703,0.007830309,0.01728707,-0.0075830515,0.0033169608,0.024836233,-0.008874147,-0.03491365,-0.013810865,-0.008645276,-0.011236913,0.0078894375,0.008528448,0.0041196425,0.008204228,0.012040397,-0.015203034,0.012744476,0.008601945,-0.03497542,-0.0032734508,0.007265979,0.0021075385,0.041878324,0.006118516,0.018397808,-0.10528858,-1.1908805e-05,-0.014718429,-0.026164318,0.0058325697,0.0036419996,0.004421018,0.003577995,-0.012414782,-0.0043667615,0.0005888598,0.0114649795,-0.004704311,-0.0039734636,0.00458387,0.02004475,-0.0040026144,-0.0056668683,0.027335722,-0.005464284,-0.008559875,-0.00010097487,-0.00834148,-0.018955082,0.012969666,0.011501669,-0.026717277,0.002724852,-0.008826203,0.012977981,0.0065220864,0.0017576003,-0.008208442,0.012404308,-0.0020924474,-0.024829691,0.0157799,0.011360652,0.014390241,-0.021318875,0.010478569,-0.00773006,0.011206733,0.0020946946,0.012275973,-0.0033488125,0.0068703997,-0.0069602355,0.004629673,-0.017715707,-0.00010527318,-0.025232634,-0.00028993396,-0.00038746354,-0.011081643,0.01367327,0.0061370316,-0.025157562,0.008250373,-0.026794374,0.014939952,0.0012608169,0.019741297,0.009448604,0.0003051047,0.0007451582,-0.0027427285,-0.020028064,0.02155551,-0.002996802,-0.0170122,-0.006922671,-0.0022256311,0.01861625,0.0076913405,-0.00017911656,-0.0005312498,0.01012664,-0.019298926,-0.010968111,0.0015832438,-0.02013229,0.008539248,-0.0020238517,0.05374033,-0.020487059,-0.005537927,-0.0042949067,-0.011298203,-0.0029007467,-0.00896062,0.010112949,-0.010292758,0.0029784373,-0.0032782478,-0.014980645,0.009070186,0.006580477,-0.001032301,0.0048238374,0.0040229456,-0.00081407663,0.02823247,0.0030352073,-0.011891989,0.0021939592,-0.014231601,0.0048403805,-0.024167486,0.00012804724,-0.019385448,-0.008946018,-0.044353433,-0.005869614,-0.004278433,0.016766727,0.005293235,-0.0020931603,0.011259658,0.0006315393,0.013029193,-0.0040903143,-0.012408185,-0.007895307,0.0019430303,-0.003357815,-0.00090946234,0.005796652,0.010647413,0.0030306883,-0.0019966685,-0.0038498782,0.034637492,-0.011329302,0.03344837,0.010174032,0.01887929,0.010659916,0.0014590776,0.012226998,-0.018171592,-0.013639683,-0.02068156,-0.0046135695,-0.0055278367,0.009326562,0.037540697,0.015114068,-0.0028354197,-0.007540643,0.016028987,-0.0026517734,-0.0018842478,0.0026239888,0.0040234737,0.0071621253,0.012086473,-0.002447265,-0.009082522,-0.014086644,0.0038800754,-0.0034362758,-0.030678218,0.012323305,0.007664021,-0.004212001,-0.007272019,0.008801714,-0.013814413,0.0035900914,-0.005858218,0.008843173,-0.002613225,-0.0072968863,0.0016959893,-0.015310688,0.012631042,-0.0016148952,-0.016527306,-0.06843101,-0.0008296868,-0.013820557,0.0035586616,0.009498525,0.00865636,-0.0071675535,0.0018867555,-0.027771465,-0.0033780474,0.0062085097,-0.0004528447,0.0076033454,0.037955917,-0.0133862775,0.018778259,-0.0033398964,-0.009720748,-0.0041145966,-0.009841689,0.01859997,0.014437804,-0.0073027527,-0.032415114,-0.0071538,-0.0044061295,0.0007688846,-0.012132784,-0.018644808,-0.022260688,0.0064953887,-0.016640408,0.0015790225,-0.012806415,0.008775337,-0.030601483,-0.013713727,-0.0027039903,-0.0052086944,-0.0036001126,0.008695974,0.010082355,-0.08341254,0.0010648122,0.025095368,-0.022960572,0.0020883458,-0.013199516,0.010742192,0.0066219135,0.008757444,-0.016134894,0.0137976585,0.008036696,-0.006953348,-0.0066464785,0.004388807,0.000859892,-0.019258477,-0.012617112,-0.0051401625,-0.013466455,-0.0045808908,0.005148971,0.0031955328,0.019341081,-0.0049390164,0.0320505,0.002530072,0.027553484,0.0064655393,-0.031413432,-0.016032338,-0.0031971151,-2.4116938e-05,0.011148015,0.011975097,-0.009142266,0.005945728,0.0035139474,-0.009426431,0.027067954,-0.0013479306,0.014834047,0.034255926,-0.0033245387,-0.008901981,-0.10271631,-0.00824468,-0.015650673,-0.0038621407,-0.009885249,-0.0025140787,0.002515457,0.031674724,-0.0126205925,-0.018834066,-0.0007314087,-0.016906524,0.011560549,-0.010448599,-0.019604156,-0.020077249,0.008753794,-0.012735099,0.0007565976,0.014295292,0.0050799884,-0.0127422735,0.0045606117,0.013978309,0.008010785,-0.03087256,-0.0045722183,-0.016568976,0.004514057,0.0012284452,0.014719918,0.014533834,0.004833668,0.0069489554,0.01630498,0.013362873,0.0028234567,-0.005581769,0.005512285,-0.017778248,-0.007186208,0.00952093,0.008383703,0.0066894926,-0.01752412,0.018701661,-0.013717225,-0.0051841578,-0.017526077,-0.0082491655,0.011523151,0.015123223,0.0043514906,0.0034799722,0.016689515,0.0044879164,-0.0014679739,-0.00017954812,0.00024832573,0.014399582,-0.016208889,-0.0031605016,0.0014391596,-0.0050059548,-0.006481544,-0.0062677884,-0.0036759074,0.0024248646,-0.018767167,0.013948723,0.019196535,0.028661286,0.016792785,-0.005076884,0.001956321,0.012011463,0.004139997,0.035048544,-0.015800735,0.009502484,-0.005708079,0.0030983584,0.026897023,-0.011014837,-0.009149084,0.0043568537,-0.001620636,-0.0015343197,-0.0051409,-0.007282511,0.009555964,-0.018816529,0.0027642143,0.0110573815,0.0037352813,0.020692661,-0.0043588425,0.004695664,-0.00305055,-0.004697357,0.0010362688,0.0013107857,0.012202289,-0.009592932,-0.0023877812,-0.0067808796,0.0068185576,0.0025171142,-0.026141064,0.006982389,0.011764874,-0.011220009,-0.018754242,0.0040105707,0.0073481943,-0.0026724879,0.008302248,0.004342554,-0.0029732331,0.004629088,-0.003712782,-0.024792293,0.018002694,-0.02028871,0.0061503975,-0.018932603,-0.005700641,0.012527506,0.020929694,0.005191254,0.011142796,0.0077277236,0.0123148495,0.019793771,0.00044077568,-0.0015461375,-0.007882549,0.018044043,0.027048076,0.012990914,0.008073254,-0.003813656,0.0007510327,0.0068355184,-0.008246749,0.019891493,0.019040184,0.010798863,0.006090745,-0.0044235033,0.02105802,0.0036396685,0.019779593,-0.0094299,0.0035355662,0.0074700587,0.013086547,-0.018682668,-0.004448687,0.009389359,-0.0064206216,0.025722533,0.0033918878,0.0029862379,0.02534567,-0.0060957847,-0.00083951594,-0.012766209,0.012698586,0.00019189302,0.03478498,-0.021951927,-0.01778402,-0.008416719,0.04183905,-0.013351013,-0.0071213087,0.0064656376,0.0035693988,0.0006677898,0.0041598952,-0.013306137,-0.0012407602,-0.00687432,-0.017541979,0.0036639222,0.0037567606,-0.00029285348,0.006233935,0.0033998531,0.012727136,0.013088276,0.009604603,-0.0051743547,-0.0024199467,-0.019245556,-0.0149111375,0.0014079575,0.012027144,0.028675709,-0.011475328,0.004994821,-0.0058140103,0.018048668,-0.0068112025,-0.018446065,-0.045696985,-0.003260075,-0.020381212,0.017802397,-0.0008177105,0.00020097347,0.0028126028,0.012516829,-0.007222532,0.013578438,-0.010850345,-0.010166798,0.009069999,0.027653364,0.0072493106,0.03248306,-0.0074856426,-0.008077608,0.004355308,0.002858823,0.0029512204,-0.017376816,0.0072576064,-0.0021828949,0.010323166,-0.01018012,-0.009644143,0.02701914,0.006718001,0.0076207537,-0.022260206,0.0011197274,0.0069108885,0.006758629,0.018045446,-0.0010511883,0.010312221,0.028408388,-0.025209093,-0.021677595,-0.018169984,-0.014632276,0.0037587802,0.020004556,0.0040976037,0.008069737,0.0020606257,-0.015649434,-0.023463447,-0.013919907,0.015775181,0.010368923,0.012305393,-0.012526874,0.009556466,0.013496027,-0.019292977,-0.007895041,-0.029894417,-0.029679434,-0.005580984,0.0009410994,-0.0059003686,-0.0012650563,0.012574975,-0.008628915,-0.0021962244,0.010280832,-0.02381256,0.0111920135,-0.0018979287,-0.014383937,-0.004059842,0.021034595,-0.01341757,0.0009089054,0.029491225,-0.012001206,0.0094368,0.010042619,-0.01571139,0.001669437,0.010799621,-0.014019532,0.019277021,-0.022622656,0.01795896,0.00039388146,-0.013580054,0.005651456,-0.005824005,-0.007483292,-0.015846051,-0.013458644,0.021018574,-0.024068415,0.022918053,-0.025576856,0.008519968,-0.0068787457,0.025474526,-0.017334083,0.00011750002,0.007722391,-0.0016692154,0.009389615,-0.018044673,0.009221743,-0.015184709,0.012277023,-0.0068401964,0.0033095381,0.002295075,-0.004601696,-0.010255877,-0.000337349,-0.0016691508,-0.0065878085,-0.00052043505,-0.0010880822,0.014095083,-0.004278738,0.019978143,-0.0059218374,-0.009384633,-0.016195439,-0.00766057,-0.010898006,-0.0018311782,0.021598369,0.020996975,0.01534192,0.0073207743,0.017621413,-0.017415168,0.028394789,0.009946831,-0.015206419,0.019324593,-0.0031380365,-0.0029110133,-0.014798064,0.009355273,-0.0343434,-0.01436698,-0.030707795,0.014421132,0.004022769,-0.012428751,-0.0010237126,-0.002271286,-0.03410124,-0.0011382306,-0.007533252,0.009301636,0.009704792,-0.0061552688,0.01358271,0.0024348672,0.0007451982,-0.0054683667,-0.02851823,-0.023379248,0.04215261,-0.007750441,0.020904774,-0.00515347,-0.010716819,0.011954586,0.016550299,0.010260494,-0.003676405,-0.00077587884,-0.008869066,-0.0028444035,0.013661886,-0.0073528923,-0.0066096648,0.0015998194,-0.01607644,-0.0088797435,-0.003047655,-0.018903257,-0.010092713,-0.0039654523,-0.0040439446,0.023413856,-0.00487412,0.0015356163,0.0028851156,-0.008696403,-0.010137048,-0.016482014,0.027452135,0.010097428,-0.005298311,0.0050056176,-0.022470394,0.014785699,0.004766798,0.00031440184,-0.005627063,-0.026903009,0.00696614,0.012612493,-0.011990617,-0.0059089437,-7.3823794e-05,-0.030922135,0.0040105316,0.012113756,0.0015794473,-0.027251516,-0.00026582432,-0.005182038,0.012669586,-0.01998739,0.009246945,-0.005304764,0.005620928,-0.0014839876,-0.004361534,0.009677789,0.0066597844,-0.021485588,-0.00839881,0.024484986,0.0039498336,0.015218206,-0.012694326,0.005557343,-0.013429166,-0.015595507,0.024563773,0.0009981856,0.013395418,0.005107259,0.027146172,0.013928428,0.0006575174,0.0036960668,0.0033289047,-0.021932604,-0.002960227,-0.0027840666,0.0029938943,-0.01720592,-0.0075449655,0.015020189,0.00505414,0.0032458017,-0.006308669,0.025319917,0.010396495,0.0046423017,-0.0014742546,0.0033647236,-0.003868403,0.0016989295,-0.03214492,-0.0144404825,-0.02275423,-0.015325632,-0.00037166456,-0.01017338,0.010571702,-0.04747858,0.019099016,0.02768573,-0.008550902,0.01547355,-0.013902798,0.0022062396,-0.053009603,0.037595343,-0.014023251,0.0057118004,0.004112757,-0.0065737744,0.005040606,0.0012767271,-0.003174112,-0.0022984955,0.0012638881,0.014893331,-0.009716418,-0.015413578,-0.0051882085,0.0016306384,0.011181051,0.0039301645,-0.02233323,0.003152985,-0.047318038,-0.0041846563,-0.0042723482,-0.00017705653,0.011135462,-0.01206488,0.0072316476,0.012057871,0.0230505,-0.013409067,-0.019011635,-0.005983041,-0.012370696,-0.0031990954,-0.019185124,0.009205347,-0.018516414,-0.008029569,0.01632435,0.018421007,0.01618739,8.58784e-05,-0.02255181,0.0039133453,-0.0068446114,0.01720336,-5.125145e-05,-0.028163835,0.017373947,-0.010484731,-0.005180718,0.008956356,0.017358307,-0.014731792,0.011428968,0.00464865,-0.017066495,0.008691077,-0.008823492,-0.009671179,-0.037036754,-0.013072102,-0.017128233,0.009300634,-0.0026927905,-0.0073314672,-0.016246334,-0.01512186,-0.01539227,-0.0023784502,-0.0035448128,-0.0012045963,0.00402836,0.0040649166,-0.018706292,-0.016952574,0.00039301778,0.023193719,0.011480531,0.012813913,-0.013307297,-0.0020263758,0.000367809,-0.021576721,0.0004711744,-0.038779266,0.009890915,0.008171786,0.006151366,-0.009142646,0.011853919,0.0072186836,-0.035399076,0.015917407,-0.0036714922,0.024971405,-0.030268693,-0.0057803644,0.0001251312,0.005680308,0.020221623,0.009237282,-0.021686615,-0.0064878,0.022795707,-0.0062377634,-0.019985016,0.010302359,0.018205844,0.00880146,0.015248296,-0.0050166626,-0.0126729505,0.0011098873,0.004330588,-0.005402709,-0.013373475,0.0074586035,0.005646189,0.0065654223,-0.01799065,0.0091101425,-0.006627782,0.004498172,0.008033611,-0.016756887,-0.0009077143,0.015365835,-9.962359e-05,0.022286953,-0.0062853005,-0.0065159868,0.03764979,-0.0040224977,0.0007204802,0.001581466,0.01521544,0.023539491,-0.007598533,0.00491057,-0.0062740673,0.013503887,-0.007828731,0.011966393,-0.01991847,0.0039273663,-0.01502733,0.026423903,-0.0015763391,-0.007878347,0.015782159,-0.0039127055,-0.000756215,-0.0047118682,0.012721963,0.012684501,0.0106725,0.012867868,-0.0073132934,-0.004663779,0.016107906,0.012576504,0.0056214547,-0.0020640679,0.004033956,0.008849814,-0.004961855,-0.0057618646,-0.0016244914,0.011092366,-0.009820589,0.0177212,-0.007451288,0.02773639,-0.012003401,-0.010774206,-0.0020263135,0.010881843,0.002863487,0.014404071,0.004900112,-0.007014497,-0.018819742,0.003350845,-0.007081854,0.001067163,0.0024610367,-0.0081815,-0.0124379005,0.007483979,-0.0024512322,0.014625918,0.0027034252,-0.013872154,-0.02197288,0.0020575381,0.0005485254,0.002475653,0.033806097,0.021433448,-0.005435709,-0.031057669,0.016873397,-0.011822197,0.014742043,0.010562578,0.005969131,0.1773297,0.113845244,-9.332696e-05,0.016442273,0.008737337,0.007336363,-0.034012035,0.0017500443,-0.0025468857,-0.022264916,0.0028465441,-0.0040024817,0.004950423,0.013786514,0.0016502902,0.021404013,0.015529168,0.006582767,-0.0029004826,0.0030803378,-0.031574506,0.008105987,-0.0128370365,-0.010843779,-0.024803106,-0.013038057,0.012198776,0.019285178,0.012811193,0.022619255,-0.012021063,0.012660929,-0.0075681624,-0.00494033,-0.015400945,-0.042856764,-0.013779326,0.026801186,0.0024732882,-0.015001155,-0.015597237,0.015416333,0.006270575,-0.013720115,0.012560142,0.002219239,-0.003545906,-0.012383694,0.0066669434,0.0017504542,-0.006186736,-0.004862384,0.0030236694,0.00968521,0.0009911323,-0.00726141,0.016692312,0.01799741,-0.0042346544,0.018976944,0.017298898,-0.01060586,0.0034897309,-0.0058284053,0.0043608034,-0.0065691355,-0.016853388,-0.0029249236,0.0034177108,0.00038014422,-0.0057352665,0.0053462447,0.0068145045,0.0142960055,-0.0020812878,-0.0062306863,0.022280952,-0.009824015,-0.01124867,-0.012567173,-0.011312861,-0.026872188,0.012896263,0.024846904,0.011043672,0.0034609544,-0.007500475,0.015787924,0.049181476,0.0038872967,0.0112719,-0.033368353,-0.015580778,0.005157509,0.011823738,0.011728786,-0.010462218,-0.00069162826,0.005604827,-0.011291958,0.006853506,0.009350392,0.010967055,0.012861726,0.030739676,0.02939075,0.013764444,0.0011234299,-0.016097097,0.0028426067,0.022976724,0.0038121645,0.016619172,-0.00367518,0.005411874,-0.009225685,0.0035635259,0.040960245,-0.092054315,-0.008025161,0.008333228,0.018922098,0.0085616885,0.018719142,0.040586207,-0.00843271,0.003220665,-0.024483414,0.014162832,-0.0058833174,-0.00013950576,-0.01568864,-0.008060219,-0.011629837,0.014535556,-0.015884625,-0.010646402,0.0013394493,-0.024683844,0.012819817,0.012145246,0.014596816,0.020794278,0.029403849,-0.010428875,0.01780004,0.02317093,0.006978889,0.0003581888,0.0043261205,-0.01912145,-0.0032897375,0.01626069,-0.0026187045,0.012940267,0.0139675075,0.017178427,-0.0005929508,-0.010060279,-0.0428197,-0.011118475,-0.007814241,0.013370034,-0.02662087,-0.0045138993,-0.009305856,-0.009237363,0.004330161,0.015279561,-0.015886929,-0.003531595,-0.00023287938,-0.005595964,-0.019474734,-0.020282438,0.002625266,-0.011607338,-0.0016596147,-0.019116526,0.0017555382,-0.0077925376,-0.009054776,0.016804367,-0.0043021534,-0.020611601,-0.012034903,0.01323604,-0.0015022934,-0.02073444,-0.0017295092,-0.01601437,0.0026783505,-0.001839543,-0.0013708645,-0.021488875,-0.013741207,-0.01737623,0.021892056,-0.012300746,-0.012787635,0.0048709386,0.1312977,-0.00133863,-0.0037779238,-0.014400146,-0.00039137888,-0.012663594,-0.0015205356,0.02591196,0.026031423,0.012859835,0.02812452,0.007397846,-0.0045147766,-0.011167727,-0.00083657907,-0.003628111,0.0011316158,-0.010650341,0.025615044,0.0019324328,-0.01690158,0.007229057,0.010796329,-0.018334381,-0.020220062,0.016653888,-0.009754982,0.007189284,0.00025567386,-0.016758807,-0.0144973295,-0.010102666,0.009151932,0.0050154794,-0.015451871,0.02103033,-0.0090001775,-0.010146559,0.0041625756,-0.0061408016,0.006295393,-0.003403215,-0.0029886141,0.007692653,-0.06558323,0.21367766,0.0028912982,0.0061977264,-0.021757452,0.0011868172,-0.0024552664,0.00370726,0.013559514,-0.015808025,0.003321343,0.026308518,0.011239905,-0.009697538,-0.00528445,-0.0022222262,-0.00471973,0.009361234,-0.0055269566,0.0019536212,0.014650186,0.023865335,-0.0117664235,0.0026277856,0.021775503,-0.003396467,0.011111012,0.014293924,0.008051876,-0.0031788726,-0.005098375,0.01288105,-0.0034072502,0.00086974166,-0.0068183932,-0.02508864,0.015526658,0.019416055,-0.00076813396,0.0045450716,0.00021134652,0.007861444,0.0089305155,0.0021503912,0.005613185,-0.005042762,0.00064181624,-0.014077225,0.0036078903,0.0133195175,-0.00054637186,0.026770603,0.01179424,0.011000631,-0.005393932,-0.0142260855,0.011162025,-0.00026437672,0.015516228,-0.0136041725,0.002757943,-0.009476731,-0.0007048866,0.007595241,-0.006671955,0.02726365,0.0039162003,-0.025196847]	f	1998-06-29	Male
ab6fec67-eec0-468d-b59f-6c9de76a1537	\N	jatinder kumar	jatinderkumar@gmail.com	9876545678	Punjab	Ludhiana	Software Development	Full Stack Developer	["IT / SaaS", "HealthCare", "Supply Chain"]	Day Shift	Fresher	500000	Indeed	professional journey	/resumes/guest_4a5c52e4/02285b90f36e46e3a6dab5dca27ef857.pdf				pending	2026-05-30 10:19:18.252069	2026-05-30 10:19:18.252081	[0.010224547,0.0058966447,0.019768968,-0.05221004,-0.014630603,0.034888156,0.010245078,-0.010890378,-0.0054987,-0.01262198,-0.015748939,-0.010982569,-0.009575732,0.041728366,0.108614616,-0.0022751458,-0.010952638,0.020467885,0.014740016,0.0080305,-0.011331049,0.0142293135,-0.012254941,-0.040395424,-0.021121213,-0.019730465,0.047209714,0.014998026,0.034456346,-0.0011418429,-0.010288234,-0.0014282409,-0.0028306956,0.030151574,-0.01237285,-0.0012372885,0.01788776,-0.01973184,-0.009280928,0.027274773,0.01542774,0.009526974,-0.023659889,-0.013690962,-0.014183605,0.0035660355,-0.0032648442,0.016465217,0.013299454,0.021091772,0.0037805946,-0.0071808603,-0.03948666,-0.17577171,-0.008383966,0.017302511,0.016105574,-0.023089925,0.00260755,-0.022306275,-0.0017681447,0.026985116,-0.03779756,0.026848301,0.010209442,-0.017247094,0.021793501,-0.0053629857,-0.0014673214,-0.013164451,0.026295325,0.012625406,-0.029118968,-0.010354986,-0.00858066,-0.021370726,0.019999953,-0.010195699,0.0060935635,-0.0034498968,-0.020414403,-0.013262305,0.0053668735,-4.9846483e-05,0.025938978,-0.021583827,0.012969808,0.0051055704,0.0060863486,-0.01135237,-0.009313176,0.012343473,0.005264845,0.0080860825,-0.011750793,-0.0011169775,0.01154809,0.015996834,0.013137976,-0.0021383658,-0.0060203113,-0.0043132636,0.023340847,0.0008373319,0.019851582,0.020493697,0.0118322205,-0.019410174,-0.024950525,0.0153595265,0.028081847,-0.019499125,-0.0018612941,0.04207161,0.017285042,-0.17072675,0.0088911615,0.00031187595,0.0050352905,0.005833812,0.0024547535,0.027227802,-0.0061139525,0.016902298,-0.016053956,-0.0111423405,0.021621706,-0.008744048,-0.019147882,-0.0134556405,-0.018841535,-0.020771984,0.011202035,-0.017276322,0.027213037,-0.0043830127,0.027618207,-0.015119491,-0.01587293,-0.014440285,-0.004788045,0.024928143,0.018186128,0.021346686,-0.024625828,-0.00968565,0.0054194466,-0.0017220108,0.0048391283,-0.0105912415,-0.012168701,-0.007993753,0.0049193925,-0.020062484,0.012934984,-0.03961956,0.020502986,0.0031267565,-0.0080973655,-0.014525126,-0.012333413,-0.008834659,0.019858696,0.005804652,-0.0064418404,-0.005737406,-0.042653546,0.008408303,0.027286341,-0.004419418,-0.009495721,0.0181446,-0.028398203,0.013943404,-0.0039099334,-0.03327272,-0.00525567,0.016264837,0.0050885817,-0.040650174,0.012652326,-0.012393957,-0.015475188,0.0053890226,0.009564495,-0.005533393,-0.029545117,0.018622043,-0.004081172,-0.012455976,0.010324995,-0.023344032,-0.03135175,0.028517218,0.013438465,-0.0095697185,0.008292982,-0.008567641,0.015144441,-0.007778523,0.00041933608,-0.0035608285,-0.0038032525,0.010517399,0.0028663208,-0.0042255023,-0.017131617,0.009278213,0.0027558983,0.0063095614,-0.009788888,0.018049404,0.04283249,-0.016561309,0.019058684,-0.0095916465,0.02263832,-0.009587777,-0.016495822,-0.0026954263,0.01342838,-0.013596967,0.0070925183,0.028082864,-0.014664569,0.013807321,-0.00040901641,0.027819904,-0.005427661,-0.00775214,0.002471649,0.0005335989,-0.011973167,-0.00638096,0.027110063,-0.042591847,0.00546693,0.024267795,-0.0075258743,0.010735368,0.011845599,-0.013759263,-0.009554457,0.009748121,0.059822995,0.024325728,-0.016318554,-0.012794181,-0.009581077,-0.010910608,-0.02216911,-0.027468147,-0.0021951732,-0.0014539622,-0.0018000008,0.005160469,0.006625297,-0.0014715146,-0.00965139,-0.0072114714,-0.020604452,0.0071547376,-0.035519175,-0.023755495,-0.017680965,0.008231752,0.005768015,-0.00083533773,-0.0049831895,-0.00043290184,0.015055953,0.027766764,0.023711687,-0.0035615345,0.012780714,-0.00645017,-0.063664645,0.005512873,0.0018226446,-0.023964737,0.015307051,-0.0028563763,-0.024564816,-0.010046281,0.0074165063,-0.0021210273,0.017762259,-0.021169001,0.01032304,-0.0053047393,-9.622473e-05,-0.022326771,-0.0150275,-0.019622898,0.0013463675,-0.030918047,-0.0072931563,-0.033583038,-0.014794285,0.015472927,-0.0010907723,-0.028415617,0.025368705,0.020157425,-0.0016317623,-0.015473568,0.0108147515,0.02691556,0.007357622,-0.0044205775,0.0022804427,0.0037027097,0.005090613,-0.0029057276,-0.0009151412,-0.0023284059,0.0055617653,-0.0062492657,-0.006440977,0.0064353403,0.014904917,0.0016457918,0.016389841,0.023353912,0.01737095,0.010411539,-0.023575105,0.028253634,0.029540904,-0.017767971,-0.006237865,0.01430642,0.018517656,0.0061983084,-0.0011717076,0.027445033,0.03850042,0.018744921,0.0023616727,0.01404997,0.017662454,0.018344756,0.007936607,0.00044431194,0.009987155,-0.015297732,-0.034962174,-0.01714775,0.013296036,-0.03443771,-0.029976113,0.028081307,-0.036799252,-0.014200463,-0.020749578,0.019939749,0.009520005,0.004255979,0.0018655839,0.02936467,0.006588953,-0.009347241,-0.0058866693,0.0035886664,-0.0025147665,0.019807935,-0.00037138007,-0.0004734254,-0.038183294,0.0043484457,-0.0047785877,0.013704059,0.002585837,-0.031111278,0.019693797,0.03404652,-0.019039897,-0.0067174113,-0.012307979,-0.0034839327,-0.012679011,0.012069522,-0.014149079,0.016903399,0.015829029,0.008050574,0.0091853775,-0.004884194,0.0013819715,-0.003456359,-0.015289216,0.024829937,-0.022084542,0.026062723,-0.011253703,-0.016293902,0.008584981,0.003096137,-0.03345224,0.021555161,-0.006166638,0.008046306,-0.00702306,-0.015628355,-0.0013249681,0.010170132,0.009763571,-0.010586474,-0.0052861716,0.009473685,0.010564749,-0.023845272,-0.002069265,0.02264765,0.008710713,-0.0023267139,-0.004620658,0.0074186227,-0.0022957616,-0.005791824,0.016576093,0.0039042523,-0.013213492,-0.012526459,-0.016477045,-0.0017747439,-0.02113235,-0.017478429,-0.00046744532,-0.00458956,-0.014979183,-0.00068572606,0.0055618123,-0.02241458,-0.012692355,0.005415211,-0.033662204,-0.00119055,-0.013257116,-0.012178447,0.00072425796,0.014966893,0.015609349,0.0014685086,-0.00075552234,-0.0048639914,-0.021575123,-0.009676118,-0.018753938,0.011006265,0.012988112,0.013525647,0.014658217,0.0024854655,0.023922808,0.014474198,-0.001679571,-0.008199397,-0.026882473,0.0038094267,-0.016198477,-0.02036039,0.01238474,-0.0087520145,-0.0018668838,-0.02987226,-0.0008428098,0.014002135,-0.0013259016,0.0037443114,-0.008637624,0.012445333,-0.005382213,-0.020373102,-0.016160745,-0.000534901,0.029424764,-0.021993823,0.022980692,-0.01965819,0.013658416,0.028425675,-0.016949749,0.009270447,0.0084727,0.019062433,-0.01647639,0.009741838,0.02043653,0.019367745,0.012999891,0.04242375,0.02335253,-0.023973053,-0.019003574,0.01578454,0.017696228,-0.018817063,-0.007898194,0.025943898,0.008095404,-0.025598448,-0.015487416,0.009229977,-0.009097481,-0.011552805,0.026536336,-0.019029478,0.026643587,0.02152286,0.005572234,-0.017183112,0.0061492613,-0.009245558,-0.0007894441,0.004840315,-0.00030053937,-0.03226158,0.013114763,-0.024645185,-0.0034609602,-0.0017473517,-0.0036993297,0.0058117486,0.0015397473,0.016312337,0.03343962,0.02477601,0.011949829,0.0027065803,-0.0056167915,0.018438406,0.002348662,-0.006945058,-0.014700973,0.0029184618,-0.0045395186,0.0014379768,-0.000369369,0.015959918,0.0015043354,-0.017785512,-0.022980824,-0.0027969186,0.0053332313,-0.037855674,-0.0034213832,0.004407409,-0.0054127653,0.0043876315,0.0058015743,-0.0056872847,-0.025470683,-0.021372432,-0.005434111,-0.01078112,-0.031234687,0.003272882,0.003939032,-0.01591555,-0.006595103,-0.008569556,0.015969416,-0.014323956,-0.015055831,-0.015758716,0.017722847,0.0008771797,-0.010803616,0.007994289,0.030730838,0.04373266,4.850681e-05,0.01737516,-0.019052299,-0.030011516,-0.028592542,0.007816127,0.017924147,-0.0044473307,-0.008988972,-0.0029291206,-0.03313564,0.014822374,0.01827607,0.0016071392,-0.004129014,0.0125322575,0.012871165,-0.00060846284,-0.014919319,0.009196678,-0.003023749,-0.03354163,0.030795496,-0.04183104,-0.019035269,-0.0019574363,-0.008132617,-0.012997393,0.0057326294,-0.0030443827,-0.031435985,-0.0069868932,0.0057028974,-0.0015711478,0.01903244,0.022696929,0.038090628,0.00983839,0.016059361,-0.016545499,0.004856617,0.0107741915,0.011887038,0.00090544636,0.009826102,-0.026815975,0.023093164,-0.019351566,0.02526275,-0.009328195,0.01984263,-0.0153018385,-0.0019660527,-0.010090854,0.008475637,-0.062318534,-0.033561066,0.0012402671,-0.01592504,0.0057975766,0.011020755,-0.0023695477,0.011388733,0.0095726745,-0.0025789656,-0.022965323,-0.013110317,0.011168221,-0.025513522,0.0128206,0.0317077,0.032229934,0.031205172,-0.008828372,-0.017390786,0.004848355,0.0068245223,-0.007568132,0.0028615084,-0.006838519,-0.0051587857,-0.02400174,0.015727742,0.024294602,-0.011361691,0.0054925284,-0.15952681,-0.003807514,-0.010049898,-0.014386636,-0.0006139383,0.017572733,-0.014237305,-0.0062567308,-0.022918867,-0.01578369,0.020391602,-0.009930663,-0.01885441,-0.021737628,0.017576646,0.09200435,0.02102011,-0.03205954,0.0101887,0.002190049,-0.004739225,-0.022948647,-0.014086839,-0.010798251,0.005542457,-0.008391092,0.0084442375,-0.006200819,-0.006779877,0.0012856603,-0.0065590534,-0.016313408,-0.040267482,-0.004697527,0.004081085,-0.007315119,0.0055376687,0.00599293,0.0036570672,-0.039632197,0.035164442,0.033047643,-0.03734384,-0.002820375,0.0047428897,-0.006693604,-0.010783173,-0.027476525,-0.008657149,-0.0029618714,-0.02026065,-0.09480078,-0.013421373,0.025656585,0.009125563,0.0007112373,-0.01736382,-0.026353825,-0.024289446,-0.0018233877,0.009785484,-0.014616198,0.015387683,-0.007387415,-0.0001262488,0.0039718286,0.027744532,-0.009070709,-0.008205057,-0.017096266,0.013563843,-0.006649138,0.009974831,0.027080724,0.008142136,-0.012226577,-0.016732063,0.037214704,-0.012469057,-0.030415827,-0.0124106165,0.023271877,0.014536921,-0.027002664,0.0038499327,-0.0038628196,0.023611141,-0.019462327,-0.003926827,0.0048552547,0.015830556,0.017794564,-0.015035377,-0.013699694,-0.0019425381,-0.0065807886,-4.52565e-05,0.032260574,0.0067553804,-0.015573857,0.00028319983,-0.026433606,0.021130214,-0.047979657,0.0062544537,0.004958889,0.04036078,-0.0066497363,0.017642504,0.008122939,0.0035063147,-0.0033134269,-0.028298475,-0.016815383,-0.0048651565,0.010825632,0.01517983,-0.0042751287,0.0003340238,-0.01271752,0.01990394,-0.0020465623,-0.0036612463,-0.009943088,-0.0023936387,0.00019952157,-0.0065605696,0.0068524545,-0.007663342,-0.0114512015,-0.0018665408,0.011583124,-0.0054829684,0.008364531,0.0018341517,0.0052064992,0.016921936,-0.01889423,0.002336769,-0.0160566,0.014417588,-0.0070388927,-0.0057748393,-0.0030058585,0.0027520885,-0.009725306,-0.017075852,-0.0010836226,0.016872939,0.007865582,0.014476,-0.009461493,-0.006278098,0.0014770874,0.019638138,0.00841948,0.00015927911,0.006568242,0.007037019,-0.015513441,0.0004152608,0.004136842,0.019915462,-0.007309767,0.014519699,-0.0031976474,0.0029026715,0.0036426787,0.0049077505,0.018375745,0.017002024,-0.019550597,-0.010705906,0.0074579827,0.0089163575,0.0084108105,0.009569777,0.0055402997,-0.0030121098,-0.0007086232,-0.019696165,0.00092697825,0.0028289382,0.01600169,-0.012332833,0.013319849,0.0010414383,-0.0051052673,0.0021626158,0.0035801474,-0.021456731,-0.008716407,0.012892295,-0.017655518,-0.000576951,5.334515e-06,-0.008907279,-0.0027937707,0.0009169446,-1.2769551e-05,0.01802156,-0.0045880466,0.012036631,-0.0012485231,-0.014152774,0.006353214,0.02628577,0.016507437,0.012401448,0.0059615015,0.010852386,0.006744398,-0.0035284087,0.0036208762,-0.004543052,0.005332723,0.0097097205,0.0062487274,-0.011692306,-0.0021094459,-0.02177288,0.007965759,0.00816926,0.010172155,0.0066179154,-0.009000383,-0.00044843764,0.007213121,-0.003351977,-0.014852254,-0.005185586,0.024476387,0.003932803,0.0033601748,-0.006615051,0.0030880983,0.006188071,-0.0054307287,0.009961167,-0.020459257,0.0021765078,-0.00015380446,0.007336345,-0.0015843576,0.008206928,-0.0005009855,0.027551152,0.0013884727,-0.025956338,0.008349221,-0.0006577641,0.0053368965,0.01978417,-0.004054155,-0.0043950714,0.009879207,-0.0021759036,0.008346854,-0.01450126,0.0081207305,0.0046669873,-0.028011264,-0.014269005,-0.016907975,0.009361218,-0.008416808,-0.0037753668,0.021860328,0.00088153157,0.03013424,0.00028129047,-0.00043276144,0.010904481,-0.00018888993,0.003545196,-0.015231358,-0.0066730245,-0.00041788552,0.012047234,-0.005479386,-0.007414065,0.0026134322,-0.0134619055,-0.0035568334,0.0011251699,-0.01668945,0.00858377,-0.007837136,-0.011444152,-0.018964175,-0.0019354994,0.0067448686,0.003559162,0.018435575,-0.021652026,0.0047538816,-0.002566236,0.0074967914,0.010897877,-0.000720532,-0.007974501,0.005557329,0.011877102,-0.0023108488,0.015475354,-0.011939337,-0.008885096,-0.011843509,0.01622753,-0.0019708534,0.115113474,0.026210358,-0.023891257,0.020697683,-0.015657818,0.010698731,0.011799674,-0.015824946,0.01695801,-0.0032676654,-0.01965254,-0.008175927,0.010100292,-0.007409941,-0.0068267616,-0.009650028,-0.006611894,0.009458945,0.00286634,0.0074767424,-0.023516864,0.011724229,-0.0090406975,0.0030706618,0.0018772978,-0.014543803,0.0072269193,-0.0025558167,0.006605294,0.019453466,-0.0034553388,0.018393643,-0.012817777,-0.0058041913,-0.018585393,-0.01541491,-0.0039431085,-0.001613281,-0.0032280437,0.021801453,-0.0025653294,0.0034002834,0.0084987385,0.0063193277,-0.0079724165,0.02463644,-0.009619747,0.00047802244,-0.013443128,-0.01645019,-0.006200027,-0.0059237047,-0.00062544295,-0.005643769,-0.0264213,-0.007929175,-0.011835498,0.019998122,-0.0055808793,0.005315159,-0.022449844,0.0067165624,-0.008149256,-0.025250662,-0.0034095794,-0.024914615,-0.0058787554,-0.014278419,0.0046093436,-0.0065228604,0.0016944183,-0.022950806,-0.01391706,0.0077177105,0.03248778,0.008483278,0.0031952392,0.0037204863,-0.0014664779,0.001489071,0.0053414144,0.0185694,-0.013191526,0.0056994865,-0.0036619476,-0.004263826,0.0024629894,-0.0034927651,0.020643737,0.008016031,0.0053813946,0.004599603,0.0022289013,0.013931831,-0.0069656996,0.008250646,0.036389597,0.0051475163,-0.0013264529,-0.0072042774,-0.0075730337,0.00084495684,-0.013887113,-0.008924428,0.014186408,0.00031069593,0.0095820185,-0.01124462,0.01764575,-0.010624209,-0.0037729049,0.007038913,0.007211187,-0.0008712562,-0.011654527,0.0068316516,-0.0027942166,0.0020414328,-0.022689044,0.0020787725,0.020701963,-0.012826267,0.0023974518,0.008649959,0.012429517,0.0025920344,-0.011203506,-0.006216643,0.0072601573,-0.0044650566,-0.0035656388,-0.012046574,0.016526747,0.012874542,-0.0014420142,0.003542022,-0.017021907,0.0034385137,-0.008800555,0.00689281,-0.007121723,-0.019785324,-0.013466026,0.0018525064,0.0063248333,0.0037988303,0.005336013,0.014010983,-0.003297226,-0.0060803597,0.015158881,-0.0030691223,-0.0005078483,0.007400289,-0.017804584,-0.0036887946,0.011864196,-0.011669971,0.00415237,0.012528651,-0.010384457,-0.0017461153,0.004668006,0.005958759,0.014270187,-0.03333836,-0.021482758,0.03325893,0.0040153177,0.008613919,0.005420177,-0.0013844921,0.0017486477,0.0031896215,0.0008613873,0.001635754,0.007630521,-0.012014619,0.00057451153,-0.008693036,-0.0027549546,-0.0031718495,0.0038112097,-0.003941293,-0.011757496,-0.00764124,-0.008699024,0.0032081963,0.00942394,-0.0045893574,0.0058254222,-0.005920595,0.009848534,0.018157413,0.026232477,0.0065943063,0.004518358,0.00895647,0.0037657472,-0.007173976,-0.0058551086,0.0022852835,0.00032467666,-0.014542208,0.021566069,0.0074060867,0.003545701,0.0019213937,-0.008369375,0.0018014793,-0.021281091,-0.0182145,0.006912736,-0.020277346,0.015308166,0.0027263667,-0.010669691,-0.0020841027,-0.0121705895,-0.012774888,-0.004908822,-0.009017314,0.013850188,0.014401854,-0.00020473768,-0.0018745586,0.005057729,0.0048644417,0.018331364,0.01320804,0.00701655,0.010665707,-0.008859592,0.011503785,-0.012753308,0.0060422225,-0.022720087,-0.0005472999,0.0038251611,-0.0144426115,-0.010348688,0.008965918,-0.0018885969,0.0015573925,0.0062548737,-0.0036467123,-0.0046792645,0.013382296,-0.0029419002,-0.014492962,0.0071736267,0.014439438,-0.0024714235,0.010439432,-0.008997458,0.013286995,-0.0020821248,-0.046104312,0.015355587,0.00028906422,0.012773926,-0.001818768,-0.006021835,0.009425921,0.021566782,0.0044414904,-0.0071643433,-0.013904254,-0.0066670743,-0.0040370226,0.013574306,-0.0071416204,-0.0052140607,-0.004992587,0.01736634,-0.008757502,0.002766827,-0.0127132125,-0.026116583,-0.025029251,0.0014087878,-0.008201419,-0.005285329,-0.00043221138,0.006473817,-0.0018004924,0.0016213013,0.009123737,-0.005290844,-0.011851208,-0.0047507333,-0.00023546485,0.010687944,-0.0016486552,-0.01029683,-0.00019776454,-0.013276242,0.013250962,-0.011223281,0.0039570252,0.01796719,-0.012406584,0.0057238503,-0.0014668505,-0.0065865265,-0.005022525,0.012222364,0.0057169823,0.023943573,0.004236341,0.038327392,-0.0061751865,-0.0114807375,0.012734793,0.023708135,-0.0022133763,0.004114686,0.018433724,0.017415568,-0.016102355,-0.0044674184,-0.026279509,-0.015751248,0.021132521,-0.011386613,-0.016997557,0.03369407,0.0016788525,0.00546756,0.014058757,0.017229903,0.0019143785,0.021176511,0.0012905989,-0.013343968,-0.0003192011,0.0044290954,0.0058346945,0.019766415,-0.0034024478,0.012048254,-0.010018592,0.010571381,-0.006332824,0.0014271003,-0.019988542,0.00560106,0.013065645,-0.0025141013,0.0037923388,-0.009297477,0.0073331036,0.019239329,-0.0022688813,0.02716353,0.010791841,0.006520121,-0.012652865,-0.0017794238,-0.0012459616,0.012335887,-0.015752466,0.012764742,0.005635335,0.010883673,0.002411049,-0.009803333,0.011100272,-0.005793885,-0.003585433,-0.022778567,-0.0074237413,-0.004448059,0.0035936357,-0.0029461614,-0.012030444,-0.009006531,-0.023808721,-0.0055710645,-0.010438755,-0.0059217024,0.007840569,0.001389981,-0.0015446082,0.006545024,-0.0011498483,-0.01362945,0.0054554995,-0.003833056,0.0033906724,0.0078047514,0.0070759384,0.0058527864,0.02173059,-0.008333771,0.00766019,0.007149111,0.017971894,0.0025409628,0.013797232,-0.006667351,-0.0002795547,0.0135902595,0.0015659108,0.0004095058,-0.0046381042,0.002666698,0.010151474,-0.005189415,-0.010261019,0.0022213946,-0.0073901336,0.006793986,0.0152917085,0.0074046534,0.00033649878,-0.021700425,0.013222465,0.006650935,-0.0066361106,0.0072286935,0.003442486,0.0026534065,-0.022944678,-0.0053500715,-0.009466096,0.008907852,0.00815385,-0.012971161,0.0037563415,0.011483446,0.009006527,0.0069598556,-0.016959641,0.001884637,-0.017825108,0.0068459515,-0.019603992,-0.00409059,0.0043283077,0.0067925593,0.007074419,-0.0062984047,-0.0101957135,0.0002473658,0.0069209207,0.00092643214,0.0130060455,0.013080876,-0.011831299,-0.017750371,-0.011626968,0.0045547565,0.0010016568,-0.00021358479,-0.0045106895,0.0030089344,0.003827081,-0.004878225,-0.0028161593,-0.004471646,0.0073491842,-0.10139416,-0.005702183,-0.012454036,0.021616818,0.015430673,0.01964853,-0.00016757166,0.005381283,-0.013636203,0.0034833057,-0.01113638,-5.482578e-05,0.0023234626,-0.025685951,-0.00042480402,-0.008149219,-0.008943403,-0.0008033273,-0.0068171034,0.004537776,0.012747112,0.0050168796,-0.00972101,0.0016135875,-0.010489005,0.002050484,-0.019850397,-0.019469174,0.0067871646,0.002652562,-0.006732492,-0.012985738,0.012679248,0.012746071,0.0068513174,-0.0054564076,-0.0043439334,0.008067013,-0.12683475,-0.012276252,-0.009408644,0.012837369,-0.008322827,0.0050363727,0.0040697,0.02532779,0.021097094,-0.0021351369,-0.006118727,0.010800191,-0.009425066,0.0023487033,0.016021779,0.0071311616,0.0070802253,0.009542341,-0.017199459,0.0069385245,0.00377958,0.0021384477,0.0140029825,-0.0045448598,0.0052607134,0.006726869,-0.0022091263,0.012956256,-0.0007864898,-0.003056954,0.010712434,0.01262373,-0.006250507,0.0021885743,-0.007638722,-0.00091097504,0.0049052164,0.022900961,-0.0316571,-0.015182332,0.023982652,0.011267224,-0.00059356086,-0.0031355575,0.008895438,-0.015313593,-0.0017538007,0.0020264992,0.0030350948,-0.019370168,0.009178461,-0.0029167999,-0.020726621,0.0013185389,0.0013761367,-0.002326133,0.0022683784,0.013439154,-0.008276964,0.011508796,-0.02165458,-0.00637624,-0.00020730596,-0.018221766,-0.009488258,0.0031527316,0.009649362,0.019207887,0.0054657953,0.025451092,0.015202464,0.010983384,-0.0088825775,0.001652707,0.028031562,-0.011905182,0.0047530103,-0.006661742,-0.03569111,-0.0018752175,0.009539888,0.011535043,0.009828712,-0.009115291,0.005106541,-0.017311122,-0.014545597,-0.03149482,-0.011501948,-0.041859806,-0.0031089566,0.0023446893,0.0106971655,0.008650325,-0.015103596,0.014477425,0.006184592,-0.002646714,-0.0033090806,-0.0023224973,-0.002953501,-0.0048601283,-0.0015397958,-0.0043363837,0.010930929,0.012478272,-0.0006759874,-0.010825584,-0.007385839,0.00041421308,-0.02066621,0.003329853,0.020217855,0.010543258,-0.009145873,0.005939029,-0.0034076779,-0.00082411,-0.01786447,0.0044110534,0.0054314714,0.0043640565,0.0024667191,-0.007910047,0.014413491,-0.012118865,0.012418387,0.03137774,-0.002777315,0.027424784,-0.011955742,-0.0062011275,0.025759678,-0.0070732594,0.007635261,0.012431947,-0.014946217,0.018203711,0.003762672,-0.0025462317,0.013425218,0.0021588737,0.011732501,-0.00020315313,-0.008563687,-0.0050555198,-0.0029147316,0.010545469,-0.006833867,0.024134882,-0.017251473,0.001237211,0.011950175,-0.002479577,0.002574687,-0.015501153,0.024648018,-0.008635889,0.005770525,-0.011196927,-0.0025483847,-0.0018889961,0.0018948468,0.01147088,0.0005694111,0.03619483,0.0056411927,-0.0041433037,0.017586578,-0.0044002836,0.0048014955,-0.008373275,0.0032414703,0.004489859,0.008413541,0.020357383,-0.011864263,0.009428163,0.0026959437,-0.0054196496,-0.032329593,-0.035534915,-0.021236766,-0.041616455,0.04114816,-0.005931202,-0.00036735958,-0.003131048,-0.023577463,-0.02444258,0.0019380995,-0.018113595,0.015392076,0.010656979,-0.0043687257,-0.0013930233,0.008582788,-0.0077971946,0.0064622504,0.007821188,-0.011921912,0.002614555,0.0007180979,-0.16217461,-0.014749576,-0.01741296,0.011957781,0.018869543,-0.0007941863,-0.004115523,-0.015430665,-0.007211453,0.0051858863,-0.009791694,-0.007682232,0.011502023,-0.0032592316,-0.008292744,0.009315412,0.0057620103,-0.00022359875,0.007803845,-0.0013933815,-0.020730762,0.010142603,-0.009268927,0.0028516254,-0.03388837,0.008063424,0.023934443,0.010078348,-0.007871348,-0.02212177,0.00814764,0.0013820168,-0.011686024,0.012416227,0.006180607,0.0026293115,-0.0006220231,0.007473199,0.003539077,0.017461596,-0.03204877,0.0110785505,-0.02780308,-0.008489318,-0.00019063817,0.001120538,-0.026235847,-0.014099127,-0.03844179,0.002754518,0.015441417,-0.021544898,0.01979747,0.009047705,-0.004075044,-0.025190825,0.0041007274,-0.032408316,0.0022941923,0.001361758,-0.003537173,-0.0051841266,0.017558953,-0.022796042,0.015466038,-0.026741749,-0.0010158913,0.17573003,0.007236725,-0.006067079,-0.0007253506,-0.0016569901,0.012233448,-0.0065804194,-0.0060026953,-0.018027516,-0.0035101396,-0.0024960134,0.016395561,-0.026098838,-0.0041901604,-0.023856184,-0.016687578,-0.00957748,0.0011242678,0.016699193,-0.0048285355,-0.010643515,-0.0020712398,-0.013948125,-0.0152618075,0.016640749,-0.004815054,0.012076205,-0.0014834071,-0.016057298,0.033548597,-0.014789376,-0.0032124578,-0.015931636,-0.010575485,0.005103324,0.0068901395,-0.010987138,-0.0046977475,0.01742755,0.008945085,0.009145534,0.014949913,0.0025529277,-0.012716911,-0.009067135,0.0077661914,0.0011257491,0.0055219764,-0.00077390467,-0.015073081,-0.028576277,-0.008741574,-0.0006749415,0.0055362238,0.04779742,0.018117951,-0.00021860149,-0.0009193312,-0.020401765,0.020890003,0.03202761,0.008800094,-0.019316902,-0.008958353,0.002913143,-0.009762693,0.0479914,-0.007924387,0.006908748,-0.11126219,0.004052463,-0.021867037,-0.014412516,0.015764654,0.0042401003,0.006381585,0.02158189,0.01576369,-0.0064037256,0.0020932392,0.0022565029,0.008280975,0.0026846426,0.009108445,0.019578997,-0.008309633,-0.0040988424,0.019951766,0.0007868289,-0.0038267383,0.007842855,-0.019395182,-0.021994544,-0.015459557,0.0051470175,-0.01783984,0.006071877,0.0020881104,0.0035675894,-0.006544588,0.00093580416,-0.016280519,0.02343004,-0.007838088,-0.026567023,0.0032450634,0.0016276194,0.0010562235,-0.019549148,-0.008153928,-0.0028629415,0.018063756,0.007844011,0.0018351258,-0.002087558,0.020849276,-0.0093872845,0.020357087,-0.0071906736,-0.013103251,-0.0069919517,-0.014487466,-0.014038437,-0.00047505854,0.010731022,0.0060636173,-0.030269315,0.00076931244,-0.03782198,-0.005371347,-0.002966397,0.027899316,0.005489567,0.015877347,-0.010253113,-0.011090457,-0.006873153,0.010812088,-0.01648995,-0.0067209033,-0.014146445,-0.019477174,0.011383435,0.0014984416,-0.00510735,0.008626505,0.0076580984,-0.017959049,-0.004542112,0.0056109824,-0.027984802,0.020730633,-0.001719468,0.056844935,0.0017750105,-0.0046056597,-0.021337096,6.674742e-05,0.0130646415,0.014914918,0.015149705,-0.016527375,0.016575562,-0.0066886097,-0.010935274,0.0037973952,-0.0036190874,0.0059155384,-0.009735419,0.0016452421,0.013706556,0.030198954,-0.0010192888,-0.026469193,-0.0028739981,-0.010003071,-0.015462789,-0.012586371,-0.0075700767,-0.0129533205,-0.0031973198,-0.01884276,-0.009679508,-0.014480516,0.016802568,-0.008821534,-0.0043366896,0.016696593,-0.009135377,0.019948639,-0.018932655,-0.006115884,-0.010573235,-0.0028864301,-0.00305301,0.009423104,0.02802132,-0.0012391781,-0.02753334,0.013623524,0.0023609265,0.02952467,-0.0028409665,0.04472826,-0.0084198825,0.023763027,0.012351312,-0.005470313,0.017890407,-0.014136817,-0.0075028148,-0.0123608485,0.006212486,0.0024348348,-0.0149178635,0.021698168,0.018919189,-0.010417828,-0.004475511,0.018947234,0.011640726,-0.014796539,0.002252814,0.0035751755,-0.0037039747,-0.007710433,0.005016396,-0.017389309,-0.011979485,0.0031334301,-0.0086380765,-0.016821325,0.009995807,-0.0023288492,-0.009101883,0.0020183765,-0.006941873,-0.018398829,-0.003991732,0.007444947,0.0060650064,0.004598918,-0.02747575,0.0026871446,0.008118005,0.0064952113,0.0009990998,-0.0039280164,-0.076439306,0.023757517,0.009174873,-0.0029332044,0.011371606,0.0052999,0.008705406,-0.004745636,-0.004581478,0.01881097,0.0055855657,-0.012279525,0.0030168,0.03362365,-0.014696648,0.0039275675,-0.026126204,-0.014751281,-0.003571606,-0.015696235,-0.005423525,0.00866561,-0.0055172746,-0.026965244,-0.009239206,0.020291336,-0.0028605347,0.00084311934,-0.0047513545,-0.01663247,0.0013674017,-0.034101296,0.01777723,-0.0103610065,-0.0022049895,-0.027542196,-0.018896375,-0.020517156,0.00025338837,-0.023027724,0.0082162935,0.0028694111,-0.06688736,0.005466726,0.031395424,-0.0014014473,-0.0036587487,-0.009238282,0.014193616,-0.0050098295,0.005053364,-0.012395328,0.020232366,0.0012599024,-0.00047446447,0.0021957476,-0.00058668817,0.007723876,-0.0075244512,0.009354538,-0.0046926015,-0.008120949,-0.02501327,-0.0182482,0.0054633194,0.0068714614,0.0063527194,0.017965008,0.004880481,0.024233986,-0.0125767,-0.017556308,-0.0067630135,0.004897043,5.0191804e-05,0.022108886,0.019196058,-0.016378537,-0.001265644,0.019617904,-0.004181235,0.017200314,-0.002499032,0.008814694,0.011734076,0.010237696,-0.0065853093,-0.10814981,-0.008417535,0.011299485,0.004878794,-0.008890048,0.011423871,0.01263125,0.04801463,0.0002571968,-0.015364396,-0.011923557,-0.016882142,0.02500253,-0.0022440304,-0.016371619,-0.014217314,0.015804,-0.00660614,0.0044260332,0.0071695526,0.014953318,-0.0053277817,-0.015364385,0.0012825648,0.006869857,-0.035641138,0.015678078,-0.0013648359,0.0152217,0.0051225517,0.0023191047,-0.009472292,-0.015041253,0.007033183,0.0066567133,0.012569442,0.00820538,-0.010068947,0.025451154,-0.0060637323,-0.032501165,0.003232862,-0.00021849517,0.005465293,-0.013146552,0.0058145486,-0.007359397,-0.0025702436,-0.017161798,0.00095763087,0.015164534,0.030068507,0.0130215725,-0.003516285,0.0089111505,-0.011986884,0.002853059,-0.005415137,0.01177388,0.007512678,-0.015619766,-0.004958651,0.018924518,-0.0034995615,-0.017326355,0.004803578,-0.0081226425,-0.02008896,-0.010957171,-0.009453674,0.0115027735,0.020170873,0.0334008,0.009986345,-6.0803282e-05,0.009737945,-0.0016908249,0.034932114,-0.007027764,-0.0019547124,-0.016327772,-0.010913659,0.023884837,-0.0066432706,-0.017054321,0.0017114707,0.00072199246,0.0028484534,-0.005080379,-0.023430727,0.004912151,-0.03021483,-0.021611223,0.0066274065,0.012337229,0.0070992876,-0.0003479118,-0.01034928,0.0034014229,-0.012961946,0.012833827,0.028371556,0.018456649,-0.0016260605,-0.012469269,-0.017760055,0.0075884503,0.006740163,-0.004149779,0.010748994,0.024884557,-0.002728402,-0.020036597,0.008837602,-0.009978963,0.00012595167,-0.0053586387,-0.00068119547,0.0036977949,-0.013362772,-0.000793866,-0.006518095,-0.00096981815,-0.014046566,-0.008628764,-0.021788135,-0.024110788,0.012805549,0.015418939,0.010169436,0.0038332348,0.02561212,-0.004517164,0.005145795,0.0068012644,-0.0025325166,-0.012306535,-0.0025710084,-0.013055692,0.014772331,0.004504352,-0.00037475594,0.013648121,0.0022922016,0.0065628137,0.03674763,0.0098103965,-0.0013950384,-0.0034061265,-0.0122767715,0.010069572,-0.00017296337,0.0041141547,-0.0033378054,-0.0077610994,0.00946217,0.004062715,-0.023695672,-0.004019719,0.009354514,0.004105147,0.039876603,-0.008503199,-0.00079254207,0.018540887,-0.017648716,-0.013691692,-0.007850579,0.020042242,-0.0027677182,0.03647731,0.0006109567,-0.00940179,-0.013046616,0.044402514,-0.0170524,-0.008877302,0.009209822,0.014677096,-0.0058220304,-0.0067780134,-0.006946084,-0.004357119,-0.00424038,0.002754254,-0.010541563,-0.0019997123,-0.019158041,0.014937286,0.0019790502,-0.0025262358,0.0008496313,-0.0077234404,-0.009247369,0.002839995,-0.0021063471,0.0052607697,-0.0008147343,0.024073781,0.037684873,-0.010685032,0.026287599,0.0025256686,0.0050301948,-0.017297799,-0.0031485406,-0.04372069,0.01590974,-0.025416592,0.020411013,-0.0056122467,-0.0129057905,0.00455259,0.0114887785,-0.013445349,0.013541827,-0.007624871,-0.0015289163,0.0068075885,0.010480295,0.00035231776,0.017362447,-0.002549292,-0.01275909,0.0053202193,-0.003763796,0.009608458,-0.008849551,-0.004654951,0.0060413424,0.011726344,-0.0030462516,-0.008248122,0.008417501,-0.01687602,-0.0010296934,-0.011656901,-0.011553674,-0.001379058,0.012120857,0.02681053,0.0003693217,-0.010793996,0.04607159,-0.015717953,-0.030691134,-0.0133834835,-0.014579299,-0.012483474,0.02147093,0.012677277,-0.0026793666,-0.0043376614,-0.0018288681,-0.019249458,-0.015890392,-0.0005460233,0.008175217,0.018824235,-0.011616686,0.011611763,0.019154187,-0.012779376,0.010407755,-0.036157236,-0.0190122,0.0037653993,0.016152885,-4.026437e-05,0.0078008063,0.019481894,-0.011071292,0.012141502,0.009125005,-0.01482054,0.0059660454,-0.003273643,0.00058218505,0.0086300215,0.0068590413,-0.004722339,0.0020588066,0.012094764,-0.0101904655,0.014764487,-0.005822884,-0.019765826,-0.006988485,0.01666497,-0.00025433415,0.016558977,-0.011686535,-0.007280561,0.0021805014,-0.0025711777,0.0034578019,-0.022727067,-0.0032624821,-0.011217224,-0.009278369,0.016936453,-0.0050625657,-0.0008889725,-0.016142428,-0.0075304555,0.0020124568,0.010658643,-0.016227968,-0.0018412501,-0.00068579934,0.0050765323,0.013639248,-0.0009170095,0.007893533,-0.029823435,0.009136548,-0.0010339472,0.013198823,0.006597268,0.010794791,0.004018869,-0.012115274,0.003887083,0.010330291,-0.0012694811,0.012851763,0.026137523,-0.008458075,-0.00021382088,-0.0029542202,0.0040499177,0.0023667153,0.009564963,-0.017921986,0.0133150015,0.008102424,0.0053536408,0.02711266,0.0013260253,0.0082467105,-0.00065757247,0.032252878,0.0076120314,-0.006489638,0.012170063,-0.00028855266,-0.011882183,-0.001822675,0.023724407,-0.018425042,0.0010771431,0.0054428494,0.003755687,0.0014613192,-0.0104201455,-0.0069663036,0.0027281737,-0.023661092,-0.00023843949,0.0002941467,0.0071012173,0.004109525,-0.01297145,0.008330963,-0.0106603075,-0.0076442356,-0.010606608,-0.027650557,-0.022224164,0.028895825,-0.0075570624,0.011038635,0.010075686,0.0010819862,-0.005954396,0.0017764943,0.0005607528,0.0054505947,-0.008057329,-0.0027617803,-0.02545079,0.008623909,-0.005629025,0.0014874879,-0.0039054265,-0.011371621,-0.00932243,-0.010928186,-0.004288278,-0.020606251,-0.003993674,-0.0013504546,0.024437808,0.008287441,-0.0013513127,-0.0062825046,-0.024489004,-0.019938245,-0.022689676,0.009647985,0.019969197,-0.018654322,0.008880628,-0.011299792,0.0021563568,0.010563938,-0.011123272,0.0022046277,-0.013803146,0.00065350503,9.500602e-05,-0.01117148,-0.017035935,0.008213384,-0.022311129,0.016237525,0.009192426,-0.0035403834,-0.0004401129,0.0012118979,0.0050909016,0.012996536,-0.0074092993,0.0060787154,0.0012122106,0.015558271,0.002813545,-0.004975494,-0.0026497494,-0.014472481,-0.016887875,-0.008737119,0.009620372,-0.00617898,-0.012087142,-0.008070635,0.003594934,-0.009330752,-0.016659474,0.022828067,0.0109574795,0.007901267,0.0015440445,0.012750803,0.012208242,0.0065945443,-0.019006828,-0.0064975717,-0.013609579,0.008888986,0.0027520626,0.006251128,-0.011682595,-0.012753726,0.01584828,-0.0077035218,-0.0019335506,0.0023356997,0.008108966,-0.0018134118,-0.0060911216,0.013968271,0.006556288,0.009694163,0.00892152,-0.019067993,-0.0025082105,-0.017000142,-0.0020819576,0.015945785,-0.0067300685,0.013101638,-0.03541897,0.007814497,0.02355034,0.014527051,0.011140291,0.02017622,-0.0017884853,-0.05287872,0.016448772,-0.0140982205,0.014427354,-0.015864344,-0.017321745,0.0026491976,-0.017126076,0.008076522,0.010277801,0.0034540254,-9.6619355e-05,-0.0043892236,-0.010453702,-0.007278749,0.014895438,0.006872415,-0.0009534498,-0.034939162,0.021368058,-0.024845127,-0.0047788695,-0.010912255,0.011834924,-0.0056186924,-0.021441959,0.010658,0.013950508,0.021435263,-0.014914367,-0.03241051,-0.021797167,-0.020768162,0.0036627057,-0.026175419,-0.006742581,-0.012620686,-0.00056315353,0.008702318,0.018011937,2.7138503e-05,-0.017678892,-0.013145297,-0.008357943,-0.02063231,0.012046687,-0.021076817,-0.030228516,0.022311218,-0.018792972,-0.010808822,0.0013520397,0.004812251,-0.022239916,0.021813039,-0.00041889655,0.007077725,0.006478945,-0.019418746,0.010006203,-0.01847578,-0.00808361,-0.025900517,0.004650304,-0.002546583,-0.009825925,-0.025545884,-0.00036606827,-0.029302483,0.0024195246,0.0029811244,0.0054587554,-0.0049057533,-0.0016264883,-0.016280932,-0.0027940283,0.01328431,0.024637984,0.02302365,0.0019703116,0.008862322,0.008814488,-0.011669125,-0.018839143,-0.013387912,-0.030005027,0.00909187,0.015010105,0.012993347,-0.024550676,0.0042255395,-0.0064508133,-0.023065,0.029817084,0.00042453926,0.020750303,-0.0043135155,-0.010607971,-0.020030685,0.014509163,0.013163749,-0.009145245,-0.028899096,-0.0075402604,0.024823224,0.006199051,0.00033495418,0.009568745,-0.011091479,0.012035999,0.004074382,-0.004361662,0.0019832007,0.008131906,0.011058104,-0.0053951796,-0.0039781607,0.010454578,-0.007879092,0.0004480278,-0.016608818,-0.0069424245,-0.013462942,0.0018702437,0.017911177,-0.017935626,-0.011758339,0.0100488905,-0.019368455,0.018689202,-0.01679909,-0.003578022,0.019539297,-0.015175379,0.0033494635,-0.0038704537,0.010179268,0.008368535,-0.007921448,0.0033538528,0.00096325425,0.008139092,0.00087766704,0.022567911,-0.023746626,-0.013197784,-0.0062204436,-0.001115814,-0.0073401066,0.0058241645,0.008024146,0.008927104,-0.0073331646,-0.002729785,0.0014990296,0.013467873,0.02067802,0.012715983,-0.019145194,0.018865598,0.00639598,0.00889706,-0.0129790045,0.0044702864,-0.0054732175,-0.011487744,0.011714676,-0.008864021,0.0007001016,0.021082843,-0.006510498,-0.00022869205,-0.016966771,0.002446988,-0.021748468,0.0020691687,0.014862144,0.02230896,-0.016013985,0.012498585,0.021241328,0.0020980805,-0.01703397,-0.0024269426,-0.001212345,0.0031984898,-0.015027417,-0.008310083,-0.026900016,0.0010512932,0.016208066,0.01899792,-0.0012503908,-0.013456344,-0.0032947897,0.011703875,-0.0014309552,-0.010313737,0.009074278,0.017394608,-0.014171085,-0.01989265,0.0027956078,-0.0028321159,0.01677002,0.0020766675,0.004719427,0.17162214,0.11815688,0.008506428,0.013645269,-9.28584e-05,0.0049599083,-0.033589106,0.011547259,0.020353487,-0.011036747,0.0036995867,-0.0056675505,0.007480579,0.005520276,0.006619722,0.014451812,0.013280823,0.008542088,-0.005958916,0.0046061347,-0.021972805,0.012086421,-0.0026816672,0.009326744,-0.02899373,0.00059081387,0.0035348132,0.01762238,-0.006420288,0.029285979,-0.023649285,0.0031644064,-0.015117581,0.0013993469,-0.010344973,-0.02336047,-0.022880826,0.029164689,0.016108986,-0.0051313885,0.0031247644,0.024890881,0.011659048,-0.020845069,0.021412684,0.018124778,-0.00070524693,-0.004944331,0.008493778,0.014754821,-0.015378065,-0.005988376,-0.01956822,0.00013817044,-0.0010846752,-0.001961568,0.006906933,8.563085e-05,-0.018010117,0.014032561,0.015255939,-0.016055739,-0.0002374696,0.00084503606,-0.004540874,-0.0061537228,-0.009041097,0.00968458,-0.0051220465,0.010380745,-0.00884487,0.008016151,-0.006753225,0.009361886,-0.004092662,0.014990923,0.008580405,0.004792182,0.0023735103,-0.019235263,0.0056357984,-0.0039149914,0.008913879,0.024207897,-0.01179678,-0.004890316,-0.0007644481,0.020653533,0.06834985,-0.021964896,0.013579986,-0.015406807,-0.024332236,-0.009563343,0.0022529159,0.015664872,-0.0064545437,0.012463952,-0.011661921,-0.00074452854,-0.0075444863,-0.0042098984,0.012402091,0.015658256,0.035774466,0.044313677,0.012341869,3.421887e-05,0.0014790836,0.0020695687,0.017138593,-0.00868383,0.0043348097,-0.0056866985,0.012718434,0.0054779514,0.0055852593,0.023239283,-0.098217286,-0.0067492016,-0.028487481,0.0036629203,-0.0053365836,0.024281261,0.0333323,0.011200106,-0.0043960614,-0.013342567,-0.012066644,-0.00649505,0.008768805,-0.0021768396,0.008332559,0.007634683,0.016799696,-0.032297384,-0.0080693895,-0.00031254918,-0.015296606,0.0062236637,-4.8825186e-06,0.004578293,0.014855891,0.031705767,-0.015014455,0.0011623537,0.012768099,-0.0015671471,-0.020571453,0.0151847415,-0.013153879,-0.0067719906,-0.006649039,0.012907018,0.019879436,0.0050823814,0.020842694,-0.023016984,-0.0044477517,-0.030777168,-0.0005738633,-0.015148322,0.01807831,-0.027545402,-0.014614966,-0.016464477,-0.027305374,0.0029191116,0.040007595,-0.0016595159,-0.0055513647,-0.010828851,-0.011281988,-0.013778374,-0.029727709,0.01031272,-0.0043917736,-0.023264,-0.0011921113,0.013714685,-0.0019739186,-0.011467283,0.0048576295,-0.015404402,-0.009243289,-0.024430435,0.0011031949,-0.0026511152,0.0018349099,-0.017042063,-0.009322599,-0.009606002,-0.009913566,0.00016738764,0.007032639,-0.021295916,-0.017835353,0.008381298,-0.021158366,-0.012625966,-0.010652288,0.13938576,-0.016777646,-0.004339788,-0.011086698,0.005924182,-0.011445669,0.02072057,0.027117746,0.020827563,0.0064457515,0.024747098,0.013369777,0.003030366,-0.020515706,-0.0075948616,0.0008554932,0.0023754106,-0.012912389,0.018755876,-0.0038879723,-0.013375974,-0.001714466,-0.0017315887,-0.009174047,-0.02289747,0.015868116,-0.031843856,0.008492488,0.0013116163,-0.0154204555,-0.010040799,-0.006512221,-0.0015266684,-0.0059698084,-0.0064686304,-0.0035097613,-0.009766691,0.0006475405,-0.0043115336,-0.0076832348,0.0014718808,-0.0027303796,0.024990564,0.024823047,-0.053699218,0.20557676,-0.0070983176,-0.007851419,-0.0060188374,0.004515983,-0.0057968264,0.00078510446,0.0036854853,-0.0019894843,0.008568128,0.012387667,0.01869202,-0.009923507,-0.00903541,-0.0038658467,0.0021708636,0.010322927,0.011598261,0.007766631,0.006123972,0.01759325,-0.014878117,-0.00078131695,0.014369437,-0.013095112,0.032289624,-0.01618232,0.0042168214,-0.0012598679,0.017341357,0.007424865,-0.008040006,-0.0078635225,-0.012189841,0.0016552196,0.015560379,0.0029111498,-0.007460975,0.017114665,0.0057080938,-0.00048777089,0.009231547,0.003670706,-0.0029846004,-0.008322871,0.0064610494,-0.026467066,0.0030435685,0.011505525,0.0036101516,0.012702394,0.0065572043,-0.0043009613,-0.0033228253,-0.02610136,0.0015716273,-0.009466154,-0.0026506088,-0.004557778,-0.0034155385,0.0026798479,-0.004375169,0.020338792,-0.020146126,0.007687349,0.0047169724,-0.028135804]	f	2010-01-30	Male
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
\.


--
-- Data for Name: portfolios; Type: TABLE DATA; Schema: public; Owner: jobmatch
--

COPY public.portfolios (id, user_id, headline, bio, date_of_birth, gender, city, state, linkedin_url, github_url, website_url, total_experience_years, current_company, "current_role", skills, work_experiences, education, certifications, languages, projects, intro_video_path, intro_video_filename, intro_audio_path, intro_audio_filename, created_at, updated_at) FROM stdin;
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

COPY public.users (id, first_name, last_name, email, phone, hashed_password, profile_pic_url, is_verified, onboarding_complete, is_assessment_done, totp_secret, totp_enabled, is_first_login, role, industry, job_role, job_type, salary_range, experience, auto_apply_enabled, company_type, company_name, company_location, company_size, preferred_locations, profile_embedding, created_at, updated_at) FROM stdin;
97279db6-b5ec-4d86-bae7-a7b2341b0e8d	Shiv	Kumar	shivkumar32334@gmail.com	8557068128	$2b$12$baqqqcR39jDyigSVDZDLBuCcB31oLH8Ckq5nA4GkmFspaICCiDXF6	\N	f	f	t	CHYYHZF6NBNW5Q2MWQEWQPTPW6IPINL3	f	t	seeker	\N	\N	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	2026-05-30 08:15:22.376028	2026-05-30 08:15:22.376031
546afbd2-27a5-4ed3-8ed0-90f0b043ccd9	Harsh	Dev	harshdevarya96@gmail.com	8076939081	$2b$12$St6l/poNt.3DtPY97f3bxeIG2f.xlNzuaB1dE.ioyMwy8CsIpxeNG	\N	f	f	t	B37UNOWPAZ4ARKHH5M25KYEP37QNJBLX	f	t	seeker	\N	\N	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	2026-05-30 08:22:51.451657	2026-05-30 08:22:51.45166
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

