import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Text, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base

def _uuid():
    return str(uuid.uuid4())

class JobFair(Base):
    __tablename__ = "job_fairs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    date = Column(DateTime, nullable=False)
    location = Column(String(200), nullable=False)
    banner_image_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    industries = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    companies = relationship("JobFairCompany", back_populates="job_fair", cascade="all, delete-orphan")
    seekers = relationship("JobFairSeeker", back_populates="job_fair", cascade="all, delete-orphan")


class JobFairCompany(Base):
    __tablename__ = "job_fair_companies"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    job_fair_id = Column(UUID(as_uuid=False), ForeignKey("job_fairs.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Registration details
    department = Column(String(100), nullable=True)
    sector = Column(String(100), nullable=True)
    vacancy = Column(String(100), nullable=True)
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Complete company details Snapshot
    company_name = Column(String(200), nullable=True)
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    website = Column(String(200), nullable=True)
    company_size = Column(String(100), nullable=True)
    company_address = Column(Text, nullable=True)
    contact_person_name = Column(String(200), nullable=True)
    contact_person_designation = Column(String(200), nullable=True)
    contact_person_phone = Column(String(50), nullable=True)
    openings = Column(JSON, nullable=True)
    logo_url = Column(String(500), nullable=True)
    state = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)

    # Relationships
    job_fair = relationship("JobFair", back_populates="companies")
    provider = relationship("User")


class JobFairSeeker(Base):
    __tablename__ = "job_fair_seekers"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    job_fair_id = Column(UUID(as_uuid=False), ForeignKey("job_fairs.id", ondelete="CASCADE"), nullable=False, index=True)
    seeker_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    is_attending = Column(Boolean, default=True, nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job_fair = relationship("JobFair", back_populates="seekers")
    seeker = relationship("User")
