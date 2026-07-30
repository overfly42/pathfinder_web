"""How many spells a caster class knows/has in its spellbook at a given
class level — and, for the picker itself, which grades are even accessible
yet. Composition (which spells exist, at what grade, for which class) is
real data (`BaseSpell`/`BaseClassSpell`/`BaseClassSpellsKnown`); only the
budget arithmetic itself is code, per CLAUDE.md's composition-vs-computation
split. Mirrors the frontend's spell-picker calculations
(creationCalculations.ts) — keep both in sync.

Three distinct acquisition rules, per `roadmap.md`'s slice-3 spellbook entry:
- Spontaneous casters (Sorcerer/Bard/Oracle-style, `spellType: 'spontaneous'`)
  pick from a fixed, cumulative known-count table (`spontaneous_known_budget`)
  — a level-up only ever grants the *delta* versus the previous level, but at
  creation the cumulative count at the character's final level is the whole
  budget, since it already is a running total.
- Arcane-prepared (Wizard-style, `spellType: 'arcane-prepared'`) casters get
  every grade-0 spell for free (not counted against any budget) plus a
  separately-computed non-cantrip budget (`arcane_prepared_budget`): "2 +
  casting-ability-mod" grade-1 spells at 1st level, then +2 spells of any
  currently-accessible grade every level after. Their spellbook can also grow
  at any time in play via the add-to-spellbook action, uncapped (gold/downtime
  cost isn't tracked yet).
- Divine-prepared (Cleric/Druid/Ranger-style, `spellType: 'divine-prepared'`)
  casters have no known-spell list at all — they prepare from the full class
  spell list, so there is nothing for this module to compute for them.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BaseClassSpellsKnown


def known_grades(db: Session, base_class_id: UUID, level: int) -> set[int]:
    """Which spell grades are accessible at all at this class level — row
    *presence* in `base_class_spells_known` is the gate, regardless of
    casting style; a missing row means that grade isn't castable yet."""
    rows = db.scalars(
        select(BaseClassSpellsKnown.grade).where(
            BaseClassSpellsKnown.base_class_id == base_class_id, BaseClassSpellsKnown.level == level
        )
    ).all()
    return set(rows)


def spontaneous_known_budget(db: Session, base_class_id: UUID, level: int) -> dict[int, int]:
    """Cumulative known-spell cap per grade at this class level, straight
    from `base_class_spells_known.count` — already a running total, so this
    *is* the creation-time budget (not a delta; level-up deltas are the
    caller's concern, computed as this level's count minus the previous
    level's, once a real level-up endpoint exists)."""
    rows = db.scalars(
        select(BaseClassSpellsKnown).where(
            BaseClassSpellsKnown.base_class_id == base_class_id, BaseClassSpellsKnown.level == level
        )
    ).all()
    return {row.grade: row.count for row in rows if row.count is not None}


def arcane_prepared_budget(level: int, ability_mod: int) -> int:
    """Non-grade-0 spellbook picks available at creation: `2 + ability_mod`
    from reaching 1st level, plus 2 more for every level after that. Grade-0
    spells are handled separately (all of them, unconditionally) — never
    counted against this budget."""
    if level < 1:
        return 0
    return (2 + ability_mod) + 2 * (level - 1)
