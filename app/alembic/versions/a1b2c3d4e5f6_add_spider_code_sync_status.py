"""add spider code_sync_status

Revision ID: a1b2c3d4e5f6
Revises: 5afe2b9b81fe
Create Date: 2026-02-08 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '5afe2b9b81fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('crawlhub_spiders', sa.Column('code_sync_status', sa.String(length=20), nullable=True, comment='代码同步状态: syncing/synced/failed'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('crawlhub_spiders', 'code_sync_status')
