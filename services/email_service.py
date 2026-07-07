from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
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


IST_TZ = timezone(timedelta(hours=5, minutes=30))


def _to_ist(fair_date: datetime) -> datetime:
    """Normalize datetime to IST for user-facing emails."""
    if fair_date.tzinfo is None:
        # Job fair datetimes are persisted as UTC wall-time without tzinfo.
        fair_date = fair_date.replace(tzinfo=timezone.utc)
    return fair_date.astimezone(IST_TZ)


def _ordinal_day(day: int) -> str:
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def _format_job_fair_datetime(fair_date: datetime) -> tuple[str, str]:
    """Return (date_display, time_display) in IST for email templates."""
    ist_date = _to_ist(fair_date)
    date_display = (
        f"{ist_date.strftime('%A')}, {_ordinal_day(ist_date.day)} "
        f"{ist_date.strftime('%B')}, {ist_date.year}"
    )
    hour = ist_date.hour % 12 or 12
    minute = ist_date.minute
    am_pm = "AM" if ist_date.hour < 12 else "PM"
    if ist_date.hour or ist_date.minute:
        time_display = f"{hour}:{minute:02d} {am_pm} IST Onwards"
    else:
        time_display = "IST Onwards"
    return date_display, time_display


def _absolute_public_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = settings.FRONTEND_URL.rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def _banner_src_for_email(banner: Optional[str]) -> Optional[str]:
    """Return cid: or public URL for job fair banner images in email HTML."""
    if not banner:
        return None
    from services.email_template_service import uploads_root, _upload_rel_to_cid

    rel: Optional[str] = None
    if banner.startswith("/uploads/"):
        rel = banner.removeprefix("/uploads/").lstrip("/")
    else:
        frontend = settings.FRONTEND_URL.rstrip("/")
        if banner.startswith(f"{frontend}/uploads/"):
            rel = banner[len(f"{frontend}/uploads/"):].lstrip("/")

    if rel:
        file_path = uploads_root() / rel
        if file_path.is_file():
            return f"cid:{_upload_rel_to_cid(rel)}"
    return _absolute_public_url(banner)


def _support_context() -> dict[str, str]:
    return {
        "support_email": settings.SUPPORT_EMAIL,
        "support_phones": settings.SUPPORT_PHONES,
    }


def build_job_fair_email_context(job_fair: Any = None) -> dict[str, Any]:
    """Build template variables from a JobFair record (or sensible defaults)."""
    ctx: dict[str, Any] = {
        "job_fair_title": "Job Fair",
        "job_fair_slug": "",
        "job_fair_location": "",
        "job_fair_description": "",
        "collaboration_text": "",
        "job_fair_date_display": "",
        "job_fair_time_display": "",
        "banner_image_url": None,
        "event_helpline": "",
        "host_organization": "",
    }
    if not job_fair:
        return ctx

    title = getattr(job_fair, "title", None) or "Job Fair"
    ctx["job_fair_title"] = title
    ctx["job_fair_slug"] = getattr(job_fair, "slug", "") or ""
    ctx["job_fair_location"] = getattr(job_fair, "location", "") or ""
    description = (getattr(job_fair, "description", None) or "").strip()
    ctx["job_fair_description"] = description

    # First line of description can carry collaboration / host notes from admin.
    if description:
        lines = [line.strip() for line in description.splitlines() if line.strip()]
        if lines:
            first = lines[0]
            if first.lower().startswith("in collaboration") or first.lower().startswith("hosted by"):
                ctx["collaboration_text"] = first
                ctx["job_fair_description"] = "\n".join(lines[1:]).strip()
            for line in lines:
                lower = line.lower()
                if lower.startswith("helpline:") or lower.startswith("helpline number:"):
                    ctx["event_helpline"] = line.split(":", 1)[-1].strip()
                elif lower.startswith("host:"):
                    ctx["host_organization"] = line.split(":", 1)[-1].strip()

    fair_date = getattr(job_fair, "date", None)
    if fair_date:
        ctx["job_fair_date_display"], ctx["job_fair_time_display"] = _format_job_fair_datetime(fair_date)

    banner = getattr(job_fair, "banner_image_url", None)
    ctx["banner_image_url"] = _banner_src_for_email(banner)
    return ctx


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


async def _send_branded_email(
    to_email: str,
    subject: str,
    html_body: str,
    *,
    raise_on_error: bool = False,
) -> None:
    """Send HTML email with inline cid: images (logos, banners, uploads)."""
    from services.email_template_service import prepare_html_for_delivery

    html = prepare_html_for_delivery(html_body)
    await send_campaign_email(to_email, subject, html, raise_on_error=raise_on_error)


async def send_otp_email(to_email: str, otp: str, first_name: str) -> None:
    """Send a styled OTP verification email."""
    template = _env.get_template("otp_email.html")
    html = template.render(
        first_name=first_name,
        otp=otp,
        year=datetime.utcnow().year,
        expires_minutes=10,
        login_url=f"{settings.FRONTEND_URL.rstrip('/')}/login",
        **_support_context(),
    )
    await _send_branded_email(to_email, "Verify Your RojgarMela.AI Account", html)


async def send_welcome_email(
    to_email: str,
    first_name: str,
    role: str,
    *,
    password: Optional[str] = None,
) -> None:
    """Send a welcome email after normal account registration / onboarding."""
    template = _env.get_template("welcome_email.html")
    is_seeker = role == "seeker"
    role_label = "Job Seeker" if is_seeker else "Job Provider"
    html = template.render(
        first_name=first_name,
        name=first_name,
        email=to_email,
        password=password or "",
        role=role,
        role_label=role_label,
        is_seeker=is_seeker,
        is_provider=not is_seeker,
        login_url=f"{settings.FRONTEND_URL.rstrip('/')}/login",
        year=datetime.utcnow().year,
        **_support_context(),
    )
    await _send_branded_email(to_email, f"Welcome to RojgarMela.AI, {first_name}!", html)


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
                            <p style="margin:0 0 14px 0;font-size:13px;line-height:1.65;color:#1f2937;">Hi <strong>{first_name}</strong>,</p>
                            <p style="margin:0 0 18px 0;font-size:13px;line-height:1.65;color:#1f2937;">Your account has been successfully created as a <strong>{role_label}</strong>. We are thrilled to welcome you to the Rojgar Mela platform!</p>
                            <p style="margin:0 0 18px 0;font-size:13px;line-height:1.65;color:#1f2937;">Use the credentials below to log in to your account and get started:</p>
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
                                        <a href="{settings.FRONTEND_URL}/login" target="_blank" style="display:inline-block;background:#0f2d52;color:#ffffff;text-decoration:none;font-size:13px;font-weight:600;padding:14px 32px;border-radius:4px;letter-spacing:0.02em;">Log In to Dashboard</a>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin:0;font-size:13px;line-height:1.6;color:#1f2937;">Regards,<br /><strong style="color:#0f2d52;">Mega Job Fair Organizing Committee</strong><br /><span style="font-size:13px;color:#64748b;">CICU x Rojgar Mela AI</span></p>
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
    recipient_name: str,
    password: str,
    profile_link: str,
    *,
    job_fair: Any = None,
    role: str = "seeker",
) -> None:
    """Send registration email for users signing up via a Job Fair form."""
    template = _env.get_template("job_fair_email.html")
    fair_ctx = build_job_fair_email_context(job_fair)
    is_seeker = role == "seeker"
    role_label = "Job Seeker" if is_seeker else "Job Provider"
    fair_title = fair_ctx.get("job_fair_title") or "Job Fair"
    subject = f"{fair_title} – Login & Complete Your Profile"

    html = template.render(
        seeker_name=recipient_name,
        recipient_name=recipient_name,
        email=to_email,
        password=password,
        profile_link=profile_link,
        role=role,
        role_label=role_label,
        is_seeker=is_seeker,
        is_provider=not is_seeker,
        year=datetime.utcnow().year,
        login_url=f"{settings.FRONTEND_URL.rstrip('/')}/login",
        **_support_context(),
        **fair_ctx,
    )

    await _send_branded_email(to_email, subject, html, raise_on_error=True)


async def send_training_portal_batch_assigned_email(
    to_email: str,
    candidate_name: str,
    course_title: str,
    batch_name: str,
    time_slot: str,
    venue: str,
    days: list,
) -> None:
    days_text = ", ".join(days) if days else "To be announced"
    html = f"""
    <p>Hi {candidate_name},</p>
    <p>Your batch has been assigned for <strong>{course_title}</strong>.</p>
    <ul>
      <li><strong>Batch:</strong> {batch_name}</li>
      <li><strong>Schedule:</strong> {time_slot} ({days_text})</li>
      <li><strong>Venue:</strong> {venue}</li>
    </ul>
    <p>Login to the Training Portal to view your schedule.</p>
    """
    await send_notification_email(to_email, candidate_name, "Batch Assigned – RojgarMela Training", html)


async def send_training_portal_payment_link_email(
    to_email: str,
    candidate_name: str,
    program_title: str,
    amount: float,
    enrollment_id: str,
) -> None:
    pay_url = f"{settings.TRAINING_URL.rstrip('/')}/candidate/enrollments?pay={enrollment_id}"
    html = f"""
    <p>Hi {candidate_name},</p>
    <p>Complete your payment of <strong>₹{amount:,.0f}</strong> for <strong>{program_title}</strong>.</p>
    <p><a href="{pay_url}">Pay Now</a></p>
    """
    await send_notification_email(to_email, candidate_name, "Complete Your Training Payment", html)


async def send_training_portal_payment_success_email(
    to_email: str,
    candidate_name: str,
    program_title: str,
    amount: float,
    invoice_number: str,
    invoice_date: str,
    payment_mode: str | None = None,
    batch_name: str | None = None,
    invoice_url: str | None = None,
) -> None:
    batch_html = f"<p><strong>Batch:</strong> {batch_name}</p>" if batch_name else ""
    payment_mode_html = f"<p><strong>Payment mode:</strong> {payment_mode}</p>" if payment_mode else ""
    invoice_url_html = (
        f'<p>You can view and print your invoice here: <a href="{invoice_url}">Open Invoice</a></p>'
        if invoice_url
        else ""
    )
    html = f"""
    <p>Hi {candidate_name},</p>
    <p>We received your payment of <strong>₹{amount:,.0f}</strong> for <strong>{program_title}</strong>.</p>
    <p><strong>Invoice No:</strong> {invoice_number}</p>
    <p><strong>Invoice Date:</strong> {invoice_date}</p>
    {payment_mode_html}
    {batch_html}
    <p>Your enrollment is now confirmed. Our admin team will contact you regarding batch assignment.</p>
    {invoice_url_html}
    """
    await send_notification_email(to_email, candidate_name, "Payment Received – RojgarMela Training", html)
