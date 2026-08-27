from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.super_admin.schemas.blog_admin import (
    BlogCategoryListResponse,
    BlogPostListResponse,
    BlogPostOut,
)
from app.modules.super_admin.services import blog_service

router = APIRouter(prefix="/api/blogs", tags=["Public Blogs"])


@router.get("", response_model=BlogPostListResponse)
async def list_public_blogs(
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_featured: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve published career blogs for the public portal."""
    items, total = await blog_service.list_blog_posts(
        db,
        page=page,
        limit=limit,
        search=search,
        category=category,
        is_featured=is_featured,
        public_only=True,
    )
    pages = (total + limit - 1) // limit if total > 0 else 1
    return BlogPostListResponse(items=items, total=total, page=page, limit=limit, pages=pages)


@router.get("/categories", response_model=BlogCategoryListResponse)
async def get_public_blog_categories(
    db: AsyncSession = Depends(get_db),
):
    """List active blog categories with their article counts."""
    categories = await blog_service.get_blog_categories(db, public_only=True)
    return BlogCategoryListResponse(categories=categories)


@router.get("/{slug}", response_model=BlogPostOut)
async def get_public_blog_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single published blog by slug and increment view counter."""
    post = await blog_service.get_blog_post_by_slug(db, slug, increment_view=True)
    if not post or post.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")
    return post


@router.post("/{slug}/react", response_model=BlogPostOut)
async def react_to_blog(
    slug: str,
    reaction_type: str = Query("helpful"),
    db: AsyncSession = Depends(get_db),
):
    """Record an interactive reaction to a blog post."""
    post = await blog_service.react_to_blog_post(db, slug, reaction_type=reaction_type)
    if not post or post.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")
    return post
