"""add notification channels, alert rules, and spider item_schema

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-09 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import models


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. 通知渠道表
    op.create_table(
        'crawlhub_notification_channels',
        sa.Column('id', models.types.StringUUID(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, comment='渠道名称'),
        sa.Column('channel_type', sa.String(20), nullable=False, comment='渠道类型'),
        sa.Column('config', sa.Text(), nullable=False, comment='渠道配置 JSON'),
        sa.Column('is_enabled', sa.Boolean(), nullable=True, comment='是否启用'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id', name=op.f('crawlhub_notification_channels_pkey')),
    )

    # 2. 告警规则表
    op.create_table(
        'crawlhub_alert_rules',
        sa.Column('id', models.types.StringUUID(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False, comment='规则名称'),
        sa.Column('rule_type', sa.String(30), nullable=False, comment='规则类型'),
        sa.Column('condition', sa.Text(), nullable=False, comment='规则条件 JSON'),
        sa.Column('notification_channel_id', models.types.StringUUID(), nullable=True, comment='通知渠道ID'),
        sa.Column('spider_id', models.types.StringUUID(), nullable=True, comment='关联爬虫ID'),
        sa.Column('is_enabled', sa.Boolean(), nullable=True, comment='是否启用'),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=True, comment='冷却时间（分钟）'),
        sa.Column('last_triggered_at', sa.DateTime(), nullable=True, comment='上次触发时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id', name=op.f('crawlhub_alert_rules_pkey')),
    )

    # 3. Spider 表新增 item_schema 字段
    op.add_column(
        'crawlhub_spiders',
        sa.Column('item_schema', sa.Text(), nullable=True, comment='数据 Schema (JSON Schema 格式)'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('crawlhub_spiders', 'item_schema')
    op.drop_table('crawlhub_alert_rules')
    op.drop_table('crawlhub_notification_channels')
