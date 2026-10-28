"""
Seed / Sync Email Templates into the database (email_templates table).
Reads HTML template files from app/shared/templates/ and stores them into the database
so they can be managed, fetched, and rendered dynamically with fallback support.

Usage:
    docker compose exec backend python scripts/seed_email_templates.py
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add backend root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, import_all_models
from app.modules.super_admin.models.email_template import EmailTemplate, EmailTemplateCategory

import_all_models()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "app" / "shared" / "templates"

TEMPLATE_DEFINITIONS = [
    {
        "slug": "interview-scheduled",
        "filename": "interview_scheduled_email.html",
        "name": "Interview Scheduled Notification",
        "subject": "Interview Scheduled: {{ job_title }} at {{ company_name }}",
        "category": EmailTemplateCategory.custom,
        "description": "Sent to job seeker when a recruiter schedules an interview (virtual or in-person).",
    },
    {
        "slug": "job-match",
        "filename": "job_match_email.html",
        "name": "AI Job Match Notification",
        "subject": "🎯 AI Job Match: {{ job_title }} at {{ company_name }} ({{ match_score }}% Match)",
        "category": EmailTemplateCategory.custom,
        "description": "Sent to job seeker when AI finds a high compatibility job match.",
    },
    {
        "slug": "candidate-match",
        "filename": "candidate_match_email.html",
        "name": "AI Candidate Match Notification",
        "subject": "🌟 Top Candidate Matched: {{ candidate_name }} for '{{ job_title }}' ({{ match_score }}% Match)",
        "category": EmailTemplateCategory.custom,
        "description": "Sent to employer/recruiter when AI matches a qualified candidate to their job opening.",
    },
    {
        "slug": "welcome-email",
        "filename": "welcome_email.html",
        "name": "Welcome to RojgarMela.AI",
        "subject": "Welcome to RojgarMela.AI!",
        "category": EmailTemplateCategory.custom,
        "description": "Sent upon user registration with platform introduction and role-specific steps.",
    },
    {
        "slug": "otp-email",
        "filename": "otp_email.html",
        "name": "Verify Your Email OTP",
        "subject": "Verify Your Email – RojgarMela.AI",
        "category": EmailTemplateCategory.custom,
        "description": "Verification code email for signup and authentication.",
    },
]


async def seed_templates():
    print(f"[*] Starting Email Template database sync from: {TEMPLATES_DIR}")
    if not TEMPLATES_DIR.exists():
        print(f"[!] Templates directory does not exist: {TEMPLATES_DIR}")
        return

    synced_count = 0
    async with AsyncSessionLocal() as session:
        for item in TEMPLATE_DEFINITIONS:
            file_path = TEMPLATES_DIR / item["filename"]
            if not file_path.is_file():
                print(f"[!] Warning: File {item['filename']} not found. Skipping.")
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                html_body = f.read()

            stmt = select(EmailTemplate).where(EmailTemplate.slug == item["slug"])
            result = await session.execute(stmt)
            existing: EmailTemplate | None = result.scalar_one_or_none()

            if existing:
                existing.name = item["name"]
                existing.subject = item["subject"]
                existing.html_body = html_body
                existing.description = item.get("description", existing.description)
                existing.is_active = True
                existing.is_system = True
                existing.updated_at = datetime.utcnow()
                print(f"[✓] Updated template in DB: '{item['slug']}' ({len(html_body)} bytes)")
            else:
                new_template = EmailTemplate(
                    id=str(uuid.uuid4()),
                    slug=item["slug"],
                    name=item["name"],
                    subject=item["subject"],
                    html_body=html_body,
                    description=item.get("description"),
                    category=item["category"],
                    design_config={},
                    placeholders={},
                    is_active=True,
                    is_system=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(new_template)
                print(f"[+] Created new template in DB: '{item['slug']}' ({len(html_body)} bytes)")

            synced_count += 1

        await session.commit()
        print(f"\n[✓] Successfully synchronized {synced_count} email templates to the database!")


if __name__ == "__main__":
    asyncio.run(seed_templates())
