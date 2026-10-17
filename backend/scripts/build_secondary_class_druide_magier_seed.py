"""Builds the Druide's and the Magier's rows of
`../app/fixtures/seed/base_secondary_class_ability_grants.json` (the
"Sekundärklasse" alternate rule, roadmap slice 9) — done as part of roadmap
slice 10's remaining items, because both tracks give a companion: the
Druide an animal companion from 7th level, the Magier a familiar from 3rd.

Source text (http://prd.5footstep.de/Alternativregeln/Fertigkeiten/
AlternativesSystemfuerCharakteremitKlassenkombinationen, fetched
2026-10-17) — quoted in `DRUIDE_TIERS`/`MAGIER_TIERS` below.

Every tier uses the character level as effective class level (offset 0),
so the one synthetic level `rules/secondary_class.py` keeps per class is
right for all of them (e.g. Tierempathie at 3rd). The one exception is the
Druide's animal companion ("Charakterstufe -4" from 7th, full level from
11th): it doesn't ride on that synthetic Druide level — which would drag
Tierempathie down by 4 as well — but gets two trigger abilities of its own,
"Tiergefährte (Sekundärklasse Druide)" and "Verbesserter Tiergefährte
(Sekundärklasse Druide)", which `build_companion_level_sources.py` turns
into two `character_level` sources (offset −4 / 0) sharing a
`stack_group`, so the better one counts. This script also writes the
animal-companion slot for the first trigger (the Druide's species list).

The Magier's familiar reuses the existing "Vertrauter (Magier)" trigger:
its source counts Magier level, which the Sekundärklasse sets to the
character level. The Magier's 1st-level "Schule der Magie" is the existing
`school` option group, already flagged as the Sekundärklasse's initial pick.

Abilities without anything computable (Verhaltenskodex, the Druide's
Tiergestalt tiers, the Magier's school powers, Zaubertrick, Entdeckung) are
descriptive rows with the PRD text.

Run with the project venv active (writes fixture JSON only), then rebuild
the level sources and seed:
    cd backend && python scripts/build_secondary_class_druide_magier_seed.py
    python scripts/build_companion_level_sources.py
    python -m app.seed.class_ability_seed && python -m app.seed.secondary_class_seed
    python -m app.seed.companion_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
ID_NAMESPACE = uuid.UUID("5d8e2f4a-6b1c-4e9d-a7f3-0c2b4e6d8f17")

TIEREMPATHIE_ABILITY_ID = "ebd5060b-066a-4bc0-bdfa-064222de85bf"
VERTRAUTER_MAGIER_ABILITY_ID = "91a0b27d-8fb2-5aca-93de-7d544354ece2"
DRUIDE_SLOT_TRIGGER_ID = "1e421552-622f-583b-a8f9-62944ace3dc5"  # "Tiergefährte (Druide)"

DRUIDE_TIERS = [
    (1, "Verhaltenskodex (Sekundärklasse Druide)",
     "Mit der 1. Stufe erhält er Druidisch als Bonussprache und muss sich dem Verhaltenskodex der Druiden "
     "unterwerfen: Respektiere die Natur, lehre Druidisch keinen Außenstehenden, trage keine Metallrüstungen usw."),
    (3, None, None),  # Tierempathie: the existing row, effective Druide level = character level
    (7, "Tiergefährte (Sekundärklasse Druide)",
     "Mit der 7. Stufe erhält er einen Tiergefährten, seine effektive Druidenstufe für dieses Klassenmerkmal ist "
     "seine Charakterstufe -4. Diese effektive Druidenstufe kann durch keine andere Fähigkeit außer Verbesserter "
     "Tiergefährte jemals verbessert werden."),
    (11, "Verbesserter Tiergefährte (Sekundärklasse Druide)",
     "Ab der 11. Stufe entspricht seine effektive Druidenstufe für das Klassenmerkmal Tiergefährte seiner "
     "Charakterstufe."),
    (15, "Tiergestalt (Sekundärklasse Druide)",
     "Mit der 15. Stufe erhält er die Fähigkeit, sich zwei Mal am Tag für jeweils maximal 1 Stunde pro "
     "Charakterstufe in ein Tier der Größenkategorie Klein oder Mittelgroß zu verwandeln."),
    (19, "Mächtige Tiergestalt (Sekundärklasse Druide)",
     "Beginnend mit der 19. Stufe verbessert sich seine Fähigkeit Tiergestalt: ihm stehen darin nun die Optionen "
     "eines Druiden der 6. Stufe zur Verfügung, ferner kann er sie drei Mal am Tag einsetzen."),
]
MAGIER_TIERS = [
    (1, "Schule der Magie (Sekundärklasse Magier)",
     "Auf der 1. Stufe wählt er eine Schule der Magie aus, in welcher er sich spezialisiert. Hinsichtlich aller "
     "Schulfähigkeiten dieser Schule entspricht seine effektive Magierstufe seiner Charakterstufe."),
    (3, None, None),  # Vertrauter: the existing "Vertrauter (Magier)" trigger
    (7, "Schulfähigkeit (Sekundärklasse Magier)",
     "Ab der 7. Stufe erhält er die Schulfähigkeiten der 1. Stufe seiner gewählten Schule. Sollte eine dieser "
     "Fähigkeiten mit der 20. Stufe einen zusätzlichen Effekt verleihen, so erhält er diesen zusätzlichen Effekt "
     "nicht."),
    (11, "Zaubertrick (Sekundärklasse Magier)",
     "Mit der 11. Stufe wählt er einen Zaubertrick (Magierzauber des Grades 0) seiner gewählten Schule, sofern er "
     "über einen Intelligenzwert von 10 oder höher verfügt; er kann diesen Zaubertrick beliebig oft einsetzen und "
     "hinsichtlich dieser Fähigkeit entspricht seine effektive Magierstufe seiner Charakterstufe, das "
     "Schlüsselattribut ist Intelligenz."),
    (15, "Entdeckung (Sekundärklasse Magier)",
     "Auf der 15. Stufe erhält er eine Arkane Entdeckung oder ein Magierbonustalent. Hinsichtlich dieser "
     "Fähigkeit entspricht seine effektive Magierstufe seiner Charakterstufe."),
    (19, "Mächtige Schulfähigkeit (Sekundärklasse Magier)",
     "Mit der 19. Stufe erhält er die Schulfähigkeit der 8. Stufe seiner gewählten Schule."),
]
EXISTING_ABILITY_BY_CLASS_LEVEL = {("Druide", 3): TIEREMPATHIE_ABILITY_ID, ("Magier", 3): VERTRAUTER_MAGIER_ABILITY_ID}


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
    class_ids = {c["name"]: c["id"] for c in load("base_classes.json") if c["arch_class_of"] is None}
    abilities = load("base_class_abilities.json")
    grants = load("base_secondary_class_ability_grants.json")
    for class_name, tiers in (("Druide", DRUIDE_TIERS), ("Magier", MAGIER_TIERS)):
        class_id = class_ids[class_name]
        for level, name, description in tiers:
            if name is None:
                ability_id = EXISTING_ABILITY_BY_CLASS_LEVEL[(class_name, level)]
            else:
                ability_id = uid("ability", name)
                abilities.append({"id": ability_id, "name": name, "description": description})
            grants.append(
                {
                    "id": uid("secondary-grant", class_id, str(level)),
                    "secondary_base_class_id": class_id,
                    "character_level": level,
                    "ability_id": ability_id,
                    "effective_level_offset": 0,
                    "effective_level_divisor": 1,
                    "effective_level_minimum": None,
                    "option_group_key": None,
                    "option_choice_id": None,
                }
            )
            print(f"{class_name} {level}: {name or ability_id}")
    save("base_class_abilities.json", abilities)
    save("base_secondary_class_ability_grants.json", grants)

    # The Druide-Sekundärklasse companion slot, same species as the Druide's.
    trigger_id = uid("ability", "Tiergefährte (Sekundärklasse Druide)")
    druide_slot = next(g for g in load("base_companion_slot_grants.json") if g["class_ability_id"] == DRUIDE_SLOT_TRIGGER_ID)
    slot_grants = load("base_companion_slot_grants.json")
    slot_species = load("base_companion_slot_species.json")
    grant_id = uid("slot", trigger_id)
    slot_grants.append(
        {"id": grant_id, "class_ability_id": trigger_id, "track": "animal_companion", "slot_key": "primary",
         "level_offset": 0, "divisor": 1, "minimum": None}
    )
    for row in [r for r in slot_species if r["slot_grant_id"] == druide_slot["id"]]:
        slot_species.append(
            {"id": uid("slot-species", grant_id, row["race_id"]), "slot_grant_id": grant_id, "race_id": row["race_id"],
             "master_sizes": row["master_sizes"], "min_level": row["min_level"]}
        )
    save("base_companion_slot_grants.json", slot_grants)
    save("base_companion_slot_species.json", slot_species)


if __name__ == "__main__":
    main()
