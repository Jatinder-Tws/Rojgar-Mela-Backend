from datetime import datetime, date
from pathlib import Path
from typing import Optional
import re
import uuid

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.utils import parseaddr
from jinja2 import Environment, FileSystemLoader

from config import settings

# Template engine
_template_dir = Path(__file__).parent.parent / "templates"
_env = Environment(loader=FileSystemLoader(str(_template_dir)), autoescape=True)

_UPLOADS_DIR = Path(__file__).parent.parent / "uploads"

_INLINE_LOGOS = (
    ("cicu_logo", ("cicu_logo.jpg", "cicu_logo.png")),
    ("rojgar_logo", ("rojgar_logo.png",)),
)


def _sender_domain() -> str:
    _, addr = parseaddr(settings.SMTP_FROM)
    if addr and "@" in addr:
        return addr.split("@", 1)[1]
    return "rojgarmela.ai"


def _message_id() -> str:
    return f"<{uuid.uuid4().hex}@{_sender_domain()}>"


def _html_to_plain_text(html_body: str) -> str:
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", html_body)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^<]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _apply_common_headers(msg: MIMEMultipart, to_email: str, subject: str, *, is_bulk: bool = False) -> None:
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg["Message-ID"] = _message_id()
    msg["Reply-To"] = settings.SMTP_USER or parseaddr(settings.SMTP_FROM)[1]
    if is_bulk:
        msg["Precedence"] = "bulk"
        reply_addr = parseaddr(settings.SMTP_FROM)[1] or settings.SMTP_USER
        if reply_addr:
            msg["List-Unsubscribe"] = f"<mailto:{reply_addr}?subject=unsubscribe>"


def _attach_inline_image(msg: MIMEMultipart, file_path: Path, content_id: str) -> None:
    """Attach a local image for use as cid: in HTML email bodies."""
    if not file_path.is_file():
        return
    suffix = file_path.suffix.lower()
    subtype = "jpeg" if suffix in {".jpg", ".jpeg"} else "png"
    with open(file_path, "rb") as f:
        data = f.read()
    image = MIMEImage(data, _subtype=subtype)
    image.add_header("Content-ID", f"<{content_id}>")
    image.add_header("Content-Disposition", "inline", filename=file_path.name)
    msg.attach(image)


def _attach_brand_logos(msg: MIMEMultipart, html_body: str) -> None:
    """Attach CICU/Rojgar logos when the HTML references them via cid:."""
    if "cid:cicu_logo" not in html_body and "cid:rojgar_logo" not in html_body:
        return
    for content_id, filenames in _INLINE_LOGOS:
        if f"cid:{content_id}" not in html_body:
            continue
        for filename in filenames:
            path = _UPLOADS_DIR / filename
            if path.is_file():
                _attach_inline_image(msg, path, content_id)
                break


async def _deliver_message(msg: MIMEMultipart, to_email: str, *, raise_on_error: bool = False) -> None:
    try:
        use_tls = settings.SMTP_PORT == 465
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=use_tls,
            start_tls=settings.SMTP_TLS if not use_tls else False,
        )
    except Exception as e:
        err_msg = str(e) or "SMTP delivery failed"
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {err_msg}")
        if raise_on_error:
            raise RuntimeError(err_msg) from e


async def _send_email(to_email: str, subject: str, html_body: str, *, raise_on_error: bool = False) -> None:
    """Internal SMTP sender using aiosmtplib."""
    msg = MIMEMultipart("alternative")
    _apply_common_headers(msg, to_email, subject)
    text_body = _html_to_plain_text(html_body)
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    await _deliver_message(msg, to_email, raise_on_error=raise_on_error)


async def send_campaign_email(
    to_email: str,
    subject: str,
    html_body: str,
    *,
    raise_on_error: bool = False,
) -> None:
    """Send campaign HTML with inline brand logos and bulk-friendly headers."""
    msg = MIMEMultipart("related")
    _apply_common_headers(msg, to_email, subject, is_bulk=True)

    msg_alternative = MIMEMultipart("alternative")
    text_body = _html_to_plain_text(html_body)
    msg_alternative.attach(MIMEText(text_body, "plain"))
    msg_alternative.attach(MIMEText(html_body, "html"))
    msg.attach(msg_alternative)

    _attach_brand_logos(msg, html_body)
    await _deliver_message(msg, to_email, raise_on_error=raise_on_error)


async def send_otp_email(to_email: str, otp: str, first_name: str) -> None:
    """Send a styled OTP verification email."""
    template = _env.get_template("otp_email.html")
    html = template.render(
        first_name=first_name,
        otp=otp,
        year=datetime.utcnow().year,
        expires_minutes=10,
    )
    await _send_email(to_email, "Verify Your Rojgar Mela Account", html)


async def send_welcome_email(to_email: str, first_name: str, role: str) -> None:
    """Send a welcome email after onboarding completes."""
    template = _env.get_template("welcome_email.html")
    role_label = "Job Seeker" if role == "seeker" else "Job Provider"
    html = template.render(
        first_name=first_name,
        role_label=role_label,
        year=datetime.utcnow().year,
    )
    await _send_email(to_email, f"Welcome to Rojgar Mela, {first_name}!", html)


async def send_notification_email(to_email: str, first_name: str, title: str, message: str) -> None:
    """Generic notification email."""
    template = _env.get_template("notification_email.html")
    html = template.render(
        first_name=first_name,
        title=title,
        message=message,
        year=datetime.utcnow().year,
    )
    await _send_email(to_email, title, html)


async def send_password_email(to_email: str, first_name: str, password: str, role: str) -> None:
    """Send account credentials email with temporary password."""
    role_label = "Job Seeker" if role == "seeker" else "Job Provider"
    html = f"""
    <html>
    <head><style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 30px 20px; background: #f9fafb; }}
        .credentials {{ background: white; border: 2px dashed #2563eb; padding: 20px; margin: 20px 0; border-radius: 8px; }}
        .password {{ font-size: 20px; font-weight: bold; color: #2563eb; letter-spacing: 2px; }}
        .warning {{ background: #fef3c7; padding: 10px; border-radius: 4px; font-size: 13px; color: #92400e; }}
        .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }}
    </style></head>
    <body>
        <div class="container">
            <div class="header"><h1>Welcome to Rojgar Mela!</h1></div>
            <div class="content">
                <p>Hi <strong>{first_name}</strong>,</p>
                <p>Your account has been created as a <strong>{role_label}</strong>.</p>
                <p>Use the following credentials to log in:</p>
                <div class="credentials">
                    <p><strong>Email:</strong> {to_email}</p>
                    <p><strong>Password:</strong></p>
                    <p class="password">{password}</p>
                </div>
                <div class="warning">
                    <strong>⚠️ Important:</strong> Please change this password after your first login.
                    Do not share your password with anyone.
                </div>
                <p>After logging in, you'll be prompted to set up Two-Factor Authentication (TOTP) for added security.</p>
            </div>
            <div class="footer">© {datetime.utcnow().year} Rojgar Mela. All rights reserved.</div>
        </div>
    </body>
    </html>
    """
    await _send_email(to_email, "Your Rojgar Mela Account Credentials", html)


async def send_job_fair_welcome_email(
    to_email: str,
    seeker_name: str,
    password: str,
    profile_link: str
) -> None:
    """Send a welcome email for Job Fair 2026 to imported seekers."""
    template = _env.get_template("job_fair_email.html")
    
    html = template.render(
        seeker_name=seeker_name,
        email=to_email,
        password=password,
        profile_link=profile_link,
        year=datetime.utcnow().year,
    )

    from services.email_template_service import prepare_html_for_delivery

    html = prepare_html_for_delivery(html)
    await send_campaign_email(
        to_email,
        "11th Mega Job Fair 2026 (4 June) – Login & Complete Your Profile",
        html,
        raise_on_error=True,
    )
