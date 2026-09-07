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

from ..models import BaseClassSpellsKnown, Character
from ..models.spell import BaseClassSpellGrant, CharacterSpell, CharacterSpellSlotUsage


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


# `BaseClassOptionChoice.name` values for the race-scoped favored-class-bonus
# variant that adds one extra known spell, grade at least 1 below the
# highest the class can currently cast — Mystiker's (Halb-Ork/Katzenvolk,
# now one shared `BaseClassAbility` row, "Zusätzlicher Mystikerzauber") and
# Hexe's (Ork/Elf, "Zusätzlicher Hexenvertraut-Zauber"; the Hexenvertraute
# is mechanically just this project's existing arcane-prepared spellbook,
# no separate familiar-spell-list concept needed). Keyed by root class name,
# not by choice id: `routers/characters.py` already threads every other
# favored-class-bonus check through the choice's plain name string
# (`submitted_favored_bonus`/`body.favored_class_bonus`), and a character's
# fixed race means at most one of a class's two names is ever relevant to
# them, so summing/checking against the whole set is safe. See
# `rules/favored_class_bonuses.py`'s module docstring for why this family
# has no `_fraction_bonus`-style handler there instead.
BONUS_KNOWN_SPELL_CHOICE_NAMES: dict[str, frozenset[str]] = {
    "Mystiker": frozenset({"Halb-Ork (Mystiker)", "Katzenvolk (Mystiker)"}),
    "Hexe": frozenset({"Ork (Hexe)", "Elf (Hexe)"}),
}


def bonus_known_spell_slot(class_name: str, favored_bonus_value: str | None) -> bool:
    """Whether one specific favored-class-bonus pick — this level's own
    value, not a career total — grants `class_name` one extra known-spell
    slot. Deliberately evaluated per pick rather than accumulated across a
    character's career and carried forward: the bonus is defined relative
    to "the highest grade you can currently cast", so this project requires
    it to be spent in the very same request that grants it (creation, or
    that one level-up) instead of banking an unused credit. That sidesteps
    needing a persisted "how much bonus is left" ledger — deriving it
    retroactively from `known_count - normal_budget` would silently
    undercount the moment a later level's normal budget grows past what it
    was when the bonus was actually spent (budgets are cumulative and only
    ever grow, so an unspent-that-level bonus can look "absorbed" by a
    bigger budget one level later even though the class-table budget alone
    never actually covered it)."""
    if favored_bonus_value is None:
        return False
    return favored_bonus_value in BONUS_KNOWN_SPELL_CHOICE_NAMES.get(class_name, frozenset())


def spontaneous_grade_overflow(
    picked_by_grade: dict[int, int],
    known_by_grade: dict[int, int],
    budget: dict[int, int],
    bonus_cap_grade: int,
    bonus_available: int,
) -> int | None:
    """First grade (if any) whose newly-picked spells don't fit the normal
    per-grade budget even after drawing on `bonus_available` — `None` if
    every grade's picks fit. The bonus is one shared pool across grades
    (not its own per-grade slot), consumed in `picked_by_grade` iteration
    order, and can only cover a grade at or below `bonus_cap_grade` (pass
    -1 when nothing is known yet, so no grade ever qualifies)."""
    remaining = bonus_available
    for grade, picked_count in picked_by_grade.items():
        normal_available = max(0, budget.get(grade, 0) - known_by_grade.get(grade, 0))
        overflow = picked_count - normal_available
        if overflow > 0:
            if grade > bonus_cap_grade or overflow > remaining:
                return grade
            remaining -= overflow
    return None


def arcane_prepared_overflows_budget(
    known_non_grade0: int,
    picked_grades: Iterable[int],
    budget: int,
    bonus_cap_grade: int,
    bonus_available: int,
) -> bool:
    """Whether the newly-picked non-grade0 spells (`picked_grades`) exceed
    `budget` even after applying up to `bonus_available` extra slots. The
    flat arcane-prepared budget has no per-grade split to begin with, so
    unlike `spontaneous_grade_overflow` this can't attribute *which*
    specific pick used the bonus — it only checks that *enough* of the
    picks (at least as many as the overflow) are individually at or below
    `bonus_cap_grade`, a count-based check that's sufficient since a known
    spell stays known regardless of which slot it nominally came from."""
    picked_grades = list(picked_grades)
    overflow = len(picked_grades) - max(0, budget - known_non_grade0)
    if overflow <= 0:
        return False
    if overflow > bonus_available:
        return True
    eligible = sum(1 for grade in picked_grades if grade <= bonus_cap_grade)
    return eligible < overflow


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


def granted_option_choice_spells(
    db: Session,
    base_class_id: UUID,
    max_level: int,
    choice_ids: Iterable[UUID],
    already_known: set[tuple[UUID, UUID]],
    min_level: int = 1,
) -> list[CharacterSpell]:
    """Fixed, no-choice bonus spells a class option choice grants
    automatically at a given class level (`BaseClassSpellGrant` — Hexe's
    Schutzherr, and Hexenmeister's Blutlinie once spontaneous casters get a
    spellbook to show it in, see `sheet.py`'s module docstring) — turned
    into ordinary `CharacterSpell` rows, since for an arcane-/divine-
    prepared caster that's simply an extra spellbook candidate, nothing
    else needs to know this spell came from a grant rather than a player
    pick.

    `max_level` is the character's level *in this root class*, matching
    `BaseClassSpellGrant.level`'s own semantics (class level, not overall
    character level — relevant for multiclassing). `min_level` narrows this
    to grants strictly above a level already covered (e.g. at level-up,
    pass `min_level=max_level` since every earlier level's grants were
    already handled at their own point in time); left at its default of 1
    for character creation, where every grant up to `max_level` is new.

    `already_known` is the caller's own `{(base_class_id, spell_id)}` scan
    over the character's existing `CharacterSpell` rows (same idempotency
    check `add_to_spellbook` already does, `routers/characters.py`) — a
    grant already present (e.g. from an earlier level-up, or already
    manually in the spellbook) is skipped rather than duplicated, since
    `CharacterSpell` carries no provenance column to distinguish the two."""
    choice_ids = list(choice_ids)
    if not choice_ids:
        return []
    rows = db.scalars(
        select(BaseClassSpellGrant).where(
            BaseClassSpellGrant.base_class_id == base_class_id,
            BaseClassSpellGrant.option_choice_id.in_(choice_ids),
            BaseClassSpellGrant.level >= min_level,
            BaseClassSpellGrant.level <= max_level,
        )
    ).all()
    return [
        CharacterSpell(base_class_id=base_class_id, spell_id=row.spell_id)
        for row in rows
        if (base_class_id, row.spell_id) not in already_known
    ]


def remaining_spontaneous_slots_by_grade(
    db: Session,
    character: Character,
    base_class_id: UUID,
    class_level: int,
    ability_mod: int,
    granted_ability_ids: Iterable[UUID] = (),
) -> dict[int, int]:
    """Real remaining per-day slots today, per grade 1-9, for a spontaneous
    caster (`spellType: 'spontaneous'`, e.g. Mystiker) — `total_spell_slots`
    (this class's own base table + ability-mod bonus + any archetype slot
    delta, same function prepared casters use) minus whatever
    `CharacterSpellSlotUsage.used_today` already tracks. A grade missing
    from the returned dict isn't accessible yet at this class level at all
    (mirrors `total_spell_slots`'s own `None` sentinel) — distinct from a
    grade present with `0` or negative remaining (accessible, just spent
    for today).

    Grade 0 (cantrips) is deliberately excluded: per PF1e RAW a prepared
    cantrip is never expended, so it's never slot-limited in the first
    place — see `sheet.py`'s spontaneous branch and `cast_spell`'s
    `is_cantrip` short-circuit, both of which skip this pool entirely for
    grade 0."""
    accessible_grades = known_grades(db, base_class_id, class_level)
    # Same "a bonus spell for a still-locked grade folds down into the
    # highest currently accessible grade" house rule prepared casters use
    # (`total_spell_slots`'s own `fold_higher_grades_into_this_one` doc) —
    # must match exactly, or a spontaneous caster's displayed/enforced slot
    # count would diverge from a prepared caster's for no reason.
    max_accessible_grade = max((g for g in accessible_grades if g >= 1), default=None)
    used_by_grade = {
        row.grade: row.used_today
        for row in db.scalars(
            select(CharacterSpellSlotUsage).where(
                CharacterSpellSlotUsage.character_id == character.id,
                CharacterSpellSlotUsage.base_class_id == base_class_id,
            )
        ).all()
    }
    remaining: dict[int, int] = {}
    for grade in range(1, 10):
        slots = total_spell_slots(
            db,
            base_class_id,
            class_level,
            grade,
            ability_mod,
            granted_ability_ids,
            fold_higher_grades_into_this_one=(grade == max_accessible_grade),
        )
        if slots is not None:
            remaining[grade] = slots - used_by_grade.get(grade, 0)
    return remaining


def find_open_spontaneous_grade(remaining_by_grade: dict[int, int], min_grade: int) -> int | None:
    """First grade from `min_grade` through 9 that still has a free slot
    today, per PF1e's universal "a higher slot can cast a lower-grade
    spell" rule — `None` if every grade from `min_grade` up is either
    exhausted or not accessible yet. Callers never pass `min_grade=0`
    (cantrips bypass this pool entirely, see `remaining_spontaneous_slots_by_grade`'s
    docstring) but the clamp is harmless either way."""
    return next((grade for grade in range(max(min_grade, 1), 10) if remaining_by_grade.get(grade, 0) > 0), None)


def consume_spontaneous_slot(db: Session, character: Character, base_class_id: UUID, grade: int) -> None:
    """Spends one of today's slots at `grade` for a spontaneous caster —
    the `cast_spell` counterpart to `prepare_spell`'s
    `CharacterSpellPreparation` increment, but keyed on `(character,
    base_class, grade)` rather than a specific spell, since any known
    spell can spend any slot of its own grade (`find_open_spontaneous_grade`
    picks which grade to charge before this is called). Get-or-create, same
    lazy-default convention as every other daily-usage row in this app."""
    row = db.scalar(
        select(CharacterSpellSlotUsage).where(
            CharacterSpellSlotUsage.character_id == character.id,
            CharacterSpellSlotUsage.base_class_id == base_class_id,
            CharacterSpellSlotUsage.grade == grade,
        )
    )
    if row is None:
        row = CharacterSpellSlotUsage(character_id=character.id, base_class_id=base_class_id, grade=grade, used_today=0)
        db.add(row)
    row.used_today += 1
