import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    subtitle = Column(String(500), nullable=True)
    excerpt = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    tags = Column(JSON, nullable=False, server_default=text("'[]'::json"))
    
    author_name = Column(String(150), nullable=False, default="Rojgar Mela Content Team")
    author_role = Column(String(150), nullable=True, default="Career Research & Editorial")
    author_avatar = Column(String(500), nullable=True)
    author_bio = Column(Text, nullable=True)
    
    cover_image = Column(String(500), nullable=True)
    read_time = Column(String(50), nullable=False, default="6 min read")
    published_date = Column(String(100), nullable=True)
    
    status = Column(String(20), nullable=False, default="published", server_default=text("'published'")) # 'draft', 'published', 'archived'
    is_featured = Column(Boolean, default=False, nullable=False, server_default=text("false"))
    views_count = Column(Integer, default=0, nullable=False, server_default=text("0"))
    likes_count = Column(Integer, default=0, nullable=False, server_default=text("0"))
    
    content_markdown = Column(Text, nullable=True)
    sections = Column(JSON, nullable=True, server_default=text("'[]'::json"))
    faqs = Column(JSON, nullable=True, server_default=text("'[]'::json"))
    
    created_by_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
