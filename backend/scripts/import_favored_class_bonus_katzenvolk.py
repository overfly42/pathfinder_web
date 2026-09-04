"""Import Katzenvolk's (Catfolk) Advanced Race Guide alternate
favored-class-bonus options from http://prd.5footstep.de/AusbauregelnIIIVoelker/
UngewoehnlicheVoelker/Katzenvolk into the seed JSON files. Same shape as
`import_favored_class_bonus_elf.py`/`import_favored_class_bonus_halbork.py`/
`import_ork.py`'s own favored-class-bonus section - one `race_id`-scoped
`BaseClassOptionChoice` per class, added to that class's existing
`favored_class_bonus` `BaseClassOptionGroup` if an earlier race's script
already created one (`(base_class_id, key)` is unique - a second group would
collide), or a newly created one otherwise.

The page lists 7 entries, one per class (Barde, Druide, Hexenmeister,
Mystiker, Ritter, Schurke, Waldläufer). This script transcribes the 6 that
have a matching seeded root `BaseClass` in this app - Ritter has no seeded
`BaseClass` row at all (see roadmap.md: blocked on that class existing at
all first, same as Alchemist/Inquisitor/Kampfmagus/Paktmagier/Schütze were
for the Halb-Ork/Elf scripts), so it's skipped, not guessed.

Every choice's description lives on a matching `BaseClassAbility` +
`BaseClassAbilityGrant(option_choice_id=<choice>.id, level=1)` pair, same
pattern every other option-group choice in this codebase uses. The universal
"hp"/"skill" values stay the two hardcoded string literals
`routers/characters.py`'s `level_up_character` already checks directly - not
modeled here, same as every prior race's script.

Numeric computation (how many picks convert to how much bonus, flat or
fractional, capped or not) is deliberately NOT implemented here -
`rules/favored_class_bonuses.py` only has handlers for the Halb-Ork/Ork
entries seeded so far (Elf's own 15 entries are flavor-only too, per that
script's own docstring); wiring these 6 new choice ids in there is a
follow-up, composition (this script) vs. computation, per CLAUDE.md.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database - run the normal seed scripts afterward):
    cd backend && python scripts/import_favored_class_bonus_katzenvolk.py
    python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("f0a681a3-8b99-4c58-bcfd-3ee0cb6aea72")

KATZENVOLK_RACE_ID = "b7af198e-2839-44d3-a7fd-b800759ede9c"

# (class_name, description) - verbatim PRD text, same convention as
# import_favored_class_bonus_elf.py/import_favored_class_bonus_halbork.py.
ENTRIES: list[tuple[str, str]] = [
    (
        "Barde",
        "Addiere +1/2 auf den Bonus von Bardenwissen.",
    ),
    (
        "Druide",
        "Addiere +1 TP zu den TP des Tiergefährten des Druiden. Sollte der Druide je seinen "
        "Tiergefährten ersetzen, erhält der neue Tiergefährte diese Bonustrefferpunkte.",
    ),
    (
        "Hexenmeister",
        "Wähle eine Blutlinienkraft der 1. Stufe, welche CH-Modifikator +3 Mal am Tag einsetzbar "
        "ist. Addiere +1/2 zu der Anzahl der täglichen Anwendungen dieser Blutlinienkraft.",
    ),
    (
        "Mystiker",
        "Addiere einen Zauber von der Zauberliste des Mystikers zur Liste der ihm bekannten "
        "Zauber. Der Grad dieses Zaubers muss mindestens um einen Grad geringer sein als der "
        "höchstgradige Mystikerzauber des Mystikers.",
    ),
    (
        "Schurke",
        "Addiere einen Bonus von +1/2 auf Fertigkeitswürfe für Bluffen zum Fintieren und für "
        "Fingerfertigkeit für Taschendiebstahl.",
    ),
    (
        "Waldläufer",
        "Wähle eine der folgenden Waffen aus: Klauen, Kukri, Kurzbogen, Kurzspeer, Langbogen oder "
        "Langschwert. Addiere +1/2 auf Bestätigungswürfe für Kritische Treffer mit dieser Waffe "
        "(maximal +4); dieser Bonus ist nicht kumulativ mit Kritischer Trefferfokus.",
    ),
]

assert len(ENTRIES) == 6, len(ENTRIES)
assert len({name for name, _ in ENTRIES}) == 6, "duplicate class name in ENTRIES"


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
    classes = load("base_classes.json")
    class_id_by_name = {c["name"]: c["id"] for c in classes}
    for name, _description in ENTRIES:
        assert name in class_id_by_name, f"no seeded BaseClass named {name!r}"

    groups = load("base_class_option_groups.json")
    choices = load("base_class_option_choices.json")
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    existing_ability_ids = {a["id"] for a in abilities}

    # `favored_class_bonus` is one shared `BaseClassOptionGroup` per class
    # (unique on `(base_class_id, key)`) - reuse an earlier race's row where
    # one already exists (every class here already has one from Halb-Ork/
    # Ork/Elf); nothing new to create in practice, but the fallback stays
    # for symmetry with those scripts.
    existing_group_id_by_class = {g["base_class_id"]: g["id"] for g in groups if g["key"] == "favored_class_bonus"}

    own_choice_ids = {uid("katzenvolk-fcb-choice", class_id_by_name[name]) for name, _ in ENTRIES}
    choices[:] = [c for c in choices if c["id"] not in own_choice_ids]
    own_ability_ids = {uid("katzenvolk-fcb-ability", name) for name, _ in ENTRIES}
    abilities[:] = [a for a in abilities if a["id"] not in own_ability_ids]
    own_grant_ids = {uid("katzenvolk-fcb-grant", class_id_by_name[name]) for name, _ in ENTRIES}
    grants[:] = [g for g in grants if g["id"] not in own_grant_ids]

    for class_name, description in ENTRIES:
        class_id = class_id_by_name[class_name]
        group_id = existing_group_id_by_class.get(class_id)
        if group_id is None:
            group_id = uid("katzenvolk-fcb-group", class_id)
            groups.append(
                {
                    "id": group_id,
                    "base_class_id": class_id,
                    "key": "favored_class_bonus",
                    "label": "Bevorzugte Klasse",
                    "max_choices": 20,
                }
            )
            existing_group_id_by_class[class_id] = group_id

        choice_id = uid("katzenvolk-fcb-choice", class_id)
        choices.append(
            {
                "id": choice_id,
                "group_id": group_id,
                "name": f"Katzenvolk ({class_name})",
                "min_level": None,
                "requires_choice_id": None,
                "race_id": KATZENVOLK_RACE_ID,
            }
        )

        ability_id = uid("katzenvolk-fcb-ability", class_name)
        if ability_id not in existing_ability_ids:
            abilities.append({"id": ability_id, "name": f"Katzenvolk ({class_name})", "description": description})
            existing_ability_ids.add(ability_id)

        grants.append(
            {
                "id": uid("katzenvolk-fcb-grant", class_id),
                "base_class_id": class_id,
                "ability_id": ability_id,
                "option_choice_id": choice_id,
                "level": 1,
            }
        )

    save("base_class_option_groups.json", groups)
    save("base_class_option_choices.json", choices)
    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)

    print("Favored-class-bonus entries imported:", len(ENTRIES))
    print("Done.")


if __name__ == "__main__":
    main()
