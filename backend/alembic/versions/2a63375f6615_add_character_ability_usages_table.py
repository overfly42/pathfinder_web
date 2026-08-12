"""add character ability usages table

Revision ID: 2a63375f6615
Revises: d8a3283c7056
Create Date: 2026-08-12 21:50:33.096882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a63375f6615'
down_revision: Union[str, Sequence[str], None] = 'd8a3283c7056'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'character_ability_usages',
        sa.Column('character_id', sa.UUID(), nullable=False),
        sa.Column('source_type', sa.String(length=32), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('used_today', sa.Integer(), server_default='0', nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('character_id', 'source_type', 'source_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('character_ability_usages')
