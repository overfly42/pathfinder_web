"""Fills in `base_class_spells_known.spells_per_day` (roadmap slice 6 —
real daily spell-slot counts, `rules/spells.py`'s `spells_per_day`/
`total_spell_slots`) for the 6 originally-seeded arcane-/divine-prepared
classes, plus (2026-09-05) the 3 spontaneous classes (Barde/Hexenmeister/
Mystiker) once they gained a per-grade slot pool of their own
(`CharacterSpellSlotUsage`, `rules/spells.py`'s
`remaining_spontaneous_slots_by_grade`) — all transcribed from each class's
own "Zauber pro Tag" table on prd.5footstep.de (fetched directly, not from
memory — see the URLs in each table constant below).

Magier/Hexe/Kampfmagus already have grade-gate rows (`count=None`,
`spells_per_day=None`) from `build_arcane_prepared_spells_known_seed.py`
(arcane-prepared) and their own class-import scripts (Kampfmagus) — this
script only adds `spells_per_day` onto those existing rows.

Kleriker/Druide/Waldläufer (divine-prepared) had **zero** rows in
`base_class_spells_known.json` before this script: `sheet.py`'s spell
builder never looked at divine-prepared classes at all until the prepared-
spellcasting feature this seeds, so nobody needed their grade-gate rows
either. This script creates them from scratch (same `GRADE_UNLOCK_LEVEL`-row
shape as the arcane-prepared script) *and* fills `spells_per_day` in the
same pass.

Barde/Hexenmeister/Mystiker already had grade-gate rows too (`count`
populated — the spontaneous known-spell-count table, `spontaneous_known_budget`
— `spells_per_day=None`) from each class's own import script
(`import_barde.py`/`import_mystiker.py`, Hexenmeister seeded alongside its
Blutlinie work) — same "only add `spells_per_day` onto existing rows"
treatment as Magier/Hexe/Kampfmagus, **not** the "create from scratch"
treatment Kleriker/Druide/Waldläufer needed. One real difference from every class above: grade 0 (cantrips) never
appears in Barde's/Hexenmeister's/Mystiker's own "Zauber pro Tag" table at
all — unlike Magier/Kleriker/Druide, whose table gives cantrips a real
per-day number, PF1e RAW makes a spontaneous caster's cantrips flatly
unlimited per day. This script therefore never writes `spells_per_day` for
grade 0 on these three classes, leaving it `None` — `sheet.py`'s
spontaneous branch and `cast_spell` both already special-case grade 0 as
categorically free without ever consulting this column, so a `None` here
is simply never read for them, not a gap.

Table sources (verified 2026-08-23 against the live pages for the original
6 classes, 2026-09-05 for the 3 spontaneous ones — all fetched over plain
http://, not https://: the domain returns a hosting-provider placeholder
page for https requests, not the real site, so an https fetch silently
returns garbage rather than a real error):
- Magier: http://prd.5footstep.de/Grundregelwerk/Klassen/Magier
- Kleriker/Druide: same numeric progression as Magier (PF1e's three "full"
  9-grade casters share one spells-per-day table; only grade-unlock timing
  and bonus spells for domain/etc. differ) — cross-checked against Kleriker's
  and Druide's own pages, which republish the identical numbers (their pages
  render the table with WackoWiki rowspans that make bulk-parsing them
  directly unreliable; the values line up cell-for-cell where checked).
- Hexe: `build_arcane_prepared_spells_known_seed.py` already established
  Hexe shares Magier's full 9-grade table for grade-unlock levels; same
  precedent extended to spells_per_day here (Witch is explicitly a "high"
  9-grade caster in PF1e, same progression as Wizard).
- Kampfmagus: http://prd.5footstep.de/AusbauregelnMagie/Kampfmagus ("Tabelle: Kampfmagus")
- Waldläufer: http://prd.5footstep.de/Grundregelwerk/Klassen/Waldlaeufer
- Hexenmeister: http://prd.5footstep.de/Grundregelwerk/Klassen/Hexenmeister
  ("Tabelle: Hexenmeister") — a full 9-grade caster, but *not* Magier's
  progression: each grade unlocks one class level later (grade 2 at level
  4, not 3; grade 9 at level 18, not 17) and grade 1 itself starts at 3
  spells/day, not 1 — transcribed as its own `SPONTANEOUS_9_GRADE_UNLOCK`/
  `SPONTANEOUS_9_GRADE_SPELLS_PER_DAY` rather than reusing
  `FULL_9_GRADE_UNLOCK`/`FULL_9_GRADE_SPELLS_PER_DAY`.
- Mystiker: http://prd.5footstep.de/Expertenregeln/Klassen/Basisklassen/Mystiker
  ("Tabelle: Mystiker (MYS)") — numbers transcribed cell-for-cell identical
  to Hexenmeister's own table (PF1e RAW: Sorcerer and Oracle share one
  spells-per-day progression, same way Wizard/Cleric/Druid share theirs) —
  confirmed against the live page rather than assumed from that precedent,
  reuses the same `SPONTANEOUS_9_GRADE_*` constants.
- Barde: http://prd.5footstep.de/Grundregelwerk/Klassen/Barde ("Tabelle: Barde")
  — a 6-grade caster (no 7th-9th grade spells exist for Bard at all), own
  `BARD_GRADE_UNLOCK`/`BARD_SPELLS_PER_DAY` constants.

Usage (from backend/scripts, project venv active):
    python build_spells_per_day_seed.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
NAMESPACE = uuid.UUID("2b6e4a1d-8f3c-4b7a-9d5e-6c1f8a2b3d4e")  # same namespace as the arcane-prepared script
MAX_LEVEL = 20

# grade -> first class level it's accessible at.
FULL_9_GRADE_UNLOCK = {0: 1, 1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11, 7: 13, 8: 15, 9: 17}
KAMPFMAGUS_GRADE_UNLOCK = {0: 1, 1: 1, 2: 4, 3: 7, 4: 10, 5: 13, 6: 16}
RANGER_4_GRADE_UNLOCK = {1: 4, 2: 7, 3: 10, 4: 13}

# level -> [spells/day for grade 0..N], "-" cells kept as 0 for grades not
# yet unlocked at that level (never written, since a row only exists once
# `GRADE_UNLOCK_LEVEL` says the grade is open — see the loop below).
FULL_9_GRADE_SPELLS_PER_DAY: dict[int, list[int]] = {
    1: [3, 1, 0, 0, 0, 0, 0, 0, 0, 0],
    2: [4, 2, 0, 0, 0, 0, 0, 0, 0, 0],
    3: [4, 2, 1, 0, 0, 0, 0, 0, 0, 0],
    4: [4, 3, 2, 0, 0, 0, 0, 0, 0, 0],
    5: [4, 3, 2, 1, 0, 0, 0, 0, 0, 0],
    6: [4, 3, 3, 2, 0, 0, 0, 0, 0, 0],
    7: [4, 4, 3, 2, 1, 0, 0, 0, 0, 0],
    8: [4, 4, 3, 3, 2, 0, 0, 0, 0, 0],
    9: [4, 4, 4, 3, 2, 1, 0, 0, 0, 0],
    10: [4, 4, 4, 3, 3, 2, 0, 0, 0, 0],
    11: [4, 4, 4, 4, 3, 2, 1, 0, 0, 0],
    12: [4, 4, 4, 4, 3, 3, 2, 0, 0, 0],
    13: [4, 4, 4, 4, 4, 3, 2, 1, 0, 0],
    14: [4, 4, 4, 4, 4, 3, 3, 2, 0, 0],
    15: [4, 4, 4, 4, 4, 4, 3, 2, 1, 0],
    16: [4, 4, 4, 4, 4, 4, 3, 3, 2, 0],
    17: [4, 4, 4, 4, 4, 4, 4, 3, 2, 1],
    18: [4, 4, 4, 4, 4, 4, 4, 3, 3, 2],
    19: [4, 4, 4, 4, 4, 4, 4, 4, 3, 3],
    20: [4, 4, 4, 4, 4, 4, 4, 4, 4, 4],
}

KAMPFMAGUS_SPELLS_PER_DAY: dict[int, list[int]] = {
    1: [3, 1, 0, 0, 0, 0, 0],
    2: [4, 2, 0, 0, 0, 0, 0],
    3: [4, 3, 0, 0, 0, 0, 0],
    4: [4, 3, 1, 0, 0, 0, 0],
    5: [4, 4, 2, 0, 0, 0, 0],
    6: [5, 4, 3, 0, 0, 0, 0],
    7: [5, 4, 3, 1, 0, 0, 0],
    8: [5, 4, 4, 2, 0, 0, 0],
    9: [5, 5, 4, 3, 0, 0, 0],
    10: [5, 5, 4, 3, 1, 0, 0],
    11: [5, 5, 4, 4, 2, 0, 0],
    12: [5, 5, 5, 4, 3, 0, 0],
    13: [5, 5, 5, 4, 3, 1, 0],
    14: [5, 5, 5, 4, 4, 2, 0],
    15: [5, 5, 5, 5, 4, 3, 0],
    16: [5, 5, 5, 5, 4, 3, 1],
    17: [5, 5, 5, 5, 4, 4, 2],
    18: [5, 5, 5, 5, 5, 4, 3],
    19: [5, 5, 5, 5, 5, 5, 4],
    20: [5, 5, 5, 5, 5, 5, 5],
}

# grade 1..4 only (Ranger has no cantrips) — index 0 of each list is grade 1.
RANGER_SPELLS_PER_DAY: dict[int, list[int]] = {
    4: [0, 0, 0, 0],
    5: [1, 0, 0, 0],
    6: [1, 0, 0, 0],
    7: [1, 0, 0, 0],
    8: [1, 1, 0, 0],
    9: [2, 1, 0, 0],
    10: [2, 1, 0, 0],
    11: [2, 1, 1, 0],
    12: [2, 2, 1, 0],
    13: [3, 2, 1, 0],
    14: [3, 2, 1, 1],
    15: [3, 2, 2, 1],
    16: [3, 3, 2, 1],
    17: [4, 3, 2, 1],
    18: [4, 3, 2, 2],
    19: [4, 3, 3, 2],
    20: [4, 4, 3, 3],
}

# grade -> first class level it's accessible at. One level later per grade
# than `FULL_9_GRADE_UNLOCK` (grade 2 at level 4, not 3; ... grade 9 at
# level 18, not 17) — Hexenmeister's/Mystiker's own "Zauber pro Tag" table,
# not Magier's/Kleriker's. Grade 0's `0: 1` entry only keeps `emit()` below
# touching (and thus preserving) the pre-existing grade-0 rows' `count` —
# see `_spontaneous_9_grade_value`'s own `None` short-circuit for why no
# real `spells_per_day` number is ever attached to it.
SPONTANEOUS_9_GRADE_UNLOCK = {0: 1, 1: 1, 2: 4, 3: 6, 4: 8, 5: 10, 6: 12, 7: 14, 8: 16, 9: 18}

# grade 1..9 only — cantrips are unconditionally unlimited per day for
# these classes (see this module's own docstring), never a row here or a
# `spells_per_day` value on grade 0. Index 0 of each list is grade 1.
# Cell-for-cell identical between Hexenmeister and Mystiker on the live
# site (PF1e RAW: Sorcerer and Oracle share one spells-per-day table).
SPONTANEOUS_9_GRADE_SPELLS_PER_DAY: dict[int, list[int]] = {
    1: [3, 0, 0, 0, 0, 0, 0, 0, 0],
    2: [4, 0, 0, 0, 0, 0, 0, 0, 0],
    3: [5, 0, 0, 0, 0, 0, 0, 0, 0],
    4: [6, 3, 0, 0, 0, 0, 0, 0, 0],
    5: [6, 4, 0, 0, 0, 0, 0, 0, 0],
    6: [6, 5, 3, 0, 0, 0, 0, 0, 0],
    7: [6, 6, 4, 0, 0, 0, 0, 0, 0],
    8: [6, 6, 5, 3, 0, 0, 0, 0, 0],
    9: [6, 6, 6, 4, 0, 0, 0, 0, 0],
    10: [6, 6, 6, 5, 3, 0, 0, 0, 0],
    11: [6, 6, 6, 6, 4, 0, 0, 0, 0],
    12: [6, 6, 6, 6, 5, 3, 0, 0, 0],
    13: [6, 6, 6, 6, 6, 4, 0, 0, 0],
    14: [6, 6, 6, 6, 6, 5, 3, 0, 0],
    15: [6, 6, 6, 6, 6, 6, 4, 0, 0],
    16: [6, 6, 6, 6, 6, 6, 5, 3, 0],
    17: [6, 6, 6, 6, 6, 6, 6, 4, 0],
    18: [6, 6, 6, 6, 6, 6, 6, 5, 3],
    19: [6, 6, 6, 6, 6, 6, 6, 6, 4],
    20: [6, 6, 6, 6, 6, 6, 6, 6, 6],
}

# Bard's own progression: a 6-grade caster (grades 7-9 don't exist for this
# class at all), unlock levels one class level apart from level 4 onward
# (grade 2 at 4, grade 3 at 7, ... grade 6 at 16). Grade 0's `0: 1` entry:
# same "preserve the existing grade-0 row" reasoning as
# `SPONTANEOUS_9_GRADE_UNLOCK`'s own docstring.
BARD_GRADE_UNLOCK = {0: 1, 1: 1, 2: 4, 3: 7, 4: 10, 5: 13, 6: 16}

# grade 1..6 only, same "cantrips are unlimited, never a row/value here"
# rule as the spontaneous 9-grade table above. Index 0 of each list is
# grade 1.
BARD_SPELLS_PER_DAY: dict[int, list[int]] = {
    1: [1, 0, 0, 0, 0, 0],
    2: [2, 0, 0, 0, 0, 0],
    3: [3, 0, 0, 0, 0, 0],
    4: [3, 1, 0, 0, 0, 0],
    5: [4, 2, 0, 0, 0, 0],
    6: [4, 3, 0, 0, 0, 0],
    7: [4, 3, 1, 0, 0, 0],
    8: [4, 4, 2, 0, 0, 0],
    9: [5, 4, 3, 0, 0, 0],
    10: [5, 4, 3, 1, 0, 0],
    11: [5, 4, 4, 2, 0, 0],
    12: [5, 5, 4, 3, 0, 0],
    13: [5, 5, 4, 3, 1, 0],
    14: [5, 5, 4, 4, 2, 0],
    15: [5, 5, 5, 4, 3, 0],
    16: [5, 5, 5, 4, 3, 1],
    17: [5, 5, 5, 4, 4, 2],
    18: [5, 5, 5, 5, 4, 3],
    19: [5, 5, 5, 5, 5, 4],
    20: [5, 5, 5, 5, 5, 5],
}


def _full_9_grade_value(level: int, grade: int) -> int:
    return FULL_9_GRADE_SPELLS_PER_DAY[level][grade]


def _kampfmagus_value(level: int, grade: int) -> int:
    return KAMPFMAGUS_SPELLS_PER_DAY[level][grade]


def _ranger_value(level: int, grade: int) -> int:
    return RANGER_SPELLS_PER_DAY[level][grade - 1]


def _spontaneous_9_grade_value(level: int, grade: int) -> int | None:
    # Grade 0 (cantrips) is unconditionally unlimited for these classes —
    # never a real per-day number, see this module's own docstring.
    if grade == 0:
        return None
    return SPONTANEOUS_9_GRADE_SPELLS_PER_DAY[level][grade - 1]


def _bard_value(level: int, grade: int) -> int | None:
    if grade == 0:
        return None
    return BARD_SPELLS_PER_DAY[level][grade - 1]


# class name -> (grade-unlock table, spells/day lookup)
FULL_9_GRADE_CLASSES = ("Magier", "Hexe", "Kleriker", "Druide")
KAMPFMAGUS_CLASSES = ("Kampfmagus",)
RANGER_CLASSES = ("Waldläufer",)
SPONTANEOUS_9_GRADE_CLASSES = ("Hexenmeister", "Mystiker")
BARD_CLASSES = ("Barde",)


def main() -> None:
    classes = json.loads((SEED_DIR / "base_classes.json").read_text(encoding="utf-8"))
    class_id_by_name = {c["name"]: c["id"] for c in classes}

    existing = json.loads((SEED_DIR / "base_class_spells_known.json").read_text(encoding="utf-8"))
    existing_by_key = {(row["base_class_id"], row["level"], row["grade"]): row for row in existing}

    touched_class_ids = {
        class_id_by_name[name]
        for name in FULL_9_GRADE_CLASSES
        + KAMPFMAGUS_CLASSES
        + RANGER_CLASSES
        + SPONTANEOUS_9_GRADE_CLASSES
        + BARD_CLASSES
    }
    final = [row for row in existing if row["base_class_id"] not in touched_class_ids]

    def emit(class_name: str, unlock: dict[int, int], value_fn) -> int:
        base_class_id = class_id_by_name[class_name]
        count = 0
        for level in range(1, MAX_LEVEL + 1):
            grades = [grade for grade, unlock_level in unlock.items() if unlock_level <= level]
            for grade in grades:
                key = (base_class_id, level, grade)
                prior = existing_by_key.get(key)
                row_id = prior["id"] if prior else str(uuid.uuid5(NAMESPACE, f"{base_class_id}|{level}|{grade}"))
                prior_count = prior["count"] if prior else None
                final.append(
                    {
                        "id": row_id,
                        "base_class_id": base_class_id,
                        "level": level,
                        "grade": grade,
                        "count": prior_count,
                        "spells_per_day": value_fn(level, grade),
                    }
                )
                count += 1
        return count

    added = 0
    for name in FULL_9_GRADE_CLASSES:
        added += emit(name, FULL_9_GRADE_UNLOCK, _full_9_grade_value)
    for name in KAMPFMAGUS_CLASSES:
        added += emit(name, KAMPFMAGUS_GRADE_UNLOCK, _kampfmagus_value)
    for name in RANGER_CLASSES:
        added += emit(name, RANGER_4_GRADE_UNLOCK, _ranger_value)
    for name in SPONTANEOUS_9_GRADE_CLASSES:
        added += emit(name, SPONTANEOUS_9_GRADE_UNLOCK, _spontaneous_9_grade_value)
    for name in BARD_CLASSES:
        added += emit(name, BARD_GRADE_UNLOCK, _bard_value)

    final.sort(key=lambda r: (r["base_class_id"], r["level"], r["grade"]))
    (SEED_DIR / "base_class_spells_known.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"base_class_spells_known: {len(final)} rows ({added} touched, {len(final) - added} untouched)")


if __name__ == "__main__":
    main()
