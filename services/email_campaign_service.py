"""Email campaign audience resolution and bulk sending."""
import re
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models.email_campaign import (
    AudienceType,
    CampaignStatus,
    EmailCampaign,
    EmailCampaignRecipient,
    RecipientStatus,
)
from models.email_template import EmailTemplate
from models.job_fair import JobFairCompany, JobFairSeeker
from models.user import User, UserRole
from services.email_campaign_job_store import create_campaign_job, get_job, update_job
from config import settings
from services.email_service import send_campaign_email
from services.email_template_service import build_user_context, render_email_template

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _full_name(user: User) -> str:
    parts = [user.first_name or "", user.last_name or ""]
    return " ".join(p for p in parts if p).strip() or "User"


def _audience_filter_dict(audience_filter: Optional[dict[str, Any]]) -> dict[str, Any]:
    return audience_filter or {}


def _normalize_imported_emails(audience_filter: Optional[dict[str, Any]]) -> list[dict[str, str]]:
    filt = _audience_filter_dict(audience_filter)
    rows = filt.get("imported_emails") or []
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        if isinstance(row, str):
            email = row.strip().lower()
            name = ""
        else:
            email = (row.get("email") or "").strip().lower()
            name = (row.get("name") or "").strip()
        if not email or not _EMAIL_RE.match(email):
            continue
        if email in seen:
            continue
        seen.add(email)
        out.append({"email": email, "name": name})
    return out


async def build_audience_query(
    audience_type: str,
    audience_filter: Optional[dict[str, Any]] = None,
):
    filt = _audience_filter_dict(audience_filter)
    q = select(User).where(
        User.is_super_admin.is_(False),
        User.email.isnot(None),
        User.email != "",
    )

    if audience_type == AudienceType.all_seekers.value:
        q = q.where(User.role == UserRole.seeker)
    elif audience_type == AudienceType.all_providers.value:
        q = q.where(User.role == UserRole.provider)
    elif audience_type == AudienceType.all_users.value:
        q = q.where(User.role.in_([UserRole.seeker, UserRole.provider]))
    elif audience_type == AudienceType.industry_seekers.value:
        q = q.where(User.role == UserRole.seeker)
        industries = filt.get("industries") or []
        if industries:
            q = q.where(User.industry.in_(industries))
    elif audience_type == AudienceType.industry_providers.value:
        q = q.where(User.role == UserRole.provider)
        industries = filt.get("industries") or []
        if industries:
            q = q.where(User.industry.in_(industries))
    elif audience_type == AudienceType.specific_users.value:
        user_ids = filt.get("user_ids") or []
        if not user_ids:
            q = q.where(false())
        else:
            q = q.where(User.id.in_(user_ids))
    elif audience_type == AudienceType.job_fair_seekers.value:
        job_fair_id = filt.get("job_fair_id")
        if not job_fair_id:
            q = q.where(false())
        else:
            q = (
                q.join(JobFairSeeker, JobFairSeeker.seeker_id == User.id)
                .where(
                    JobFairSeeker.job_fair_id == job_fair_id,
                    User.role == UserRole.seeker,
                )
                .distinct()
            )
    elif audience_type == AudienceType.job_fair_providers.value:
        job_fair_id = filt.get("job_fair_id")
        if not job_fair_id:
            q = q.where(false())
        else:
            q = (
                q.join(JobFairCompany, JobFairCompany.provider_id == User.id)
                .where(
                    JobFairCompany.job_fair_id == job_fair_id,
                    User.role == UserRole.provider,
                )
                .distinct()
            )
    elif audience_type == AudienceType.csv_import.value:
        q = q.where(false())
    else:
        q = q.where(false())

    if filt.get("is_verified") is True:
        q = q.where(User.is_verified.is_(True))

    return q


async def count_audience(
    db: AsyncSession,
    audience_type: str,
    audience_filter: Optional[dict[str, Any]] = None,
) -> int:
    if audience_type == AudienceType.csv_import.value:
        return len(_normalize_imported_emails(audience_filter))
    q = await build_audience_query(audience_type, audience_filter)
    count_q = select(func.count()).select_from(q.subquery())
    return (await db.execute(count_q)).scalar() or 0


async def resolve_campaign_recipients(
    db: AsyncSession,
    audience_type: str,
    audience_filter: Optional[dict[str, Any]] = None,
) -> list[tuple[Optional[User], str, str]]:
    """Return (user_or_none, email, recipient_name) for each campaign recipient."""
    if audience_type == AudienceType.csv_import.value:
        rows = _normalize_imported_emails(audience_filter)
        if not rows:
            return []
        emails = [row["email"] for row in rows]
        users_by_email: dict[str, User] = {}
        user_rows = (
            await db.execute(select(User).where(func.lower(User.email).in_(emails)))
        ).scalars().all()
        for user in user_rows:
            if user.email:
                users_by_email[user.email.strip().lower()] = user

        recipients: list[tuple[Optional[User], str, str]] = []
        for row in rows:
            email = row["email"]
            user = users_by_email.get(email)
            name = row.get("name") or (user and _full_name(user)) or email.split("@")[0]
            recipients.append((user, email, name))
        return recipients

    audience_q = await build_audience_query(audience_type, audience_filter)
    users = (await db.execute(audience_q)).scalars().all()
    return [(user, user.email, _full_name(user)) for user in users]


async def get_audience_sample(
    db: AsyncSession,
    audience_type: str,
    audience_filter: Optional[dict[str, Any]] = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if audience_type == AudienceType.csv_import.value:
        rows = _normalize_imported_emails(audience_filter)[:limit]
        return [
            {
                "id": "",
                "name": row.get("name") or row["email"],
                "email": row["email"],
                "role": "",
            }
            for row in rows
        ]

    users, _ = await get_audience_users(db, audience_type, audience_filter, page=1, page_size=limit)
    return [
        {
            "id": user.id,
            "name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
            "email": user.email,
            "role": user.role.value if user.role else "",
        }
        for user in users
    ]


def build_picker_users_query(
    search: Optional[str] = None,
    role: Optional[str] = None,
):
    """Base query for the campaign user picker (seekers + providers with email)."""
    q = select(User).where(
        User.is_super_admin.is_(False),
        User.email.isnot(None),
        User.email != "",
        User.role.in_([UserRole.seeker, UserRole.provider]),
    )
    if role == "seeker":
        q = q.where(User.role == UserRole.seeker)
    elif role == "provider":
        q = q.where(User.role == UserRole.provider)

    if search and search.strip():
        term = f"%{search.strip()}%"
        full_name = func.concat(
            func.coalesce(User.first_name, ""),
            " ",
            func.coalesce(User.last_name, ""),
        )
        q = q.where(
            or_(
                User.first_name.ilike(term),
                User.last_name.ilike(term),
                full_name.ilike(term),
                User.email.ilike(term),
                User.company_name.ilike(term),
            )
        )
    return q


async def list_picker_users(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
):
    q = build_picker_users_query(search, role)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    users = (await db.execute(q)).scalars().all()
    return users, total


async def get_picker_user_ids(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    role: Optional[str] = None,
) -> tuple[list[str], int]:
    q = build_picker_users_query(search, role)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    id_q = q.order_by(User.created_at.desc()).with_only_columns(User.id)
    ids = list((await db.execute(id_q)).scalars().all())
    return ids, int(total)


async def get_audience_users(
    db: AsyncSession,
    audience_type: str,
    audience_filter: Optional[dict[str, Any]] = None,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
):
    q = await build_audience_query(audience_type, audience_filter)

    if role == "seeker":
        q = q.where(User.role == UserRole.seeker)
    elif role == "provider":
        q = q.where(User.role == UserRole.provider)

    if search and search.strip():
        term = f"%{search.strip()}%"
        full_name = func.concat(
            func.coalesce(User.first_name, ""),
            " ",
            func.coalesce(User.last_name, ""),
        )
        q = q.where(
            or_(
                User.first_name.ilike(term),
                User.last_name.ilike(term),
                full_name.ilike(term),
                User.email.ilike(term),
                User.company_name.ilike(term),
            )
        )

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    users = (await db.execute(q)).scalars().all()
    return users, total


async def run_campaign_send_job(job_id: str, campaign_id: str) -> None:
    try:
        await _run_campaign_send_job_inner(job_id, campaign_id)
    except Exception as exc:
        update_job(job_id, status="failed", message=str(exc), progress=100)
        async with AsyncSessionLocal() as db:
            campaign = (await db.execute(
                select(EmailCampaign).where(EmailCampaign.id == campaign_id)
            )).scalar_one_or_none()
            if campaign:
                campaign.status = CampaignStatus.failed
                await db.commit()


async def _run_campaign_send_job_inner(job_id: str, campaign_id: str) -> None:
    async with AsyncSessionLocal() as db:
        campaign = (await db.execute(
            select(EmailCampaign).where(EmailCampaign.id == campaign_id)
        )).scalar_one_or_none()
        if not campaign:
            update_job(job_id, status="failed", message="Campaign not found", progress=100)
            return

        template = (await db.execute(
            select(EmailTemplate).where(EmailTemplate.id == campaign.template_id)
        )).scalar_one_or_none()
        if not template or not template.is_active:
            campaign.status = CampaignStatus.failed
            await db.commit()
            update_job(job_id, status="failed", message="Template not found or inactive", progress=100)
            return

        audience_type = (
            campaign.audience_type.value
            if hasattr(campaign.audience_type, "value")
            else campaign.audience_type
        )
        recipients = await resolve_campaign_recipients(
            db,
            audience_type,
            campaign.audience_filter,
        )

        total = len(recipients)
        campaign.status = CampaignStatus.running
        campaign.started_at = datetime.utcnow()
        campaign.total_recipients = total
        campaign.sent_count = 0
        campaign.failed_count = 0
        await db.commit()

        update_job(job_id, status="running", total=total, processed=0, sent=0, failed=0, progress=0)

        sent = 0
        failed = 0
        batch_size = 25

        for idx, (user, email, recipient_name) in enumerate(recipients):
            recipient = EmailCampaignRecipient(
                campaign_id=campaign.id,
                user_id=user.id if user else None,
                email=email,
                recipient_name=recipient_name,
                status=RecipientStatus.pending,
            )
            db.add(recipient)
            await db.flush()

            try:
                context = _build_recipient_context(recipient, user)
                subject, html_body = render_email_template(template, context)
                await send_campaign_email(email, subject, html_body, raise_on_error=True)
                recipient.status = RecipientStatus.sent
                recipient.sent_at = datetime.utcnow()
                sent += 1
            except Exception as exc:
                recipient.status = RecipientStatus.failed
                recipient.error = str(exc)
                failed += 1

            if (idx + 1) % batch_size == 0 or idx + 1 == total:
                campaign.sent_count = sent
                campaign.failed_count = failed
                await db.commit()
                progress = int(((idx + 1) / total) * 100) if total else 100
                update_job(
                    job_id,
                    processed=idx + 1,
                    sent=sent,
                    failed=failed,
                    progress=progress,
                    message=f"Sent {sent} of {total} emails…",
                )

        campaign.status = CampaignStatus.completed
        campaign.completed_at = datetime.utcnow()
        campaign.sent_count = sent
        campaign.failed_count = failed
        await db.commit()

        update_job(
            job_id,
            status="completed",
            progress=100,
            processed=total,
            sent=sent,
            failed=failed,
            message=f"Completed: {sent} sent, {failed} failed",
        )


def start_campaign_job(campaign_id: str) -> str:
    job_id = create_campaign_job(campaign_id)
    return job_id


def _build_recipient_context(recipient: EmailCampaignRecipient, user: Optional[User] = None) -> dict[str, Any]:
    if user:
        return build_user_context(user)
    name = recipient.recipient_name or "User"
    parts = [p for p in name.split() if p]
    first = parts[0] if parts else "User"
    last = " ".join(parts[1:]) if len(parts) > 1 else ""
    login_url = f"{settings.FRONTEND_URL.rstrip('/')}/login"
    return {
        "first_name": first,
        "last_name": last,
        "name": name,
        "seeker_name": name,
        "email": recipient.email,
        "password": "",
        "profile_link": login_url,
        "industry": "",
        "company_name": "",
        "role_label": "User",
        "phone": "",
        "year": datetime.utcnow().year,
    }


async def _get_campaign_template(db: AsyncSession, campaign_id: str) -> tuple[EmailCampaign, EmailTemplate]:
    campaign = (await db.execute(select(EmailCampaign).where(EmailCampaign.id == campaign_id))).scalar_one_or_none()
    if not campaign:
        raise ValueError("Campaign not found")
    template = (await db.execute(
        select(EmailTemplate).where(EmailTemplate.id == campaign.template_id)
    )).scalar_one_or_none()
    if not template or not template.is_active:
        raise ValueError("Template not found or inactive")
    return campaign, template


async def resend_to_recipient(
    db: AsyncSession,
    campaign_id: str,
    recipient_id: str,
) -> EmailCampaignRecipient:
    recipient = (
        await db.execute(
            select(EmailCampaignRecipient).where(
                EmailCampaignRecipient.id == recipient_id,
                EmailCampaignRecipient.campaign_id == campaign_id,
            )
        )
    ).scalar_one_or_none()
    if not recipient:
        raise ValueError("Recipient not found")
    if recipient.status != RecipientStatus.failed:
        raise ValueError("Only failed emails can be resent")

    campaign, template = await _get_campaign_template(db, campaign_id)
    user = None
    if recipient.user_id:
        user = (await db.execute(select(User).where(User.id == recipient.user_id))).scalar_one_or_none()

    was_failed = recipient.status == RecipientStatus.failed
    try:
        context = _build_recipient_context(recipient, user)
        subject, html_body = render_email_template(template, context)
        await send_campaign_email(recipient.email, subject, html_body, raise_on_error=True)
        recipient.status = RecipientStatus.sent
        recipient.error = None
        recipient.sent_at = datetime.utcnow()
        if was_failed:
            campaign.failed_count = max(0, campaign.failed_count - 1)
            campaign.sent_count += 1
    except Exception as exc:
        recipient.status = RecipientStatus.failed
        recipient.error = str(exc)
        raise

    await db.flush()
    return recipient


async def resend_all_failed(db: AsyncSession, campaign_id: str) -> tuple[int, int, int]:
    campaign, template = await _get_campaign_template(db, campaign_id)
    failed_recipients = (
        await db.execute(
            select(EmailCampaignRecipient).where(
                EmailCampaignRecipient.campaign_id == campaign_id,
                EmailCampaignRecipient.status == RecipientStatus.failed,
            )
        )
    ).scalars().all()

    total = len(failed_recipients)
    sent = 0
    still_failed = 0

    for recipient in failed_recipients:
        user = None
        if recipient.user_id:
            user = (await db.execute(select(User).where(User.id == recipient.user_id))).scalar_one_or_none()
        try:
            context = _build_recipient_context(recipient, user)
            subject, html_body = render_email_template(template, context)
            await send_campaign_email(recipient.email, subject, html_body, raise_on_error=True)
            recipient.status = RecipientStatus.sent
            recipient.error = None
            recipient.sent_at = datetime.utcnow()
            campaign.failed_count = max(0, campaign.failed_count - 1)
            campaign.sent_count += 1
            sent += 1
        except Exception as exc:
            recipient.error = str(exc)
            still_failed += 1

    await db.flush()
    return total, sent, still_failed
