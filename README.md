# JobMatch AI — Backend

> **AI-Powered Bidirectional Job Matching Platform**

JobMatch AI is a modern backend API that intelligently connects job seekers with recruiters using semantic AI matching, automated interviews, personalized career roadmaps, and real-time notifications.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [1. Clone & Configure](#1-clone--configure)
  - [2. Run with Docker](#2-run-with-docker)
  - [3. Run Locally (Without Docker)](#3-run-locally-without-docker)
- [Environment Variables](#environment-variables)
- [API Overview](#api-overview)
- [Authentication Flow](#authentication-flow)
- [AI Integration](#ai-integration)
- [Database](#database)
- [Scripts & Migrations](#scripts--migrations)
- [License](#license)

---

## Features

### 🔐 Authentication & Security
- **JWT-based authentication** with role-based access control (seeker / provider)
- **TOTP 2FA** (Time-based One-Time Password) with QR code setup via authenticator apps
- **Email OTP verification** for account activation
- **Phone-based login** with TOTP fallback
- Password hashing with bcrypt

### 💼 Job Management
- Full CRUD for job postings (providers only)
- **AI-generated job descriptions** and **AI-suggested skills**
- Job activation / deactivation with scheduled cleanup
- Support for job types, employment types, salary ranges, shifts, perks
- Public job listing endpoints for external candidates

### 🧠 AI-Powered Matching
- **Semantic vector matching** using embeddings (OpenAI or Google Gemini)
- pgvector extension for efficient similarity search in PostgreSQL
- **Proactive matching**: jobs auto-match candidates on creation, and vice versa
- Match highlights, skill gaps, and fit reasons generated for each pair
- Configurable match score thresholds
- **External candidate matching** for guest applicants

### 🤖 AI Interview
- Automated interview sessions with dynamic question generation
- Session tracking with transcripts and chat history
- Score calculation and detailed AI feedback at interview completion

### 🗺️ Career Roadmap
- AI-generated personalized learning roadmaps for job seekers
- Structured milestones with learning resources (courses, articles, videos, projects)
- Progress tracking per milestone (pending → in-progress → completed)
- Roadmap categories and roles from master data
- Suggested target roles based on user profile
- Regeneration with updated preferences

### 📄 Resume Management
- Resume file upload and parsing (PDF support)
- AI-powered skill extraction from resumes
- Resume embedding for semantic matching

### 📊 Assessments & Portfolio
- Candidate skill assessments
- Portfolio builder for showcasing projects and experience

### 🔔 Notifications
- In-app notification system with real-time WebSocket delivery
- Email notifications (OTP, welcome, alerts)
- Interest alerts: providers can express interest in candidates

### 🌐 External Candidate Portal
- Public API for non-registered candidates to apply
- Public job browsing without authentication
- Background AI matching for guest applicants
- Shortlist / reject workflow for providers

### ⚡ Real-Time
- WebSocket endpoints for live notifications (`/ws/{user_id}`)

### 🎯 Analytics & Master Data
- Dashboard analytics endpoints
- Seeded reference data (categories, roles, skills, industries)

---

## Tech Stack

| Layer           | Technology                                        |
| --------------- | ------------------------------------------------- |
| **Framework**   | FastAPI (async) + Uvicorn                         |
| **Database**    | PostgreSQL 14+ with pgvector extension             |
| **ORM**         | SQLAlchemy 2.0 (async)                             |
| **Auth**        | JWT (python-jose) + bcrypt + pyotp (TOTP)         |
| **AI / LLM**    | OpenAI (GPT-4o, text-embedding-3-small) / Google Gemini |
| **Cache**       | Redis                                              |
| **Email**       | aiosmtplib + Jinja2 templates                      |
| **File Storage**| Local filesystem (uploads directory)               |
| **PDF Parsing** | PyMuPDF, pdfplumber, pdfminer.six                  |
| **Docker**      | Docker + Docker Compose                            |
| **Validation**  | Pydantic v2                                        |

---

## Project Structure

```
backend/
├── main.py                  # FastAPI app entry point, CORS, lifespan, routers
├── config.py                # Pydantic settings from .env
├── database.py              # Async SQLAlchemy engine, session, init_db
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container build
├── docker-compose.yml       # PostgreSQL + pgAdmin + Redis + Backend
│
├── models/                  # SQLAlchemy ORM models
│   ├── user.py              # User (seeker/provider roles)
│   ├── job.py               # JobPosting
│   ├── resume.py            # Resume
│   ├── match.py             # Match (job ↔ seeker)
│   ├── external_candidate.py
│   ├── external_candidate_match.py
│   ├── application.py       # Job applications
│   ├── interview.py         # Interview records
│   ├── ai_interview.py      # AI interview sessions
│   ├── assessment.py        # Skill assessments
│   ├── portfolio.py         # Candidate portfolios
│   ├── roadmap.py           # Career roadmaps, milestones, resources
│   ├── notification.py      # In-app notifications
│   ├── otp.py               # OTP records
│   ├── master.py            # Static reference data
│   └── master_data.py       # Category/role master data
│
├── schemas/                 # Pydantic request/response models
│   ├── auth.py, jobs.py, resume.py, portfolio.py
│   ├── assessment.py, interviews.py, roadmap.py
│   └── external_candidate.py
│
├── routers/                 # API route handlers
│   ├── auth.py              # Register, login, OTP, TOTP
│   ├── users.py             # User profile management
│   ├── jobs.py              # Job CRUD + AI description/skills generation
│   ├── resumes.py           # Resume upload & parsing
│   ├── matches.py           # Job↔Candidate match results
│   ├── applications.py      # Job applications
│   ├── interviews.py        # Interview scheduling
│   ├── ai_interview.py      # AI-powered interviews
│   ├── assessment.py        # Candidate assessments
│   ├── portfolio.py         # Portfolio management
│   ├── analytics.py         # Dashboard analytics
│   ├── resume_builder.py    # Resume builder
│   ├── onboarding.py        # User onboarding
│   ├── master.py            # Reference data
│   ├── master_data.py       # Category/role data
│   ├── roadmap.py           # Career roadmap endpoints
│   ├── external_candidate.py# Public external candidate API
│   └── notifications.py     # Notification endpoints
│
├── services/                # Business logic & external integrations
│   ├── auth_service.py      # JWT, password hashing, OTP generation
│   ├── matching_service.py  # Semantic matching, embeddings, proactive match
│   ├── ai_service.py        # Core AI/LLM calls
│   ├── ai_interview_service.py
│   ├── ai_jobcreation_service.py
│   ├── ai_roadmap_service.py
│   ├── ai_feedback_service.py
│   ├── ai_improvement_suggestion_service.py
│   ├── jobs_service.py      # Job activation/deactivation logic
│   ├── roadmap_service.py   # Roadmap CRUD & progress
│   ├── notification_service.py
│   ├── email_service.py     # SMTP email sender
│   ├── totp_service.py      # TOTP generation & verification
│   ├── file_service.py      # File upload handling
│   ├── file_extract_service.py
│   ├── resume_parser.py     # PDF resume parsing
│   ├── portfolio_service.py
│   └── websocket_manager.py # WebSocket connection manager
│
├── templates/               # Jinja2 email templates
│   ├── otp_email.html
│   ├── welcome_email.html
│   └── notification_email.html
│
├── uploads/                 # Uploaded files directory
├── .env                     # Environment configuration (git-ignored)
├── .env.example             # Environment template
│
└── scripts/ (root-level)    # Migration & utility scripts
    ├── seed_master.py       # Master data seeder
    ├── seed_data.py / seed_db.py
    ├── add_*.py             # Various migration scripts
    └── fix_*.py / test_*.py # Fix & test utilities
```

---

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 14+** with [pgvector extension](https://github.com/pgvector/pgvector)
- **Redis** (optional, for caching / future Celery tasks)
- **OpenAI API Key** and/or **Google Gemini API Key**
- **Docker & Docker Compose** (optional but recommended)

---

## Quick Start

### 1. Clone & Configure

```bash
# Clone the repository
git clone <repo-url>
cd backend/combined_backend

# Copy and edit environment variables
cp .env.example .env
# Edit .env with your actual credentials (API keys, DB credentials, SMTP, etc.)
```

### 2. Run with Docker (Recommended)

```bash
# Build and start all services (PostgreSQL + pgAdmin + Redis + Backend)
docker-compose up --build
```

This will:
- Start PostgreSQL with pgvector on port `5432`
- Start pgAdmin on port `5050` (email: `admin@jobmatch.ai`, password: `admin`)
- Start Redis on port `6379`
- Start the FastAPI backend on port `8000` with hot-reload

The API is available at: **http://localhost:8000**

Swagger UI: **http://localhost:8000/docs**

Health check: **http://localhost:8000/health**

### 3. Run Locally (Without Docker)

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Make sure PostgreSQL + pgvector + Redis are running locally
# Then start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Environment Variables

Configure these in your `.env` file:

| Variable                        | Default                                  | Description                          |
| ------------------------------- | ---------------------------------------- | ------------------------------------ |
| `DATABASE_URL`                  | `postgresql+asyncpg://jobmatch:secret@localhost:5432/jobmatch_db` | PostgreSQL connection string |
| `SECRET_KEY`                    | `change-this-secret`                     | JWT signing key (change in production!) |
| `ALGORITHM`                     | `HS256`                                  | JWT algorithm                        |
| `ACCESS_TOKEN_EXPIRE_MINUTES`   | `10080` (7 days)                         | Token expiry                         |
| `OPENAI_API_KEY`                | _(required for AI features)_             | OpenAI API key                       |
| `OPENAI_CHAT_MODEL`             | `gpt-4o`                                 | Chat model                           |
| `OPENAI_EMBEDDING_MODEL`        | `text-embedding-3-small`                 | Embedding model                      |
| `GOOGLE_API_KEY`                | _(required for Gemini mode)_             | Google Gemini API key                |
| `GEMINI_CHAT_MODEL`             | `gemini-2.5-flash`                       | Gemini chat model                    |
| `AI_MODE`                       | `openai`                                 | `openai` / `gemini` / `mock`         |
| `SMTP_HOST`                     | `smtp.gmail.com`                         | SMTP server                          |
| `SMTP_PORT`                     | `587`                                    | SMTP port                            |
| `SMTP_USER` / `SMTP_PASSWORD`   | _(required for emails)_                  | SMTP credentials                     |
| `REDIS_URL`                     | `redis://localhost:6379/0`               | Redis connection                     |
| `FRONTEND_URL`                  | `http://localhost:5173`                  | Frontend origin for CORS             |
| `CORS_ORIGINS`                  | _(optional)_                             | Comma-separated extra origins        |
| `UPLOAD_DIR`                    | `uploads`                                | File upload directory                |
| `MAX_UPLOAD_MB`                 | `10`                                     | Max upload size                      |
| `AUTO_MATCH_THRESHOLD`          | `0.70`                                   | Minimum match score for auto-matching |
| `PROVIDER_MATCH_THRESHOLD`      | `0.75`                                   | Provider-side match threshold        |

---

## API Overview

### Auth (`/api/auth`)
| Method | Endpoint            | Description                        |
| ------ | ------------------- | ---------------------------------- |
| POST   | `/register`         | Register new user (returns TOTP QR)|
| POST   | `/login`            | Email + password login             |
| POST   | `/verify-otp`       | Verify email OTP                   |
| POST   | `/send-phone-otp`   | Phone-based login (TOTP)           |
| POST   | `/verify-phone-otp` | Verify phone TOTP                  |
| GET    | `/me`               | Get current user profile           |
| POST   | `/totp/setup`       | Set up TOTP 2FA                    |
| POST   | `/totp/enable`      | Enable TOTP                        |
| POST   | `/totp/disable`     | Disable TOTP                       |
| POST   | `/totp/verify`      | Verify TOTP during login           |

### Jobs (`/api/jobs`)
| Method | Endpoint                   | Description                     |
| ------ | -------------------------- | ------------------------------- |
| POST   | `/`                        | Create job (provider only)      |
| GET    | `/`                        | List jobs (seeker: all active; provider: own) |
| GET    | `/{job_id}`                | Get job details                 |
| PATCH  | `/{job_id}`                | Update job                      |
| PUT    | `/{job_id}`                | Full update job                 |
| DELETE | `/{job_id}`                | Delete job (deactivate + cleanup)|
| PATCH  | `/{job_id}/deactivate`     | Deactivate job                  |
| PATCH  | `/{job_id}/activate`       | Re-activate job                 |
| POST   | `/generate-description`    | AI generate job description     |
| POST   | `/generate-skills`         | AI suggest required skills      |

### Matches (`/api/matches`)
| Method | Endpoint              | Description                         |
| ------ | --------------------- | ----------------------------------- |
| GET    | `/jobs`               | Seeker: get matched job recommendations |
| GET    | `/candidates`         | Provider: get matched candidates    |
| GET    | `/candidate/{id}`     | Provider: detailed candidate profile|
| POST   | `/interest/{id}`      | Provider: express interest          |

### AI Interview (`/api/interviews/ai`)
| Method | Endpoint          | Description                     |
| ------ | ----------------- | ------------------------------- |
| POST   | `/start`          | Start AI interview session      |
| POST   | `/respond`        | Submit answer, get next question|
| GET    | `/result/{id}`    | Get interview results & feedback|

### Career Roadmaps (`/api/roadmaps`)
| Method | Endpoint                                  | Description                     |
| ------ | ----------------------------------------- | ------------------------------- |
| GET    | `/categories`                             | List roadmap categories         |
| GET    | `/categories/{id}/roles`                  | List roles in a category        |
| GET    | `/suggested-roles`                        | AI-suggested target roles       |
| POST   | `/generate`                               | Generate new AI roadmap         |
| GET    | `/`                                       | List user roadmaps              |
| GET    | `/{id}`                                   | Get roadmap with milestones     |
| PATCH  | `/{id}`                                   | Update roadmap                  |
| DELETE | `/{id}`                                   | Delete roadmap                  |
| GET    | `/{id}/progress`                          | Get roadmap progress            |
| POST   | `/{id}/regenerate`                        | Regenerate with new preferences |
| PUT    | `/{id}/milestones/{mid}/status`           | Update milestone status         |
| GET    | `/{id}/milestones/{mid}`                  | Get milestone details           |

### External Candidates (`/api/external`)
| Method | Endpoint                          | Description                      |
| ------ | --------------------------------- | -------------------------------- |
| POST   | `/apply`                          | Public job application           |
| GET    | `/jobs`                           | Public active job listings       |
| GET    | `/jobs/{id}`                      | Public job detail                |
| POST   | `/upload`                         | Public file upload               |
| PUT    | `/shortlist/{id}`                 | Shortlist candidate (provider)   |
| PUT    | `/reject/{id}`                    | Reject candidate (provider)      |
| GET    | `/candidates/{id}/matches`        | Get candidate's job matches      |
| GET    | `/jobs/{id}/external-matches`     | Get job's external matches       |

Additional modules: **Users**, **Resumes**, **Applications**, **Interviews**, **Assessments**, **Portfolio**, **Notifications**, **Analytics**, **Resume Builder**, **Onboarding**, **Master Data** — all available under `/api` prefix.

Full interactive API docs at: **http://localhost:8000/docs**

---

## Authentication Flow

```
1. Register (email + password + role) → Receive TOTP QR code
2. Scan QR with authenticator app (Google Authenticator, Authy, etc.)
3. Login → OTP sent to email → verify OTP → TOTP challenge → JWT token issued

Phone-based flow:
1. Send phone OTP → Receive TOTP QR (first time) / TOTP prompt (returning)
2. Enter TOTP code from authenticator → JWT token issued
```

All protected endpoints require the `Authorization: Bearer <token>` header.

---

## AI Integration

JobMatch AI supports two AI backends, configurable via `AI_MODE`:

| Mode     | Description                                           |
| -------- | ----------------------------------------------------- |
| `openai` | Uses OpenAI GPT-4o + text-embedding-3-small models    |
| `gemini` | Uses Google Gemini 2.5 Flash + embedding-001 models   |
| `mock`   | Returns mock responses — useful for local development |

AI-powered features:
- **Job description & skills generation** from a job title
- **Semantic candidate-job matching** via vector embeddings (pgvector)
- **AI interviews** with dynamic questioning and scoring
- **Career roadmap generation** with milestones and learning resources
- **Resume parsing** and skill extraction
- **Feedback & improvement suggestions**

---

## Database

PostgreSQL with the **pgvector** extension is required for semantic matching.

The `docker-compose.yml` uses the `ankane/pgvector` image which includes the extension.

On startup, the app automatically:
1. Enables the `vector` extension
2. Creates all tables via SQLAlchemy `create_all`
3. Seeds master data (categories, roles, etc.)

Connection pooling is configured with:
- `pool_size=10`, `max_overflow=20`
- `pool_pre_ping=True` for connection health checks

---

## Scripts & Migrations

Several utility scripts are at the project root for database migrations and fixes:

| Script                             | Purpose                                |
| ---------------------------------- | -------------------------------------- |
| `seed_master.py`                   | Seed master/category/role data         |
| `seed_data.py` / `seed_db.py`      | Seed test data                         |
| `create_roadmap_tables.py`         | Create roadmap-related tables          |
| `add_ai_interview_columns.py`      | Add AI interview columns               |
| `add_application_candidate_columns.py` | Add candidate columns to applications |
| `add_external_candidate_matches.py`| Add external candidate match tables    |
| `add_roadmap_current_skills.py`    | Add current skills to roadmaps         |
| `add_difficulty_to_milestones.py`  | Add difficulty field to milestones     |
| `add_milestone_stage_columns.py`   | Add stage columns to milestones        |
| `fix_assessment_tables.py`         | Fix assessment table schema            |
| `fix_interviews_table.py`          | Fix interview table schema             |
| `fix_otp_records.py`              | Fix OTP records schema                 |
| `update_enum.py` / `update_user_schema.py` | Schema updates                  |
| `test_*.py`                        | Various test/debug scripts             |

These are run manually as needed — they are **not** part of the auto-startup flow.

---

## License

Proprietary — All rights reserved.


<!-- Setup commands or run the backend services -->
cd combined_backend

<!-- Docker setup commands  -->
docker-compose build 

docker-compose up 