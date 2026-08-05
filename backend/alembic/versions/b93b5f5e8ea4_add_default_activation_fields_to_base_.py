"""add default activation fields to base_conditions

Revision ID: b93b5f5e8ea4
Revises: b585b4104b22
Create Date: 2026-08-05 20:24:24.174141

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b93b5f5e8ea4'
down_revision: Union[str, Sequence[str], None] = 'b585b4104b22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('base_conditions', sa.Column('default_incubation_rounds', sa.Integer(), nullable=True))
    op.add_column('base_conditions', sa.Column('default_duration_rounds', sa.Integer(), nullable=True))
    op.add_column('base_conditions', sa.Column('default_frequency_rounds', sa.Integer(), nullable=True))
    op.add_column('base_conditions', sa.Column('default_successes_required', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('base_conditions', 'default_successes_required')
    op.drop_column('base_conditions', 'default_frequency_rounds')
    op.drop_column('base_conditions', 'default_duration_rounds')
    op.drop_column('base_conditions', 'default_incubation_rounds')
