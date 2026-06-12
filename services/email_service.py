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


def _attach_inline_images(msg: MIMEMultipart, html_body: str) -> None:
    """Attach all images referenced via cid: in the HTML body."""
    from services.email_template_service import cid_to_file_path

    content_ids = set(re.findall(r"cid:([a-zA-Z0-9_\-]+)", html_body))
    for content_id in content_ids:
        path = cid_to_file_path(content_id)
        if path:
            _attach_inline_image(msg, path, content_id)


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

    _attach_inline_images(msg, html_body)
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
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Your Account Credentials – CICU</title>
</head>
<body style="margin:0;padding:0;background:#eef4f9;font-family:'Segoe UI',Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;">
    <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:#eef4f9;padding:32px 16px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" role="presentation" style="max-width:600px;width:100%;background:#ffffff;border-radius:4px;overflow:hidden;box-shadow:0 4px 18px rgba(15,40,80,0.08);">
                    <!-- Partner logos: CICU (left) · Rojgar Mela (right) -->
                    <tr>
                        <td style="padding:25px 32px 8px;background:#ffffff;">
                            <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                                <tr>
                                    <td align="left" valign="middle" width="50%" style="padding-right:12px;">
                                        <img src="https://spatial-aqua-roadrunner.myfilebase.com/ipfs/QmSXRsnibbzf9yNo8Zqieqc35Ybbu5wn1YneR9MJkjgM9u" alt="CICU" style="height:56px;width:auto;max-width:240px;display:block;object-fit:contain;" />
                                    </td>
                                    <td align="right" valign="middle" width="50%" style="padding-left:12px;">
                                        <img src="https://spatial-aqua-roadrunner.myfilebase.com/ipfs/QmP8nbxreh5FS1KABK3599syFUFY5UoV7hHcrA9riAfRxT" alt="Rojgar Mela AI" style="height:48px;width:auto;max-width:240px;display:block;margin-left:auto;object-fit:contain;" />
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Main body -->
                    <tr>
                        <td style="padding:10px 36px 24px;background:#ffffff;text-align:left;">
                            <h1 style="margin:0 0 16px 0;font-size:22px;font-weight:700;color:#0f2d52;line-height:1.3;border-bottom:3px solid #ea580c;padding-bottom:10px;">Welcome to Rojgar Mela!</h1>
                            <p style="margin:0 0 14px 0;font-size:15px;line-height:1.65;color:#1f2937;">Hi <strong>{first_name}</strong>,</p>
                            <p style="margin:0 0 18px 0;font-size:15px;line-height:1.65;color:#1f2937;">Your account has been successfully created as a <strong>{role_label}</strong>. We are thrilled to welcome you to the Rojgar Mela platform!</p>
                            <p style="margin:0 0 18px 0;font-size:15px;line-height:1.65;color:#1f2937;">Use the credentials below to log in to your account and get started:</p>
                            <!-- Credentials Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:0 0 22px 0;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;">
                                <tr>
                                    <td style="padding:16px 18px;">
                                        <p style="margin:0 0 10px 0;font-size:12px;font-weight:700;color:#0f2d52;text-transform:uppercase;letter-spacing:0.06em;">Your Login Credentials</p>
                                        <p style="margin:0 0 8px 0;font-size:14px;color:#334155;"><strong>Login Email:</strong> {to_email}</p>
                                        <p style="margin:0;font-size:14px;color:#334155;"><strong>Temporary Password:</strong> <span style="font-family:monospace;font-size:16px;font-weight:bold;color:#ea580c;background:#fff7ed;padding:4px 8px;border-radius:4px;border:1px solid #ffedd5;">{password}</span></p>
                                    </td>
                                </tr>
                            </table>
                            <!-- Security Warning -->
                            <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:0 0 22px 0;background:#fffbeb;border-left:4px solid #d97706;border-radius:0 4px 4px 0;">
                                <tr>
                                    <td style="padding:16px 18px;">
                                        <p style="margin:0 0 8px 0;font-size:14px;font-weight:700;color:#92400e;">⚠️ Security Notice</p>
                                        <p style="margin:0;font-size:14px;line-height:1.65;color:#334155;">Please change your password immediately after logging in. Do not share your temporary credentials with anyone. For your protection, you will be prompted to set up Two-Factor Authentication (TOTP) upon first login.</p>
                                    </td>
                                </tr>
                            </table>
                            <!-- CTA -->
                            <table cellpadding="0" align="center" cellspacing="0" role="presentation" style="margin:0 0 24px 0;" width="100%">
                                <tr>
                                    <td align="center">
                                        <a href="{settings.FRONTEND_URL}/login" target="_blank" style="display:inline-block;background:#0f2d52;color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;padding:14px 32px;border-radius:4px;letter-spacing:0.02em;">Log In to Dashboard</a>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin:0;font-size:15px;line-height:1.6;color:#1f2937;">Regards,<br /><strong style="color:#0f2d52;">Mega Job Fair Organizing Committee</strong><br /><span style="font-size:13px;color:#64748b;">CICU x Rojgar Mela AI</span></p>
                        </td>
                    </tr>
                    <!-- Footer with logos -->
                    <tr>
                        <td style="background:#eef5fb;padding:24px 32px 8px;border-top:1px solid #dbeafe;">
                            <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                                <tr>
                                    <td align="left" valign="middle" width="50%"><img src="https://spatial-aqua-roadrunner.myfilebase.com/ipfs/QmSXRsnibbzf9yNo8Zqieqc35Ybbu5wn1YneR9MJkjgM9u" alt="CICU" style="height:48px;width:auto;max-width:200px;display:block;object-fit:contain;" /></td>
                                    <td align="right" valign="middle" width="50%"><img src="https://spatial-aqua-roadrunner.myfilebase.com/ipfs/QmP8nbxreh5FS1KABK3599syFUFY5UoV7hHcrA9riAfRxT" alt="Rojgar Mela AI" style="height:40px;width:auto;max-width:200px;display:block;margin-left:auto;object-fit:contain;" /></td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td align="center" style="background:#eef5fb;padding:8px 32px 32px;">
                            <p style="margin:0 0 8px 0;font-size:14px;color:#475569;line-height:1.5;">If you have any questions,</p>
                            <p style="margin:0 0 6px 0;font-size:14px;color:#475569;line-height:1.5;">Please email us at <a href="mailto:usahuja@swanindia.com" style="color:#2563eb;text-decoration:none;font-weight:600;">cicu@cicuindia.org</a></p>
                            <p style="margin:0 0 16px 0;font-size:14px;color:#475569;line-height:1.5;">or <a href="mailto:chamber@cicuindia.org" style="color:#2563eb;text-decoration:none;font-weight:600;">chamber@cicuindia.org</a></p>
                            <p style="margin:0;font-size:12px;color:#94a3b8;line-height:1.5;">You received this email because you registered for the Mega Job Fair.<br />© {datetime.utcnow().year} CICU &amp; Rojgar Mela AI. All rights reserved.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
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
        "The Job Carnival 2026 (19 June) – Login & Complete Your Profile",
        html,
        raise_on_error=True,
    )
