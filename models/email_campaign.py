import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from database import Base


def _uuid():
    return str(uuid.uuid4())


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class AudienceType(str, enum.Enum):
    all_seekers = "all_seekers"
    all_providers = "all_providers"
    all_users = "all_users"
    industry_seekers = "industry_seekers"
    industry_providers = "industry_providers"
    specific_users = "specific_users"


class RecipientStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    skipped = "skipped"


class EmailCampaign(Base):
    __tablename__ = "email_campaigns"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(200), nullable=False)
    template_id = Column(UUID(as_uuid=False), ForeignKey("email_templates.id", ondelete="RESTRICT"), nullable=False)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.draft, nullable=False)
    audience_type = Column(Enum(AudienceType), nullable=False)
    audience_filter = Column(JSON, nullable=True)
    total_recipients = Column(Integer, default=0, nullable=False)
    sent_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    job_id = Column(String(36), nullable=True)
    created_by = Column(UUID(as_uuid=False), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    template = relationship("EmailTemplate")
    recipients = relationship("EmailCampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")


class EmailCampaignRecipient(Base):
    __tablename__ = "email_campaign_recipients"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    campaign_id = Column(UUID(as_uuid=False), ForeignKey("email_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String(255), nullable=False)
    recipient_name = Column(String(200), nullable=True)
    status = Column(Enum(RecipientStatus), default=RecipientStatus.pending, nullable=False)
    error = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("EmailCampaign", back_populates="recipients")
