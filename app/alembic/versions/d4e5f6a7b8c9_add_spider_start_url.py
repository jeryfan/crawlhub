"""add spider start_url

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-09 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('crawlhub_spiders', sa.Column('start_url', sa.String(length=2000), nullable=True, comment='目标抓取URL'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('crawlhub_spiders', 'start_url')
