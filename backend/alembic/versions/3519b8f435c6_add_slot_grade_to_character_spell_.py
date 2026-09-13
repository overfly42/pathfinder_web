"""add slot_grade to character spell preparations

Revision ID: 3519b8f435c6
Revises: c3f1c0239344
Create Date: 2026-09-13 22:02:03.569444

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3519b8f435c6'
down_revision: Union[str, Sequence[str], None] = 'c3f1c0239344'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. `slot_grade` (roadmap "Zauber in einem höheren Slot
    vorbereiten" concept) is the grade of the slot pool a prepared copy
    draws from — usually the spell's own grade, but PF1e RAW lets a
    prepared caster use a higher-grade slot for a lower-grade spell.
    Backfilled from `base_class_spells` for existing rows (equal to the
    spell's own grade, since no row predates this feature), same
    `effective_spell_list_class_id`/`spell_list_source_id` two-pass
    resolution `sheet.py`'s `_build_prepared_spell_grades` already uses for
    the rare class whose spell *list* is drawn from another class
    (Mystiker -> Kleriker) but which also has its own extra granted-spell
    rows (Mystiker's Heimgesucht curse)."""
    op.add_column('character_spell_preparations', sa.Column('slot_grade', sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE character_spell_preparations csp
        SET slot_grade = bcs.grade
        FROM base_class_spells bcs, base_classes bc
        WHERE bc.id = csp.base_class_id
        AND bcs.base_class_id = COALESCE(bc.spell_list_source_id, bc.id)
        AND bcs.spell_id = csp.spell_id
        """
    )
    op.execute(
        """
        UPDATE character_spell_preparations csp
        SET slot_grade = bcs.grade
        FROM base_class_spells bcs
        WHERE csp.slot_grade IS NULL
        AND bcs.base_class_id = csp.base_class_id
        AND bcs.spell_id = csp.spell_id
        """
    )
    # Defensive backstop, not expected to fire: any row this two-pass lookup
    # still can't resolve (no matching `base_class_spells` row at all) keeps
    # its own spell's grade unknowable here, so treat it as grade 0 rather
    # than block the migration — matches `grade_by_spell_id.get(spell_id, 0)`'s
    # own fallback in `sheet.py`.
    op.execute("UPDATE character_spell_preparations SET slot_grade = 0 WHERE slot_grade IS NULL")

    op.alter_column('character_spell_preparations', 'slot_grade', nullable=False)
    op.drop_constraint(
        'character_spell_preparations_character_id_base_class_id_spe_key',
        'character_spell_preparations',
        type_='unique',
    )
    op.create_unique_constraint(
        'character_spell_preparations_character_id_base_class_id_spe_key',
        'character_spell_preparations',
        ['character_id', 'base_class_id', 'spell_id', 'slot_grade'],
    )


def downgrade() -> None:
    """Downgrade schema. Collapses back to one row per (character,
    base_class, spell) if a downgrade somehow runs while two rows exist for
    the same spell at different slot grades (only possible once the feature
    this column enables has actually been used) — keeps the row with the
    higher `prepared_count`, same "pick one, don't try to merge counts that
    represent different slot grades" tradeoff `f2d551a5b053`'s rename
    accepts for its own asymmetric downgrade."""
    op.execute(
        """
        DELETE FROM character_spell_preparations csp
        WHERE EXISTS (
            SELECT 1 FROM character_spell_preparations other
            WHERE other.character_id = csp.character_id
            AND other.base_class_id = csp.base_class_id
            AND other.spell_id = csp.spell_id
            AND (other.prepared_count, other.id) > (csp.prepared_count, csp.id)
        )
        """
    )
    op.drop_constraint(
        'character_spell_preparations_character_id_base_class_id_spe_key',
        'character_spell_preparations',
        type_='unique',
    )
    op.create_unique_constraint(
        'character_spell_preparations_character_id_base_class_id_spe_key',
        'character_spell_preparations',
        ['character_id', 'base_class_id', 'spell_id'],
    )
    op.drop_column('character_spell_preparations', 'slot_grade')
