import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from app.core.database import Base


class Scholarship(Base):
    __tablename__ = "scholarships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(150), nullable=False, index=True)
    source_platform = Column(String(50), nullable=False, index=True)  # 'unstop', 'buddy4study'
    
    title = Column(String(500), nullable=False, index=True)
    slug = Column(String(500), nullable=True, index=True)
    
    organization_name = Column(String(300), nullable=True, index=True)
    organization_logo = Column(String(1000), nullable=True)
    banner_image = Column(String(1000), nullable=True)
    
    description = Column(Text, nullable=True)
    eligibility_criteria = Column(Text, nullable=True)
    award_amount = Column(String(200), nullable=True)  # e.g., "₹50,000" or "Up to ₹2,50,000 / year"
    award_type = Column(String(100), nullable=True)    # e.g., "Full Tuition", "Financial Aid", "Cash Grant"
    currency = Column(String(10), default="INR", nullable=False)
    
    target_education_levels = Column(JSON, default=list, nullable=True)  # ["School", "Undergraduate", "Postgraduate"]
    gender_eligibility = Column(String(50), default="All", nullable=True)  # "All", "Female", "Male"
    region_or_country = Column(String(100), default="India", nullable=True)
    
    deadline = Column(DateTime, nullable=True, index=True)
    is_featured = Column(Boolean, default=False, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    application_url = Column(String(1000), nullable=False)  # Redirect URL for "Apply Now"
    raw_data = Column(JSON, nullable=True)                  # Original provider payload
    
    last_synced_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("source_platform", "external_id", name="uq_scholarship_source_external_id"),
        Index("ix_scholarships_platform_active", "source_platform", "is_active"),
        Index("ix_scholarships_deadline_active", "deadline", "is_active"),
    )
