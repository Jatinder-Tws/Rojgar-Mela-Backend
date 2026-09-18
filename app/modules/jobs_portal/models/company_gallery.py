import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class CompanyGalleryImage(Base):
    __tablename__ = "company_gallery_images"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    provider_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_url = Column(Text, nullable=False)
    caption = Column(String(200), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    source = Column(String(20), nullable=True)  # upload | google

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    provider = relationship("User", back_populates="company_gallery_images")
