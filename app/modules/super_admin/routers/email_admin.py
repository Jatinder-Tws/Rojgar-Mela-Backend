"""Super admin email templates and bulk email campaigns."""
import asyncio
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.super_admin.models.email_campaign import CampaignStatus, EmailCampaign, EmailCampaignRecipient, RecipientStatus
from app.modules.super_admin.models.email_template import EmailTemplate
from app.shared.models.user import User, UserRole
from app.modules.super_admin.schemas.email_admin import (
    AudienceEstimateRequest,
    AudienceEstimateResponse,
    AudienceUserIdsResponse,
    AudienceUserListResponse,
    AudienceUserOut,
    CampaignJobStarted,
    CampaignJobStatus,
    CampaignDeliveryStats,
    CampaignRecipientListResponse,
    CampaignRecipientOut,
    ResendRecipientResponse,
    EmailCampaignCreate,
    EmailCampaignListResponse,
    EmailCampaignOut,
    EmailCampaignUpdate,
    EmailTemplateCreate,
    EmailTemplateListResponse,
    EmailTemplateOut,
    EmailImageUploadResponse,
    EmailTemplatePreviewRequest,
    EmailTemplatePreviewResponse,
    EmailTemplateTestSendRequest,
    EmailTemplateUpdate,
)
from app.core.dependencies import require_super_admin
from app.modules.super_admin.services.email_campaign_job_store import get_job
from app.modules.super_admin.services.email_campaign_service import (
    count_audience,
    get_audience_sample,
    get_audience_users,
    get_picker_user_ids,
    list_picker_users,
    resend_to_recipient,
    run_campaign_resend_failed_job,
    run_campaign_send_job,
    start_campaign_job,
)
from app.shared.services.email_service import _send_email, send_campaign_email
from app.core.config import settings
from app.modules.super_admin.services.email_template_service import (
    build_image_html_snippet,
    email_assets_dir,
    preview_email,
    render_email_template,
    slugify,
)

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
    status: Optional[str] = Query(None),
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
    if status and status != "all":
        if status == "active":
            q = q.where(EmailTemplate.is_active.is_(True))
        elif status == "inactive":
            q = q.where(EmailTemplate.is_active.is_(False))
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
    await db.commit()
    return _template_to_out(template)


@router.post("/email-templates/preview", response_model=EmailTemplatePreviewResponse)
async def preview_email_template(
    body: EmailTemplatePreviewRequest,
    _admin: User = Depends(require_super_admin),
):
    subject, html_body = preview_email(body.subject, body.html_body, body.sample_data)
    return EmailTemplatePreviewResponse(subject=subject, html_body=html_body)


_ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


@router.post("/email-templates/upload-image", response_model=EmailImageUploadResponse)
async def upload_email_template_image(
    file: UploadFile = File(...),
    _admin: User = Depends(require_super_admin),
):
    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only PNG, JPEG, GIF, and WebP images are allowed")

    data = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail=f"Image must be under {settings.MAX_UPLOAD_MB} MB")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    ext = _ALLOWED_IMAGE_TYPES[content_type]
    content_id = f"email_img_{uuid.uuid4().hex[:12]}"
    dest = email_assets_dir() / f"{content_id}{ext}"
    dest.write_bytes(data)

    public_url = f"/uploads/email_assets/{content_id}{ext}"
    return EmailImageUploadResponse(
        cid=content_id,
        url=public_url,
        html_snippet=build_image_html_snippet(content_id),
    )


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

    await db.commit()
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
    await send_campaign_email(body.to_email, subject, html_body)
    return {"message": f"Test email sent to {body.to_email}"}


# ── Email Campaigns ──────────────────────────────────────────────────────────

@router.get("/email-campaigns", response_model=EmailCampaignListResponse)
async def list_email_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    q = select(EmailCampaign, EmailTemplate.name.label("template_name")).join(
        EmailTemplate, EmailCampaign.template_id == EmailTemplate.id
    )
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.where(EmailCampaign.name.ilike(term))
    if status and status != "all":
        q = q.where(EmailCampaign.status == status)
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

    audience_filter = body.audience_filter.model_dump(exclude_none=True) if body.audience_filter else {}
    if not audience_filter.get("audience_types"):
        audience_filter["audience_types"] = [body.audience_type]
    count = await count_audience(db, body.audience_type, audience_filter)
    if count == 0:
        raise HTTPException(status_code=400, detail="Audience has no recipients")

    campaign = EmailCampaign(
        name=body.name,
        template_id=body.template_id,
        audience_type=body.audience_type,
        audience_filter=audience_filter,
        total_recipients=count,
        created_by=admin.id,
    )
    db.add(campaign)
    await db.commit()
    return _campaign_to_out(campaign, template.name)


@router.post("/email-campaigns/estimate-audience", response_model=AudienceEstimateResponse)
async def estimate_audience(
    body: AudienceEstimateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    audience_filter = body.audience_filter.model_dump(exclude_none=True) if body.audience_filter else None
    count = await count_audience(db, body.audience_type, audience_filter)
    sample = await get_audience_sample(db, body.audience_type, audience_filter, limit=5)
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
    users, total = await list_picker_users(
        db, page=page, page_size=page_size, search=search, role=role
    )
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


@router.get("/email-campaigns/audience-user-ids", response_model=AudienceUserIdsResponse)
async def list_audience_user_ids(
    search: Optional[str] = None,
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    """Return all user IDs matching picker filters (for select-all across pages)."""
    ids, total = await get_picker_user_ids(db, search=search, role=role)
    return AudienceUserIdsResponse(ids=ids, total=total)


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
        audience_filter = body.audience_filter.model_dump(exclude_none=True)
        audience_type_for_filter = (
            body.audience_type
            or (campaign.audience_type.value if hasattr(campaign.audience_type, "value") else campaign.audience_type)
        )
        if not audience_filter.get("audience_types"):
            audience_filter["audience_types"] = [audience_type_for_filter]
        campaign.audience_filter = audience_filter

    audience_type = campaign.audience_type.value if hasattr(campaign.audience_type, "value") else campaign.audience_type
    campaign.total_recipients = await count_audience(db, audience_type, campaign.audience_filter)

    template = (await db.execute(select(EmailTemplate).where(EmailTemplate.id == campaign.template_id))).scalar_one_or_none()
    await db.commit()
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
    await db.commit()

    from app.shared.services.celery_tasks import broadcast_bulk_email_task
    broadcast_bulk_email_task.delay(campaign_id, job_id, is_resend=False)
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

    # Reconcile the campaign's denormalized counters with the live recipient
    # counts. These can drift (e.g. recipient statuses change without the
    # campaign row being updated), which makes the campaign detail endpoint
    # disagree with these delivery stats.
    if total > 0 and (campaign.sent_count != sent or campaign.failed_count != failed):
        campaign.sent_count = sent
        campaign.failed_count = failed
        await db.commit()

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


@router.post("/email-campaigns/{campaign_id}/resend-failed", response_model=CampaignJobStarted)
async def resend_failed_campaign_emails(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    campaign = (await db.execute(select(EmailCampaign).where(EmailCampaign.id == campaign_id))).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status in (CampaignStatus.running, CampaignStatus.queued):
        raise HTTPException(status_code=400, detail="Campaign is already sending")

    failed_count = (
        await db.execute(
            select(func.count()).where(
                EmailCampaignRecipient.campaign_id == campaign_id,
                EmailCampaignRecipient.status == RecipientStatus.failed,
            )
        )
    ).scalar() or 0

    if failed_count == 0:
        raise HTTPException(status_code=400, detail="No failed emails to resend")

    job_id = start_campaign_job(campaign_id)
    campaign.status = CampaignStatus.queued
    campaign.job_id = job_id
    from app.shared.services.celery_tasks import broadcast_bulk_email_task
    broadcast_bulk_email_task.delay(campaign_id, job_id, is_resend=True)
    return CampaignJobStarted(
        job_id=job_id,
        campaign_id=campaign_id,
        message=f"Resending {failed_count} failed email(s)…",
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
        try:
            status_enum = RecipientStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid status filter") from exc
        q = q.where(EmailCampaignRecipient.status == status_enum)

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
