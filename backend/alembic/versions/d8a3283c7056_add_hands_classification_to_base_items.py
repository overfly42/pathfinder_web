"""add hands classification to base_items

Revision ID: d8a3283c7056
Revises: e06ba7badfba
Create Date: 2026-08-11 21:14:01.752448

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8a3283c7056'
down_revision: Union[str, Sequence[str], None] = 'e06ba7badfba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('base_items', sa.Column('hands', sa.String(length=8), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('base_items', 'hands')
