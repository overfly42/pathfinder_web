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

from collections.abc import Iterable
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


def spells_per_day(db: Session, base_class_id: UUID, level: int, grade: int) -> int | None:
    """The base (pre-ability-modifier) number of spell slots this class gets
    per day at this grade and level, straight from
    `base_class_spells_known.spells_per_day` — `None` if no row exists at
    all (this grade isn't accessible yet at this level, same gate
    `known_grades` reads off row presence) or if the row exists but the
    column hasn't been seeded for this class."""
    row = db.scalar(
        select(BaseClassSpellsKnown).where(
            BaseClassSpellsKnown.base_class_id == base_class_id,
            BaseClassSpellsKnown.level == level,
            BaseClassSpellsKnown.grade == grade,
        )
    )
    return row.spells_per_day if row is not None else None


def bonus_spells_from_mod(mod: int, grade: int) -> int:
    """"Attributsmodifikatoren und zusätzliche Zauber pro Tag" — the real
    table (transcribed 2026-08-24 against the authoritative source, which
    turned out to diverge from an earlier, incorrect from-memory version of
    this function: bonus spells start at `mod >= grade`, not `mod >= 2*grade
    - 1`, and the count itself climbs every 4 points of modifier past that,
    not staying fixed at 1 forever). Closed form, verified cell-for-cell
    against the source table through mod +17: `(mod - grade) // 4 + 1` once
    `mod >= grade >= 1`, else 0. Grade 0 (cantrips) never gets a bonus
    spell. Extrapolates cleanly past +17 (the source table's own listed
    range) since the underlying pattern is a flat arithmetic progression,
    not a hand-curated exception past that point."""
    if grade < 1 or mod < grade:
        return 0
    return (mod - grade) // 4 + 1


def folded_bonus_spells(ability_mod: int, above_grade: int) -> int:
    """Deliberate deviation from RAW (confirmed with the project owner,
    2026-08-24): a bonus spell `bonus_spells_from_mod` would grant for a
    grade the character can't actually access yet (too low level, or a
    class whose own table never reaches that high) doesn't vanish — it
    becomes an extra slot at the highest grade the character *can*
    currently access. Sums every grade above `above_grade` through grade 9
    (the real table's max); callers add this only to the one grade entry
    that *is* the character's current highest accessible grade, everywhere
    else is unaffected. `above_grade` is always the character's current
    max accessible grade (level-gated, not the class's theoretical max) —
    see `_build_prepared_spell_grades`/`prepare_spell`'s own
    `known_grades`-derived `max_accessible_grade`."""
    return sum(bonus_spells_from_mod(ability_mod, grade) for grade in range(above_grade + 1, 10))


def total_spell_slots(
    db: Session,
    base_class_id: UUID,
    level: int,
    grade: int,
    ability_mod: int,
    granted_ability_ids: Iterable[UUID] = (),
    fold_higher_grades_into_this_one: bool = False,
) -> int | None:
    """Real per-day castable slots at this grade: the class's base table
    value (adjusted by any granted ability with a `SPELL_SLOT_DELTA` entry,
    e.g. a Kampfmagus archetype's "Vermindertes Zauberwirken",
    `rules/classes/kampfmagus.py` — floored at 0, never negative) plus the
    character's ability-modifier bonus for this grade, which is untouched
    by that reduction. `None` if the base table has nothing for this
    (class, level, grade) at all (grade not accessible yet), distinct from
    a legitimate `0` (grade accessible, but e.g. a low-level caster who
    hasn't reached this grade's bonus-spell threshold, or a diminished-
    spellcasting archetype whose reduced base hits 0 — the caster can still
    cast a spell of that grade if the bonus alone is `> 0`).

    `fold_higher_grades_into_this_one=True` additionally adds
    `folded_bonus_spells(ability_mod, grade)` — pass this only for the
    single grade that is the character's current highest *accessible* one;
    see that function's docstring for the house rule this implements."""
    base = spells_per_day(db, base_class_id, level, grade)
    if base is None:
        return None
    from .handlers import SPELL_SLOT_DELTAS  # deferred: see daily_limits.py's own import for why

    delta = sum(SPELL_SLOT_DELTAS.get(ability_id, 0) for ability_id in granted_ability_ids)
    base = max(0, base + delta)
    bonus = bonus_spells_from_mod(ability_mod, grade)
    if fold_higher_grades_into_this_one:
        bonus += folded_bonus_spells(ability_mod, grade)
    return base + bonus
