"""House rule (2026-10-28, requested by the project owner): the Grizzlybär is
an animal companion species. Same case as `import_hausregel_saebelzahnkatze.py`:
its German source, Ausbauregeln X: Wildnis (Ultimate Wilderness, p. 179),
isn't on prd.5footstep.de, so its values come from the English entry
(https://www.aonprd.com/DruidCompanions.aspx?ItemName=Grizzly%20Bear); the
ability names reuse the German Monsterhandbuch rows the animal companion
importer already seeded (Dämmersicht, Geruchssinn, Ergreifen).

    Starting Statistics: Size Medium; Speed 40 ft.; AC +1 natural armor;
    Attack bite (1d6), 2 claws (1d4); Ability Scores Str 17, Dex 13, Con 13,
    Int 2, Wis 13, Cha 6; Special Qualities low-light vision, scent.
    7th-Level Advancement: Size Large; AC +4 natural armor; Attack bite
    (1d8), 2 claws (1d6 plus grab); Ability Scores Str +4, Dex -2, Con +4.

Allowed wherever the Druide's full species list is (same slots as the
Säbelzahnkatze) and for the Bärenschamane besides the Bär. The name carries
"(Hausregel)" so players see it in the picker.

Run after `import_companion_species.py`, `import_druide_tierschamanen.py`
and `build_secondary_class_druide_magier_seed.py`:
    cd backend && python scripts/import_hausregel_grizzlybaer.py
    python -m app.seed.race_seed && python -m app.seed.companion_seed
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_companion_species import DAEMMERSICHT_ABILITY_ID  # noqa: E402
from import_companion_species import uid as companion_uid  # noqa: E402
from import_hausregel_saebelzahnkatze import attack, load, save  # noqa: E402

ID_NAMESPACE = uuid.UUID("2c7e9b14-5a8d-4f61-93e0-b4d6a1c8f257")

NAME = "Grizzlybär (Hausregel)"
SOURCE = "Hausregel: Ausbauregeln X – Wildnis (nicht im PRD; Werte nach aonprd \"Grizzly Bear\")"
BAERENSCHAMANE_TRIGGER = "Tiergefährte (Bärenschamane)"


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def main() -> None:
    race_id = uid("species", NAME)
    races = load("base_races.json")
    races.append(
        {
            "id": race_id,
            "code": "companion-grizzlybaer",
            "name": NAME,
            "short_description": f"Tiergefährte ({SOURCE})",
            "companion_kind": "animal_companion",
            "creature_type": "Tier",
            "source": SOURCE,
        }
    )

    ability = {
        "Dämmersicht": DAEMMERSICHT_ABILITY_ID,
        "Geruchssinn": companion_uid("species-ability", "Geruchssinn"),
        "Ergreifen": companion_uid("species-ability", "Ergreifen"),
    }
    known = {a["id"] for a in load("base_race_abilities.json")}
    assert all(ability_id in known for ability_id in ability.values()), "run import_companion_species.py first"

    stages = [
        {
            "id": uid("stage", race_id, "1"),
            "race_id": race_id,
            "level": 1,
            "size": "Mittelgroß",
            "natural_armor": 1,
            "ability_scores": {"ST": 17, "GE": 13, "KO": 13, "IN": 2, "WE": 13, "CH": 6},
            "speeds": {"land": 12},
            "fly_maneuverability": None,
            "natural_attacks": [
                attack("Biss", 1, "1W6", "H/S/W", None, False),
                attack("Klauen", 2, "1W4", "H/W", None, False),
            ],
            "abilities": ["Dämmersicht", "Geruchssinn"],
        },
        {
            "id": uid("stage", race_id, "7"),
            "race_id": race_id,
            "level": 7,
            "size": "Groß",
            "natural_armor": 4,
            "ability_scores": {"ST": 4, "GE": -2, "KO": 4},
            "speeds": None,
            "fly_maneuverability": None,
            "natural_attacks": [
                attack("Biss", 1, "1W8", "H/S/W", None, False),
                attack("Klauen", 2, "1W6", "H/W", "plus Ergreifen", False),
            ],
            "abilities": ["Ergreifen"],
        },
    ]
    stage_rows = load("base_companion_species_stages.json")
    stage_abilities = load("base_companion_species_stage_abilities.json")
    for stage in stages:
        names = stage.pop("abilities")
        stage_rows.append(stage)
        for name in names:
            stage_abilities.append(
                {"id": uid("stage-ability", stage["id"], name), "stage_id": stage["id"], "ability_id": ability[name]}
            )

    # Slots: every one allowing the Druide's full PRD list, plus the Bärenschamane's.
    druid_species = {r["id"] for r in races if r.get("source") == "Grundregelwerk: Druide"}
    assert len(druid_species) == 17, len(druid_species)
    slot_grants = load("base_companion_slot_grants.json")
    slot_species = load("base_companion_slot_species.json")
    ability_name_by_id = {a["id"]: a["name"] for a in load("base_class_abilities.json")}
    target_slots = [
        grant["id"]
        for grant in slot_grants
        if druid_species <= {s["race_id"] for s in slot_species if s["slot_grant_id"] == grant["id"]}
        or ability_name_by_id.get(grant["class_ability_id"]) == BAERENSCHAMANE_TRIGGER
    ]
    for slot_id in target_slots:
        slot_species.append(
            {"id": uid("slot-species", slot_id), "slot_grant_id": slot_id, "race_id": race_id,
             "master_sizes": None, "min_level": None}
        )
        print("allowed for", ability_name_by_id[next(g for g in slot_grants if g["id"] == slot_id)["class_ability_id"]])

    save("base_races.json", races)
    save("base_companion_species_stages.json", stage_rows)
    save("base_companion_species_stage_abilities.json", stage_abilities)
    save("base_companion_slot_species.json", slot_species)


if __name__ == "__main__":
    main()
