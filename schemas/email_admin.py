from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class EmailTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: Optional[str] = Field(None, max_length=100)
    subject: str = Field(..., min_length=1, max_length=500)
    html_body: str = Field(..., min_length=1)
    description: Optional[str] = None
    is_active: bool = True


class EmailTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, max_length=100)
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    html_body: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class EmailTemplateOut(BaseModel):
    id: str
    name: str
    slug: str
    subject: str
    html_body: str
    description: Optional[str] = None
    is_active: bool
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmailTemplateListResponse(BaseModel):
    items: list[EmailTemplateOut]
    total: int
    page: int
    page_size: int


class EmailTemplatePreviewRequest(BaseModel):
    subject: str
    html_body: str
    sample_data: Optional[dict[str, Any]] = None


class EmailTemplatePreviewResponse(BaseModel):
    subject: str
    html_body: str


class EmailTemplateTestSendRequest(BaseModel):
    to_email: str


class EmailImageUploadResponse(BaseModel):
    cid: str
    url: str
    html_snippet: str


class ImportedEmailRow(BaseModel):
    email: str
    name: Optional[str] = None


class AudienceFilter(BaseModel):
    industries: Optional[list[str]] = None
    user_ids: Optional[list[str]] = None
    is_verified: Optional[bool] = None
    imported_emails: Optional[list[ImportedEmailRow]] = None
    job_fair_id: Optional[str] = None


_AUDIENCE_TYPE_LITERAL = Literal[
    "all_seekers",
    "all_providers",
    "all_users",
    "industry_seekers",
    "industry_providers",
    "specific_users",
    "csv_import",
    "job_fair_seekers",
    "job_fair_providers",
]


class EmailCampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    template_id: str
    audience_type: _AUDIENCE_TYPE_LITERAL
    audience_filter: Optional[AudienceFilter] = None


class EmailCampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    template_id: Optional[str] = None
    audience_type: Optional[_AUDIENCE_TYPE_LITERAL] = None
    audience_filter: Optional[AudienceFilter] = None


class EmailCampaignOut(BaseModel):
    id: str
    name: str
    template_id: str
    template_name: Optional[str] = None
    status: str
    audience_type: str
    audience_filter: Optional[dict[str, Any]] = None
    total_recipients: int
    sent_count: int
    failed_count: int
    job_id: Optional[str] = None
    created_by: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmailCampaignListResponse(BaseModel):
    items: list[EmailCampaignOut]
    total: int
    page: int
    page_size: int


class AudienceEstimateRequest(BaseModel):
    audience_type: _AUDIENCE_TYPE_LITERAL
    audience_filter: Optional[AudienceFilter] = None


class AudienceEstimateResponse(BaseModel):
    count: int
    sample_users: list[dict[str, Any]]


class CampaignJobStarted(BaseModel):
    job_id: str
    campaign_id: str
    message: str


class CampaignJobStatus(BaseModel):
    id: str
    campaign_id: str
    status: str
    progress: int
    total: int
    processed: int
    sent: int
    failed: int
    message: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CampaignRecipientOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    email: str
    recipient_name: Optional[str] = None
    status: str
    error: Optional[str] = None
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CampaignRecipientListResponse(BaseModel):
    items: list[CampaignRecipientOut]
    total: int
    page: int
    page_size: int


class CampaignDeliveryStats(BaseModel):
    total: int
    sent: int
    failed: int
    pending: int
    skipped: int


class ResendRecipientResponse(BaseModel):
    recipient: CampaignRecipientOut
    message: str


class ResendFailedResponse(BaseModel):
    total: int
    sent: int
    failed: int
    message: str


class AudienceUserOut(BaseModel):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    role: str
    industry: Optional[str] = None
    company_name: Optional[str] = None


class AudienceUserListResponse(BaseModel):
    items: list[AudienceUserOut]
    total: int
    page: int
    page_size: int


class AudienceUserIdsResponse(BaseModel):
    ids: list[str]
    total: int
