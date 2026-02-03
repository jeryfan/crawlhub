"""migrate_to_coder

Revision ID: b7e3c4d5f6a1
Revises: af6506912ce5
Create Date: 2026-02-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7e3c4d5f6a1'
down_revision: Union[str, Sequence[str], None] = 'af6506912ce5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add Coder workspace fields to crawlhub_spiders
    op.add_column('crawlhub_spiders', sa.Column('coder_workspace_id', sa.String(length=100), nullable=True, comment='Coder 工作区 ID'))
    op.add_column('crawlhub_spiders', sa.Column('coder_workspace_name', sa.String(length=255), nullable=True, comment='Coder 工作区名称'))

    # Drop crawlhub_spider_files table (file management now handled by Coder)
    op.drop_table('crawlhub_spider_files')

    # Drop crawlhub_code_sessions table if it exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if 'crawlhub_code_sessions' in inspector.get_table_names():
        op.drop_table('crawlhub_code_sessions')


def downgrade() -> None:
    """Downgrade schema."""
    import models

    # Recreate crawlhub_spider_files table
    op.create_table('crawlhub_spider_files',
        sa.Column('spider_id', models.types.StringUUID(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False, comment='文件相对路径'),
        sa.Column('storage_key', sa.String(length=500), nullable=False, comment='存储Key'),
        sa.Column('file_size', sa.Integer(), nullable=False, comment='文件大小(字节)'),
        sa.Column('content_type', sa.String(length=100), nullable=False, comment='MIME类型'),
        sa.Column('id', models.types.StringUUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('crawlhub_spider_files_pkey'))
    )

    # Remove Coder workspace fields from crawlhub_spiders
    op.drop_column('crawlhub_spiders', 'coder_workspace_name')
    op.drop_column('crawlhub_spiders', 'coder_workspace_id')
