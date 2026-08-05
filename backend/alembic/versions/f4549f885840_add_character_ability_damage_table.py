"""add character ability damage table

Revision ID: f4549f885840
Revises: b93b5f5e8ea4
Create Date: 2026-08-05 23:44:12.113833

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4549f885840'
down_revision: Union[str, Sequence[str], None] = 'b93b5f5e8ea4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'character_ability_damage',
        sa.Column('character_id', sa.UUID(), nullable=False),
        sa.Column('ability', sa.String(length=2), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('character_id', 'ability', 'kind'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('character_ability_damage')
