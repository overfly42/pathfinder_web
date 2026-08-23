"""add skill specialization catalog

Revision ID: bd221c2daa16
Revises: 4f3a7dc5cbc9
Create Date: 2026-08-23 14:40:58.852748

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd221c2daa16'
down_revision: Union[str, Sequence[str], None] = '4f3a7dc5cbc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'base_skill_specializations',
        sa.Column('skill_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['skill_id'], ['base_skills.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('skill_id', 'name'),
    )
    op.add_column(
        'base_skills', sa.Column('has_specialization', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.alter_column('base_skills', 'has_specialization', server_default=None)
    op.add_column('character_skill_ranks', sa.Column('specialization_id', sa.UUID(), nullable=True))
    op.add_column('character_skill_ranks', sa.Column('custom_specialization', sa.String(length=255), nullable=True))
    op.drop_constraint('character_skill_ranks_level_id_skill_id_key', 'character_skill_ranks', type_='unique')
    op.create_unique_constraint(
        'character_skill_ranks_specialization_uq',
        'character_skill_ranks',
        ['level_id', 'skill_id', 'specialization_id', 'custom_specialization'],
    )
    op.create_foreign_key(
        'fk_character_skill_ranks_specialization_id',
        'character_skill_ranks',
        'base_skill_specializations',
        ['specialization_id'],
        ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_character_skill_ranks_specialization_id', 'character_skill_ranks', type_='foreignkey')
    op.drop_constraint(
        'character_skill_ranks_specialization_uq',
        'character_skill_ranks',
        type_='unique',
    )
    op.create_unique_constraint(
        'character_skill_ranks_level_id_skill_id_key', 'character_skill_ranks', ['level_id', 'skill_id']
    )
    op.drop_column('character_skill_ranks', 'custom_specialization')
    op.drop_column('character_skill_ranks', 'specialization_id')
    op.drop_column('base_skills', 'has_specialization')
    op.drop_table('base_skill_specializations')
