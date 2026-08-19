"""add background skills support

Revision ID: 066674db6a18
Revises: 64e9cdd3cd66
Create Date: 2026-08-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '066674db6a18'
down_revision: Union[str, Sequence[str], None] = '64e9cdd3cd66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'base_skills', sa.Column('is_background', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.alter_column('base_skills', 'is_background', server_default=None)
    op.add_column(
        'characters', sa.Column('use_background_skills', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.alter_column('characters', 'use_background_skills', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('characters', 'use_background_skills')
    op.drop_column('base_skills', 'is_background')
