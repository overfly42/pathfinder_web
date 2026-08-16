"""add race_id to base_class_option_choices

Revision ID: e9be63c0c090
Revises: 2a63375f6615
Create Date: 2026-08-16 17:42:49.939185

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9be63c0c090'
down_revision: Union[str, Sequence[str], None] = '2a63375f6615'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('base_class_option_choices', sa.Column('race_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_base_class_option_choices_race_id',
        'base_class_option_choices',
        'base_races',
        ['race_id'],
        ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_base_class_option_choices_race_id', 'base_class_option_choices', type_='foreignkey')
    op.drop_column('base_class_option_choices', 'race_id')
