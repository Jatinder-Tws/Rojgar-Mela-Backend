from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AIBlogGenerateRequest(BaseModel):
    prompt: str = Field(..., description="Prompt or topic for the blog post", min_length=3)
    category: Optional[str] = Field(None, description="Target category e.g. Resume & Cover Letters, Engineering & Tech")
    tone: Optional[str] = Field("professional", description="Tone: professional | practical | educational")
    include_templates: bool = Field(True, description="Whether to generate ready-to-copy templates")
    include_qa: bool = Field(True, description="Whether to generate interview Q&A")


class AIBlogEditRequest(BaseModel):
    instruction: str = Field(..., description="Prompt or instructions on what changes to make to the blog", min_length=3)
    current_blog: Dict[str, Any] = Field(..., description="Current blog post data to edit")
    target_scope: Optional[str] = Field("auto", description="Scope of edit: auto | add_section | rewrite_section | faqs | tone_polish")


class AIBlogImageGenerateRequest(BaseModel):
    title: str = Field(..., description="Blog title", min_length=2)
    subtitle: Optional[str] = Field(None, description="Subtitle or context")
    category: Optional[str] = Field(None, description="Category")


class AIBlogSection(BaseModel):
    id: str
    heading: str
    paragraphs: List[str]
    keyTakeaways: Optional[List[str]] = None
    templateSnippet: Optional[Dict[str, Any]] = None
    qaList: Optional[List[Dict[str, Any]]] = None
    tableData: Optional[Dict[str, Any]] = None


class AIBlogFAQ(BaseModel):
    question: str
    answer: str


class AIBlogAuthor(BaseModel):
    name: str
    role: str
    avatar: str
    bio: Optional[str] = None


class AIBlogGenerateResponse(BaseModel):
    title: str
    slug: str
    subtitle: Optional[str] = None
    excerpt: str
    category: str
    tags: List[str]
    readTime: str
    coverImage: str
    author: AIBlogAuthor
    sections: List[AIBlogSection]
    faqs: List[AIBlogFAQ]
