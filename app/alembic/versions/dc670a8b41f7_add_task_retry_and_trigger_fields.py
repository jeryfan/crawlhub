"""add task retry and trigger fields

Revision ID: dc670a8b41f7
Revises: d9e5f6a7b8c3
Create Date: 2026-02-08 11:39:29.163146

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'dc670a8b41f7'
down_revision: Union[str, Sequence[str], None] = 'd9e5f6a7b8c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('crawlhub_tasks', sa.Column('trigger_type', sa.String(length=20), nullable=False, server_default='manual', comment='触发类型: manual/schedule'))
    op.add_column('crawlhub_tasks', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0', comment='已重试次数'))
    op.add_column('crawlhub_tasks', sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3', comment='最大重试次数'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('crawlhub_tasks', 'max_retries')
    op.drop_column('crawlhub_tasks', 'retry_count')
    op.drop_column('crawlhub_tasks', 'trigger_type')
