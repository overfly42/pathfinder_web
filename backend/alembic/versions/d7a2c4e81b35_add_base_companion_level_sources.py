"""add base_companion_level_sources

Revision ID: d7a2c4e81b35
Revises: c3f1a7d29e04
Create Date: 2026-10-17 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7a2c4e81b35'
down_revision: Union[str, Sequence[str], None] = 'c3f1a7d29e04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'base_companion_level_sources',
        sa.Column('track', sa.String(length=32), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('class_ability_id', sa.UUID(), nullable=True),
        sa.Column('feat_id', sa.UUID(), nullable=True),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('root_class_id', sa.UUID(), nullable=True),
        sa.Column('offset', sa.Integer(), server_default='0', nullable=False),
        sa.Column('divisor', sa.Integer(), server_default='1', nullable=False),
        sa.Column('minimum', sa.Integer(), nullable=True),
        sa.Column('stack_group', sa.String(length=64), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            '(class_ability_id IS NULL) <> (feat_id IS NULL)', name='ck_companion_level_source_one_trigger'
        ),
        sa.CheckConstraint(
            "kind IN ('class_level', 'character_level', 'flat_bonus')", name='ck_companion_level_source_kind'
        ),
        sa.CheckConstraint("track IN ('animal_companion', 'familiar')", name='ck_companion_level_source_track'),
        sa.ForeignKeyConstraint(['class_ability_id'], ['base_class_abilities.id'], ),
        sa.ForeignKeyConstraint(['feat_id'], ['base_feats.id'], ),
        sa.ForeignKeyConstraint(['root_class_id'], ['base_classes.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('base_companion_level_sources')
