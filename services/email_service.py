from datetime import datetime, date
from pathlib import Path
from typing import Optional
import re

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from jinja2 import Environment, FileSystemLoader

from config import settings

# Template engine
_template_dir = Path(__file__).parent.parent / "templates"
_env = Environment(loader=FileSystemLoader(str(_template_dir)), autoescape=True)

_UPLOADS_DIR = Path(__file__).parent.parent / "uploads"


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


async def _send_email(to_email: str, subject: str, html_body: str) -> None:
    """Internal SMTP sender using aiosmtplib."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg["Message-ID"] = f"<{datetime.utcnow().timestamp()}@jobmatch.ai>"
    msg["Reply-To"] = settings.SMTP_USER
    
    # Create plain text version by stripping HTML tags
    text_body = re.sub('<[^<]+>', '', html_body)
    
    # Attach parts (plain text must be attached first)
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

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
        # Log but don't crash the request if email fails
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")


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

    # Build the email with inline image
    # Structure: mixed -> related -> alternative (text + html) + image
    msg = MIMEMultipart("related")
    msg["Subject"] = "11th Mega Job Fair 2026 (4 June) – Login & Complete Your Profile"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg["Message-ID"] = f"<{datetime.utcnow().timestamp()}@jobmatch.ai>"
    msg["Reply-To"] = settings.SMTP_USER

    # Create the text/html alternatives
    msg_alternative = MIMEMultipart("alternative")
    text_body = re.sub('<[^<]+>', '', html)
    msg_alternative.attach(MIMEText(text_body, "plain"))
    msg_alternative.attach(MIMEText(html, "html"))
    msg.attach(msg_alternative)

    _attach_inline_image(msg, _UPLOADS_DIR / "cicu_logo.jpg", "cicu_logo")
    _attach_inline_image(msg, _UPLOADS_DIR / "rojgar_logo.png", "rojgar_logo")

    # Send the email
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
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")
        raise
