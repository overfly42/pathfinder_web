"""Import the "Scaled Fist" Monk archetype from
https://www.d20pfsrd.com/classes/core-classes/monk/archetypes/paizo-monk-archetypes/scaled-fist-monk-archetype/
(English source — this archetype has no page on prd.5footstep.de, the
German PRD site every other class/archetype import in this directory pulls
from; names below are this project's own translation, not an official
Ulisses Spiele localization, same situation `import_herb_witch_archetype.py`
was already in for "Kräuterhexe").

Must run after `import_moench.py` (resolves the Mönch grant rows it
replaces by loading the already-written seed files, same convention
`import_meister_aller_kampfstile.py` uses).

Four named class features from the source:
- **Drachenmacht** (Draconic Might, all levels): every Mönch class ability
  that keys off Weisheit (including bonus-feat DCs/uses-per-day such as
  Betäubender Schlag, but not Weisheit-based skills or Willenswürfe) is
  instead keyed off Charisma. Also folds in the source's "Bonustalente"
  modification (Dragon Style/Intimidating Prowess at 1st, Dazzling
  Display/Dragon Ferocity at 6th, Disheartening Display/Dragon Roar/
  Shatter Defenses at 10th) as prose only, no `BaseClassAbilityFeatOption`
  rows — none of those six feats resolve to an existing `base_feats.json`
  row under any plausible German name (checked before writing this script:
  no "Drachen-"/"Blendend-"/"Entmutigend-" prefixed feat exists, and
  Ausbaustufe's one superficially close hit, "Einschüchterndes
  Selbstvertrauen", is a different, unrelated feat by its own description).
  Neither sub-feature replaces a specific parent grant (the source doesn't
  phrase either as "replaces X"), so no `BaseClassAbilityReplacement` row
  either — same "restatement only" shape as `import_moench.py` leaving the
  favored-class-bonus grants alone.
- **Drachenmut** (Draconic Mettle, 3rd level): +2 on saves vs. fear,
  paralysis, and sleep effects. Replaces the base Mönch's Ruhiger Geist
  (Still Mind).
- **Drachenfurie** (Draconic Fury, 3rd level): spend a ki point for 1d6
  points of energy damage on unarmed strikes for a number of rounds equal
  to half the Mönch's level. Replaces the base Mönch's Manövertraining
  (Maneuver Training).
- **Drachenatem** (Draconic Breath, 15th level): spend 3 ki points for a
  standard-action breath-weapon attack, 1d6 energy damage per Mönch level in
  a 30-foot cone. Replaces the base Mönch's Vibrierende Handfläche
  (Quivering Palm).

Deliberately out of scope, same "composition only" principle as every other
class/archetype pass here: no handler computes the WIS->CHA substitution,
the per-round elemental damage, or the breath-weapon damage/save — the base
Mönch itself has no `rules/classes/moench.py` handler yet either, so there's
nothing for these to plug into.

Run with the project venv active (writes fixture JSON only, run the seed
scripts afterward):
    cd backend && python scripts/import_moench.py
    python scripts/import_scaled_fist_archetype.py
    python -m app.seed.class_seed
    python -m app.seed.class_ability_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("8b1a5b3c-9d4e-4c7a-8f2b-1e6a7c3d5f90")

MOENCH_ID = "4ed3adcc-31e6-408d-a554-5e76a368df9d"

DRACHENMACHT_DESC = (
    "Alle Klassenmerkmale des Mönchs, die Berechnungen anhand seines Weisheitswertes vornehmen (einschließlich "
    "Bonustalente mit Schwierigkeitsgraden oder täglichen Anwendungen wie Betäubender Schlag, jedoch nicht auf "
    "Weisheit basierende Fertigkeiten oder Willenswürfe), verwenden stattdessen seinen Charismawert.\n\n"
    "Außerdem stehen einer Beschuppten Faust als Bonustalente andere Talente zur Auswahl als einem gewöhnlichen "
    "Mönch: Drachenstil und Einschüchterndes Auftreten auf der 1. Stufe; Blendender Auftritt und Drachenwildheit "
    "auf der 6. Stufe; Entmutigender Auftritt, Drachengebrüll und Zerschmetterte Verteidigung auf der 10. Stufe "
    "(keines dieser Talente existiert bislang im Talentkatalog dieser App, siehe Skriptkommentar — die "
    "Bonustalent-Auswahl des Mönchs bleibt bis dahin unverändert nutzbar)."
)

DRACHENMUT_DESC = (
    "(AF) Ab der 3. Stufe erhält eine Beschuppte Faust einen Bonus von +2 auf Rettungswürfe gegen Furcht-, "
    "Lähmungs- und Schlafeffekte. Dieses Klassenmerkmal ersetzt Ruhiger Geist."
)

DRACHENFURIE_DESC = (
    "(ÜF) Ab der 3. Stufe kann eine Beschuppte Faust einen Punkt ihres Ki-Vorrats ausgeben, um ihre unbewaffneten "
    "Angriffe für eine Anzahl von Runden in Höhe der Hälfte ihrer Mönchsstufe mit 1W6 zusätzlichem Energieschaden "
    "eines gewählten Energietyps zu versehen. Dieses Klassenmerkmal ersetzt Manövertraining."
)

DRACHENATEM_DESC = (
    "(ÜF) Ab der 15. Stufe kann eine Beschuppte Faust drei Punkte ihres Ki-Vorrats ausgeben, um als Standardaktion "
    "einen Odemangriff in einem 9 m langen Kegel auszuführen, der 1W6 Energieschaden pro Mönchsstufe verursacht. "
    "Dieses Klassenmerkmal ersetzt Vibrierende Handfläche."
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


def moench_grant_id(*, abilities: list[dict], grants: list[dict], ability_name: str, level: int) -> str:
    name_by_ability_id = {a["id"]: a["name"] for a in abilities}
    matches = [
        g["id"]
        for g in grants
        if g["base_class_id"] == MOENCH_ID and g["level"] == level and name_by_ability_id.get(g["ability_id"]) == ability_name
    ]
    assert len(matches) == 1, f"Mönch grant not found for {ability_name!r} at level {level} — run import_moench.py first"
    return matches[0]


def main() -> None:
    classes = load("base_classes.json")
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    replacements = load("base_class_ability_replacements.json")

    archetype_id = uid("beschuppte-faust-archetype", MOENCH_ID)
    classes = [c for c in classes if c["id"] != archetype_id]
    classes.append(
        {
            "id": archetype_id,
            "name": "Beschuppte Faust",
            "hit_dice": None,
            "arch_class_of": MOENCH_ID,
            "casting_ability": None,
            "spell_tradition": None,
            "bab_progression": None,
            "fort_save": None,
            "ref_save": None,
            "wil_save": None,
            "skill_points_base": None,
        }
    )

    ability_ids = {a["id"] for a in abilities}

    def add_ability(name: str, description: str) -> str:
        aid = uid("beschuppte-faust-ability", archetype_id, name)
        if aid not in ability_ids:
            abilities.append({"id": aid, "name": name, "description": description})
            ability_ids.add(aid)
        return aid

    def add_grant(ability_id: str, level: int) -> None:
        grant_id = uid("beschuppte-faust-grant", ability_id, str(level))
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

    def add_replacement(ability_id: str, replaces_grant_id: str) -> None:
        replacement_id = uid("beschuppte-faust-replacement", ability_id, replaces_grant_id)
        replacements[:] = [r for r in replacements if r["id"] != replacement_id]
        replacements.append(
            {
                "id": replacement_id,
                "archetype_class_id": archetype_id,
                "ability_id": ability_id,
                "replaces_grant_id": replaces_grant_id,
            }
        )

    # ---- Drachenmacht: blanket restatement, replaces nothing ----
    drachenmacht_id = add_ability("Drachenmacht", DRACHENMACHT_DESC)
    add_grant(drachenmacht_id, 1)

    # ---- Drachenmut: replaces Ruhiger Geist (3) ----
    drachenmut_id = add_ability("Drachenmut", DRACHENMUT_DESC)
    add_grant(drachenmut_id, 3)
    add_replacement(
        drachenmut_id,
        moench_grant_id(abilities=abilities, grants=grants, ability_name="Ruhiger Geist", level=3),
    )

    # ---- Drachenfurie: replaces Manövertraining (3) ----
    drachenfurie_id = add_ability("Drachenfurie", DRACHENFURIE_DESC)
    add_grant(drachenfurie_id, 3)
    add_replacement(
        drachenfurie_id,
        moench_grant_id(abilities=abilities, grants=grants, ability_name="Manövertraining", level=3),
    )

    # ---- Drachenatem: replaces Vibrierende Handfläche (15) ----
    drachenatem_id = add_ability("Drachenatem", DRACHENATEM_DESC)
    add_grant(drachenatem_id, 15)
    add_replacement(
        drachenatem_id,
        moench_grant_id(abilities=abilities, grants=grants, ability_name="Vibrierende Handfläche", level=15),
    )

    save("base_classes.json", classes)
    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)
    save("base_class_ability_replacements.json", replacements)

    print("Beschuppte Faust class id:", archetype_id)
    print("Done.")


if __name__ == "__main__":
    main()
