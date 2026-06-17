import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, Template, select_autoescape

from config import settings
from models.email_template import EmailTemplate
from models.user import User, UserRole

_EMAIL_ASSETS_SUBDIR = "email_assets"
_BACKEND_ROOT = Path(__file__).parent.parent
_STATIC_EMAIL_DIR = _BACKEND_ROOT / "static" / "email"

_BRAND_LOGO_FILES: dict[str, tuple[str, ...]] = {
    "cicu_logo": ("cicu_logo.jpg", "cicu_logo.png"),
    "lgc_logo": ("lgc_logo.png", "lgc_logo.jpg", "lgc_logo.jpeg"),
    "rojgar_logo": ("rojgar_logo.png",),
    "job_carnival_flyer": (
        "email_assets/job_carnival_flyer.png",
        "email_assets/job_carnival_flyer.jpg",
        "email_assets/job_carnival_flyer.jpeg",
    ),
}

# Bundled logos shipped with the backend (fallback when uploads/ is empty).
_STATIC_BRAND_LOGOS: dict[str, Path] = {
    "rojgar_logo": _STATIC_EMAIL_DIR / "rojgar_logo.png",
}

DEFAULT_IMG_STYLE = "max-width:100%;height:auto;display:block;"
LOGO_IMG_STYLE = "height:56px;width:auto;max-width:240px;display:block;object-fit:contain;"

_jinja_env = Environment(autoescape=select_autoescape(["html", "xml"]))

# External logo URLs used in legacy templates — replaced with cid: at send time.
CICU_LOGO_URL = (
    "https://spatial-aqua-roadrunner.myfilebase.com/ipfs/"
    "QmSXRsnibbzf9yNo8Zqieqc35Ybbu5wn1YneR9MJkjgM9u"
)
ROJGAR_LOGO_URL = (
    "https://spatial-aqua-roadrunner.myfilebase.com/ipfs/"
    "QmP8nbxreh5FS1KABK3599syFUFY5UoV7hHcrA9riAfRxT"
)

SAMPLE_CONTEXT = {
    "first_name": "Rahul",
    "last_name": "Sharma",
    "name": "Rahul Sharma",
    "seeker_name": "Rahul Sharma",
    "recipient_name": "Rahul Sharma",
    "email": "rahul@example.com",
    "password": "",
    "profile_link": f"{settings.FRONTEND_URL.rstrip('/')}/login",
    "login_url": f"{settings.FRONTEND_URL.rstrip('/')}/login",
    "industry": "Information Technology",
    "company_name": "Tech Solutions Pvt Ltd",
    "role": "seeker",
    "role_label": "Job Seeker",
    "is_seeker": True,
    "is_provider": False,
    "phone": "9876543210",
    "year": datetime.utcnow().year,
    "support_email": settings.SUPPORT_EMAIL,
    "support_phones": settings.SUPPORT_PHONES,
    "job_fair_title": "The Job Carnival 2026",
    "job_fair_slug": "job-carnival-2026",
    "job_fair_location": "Chaukimann, Ferozepur Road, Ludhiana",
    "job_fair_description": "",
    "collaboration_text": "In Collaboration with District Bureau of Employment & Enterprises (DBEE)",
    "job_fair_date_display": "Friday, 19th June, 2026",
    "job_fair_time_display": "9:30 AM Onwards",
    "banner_image_url": None,
    "event_helpline": "81464-07200",
    "host_organization": "",
}


def uploads_root() -> Path:
    """Absolute path to the uploads directory (works in Docker and local dev)."""
    root = Path(settings.UPLOAD_DIR)
    if not root.is_absolute():
        root = _BACKEND_ROOT / root
    return root


def _upload_rel_to_cid(relative_path: str) -> str:
    return "u__" + relative_path.replace("/", "__")


def _cid_to_upload_rel(content_id: str) -> Optional[str]:
    if content_id.startswith("u__"):
        return content_id[3:].replace("__", "/")
    return None


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
    login_url = f"{settings.FRONTEND_URL.rstrip('/')}/login"
    return {
        "first_name": first or "User",
        "last_name": last,
        "name": full_name,
        "seeker_name": full_name,
        "email": user.email or "",
        "password": "",
        "profile_link": login_url,
        "industry": user.industry or "",
        "company_name": user.company_name or "",
        "role_label": role_label,
        "phone": user.phone or "",
        "year": datetime.utcnow().year,
    }


def cid_to_file_path(content_id: str) -> Optional[Path]:
    """Resolve a cid: content id to a local image file."""
    static_path = _STATIC_BRAND_LOGOS.get(content_id)
    if static_path and static_path.is_file():
        return static_path

    uploads = uploads_root()
    for filename in _BRAND_LOGO_FILES.get(content_id, ()):
        path = uploads / filename
        if path.is_file():
            return path

    upload_rel = _cid_to_upload_rel(content_id)
    if upload_rel:
        path = uploads / upload_rel
        if path.is_file():
            return path

    assets_dir = uploads / _EMAIL_ASSETS_SUBDIR
    if assets_dir.is_dir():
        for path in assets_dir.glob(f"{content_id}.*"):
            if path.is_file():
                return path
    return None


def cid_to_public_url(content_id: str) -> Optional[str]:
    path = cid_to_file_path(content_id)
    if not path:
        return None
    uploads = uploads_root()
    try:
        rel = path.relative_to(uploads)
        return f"/uploads/{rel.as_posix()}"
    except ValueError:
        return None


def _replace_external_logo_urls(html: str) -> str:
    """Swap known external logo URLs for cid: only when the local file exists."""
    if cid_to_file_path("cicu_logo"):
        html = html.replace(CICU_LOGO_URL, "cid:cicu_logo")
    if cid_to_file_path("rojgar_logo"):
        html = html.replace(ROJGAR_LOGO_URL, "cid:rojgar_logo")
    return html


def _replace_upload_urls_with_cid(html: str) -> str:
    """Convert local /uploads/... image URLs to cid: for MIME inline attachment."""
    uploads = uploads_root()
    frontend = settings.FRONTEND_URL.rstrip("/")

    def _to_cid(match: re.Match[str]) -> str:
        quote = match.group(1)
        upload_path = match.group(2)
        rel = upload_path.removeprefix("/uploads/").lstrip("/")
        if (uploads / rel).is_file():
            return f'src={quote}cid:{_upload_rel_to_cid(rel)}{quote}'
        return match.group(0)

    html = re.sub(r'src=(["\'])(/uploads/[^"\']+)\1', _to_cid, html)
    html = re.sub(
        rf'src=(["\']){re.escape(frontend)}(/uploads/[^"\']+)\1',
        _to_cid,
        html,
    )
    return html


def resolve_cids_for_preview(html_body: str) -> str:
    """Replace cid: image references with /uploads/ URLs for browser preview."""
    def _replace_src(match: re.Match[str]) -> str:
        quote = match.group(1)
        content_id = match.group(2)
        url = cid_to_public_url(content_id)
        if url:
            return f"src={quote}{url}{quote}"
        return match.group(0)

    html = re.sub(r'src=(["\'])cid:([^"\']+)\1', _replace_src, html_body)
    # Legacy external logo URLs should preview as local uploads when possible.
    html = html.replace(CICU_LOGO_URL, cid_to_public_url("cicu_logo") or CICU_LOGO_URL)
    html = html.replace(ROJGAR_LOGO_URL, cid_to_public_url("rojgar_logo") or ROJGAR_LOGO_URL)
    return html


def prepare_html_for_delivery(html_body: str) -> str:
    """Normalize campaign HTML: inline logos, uploaded assets, strip placeholders."""
    html = html_body
    html = _replace_external_logo_urls(html)
    html = _replace_upload_urls_with_cid(html)
    # Uploaded template images stored as /uploads/email_assets/email_img_*.ext → cid:
    html = re.sub(
        r'src=(["\'])/uploads/email_assets/(email_img_[^"\']+?)\.(?:png|jpe?g|gif|webp)\1',
        lambda m: f'src={m.group(1)}cid:{m.group(2)}{m.group(1)}',
        html,
        flags=re.I,
    )
    html = re.sub(r"(?i)(?<![\w>])undefined(?![\w<])", "", html)
    return html


def build_image_html_snippet(content_id: str, *, alt: str = "", logo: bool = False) -> str:
    style = LOGO_IMG_STYLE if logo else DEFAULT_IMG_STYLE
    alt_attr = f' alt="{alt}"' if alt else ""
    return f'<img src="cid:{content_id}"{alt_attr} style="{style}" />'


def email_assets_dir() -> Path:
    path = uploads_root() / _EMAIL_ASSETS_SUBDIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def render_template_string(template_str: str, context: dict[str, Any]) -> str:
    return _jinja_env.from_string(template_str).render(**context)


def render_email_template(
    template: EmailTemplate,
    context: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    ctx = {**SAMPLE_CONTEXT, **(context or {})}
    subject = render_template_string(template.subject, ctx)
    html_body = prepare_html_for_delivery(render_template_string(template.html_body, ctx))
    return subject, html_body


def preview_email(
    subject: str,
    html_body: str,
    sample_data: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    ctx = {**SAMPLE_CONTEXT, **(sample_data or {})}
    rendered_subject = render_template_string(subject, ctx)
    rendered_html = resolve_cids_for_preview(render_template_string(html_body, ctx))
    return rendered_subject, rendered_html
