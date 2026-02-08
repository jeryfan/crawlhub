"""add spider webhook_url field

Revision ID: c1ddd10e13a4
Revises: b0a1707c2975
Create Date: 2026-02-08 12:35:05.258808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1ddd10e13a4'
down_revision: Union[str, Sequence[str], None] = 'b0a1707c2975'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('crawlhub_spiders', sa.Column('webhook_url', sa.String(length=500), nullable=True, comment='Webhook 回调 URL'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('crawlhub_spiders', 'webhook_url')
