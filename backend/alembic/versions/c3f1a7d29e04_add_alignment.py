"""add characters.alignment and base_classes.allowed_alignments

Revision ID: c3f1a7d29e04
Revises: 4242a1e02036
Create Date: 2026-10-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f1a7d29e04'
down_revision: Union[str, Sequence[str], None] = '4242a1e02036'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('characters', sa.Column('alignment', sa.String(length=2), nullable=True))
    op.add_column('base_classes', sa.Column('allowed_alignments', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('base_classes', 'allowed_alignments')
    op.drop_column('characters', 'alignment')
