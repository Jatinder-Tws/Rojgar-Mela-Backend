"""
Supervisor permissions constants and catalog definition.
"""
from typing import Dict, List, Optional, TypedDict


class PermissionDefinition(TypedDict):
    key: str
    label: str
    description: str
    category: str
    platform: Optional[str]


class PermissionCategory(TypedDict):
    id: str
    name: str
    description: str
    platform: str
    permissions: List[PermissionDefinition]


SUPERVISOR_PERMISSIONS: List[PermissionDefinition] = [
    # Candidates & Recruiters
    {
        "key": "job_providers",
        "label": "Job Providers",
        "description": "View, verify, edit, and manage employer & provider accounts",
        "category": "Candidates & Recruiters",
        "platform": "job_portal",
    },
    {
        "key": "job_seekers",
        "label": "Job Seekers",
        "description": "View, search, edit, and manage candidate & job seeker profiles",
        "category": "Candidates & Recruiters",
        "platform": "job_portal",
    },
    {
        "key": "applications",
        "label": "Applications Pipeline",
        "description": "Track, filter, and moderate candidate job applications",
        "category": "Candidates & Recruiters",
        "platform": "job_portal",
    },

    # Opportunities & Matches
    {
        "key": "jobs",
        "label": "Job Postings",
        "description": "Review, publish, feature, or close job listings across the platform",
        "category": "Opportunities & Matches",
        "platform": "job_portal",
    },
    {
        "key": "internships",
        "label": "Internships",
        "description": "Manage internship programs and applications",
        "category": "Opportunities & Matches",
        "platform": "job_portal",
    },
    {
        "key": "roadmaps",
        "label": "Career Roadmaps",
        "description": "Create, edit, and manage structured career paths and guides",
        "category": "Opportunities & Matches",
        "platform": "job_portal",
    },
    {
        "key": "ai_matching",
        "label": "AI Matching Engine",
        "description": "Inspect candidate-job AI match scores and recommendation vectors",
        "category": "Opportunities & Matches",
        "platform": "job_portal",
    },
    {
        "key": "job_fairs",
        "label": "Job Fairs & Events",
        "description": "Create, edit, and oversee physical & virtual job fair events",
        "category": "Opportunities & Matches",
        "platform": "job_portal",
    },
    {
        "key": "attendance",
        "label": "Attendance & Check-in",
        "description": "View and manage job fair candidate check-ins and QR attendance",
        "category": "Opportunities & Matches",
        "platform": "job_portal",
    },

    # Learning & Support
    {
        "key": "help_desk",
        "label": "Help Desk & Tickets",
        "description": "Handle user support tickets, live queries, and bot resolution",
        "category": "Learning & Support",
        "platform": "job_portal",
    },
    {
        "key": "enquiries",
        "label": "Public Enquiries",
        "description": "Review and respond to platform contact inquiries and career queries",
        "category": "Learning & Support",
        "platform": "job_portal",
    },
    {
        "key": "blogs",
        "label": "Blog & Articles",
        "description": "Draft, edit, generate with AI, and publish blog articles",
        "category": "Learning & Support",
        "platform": "job_portal",
    },

    # Platform & Outreach
    {
        "key": "email_campaigns",
        "label": "Email Broadcasts",
        "description": "Compose and broadcast bulk targeted email campaigns",
        "category": "Platform & Outreach",
        "platform": "job_portal",
    },
    {
        "key": "email_templates",
        "label": "Email Templates",
        "description": "Design and manage branded visual email templates",
        "category": "Platform & Outreach",
        "platform": "job_portal",
    },
    {
        "key": "social_login",
        "label": "Social & Auth Config",
        "description": "Manage OAuth identity providers and authentication settings",
        "category": "Platform & Outreach",
        "platform": "job_portal",
    },
    {
        "key": "settings",
        "label": "Platform & Account Settings",
        "description": "Manage supervisor profile, passwords, portal preferences, and general settings",
        "category": "Platform & Outreach",
        "platform": "job_portal",
    },

    # Training Platform (Rojgar Mela Training)
    {
        "key": "training",
        "label": "Training Platform Access",
        "description": "Primary switch: Grant access to enter and operate the Rojgar Mela Training portal",
        "category": "Training Platform",
        "platform": "training_portal",
    },
    {
        "key": "training_courses",
        "label": "Courses & Curriculums",
        "description": "Create, edit, publish, and manage physical & online course offerings",
        "category": "Training Platform",
        "platform": "training_portal",
    },
    {
        "key": "training_batches",
        "label": "Batches & Class Schedules",
        "description": "Schedule batch sessions, manage timings, and assign classroom instructors",
        "category": "Training Platform",
        "platform": "training_portal",
    },
    {
        "key": "training_teachers",
        "label": "Instructors & Faculty",
        "description": "Manage teacher directory, bio credentials, and assigned batches",
        "category": "Training Platform",
        "platform": "training_portal",
    },
    {
        "key": "training_students",
        "label": "Enrolled Students & KYC",
        "description": "Track student registrations, document verification, and batch allotments",
        "category": "Training Platform",
        "platform": "training_portal",
    },
    {
        "key": "training_fees",
        "label": "Fee Ledger & Transactions",
        "description": "Inspect fee collections, EMI installments, receipts, and refund requests",
        "category": "Training Platform",
        "platform": "training_portal",
    },
    {
        "key": "training_attendance",
        "label": "Attendance & Leave Approvals",
        "description": "Review daily student classroom attendance and process leave requests",
        "category": "Training Platform",
        "platform": "training_portal",
    },
    {
        "key": "training_certifications",
        "label": "Certificates & Badges",
        "description": "Generate, issue, and verify student course completion certificates",
        "category": "Training Platform",
        "platform": "training_portal",
    },
    {
        "key": "training_analytics",
        "label": "Training Analytics & Reports",
        "description": "Analyze batch completion rates, attendance stats, and revenue performance",
        "category": "Training Platform",
        "platform": "training_portal",
    },
]

VALID_PERMISSION_KEYS = {p["key"] for p in SUPERVISOR_PERMISSIONS}


def get_categorized_permissions() -> List[PermissionCategory]:
    """Returns permissions grouped by category for UI displays."""
    categories_map: Dict[str, List[PermissionDefinition]] = {}
    cat_platform_map: Dict[str, str] = {}
    for perm in SUPERVISOR_PERMISSIONS:
        cat = perm["category"]
        if cat not in categories_map:
            categories_map[cat] = []
        categories_map[cat].append(perm)
        cat_platform_map[cat] = perm.get("platform", "job_portal")

    return [
        {
            "id": cat.lower().replace(" & ", "_").replace(" ", "_"),
            "name": cat,
            "description": f"Permissions relating to {cat.lower()}",
            "platform": cat_platform_map.get(cat, "job_portal"),
            "permissions": perms,
        }
        for cat, perms in categories_map.items()
    ]
