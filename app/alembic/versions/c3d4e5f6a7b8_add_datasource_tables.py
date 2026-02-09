"""add datasource tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-09 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create datasource and spider_datasource tables."""
    op.create_table(
        'crawlhub_datasources',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(255), nullable=False, comment='数据源名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='描述'),
        sa.Column('type', sa.VARCHAR(20), nullable=False, comment='数据库类型'),
        sa.Column('mode', sa.VARCHAR(20), nullable=True, comment='连接模式'),
        sa.Column('status', sa.VARCHAR(20), nullable=True, comment='状态'),
        sa.Column('host', sa.String(255), nullable=True, comment='主机地址'),
        sa.Column('port', sa.Integer(), nullable=True, comment='端口'),
        sa.Column('username', sa.String(255), nullable=True, comment='用户名'),
        sa.Column('password', sa.String(500), nullable=True, comment='密码'),
        sa.Column('database', sa.String(255), nullable=True, comment='数据库名'),
        sa.Column('connection_options', sa.JSON(), nullable=True, comment='连接选项'),
        sa.Column('container_id', sa.String(100), nullable=True, comment='容器ID'),
        sa.Column('container_name', sa.String(255), nullable=True, comment='容器名称'),
        sa.Column('docker_image', sa.String(255), nullable=True, comment='Docker镜像'),
        sa.Column('mapped_port', sa.Integer(), nullable=True, comment='宿主机映射端口'),
        sa.Column('volume_path', sa.String(500), nullable=True, comment='数据卷路径'),
        sa.Column('last_check_at', sa.DateTime(), nullable=True, comment='最后检查时间'),
        sa.Column('last_error', sa.Text(), nullable=True, comment='最后错误信息'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'crawlhub_spider_datasources',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('spider_id', UUID(as_uuid=False), nullable=False, comment='爬虫ID'),
        sa.Column('datasource_id', UUID(as_uuid=False), nullable=False, comment='数据源ID'),
        sa.Column('target_table', sa.String(255), nullable=False, comment='目标表名/集合名'),
        sa.Column('is_enabled', sa.Boolean(), nullable=True, comment='是否启用'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_crawlhub_spider_datasources_spider_id', 'crawlhub_spider_datasources', ['spider_id'])
    op.create_index('ix_crawlhub_spider_datasources_datasource_id', 'crawlhub_spider_datasources', ['datasource_id'])


def downgrade() -> None:
    """Drop datasource and spider_datasource tables."""
    op.drop_index('ix_crawlhub_spider_datasources_datasource_id', table_name='crawlhub_spider_datasources')
    op.drop_index('ix_crawlhub_spider_datasources_spider_id', table_name='crawlhub_spider_datasources')
    op.drop_table('crawlhub_spider_datasources')
    op.drop_table('crawlhub_datasources')
