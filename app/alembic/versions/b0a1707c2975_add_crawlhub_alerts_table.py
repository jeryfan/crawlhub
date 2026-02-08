"""add crawlhub alerts table

Revision ID: b0a1707c2975
Revises: dc670a8b41f7
Create Date: 2026-02-08 11:53:43.207065

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from models.crawlhub.alert import AlertLevel
import models

# revision identifiers, used by Alembic.
revision: str = 'b0a1707c2975'
down_revision: Union[str, Sequence[str], None] = 'dc670a8b41f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('crawlhub_alerts',
    sa.Column('type', sa.String(length=50), nullable=False, comment='告警类型'),
    sa.Column('level', models.types.EnumText(AlertLevel), nullable=False, comment='告警级别'),
    sa.Column('message', sa.Text(), nullable=False, comment='告警信息'),
    sa.Column('spider_id', models.types.StringUUID(), nullable=True, comment='关联爬虫'),
    sa.Column('task_id', models.types.StringUUID(), nullable=True, comment='关联任务'),
    sa.Column('is_read', sa.Boolean(), nullable=False, comment='是否已读'),
    sa.Column('id', models.types.StringUUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('crawlhub_alerts_pkey'))
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('crawlhub_alerts')
