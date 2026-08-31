"""Import the "Schutzherr" (Patron) option group for the Hexe (Witch) class.

Adds a new `patron` `BaseClassOptionGroup` (max_choices=1), 18
`BaseClassOptionChoice` rows, one identity `BaseClassAbility`/
`BaseClassAbilityGrant` pair per sourced patron (same "Schutzherr: X" shape
Hexenmeister's bloodline identity grants already use), and
`BaseClassSpellGrant` rows for the patron's bonus spells.

12 of the 18 patrons are sourced from `prd.5footstep.de` (this project's
primary German reference), which has the full Grundregelwerk patron list
with its complete bonus-spell-per-level table:
https://prd.5footstep.de/Expertenregeln/Klassen/Basisklassen/Hexe#Schutzherrenzauber
(Ausdauer, Beweglichkeit, Elemente, Schatten, Seuche, Stärke, Täuschung,
Tiere, Trickserei, Verwandlung, Wasser, Weisheit) — every referenced spell
name was checked against `base_spells.json` and resolves to a real entry
(a few purely cosmetic name differences: "Massenunsichtbarkeit" has no
hyphen here vs. the PRD's "Massen-Unsichtbarkeit"; "Elementargestalt III"/
"IV" and "Kugel der Unverwundbarkeit" are seeded without the PRD's "(nur
Wasser)"/"(Mächtige)" qualifiers, same spell). "Wasser"'s 2nd-level entry
lists two alignment-alternate spells ("Wasser weihen"/"Wasser entweihen");
both are seeded as separate grants at level 2 rather than picking one
arbitrarily, since a `BaseClassSpellGrant` only ever expands spellbook
*candidates* — granting both is a superset, not a false choice, and the
Hexe still chooses what to actually prepare like any other known spell.

The remaining 6 patrons are Kräuterhexe (Herb Witch)-specific themes named
in its own already-imported description (`import_herb_witch_archetype.py`):
Ahnen, Tod, Heilung, Pflanzen, Zeit, Winter. These come from Paizo
sourcebooks `prd.5footstep.de` never translated, so there's no sourced
bonus-spell list for them — seeded as bare option choices only, no identity
ability, no spell grants.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database — run the seed scripts afterward):
    cd backend && python scripts/import_hexe_patrons.py
    python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed
    python -m app.seed.spell_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("8a5e2f0b-9c1d-4e6a-b3f7-2d8c4a9e0f61")

HEXE_ID = "2ac0bd62-8800-4db8-9395-22b4391a9646"

# level -> spell name, per sourced patron. "Wasser" additionally grants a
# second level-2 spell, see WASSER_EXTRA_LEVEL2 below.
SOURCED_PATRON_SPELLS: dict[str, dict[int, str]] = {
    "Ausdauer": {
        2: "Elementen trotzen", 4: "Ausdauer des Ochsen", 6: "Schutz vor Energien",
        8: "Immunität gegen Zauber", 10: "Zauberresistenz", 12: "Massen-Ausdauer des Ochsen",
        14: "Vollständige Genesung", 16: "Eiserner Körper", 18: "Wunder",
    },
    "Beweglichkeit": {
        2: "Springen", 4: "Katzenhafte Anmut", 6: "Hast", 8: "Bewegungsfreiheit",
        10: "Verwandlung", 12: "Massen-Katzenhafte Anmut", 14: "Ätherischer Ausflug",
        16: "Tierform", 18: "Gestaltwandel",
    },
    "Elemente": {
        2: "Schockgriff", 4: "Flammenkugel", 6: "Feuerball", 8: "Eiswand",
        10: "Flammenschlag", 12: "Frostsphäre", 14: "Strudel", 16: "Feuersturm",
        18: "Meteoritenschwarm",
    },
    "Schatten": {
        2: "Stilles Trugbild", 4: "Dunkelheit", 6: "Tiefere Dunkelheit",
        8: "Schattenbeschwörung", 10: "Schattenhervorrufung", 12: "Schattenreise",
        14: "Mächtige Schattenbeschwörung", 16: "Mächtige Schattenhervorrufung", 18: "Schatten",
    },
    "Seuche": {
        2: "Untote entdecken", 4: "Untote befehligen", 6: "Ansteckung", 8: "Tote beleben",
        10: "Riesenhaftes Ungeziefer", 12: "Untote erschaffen", 14: "Untote kontrollieren",
        16: "Mächtigere Untote erschaffen", 18: "Entzug von Lebenskraft",
    },
    "Stärke": {
        2: "Göttliche Gunst", 4: "Bärenstärke", 6: "Mächtige Magische Waffe",
        8: "Göttliche Macht", 10: "Gerechte Macht", 12: "Massen-Bärenstärke",
        14: "Riesengestalt I", 16: "Riesengestalt II", 18: "Gestaltwandel",
    },
    "Täuschung": {
        2: "Bauchreden", 4: "Unsichtbarkeit", 6: "Flimmern", 8: "Verwirrung",
        10: "Wände passieren", 12: "Vorbestimmtes Trugbild", 14: "Massenunsichtbarkeit",
        16: "Schillerndes Muster", 18: "Zeitstopp",
    },
    "Tiere": {
        2: "Tier bezaubern", 4: "Mit Tieren sprechen", 6: "Tier beherrschen",
        8: "Verbündeten der Natur herbeizaubern IV", 10: "Tierwachstum",
        12: "Schutzhülle gegen Lebendes", 14: "Bestiengestalt IV", 16: "Tierform",
        18: "Verbündeten der Natur herbeizaubern IX",
    },
    "Trickserei": {
        2: "Seil beleben", 4: "Spiegelbilder", 6: "Mächtiges Trugbild", 8: "Scheingelände",
        10: "Arkane Spiegelung", 12: "Ablenkung", 14: "Schwerkraft umkehren",
        16: "Abschirmung", 18: "Zeitstopp",
    },
    "Verwandlung": {
        2: "Springen", 4: "Ausdauer des Ochsen", 6: "Bestiengestalt I", 8: "Bestiengestalt II",
        10: "Bestiengestalt III", 12: "Drachengestalt I", 14: "Drachengestalt II",
        16: "Drachengestalt III", 18: "Gestaltwandel",
    },
    "Wasser": {
        2: "Wasser weihen", 4: "Wellenritt", 6: "Wasser atmen", 8: "Wasser kontrollieren",
        10: "Geysir", 12: "Elementargestalt III", 14: "Elementargestalt IV",
        16: "Mantel der See", 18: "Tsunami",
    },
    "Weisheit": {
        2: "Schild des Glaubens", 4: "Weisheit der Eule", 6: "Magisches Schutzgewand",
        8: "Schwächere Kugel der Unverwundbarkeit", 10: "Traum",
        12: "Kugel der Unverwundbarkeit", 14: "Zauber zurückwerfen",
        16: "Schutz vor Zaubern", 18: "Magische Auftrennung",
    },
}
WASSER_EXTRA_LEVEL2 = "Wasser entweihen"

KRAEUTERHEXE_ONLY_PATRONS = ["Ahnen", "Tod", "Heilung", "Pflanzen", "Zeit", "Winter"]

HEXEREI_GROUP_ID = "31954213-c209-4009-ad1b-5fc1d5e538d4"  # unused here, kept for reference


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


def describe_patron(patron: str, levels: dict[int, str]) -> str:
    entries = ", ".join(f"{spell} ({level}.)" for level, spell in sorted(levels.items()))
    if patron == "Wasser":
        entries = entries.replace("Wasser weihen (2.)", "Wasser weihen/Wasser entweihen (2.)")
    return (
        f"Ab der 2. Stufe und danach alle weiteren zwei Stufen als Hexe fügt der Schutzherr "
        f"\"{patron}\" folgende Zauber automatisch zur Liste bekannter Hexenzauber hinzu, welche "
        f"auch im Hexenvertrauten gespeichert werden: {entries}."
    )


def main() -> None:
    groups = load("base_class_option_groups.json")
    choices = load("base_class_option_choices.json")
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    spell_grants = load("base_class_spell_grants.json")
    spells_by_name = {s["name"]: s["id"] for s in json.loads((SEED_DIR / "base_spells.json").read_text(encoding="utf-8"))}

    group_id = uid("hexe-patron-group")
    groups[:] = [g for g in groups if g["id"] != group_id]
    groups.append({"id": group_id, "base_class_id": HEXE_ID, "key": "patron", "label": "Schutzherr", "max_choices": 1})

    all_patron_names = list(SOURCED_PATRON_SPELLS.keys()) + KRAEUTERHEXE_ONLY_PATRONS
    for patron in all_patron_names:
        choice_id = uid("hexe-patron-choice", patron)
        choices[:] = [c for c in choices if c["id"] != choice_id]
        choices.append({"id": choice_id, "group_id": group_id, "name": patron})

        if patron not in SOURCED_PATRON_SPELLS:
            continue

        levels = SOURCED_PATRON_SPELLS[patron]
        ability_id = uid("hexe-patron-ability", patron)
        abilities[:] = [a for a in abilities if a["id"] != ability_id]
        abilities.append(
            {"id": ability_id, "name": f"Schutzherr: {patron}", "description": describe_patron(patron, levels)}
        )

        grant_id = uid("hexe-patron-identity-grant", patron)
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

        spell_entries = list(levels.items())
        if patron == "Wasser":
            spell_entries.append((2, WASSER_EXTRA_LEVEL2))
        for level, spell_name in spell_entries:
            spell_id = spells_by_name[spell_name]
            spell_grant_id = uid("hexe-patron-spell-grant", patron, str(level), spell_name)
            spell_grants[:] = [sg for sg in spell_grants if sg["id"] != spell_grant_id]
            spell_grants.append(
                {
                    "id": spell_grant_id,
                    "base_class_id": HEXE_ID,
                    "option_choice_id": choice_id,
                    "spell_id": spell_id,
                    "level": level,
                }
            )

    save("base_class_option_groups.json", groups)
    save("base_class_option_choices.json", choices)
    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)
    save("base_class_spell_grants.json", spell_grants)

    print("Schutzherr option group id:", group_id)
    print("Patrons seeded:", len(all_patron_names), "sourced:", len(SOURCED_PATRON_SPELLS))
    print("Done.")


if __name__ == "__main__":
    main()
