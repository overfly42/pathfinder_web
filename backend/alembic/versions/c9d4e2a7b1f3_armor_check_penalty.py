"""armor check penalty on items

Revision ID: c9d4e2a7b1f3
Revises: b3e8c1d5f7a9
Create Date: 2026-10-17 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d4e2a7b1f3'
down_revision: Union[str, Sequence[str], None] = 'b3e8c1d5f7a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('base_items', sa.Column('armor_check_penalty', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('base_items', 'armor_check_penalty')
