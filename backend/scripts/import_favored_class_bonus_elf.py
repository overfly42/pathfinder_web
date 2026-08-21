"""Import Elf's Advanced Race Guide alternate favored-class-bonus options
from http://prd.5footstep.de/AusbauregelnIIIVoelker/Grundvoelker/Elfen into
the seed JSON files. Same shape as `import_favored_class_bonus_halbork.py`/
`import_ork.py`'s own favored-class-bonus section - one `race_id`-scoped
`BaseClassOptionChoice` per class, added to that class's existing
`favored_class_bonus` `BaseClassOptionGroup` if Halb-Ork/Ork already created
one (`(base_class_id, key)` is unique - a second group would collide), or a
newly created one otherwise.

The page lists 19 entries, one per class. This script transcribes the 14
that have a matching seeded root `BaseClass` in this app (Barbar, Barde,
Druide, Hexe, Hexenmeister, Kämpfer, Kampfmagus, Kleriker, Magier, Mönch,
Mystiker, Paladin, Schurke, Waldläufer) plus Entfesselter Barbar (Unchained
Barbarian) - same judgment call `import_favored_class_bonus_halbork.py`
documents for the same class: the page only lists "Barbar", not
"Entfesselter Barbar" separately, but this particular bonus (+1 base speed,
stacking with and bound by the same conditions as the Schnelle Bewegung
class feature) applies to an unchanged class feature both classes share
unmodified (`import_entfesselter_barbar.py`'s own docstring: only rage
itself changed between core and unchained, not fast movement) - so the same
text is reused verbatim for both. Alchemist/Inquisitor/Paktmagier/Ritter/
Schütze have no seeded `BaseClass` row at all - nothing to attach their
entries to, so they're skipped, not guessed.

Every choice's description lives on a matching `BaseClassAbility` +
`BaseClassAbilityGrant(option_choice_id=<choice>.id, level=1)` pair, same
pattern every other option-group choice in this codebase uses. The universal
"hp"/"skill" values stay the two hardcoded string literals
`routers/characters.py`'s `level_up_character` already checks directly -
not modeled here, same as the Halb-Ork/Ork scripts.

Numeric computation (how many picks convert to how much bonus, flat or
fractional, capped or not) is deliberately NOT implemented here -
`rules/favored_class_bonuses.py` only has handlers for the Halb-Ork/Ork
entries seeded so far; wiring these 15 new choice ids in there is a
follow-up, composition (this script) vs. computation, per CLAUDE.md.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database - run the normal seed scripts afterward):
    cd backend && python scripts/import_favored_class_bonus_elf.py
    python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("8e4b6d2a-1c3f-4a5e-9b7d-2c4e6f8a0b1c")

ELF_RACE_ID = "45790090-5c8f-494e-aefc-b1d3963c169f"

# (class_name, description) - verbatim PRD text, same convention as
# import_favored_class_bonus_halbork.py/import_ork.py.
ENTRIES: list[tuple[str, str]] = [
    (
        "Barbar",
        "Addiere +1 auf die Grundbewegungsrate des Barbaren. Im Kampf wirkt sich dies nur aus, falls "
        "der Barbar diese Option fünf Mal (oder ein Mehrfaches von Fünf) gewählt hat. Dieser Bonus ist "
        "kumulativ mit dem Klassenmerkmal Schnelle Bewegung und unterliegt denselben Bedingungen.",
    ),
    (
        "Entfesselter Barbar",
        "Addiere +1 auf die Grundbewegungsrate des Barbaren. Im Kampf wirkt sich dies nur aus, falls "
        "der Barbar diese Option fünf Mal (oder ein Mehrfaches von Fünf) gewählt hat. Dieser Bonus ist "
        "kumulativ mit dem Klassenmerkmal Schnelle Bewegung und unterliegt denselben Bedingungen.",
    ),
    (
        "Barde",
        "Addiere +1 auf die KMV des Barden gegen Entwaffnen.",
    ),
    (
        "Druide",
        "Addiere +1/3 auf den natürlichen Rüstungsbonus des Druiden in Tiergestalt.",
    ),
    (
        "Hexe",
        "Füge einen Hexenzauber von der Liste der Hexenzauber den dem Hexenvertrauten bekannten "
        "Zaubern hinzu. Der Grad dieses Zaubers muss niedriger sein als der dem Vertrauten bekannte "
        "Höchstgrad. Sollte die Hexe jemals ihren Vertrauten ersetzen, kennt der neue Vertraute diese "
        "Bonuszauber.",
    ),
    (
        "Hexenmeister",
        "Wähle eine Blutlinienkraft der 1. Stufe, welche normalerweise (3 + CH-Modifikator des Elfen) "
        "Mal am Tag einsetzbar ist. Der Hexenmeister addiert +1/2 tägliche Anwendung dieser Kraft.",
    ),
    (
        "Kämpfer",
        "Addiere +1 auf die KMV des Kämpfers gegen Entwaffnen und Zerschmettern.",
    ),
    (
        "Kampfmagus",
        "Der Kampfmagus erhält 1/6 eines neuen Kampfmagusarkanums.",
    ),
    (
        "Kleriker",
        "Wähle eine Domänenkraft der 1. Stufe, welche normalerweise (3 + WE-Modifikator des Elfen) Mal "
        "am Tag einsetzbar ist. Der Kleriker addiert +1/2 tägliche Anwendung dieser Kraft.",
    ),
    (
        "Magier",
        "Wähle eine Kraft der arkanen Schule der 1. Stufe, welche normalerweise (3 + IN-Modifikator des "
        "Elfen) Mal am Tag einsetzbar ist. Der Magier addiert +1/2 tägliche Anwendung dieser Kraft.",
    ),
    (
        "Mönch",
        "Addiere +1 auf die Grundbewegungsrate des Mönchs. Im Kampf wirkt sich dies nur aus, falls der "
        "Mönch diese Option fünf Mal (oder ein Mehrfaches von Fünf) gewählt hat. Dieser Bonus ist "
        "kumulativ mit dem Klassenmerkmal Schnelle Bewegung und unterliegt denselben Bedingungen.",
    ),
    (
        "Mystiker",
        "Addiere +1/2 auf die Stufe des Mystikers, um die Effekte einer Offenbarung zu bestimmen.",
    ),
    (
        "Paladin",
        "Addiere +1/2 Trefferpunkt zur Fähigkeit Handauflegen, egal ob diese zum Heilen oder Schädigen "
        "genutzt wird.",
    ),
    (
        "Schurke",
        "Addiere +1 auf die Zahl, welche der Schurke täglich einen Zaubertrick oder Zauber des 1. "
        "Grades nutzen kann, den er über den Schurkentrick Höhere Magie oder Niedere Magie erlangt hat. "
        "Er kann Höhere Magie nicht öfter am Tag einsetzen als Niedere Magie und muss natürlich über "
        "den entsprechenden Schurkentrick verfügen, um diese Option wählen zu können.",
    ),
    (
        "Waldläufer",
        "Wähle eine der folgenden Waffen: Kurzbogen, Kurzschwert, Langbogen, Langschwert, Rapier oder "
        "eine Waffe mit Elfisch im Namen. Addiere +1/2 auf Kritische Bestätigungswürfe mit dieser Waffe "
        "(Maximalbonus +4). Dieser Bonus ist nicht kumulativ mit Kritischer-Treffer-Fokus.",
    ),
]

assert len(ENTRIES) == 15, len(ENTRIES)
assert len({name for name, _ in ENTRIES}) == 15, "duplicate class name in ENTRIES"


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
    # (unique on `(base_class_id, key)`) - reuse Halb-Ork's/Ork's row where
    # one already exists (e.g. Barbar, Kleriker, Hexe, ...); only Kampfmagus
    # (brand new, no prior race has an alternate for it yet) needs one
    # created here.
    existing_group_id_by_class = {g["base_class_id"]: g["id"] for g in groups if g["key"] == "favored_class_bonus"}

    own_choice_ids = {uid("elf-fcb-choice", class_id_by_name[name]) for name, _ in ENTRIES}
    choices[:] = [c for c in choices if c["id"] not in own_choice_ids]
    own_ability_ids = {uid("elf-fcb-ability", name) for name, _ in ENTRIES}
    abilities[:] = [a for a in abilities if a["id"] not in own_ability_ids]
    own_grant_ids = {uid("elf-fcb-grant", class_id_by_name[name]) for name, _ in ENTRIES}
    grants[:] = [g for g in grants if g["id"] not in own_grant_ids]

    for class_name, description in ENTRIES:
        class_id = class_id_by_name[class_name]
        group_id = existing_group_id_by_class.get(class_id)
        if group_id is None:
            group_id = uid("elf-fcb-group", class_id)
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

        choice_id = uid("elf-fcb-choice", class_id)
        choices.append(
            {
                "id": choice_id,
                "group_id": group_id,
                "name": f"Elf ({class_name})",
                "min_level": None,
                "requires_choice_id": None,
                "race_id": ELF_RACE_ID,
            }
        )

        ability_id = uid("elf-fcb-ability", class_name)
        if ability_id not in existing_ability_ids:
            abilities.append({"id": ability_id, "name": f"Elf ({class_name})", "description": description})
            existing_ability_ids.add(ability_id)

        grants.append(
            {
                "id": uid("elf-fcb-grant", class_id),
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
