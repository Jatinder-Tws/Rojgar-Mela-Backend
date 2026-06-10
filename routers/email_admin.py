"""Super admin email templates and bulk email campaigns."""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.email_campaign import CampaignStatus, EmailCampaign, EmailCampaignRecipient, RecipientStatus
from models.email_template import EmailTemplate
from models.user import User, UserRole
from schemas.email_admin import (
    AudienceEstimateRequest,
    AudienceEstimateResponse,
    AudienceUserListResponse,
    AudienceUserOut,
    CampaignJobStarted,
    CampaignJobStatus,
    CampaignDeliveryStats,
    CampaignRecipientListResponse,
    CampaignRecipientOut,
    ResendFailedResponse,
    ResendRecipientResponse,
    EmailCampaignCreate,
    EmailCampaignListResponse,
    EmailCampaignOut,
    EmailCampaignUpdate,
    EmailTemplateCreate,
    EmailTemplateListResponse,
    EmailTemplateOut,
    EmailTemplatePreviewRequest,
    EmailTemplatePreviewResponse,
    EmailTemplateTestSendRequest,
    EmailTemplateUpdate,
)
from services.auth_service import require_super_admin
from services.email_campaign_job_store import get_job
from services.email_campaign_service import (
    count_audience,
    get_audience_users,
    resend_all_failed,
    resend_to_recipient,
    run_campaign_send_job,
    start_campaign_job,
)
from services.email_service import _send_email
from services.email_template_service import preview_email, render_email_template, slugify

router = APIRouter(prefix="/super-admin", tags=["super-admin-email"])


def _template_to_out(t: EmailTemplate) -> EmailTemplateOut:
    return EmailTemplateOut.model_validate(t)


def _campaign_to_out(c: EmailCampaign, template_name: Optional[str] = None) -> EmailCampaignOut:
    return EmailCampaignOut(
        id=c.id,
        name=c.name,
        template_id=c.template_id,
        template_name=template_name,
        status=c.status.value if hasattr(c.status, "value") else c.status,
        audience_type=c.audience_type.value if hasattr(c.audience_type, "value") else c.audience_type,
        audience_filter=c.audience_filter,
        total_recipients=c.total_recipients,
        sent_count=c.sent_count,
        failed_count=c.failed_count,
        job_id=c.job_id,
        created_by=c.created_by,
        started_at=c.started_at,
        completed_at=c.completed_at,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


# ── Email Templates ──────────────────────────────────────────────────────────

@router.get("/email-templates", response_model=EmailTemplateListResponse)
async def list_email_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    q = select(EmailTemplate)
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.where(
            or_(
                EmailTemplate.name.ilike(term),
                EmailTemplate.slug.ilike(term),
                EmailTemplate.subject.ilike(term),
            )
        )
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(EmailTemplate.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(q)).scalars().all()
    return EmailTemplateListResponse(
        items=[_template_to_out(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/email-templates", response_model=EmailTemplateOut, status_code=status.HTTP_201_CREATED)
async def create_email_template(
    body: EmailTemplateCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    slug = slugify(body.slug or body.name)
    existing = (await db.execute(select(EmailTemplate).where(EmailTemplate.slug == slug))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Template slug already exists")

    template = EmailTemplate(
        name=body.name,
        slug=slug,
        subject=body.subject,
        html_body=body.html_body,
        description=body.description,
        is_active=body.is_active,
        created_by=admin.id,
    )
    db.add(template)
    await db.flush()
    return _template_to_out(template)


@router.post("/email-templates/preview", response_model=EmailTemplatePreviewResponse)
async def preview_email_template(
    body: EmailTemplatePreviewRequest,
    _admin: User = Depends(require_super_admin),
):
    subject, html_body = preview_email(body.subject, body.html_body, body.sample_data)
    return EmailTemplatePreviewResponse(subject=subject, html_body=html_body)


@router.get("/email-templates/{template_id}", response_model=EmailTemplateOut)
async def get_email_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    template = (await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_to_out(template)


@router.put("/email-templates/{template_id}", response_model=EmailTemplateOut)
async def update_email_template(
    template_id: str,
    body: EmailTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    template = (await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if body.slug is not None:
        slug = slugify(body.slug)
        clash = (await db.execute(
            select(EmailTemplate).where(EmailTemplate.slug == slug, EmailTemplate.id != template_id)
        )).scalar_one_or_none()
        if clash:
            raise HTTPException(status_code=409, detail="Template slug already exists")
        template.slug = slug

    for field in ("name", "subject", "html_body", "description", "is_active"):
        value = getattr(body, field)
        if value is not None:
            setattr(template, field, value)

    await db.flush()
    return _template_to_out(template)


@router.delete("/email-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    template = (await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    in_use = (await db.execute(
        select(func.count()).where(EmailCampaign.template_id == template_id)
    )).scalar() or 0
    if in_use:
        raise HTTPException(status_code=400, detail="Template is used by campaigns and cannot be deleted")

    await db.delete(template)


@router.post("/email-templates/{template_id}/test-send")
async def test_send_email_template(
    template_id: str,
    body: EmailTemplateTestSendRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    template = (await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    subject, html_body = render_email_template(template)
    await _send_email(body.to_email, subject, html_body)
    return {"message": f"Test email sent to {body.to_email}"}


# ── Email Campaigns ──────────────────────────────────────────────────────────

@router.get("/email-campaigns", response_model=EmailCampaignListResponse)
async def list_email_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    q = select(EmailCampaign, EmailTemplate.name.label("template_name")).join(
        EmailTemplate, EmailCampaign.template_id == EmailTemplate.id
    )
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.where(EmailCampaign.name.ilike(term))
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(EmailCampaign.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).all()
    items = [_campaign_to_out(c, template_name) for c, template_name in rows]
    return EmailCampaignListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/email-campaigns", response_model=EmailCampaignOut, status_code=status.HTTP_201_CREATED)
async def create_email_campaign(
    body: EmailCampaignCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    template = (await db.execute(select(EmailTemplate).where(EmailTemplate.id == body.template_id))).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    audience_filter = body.audience_filter.model_dump() if body.audience_filter else None
    count = await count_audience(db, body.audience_type, audience_filter)

    campaign = EmailCampaign(
        name=body.name,
        template_id=body.template_id,
        audience_type=body.audience_type,
        audience_filter=audience_filter,
        total_recipients=count,
        created_by=admin.id,
    )
    db.add(campaign)
    await db.flush()
    return _campaign_to_out(campaign, template.name)


@router.post("/email-campaigns/estimate-audience", response_model=AudienceEstimateResponse)
async def estimate_audience(
    body: AudienceEstimateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    audience_filter = body.audience_filter.model_dump() if body.audience_filter else None
    count = await count_audience(db, body.audience_type, audience_filter)
    users, _ = await get_audience_users(db, body.audience_type, audience_filter, page=1, page_size=5)
    sample = [
        {
            "id": u.id,
            "name": f"{u.first_name or ''} {u.last_name or ''}".strip(),
            "email": u.email,
            "role": u.role.value if u.role else "",
        }
        for u in users
    ]
    return AudienceEstimateResponse(count=count, sample_users=sample)


@router.get("/email-campaigns/audience-users", response_model=AudienceUserListResponse)
async def list_audience_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
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
        full_name = func.concat(func.coalesce(User.first_name, ""), " ", func.coalesce(User.last_name, ""))
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

    items = [
        AudienceUserOut(
            id=u.id,
            first_name=u.first_name,
            last_name=u.last_name,
            email=u.email,
            role=u.role.value if u.role else "",
            industry=u.industry,
            company_name=u.company_name,
        )
        for u in users
    ]
    return AudienceUserListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/email-campaigns/jobs/{job_id}", response_model=CampaignJobStatus)
async def get_campaign_job_status(
    job_id: str,
    _admin: User = Depends(require_super_admin),
):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return CampaignJobStatus(**job)


@router.get("/email-campaigns/{campaign_id}", response_model=EmailCampaignOut)
async def get_email_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    row = (await db.execute(
        select(EmailCampaign, EmailTemplate.name.label("template_name"))
        .join(EmailTemplate, EmailCampaign.template_id == EmailTemplate.id)
        .where(EmailCampaign.id == campaign_id)
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign, template_name = row
    return _campaign_to_out(campaign, template_name)


@router.put("/email-campaigns/{campaign_id}", response_model=EmailCampaignOut)
async def update_email_campaign(
    campaign_id: str,
    body: EmailCampaignUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    campaign = (await db.execute(select(EmailCampaign).where(EmailCampaign.id == campaign_id))).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status not in (CampaignStatus.draft,):
        raise HTTPException(status_code=400, detail="Only draft campaigns can be edited")

    if body.template_id:
        template = (await db.execute(select(EmailTemplate).where(EmailTemplate.id == body.template_id))).scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        campaign.template_id = body.template_id

    if body.name is not None:
        campaign.name = body.name
    if body.audience_type is not None:
        campaign.audience_type = body.audience_type
    if body.audience_filter is not None:
        campaign.audience_filter = body.audience_filter.model_dump()

    audience_type = campaign.audience_type.value if hasattr(campaign.audience_type, "value") else campaign.audience_type
    campaign.total_recipients = await count_audience(db, audience_type, campaign.audience_filter)

    template = (await db.execute(select(EmailTemplate).where(EmailTemplate.id == campaign.template_id))).scalar_one_or_none()
    await db.flush()
    return _campaign_to_out(campaign, template.name if template else None)


@router.delete("/email-campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    campaign = (await db.execute(select(EmailCampaign).where(EmailCampaign.id == campaign_id))).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == CampaignStatus.running:
        raise HTTPException(status_code=400, detail="Cannot delete a running campaign")
    await db.delete(campaign)


@router.post("/email-campaigns/{campaign_id}/send", response_model=CampaignJobStarted)
async def send_email_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    campaign = (await db.execute(select(EmailCampaign).where(EmailCampaign.id == campaign_id))).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status in (CampaignStatus.running, CampaignStatus.queued):
        raise HTTPException(status_code=400, detail="Campaign is already sending")

    audience_type = campaign.audience_type.value if hasattr(campaign.audience_type, "value") else campaign.audience_type
    count = await count_audience(db, audience_type, campaign.audience_filter)
    if count == 0:
        raise HTTPException(status_code=400, detail="No recipients match the selected audience")

    job_id = start_campaign_job(campaign_id)
    campaign.status = CampaignStatus.queued
    campaign.job_id = job_id
    campaign.total_recipients = count
    await db.flush()

    asyncio.create_task(run_campaign_send_job(job_id, campaign_id))
    return CampaignJobStarted(
        job_id=job_id,
        campaign_id=campaign_id,
        message=f"Sending to {count} recipients…",
    )


@router.get("/email-campaigns/{campaign_id}/delivery-stats", response_model=CampaignDeliveryStats)
async def get_campaign_delivery_stats(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    campaign = (await db.execute(select(EmailCampaign).where(EmailCampaign.id == campaign_id))).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    async def _count(status: Optional[RecipientStatus] = None) -> int:
        q = select(func.count()).where(EmailCampaignRecipient.campaign_id == campaign_id)
        if status is not None:
            q = q.where(EmailCampaignRecipient.status == status)
        return (await db.execute(q)).scalar() or 0

    sent = await _count(RecipientStatus.sent)
    failed = await _count(RecipientStatus.failed)
    pending = await _count(RecipientStatus.pending)
    skipped = await _count(RecipientStatus.skipped)
    total = sent + failed + pending + skipped
    if total == 0:
        total = campaign.total_recipients

    return CampaignDeliveryStats(
        total=total,
        sent=sent,
        failed=failed,
        pending=pending,
        skipped=skipped,
    )


def _recipient_to_out(r: EmailCampaignRecipient) -> CampaignRecipientOut:
    return CampaignRecipientOut(
        id=r.id,
        user_id=r.user_id,
        email=r.email,
        recipient_name=r.recipient_name,
        status=r.status.value if hasattr(r.status, "value") else r.status,
        error=r.error,
        sent_at=r.sent_at,
    )


@router.post("/email-campaigns/{campaign_id}/resend-failed", response_model=ResendFailedResponse)
async def resend_failed_campaign_emails(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    campaign = (await db.execute(select(EmailCampaign).where(EmailCampaign.id == campaign_id))).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == CampaignStatus.running:
        raise HTTPException(status_code=400, detail="Campaign is still sending")

    try:
        total, sent, still_failed = await resend_all_failed(db, campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if total == 0:
        return ResendFailedResponse(total=0, sent=0, failed=0, message="No failed emails to resend")

    return ResendFailedResponse(
        total=total,
        sent=sent,
        failed=still_failed,
        message=f"Resent {sent} of {total} failed email(s)",
    )


@router.post("/email-campaigns/{campaign_id}/recipients/{recipient_id}/resend", response_model=ResendRecipientResponse)
async def resend_campaign_recipient_email(
    campaign_id: str,
    recipient_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    campaign = (await db.execute(select(EmailCampaign).where(EmailCampaign.id == campaign_id))).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == CampaignStatus.running:
        raise HTTPException(status_code=400, detail="Campaign is still sending")

    try:
        recipient = await resend_to_recipient(db, campaign_id, recipient_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Resend failed: {exc}") from exc

    return ResendRecipientResponse(
        recipient=_recipient_to_out(recipient),
        message=f"Email resent to {recipient.email}",
    )


@router.get("/email-campaigns/{campaign_id}/recipients", response_model=CampaignRecipientListResponse)
async def list_campaign_recipients(
    campaign_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    campaign = (await db.execute(select(EmailCampaign).where(EmailCampaign.id == campaign_id))).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    q = select(EmailCampaignRecipient).where(EmailCampaignRecipient.campaign_id == campaign_id)
    if status_filter:
        q = q.where(EmailCampaignRecipient.status == status_filter)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(EmailCampaignRecipient.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(q)).scalars().all()

    return CampaignRecipientListResponse(
        items=[_recipient_to_out(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )
