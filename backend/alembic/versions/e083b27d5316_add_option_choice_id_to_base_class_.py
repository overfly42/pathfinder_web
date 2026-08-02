"""add option_choice_id to base_class_skills

Revision ID: e083b27d5316
Revises: 821482a1c701
Create Date: 2026-08-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e083b27d5316'
down_revision: Union[str, Sequence[str], None] = '821482a1c701'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('base_class_skills_base_class_id_skill_id_key', 'base_class_skills', type_='unique')
    op.add_column('base_class_skills', sa.Column('option_choice_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_base_class_skills_option_choice_id',
        'base_class_skills',
        'base_class_option_choices',
        ['option_choice_id'],
        ['id'],
    )
    op.create_unique_constraint(
        'base_class_skills_base_class_id_skill_id_option_choice_id_key',
        'base_class_skills',
        ['base_class_id', 'skill_id', 'option_choice_id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'base_class_skills_base_class_id_skill_id_option_choice_id_key', 'base_class_skills', type_='unique'
    )
    op.drop_constraint('fk_base_class_skills_option_choice_id', 'base_class_skills', type_='foreignkey')
    op.drop_column('base_class_skills', 'option_choice_id')
    op.create_unique_constraint('base_class_skills_base_class_id_skill_id_key', 'base_class_skills', ['base_class_id', 'skill_id'])
