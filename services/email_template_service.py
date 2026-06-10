import re
from datetime import datetime
from typing import Any, Optional

from jinja2 import Environment, Template, select_autoescape

from models.email_template import EmailTemplate
from models.user import User, UserRole

_jinja_env = Environment(autoescape=select_autoescape(["html", "xml"]))

SAMPLE_CONTEXT = {
    "first_name": "Rahul",
    "last_name": "Sharma",
    "name": "Rahul Sharma",
    "email": "rahul@example.com",
    "industry": "Information Technology",
    "company_name": "Tech Solutions Pvt Ltd",
    "role_label": "Job Seeker",
    "phone": "9876543210",
    "year": datetime.utcnow().year,
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-") or "template"


def build_user_context(user: User) -> dict[str, Any]:
    first = user.first_name or ""
    last = user.last_name or ""
    full_name = f"{first} {last}".strip() or "User"
    role_label = "Job Provider" if user.role == UserRole.provider else "Job Seeker"
    return {
        "first_name": first or "User",
        "last_name": last,
        "name": full_name,
        "email": user.email or "",
        "industry": user.industry or "",
        "company_name": user.company_name or "",
        "role_label": role_label,
        "phone": user.phone or "",
        "year": datetime.utcnow().year,
    }


def render_template_string(template_str: str, context: dict[str, Any]) -> str:
    return _jinja_env.from_string(template_str).render(**context)


def render_email_template(
    template: EmailTemplate,
    context: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    ctx = {**SAMPLE_CONTEXT, **(context or {})}
    subject = render_template_string(template.subject, ctx)
    html_body = render_template_string(template.html_body, ctx)
    return subject, html_body


def preview_email(
    subject: str,
    html_body: str,
    sample_data: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    ctx = {**SAMPLE_CONTEXT, **(sample_data or {})}
    return render_template_string(subject, ctx), render_template_string(html_body, ctx)
