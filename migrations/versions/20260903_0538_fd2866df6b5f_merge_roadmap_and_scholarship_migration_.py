"""merge roadmap and scholarship migration heads

Revision ID: fd2866df6b5f
Revises: e4f5a6b7c8d9, e9f0a1b2c3d4
Create Date: 2026-09-03 05:38:24.756605

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision: str = 'fd2866df6b5f'
down_revision: Union[str, None] = ('e4f5a6b7c8d9', 'e9f0a1b2c3d4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
