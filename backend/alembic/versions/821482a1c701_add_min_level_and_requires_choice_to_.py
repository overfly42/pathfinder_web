"""add min_level and requires_choice_id to class option/ability-pool tables

Revision ID: 821482a1c701
Revises: a92f912d53bf
Create Date: 2026-08-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '821482a1c701'
down_revision: Union[str, Sequence[str], None] = 'a92f912d53bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('base_class_option_choices', sa.Column('min_level', sa.Integer(), nullable=True))
    op.add_column('base_class_option_choices', sa.Column('requires_choice_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_base_class_option_choices_requires_choice_id',
        'base_class_option_choices',
        'base_class_option_choices',
        ['requires_choice_id'],
        ['id'],
    )
    op.add_column('base_class_ability_feat_options', sa.Column('min_level', sa.Integer(), nullable=True))
    op.add_column('base_class_ability_spell_options', sa.Column('min_level', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('base_class_ability_spell_options', 'min_level')
    op.drop_column('base_class_ability_feat_options', 'min_level')
    op.drop_constraint(
        'fk_base_class_option_choices_requires_choice_id', 'base_class_option_choices', type_='foreignkey'
    )
    op.drop_column('base_class_option_choices', 'requires_choice_id')
    op.drop_column('base_class_option_choices', 'min_level')
