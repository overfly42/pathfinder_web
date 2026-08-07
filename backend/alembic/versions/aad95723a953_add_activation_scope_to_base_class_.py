"""add activation_scope to base_class_abilities

Revision ID: aad95723a953
Revises: f4549f885840
Create Date: 2026-08-07 16:59:34.015747

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aad95723a953'
down_revision: Union[str, Sequence[str], None] = 'f4549f885840'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'base_class_abilities',
        sa.Column('activation_scope', sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('base_class_abilities', 'activation_scope')
