import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class SiteAnnouncement(Base):
    __tablename__ = "site_announcements"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    title = Column(String(255), nullable=True)
    text = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default="announcement")  # announcement, event, popup_modal, slider_banner, news
    display_placement = Column(String(50), nullable=False, default="top_banner")  # top_banner, popup_modal, home_slider, all
    target_pages = Column(String(255), nullable=False, default="all")  # all, home, colleges, jobs, training
    image_url = Column(Text, nullable=True)
    link_url = Column(Text, nullable=True)
    link_text = Column(String(100), nullable=True)
    event_date = Column(DateTime, nullable=True)
    event_location = Column(String(255), nullable=True)
    organizer = Column(String(255), nullable=True)
    home_layout = Column(String(20), nullable=True)  # banner | card — homepage events section
    badge_label = Column(String(80), nullable=True)
    tagline = Column(String(255), nullable=True)
    show_content_on_image = Column(Boolean, nullable=False, default=True)
    gallery_images = Column(JSON, nullable=True, default=list)
    qr_code_url = Column(Text, nullable=True)
    modal_delay_seconds = Column(Integer, nullable=False, default=5)
    start_date = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
