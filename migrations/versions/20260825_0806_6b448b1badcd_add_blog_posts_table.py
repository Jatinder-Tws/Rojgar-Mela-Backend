"""add_blog_posts_table

Revision ID: 6b448b1badcd
Revises: c8d9e0f1a2b3
Create Date: 2026-08-25 08:06:24.926680

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6b448b1badcd'
down_revision: Union[str, None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT to_regclass('public.blog_posts')")).scalar()
    if exists:
        return

    op.create_table(
        'blog_posts',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('subtitle', sa.String(length=500), nullable=True),
        sa.Column('excerpt', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column('author_name', sa.String(length=150), nullable=False, server_default=sa.text("'Rojgar Mela Content Team'")),
        sa.Column('author_role', sa.String(length=150), nullable=True, server_default=sa.text("'Career Research & Editorial'")),
        sa.Column('author_avatar', sa.String(length=500), nullable=True),
        sa.Column('author_bio', sa.Text(), nullable=True),
        sa.Column('cover_image', sa.String(length=500), nullable=True),
        sa.Column('read_time', sa.String(length=50), nullable=False, server_default=sa.text("'6 min read'")),
        sa.Column('published_date', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'published'"), nullable=False),
        sa.Column('is_featured', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('views_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('likes_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('content_markdown', sa.Text(), nullable=True),
        sa.Column('sections', postgresql.JSON(astext_type=sa.Text()), server_default=sa.text("'[]'::json"), nullable=True),
        sa.Column('faqs', postgresql.JSON(astext_type=sa.Text()), server_default=sa.text("'[]'::json"), nullable=True),
        sa.Column('created_by_id', sa.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_blog_posts_category'), 'blog_posts', ['category'], unique=False)
    op.create_index(op.f('ix_blog_posts_slug'), 'blog_posts', ['slug'], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT to_regclass('public.blog_posts')")).scalar()
    if not exists:
        return

    op.drop_index(op.f('ix_blog_posts_slug'), table_name='blog_posts')
    op.drop_index(op.f('ix_blog_posts_category'), table_name='blog_posts')
    op.drop_table('blog_posts')
