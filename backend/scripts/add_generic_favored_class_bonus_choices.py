"""Adds the two universal "hp"/"skill" favored-class-bonus values as real
`BaseClassOptionChoice` rows — one pair per root class, under that class's
existing `favored_class_bonus` `BaseClassOptionGroup` (all 15 root classes
already have one, seeded by the per-race favored-class-bonus importers).

Before this script, "hp"/"skill" were the two hardcoded string literals
`routers/characters.py`'s `level_up_character`/`create_character` checked
directly and never persisted as a `CharacterClassOption` row at all (see
those scripts' own docstrings, e.g. `import_favored_class_bonus_katzenvolk.py`).
That meant a favored-class level's hp/skill pick left no queryable trace
anywhere — not in `character_class_options`, not in the level-up history —
unlike every other favored-class-bonus value (a race-scoped alternate like
"Katzenvolk (Mystiker)"), which already got a real row. This script closes
that gap by giving hp/skill real, class-scoped choice rows (`race_id=None`,
so they're never race-filtered away) so every favored-class-bonus pick,
including hp/skill, flows through the exact same persistence path and is
fully auditable.

No matching `BaseClassAbility`/`BaseClassAbilityGrant` pair is created for
these two (unlike a race-scoped alternate) — the level-up wizard already has
fixed, friendly text ("+1 Trefferpunkt"/"+1 Fertigkeitsrang") for them, so
there's no rules text to attach, and `sheet.py`'s
`_favored_class_bonus_descriptions`/`_favored_class_bonus_short_labels`
deliberately keep excluding these two names from their DB-driven output.

Run with the project venv active (this only writes the fixture JSON file, it
doesn't touch the database - run the normal seed script afterward):
    cd backend && python scripts/add_generic_favored_class_bonus_choices.py
    python -m app.seed.class_option_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

# Same namespace every favored-class-bonus importer in this directory uses
# (`import_favored_class_bonus_katzenvolk.py` et al.) - not because these
# choices share their content, just for one consistent id-generation scheme
# across the whole favored-class-bonus family.
ID_NAMESPACE = uuid.UUID("f0a681a3-8b99-4c58-bcfd-3ee0cb6aea72")

GENERIC_VALUES = ("hp", "skill")


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def save(filename: str, rows: list[dict]) -> None:
    deduped: dict[str, dict] = {}
    for row in rows:
        deduped[row["id"]] = row
    (SEED_DIR / filename).write_text(
        json.dumps(list(deduped.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    groups = load("base_class_option_groups.json")
    choices = load("base_class_option_choices.json")

    fcb_groups = [g for g in groups if g["key"] == "favored_class_bonus"]
    assert fcb_groups, "no favored_class_bonus groups seeded yet - run the class/option seed first"

    own_choice_ids = {uid("generic-fcb-choice", value, g["base_class_id"]) for g in fcb_groups for value in GENERIC_VALUES}
    choices[:] = [c for c in choices if c["id"] not in own_choice_ids]

    added = 0
    for group in fcb_groups:
        for value in GENERIC_VALUES:
            choices.append(
                {
                    "id": uid("generic-fcb-choice", value, group["base_class_id"]),
                    "group_id": group["id"],
                    "name": value,
                    "min_level": None,
                    "requires_choice_id": None,
                    "race_id": None,
                }
            )
            added += 1

    save("base_class_option_choices.json", choices)

    print(f"Generic favored-class-bonus choices added: {added} ({len(fcb_groups)} classes x {len(GENERIC_VALUES)})")
    print("Done.")


if __name__ == "__main__":
    main()
