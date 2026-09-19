"""Import each Mystiker mystery's "Mysteriumszauber" table (one bonus known
spell at 2nd/4th/6th/.../18th-or-20th class level, per mystery) into
`base_class_spells.json`/`base_class_spell_grants.json` — the one part
`import_mystiker.py` explicitly deferred (see that script's own docstring,
"No BaseClassSpell/BaseClassSpellGrant rows for the ~90 spells..."). That
gap has since narrowed on its own: `base_spells.json` and Kleriker's own
`base_class_spells` rows have both grown a lot since that note was written
(most of the ~90 names now resolve, and Kleriker now has a real spell list),
so this finishes the job with today's data instead of re-deferring it.

Source: `app/fixtures/imported/mystiker_prd_import.json`'s
`mysteries.<name>.mystery_spells_text`, a semicolon-free comma list like
"Windstärke anpassen* (2.), Windstoß (4.), ...". The trailing `*` marks
something in the original PRD transcription that turned out not to
correlate cleanly with "on/off the Cleric list" once checked against this
project's actual seeded data (see the analysis this script's own history was
built from) — so it's ignored here in favor of directly checking each
resolved spell against Kleriker's real `base_class_spells` rows, which is
the fact that actually matters: whether Mystiker needs its own grade row for
this spell (`sheet.py`'s `_build_prepared_spell_grades`/`routers/characters
.py`'s `_resolve_prepared_class_spell` already established this fallback
for the Heimgesucht curse's four foreign spells — same pattern here, just
for mystery spells instead of curse spells).

Grade for a spell not on Kleriker's list is picked from whichever other
class already lists it, in this fixed preference order (Hexenmeister and
Magier agree on grade in every single one of these ~90 entries when both
have the spell at all; Hexe is the one list that occasionally runs a grade
higher, so it's deliberately not preferred):
    Hexenmeister > Magier > Druide > Barde > Waldläufer > Hexe > Kampfmagus

Run with the project venv active (writes fixture JSON only, does not touch
the database):
    cd backend && python scripts/import_mystiker_mystery_spells.py
Then load it into the dev DB the normal way:
    cd backend && python -m app.seed.spell_seed
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"
IMPORTED = FIXTURES / "imported" / "mystiker_prd_import.json"

# Same fixed id namespace `import_mystiker.py` already uses for this class's
# hand-authored ids, so a rerun upserts instead of duplicating.
ID_NAMESPACE = uuid.UUID("d4a1f8b0-6e2a-4b7a-8a5a-2f6a7b9c1d3e")

MYSTIKER_ID = uuid.UUID("949fe615-12a0-4eed-9e2e-25eaab3e3153")
KLERIKER_ID = uuid.UUID("1e6e60de-d72f-4910-b19d-55ca11e14190")

# One transcription glitch: the source text has a nested-parens qualifier
# ("Monster herbeizaubern V (nur Feuerelementare (10.)") that a plain
# "name (level.)" regex can't tell apart from the outer pair — hand-fixed
# here rather than making the regex handle nested parens for one row.
NAME_FIXUPS: dict[tuple[str, str], str] = {
    ("Flammen", "10"): "Monster herbeizaubern V",
}

GRADE_SOURCE_PRIORITY = ["Hexenmeister", "Magier", "Druide", "Barde", "Waldläufer", "Hexe", "Kampfmagus"]

ENTRY_RE = re.compile(r"([^,()]+?)\s*\((\d+)\.\)")


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def save(filename: str, rows: list[dict]) -> None:
    # Dedup by id (keep last) - uid()/uuid5 ids are deterministic, so
    # re-running this script upserts instead of appending duplicates.
    deduped: dict[str, dict] = {}
    for row in rows:
        deduped[row["id"]] = row
    (SEED_DIR / filename).write_text(
        json.dumps(list(deduped.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def parse_mystery_entries(text: str) -> list[tuple[str, int]]:
    """`(spell_name, class_level)` pairs from one mystery's
    `mystery_spells_text`, stopping before any trailing revelation prose
    (Schlacht's own text runs straight into "Offenbarungen: ..." after its
    spell list, unlike every other mystery)."""
    cut = text.split("Offenbarungen")[0]
    return [(raw_name.strip(), int(level)) for raw_name, level in ENTRY_RE.findall(cut)]


def main() -> None:
    data = json.loads(IMPORTED.read_text(encoding="utf-8"))
    mysteries = data["mysteries"]

    base_spells = load("base_spells.json")
    name_to_id = {row["name"]: row["id"] for row in base_spells}

    class_spells = load("base_class_spells.json")
    classes = load("base_classes.json")
    id_to_class_name = {row["id"]: row["name"] for row in classes}
    grades_by_spell: dict[str, dict[str, int]] = {}
    for row in class_spells:
        class_name = id_to_class_name.get(row["base_class_id"])
        if class_name:
            grades_by_spell.setdefault(row["spell_id"], {})[class_name] = row["grade"]

    mystery_group_ids = {g["id"] for g in load("base_class_option_groups.json") if g["key"] == "mystery"}
    mystery_choices = {
        row["name"]: row["id"]
        for row in load("base_class_option_choices.json")
        if row["group_id"] in mystery_group_ids
    }

    new_class_spells: list[dict] = list(class_spells)
    new_grants: list[dict] = list(load("base_class_spell_grants.json"))
    missing: list[str] = []

    for mystery, choice_id in mystery_choices.items():
        text = mysteries.get(mystery, {}).get("mystery_spells_text", "")
        for raw_name, level in parse_mystery_entries(text):
            clean_name = NAME_FIXUPS.get((mystery, str(level)), raw_name.rstrip("*").strip())
            spell_id = name_to_id.get(clean_name)
            if spell_id is None:
                missing.append(f"{mystery} ({level}.): {clean_name!r}")
                continue

            grades = grades_by_spell.get(spell_id, {})
            if "Kleriker" not in grades:
                # Foreign spell (not on Mystiker's own effective Kleriker
                # list) - needs its own grade row under Mystiker's own
                # base_class_id, same fallback `sheet.py`'s
                # `_build_prepared_spell_grades` already relies on for the
                # Heimgesucht curse's four foreign spells.
                grade = next((grades[c] for c in GRADE_SOURCE_PRIORITY if c in grades), None)
                if grade is None:
                    missing.append(f"{mystery} ({level}.): {clean_name!r} has no known grade on any list")
                    continue
                new_class_spells.append(
                    {
                        "id": uid("class-spell", str(MYSTIKER_ID), spell_id),
                        "base_class_id": str(MYSTIKER_ID),
                        "spell_id": spell_id,
                        "grade": grade,
                    }
                )

            new_grants.append(
                {
                    "id": uid("mystery-spell-grant", mystery, str(level)),
                    "base_class_id": str(MYSTIKER_ID),
                    "option_choice_id": choice_id,
                    "spell_id": spell_id,
                    "level": level,
                }
            )

    if missing:
        print("Unresolved entries (not written):")
        for entry in missing:
            print(f"  - {entry}")

    save("base_class_spells.json", new_class_spells)
    save("base_class_spell_grants.json", new_grants)
    print(f"base_class_spells.json: {len(new_class_spells)} rows total")
    print(f"base_class_spell_grants.json: {len(new_grants)} rows total")


if __name__ == "__main__":
    main()
