import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.super_admin.models.blog_post import BlogPost
from app.modules.super_admin.schemas.blog_admin import BlogPostCreate, BlogPostUpdate


def slugify(text: str) -> str:
    """Generate a clean URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


async def ensure_unique_slug(db: AsyncSession, base_slug: str, exclude_id: Optional[str] = None) -> str:
    slug = base_slug or "blog-post"
    query = select(BlogPost).where(BlogPost.slug == slug)
    if exclude_id:
        query = query.where(BlogPost.id != exclude_id)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if not existing:
        return slug
    
    counter = 1
    while True:
        candidate = f"{slug}-{counter}"
        q = select(BlogPost).where(BlogPost.slug == candidate)
        if exclude_id:
            q = q.where(BlogPost.id != exclude_id)
        res = await db.execute(q)
        if not res.scalar_one_or_none():
            return candidate
        counter += 1


SORTABLE_COLUMNS = {
    "title": BlogPost.title,
    "category": BlogPost.category,
    "status": BlogPost.status,
    "author_name": BlogPost.author_name,
    "published_date": BlogPost.published_date,
    "created_at": BlogPost.created_at,
    "updated_at": BlogPost.updated_at,
    "views_count": BlogPost.views_count,
    "likes_count": BlogPost.likes_count,
    "is_featured": BlogPost.is_featured,
}


async def list_blog_posts(
    db: AsyncSession,
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    is_featured: Optional[bool] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    public_only: bool = False,
) -> Tuple[List[BlogPost], int]:
    query = select(BlogPost)

    if public_only:
        query = query.where(BlogPost.status == "published")
    elif status and status != "all":
        query = query.where(BlogPost.status == status)

    if category and category != "all":
        query = query.where(BlogPost.category == category)

    if is_featured is not None:
        query = query.where(BlogPost.is_featured == is_featured)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                BlogPost.title.ilike(term),
                BlogPost.excerpt.ilike(term),
                BlogPost.author_name.ilike(term),
                BlogPost.category.ilike(term),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one() or 0

    sort_column = SORTABLE_COLUMNS.get(sort_by or "created_at", BlogPost.created_at)
    order_fn = sort_column.asc() if sort_order == "asc" else sort_column.desc()

    offset = (page - 1) * limit
    query = query.order_by(order_fn).offset(offset).limit(limit)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def get_blog_post_by_id(db: AsyncSession, blog_id: str) -> Optional[BlogPost]:
    result = await db.execute(select(BlogPost).where(BlogPost.id == blog_id))
    return result.scalar_one_or_none()


async def get_blog_post_by_slug(db: AsyncSession, slug: str, increment_view: bool = True) -> Optional[BlogPost]:
    result = await db.execute(select(BlogPost).where(BlogPost.slug == slug))
    post = result.scalar_one_or_none()
    if post and increment_view:
        post.views_count = (post.views_count or 0) + 1
        await db.commit()
        await db.refresh(post)
    return post


async def create_blog_post(db: AsyncSession, data: BlogPostCreate, created_by_id: Optional[str] = None) -> BlogPost:
    raw_slug = data.slug or slugify(data.title)
    unique_slug = await ensure_unique_slug(db, raw_slug)

    published_date_str = data.published_date
    if not published_date_str:
        published_date_str = datetime.utcnow().strftime("%B %d, %Y")

    post = BlogPost(
        id=str(uuid.uuid4()),
        slug=unique_slug,
        title=data.title,
        subtitle=data.subtitle,
        excerpt=data.excerpt,
        category=data.category,
        tags=data.tags or [],
        author_name=data.author_name or "Rojgar Mela Content Team",
        author_role=data.author_role or "Career Research & Editorial",
        author_avatar=data.author_avatar,
        author_bio=data.author_bio,
        cover_image=data.cover_image,
        read_time=data.read_time or "6 min read",
        published_date=published_date_str,
        status=data.status or "published",
        is_featured=data.is_featured or False,
        content_markdown=data.content_markdown,
        sections=[s if isinstance(s, dict) else s.dict() for s in (data.sections or [])],
        faqs=[f if isinstance(f, dict) else f.dict() for f in (data.faqs or [])],
        created_by_id=created_by_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def update_blog_post(db: AsyncSession, blog_id: str, data: BlogPostUpdate) -> Optional[BlogPost]:
    post = await get_blog_post_by_id(db, blog_id)
    if not post:
        return None

    update_dict = data.dict(exclude_unset=True)

    if "slug" in update_dict and update_dict["slug"]:
        update_dict["slug"] = await ensure_unique_slug(db, slugify(update_dict["slug"]), exclude_id=blog_id)
    elif "title" in update_dict and update_dict["title"] and not post.slug:
        update_dict["slug"] = await ensure_unique_slug(db, slugify(update_dict["title"]), exclude_id=blog_id)

    if "sections" in update_dict and update_dict["sections"] is not None:
        update_dict["sections"] = [
            s if isinstance(s, dict) else s.dict() for s in update_dict["sections"]
        ]

    if "faqs" in update_dict and update_dict["faqs"] is not None:
        update_dict["faqs"] = [
            f if isinstance(f, dict) else f.dict() for f in update_dict["faqs"]
        ]

    for key, value in update_dict.items():
        setattr(post, key, value)

    post.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(post)
    return post


async def delete_blog_post(db: AsyncSession, blog_id: str) -> bool:
    post = await get_blog_post_by_id(db, blog_id)
    if not post:
        return False
    await db.delete(post)
    await db.commit()
    return True


async def get_blog_categories(db: AsyncSession, public_only: bool = False) -> List[Dict[str, Any]]:
    query = select(BlogPost.category, func.count(BlogPost.id).label("count"))
    if public_only:
        query = query.where(BlogPost.status == "published")
    query = query.group_by(BlogPost.category).order_by(func.count(BlogPost.id).desc())
    
    result = await db.execute(query)
    rows = result.all()

    categories = [
        {
            "id": row[0].lower().replace(" & ", "-").replace(" ", "-"),
            "name": row[0],
            "count": row[1],
        }
        for row in rows
        if row[0]
    ]
    return categories


async def react_to_blog_post(db: AsyncSession, slug: str, reaction_type: str = "helpful") -> Optional[BlogPost]:
    post = await get_blog_post_by_slug(db, slug, increment_view=False)
    if not post:
        return None
    post.likes_count = (post.likes_count or 0) + 1
    await db.commit()
    await db.refresh(post)
    return post
