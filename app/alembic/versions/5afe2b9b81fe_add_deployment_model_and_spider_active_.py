"""add deployment model and spider active_deployment_id

Revision ID: 5afe2b9b81fe
Revises: c1ddd10e13a4
Create Date: 2026-02-08 15:49:08.723806

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import models

# revision identifiers, used by Alembic.
revision: str = '5afe2b9b81fe'
down_revision: Union[str, Sequence[str], None] = 'c1ddd10e13a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('crawlhub_deployments',
    sa.Column('spider_id', models.types.StringUUID(), nullable=False, comment='爬虫ID'),
    sa.Column('version', sa.Integer(), nullable=False, comment='版本号'),
    sa.Column('status', sa.String(length=50), nullable=False, server_default='active', comment='部署状态'),
    sa.Column('file_archive_id', sa.String(length=255), nullable=False, comment='GridFS 文件ID'),
    sa.Column('entry_point', sa.String(length=255), nullable=True, comment='入口点'),
    sa.Column('file_count', sa.Integer(), nullable=False, server_default='0', comment='文件数量'),
    sa.Column('archive_size', sa.Integer(), nullable=False, server_default='0', comment='包大小(bytes)'),
    sa.Column('deploy_note', sa.Text(), nullable=True, comment='部署备注'),
    sa.Column('id', models.types.StringUUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('crawlhub_deployments_pkey'))
    )
    op.add_column('crawlhub_spiders', sa.Column('active_deployment_id', models.types.StringUUID(), nullable=True, comment='当前活跃部署ID'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('crawlhub_spiders', 'active_deployment_id')
    op.drop_table('crawlhub_deployments')
