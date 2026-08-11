"""add temporary hit points to characters

Revision ID: e06ba7badfba
Revises: aad95723a953
Create Date: 2026-08-11 21:13:45.372617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e06ba7badfba'
down_revision: Union[str, Sequence[str], None] = 'aad95723a953'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'characters', sa.Column('temporary_hit_points', sa.Integer(), nullable=False, server_default='0')
    )
    op.alter_column('characters', 'temporary_hit_points', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('characters', 'temporary_hit_points')
