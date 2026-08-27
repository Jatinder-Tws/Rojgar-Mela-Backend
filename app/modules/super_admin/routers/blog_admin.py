import os
import shutil
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_upload_dir, settings
from app.core.database import get_db
from app.core.dependencies import require_super_admin
from app.shared.models.user import User
from app.modules.super_admin.schemas.ai_blog import (
    AIBlogEditRequest,
    AIBlogGenerateRequest,
    AIBlogGenerateResponse,
    AIBlogImageGenerateRequest,
)
from app.modules.super_admin.schemas.blog_admin import (
    BlogCategoryListResponse,
    BlogPostCreate,
    BlogPostListResponse,
    BlogPostOut,
    BlogPostUpdate,
    BlogSeedResponse,
)
from app.modules.super_admin.services import blog_service, ai_blog_generator

router = APIRouter(prefix="/api/super-admin/blogs", tags=["Super Admin Blogs"])


@router.post("/generate-ai", response_model=AIBlogGenerateResponse)
async def generate_ai_blog(
    data: AIBlogGenerateRequest,
    admin: User = Depends(require_super_admin),
):
    """Generate a complete structured blog post from a prompt using AI."""
    return await ai_blog_generator.generate_blog_with_ai(data)


@router.post("/edit-ai", response_model=AIBlogGenerateResponse)
async def edit_ai_blog(
    data: AIBlogEditRequest,
    admin: User = Depends(require_super_admin),
):
    """Edit, modify, or expand an existing blog post according to editorial instructions."""
    return await ai_blog_generator.edit_blog_with_ai(data)


@router.post("/generate-image-ai")
async def generate_ai_blog_image(
    data: AIBlogImageGenerateRequest,
    admin: User = Depends(require_super_admin),
):
    """Generate an editorial banner image for a blog using AI and store in media uploads."""
    image_url = await ai_blog_generator.generate_blog_image_with_ai(
        title=data.title,
        subtitle=data.subtitle,
        category=data.category,
    )
    if not image_url:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate AI blog image. Please try again.",
        )
    return {"url": image_url}


@router.get("", response_model=BlogPostListResponse)
async def list_admin_blogs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_featured: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    sort_order: Optional[str] = Query("desc"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """List all blog posts with administrative filters, sorting, and pagination."""
    items, total = await blog_service.list_blog_posts(
        db,
        page=page,
        limit=limit,
        search=search,
        category=category,
        status=status,
        is_featured=is_featured,
        sort_by=sort_by,
        sort_order=sort_order,
        public_only=False,
    )
    pages = (total + limit - 1) // limit if total > 0 else 1
    return BlogPostListResponse(items=items, total=total, page=page, limit=limit, pages=pages)


@router.get("/categories", response_model=BlogCategoryListResponse)
async def get_admin_categories(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """List all distinct blog categories and their post counts."""
    categories = await blog_service.get_blog_categories(db, public_only=False)
    return BlogCategoryListResponse(categories=categories)


@router.get("/{blog_id}", response_model=BlogPostOut)
async def get_admin_blog_by_id(
    blog_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Retrieve a single blog post by ID for editing or previewing."""
    post = await blog_service.get_blog_post_by_id(db, blog_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")
    return post


@router.post("", response_model=BlogPostOut, status_code=status.HTTP_201_CREATED)
async def create_admin_blog(
    data: BlogPostCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Create a new blog post."""
    post = await blog_service.create_blog_post(db, data, created_by_id=admin.id)
    return post


@router.put("/{blog_id}", response_model=BlogPostOut)
async def update_admin_blog(
    blog_id: str,
    data: BlogPostUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Update an existing blog post."""
    post = await blog_service.update_blog_post(db, blog_id, data)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")
    return post


@router.delete("/{blog_id}", status_code=status.HTTP_200_OK)
async def delete_admin_blog(
    blog_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Delete a blog post."""
    success = await blog_service.delete_blog_post(db, blog_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")
    return {"message": "Blog post deleted successfully", "id": blog_id}


@router.post("/upload-image")
async def upload_blog_image(
    file: UploadFile = File(...),
    admin: User = Depends(require_super_admin),
):
    """Upload a cover image or author avatar for a blog post."""
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image type. Allowed: JPG, PNG, WEBP, GIF, SVG",
        )

    upload_dir = os.path.join(get_upload_dir(), "blog_images")
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "image.png")[1]
    filename = f"blog_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    url = f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/uploads/blog_images/{filename}"
    return {"url": url, "filename": filename}
