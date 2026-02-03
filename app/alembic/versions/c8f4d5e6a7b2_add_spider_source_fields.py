"""add_spider_source_fields

Revision ID: c8f4d5e6a7b2
Revises: b7e3c4d5f6a1
Create Date: 2026-02-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c8f4d5e6a7b2'
down_revision: Union[str, Sequence[str], None] = 'b7e3c4d5f6a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source and git_repo fields to crawlhub_spiders."""
    op.add_column(
        'crawlhub_spiders',
        sa.Column('source', sa.String(length=50), nullable=False, server_default='empty', comment='项目来源')
    )
    op.add_column(
        'crawlhub_spiders',
        sa.Column('git_repo', sa.String(length=500), nullable=True, comment='Git 仓库地址')
    )


def downgrade() -> None:
    """Remove source and git_repo fields from crawlhub_spiders."""
    op.drop_column('crawlhub_spiders', 'git_repo')
    op.drop_column('crawlhub_spiders', 'source')
