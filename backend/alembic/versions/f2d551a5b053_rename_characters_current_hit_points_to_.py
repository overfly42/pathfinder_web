"""rename characters current_hit_points to damage_taken

Revision ID: f2d551a5b053
Revises: bc08779c752d
Create Date: 2026-08-04 15:48:17.744545

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2d551a5b053'
down_revision: Union[str, Sequence[str], None] = 'bc08779c752d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Real rename (not drop+add, which autogenerate proposed and would have
    silently discarded every row's HP state): every existing row's
    `current_hit_points` was set at creation to that character's own max HP
    (no `PATCH .../hp` endpoint exists yet to persist damage, see
    `Character.damage_taken`'s docstring) - i.e. every row already means
    "undamaged". Re-pointing the same storage at the new "damage taken"
    meaning is therefore just a value reset to 0, not a lossy conversion."""
    op.alter_column('characters', 'current_hit_points', new_column_name='damage_taken')
    op.execute('UPDATE characters SET damage_taken = 0 WHERE damage_taken IS NOT NULL')


def downgrade() -> None:
    """Inverse rename. Values aren't converted back to remaining-HP terms
    (that needs each row's computed max HP, not available in a migration) -
    same as upgrade, every row is reset, this time to NULL (the pre-existing
    "unknown, fall back to full health" state)."""
    op.execute('UPDATE characters SET damage_taken = NULL')
    op.alter_column('characters', 'damage_taken', new_column_name='current_hit_points')
