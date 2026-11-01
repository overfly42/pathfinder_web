"""ability increases from levels

A level's ability increase (`character_levels.ability_increase`) used to be
added onto the character's base score column as well, so the same +1 was
stored twice. From now on the base columns hold the point-buy (or species)
scores only and `Character.ability_scores` adds the increases from the
levels. This subtracts every recorded increase from its base column once.

Revision ID: e4b7c1d9a2f6
Revises: d27cf6d4f592
Create Date: 2026-11-01 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e4b7c1d9a2f6'
down_revision: Union[str, Sequence[str], None] = 'd27cf6d4f592'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ABILITIES = ("ST", "GE", "KO", "IN", "WE", "CH")


def _shift(sign: str) -> None:
    assignments = ", ".join(
        f"ability_score_{ability.lower()} = ability_score_{ability.lower()} {sign} ("
        f"SELECT count(*) FROM character_levels l WHERE l.character_id = c.id AND l.ability_increase = '{ability}')"
        for ability in ABILITIES
    )
    op.execute(f"UPDATE characters c SET {assignments}")


def upgrade() -> None:
    _shift("-")


def downgrade() -> None:
    _shift("+")
