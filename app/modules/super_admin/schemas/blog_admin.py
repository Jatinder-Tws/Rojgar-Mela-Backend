from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


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
