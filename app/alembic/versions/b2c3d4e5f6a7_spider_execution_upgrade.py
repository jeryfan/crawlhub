"""spider execution engine upgrade

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add execution engine fields to spiders and tasks tables."""
    # Spider 表新增 10 个字段
    op.add_column('crawlhub_spiders', sa.Column('timeout_seconds', sa.Integer(), nullable=True, server_default='300'))
    op.add_column('crawlhub_spiders', sa.Column('max_items', sa.Integer(), nullable=True))
    op.add_column('crawlhub_spiders', sa.Column('memory_limit_mb', sa.Integer(), nullable=True))
    op.add_column('crawlhub_spiders', sa.Column('requirements_txt', sa.Text(), nullable=True))
    op.add_column('crawlhub_spiders', sa.Column('env_vars', sa.Text(), nullable=True))
    op.add_column('crawlhub_spiders', sa.Column('proxy_enabled', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('crawlhub_spiders', sa.Column('rate_limit_rps', sa.Float(), nullable=True))
    op.add_column('crawlhub_spiders', sa.Column('autothrottle_enabled', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('crawlhub_spiders', sa.Column('dedup_enabled', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('crawlhub_spiders', sa.Column('dedup_fields', sa.String(500), nullable=True))

    # Task 表新增 5 个字段
    op.add_column('crawlhub_tasks', sa.Column('error_category', sa.String(20), nullable=True))
    op.add_column('crawlhub_tasks', sa.Column('last_heartbeat', sa.DateTime(), nullable=True))
    op.add_column('crawlhub_tasks', sa.Column('checkpoint_data', sa.Text(), nullable=True))
    op.add_column('crawlhub_tasks', sa.Column('items_per_second', sa.Float(), nullable=True))
    op.add_column('crawlhub_tasks', sa.Column('peak_memory_mb', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove execution engine fields."""
    # Task 表
    op.drop_column('crawlhub_tasks', 'peak_memory_mb')
    op.drop_column('crawlhub_tasks', 'items_per_second')
    op.drop_column('crawlhub_tasks', 'checkpoint_data')
    op.drop_column('crawlhub_tasks', 'last_heartbeat')
    op.drop_column('crawlhub_tasks', 'error_category')

    # Spider 表
    op.drop_column('crawlhub_spiders', 'dedup_fields')
    op.drop_column('crawlhub_spiders', 'dedup_enabled')
    op.drop_column('crawlhub_spiders', 'autothrottle_enabled')
    op.drop_column('crawlhub_spiders', 'rate_limit_rps')
    op.drop_column('crawlhub_spiders', 'proxy_enabled')
    op.drop_column('crawlhub_spiders', 'env_vars')
    op.drop_column('crawlhub_spiders', 'requirements_txt')
    op.drop_column('crawlhub_spiders', 'memory_limit_mb')
    op.drop_column('crawlhub_spiders', 'max_items')
    op.drop_column('crawlhub_spiders', 'timeout_seconds')
