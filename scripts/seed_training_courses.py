import asyncio
import uuid
from datetime import datetime
import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import AsyncSessionLocal, import_all_models
from sqlalchemy import select, delete
from app.modules.training_portal.models.training_portal_course import TrainingPortalCourse

# TrainingPortalCourse has a string-based relationship("User", ...); SQLAlchemy
# only resolves that against models that have been imported into the process.
# The app registers everything via import_all_models() during init_db() at
# startup, but this standalone script needs to do it explicitly.
import_all_models()


def make_id(prefix: str, idx: int) -> str:
    return f"{prefix}_{idx}_{uuid.uuid4().hex[:6]}"


def build_mern_phase1_modules():
    return [
        {
            "id": make_id("mod_mern", 1),
            "title": "Phase 1 - Module 1: Frontend Basics (HTML & CSS)",
            "description": "Semantic HTML, CSS fundamentals, layout (Flexbox/Grid), and building static responsive pages.",
            "sequence": 1,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_mern", 101),
                    "title": "Week 1-2: Semantic HTML & CSS Fundamentals",
                    "description": "Semantic tags, box model, CSS selectors, typography, positioning, and page structuring.",
                    "durationHours": 15,
                },
                {
                    "id": make_id("top_mern", 102),
                    "title": "Week 1-2: Responsive Layouts with Flexbox & Grid",
                    "description": "Flexbox layout properties, CSS Grid system, media queries, and mobile-first design.",
                    "durationHours": 15,
                },
            ],
        },
        {
            "id": make_id("mod_mern", 2),
            "title": "Phase 1 - Module 2: Frontend Framework (Tailwind CSS + React / Next.js)",
            "description": "Utility-first styling with Tailwind CSS; React and Next.js core concepts.",
            "sequence": 2,
            "fee": 2500.0,
            "topics": [
                {
                    "id": make_id("top_mern", 201),
                    "title": "Week 3-4: Utility-First Styling with Tailwind CSS",
                    "description": "Tailwind configuration, utility classes, responsive variants, dark mode, and component styling.",
                    "durationHours": 15,
                },
                {
                    "id": make_id("top_mern", 202),
                    "title": "Week 3-4: React & Next.js Fundamentals",
                    "description": "Components, JSX, props, useState/useEffect hooks, client vs server components, routing, and state management.",
                    "durationHours": 15,
                },
            ],
        },
        {
            "id": make_id("mod_mern", 3),
            "title": "Phase 1 - Module 3: Backend APIs (Node.js & Express)",
            "description": "Building RESTful APIs with Node.js and Express.",
            "sequence": 3,
            "fee": 2500.0,
            "topics": [
                {
                    "id": make_id("top_mern", 301),
                    "title": "Week 5-6: Building REST APIs with Node.js",
                    "description": "Node runtime, Express server setup, routing, middleware, request validation, authentication, and error handling.",
                    "durationHours": 30,
                },
            ],
        },
        {
            "id": make_id("mod_mern", 4),
            "title": "Phase 1 - Module 4: Backend Database ORMs",
            "description": "Connecting Node.js to databases using Object-Relational/Document Mappers.",
            "sequence": 4,
            "fee": 1500.0,
            "topics": [
                {
                    "id": make_id("top_mern", 401),
                    "title": "Week 7: Connecting Node.js to Databases using ORMs",
                    "description": "ORMs/ODMs setup (Prisma/TypeORM/Mongoose), models, schemas, relationships, migrations, and basic querying.",
                    "durationHours": 15,
                },
            ],
        },
        {
            "id": make_id("mod_mern", 5),
            "title": "Phase 1 - Module 5: Database - PostgreSQL (SQL)",
            "description": "Relational database design, SQL queries, joins, and Node.js integration.",
            "sequence": 5,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_mern", 501),
                    "title": "Week 8: Relational DB Design, SQL Queries & Integration",
                    "description": "PostgreSQL installation, schema design, normalization, complex SQL queries, JOINs, indexing, and backend connection.",
                    "durationHours": 15,
                },
            ],
        },
        {
            "id": make_id("mod_mern", 6),
            "title": "Phase 1 - Module 6: Database - MongoDB (NoSQL)",
            "description": "Document-based data modeling, CRUD operations, and Node.js backend integration.",
            "sequence": 6,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_mern", 601),
                    "title": "Week 9: Document Data Modeling & MongoDB Integration",
                    "description": "Document DB principles, MongoDB Atlas setup, CRUD operations, aggregation pipelines, and Mongoose integration.",
                    "durationHours": 15,
                },
            ],
        },
        {
            "id": make_id("mod_mern", 7),
            "title": "Phase 1 - Module 7: Buffer & Catch-Up Week",
            "description": "Reserved for revision, catching up on topics, and capstone preparation.",
            "sequence": 7,
            "fee": 500.0,
            "topics": [
                {
                    "id": make_id("top_mern", 701),
                    "title": "Week 10: Buffer / Catch-Up Week",
                    "description": "Concept reinforcement across frontend, backend, and database modules prior to starting the capstone project.",
                    "durationHours": 10,
                },
            ],
        },
        {
            "id": make_id("mod_mern", 8),
            "title": "Phase 1 - Module 8: Foundation Capstone Project",
            "description": "Building a complete web application applying Phase 1 core fundamentals.",
            "sequence": 8,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_mern", 801),
                    "title": "Week 11-13: Foundation Capstone Project",
                    "description": "End-to-end full-stack app built using Node.js, React / Next.js, PostgreSQL, and MongoDB.",
                    "durationHours": 40,
                },
            ],
        },
    ]


def build_mern_specialization_and_capstone_modules():
    return [
        {
            "id": make_id("mod_mern", 9),
            "title": "Phase 2 - Module 9: Track A - DevOps Specialization",
            "description": "Cloud, Version Control, CI/CD, Docker, Nginx, and SSL deployment.",
            "sequence": 9,
            "fee": 3000.0,
            "topics": [
                {
                    "id": make_id("top_mern", 901),
                    "title": "Week 14: Cloud Fundamentals & Digital Ocean",
                    "description": "Provisioning Droplets, SSH keys, security, Linux administration, and environment configuration.",
                    "durationHours": 10,
                },
                {
                    "id": make_id("top_mern", 902),
                    "title": "Week 15: Version Control & CI/CD Pipelines",
                    "description": "Advanced Git workflows, GitHub Actions, automated testing, building, and deployment pipelines.",
                    "durationHours": 10,
                },
                {
                    "id": make_id("top_mern", 903),
                    "title": "Week 16: Docker Containerization",
                    "description": "Docker images, container runtime, Dockerfiles, multi-stage builds, and Docker Compose orchestration.",
                    "durationHours": 10,
                },
                {
                    "id": make_id("top_mern", 904),
                    "title": "Week 17: Reverse Proxy, SSL & Nginx",
                    "description": "Nginx web server setup, reverse proxying, Domain configuration, and Let's Encrypt SSL/TLS certificates.",
                    "durationHours": 10,
                },
            ],
        },
        {
            "id": make_id("mod_mern", 10),
            "title": "Phase 2 - Module 10: Track A - DevOps Specialization Capstone",
            "description": "Capstone project applying cloud deployment, CI/CD, Docker, and Nginx.",
            "sequence": 10,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_mern", 1001),
                    "title": "Week 18-19: DevOps Specialization Capstone Project",
                    "description": "Deploying full-stack web applications with automated CI/CD, Docker, Nginx, and SSL setup.",
                    "durationHours": 30,
                },
            ],
        },
        {
            "id": make_id("mod_mern", 11),
            "title": "Phase 2 - Module 11: Track B - AI/ML Specialization",
            "description": "AI/ML foundations, LLMs, Agentic AI, MCP, and LangChain.",
            "sequence": 11,
            "fee": 3000.0,
            "topics": [
                {
                    "id": make_id("top_mern", 1101),
                    "title": "Week 14: AI/ML Foundations",
                    "description": "Introduction to AI/ML core concepts, model architectures, and applied LLM overview.",
                    "durationHours": 10,
                },
                {
                    "id": make_id("top_mern", 1102),
                    "title": "Week 15: Large Language Models (LLMs)",
                    "description": "Working with LLM APIs, prompt engineering, text generation, embeddings, and vector databases.",
                    "durationHours": 10,
                },
                {
                    "id": make_id("top_mern", 1103),
                    "title": "Week 16: Agentic AI & Model Context Protocol (MCP)",
                    "description": "Autonomous AI agent architecture, tool selection, loop execution, and MCP standard implementation.",
                    "durationHours": 10,
                },
                {
                    "id": make_id("top_mern", 1104),
                    "title": "Week 17: LangChain Framework",
                    "description": "Building agentic applications using LangChain, custom tools, memory, and chain execution.",
                    "durationHours": 10,
                },
            ],
        },
        {
            "id": make_id("mod_mern", 12),
            "title": "Phase 2 - Module 12: Track B - AI/ML Specialization Capstone",
            "description": "Capstone project building an interactive AI agent using LLMs, MCP, and LangChain.",
            "sequence": 12,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_mern", 1201),
                    "title": "Week 18-19: AI/ML Specialization Capstone Project",
                    "description": "Developing and integrating an AI Agent feature into a web platform using LLMs and LangChain.",
                    "durationHours": 30,
                },
            ],
        },
        {
            "id": make_id("mod_mern", 13),
            "title": "Phase 3 - Module 13: Full-Scale Capstone Project",
            "description": "Designing and building a production-style application combining foundations with chosen specialization.",
            "sequence": 13,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_mern", 1301),
                    "title": "Week 20-24: Full-Scale Capstone Development",
                    "description": "Complete production application integration using Node.js, React/Next.js, PostgreSQL, MongoDB, and DevOps/AI specialization.",
                    "durationHours": 60,
                },
            ],
        },
        {
            "id": make_id("mod_mern", 14),
            "title": "Phase 3 - Module 14: Buffer, Deployment & Final Presentation",
            "description": "Final touches, cloud deployment, and live presentation.",
            "sequence": 14,
            "fee": 1000.0,
            "topics": [
                {
                    "id": make_id("top_mern", 1401),
                    "title": "Week 25-26: Buffer, Live Deployment & Capstone Presentation",
                    "description": "Final application polishing, staging-to-production deployment, demo video preparation, and project presentation.",
                    "durationHours": 20,
                },
            ],
        },
    ]


def build_python_phase1_modules():
    return [
        {
            "id": make_id("mod_py", 1),
            "title": "Phase 1 - Module 1: Frontend Basics (HTML & CSS)",
            "description": "Semantic HTML, CSS fundamentals, layout (Flexbox/Grid), and building static responsive pages.",
            "sequence": 1,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_py", 101),
                    "title": "Week 1-2: Semantic HTML & CSS Fundamentals",
                    "description": "Semantic markup, styling rules, box model, CSS layout algorithms, and mobile responsive structure.",
                    "durationHours": 15,
                },
                {
                    "id": make_id("top_py", 102),
                    "title": "Week 1-2: Responsive Layouts with Flexbox & Grid",
                    "description": "Flexbox layouts, CSS Grid, media queries, and responsive component design.",
                    "durationHours": 15,
                },
            ],
        },
        {
            "id": make_id("mod_py", 2),
            "title": "Phase 1 - Module 2: Frontend Framework (Tailwind CSS + React / Next.js)",
            "description": "Utility-first styling with Tailwind CSS and React / Next.js web development.",
            "sequence": 2,
            "fee": 2500.0,
            "topics": [
                {
                    "id": make_id("top_py", 201),
                    "title": "Week 3-4: Utility-First Styling with Tailwind CSS",
                    "description": "Tailwind utilities, custom configuration, responsive modifiers, and modern UI creation.",
                    "durationHours": 15,
                },
                {
                    "id": make_id("top_py", 202),
                    "title": "Week 3-4: React & Next.js Fundamentals",
                    "description": "React components, props, hooks (useState, useEffect), Next.js App Router, and state handling.",
                    "durationHours": 15,
                },
            ],
        },
        {
            "id": make_id("mod_py", 3),
            "title": "Phase 1 - Module 3: Backend APIs (FastAPI)",
            "description": "Building high-performance asynchronous REST APIs with FastAPI.",
            "sequence": 3,
            "fee": 2500.0,
            "topics": [
                {
                    "id": make_id("top_py", 301),
                    "title": "Week 5-6: Building Async REST APIs with FastAPI",
                    "description": "FastAPI async endpoints, Pydantic schemas, Dependency Injection, JWT authentication, and CORS configuration.",
                    "durationHours": 30,
                },
            ],
        },
        {
            "id": make_id("mod_py", 4),
            "title": "Phase 1 - Module 4: Python Backend ORMs",
            "description": "Database integration in FastAPI using SQLAlchemy and SQLModel.",
            "sequence": 4,
            "fee": 1500.0,
            "topics": [
                {
                    "id": make_id("top_py", 401),
                    "title": "Week 7: Connecting FastAPI to Databases via ORMs",
                    "description": "Async SQLAlchemy, SQLModel, schema mappings, session handling, Alembic migrations, and database operations.",
                    "durationHours": 15,
                },
            ],
        },
        {
            "id": make_id("mod_py", 5),
            "title": "Phase 1 - Module 5: Database - PostgreSQL (SQL)",
            "description": "Relational database design, SQL queries, joins, and FastAPI integration.",
            "sequence": 5,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_py", 501),
                    "title": "Week 8: Relational DB Design, SQL Queries & Integration",
                    "description": "PostgreSQL installation, normalized tables, complex queries, JOINs, indexing, and FastAPI connection pooling.",
                    "durationHours": 15,
                },
            ],
        },
        {
            "id": make_id("mod_py", 6),
            "title": "Phase 1 - Module 6: Database - MongoDB (NoSQL)",
            "description": "Document-based data modeling, CRUD operations, and async MongoDB drivers.",
            "sequence": 6,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_py", 601),
                    "title": "Week 9: Document Data Modeling & MongoDB Integration",
                    "description": "NoSQL concepts, Motor async driver, Beanie ODM, document CRUD operations, and FastAPI integration.",
                    "durationHours": 15,
                },
            ],
        },
        {
            "id": make_id("mod_py", 7),
            "title": "Phase 1 - Module 7: Buffer & Catch-Up Week",
            "description": "Reserved for concept review and catching up before starting capstone project.",
            "sequence": 7,
            "fee": 500.0,
            "topics": [
                {
                    "id": make_id("top_py", 701),
                    "title": "Week 10: Buffer / Catch-Up Week",
                    "description": "Reviewing FastAPI backend, React frontend, and dual database integration before capstone work.",
                    "durationHours": 10,
                },
            ],
        },
        {
            "id": make_id("mod_py", 8),
            "title": "Phase 1 - Module 8: Foundation Capstone Project",
            "description": "Building a full-stack project utilizing FastAPI, React/Next.js, PostgreSQL, and MongoDB.",
            "sequence": 8,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_py", 801),
                    "title": "Week 11-13: Foundation Capstone Project",
                    "description": "Full-stack application built using FastAPI, React / Next.js, PostgreSQL, and MongoDB.",
                    "durationHours": 40,
                },
            ],
        },
    ]


def build_python_specialization_and_capstone_modules():
    return [
        {
            "id": make_id("mod_py", 9),
            "title": "Phase 2 - Module 9: Track A - DevOps Specialization",
            "description": "Cloud infrastructure, Version Control, CI/CD, Docker, Nginx, and SSL certificates.",
            "sequence": 9,
            "fee": 3000.0,
            "topics": [
                {
                    "id": make_id("top_py", 901),
                    "title": "Week 14: Cloud Fundamentals & Digital Ocean",
                    "description": "Droplet provisioning, SSH security, server setup, and Linux server management.",
                    "durationHours": 10,
                },
                {
                    "id": make_id("top_py", 902),
                    "title": "Week 15: Version Control & CI/CD Pipelines",
                    "description": "Git repository management, GitHub Actions, automated testing, and CI/CD pipelines.",
                    "durationHours": 10,
                },
                {
                    "id": make_id("top_py", 903),
                    "title": "Week 16: Docker Containerization",
                    "description": "Dockerizing FastAPI and React apps, writing Dockerfiles, and orchestrating containers with Docker Compose.",
                    "durationHours": 10,
                },
                {
                    "id": make_id("top_py", 904),
                    "title": "Week 17: Reverse Proxy, SSL & Nginx",
                    "description": "Nginx web server setup, reverse proxy configuration, Domain pointing, and Let's Encrypt SSL/TLS.",
                    "durationHours": 10,
                },
            ],
        },
        {
            "id": make_id("mod_py", 10),
            "title": "Phase 2 - Module 10: Track A - DevOps Specialization Capstone",
            "description": "Capstone project deploying FastAPI full stack app with Docker, CI/CD, and Nginx.",
            "sequence": 10,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_py", 1001),
                    "title": "Week 18-19: DevOps Specialization Capstone Project",
                    "description": "Full automated deployment pipeline setup for Python stack application.",
                    "durationHours": 30,
                },
            ],
        },
        {
            "id": make_id("mod_py", 11),
            "title": "Phase 2 - Module 11: Track B - AI/ML Specialization",
            "description": "AI/ML fundamentals, LLM API integration, Agentic AI, MCP, and LangChain.",
            "sequence": 11,
            "fee": 3000.0,
            "topics": [
                {
                    "id": make_id("top_py", 1101),
                    "title": "Week 14: AI/ML Foundations",
                    "description": "Overview of AI/ML concepts, machine learning models, and applied LLM architecture.",
                    "durationHours": 10,
                },
                {
                    "id": make_id("top_py", 1102),
                    "title": "Week 15: Large Language Models (LLMs)",
                    "description": "Integrating LLM APIs (OpenAI/Anthropic), prompt engineering, embeddings, and vector stores.",
                    "durationHours": 10,
                },
                {
                    "id": make_id("top_py", 1103),
                    "title": "Week 16: Agentic AI & Model Context Protocol (MCP)",
                    "description": "Agentic AI concepts, autonomous decision loops, tool usage, and MCP protocol integration.",
                    "durationHours": 10,
                },
                {
                    "id": make_id("top_py", 1104),
                    "title": "Week 17: LangChain Framework",
                    "description": "Building AI Agents in Python using LangChain, memory modules, custom tools, and chains.",
                    "durationHours": 10,
                },
            ],
        },
        {
            "id": make_id("mod_py", 12),
            "title": "Phase 2 - Module 12: Track B - AI/ML Specialization Capstone",
            "description": "Capstone project developing an AI Agent integrated with FastAPI backend.",
            "sequence": 12,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_py", 1201),
                    "title": "Week 18-19: AI/ML Specialization Capstone Project",
                    "description": "Building an AI Agent service using LLMs, MCP, and LangChain integrated into FastAPI.",
                    "durationHours": 30,
                },
            ],
        },
        {
            "id": make_id("mod_py", 13),
            "title": "Phase 3 - Module 13: Full-Scale Capstone Project",
            "description": "Designing and building a production-style application combining Python foundations with chosen specialization.",
            "sequence": 13,
            "fee": 2000.0,
            "topics": [
                {
                    "id": make_id("top_py", 1301),
                    "title": "Week 20-24: Full-Scale Capstone Development",
                    "description": "Complete production-style application using FastAPI, React/Next.js, PostgreSQL, MongoDB, and chosen DevOps/AI track.",
                    "durationHours": 60,
                },
            ],
        },
        {
            "id": make_id("mod_py", 14),
            "title": "Phase 3 - Module 14: Buffer, Deployment & Final Presentation",
            "description": "Final touches, cloud deployment, and live presentation.",
            "sequence": 14,
            "fee": 1000.0,
            "topics": [
                {
                    "id": make_id("top_py", 1401),
                    "title": "Week 25-26: Buffer, Live Deployment & Capstone Presentation",
                    "description": "Final polish, live deployment, presentation deck, and project demo.",
                    "durationHours": 20,
                },
            ],
        },
    ]


async def seed_courses():
    async with AsyncSessionLocal() as db:
        print("Cleaning up old portal courses...")
        await db.execute(delete(TrainingPortalCourse))
        await db.commit()

        now = datetime.utcnow()

        # 1. MERN Stack (3 Months Foundations)
        mern_3m_modules = build_mern_phase1_modules()
        mern_3m = TrainingPortalCourse(
            id=str(uuid.uuid4()),
            title="MERN Stack Web Development (3 Months Foundations)",
            description="3-Month intensive web development program covering Frontend (HTML, CSS, Tailwind CSS, React, Next.js), Backend (Node.js REST APIs, ORMs), Dual Databases (PostgreSQL & MongoDB), culminating in a Foundation Capstone Project.",
            category="Software Development",
            duration="3 Months",
            delivery_mode="Offline",
            status="published",
            skill_level="Beginner",
            fee=25000.0,
            emi_fee=9000.0,
            thumbnail_url=None,
            prerequisites="Basic computer literacy, logical reasoning, and passion for programming.",
            key_highlights=[
                "3-Month Core Web Development Foundations",
                "Dual Database Exposure: PostgreSQL (SQL) + MongoDB (NoSQL)",
                "Full-stack JavaScript (React, Next.js, Node.js, Express)",
                "Hands-on Foundation Capstone Project",
            ],
            curriculum=mern_3m_modules,
            created_at=now,
            updated_at=now,
        )

        # 2. MERN Stack (6 Months Master)
        mern_6m_modules = build_mern_phase1_modules() + build_mern_specialization_and_capstone_modules()
        mern_6m = TrainingPortalCourse(
            id=str(uuid.uuid4()),
            title="Full Stack MERN & AI/DevOps Master Program (6 Months)",
            description="6-Month comprehensive training program following the MERN/JavaScript track. Includes 3 months of core Foundations, 1.5 months of Specialization (DevOps or AI/ML track), and a 1-month full-scale capstone project.",
            category="Software Development",
            duration="6 Months",
            delivery_mode="Offline",
            status="published",
            skill_level="Beginner",
            fee=42000.0,
            emi_fee=7500.0,
            thumbnail_url=None,
            prerequisites="Basic computer literacy and problem-solving skills.",
            key_highlights=[
                "Complete 6-Month Full Stack MERN Journey",
                "Phase 1 Foundations + Phase 2 Specialization (DevOps or AI/ML) + Phase 3 Final Capstone",
                "Dual Databases: PostgreSQL (SQL) & MongoDB (NoSQL)",
                "Production deployment, Docker, Nginx, CI/CD, LLM integration & AI Agents",
            ],
            curriculum=mern_6m_modules,
            created_at=now,
            updated_at=now,
        )

        # 3. Python Stack (3 Months Foundations)
        py_3m_modules = build_python_phase1_modules()
        py_3m = TrainingPortalCourse(
            id=str(uuid.uuid4()),
            title="Python Full Stack Development (3 Months Foundations)",
            description="3-Month intensive Python full-stack program covering Frontend (HTML, CSS, Tailwind CSS, React, Next.js), Async Backend (FastAPI APIs, SQLAlchemy), Dual Databases (PostgreSQL & MongoDB), and a Foundation Capstone Project.",
            category="Software Development",
            duration="3 Months",
            delivery_mode="Offline",
            status="published",
            skill_level="Beginner",
            fee=25000.0,
            emi_fee=9000.0,
            thumbnail_url=None,
            prerequisites="Basic understanding of programming concepts and logic.",
            key_highlights=[
                "3-Month Core Python Full Stack Foundations",
                "Modern Async Backend with FastAPI & Pydantic",
                "Dual Databases: PostgreSQL (SQL) + MongoDB (NoSQL)",
                "Hands-on Foundation Capstone Project",
            ],
            curriculum=py_3m_modules,
            created_at=now,
            updated_at=now,
        )

        # 4. Python Stack (6 Months Master)
        py_6m_modules = build_python_phase1_modules() + build_python_specialization_and_capstone_modules()
        py_6m = TrainingPortalCourse(
            id=str(uuid.uuid4()),
            title="Full Stack Python & AI/DevOps Master Program (6 Months)",
            description="6-Month comprehensive training program following the Python Stack track. Features 3 months of FastAPI & React foundations, 1.5 months of DevOps or AI/ML specialization, and a 1-month full-scale capstone project.",
            category="Software Development",
            duration="6 Months",
            delivery_mode="Offline",
            status="published",
            skill_level="Beginner",
            fee=42000.0,
            emi_fee=7500.0,
            thumbnail_url=None,
            prerequisites="Basic computer skills and problem-solving mindset.",
            key_highlights=[
                "Complete 6-Month Python Full Stack Master Program",
                "Phase 1 Foundations + Phase 2 Specialization (DevOps or AI/ML) + Phase 3 Final Capstone",
                "High-performance FastAPI backend + Dual DB (PostgreSQL & MongoDB)",
                "Enterprise DevOps deployment pipeline & Agentic AI / LLM development",
            ],
            curriculum=py_6m_modules,
            created_at=now,
            updated_at=now,
        )

        db.add_all([mern_3m, mern_6m, py_3m, py_6m])
        await db.commit()
        print("Successfully seeded 4 courses with complete phase-wise and module-wise curriculums into DB!")


if __name__ == "__main__":
    asyncio.run(seed_courses())
