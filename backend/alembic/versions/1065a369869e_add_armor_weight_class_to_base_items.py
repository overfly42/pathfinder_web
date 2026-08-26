"""add armor weight class to base items

Revision ID: 1065a369869e
Revises: 88702dc539a2
Create Date: 2026-08-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1065a369869e'
down_revision: Union[str, Sequence[str], None] = '88702dc539a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('base_items', sa.Column('armor_weight_class', sa.String(length=8), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('base_items', 'armor_weight_class')
