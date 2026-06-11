import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, Template, select_autoescape

from config import settings
from models.email_template import EmailTemplate
from models.user import User, UserRole

_EMAIL_ASSETS_SUBDIR = "email_assets"
_UPLOADS_ROOT = Path(settings.UPLOAD_DIR)

_BRAND_LOGO_FILES: dict[str, tuple[str, ...]] = {
    "cicu_logo": ("cicu_logo.jpg", "cicu_logo.png"),
    "rojgar_logo": ("rojgar_logo.png",),
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
    "email": "rahul@example.com",
    "password": "",
    "profile_link": f"{settings.FRONTEND_URL.rstrip('/')}/login",
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
    """Resolve a cid: content id to a file under uploads/."""
    for filename in _BRAND_LOGO_FILES.get(content_id, ()):
        path = _UPLOADS_ROOT / filename
        if path.is_file():
            return path

    assets_dir = _UPLOADS_ROOT / _EMAIL_ASSETS_SUBDIR
    if assets_dir.is_dir():
        for path in assets_dir.glob(f"{content_id}.*"):
            if path.is_file():
                return path
    return None


def cid_to_public_url(content_id: str) -> Optional[str]:
    path = cid_to_file_path(content_id)
    if not path:
        return None
    rel = path.relative_to(_UPLOADS_ROOT)
    return f"/uploads/{rel.as_posix()}"


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
    html = html.replace(CICU_LOGO_URL, "cid:cicu_logo")
    html = html.replace(ROJGAR_LOGO_URL, "cid:rojgar_logo")
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
    path = _UPLOADS_ROOT / _EMAIL_ASSETS_SUBDIR
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
