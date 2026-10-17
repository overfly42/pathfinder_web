"""trait skill choice: list of abilities ("Personifizierte Weisheit")

Revision ID: b3e8c1d5f7a9
Revises: a77f0cf925b5
Create Date: 2026-10-17 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e8c1d5f7a9'
down_revision: Union[str, Sequence[str], None] = 'a77f0cf925b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: `skill_choice_ability` ("CH") becomes
    `skill_choice_abilities` (["CH"])."""
    op.add_column('base_traits', sa.Column('skill_choice_abilities', sa.JSON(), nullable=True))
    op.execute(
        "UPDATE base_traits SET skill_choice_abilities = json_build_array(skill_choice_ability) "
        "WHERE skill_choice_ability IS NOT NULL"
    )
    op.drop_column('base_traits', 'skill_choice_ability')


def downgrade() -> None:
    """Downgrade schema: keeps the first ability of each list."""
    op.add_column('base_traits', sa.Column('skill_choice_ability', sa.String(length=2), nullable=True))
    op.execute(
        "UPDATE base_traits SET skill_choice_ability = skill_choice_abilities ->> 0 "
        "WHERE skill_choice_abilities IS NOT NULL"
    )
    op.drop_column('base_traits', 'skill_choice_abilities')
