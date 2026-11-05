import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# Legacy rows were stored with an absolute dev-host URL
# (http://localhost:8000/uploads/blog_images/x.jpg), which never loads in production.
# Strip any "<scheme>://<host>[:port]" prefix that points at an /uploads path so
# the frontend can resolve it against the live API base.
_LOCAL_UPLOAD_PREFIX = re.compile(
    r"^https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?(?=/(?:api/)?uploads/)",
    re.IGNORECASE,
)


def _own_host_prefixes() -> tuple[str, ...]:
    """Absolute origins this deployment may have stamped on stored upload URLs."""
    from app.core.config import settings

    out: list[str] = []
    for raw in (
        settings.PUBLIC_BASE_URL or settings.BACKEND_PUBLIC_URL,
        settings.BACKEND_PUBLIC_URL,
        settings.FRONTEND_URL,
    ):
        origin = (raw or "").strip().rstrip("/")
        if origin:
            out.append(origin)
    return tuple(out)


def normalize_blog_media_url(value: Optional[str]) -> Optional[str]:
    """Turn stored upload URLs into a relative `/uploads/...` path; leave external URLs alone."""
    if value is None:
        return None
    url = value.strip()
    if not url:
        return None
    url = _LOCAL_UPLOAD_PREFIX.sub("", url, count=1)
    if url.startswith(("http://", "https://")):
        for origin in _own_host_prefixes():
            if url.startswith(origin + "/uploads/") or url.startswith(origin + "/api/uploads/"):
                url = url[len(origin):]
                break
    if url.startswith("/api/uploads/"):
        url = url[len("/api"):]
    return url


class FAQItem(BaseModel):
    question: str
    answer: str


class TemplateSnippet(BaseModel):
    title: str
    description: str
    content: str


class Subsection(BaseModel):
    title: str
    content: str
    points: Optional[List[str]] = None


class QAListItem(BaseModel):
    question: str
    answer: str
    sampleAnswer: Optional[str] = None
    proTip: Optional[str] = None


class TableData(BaseModel):
    headers: List[str]
    rows: List[List[str]]


class BlogSection(BaseModel):
    id: str
    heading: str
    paragraphs: List[str]
    subsections: Optional[List[Subsection]] = None
    keyTakeaways: Optional[List[str]] = None
    templateSnippet: Optional[TemplateSnippet] = None
    qaList: Optional[List[QAListItem]] = None
    tableData: Optional[TableData] = None


class BlogPostBase(BaseModel):
    title: str = Field(..., max_length=300)
    slug: Optional[str] = Field(None, max_length=255)
    subtitle: Optional[str] = Field(None, max_length=500)
    excerpt: str
    category: str = Field(..., max_length=100)
    tags: List[str] = []
    author_name: str = "Rojgar Mela Content Team"
    author_role: Optional[str] = "Career Research & Editorial"
    author_avatar: Optional[str] = None
    author_bio: Optional[str] = None
    cover_image: Optional[str] = None
    read_time: str = "6 min read"
    published_date: Optional[str] = None
    status: str = "published"  # 'draft', 'published', 'archived'
    is_featured: bool = False
    content_markdown: Optional[str] = None
    sections: Optional[List[Dict[str, Any]]] = []
    faqs: Optional[List[FAQItem]] = []

    @field_validator("author_avatar", "cover_image", mode="before")
    @classmethod
    def _normalize_media(cls, v: Any) -> Any:
        return normalize_blog_media_url(v) if isinstance(v, str) else v


class BlogPostCreate(BlogPostBase):
    pass


class BlogPostUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    subtitle: Optional[str] = None
    excerpt: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    author_avatar: Optional[str] = None
    author_bio: Optional[str] = None
    cover_image: Optional[str] = None
    read_time: Optional[str] = None
    published_date: Optional[str] = None
    status: Optional[str] = None
    is_featured: Optional[bool] = None
    content_markdown: Optional[str] = None
    sections: Optional[List[Dict[str, Any]]] = None
    faqs: Optional[List[FAQItem]] = None

    @field_validator("author_avatar", "cover_image", mode="before")
    @classmethod
    def _normalize_media(cls, v: Any) -> Any:
        return normalize_blog_media_url(v) if isinstance(v, str) else v


class BlogPostOut(BlogPostBase):
    id: str
    slug: str
    views_count: int = 0
    likes_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BlogPostListResponse(BaseModel):
    items: List[BlogPostOut]
    total: int
    page: int
    limit: int
    pages: int


class BlogCategoryOut(BaseModel):
    id: str
    name: str
    count: int


class BlogCategoryListResponse(BaseModel):
    categories: List[BlogCategoryOut]


class BlogSeedResponse(BaseModel):
    message: str
    seeded_count: int
    total_count: int
