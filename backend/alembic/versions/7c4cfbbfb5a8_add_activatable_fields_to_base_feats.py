"""add activatable fields to base_feats

Revision ID: 7c4cfbbfb5a8
Revises: e9be63c0c090
Create Date: 2026-08-16 23:34:05.741232

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c4cfbbfb5a8'
down_revision: Union[str, Sequence[str], None] = 'e9be63c0c090'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'base_feats', sa.Column('is_persistent_effect', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.alter_column('base_feats', 'is_persistent_effect', server_default=None)
    op.add_column('base_feats', sa.Column('default_duration_rounds', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('base_feats', 'default_duration_rounds')
    op.drop_column('base_feats', 'is_persistent_effect')
