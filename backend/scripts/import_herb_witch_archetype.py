"""Import the "Kräuterhexe" (Herb Witch) Hexe archetype from
https://www.d20pfsrd.com/classes/base-classes/witch/archetypes/paizo-witch-archetypes/herb-witch-witch-archetype
into the seed JSON files.

Herb Witch's only named, replacing class feature is Herb Lore (1st level,
replaces the witch's normal 1st-level hex) — modeled here as "Kräuterkunde",
same shape as `import_ork_archetypes.py`'s Narbenschild-replaces-Hexerei-
level-1 pattern. The archetype's other two restrictions from the source text
(patron must be nature-aligned; must select Cauldron as one of her hexes at
2nd level) aren't separate class features — nothing is gained or replaced by
them — so they're folded into Kräuterkunde's own description as prose,
consistent with how this app already treats non-mechanical requirements
(e.g. Narbiger Hexendoktor's Hexennarbe is flavor-only text, not a grant).

Cauldron itself ("Kessel") did not previously exist in this app's hex
catalog at all (only ~27 of the many published witch hexes are seeded here)
even though Herb Witch requires it, so this script also adds it as an
ordinary selectable hex under the Hexe root class's existing `hexerei`
option group (id `31954213-...`) — a real witch hex per
https://www.d20pfsrd.com/classes/base-classes/witch/hexes/hexes/common-hexes/hex-cauldron-ex/
(Brew Potion as a bonus feat, ignoring its normal caster-level-3
prerequisite, plus a +4 insight bonus on Craft (alchemy) checks), not an
Herb-Witch-exclusive ability, so any witch can pick it.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database — run the seed scripts afterward):
    cd backend && python scripts/import_herb_witch_archetype.py
    python -m app.seed.class_seed
    python -m app.seed.class_ability_seed
    python -m app.seed.class_option_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("2f6c9b3a-6a2b-4e0a-9d3c-7a5e1b8c4d90")

HEXE_ID = "2ac0bd62-8800-4db8-9395-22b4391a9646"

# Hexe grant this archetype replaces (base_class_ability_grants.json,
# base_class_id = Hexe): the level-1 "you pick a hex" slot. Same id
# `import_ork_archetypes.py` uses for Narbenschild.
HEXERELEVEL1_GRANT_ID = "a341733e-317a-4695-bf45-9c3fab9f0ce0"

# Hexe's `hexerei` option group (base_class_option_groups.json).
HEXEREI_GROUP_ID = "31954213-c209-4009-ad1b-5fc1d5e538d4"

# Trank brauen (Brew Potion), base_feats.json.
TRANK_BRAUEN_FEAT_ID = "7e594909-cd3f-53fe-aa9d-73f3a993deaa"

KRAEUTERKUNDE_DESCRIPTION = (
    "Eine Kräuterhexe muss einen Schutzherren wählen, der der Natur verbunden ist: Ahnen, Tiere, "
    "Tod, Elemente, Heilung, Seuche, Pflanzen, Stärke, Zeit, Wasser, Winter oder Weisheit.\n\n"
    "(AF) Mit der 1. Stufe kann eine Kräuterhexe Fertigkeitswürfe für Beruf (Kräuterkundige) "
    "anstelle von Handwerk (Alchemie) einsetzen, etwa um Tränke zu identifizieren oder "
    "alchemistische Erzeugnisse aller Art herzustellen, und erhält dabei einen Bonus in Höhe ihrer "
    "halben Hexenstufe auf solche Beruf (Kräuterkundige)-Würfe. Durch einstündige Kommunion mit "
    "ihrem Vertrauten bereitet sie täglich eine Anzahl von Heilmitteln in Höhe von 3 + ihrem "
    "Intelligenz-Modifikator (mindestens 1) vor. Ein Heilmittel wird unwirksam, sobald es sich "
    "nicht mehr im Besitz der Kräuterhexe befindet, spätestens jedoch, sobald sie die Heilmittel "
    "des nächsten Tages vorbereitet. Als Standardaktion kann eine Kräuterhexe einer Kreatur ein "
    "Heilmittel verabreichen, um damit eine Krankheit oder ein Gift zu heilen oder die Zustände "
    "Geblendet, Taub, Erschöpft, Übelkeit oder Kränkelnd zu beseitigen; dies erfordert einen "
    "erfolgreichen Beruf (Kräuterkundige)-Wurf gegen die Schwierigkeit des Rettungswurfs der "
    "Krankheit bzw. des Gifts oder eine für den jeweiligen Zustand angemessene Schwierigkeit. "
    "Dieses Klassenmerkmal ersetzt die Hexerei, welche eine Hexe mit der 1. Stufe erhält.\n\n"
    "Mit der 2. Stufe muss eine Kräuterhexe Kessel als eine ihrer Hexereien wählen. Empfehlenswerte "
    "weitere Hexereien sind Glück und Heilen, empfehlenswerte Mächtige Hexereien sind Mächtiges "
    "Heilen und Wetterkontrolle, empfehlenswert als Große Hexerei ist Gabe des Lebens."
)

KESSEL_DESCRIPTION = (
    "(AF) Die Hexe erhält Trank brauen als Bonusfeat, ungeachtet dessen üblicher Voraussetzung "
    "einer Zauberstufe von mindestens 3, sowie einen Einsichtsbonus von +4 auf Fertigkeitswürfe "
    "für Handwerk (Alchemie)."
)


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


def add_kessel_hex(
    *,
    abilities: list[dict],
    grants: list[dict],
    choices: list[dict],
    granted_feats: list[dict],
) -> str:
    ability_id = uid("herb-witch-hex-ability", "Kessel")
    abilities[:] = [a for a in abilities if a["id"] != ability_id]
    abilities.append({"id": ability_id, "name": "Kessel", "description": KESSEL_DESCRIPTION})

    choice_id = uid("herb-witch-hex-choice", "Kessel")
    choices[:] = [c for c in choices if c["id"] != choice_id]
    choices.append({"id": choice_id, "group_id": HEXEREI_GROUP_ID, "name": "Kessel"})

    grant_id = uid("herb-witch-hex-grant", "Kessel")
    grants[:] = [g for g in grants if g["id"] != grant_id]
    grants.append(
        {
            "id": grant_id,
            "base_class_id": HEXE_ID,
            "ability_id": ability_id,
            "option_choice_id": choice_id,
            "level": 1,
        }
    )

    granted_feat_id = uid("herb-witch-hex-granted-feat", "Kessel", "Trank brauen")
    granted_feats[:] = [f for f in granted_feats if f["id"] != granted_feat_id]
    granted_feats.append({"id": granted_feat_id, "ability_id": ability_id, "feat_id": TRANK_BRAUEN_FEAT_ID})

    return ability_id


def add_archetype(
    *,
    classes: list[dict],
    abilities: list[dict],
    grants: list[dict],
    replacements: list[dict],
) -> str:
    archetype_id = uid("herb-witch-archetype", HEXE_ID)

    classes[:] = [c for c in classes if c["id"] != archetype_id]
    classes.append(
        {
            "id": archetype_id,
            "name": "Kräuterhexe",
            "hit_dice": None,
            "arch_class_of": HEXE_ID,
            "casting_ability": None,
            "spell_tradition": None,
            "bab_progression": None,
            "fort_save": None,
            "ref_save": None,
            "wil_save": None,
            "skill_points_base": None,
        }
    )

    ability_id = uid("herb-witch-archetype-ability", archetype_id, "Kräuterkunde")
    abilities[:] = [a for a in abilities if a["id"] != ability_id]
    abilities.append({"id": ability_id, "name": "Kräuterkunde", "description": KRAEUTERKUNDE_DESCRIPTION})

    grant_id = uid("herb-witch-archetype-grant", ability_id, "1")
    grants[:] = [g for g in grants if g["id"] != grant_id]
    grants.append(
        {
            "id": grant_id,
            "base_class_id": archetype_id,
            "ability_id": ability_id,
            "option_choice_id": None,
            "level": 1,
        }
    )

    replacement_id = uid("herb-witch-archetype-replacement", ability_id, HEXERELEVEL1_GRANT_ID)
    replacements[:] = [r for r in replacements if r["id"] != replacement_id]
    replacements.append(
        {
            "id": replacement_id,
            "archetype_class_id": archetype_id,
            "ability_id": ability_id,
            "replaces_grant_id": HEXERELEVEL1_GRANT_ID,
        }
    )

    return archetype_id


def main() -> None:
    classes = load("base_classes.json")
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    replacements = load("base_class_ability_replacements.json")
    choices = load("base_class_option_choices.json")
    granted_feats = load("base_class_ability_granted_feats.json")

    add_kessel_hex(abilities=abilities, grants=grants, choices=choices, granted_feats=granted_feats)
    archetype_id = add_archetype(classes=classes, abilities=abilities, grants=grants, replacements=replacements)

    save("base_classes.json", classes)
    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)
    save("base_class_ability_replacements.json", replacements)
    save("base_class_option_choices.json", choices)
    save("base_class_ability_granted_feats.json", granted_feats)

    print("Kräuterhexe class id:", archetype_id)
    print("Done.")


if __name__ == "__main__":
    main()
