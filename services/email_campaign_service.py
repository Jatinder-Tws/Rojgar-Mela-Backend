"""Email campaign audience resolution and bulk sending."""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, func, or_, select
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
from models.user import User, UserRole
from services.email_campaign_job_store import create_campaign_job, get_job, update_job
from services.email_service import _send_email
from services.email_template_service import build_user_context, render_email_template


def _full_name(user: User) -> str:
    parts = [user.first_name or "", user.last_name or ""]
    return " ".join(p for p in parts if p).strip() or "User"


def _audience_filter_dict(audience_filter: Optional[dict[str, Any]]) -> dict[str, Any]:
    return audience_filter or {}


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
            q = q.where(User.id == "none")
        else:
            q = q.where(User.id.in_(user_ids))
    else:
        q = q.where(User.id == "none")

    if filt.get("is_verified") is True:
        q = q.where(User.is_verified.is_(True))

    return q


async def count_audience(
    db: AsyncSession,
    audience_type: str,
    audience_filter: Optional[dict[str, Any]] = None,
) -> int:
    q = await build_audience_query(audience_type, audience_filter)
    count_q = select(func.count()).select_from(q.subquery())
    return (await db.execute(count_q)).scalar() or 0


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

        audience_q = await build_audience_query(
            campaign.audience_type.value if hasattr(campaign.audience_type, "value") else campaign.audience_type,
            campaign.audience_filter,
        )
        users = (await db.execute(audience_q)).scalars().all()

        total = len(users)
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

        for idx, user in enumerate(users):
            recipient_name = _full_name(user)
            recipient = EmailCampaignRecipient(
                campaign_id=campaign.id,
                user_id=user.id,
                email=user.email,
                recipient_name=recipient_name,
                status=RecipientStatus.pending,
            )
            db.add(recipient)
            await db.flush()

            try:
                context = build_user_context(user)
                subject, html_body = render_email_template(template, context)
                await _send_email(user.email, subject, html_body, raise_on_error=True)
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
    return {
        "first_name": first,
        "last_name": last,
        "name": name,
        "email": recipient.email,
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
        await _send_email(recipient.email, subject, html_body, raise_on_error=True)
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
            await _send_email(recipient.email, subject, html_body, raise_on_error=True)
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
