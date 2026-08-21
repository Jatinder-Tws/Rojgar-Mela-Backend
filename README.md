# RojgarMela AI — Backend

> **AI-Powered Bidirectional Job Matching Platform**

RojgarMela AI is a modern backend API that intelligently connects job seekers with recruiters using semantic AI matching, automated interviews, personalized career roadmaps, and real-time notifications.

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
cd Rojgar-mela-backend

# Copy and edit environment variables
cp .env.example .env
# Edit .env with your own credentials (API keys, DB credentials, SMTP, etc.)
```

### 2. Run with Docker (Recommended)

```bash
# Build the images
docker-compose build

# Start all services (PostgreSQL + Redis + Backend + Celery worker/beat)
docker-compose up
```

This will:
- Start PostgreSQL with the `pgvector` extension on port `5435` (mapped to `5432` inside the container)
- Start Redis on port `6379`
- Start the FastAPI backend on port `8000` with hot-reload
- Start a Celery worker + beat scheduler for background/email/AI jobs

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
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Environment Variables

The app is configured entirely through a `.env` file at the project root (see `app/core/config.py` for the full list of settings). Copy `.env.example` to `.env` and fill in your own values — database credentials, JWT secret, AI provider keys, SMTP credentials, Redis URL, CORS origins, etc. Values are intentionally not documented here.

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

© 2026 Rojgar Mela. Unauthorized copying, distribution, or use of this software, in whole or in part, is strictly prohibited without prior written permission.