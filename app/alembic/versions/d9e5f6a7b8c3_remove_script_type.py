"""remove script_type and project_type columns

Revision ID: d9e5f6a7b8c3
Revises: c8f4d5e6a7b2
Create Date: 2026-02-03 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9e5f6a7b8c3'
down_revision: Union[str, None] = 'c8f4d5e6a7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop script_type and project_type columns from crawlhub_spiders table
    op.drop_column('crawlhub_spiders', 'script_type')
    op.drop_column('crawlhub_spiders', 'project_type')


def downgrade() -> None:
    # Re-add the columns if needed
    op.add_column('crawlhub_spiders', sa.Column('script_type', sa.Text(), nullable=True, server_default='httpx'))
    op.add_column('crawlhub_spiders', sa.Column('project_type', sa.Text(), nullable=True, server_default='single_file'))
