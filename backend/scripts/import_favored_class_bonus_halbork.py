"""Import Half-Orc's Advanced Race Guide alternate favored-class-bonus
options from http://prd.5footstep.de/AusbauregelnIIIVoelker/Grundvoelker/
HalbOrks into the seed JSON files.

The page lists 19 entries, one per class. This script transcribes the 13
that have a matching seeded root `BaseClass` in this app (Barbar, Barde,
Druide, Hexenmeister, Kämpfer, Kleriker, Magier, Mönch, Mystiker, Paladin,
Schurke, Waldläufer) plus Entfesselter Barbar (Unchained Barbarian) — the
page itself only lists "Barbar", not "Entfesselter Barbar" separately, but
both classes track the exact same "Runden Kampfrausch pro Tag" resource, so
the same bonus text/handler applies to both per the project owner's
explicit instruction. Alchemist/Hexe/Inquisitor/Kampfmagus/Paktmagier/
Ritter/Schütze have no seeded `BaseClass` row at all — nothing to attach
their entries to, so they're skipped, not guessed.

Each class gets its own `favored_class_bonus` `BaseClassOptionGroup`
(`max_choices=20` — a lifetime cap, one pick per favored-class level 1-20)
containing exactly one `race_id`-scoped `BaseClassOptionChoice`. The
universal "hp"/"skill" favored-class-bonus values are *not* modeled as
choices here at all — they stay the two hardcoded string literals
`routers/characters.py`'s `level_up_character` already checks directly (see
that function's docstring), since introducing them as catalog rows would
either rename those stable API values to their German display names
(breaking existing tests) or require a second, parallel naming scheme for
no benefit — this script only adds the *additional*, race-gated choice each
class gets on top of the two universal ones.

Every choice's description (this table has no description column of its
own) lives on a matching `BaseClassAbility` + `BaseClassAbilityGrant(
option_choice_id=<choice>.id, level=1)` pair — the same pattern every other
option-group choice in this codebase already uses (Kampfrauschkraft,
Mysterium/Offenbarung, ...), not a special case invented for this script.

Numeric computation (how many picks convert to how much bonus, flat or
fractional, capped or not) is `rules/favored_class_bonuses.py`'s job, keyed
by each choice's own frozen id — composition (this script) vs. computation
(that module), per CLAUDE.md.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database - run the normal seed scripts afterward):
    cd backend && python scripts/import_favored_class_bonus_halbork.py
    python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("6f1e2d3c-4b5a-4978-8a6b-1c2d3e4f5061")

HALBORK_RACE_ID = "88d38c58-be34-42e6-b4a5-08704bc97cb8"

# (class_name, description) — description is the choice's full rules text,
# verbatim from the PRD page (only "Addiere"/"Wähle"-style leading verb kept
# as-is, no paraphrasing, since this project's own convention for a choice's
# BaseClassAbility description is the real rulebook text). "Entfesselter
# Barbar" is not on the source page - see module docstring for why it's
# included here anyway, with Barbar's own text reused unmodified.
ENTRIES: list[tuple[str, str]] = [
    (
        "Barbar",
        "Addiere +1 auf die Gesamtanzahl der Runden an Kampfrausch pro Tag.",
    ),
    (
        "Entfesselter Barbar",
        "Addiere +1 auf die Gesamtanzahl der Runden an Kampfrausch pro Tag.",
    ),
    (
        "Barde",
        "Addiere +1 auf die Gesamtzahl der Runden an Bardenauftritt pro Tag.",
    ),
    (
        "Druide",
        "Addiere +1/3 auf den natürlichen Rüstungsbonus des Druiden in Tiergestalt.",
    ),
    (
        "Hexenmeister",
        "Addiere +1/2 zum Feuerschaden aller vom Hexenmeister gewirkten Zauber, die Feuerschaden "
        "verursachen.",
    ),
    (
        "Kämpfer",
        "Addiere +2 auf alle Stabilisierungswürfe, wenn der Charakter im Sterben liegt.",
    ),
    (
        "Kleriker",
        "Wähle eine Domänenfähigkeit der 1. Stufe aus, welche normalerweise (3 + WE-Modifikator des "
        "Klerikers) Mal am Tag anwendbar ist. Der Kleriker addiert +1/2 auf die Anzahl seiner "
        "Anwendungsmöglichkeiten pro Tag.",
    ),
    (
        "Magier",
        "Addiere einen Bonus von +1 auf Konzentrationswürfe, die erforderlich werden, wenn der Magier "
        "beim Wirken eines Magierzaubers Schaden nimmt.",
    ),
    (
        "Mönch",
        "Addiere +1 auf die KMV des Mönchs gegen Ringkampf und +1/2 auf die Anzahl seiner täglichen "
        "Betäubende Schläge.",
    ),
    (
        "Mystiker",
        "Addiere einen Mystikerzauber zur Liste deiner bekannten Zauber. Dieser Zauber muss "
        "wenigstens ein Grad unter dem höchsten liegen, den der Mystiker wirken kann.",
    ),
    (
        "Paladin",
        "Addiere +1/3 auf Bestätigungswürfe für Kritische Treffer, wenn du Böses niederstrecken "
        "einsetzt (Maximumbonus von +5). Dieser Bonus ist nicht kumulativ mit "
        "Kritischer-Treffer-Fokus.",
    ),
    (
        "Schurke",
        "Addiere +1/3 auf Bestätigungswürfe für Kritische Treffer mit Hinterhältigem Angriff "
        "(Maximumbonus von +5). Dieser Bonus ist nicht kumulativ mit Kritischer-Treffer-Fokus.",
    ),
    (
        "Waldläufer",
        "Der Tiergefährte des Waldläufers erhält einen zusätzlichen TP. Sollte der Halb-Ork jemals "
        "seinen Tiergefährten wechseln, erhält der neue Tiergefährte diese zusätzlichen "
        "Trefferpunkte.",
    ),
]

assert len(ENTRIES) == 13, len(ENTRIES)
assert len({name for name, _ in ENTRIES}) == 13, "duplicate class name in ENTRIES"


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

    own_group_ids = {uid("fcb-group", class_id_by_name[name]) for name, _ in ENTRIES}
    groups = [g for g in groups if g["id"] not in own_group_ids]
    choices = [c for c in choices if c["group_id"] not in own_group_ids]

    own_ability_ids = {uid("fcb-ability", name) for name, _ in ENTRIES}
    own_grant_ids = {uid("fcb-grant", class_id_by_name[name]) for name, _ in ENTRIES}
    grants = [g for g in grants if g["id"] not in own_grant_ids]

    for class_name, description in ENTRIES:
        class_id = class_id_by_name[class_name]
        group_id = uid("fcb-group", class_id)
        groups.append(
            {
                "id": group_id,
                "base_class_id": class_id,
                "key": "favored_class_bonus",
                "label": "Bevorzugte Klasse",
                "max_choices": 20,
            }
        )

        # Choice name mirrors the class name (there's only ever one
        # race-scoped choice per class today) - display text for the
        # player is the linked BaseClassAbility's own description, not
        # this name.
        choice_id = uid("fcb-choice", class_id)
        choices.append(
            {
                "id": choice_id,
                "group_id": group_id,
                "name": f"Halb-Ork ({class_name})",
                "min_level": None,
                "requires_choice_id": None,
                "race_id": HALBORK_RACE_ID,
            }
        )

        ability_id = uid("fcb-ability", class_name)
        if ability_id not in existing_ability_ids:
            abilities.append({"id": ability_id, "name": f"Halb-Ork ({class_name})", "description": description})
            existing_ability_ids.add(ability_id)

        grants.append(
            {
                "id": uid("fcb-grant", class_id),
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
