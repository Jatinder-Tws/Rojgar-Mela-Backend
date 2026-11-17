"""Create event_categories table and seed built-in event categories.

Revision ID: h0i1j2k3l4m5
Revises: g9h0i1j2k3l4
Create Date: 2026-11-17 16:25:00.000000
"""

import uuid
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from migrations.helpers import (
    create_index_if_missing,
    drop_index_if_exists,
    table_exists,
)

revision: str = "h0i1j2k3l4m5"
down_revision: Union[str, None] = "g9h0i1j2k3l4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_CATEGORIES = [
    {
        "key": "job-fair",
        "name": "Job Fair",
        "description": "Employers and candidates meet for recruitment.",
        "icon_name": "Briefcase",
        "tag_color": "#F26522",
        "pill_bg": "rgba(242, 101, 34, 0.1)",
        "sort_order": 1,
    },
    {
        "key": "campus-placement-drive",
        "name": "Campus Placement Drive",
        "description": "Companies recruit students from colleges.",
        "icon_name": "GraduationCap",
        "tag_color": "#3B82F6",
        "pill_bg": "rgba(59, 130, 246, 0.1)",
        "sort_order": 2,
    },
    {
        "key": "walk-in-interview",
        "name": "Walk-in Interview",
        "description": "Candidates attend interviews directly.",
        "icon_name": "UserCheck",
        "tag_color": "#10B981",
        "pill_bg": "rgba(16, 185, 129, 0.1)",
        "sort_order": 3,
    },
    {
        "key": "recruitment-drive",
        "name": "Recruitment Drive",
        "description": "Hiring event for specific job roles.",
        "icon_name": "Users",
        "tag_color": "#8B5CF6",
        "pill_bg": "rgba(139, 92, 246, 0.1)",
        "sort_order": 4,
    },
    {
        "key": "career-counselling",
        "name": "Career Counselling",
        "description": "Career guidance and professional advice.",
        "icon_name": "Compass",
        "tag_color": "#06B6D4",
        "pill_bg": "rgba(6, 182, 212, 0.1)",
        "sort_order": 5,
    },
    {
        "key": "workshop",
        "name": "Workshop",
        "description": "Practical, skill-based learning sessions.",
        "icon_name": "Wrench",
        "tag_color": "#F59E0B",
        "pill_bg": "rgba(245, 158, 11, 0.1)",
        "sort_order": 6,
    },
    {
        "key": "webinar",
        "name": "Webinar",
        "description": "Online educational or professional session.",
        "icon_name": "Video",
        "tag_color": "#EC4899",
        "pill_bg": "rgba(236, 72, 153, 0.1)",
        "sort_order": 7,
    },
    {
        "key": "seminar",
        "name": "Seminar",
        "description": "Expert talks and knowledge-sharing sessions.",
        "icon_name": "Mic",
        "tag_color": "#6366F1",
        "pill_bg": "rgba(99, 102, 241, 0.1)",
        "sort_order": 8,
    },
    {
        "key": "conference",
        "name": "Conference",
        "description": "Large-scale professional or industry event.",
        "icon_name": "Building2",
        "tag_color": "#0284C7",
        "pill_bg": "rgba(2, 132, 199, 0.1)",
        "sort_order": 9,
    },
    {
        "key": "hackathon",
        "name": "Hackathon",
        "description": "Coding, innovation, and technology challenges.",
        "icon_name": "Code2",
        "tag_color": "#7C3AED",
        "pill_bg": "rgba(124, 58, 237, 0.1)",
        "sort_order": 10,
    },
    {
        "key": "training-program",
        "name": "Training Program",
        "description": "Professional or technical skills training.",
        "icon_name": "BookOpen",
        "tag_color": "#059669",
        "pill_bg": "rgba(5, 150, 105, 0.1)",
        "sort_order": 11,
    },
    {
        "key": "internship-drive",
        "name": "Internship Drive",
        "description": "Recruitment for internship opportunities.",
        "icon_name": "Sparkles",
        "tag_color": "#D97706",
        "pill_bg": "rgba(217, 119, 6, 0.1)",
        "sort_order": 12,
    },
    {
        "key": "networking-event",
        "name": "Networking Event",
        "description": "Connect employers, professionals, and candidates.",
        "icon_name": "Share2",
        "tag_color": "#2563EB",
        "pill_bg": "rgba(37, 99, 235, 0.1)",
        "sort_order": 13,
    },
    {
        "key": "entrepreneurship-event",
        "name": "Entrepreneurship Event",
        "description": "Startup, business, and innovation activities.",
        "icon_name": "Rocket",
        "tag_color": "#EA580C",
        "pill_bg": "rgba(234, 88, 12, 0.1)",
        "sort_order": 14,
    },
    {
        "key": "industry-visit",
        "name": "Industry Visit",
        "description": "Educational visits to companies or industries.",
        "icon_name": "Factory",
        "tag_color": "#475569",
        "pill_bg": "rgba(71, 85, 105, 0.1)",
        "sort_order": 15,
    },
    {
        "key": "college-fest",
        "name": "College Fest",
        "description": "College-level cultural, technical, or career events.",
        "icon_name": "PartyPopper",
        "tag_color": "#E11D48",
        "pill_bg": "rgba(225, 29, 72, 0.1)",
        "sort_order": 16,
    },
    {
        "key": "placement-preparation",
        "name": "Placement Preparation",
        "description": "Resume, aptitude, and interview preparation.",
        "icon_name": "FileCheck2",
        "tag_color": "#4F46E5",
        "pill_bg": "rgba(79, 70, 229, 0.1)",
        "sort_order": 17,
    },
    {
        "key": "skill-development",
        "name": "Skill Development",
        "description": "Upskilling and professional development.",
        "icon_name": "TrendingUp",
        "tag_color": "#0D9488",
        "pill_bg": "rgba(13, 148, 136, 0.1)",
        "sort_order": 18,
    },
    {
        "key": "government-job-awareness",
        "name": "Government Job Awareness",
        "description": "Guidance about government jobs and examinations.",
        "icon_name": "Landmark",
        "tag_color": "#9333EA",
        "pill_bg": "rgba(147, 51, 234, 0.1)",
        "sort_order": 19,
    },
    {
        "key": "scholarship-event",
        "name": "Scholarship Event",
        "description": "Scholarship awareness or application assistance.",
        "icon_name": "Award",
        "tag_color": "#0891B2",
        "pill_bg": "rgba(8, 145, 178, 0.1)",
        "sort_order": 20,
    },
    {
        "key": "other",
        "name": "Other",
        "description": "Any event not covered by the available categories.",
        "icon_name": "Layers",
        "tag_color": "#64748B",
        "pill_bg": "rgba(100, 116, 139, 0.1)",
        "sort_order": 21,
    },
]


def upgrade() -> None:
    if not table_exists("event_categories"):
        op.create_table(
            "event_categories",
            sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())),
            sa.Column("key", sa.String(length=80), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("icon_name", sa.String(length=50), nullable=False, server_default="Sparkles"),
            sa.Column("tag_color", sa.String(length=30), nullable=False, server_default="#64748B"),
            sa.Column("pill_bg", sa.String(length=50), nullable=False, server_default="rgba(100, 116, 139, 0.1)"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    create_index_if_missing("ix_event_categories_key", "event_categories", ["key"], unique=True)
    create_index_if_missing("ix_event_categories_is_active", "event_categories", ["is_active"])

    # Seed built-in categories safely (ON CONFLICT DO NOTHING)
    bind = op.get_bind()
    now = datetime.utcnow()
    for cat in DEFAULT_CATEGORIES:
        bind.execute(
            sa.text(
                """
                INSERT INTO event_categories (id, key, name, description, icon_name, tag_color, pill_bg, is_active, is_builtin, sort_order, created_at, updated_at)
                VALUES (:id, :key, :name, :description, :icon_name, :tag_color, :pill_bg, true, true, :sort_order, :now, :now)
                ON CONFLICT (key) DO NOTHING;
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "key": cat["key"],
                "name": cat["name"],
                "description": cat["description"],
                "icon_name": cat["icon_name"],
                "tag_color": cat["tag_color"],
                "pill_bg": cat["pill_bg"],
                "sort_order": cat["sort_order"],
                "now": now,
            },
        )


def downgrade() -> None:
    drop_index_if_exists("ix_event_categories_is_active", "event_categories")
    drop_index_if_exists("ix_event_categories_key", "event_categories")
    if table_exists("event_categories"):
        op.drop_table("event_categories")
