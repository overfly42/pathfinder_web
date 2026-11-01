"""House rule (2026-11-01, decided by the project owner): the animal
companion archetype "Elemental Companion" from Pathfinder Player Companion:
Plane-Hopper's Handbook — not on prd.5footstep.de (the PRD has no companion
archetypes at all), so the text is translated from the English entry
(https://www.d20pfsrd.com/classes/core-classes/druid/animal-companions/animal-companion-archetypes/elemental-companion-animal-companion-archetype/).
German names are the project's own. Documented in `requirements_v2.md`,
"Hausregeln".

The element is picked with the archetype and never changes, so each element
is its own archetype row ("Elementargefährte: Luft (Hausregel)", ...) with
three abilities of its own (Elementare Unterart at 1st, the lesser
manifestation at 2nd, the greater at 9th effective master level), all four
replacing Entrinnen, Verbessertes Entrinnen and Mehrfachangriff. The fire
companion's lesser manifestation grants Behände Bewegung (Nimble Moves) as
a bonus feat (`base_class_ability_granted_feats.json`). What the
abilities compute: `app/rules/classes/tiergefaehrte.py`.

Run with the project venv active:
    cd backend && python scripts/import_hausregel_elementargefaehrte.py
    python -m app.seed.class_ability_seed && python -m app.seed.class_ability_granted_feat_seed
    python -m app.seed.companion_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
ID_NAMESPACE = uuid.UUID("9b4e7d2a-3c1f-4a6e-8d5b-2f7c1e9a0b63")

SOURCE = (
    "Hausregel: Player Companion – Plane-Hopper's Handbook (nicht im PRD; übersetzt nach d20pfsrd "
    "\"Elemental Companion\")"
)
ARCHETYPE_TEXT = (
    "Das Herz dieses Gefährten schlägt mit urtümlicher elementarer Energie. Das Element wird mit dem Archetyp "
    "gewählt. Ersetzt Entrinnen, Verbessertes Entrinnen und Mehrfachangriff."
)
# Progression abilities (`base_companion_progression_abilities.json`) the
# archetype replaces.
ENTRINNEN_ID = "18d69c89-60be-54eb-8332-58f7e0187bf2"
VERBESSERTES_ENTRINNEN_ID = "d613a371-31dd-5b6f-8a86-1b72902cba96"
MEHRFACHANGRIFF_ID = "25d66f4b-94be-5d10-a40b-7a50c2848ed7"
BEHAENDE_BEWEGUNG_FEAT_ID = "ca9bec84-cdf4-41f2-a8a6-2ac9b6826d65"

LESSER_LEVEL = 2
GREATER_LEVEL = 9
LESSER_TAIL = " Ersetzt Entrinnen und Verbessertes Entrinnen."
GREATER_TAIL = " Ersetzt Mehrfachangriff."
# Element -> (lesser manifestation, greater manifestation).
ELEMENTS = {
    "Luft": (
        "(AF) Ab der 2. Stufe erhält der Gefährte eine Fehlschlagchance von 20 % gegen Fernkampfangriffe.",
        "(ÜF) Ab der 9. Stufe erhält der Gefährte eine Flugbewegungsrate von 6 m (gut). Kann er bereits fliegen, "
        "verbessert sich stattdessen seine Manövrierfähigkeit um eine Stufe.",
    ),
    "Erde": (
        "(AF) Ab der 2. Stufe erhält der Gefährte Schadensreduzierung 1/Adamant. Sie steigt um 1 für je 4 "
        "Druidenstufen seines Meisters.",
        "(ÜF) Ab der 9. Stufe überwinden die natürlichen Angriffe des Gefährten Schadensreduzierung, als wären "
        "sie Waffen aus Adamant, kaltem Eisen und Silber.",
    ),
    "Feuer": (
        "(AF) Ab der 2. Stufe kann der Gefährte ohne Abzüge durch Feuer, Nebel und Rauch sehen und erhält "
        "Behände Bewegung als Bonustalent.",
        "(ÜF) Ab der 9. Stufe verursacht ein natürlicher Angriff nach Wahl zusätzlich 1W6 Punkte Feuerschaden "
        "je 5 Trefferwürfel des Gefährten.",
    ),
    "Wasser": (
        "(AF) Ab der 2. Stufe kann der Gefährte unter Wasser atmen, erhält eine Schwimmbewegungsrate von 6 m und "
        "einen Ausweichbonus von +2 auf die RK gegen Gelegenheitsangriffe. Hat er bereits eine "
        "Schwimmbewegungsrate, steigt sie stattdessen um 3 m.",
        "(ÜF) Ab der 9. Stufe erhält ein natürlicher Nahkampfangriff nach Wahl die Sonderfähigkeit Stoßen (3 m).",
    ),
}


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def archetype_name(element: str) -> str:
    return f"Elementargefährte: {element} (Hausregel)"


def ability_names(element: str) -> tuple[str, str, str]:
    return (
        f"Elementare Unterart ({element})",
        f"Geringere elementare Manifestation ({element})",
        f"Größere elementare Manifestation ({element})",
    )


def load(filename: str) -> list[dict]:
    path = SEED_DIR / filename
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def upsert(filename: str, new_rows: list[dict]) -> None:
    rows = {row["id"]: row for row in load(filename)}
    rows.update({row["id"]: row for row in new_rows})
    (SEED_DIR / filename).write_text(
        json.dumps(list(rows.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    abilities, archetypes, archetype_abilities, replacements, granted_feats = [], [], [], [], []
    for element, (lesser, greater) in ELEMENTS.items():
        archetype_id = uid("archetype", element)
        archetypes.append(
            {"id": archetype_id, "name": archetype_name(element), "description": f"{ARCHETYPE_TEXT}\n\n{SOURCE}"}
        )
        subtype, lesser_name, greater_name = ability_names(element)
        for name, level, text in (
            (subtype, 1, f"(AF) Der Gefährte erhält die Unterart {element}."),
            (lesser_name, LESSER_LEVEL, lesser + LESSER_TAIL),
            (greater_name, GREATER_LEVEL, greater + GREATER_TAIL),
        ):
            ability_id = uid("ability", name)
            abilities.append({"id": ability_id, "name": name, "description": text})
            archetype_abilities.append(
                {"id": uid("archetype ability", element, name), "archetype_id": archetype_id, "level": level,
                 "ability_id": ability_id}
            )
        for replaced in (ENTRINNEN_ID, VERBESSERTES_ENTRINNEN_ID, MEHRFACHANGRIFF_ID):
            replacements.append(
                {"id": uid("replacement", element, replaced), "archetype_id": archetype_id, "ability_id": replaced}
            )
        if element == "Feuer":
            granted_feats.append(
                {"id": uid("granted feat", lesser_name), "ability_id": uid("ability", lesser_name),
                 "feat_id": BEHAENDE_BEWEGUNG_FEAT_ID}
            )

    upsert("base_class_abilities.json", abilities)
    upsert("base_class_ability_granted_feats.json", granted_feats)
    upsert("base_companion_archetypes.json", archetypes)
    upsert("base_companion_archetype_abilities.json", archetype_abilities)
    upsert("base_companion_archetype_replacements.json", replacements)
    print(f"{len(archetypes)} archetypes, {len(abilities)} abilities")


if __name__ == "__main__":
    main()
