"""Fills in `base_class_spells_known.spells_per_day` (roadmap slice 6 —
real daily spell-slot counts, `rules/spells.py`'s `spells_per_day`/
`total_spell_slots`) for the 6 currently-seeded arcane-/divine-prepared
classes, transcribed from each class's own "Zauber pro Tag" table on
prd.5footstep.de (fetched directly, not from memory — see the URLs in each
table constant below).

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

Table sources (verified 2026-08-23 against the live pages, not
transcribed from memory):
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


def _full_9_grade_value(level: int, grade: int) -> int:
    return FULL_9_GRADE_SPELLS_PER_DAY[level][grade]


def _kampfmagus_value(level: int, grade: int) -> int:
    return KAMPFMAGUS_SPELLS_PER_DAY[level][grade]


def _ranger_value(level: int, grade: int) -> int:
    return RANGER_SPELLS_PER_DAY[level][grade - 1]


# class name -> (grade-unlock table, spells/day lookup)
FULL_9_GRADE_CLASSES = ("Magier", "Hexe", "Kleriker", "Druide")
KAMPFMAGUS_CLASSES = ("Kampfmagus",)
RANGER_CLASSES = ("Waldläufer",)


def main() -> None:
    classes = json.loads((SEED_DIR / "base_classes.json").read_text(encoding="utf-8"))
    class_id_by_name = {c["name"]: c["id"] for c in classes}

    existing = json.loads((SEED_DIR / "base_class_spells_known.json").read_text(encoding="utf-8"))
    existing_by_key = {(row["base_class_id"], row["level"], row["grade"]): row for row in existing}

    touched_class_ids = {
        class_id_by_name[name] for name in FULL_9_GRADE_CLASSES + KAMPFMAGUS_CLASSES + RANGER_CLASSES
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

    final.sort(key=lambda r: (r["base_class_id"], r["level"], r["grade"]))
    (SEED_DIR / "base_class_spells_known.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"base_class_spells_known: {len(final)} rows ({added} touched, {len(final) - added} untouched)")


if __name__ == "__main__":
    main()
