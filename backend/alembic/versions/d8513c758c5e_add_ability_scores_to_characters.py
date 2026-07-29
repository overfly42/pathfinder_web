"""add ability scores to characters

Revision ID: d8513c758c5e
Revises: 718344001d2b
Create Date: 2026-07-29 10:25:04.709661

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8513c758c5e'
down_revision: Union[str, Sequence[str], None] = '718344001d2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('characters', sa.Column('ability_score_st', sa.Integer(), nullable=False))
    op.add_column('characters', sa.Column('ability_score_ge', sa.Integer(), nullable=False))
    op.add_column('characters', sa.Column('ability_score_ko', sa.Integer(), nullable=False))
    op.add_column('characters', sa.Column('ability_score_in', sa.Integer(), nullable=False))
    op.add_column('characters', sa.Column('ability_score_we', sa.Integer(), nullable=False))
    op.add_column('characters', sa.Column('ability_score_ch', sa.Integer(), nullable=False))
    op.add_column('characters', sa.Column('point_budget', sa.Integer(), nullable=False))
    op.add_column('characters', sa.Column('flex_ability', sa.String(length=2), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('characters', 'flex_ability')
    op.drop_column('characters', 'point_budget')
    op.drop_column('characters', 'ability_score_ch')
    op.drop_column('characters', 'ability_score_we')
    op.drop_column('characters', 'ability_score_in')
    op.drop_column('characters', 'ability_score_ko')
    op.drop_column('characters', 'ability_score_ge')
    op.drop_column('characters', 'ability_score_st')
