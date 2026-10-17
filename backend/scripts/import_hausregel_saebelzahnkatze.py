"""House rule (2026-10-17, decided by the project owner): the Säbelzahnkatze
is an animal companion species. Its German source, Ausbauregeln X: Wildnis
(Ultimate Wilderness), isn't on prd.5footstep.de, so — unlike every other
species — its values come from the English entry
(https://www.d20pfsrd.com/classes/core-classes/druid/animal-companions,
"Saber-Toothed Cat"); the ability names reuse the German Monsterhandbuch
rows the animal companion importer already seeded (Ergreifen, Anspringen,
Dämmersicht, Geruchssinn). Documented in `requirements_v2.md`, "Hausregeln".

    Starting Statistics: Size Medium; Speed 40 ft.; AC +1 natural armor;
    Attack 2 claws (1d4 plus grab); Ability Scores Str 15, Dex 15, Con 13,
    Int 2, Wis 13, Cha 8; Special Attacks saber-toothed bite (1d10 bite
    attack, only on a grapple check to deal damage); Special Qualities
    low-light vision, scent.
    7th-Level Advancement: Size Large; AC +2 natural armor; Attack 2 claws
    (1d6 plus grab); Ability Scores Str +8, Dex –2, Con +4; Special Attacks
    pounce, saber-toothed bite (2d8 bite attack, only on a grapple check to
    deal damage).

Allowed wherever the Druide's full species list is (every slot allowing all
17 PRD species: Druide, Kleriker Tier-Domäne, Hexenmeister Sylvanische
Blutlinie, Druide as Sekundärklasse) and for the Löwenschamane besides the
lion. The name carries "(Hausregel)" so players see it in the picker.

Run after `import_companion_species.py`, `import_druide_tierschamanen.py`
and `build_secondary_class_druide_magier_seed.py`:
    cd backend && python scripts/import_hausregel_saebelzahnkatze.py
    python -m app.seed.race_seed && python -m app.seed.companion_seed
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_companion_species import DAEMMERSICHT_ABILITY_ID  # noqa: E402
from import_companion_species import uid as companion_uid  # noqa: E402

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
ID_NAMESPACE = uuid.UUID("6e1a4c8b-2d9f-4f3a-b7e5-0c8d2a6f4e91")

NAME = "Säbelzahnkatze (Hausregel)"
SOURCE = "Hausregel: Ausbauregeln X – Wildnis (nicht im PRD; Werte nach d20pfsrd \"Saber-Toothed Cat\")"
SAEBELZAHNBISS_TEXT = (
    "Säbelzahnbiss (AF): Die Säbelzahnkatze kann diesen Biss nur bei einem Ringkampfwurf einsetzen, um Schaden "
    "zu verursachen (1W10, ab dem Aufstieg auf der 7. Stufe 2W8). Etwas kleiner als der wildere Säbelzahntiger, "
    "ist die Säbelzahnkatze dennoch ein beeindruckendes Raubtier."
)
LOEWENSCHAMANE_TRIGGER = "Tiergefährte (Löwenschamane)"


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


def attack(name: str, count: int, dice: str, damage_type: str, note: str | None, alternative: bool) -> dict:
    return {"name": name, "count": count, "dice": dice, "damage_type": damage_type, "secondary": False,
            "note": note, "alternative": alternative}


def main() -> None:
    race_id = uid("species", NAME)
    races = load("base_races.json")
    races.append(
        {
            "id": race_id,
            "code": "companion-saebelzahnkatze",
            "name": NAME,
            "short_description": f"Tiergefährte ({SOURCE})",
            "companion_kind": "animal_companion",
            "creature_type": "Tier",
            "source": SOURCE,
        }
    )
    race_abilities = load("base_race_abilities.json")
    bite_ability_id = uid("ability", "Säbelzahnbiss")
    race_abilities.append({"id": bite_ability_id, "name": "Säbelzahnbiss", "description": SAEBELZAHNBISS_TEXT})

    ability = {
        "Dämmersicht": DAEMMERSICHT_ABILITY_ID,
        "Geruchssinn": companion_uid("species-ability", "Geruchssinn"),
        "Ergreifen": companion_uid("species-ability", "Ergreifen"),
        "Anspringen": companion_uid("species-ability", "Anspringen"),
        "Säbelzahnbiss": bite_ability_id,
    }
    known = {a["id"] for a in race_abilities}
    assert all(ability_id in known for ability_id in ability.values()), "run import_companion_species.py first"

    grapple_only = "nur bei einem Ringkampfwurf, um Schaden zu verursachen"
    stages = [
        {
            "id": uid("stage", race_id, "1"),
            "race_id": race_id,
            "level": 1,
            "size": "Mittelgroß",
            "natural_armor": 1,
            "ability_scores": {"ST": 15, "GE": 15, "KO": 13, "IN": 2, "WE": 13, "CH": 8},
            "speeds": {"land": 12},
            "fly_maneuverability": None,
            "natural_attacks": [
                attack("Klauen", 2, "1W4", "H/W", "plus Ergreifen", False),
                attack("Säbelzahnbiss", 1, "1W10", "H/S/W", grapple_only, True),
            ],
            "abilities": ["Dämmersicht", "Geruchssinn", "Ergreifen", "Säbelzahnbiss"],
        },
        {
            "id": uid("stage", race_id, "7"),
            "race_id": race_id,
            "level": 7,
            "size": "Groß",
            "natural_armor": 2,
            "ability_scores": {"ST": 8, "GE": -2, "KO": 4},
            "speeds": None,
            "fly_maneuverability": None,
            "natural_attacks": [
                attack("Klauen", 2, "1W6", "H/W", "plus Ergreifen", False),
                attack("Säbelzahnbiss", 1, "2W8", "H/S/W", grapple_only, True),
            ],
            "abilities": ["Anspringen"],
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

    # Slots: every one allowing the Druide's full PRD list, plus the Löwenschamane's.
    druid_species = {r["id"] for r in races if r.get("source") == "Grundregelwerk: Druide"}
    assert len(druid_species) == 17, len(druid_species)
    slot_grants = load("base_companion_slot_grants.json")
    slot_species = load("base_companion_slot_species.json")
    ability_name_by_id = {a["id"]: a["name"] for a in load("base_class_abilities.json")}
    target_slots = [
        grant["id"]
        for grant in slot_grants
        if druid_species <= {s["race_id"] for s in slot_species if s["slot_grant_id"] == grant["id"]}
        or ability_name_by_id.get(grant["class_ability_id"]) == LOEWENSCHAMANE_TRIGGER
    ]
    for slot_id in target_slots:
        slot_species.append(
            {"id": uid("slot-species", slot_id), "slot_grant_id": slot_id, "race_id": race_id,
             "master_sizes": None, "min_level": None}
        )
        print("allowed for", ability_name_by_id[next(g for g in slot_grants if g["id"] == slot_id)["class_ability_id"]])

    save("base_races.json", races)
    save("base_race_abilities.json", race_abilities)
    save("base_companion_species_stages.json", stage_rows)
    save("base_companion_species_stage_abilities.json", stage_abilities)
    save("base_companion_slot_species.json", slot_species)


if __name__ == "__main__":
    main()
