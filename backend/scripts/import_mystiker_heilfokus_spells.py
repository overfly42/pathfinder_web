"""Seed Mystiker's (Oracle's) "Stoßgebete-Fokus" (Kurieren/Verletzen) bonus
spells: real PF1e rule (the SRD/PRD Oracle text) — at 1st level an oracle
chooses once between adding every "Wunden heilen" (cure) or every "Wunden
verursachen" (inflict) spell to her spells known, each as soon as she's
capable of casting it, for free (not counted against her normal known-spell
budget). The `heilfokus` `BaseClassOptionGroup`/choices ("Wunden heilen"/
"Wunden verursachen") already existed as inert seed data (`base_class_option_
groups.json`/`base_class_option_choices.json`) with nothing granting the
actual spells - this script adds the `BaseClassSpellGrant` rows, same
mechanism already used for Hexenmeister's Blutlinie and Hexe's Schutzherr
(`rules/spells.py`'s `granted_option_choice_spells`, already called
unconditionally for every class's option choices in `create_character`/
`level_up_character` - no new grant-insertion code needed, only data).

Spell/level pairs aren't guessed from the generic 6-level spontaneous-caster
chart (grade 1 at class level 3, as Hexenmeister/Sorcerer get) - Oracle's own
`base_class_spells_known` table was queried directly and turns out to differ
(grade 1 already at 1st level): grade -> first-accessible-level came out as
{1: 1, 2: 4, 3: 6, 4: 8, 5: 10, 6: 12, 7: 14, 8: 16}. Mystiker has no `base_
class_spells.json` rows of its own at all (`spell_list_source_id` points at
Kleriker - the spell list, and therefore the cure/inflict spell ids/grades,
are Kleriker's own rows). Only the 8 non-"Legendäre" cure/inflict pairs
(grades 1-8) are granted - the "Legendäre" variants are a separate
Ausbauregeln-V-Legenden-tier spell, not part of the base "every cure spell"
rule, and there is no grade-9 cure/inflict spell in the source material at
all.

Run with the project venv active (this only writes the fixture JSON file,
it doesn't touch the database):
    cd backend && python scripts/import_mystiker_heilfokus_spells.py
    python -m app.seed.spell_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("4b8e6c2a-7d3f-4a9e-8b5c-1f6a3d9e7c4b")

MYSTIKER_ID = "949fe615-12a0-4eed-9e2e-25eaab3e3153"
KLERIKER_ID = "1e6e60de-d72f-4910-b19d-55ca11e14190"
WUNDEN_HEILEN_CHOICE_ID = "c14dc045-ba95-5d1b-b413-aac7c93bd05f"
WUNDEN_VERURSACHEN_CHOICE_ID = "5b4d0fc5-21cb-5888-8046-69151010c780"

# grade -> class level the grade first becomes accessible (from Mystiker's
# own base_class_spells_known.json, not the generic sorcerer-style chart)
LEVEL_BY_GRADE = {1: 1, 2: 4, 3: 6, 4: 8, 5: 10, 6: 12, 7: 14, 8: 16}

# (grade, cure spell name, inflict spell name) - Kleriker's base_class_spells.json
CURE_INFLICT_BY_GRADE = [
    (1, "Leichte Wunden heilen", "Leichte Wunden verursachen"),
    (2, "Mittelschwere Wunden heilen", "Mittelschwere Wunden verursachen"),
    (3, "Schwere Wunden heilen", "Schwere Wunden verursachen"),
    (4, "Kritische Wunden heilen", "Kritische Wunden verursachen"),
    (5, "Massen-Leichte Wunden heilen", "Massen-Leichte Wunden verursachen"),
    (6, "Massen-Mittelschwere Wunden heilen", "Massen-Mittelschwere Wunden verursachen"),
    (7, "Massen-Schwere Wunden heilen", "Massen-Schwere Wunden verursachen"),
    (8, "Massen-Kritische Wunden heilen", "Massen-Kritische Wunden verursachen"),
]


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
    spell_grants = load("base_class_spell_grants.json")
    spells = load("base_spells.json")
    spell_id_by_name = {s["name"]: s["id"] for s in spells}

    class_spells = load("base_class_spells.json")
    kleriker_grade_by_spell_id = {
        row["spell_id"]: row["grade"] for row in class_spells if row["base_class_id"] == KLERIKER_ID
    }

    new_grants: list[dict] = []
    unresolved: list[str] = []

    for grade, heilen_name, verursachen_name in CURE_INFLICT_BY_GRADE:
        level = LEVEL_BY_GRADE[grade]
        for choice_id, spell_name in (
            (WUNDEN_HEILEN_CHOICE_ID, heilen_name),
            (WUNDEN_VERURSACHEN_CHOICE_ID, verursachen_name),
        ):
            spell_id = spell_id_by_name.get(spell_name)
            if spell_id is None:
                unresolved.append(spell_name)
                continue
            if kleriker_grade_by_spell_id.get(spell_id) != grade:
                unresolved.append(f"{spell_name}: expected grade {grade}, found {kleriker_grade_by_spell_id.get(spell_id)}")
                continue
            new_grants.append(
                {
                    "id": uid("mystiker-heilfokus-grant", choice_id, spell_id),
                    "base_class_id": MYSTIKER_ID,
                    "option_choice_id": choice_id,
                    "spell_id": spell_id,
                    "level": level,
                }
            )

    save("base_class_spell_grants.json", spell_grants + new_grants)

    print(f"Wrote {len(new_grants)} Mystiker heilfokus spell grants.")
    if unresolved:
        print(f"WARNING: {len(unresolved)} unresolved/mismatched entr(ies):")
        for entry in unresolved:
            print(f"  {entry}")


if __name__ == "__main__":
    main()
