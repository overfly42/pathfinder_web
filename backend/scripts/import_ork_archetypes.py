"""Import the two Orc racial archetypes from
http://prd.5footstep.de/AusbauregelnIIIVoelker/UngewoehnlicheVoelker/Orks
into the seed JSON files: "Narbiger Hexendoktor" (Scarred Witch Doctor, a
Hexe archetype) and "Raufbold" (Dirty Fighter, a Kämpfer archetype). Same
shape as `import_barbar_seereauber.py` — one archetype `BaseClass` row per
archetype, new `BaseClassAbility`/`BaseClassAbilityGrant` rows under the
archetype's own class id, `BaseClassAbilityReplacement` rows scoping each to
the specific parent-class grant(s) it replaces.

Narbiger Hexendoktor (Hexe, `HEXE_ID`): the PRD text says Fetischmaske
"funktioniert ansonsten wie Hexenvertrauter und ersetzt dieses
Klassenmerkmal" (replaces the witch's familiar). The witch's familiar isn't
modeled as a `BaseClassAbility`/`BaseClassAbilityGrant` in this app at
all — there's no grant row to point a `BaseClassAbilityReplacement` at, so
Fetischmaske (like Konstitutionsabhängig and Hexennarbe, which don't replace
anything either per the source text) is added with no replacement row.
Narbenschild does replace something real: the level-1 "Hexerei" grant
(the witch's first hex pick), `HEXERELEVEL1_GRANT_ID` below.

Raufbold (Kämpfer, `KAEMPFER_ID`) — verified against the archetype's
official English name/text (d20pfsrd "Dirty Fighter", an Advanced Race
Guide Orc archetype) since one replaced-feature name in the German PRD
page doesn't match anything in this app's Kämpfer data: "Ausweichschritt...
Dieses Klassenmerkmal ersetzt Entrinnen" — Kämpfer has no "Entrinnen"
(Evasion) class feature in Pathfinder 1e at all (core or as seeded here).
The verified official text is unambiguous: Sidestep "replaces bravery" —
so Ausweichschritt is wired to replace Tapferkeit (Bravery) here, treating
the PRD's "Entrinnen" as a wiki transcription error, the same kind of
correction `import_barbar_seereauber.py`'s own docstring documents for its
Fallengespür/Gefahreninstinkt adaptation. Ausweichschritt's own bonus scales
"+1 alle vier Stufen" starting at 2nd, the exact cadence Kämpfer's Tapferkeit
already uses (2/6/10/14/18) — replaces all five Tapferkeit grants, one per
level, same repeated-grant shape `import_barbar_seereauber.py` uses for
Wilder Seemann/Gefahreninstinkt. Zweifacher Trick (13th, expanded 17th) is
one named ability granted at both levels, replacing that level's own
Waffentraining grant (3 at 13th, 4 at 17th) — same shape again.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database — run the seed scripts afterward):
    cd backend && python scripts/import_ork_archetypes.py
    python -m app.seed.class_seed
    python -m app.seed.class_ability_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("6b6f7a6c-6e1a-4a8d-9b7d-1e0a8c9d3f42")

HEXE_ID = "2ac0bd62-8800-4db8-9395-22b4391a9646"
KAEMPFER_ID = "f40316a4-b4b5-4f28-9e5c-ae0aec21bb50"

# Hexe grant this archetype replaces (base_class_ability_grants.json,
# base_class_id = Hexe): the level-1 "you pick a hex" slot.
HEXERELEVEL1_GRANT_ID = "a341733e-317a-4695-bf45-9c3fab9f0ce0"

# Kämpfer grants this archetype replaces (base_class_ability_grants.json,
# base_class_id = Kämpfer).
TAPFERKEIT_GRANT_IDS = {
    2: "a83476c9-17d9-4678-b05b-8e4fb002b858",
    6: "a7c039ea-bcdb-45e9-bc82-96af4ad006a5",
    10: "4fbfe06e-fdf6-42e8-933b-6aee147da13f",
    14: "d8735feb-f2cb-4ff3-9ab3-6b1ee0defc15",
    18: "db8e41f2-eb1e-454d-98d5-70265eaa306a",
}
WAFFENTRAINING_1_GRANT_ID = "d92f734e-3299-4465-9400-c47bad760815"  # level 5
WAFFENTRAINING_2_GRANT_ID = "3276b075-2edb-4e39-af6f-1c7bddd806c7"  # level 9
WAFFENTRAINING_3_GRANT_ID = "d84b8a7e-c874-4074-b1d6-c2526cc63555"  # level 13
WAFFENTRAINING_4_GRANT_ID = "7fdbd3f5-1182-466c-ba8d-e80b6fa8771a"  # level 17

# (name, levels, description, replaces_grant_ids_per_level) —
# replaces_grant_ids_per_level is either [] (nothing replaced), a single-item
# list reused for every level, or one entry per level (paired positionally,
# same convention `import_barbar_seereauber.py` uses for its per-level lists).
NARBIGER_HEXENDOKTOR_FEATURES: list[tuple[str, list[int], str, list[str]]] = [
    (
        "Konstitutionsabhängig",
        [1],
        "Ein Narbiger Hexendoktor benutzt als Zauberattribut Konstitution anstelle von Intelligenz. "
        "Ebenso bestimmt er die Effekte seiner Hexereien anhand seiner Konstitution anstelle seiner "
        "Intelligenz.",
        [],
    ),
    (
        "Hexennarbe",
        [1],
        "Wenn ein Narbiger Hexendoktor eine Hexerei erlernt, muss er ein Symbol in seine Hautritzen "
        "ritzen oder brennen, um diese Hexerei darzustellen. Er kann diese Narbe mit gewöhnlichen oder "
        "magischen Mitteln verbergen, sie aber nicht dauerhaft entfernen.",
        [],
    ),
    (
        "Fetischmaske",
        [1],
        "(ÜF) Mit der 1. Stufe geht ein Narbiger Hexendoktor eine Bindung mit einer Holzmaske ein. Wenn "
        "er an Macht gewinnt, wird diese Maske aufgrund der Bindung stetig hässlicher und grotesker, da "
        "sie den selbstzugefügten Schmerz aufnimmt, welcher in seine Magie eingeflochten ist. Seine "
        "Zauber entstammen den Einsichten, welche ihm sein Schutzherr verleiht, während er die "
        "Schnitte, Verbrennungen und anderen Verstümmelungen erträgt, die er sich selbst zufügt. Die "
        "Fetischmaske funktioniert hinsichtlich Vorbereiten und Erhalten von Zaubern wie ein "
        "Hexenvertrauter. Ein Narbiger Hexendoktor kommuniziert nicht täglich mit seinem Vertrauten, um "
        "seine Zauber vorzubereiten, sondern hängt die Maske an eine Wand, einen Ast oder eine andere "
        "Oberfläche und meditiert über die Schmerzen, die sie repräsentiert. Wenn ein Narbiger "
        "Hexendoktor seine Fetischmaske trägt, erhält er einen Situationsbonus von +2 auf "
        "Fertigkeitswürfe für Einschüchtern und Heilkunde und einen Bonus von +2 auf Rettungswürfe "
        "gegen Effekte der Kategorie Schmerz oder die Schmerzen hervorrufen. Sollte die Maske zerstört "
        "werden, kann der Narbige Hexendoktor eine neue Fetischmaske anfertigen, welche fast sofort "
        "das schockierende Aussehen ihres Vorgängers annimmt. Dies kostet dasselbe an Gold und Zeit wie "
        "das Ersetzen eines toten Hexenvertrauten. Mit der 5. Stufe erlangt ein Narbiger Hexendoktor "
        "die Fähigkeit, seine Maske mit magischen Eigenschaften zu versehen, als besäße er das Talent "
        "Wundersamen Gegenstand herstellen. Dieses Klassenmerkmal funktioniert ansonsten wie "
        "Hexenvertrauter und ersetzt dieses Klassenmerkmal.",
        [],
    ),
    (
        "Narbenschild",
        [1],
        "(ÜF) Mit der 1. Stufe erlernt ein Narbiger Hexendoktor, wie er seine verunstaltete Haut "
        "verhärten kann. Er erhält einen Verzauberungsbonus auf seinen natürlichen Rüstungsbonus in "
        "Höhe seiner ½ Klassenstufe (Minimum +1). Er kann diese Fähigkeit täglich für eine Anzahl von "
        "Minuten in Höhe seiner Hexenstufe einsetzen. Diese Minuten müssen nicht zusammenhängend sein, "
        "die Wirkungsdauer wird aber in Einheiten zu jeweils 1 Minute abgerechnet. Dieses "
        "Klassenmerkmal ersetzt die Hexerei, welche eine Hexe mit der 1. Stufe erhält.",
        [HEXERELEVEL1_GRANT_ID],
    ),
]

RAUFBOLD_FEATURES: list[tuple[str, list[int], str, list[str] | dict[int, str]]] = [
    (
        "Ausweichschritt",
        [2, 6, 10, 14, 18],
        "(AF) Mit der 2. Stufe erlernt ein Raufbold, wie er seinen Gegnern entgehen kann, wenn diese "
        "auf seine Kampfmanöver reagieren. Er erhält einen Ausweichbonus von +1 auf seine RK gegen im "
        "Rahmen eines Kampfmanövers selbstprovozierte Gelegenheitsangriffe. Dieser Bonus steigt um +1 "
        "pro weitere vier Stufen jenseits der 2. Stufe. Dieses Klassenmerkmal ersetzt Tapferkeit.",
        TAPFERKEIT_GRANT_IDS,
    ),
    (
        "Manövertraining",
        [5],
        "(AF) Mit der 5. Stufe wird ein Raufbold zum Meister der Schmutzigen Tricks. Er erhält einen "
        "Bonus von +2 auf Kampfmanöverwürfe für Schmutzige Tricks und einen Bonus von +2 auf seine KMV "
        "gegen Schmutzige Tricks. Dieses Klassenmerkmal ersetzt Waffentraining 1.",
        [WAFFENTRAINING_1_GRANT_ID],
    ),
    (
        "Schneller Trick",
        [9],
        "(AF) Mit der 9. Stufe hat ein Raufbold seine Schmutzigen Tricks derart perfektioniert, dass er "
        "ein solches Kampfmanöver als Angriff statt als Standard-Aktion ausführen kann. Dieses "
        "Klassenmerkmal ersetzt Waffentraining 2.",
        [WAFFENTRAINING_2_GRANT_ID],
    ),
    (
        "Zweifacher Trick",
        [13, 17],
        "(AF) Mit der 13. Stufe kann ein Raufbold mit einem Kampfmanöver für Schmutzige Tricks seinem "
        "Ziel zwei unterschiedliche Zustände zufügen. Jeder davon benötigt eine eigene Aktion, um ihn "
        "aufzuheben. Mit der 17. Stufe kann er drei unterschiedliche Zustände zufügen. Dieses "
        "Klassenmerkmal ersetzt Waffentraining 3 und 4.",
        {13: WAFFENTRAINING_3_GRANT_ID, 17: WAFFENTRAINING_4_GRANT_ID},
    ),
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


def import_archetype(
    *,
    archetype_name: str,
    parent_class_id: str,
    features: list[tuple[str, list[int], str, list[str] | dict[int, str]]],
    classes: list[dict],
    abilities: list[dict],
    grants: list[dict],
    replacements: list[dict],
) -> str:
    archetype_id = uid("ork-archetype", archetype_name, parent_class_id)

    if not any(c["id"] == archetype_id for c in classes):
        classes.append(
            {
                "id": archetype_id,
                "name": archetype_name,
                "hit_dice": None,
                "arch_class_of": parent_class_id,
                "casting_ability": None,
                "spell_tradition": None,
                "bab_progression": None,
                "fort_save": None,
                "ref_save": None,
                "wil_save": None,
                "skill_points_base": None,
            }
        )

    own_ability_ids = {uid("ork-archetype-ability", archetype_id, name) for name, _levels, _desc, _rep in features}
    for i in range(len(abilities) - 1, -1, -1):
        if abilities[i]["id"] in own_ability_ids:
            abilities.pop(i)

    def replaced_grant_id_for(replaces: list[str] | dict[int, str], level: int) -> str | None:
        if isinstance(replaces, dict):
            return replaces.get(level)
        if len(replaces) == 1:
            return replaces[0]
        return None

    for name, levels, description, replaces in features:
        ability_id = uid("ork-archetype-ability", archetype_id, name)
        abilities.append({"id": ability_id, "name": name, "description": description})

        for level in levels:
            grant_id = uid("ork-archetype-grant", ability_id, str(level))
            grants[:] = [g for g in grants if g["id"] != grant_id]
            grants.append(
                {
                    "id": grant_id,
                    "base_class_id": archetype_id,
                    "ability_id": ability_id,
                    "option_choice_id": None,
                    "level": level,
                }
            )

            replaced_grant_id = replaced_grant_id_for(replaces, level)
            if replaced_grant_id is not None:
                replacement_id = uid("ork-archetype-replacement", ability_id, replaced_grant_id)
                replacements[:] = [r for r in replacements if r["id"] != replacement_id]
                replacements.append(
                    {
                        "id": replacement_id,
                        "archetype_class_id": archetype_id,
                        "ability_id": ability_id,
                        "replaces_grant_id": replaced_grant_id,
                    }
                )

    return archetype_id


def main() -> None:
    classes = load("base_classes.json")
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    replacements = load("base_class_ability_replacements.json")

    hexendoktor_id = import_archetype(
        archetype_name="Narbiger Hexendoktor",
        parent_class_id=HEXE_ID,
        features=NARBIGER_HEXENDOKTOR_FEATURES,
        classes=classes,
        abilities=abilities,
        grants=grants,
        replacements=replacements,
    )
    raufbold_id = import_archetype(
        archetype_name="Raufbold",
        parent_class_id=KAEMPFER_ID,
        features=RAUFBOLD_FEATURES,
        classes=classes,
        abilities=abilities,
        grants=grants,
        replacements=replacements,
    )

    save("base_classes.json", classes)
    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)
    save("base_class_ability_replacements.json", replacements)

    print("Narbiger Hexendoktor class id:", hexendoktor_id)
    print("Raufbold class id:", raufbold_id)
    print("Done.")


if __name__ == "__main__":
    main()
