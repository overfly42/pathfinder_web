"""Fills in `base_class_spells_known` rows for the arcane-prepared
(Wizard-style) classes — Magier and Hexe — for the full character level
range (1-20). For this casting style `count` is unused/null (see
`BaseClassSpellsKnown`'s docstring): only row *presence* matters, as the
grade-accessibility gate ("no row for this (class, level, grade) -> that
grade isn't castable yet").

Not PRD-derived: the grade-unlocks-at-level shape below is the same
standard 9-level full-caster table shared by every PF1e class with this
progression (Wizard, Cleric, Druid, Sorcerer, Witch all match) — a rules
constant, not scraped data, same "hand-transcribe it" category as
`build_conditions_seed.py`'s standard-conditions list.

This also **fixes an existing bug**, not just fills a gap: Magier's
pre-existing rows only went up to level 6, and even within that range
capped at grade 2 for levels 5-6 — the official table opens grade 3 at
level 5, not 6. Hexe had zero rows at all (the immediate trigger: a
level-1 Hexe's character-creation spellbook step showed a 0/0 budget for
every non-cantrip grade, since no row existed to gate any grade open at
all).

Usage (from backend/scripts, project venv active):
    python build_arcane_prepared_spells_known_seed.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"

# grade -> first class level at which it's accessible (standard PF1e
# 9-level full-caster table: Wizard/Cleric/Druid/Sorcerer/Witch all share
# this shape, differing only in spells-per-day counts, which this app
# doesn't track for arcane-prepared classes anyway).
GRADE_UNLOCK_LEVEL = {0: 1, 1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11, 7: 13, 8: 15, 9: 17}
MAX_LEVEL = 20

NAMESPACE = uuid.UUID("2b6e4a1d-8f3c-4b7a-9d5e-6c1f8a2b3d4e")


def main() -> None:
    classes = json.loads((SEED_DIR / "base_classes.json").read_text(encoding="utf-8"))
    class_id_by_name = {c["name"]: c["id"] for c in classes}

    existing = json.loads((SEED_DIR / "base_class_spells_known.json").read_text(encoding="utf-8"))
    existing_by_key = {(row["base_class_id"], row["level"], row["grade"]): row["id"] for row in existing}
    # Rows for classes this script doesn't touch (Hexenmeister/Mystiker/Barde) pass through untouched.
    touched_class_ids = {class_id_by_name[name] for name in ("Magier", "Hexe")}
    final = [row for row in existing if row["base_class_id"] not in touched_class_ids]

    added = 0
    for class_name in ("Magier", "Hexe"):
        base_class_id = class_id_by_name[class_name]
        for level in range(1, MAX_LEVEL + 1):
            grades = [grade for grade, unlock_level in GRADE_UNLOCK_LEVEL.items() if unlock_level <= level]
            for grade in grades:
                key = (base_class_id, level, grade)
                row_id = existing_by_key.get(key) or str(uuid.uuid5(NAMESPACE, f"{base_class_id}|{level}|{grade}"))
                final.append({"id": row_id, "base_class_id": base_class_id, "level": level, "grade": grade, "count": None})
                added += 1

    final.sort(key=lambda r: (r["base_class_id"], r["level"], r["grade"]))
    (SEED_DIR / "base_class_spells_known.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"base_class_spells_known: {len(final)} rows ({added} for Magier+Hexe, {len(final) - added} untouched)")


if __name__ == "__main__":
    main()
