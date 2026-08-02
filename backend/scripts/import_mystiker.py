"""Import the Mystiker (Oracle) base class from
http://prd.5footstep.de/Expertenregeln/Klassen/Basisklassen/Mystiker into the
seed JSON files, replacing the placeholder "Orakel" class content that
predates any real rules import (wrong curses/mysteries, incomplete known-
spell table, wrong save/skill-point values - see todos.md's 2026-08-02
Nachtrag for the full before/after).

The page content itself was fetched and hand-parsed into
`app/fixtures/imported/mystiker_prd_import.json` in the conversation this was
scoped from (see `parse_mystiker.py` in that session's scratchpad for the
parser, not checked into this repo - the JSON output is the durable
artifact). This script is the second half: turn that parsed JSON into the
seed rows, in the same "hand-authored id, upsert-by-id" shape as every other
`app/fixtures/seed/*.json` file.

What this script does NOT attempt, and why:
- No `BaseClassSpell`/`BaseClassSpellGrant` rows for the ~90 spells the
  class page references (9 per mystery's "Mysteriumszauber" line, plus the
  Wunden-heilen/verursachen family). Only ~16 of those ~90 spell names exist
  in `base_spells.json` at all (102 rows total, imported for other classes'
  needs) - the rest would need real descriptions from their own PRD pages,
  which this script doesn't fetch. Worse: Mystiker casts from the *Cleric*
  spell list, and Kleriker itself has zero `BaseClassSpell` rows seeded yet
  (nobody has imported Cleric's spell list either) - so this is blocked on a
  much larger, pre-existing gap, not something specific to this import.
- No handler-side computation for any revelation/curse/mystery effect (that
  is `rules/`'s job once a slice needs it - composition only, per CLAUDE.md).

Run with the project venv active and the database up (this only writes the
fixture JSON files, it doesn't touch the database itself - run the normal
seed scripts afterward to load them):
    cd backend && python scripts/import_mystiker.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"
IMPORTED = FIXTURES / "imported" / "mystiker_prd_import.json"

ID_NAMESPACE = uuid.UUID("d4a1f8b0-6e2a-4b7a-8a5a-2f6a7b9c1d3e")

ORAKEL_ID = uuid.UUID("949fe615-12a0-4eed-9e2e-25eaab3e3153")
MYSTERY_GROUP_ID = uuid.UUID("3ad982ef-0582-470f-b237-4d5a1bcbdcce")
CURSE_GROUP_ID = uuid.UUID("274abc23-f7a1-44ed-a5e5-c5baff2ea80d")


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def save(filename: str, rows: list[dict]) -> None:
    # Dedup by id (keep last) so re-running this script - uid() is
    # deterministic - upserts instead of appending duplicate rows.
    deduped: dict[str, dict] = {}
    for row in rows:
        deduped[row["id"]] = row
    (SEED_DIR / filename).write_text(
        json.dumps(list(deduped.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


# Canonical mystery order, matching the page's table of contents.
MYSTERY_ORDER = [
    "Firmament",
    "Flammen",
    "Gebeine",
    "Leben",
    "Natur",
    "Schlacht",
    "Stein",
    "Wellen",
    "Wind",
    "Wissen",
]

CURSE_ORDER = ["Getrübte Sicht", "Heimgesucht", "Lahm", "Schwindsüchtig", "Taub", "Zungen"]

# Klassenfertigkeiten (Grundregelwerk): Beruf (WE), Diplomatie (CH), Handwerk
# (IN), Heilkunde (WE), Motiv erkennen (WE), Wissen (Die Ebenen) (IN), Wissen
# (Geschichte) (IN), Wissen (Religion) (IN), Zauberkunde (IN).
BASE_CLASS_SKILLS = [
    "Beruf",
    "Diplomatie",
    "Handwerk",
    "Heilkunde",
    "Motiv erkennen",
    "Wissen (Die Ebenen)",
    "Wissen (Geschichte)",
    "Wissen (Religion)",
    "Zauberkunde",
]

ALL_WISSEN_SKILLS = [
    "Wissen (Adel)",
    "Wissen (Arkanes)",
    "Wissen (Baukunst)",
    "Wissen (Die Ebenen)",
    "Wissen (Geographie)",
    "Wissen (Geschichte)",
    "Wissen (Gewölbekunde)",
    "Wissen (Lokales)",
    "Wissen (Natur)",
    "Wissen (Religion)",
]

# Bonus class skills per Mysterium, transcribed by hand from each mystery's
# "Klassenfertigkeiten:" paragraph on the class page (cross-checked against
# `class_skills_text` in the parsed import for every entry below).
MYSTERY_BONUS_SKILLS = {
    "Firmament": ["Fliegen", "Überlebenskunst", "Wahrnehmung", "Wissen (Arkanes)"],
    "Flammen": ["Akrobatik", "Auftreten", "Einschüchtern", "Klettern"],
    "Gebeine": ["Bluffen", "Einschüchtern", "Heimlichkeit", "Verkleiden"],
    "Leben": ["Mit Tieren umgehen", "Überlebenskunst", "Wissen (Natur)"],
    "Natur": ["Fliegen", "Klettern", "Reiten", "Schwimmen", "Überlebenskunst", "Wissen (Natur)"],
    "Schlacht": ["Einschüchtern", "Reiten", "Wahrnehmung", "Wissen (Baukunst)"],
    "Stein": ["Einschüchtern", "Klettern", "Schätzen", "Überlebenskunst"],
    "Wellen": ["Akrobatik", "Entfesselungskunst", "Schwimmen", "Wissen (Natur)"],
    "Wind": ["Akrobatik", "Entfesselungskunst", "Fliegen", "Heimlichkeit"],
    # "Schätzen und alle Wissensfertigkeiten"
    "Wissen": ["Schätzen", *ALL_WISSEN_SKILLS],
}

# Table: Mystiker (MYS) known-spell table ("Tabelle: Dem Mystiker bekannte
# Zauber") - level -> {grade: cumulative known count}. Grade 0 is unlimited
# per day (Stoßgebete) but still capped in *known* count by this table, same
# as any other spontaneous caster's cantrips.
KNOWN_SPELLS_TABLE = {
    1: {0: 4, 1: 2},
    2: {0: 5, 1: 2},
    3: {0: 5, 1: 3},
    4: {0: 6, 1: 3, 2: 1},
    5: {0: 6, 1: 4, 2: 2},
    6: {0: 7, 1: 4, 2: 2, 3: 1},
    7: {0: 7, 1: 5, 2: 3, 3: 2},
    8: {0: 8, 1: 5, 2: 3, 3: 2, 4: 1},
    9: {0: 8, 1: 5, 2: 4, 3: 3, 4: 2},
    10: {0: 9, 1: 5, 2: 4, 3: 3, 4: 2, 5: 1},
    11: {0: 9, 1: 5, 2: 5, 3: 4, 4: 3, 5: 2},
    12: {0: 9, 1: 5, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1},
    13: {0: 9, 1: 5, 2: 5, 3: 4, 4: 4, 5: 3, 6: 2},
    14: {0: 9, 1: 5, 2: 5, 3: 4, 4: 4, 5: 3, 6: 2, 7: 1},
    15: {0: 9, 1: 5, 2: 5, 3: 4, 4: 4, 5: 4, 6: 3, 7: 2},
    16: {0: 9, 1: 5, 2: 5, 3: 4, 4: 4, 5: 4, 6: 3, 7: 2, 8: 1},
    17: {0: 9, 1: 5, 2: 5, 3: 4, 4: 4, 5: 4, 6: 3, 7: 3, 8: 2},
    18: {0: 9, 1: 5, 2: 5, 3: 4, 4: 4, 5: 4, 6: 3, 7: 3, 8: 2, 9: 1},
    19: {0: 9, 1: 5, 2: 5, 3: 4, 4: 4, 5: 4, 6: 3, 7: 3, 8: 3, 9: 2},
    20: {0: 9, 1: 5, 2: 5, 3: 4, 4: 4, 5: 4, 6: 3, 7: 3, 8: 3, 9: 3},
}


def revelation_choice_name(mystery: str, name: str) -> str:
    """"Kampfheiler" is a distinct revelation (same name, same text) under
    both Leben and Schlacht - `BaseClassOptionChoice`'s (group_id, name)
    uniqueness needs the two disambiguated, same convention already used for
    Waldläufer's "Tiergefährte (Bund des Jägers)"."""
    if name == "Kampfheiler":
        return f"Kampfheiler ({mystery})"
    return name


def main() -> None:
    parsed = json.loads(IMPORTED.read_text(encoding="utf-8"))
    mysteries = parsed["mysteries"]
    curses = parsed["curses"]
    assert set(mysteries) == set(MYSTERY_ORDER), mysteries.keys()
    assert {c["name"] for c in curses} == set(CURSE_ORDER)

    skills = load("base_skills.json")
    skill_id_by_name = {row["name"]: row["id"] for row in skills}
    for name in [*BASE_CLASS_SKILLS, *{s for v in MYSTERY_BONUS_SKILLS.values() for s in v}]:
        assert name in skill_id_by_name, f"missing skill: {name}"

    # ---- base_classes.json: fix the Orakel placeholder in place ----
    base_classes = load("base_classes.json")
    for row in base_classes:
        if row["id"] == str(ORAKEL_ID):
            row["name"] = "Mystiker"
            row["fort_save"] = False  # was True - Mystiker has poor Fort, only good Will (page's "ZÄ" column)
            row["skill_points_base"] = 4  # was 2 - page: "4 + IN-Modifikator"
    save("base_classes.json", base_classes)

    # ---- base_class_option_groups.json: add heilfokus + revelation ----
    groups = load("base_class_option_groups.json")
    heilfokus_group_id = uid("mystiker-group", "heilfokus")
    revelation_group_id = uid("mystiker-group", "revelation")
    groups.append(
        {
            "id": heilfokus_group_id,
            "base_class_id": str(ORAKEL_ID),
            "key": "heilfokus",
            "label": "Stoßgebete-Fokus (Wunden heilen/verursachen)",
            "max_choices": 1,
        }
    )
    groups.append(
        {
            "id": revelation_group_id,
            "base_class_id": str(ORAKEL_ID),
            "key": "revelation",
            "label": "Offenbarung",
            "max_choices": 6,  # 1./3./7./11./15./19. Stufe
        }
    )
    save("base_class_option_groups.json", groups)

    # ---- base_class_option_choices.json ----
    choices = load("base_class_option_choices.json")
    # Drop the wrong placeholder mystery/curse choices (Leben/Knochen/Flamme/
    # Natur/Zeit/Wasser, Blindheit/Verstummt/Verflucht mit Schuppen/
    # Frostgezeichnet) - none of them match the real page, see todos.md.
    choices = [
        c for c in choices if c["group_id"] not in (str(MYSTERY_GROUP_ID), str(CURSE_GROUP_ID))
    ]

    mystery_choice_id = {}
    for name in MYSTERY_ORDER:
        cid = uid("mystery-choice", name)
        mystery_choice_id[name] = cid
        choices.append({"id": cid, "group_id": str(MYSTERY_GROUP_ID), "name": name})

    curse_choice_id = {}
    for name in CURSE_ORDER:
        cid = uid("curse-choice", name)
        curse_choice_id[name] = cid
        choices.append({"id": cid, "group_id": str(CURSE_GROUP_ID), "name": name})

    heilfokus_choice_id = {}
    for name in ["Wunden heilen", "Wunden verursachen"]:
        cid = uid("heilfokus-choice", name)
        heilfokus_choice_id[name] = cid
        choices.append({"id": cid, "group_id": heilfokus_group_id, "name": name})

    revelation_choice_id: dict[tuple[str, str], str] = {}
    for mystery in MYSTERY_ORDER:
        for rev in mysteries[mystery]["revelations"]:
            cname = revelation_choice_name(mystery, rev["name"])
            cid = uid("revelation-choice", mystery, rev["name"])
            revelation_choice_id[(mystery, rev["name"])] = cid
            row = {
                "id": cid,
                "group_id": revelation_group_id,
                "name": cname,
                "requires_choice_id": mystery_choice_id[mystery],
            }
            if rev["min_level"]:
                row["min_level"] = rev["min_level"]
            choices.append(row)

    assert len({(c["group_id"], c["name"]) for c in choices}) == len(choices), "duplicate (group_id, name)"
    save("base_class_option_choices.json", choices)

    # ---- base_class_abilities.json + base_class_ability_grants.json ----
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")

    def add_ability(name: str, description: str) -> str:
        aid = uid("mystiker-ability", name)
        abilities.append({"id": aid, "name": name, "description": description})
        return aid

    def add_grant(ability_id: str, level: int, option_choice_id: str | None = None) -> None:
        grants.append(
            {
                "id": uid("mystiker-grant", ability_id, str(level), option_choice_id or ""),
                "base_class_id": str(ORAKEL_ID),
                "ability_id": ability_id,
                "option_choice_id": option_choice_id,
                "level": level,
            }
        )

    # Flavor/overview class features, all unconditional at 1st level unless noted.
    weapons_id = add_ability(
        "Umgang mit Waffen und Rüstungen",
        "Mystiker sind im Umgang mit einfachen Waffen, Leichter Rüstung, Mittelschwerer Rüstung und "
        "Schilden (außer Turmschilden) geübt. Einige Offenbarungen gewähren zusätzliche "
        "Umgangsmöglichkeiten.",
    )
    add_grant(weapons_id, 1)

    zauber_id = add_ability(
        "Zauber",
        "Ein Mystiker wirkt göttliche Zauber von der Liste der Klerikerzauber. Er kann diese Zauber "
        "wirken, ohne sie vorher vorbereiten zu müssen. Um einen Zauber des entsprechenden Grades lernen "
        "oder wirken zu können, muss der Mystiker über ein Charisma von mindestens 10 + Grad des Zaubers "
        "verfügen. Der Schwierigkeitsgrad für einen Rettungswurf gegen den Zauber eines Mystikers ist 10 "
        "+ Grad des Zaubers + CH-Modifikator des Mystikers. Anders als bei anderen göttlichen "
        "Zauberkundigen ist die Zauberauswahl eines Mystikers stark eingeschränkt (siehe Tabelle: Dem "
        "Mystiker bekannte Zauber) - anders als die täglichen Zauber wird diese Anzahl nicht durch den "
        "Charismawert des Mystikers beeinflusst. Mystiker benötigen keinen göttlichen Fokus für Zauber, "
        "die einen solchen als Komponente voraussetzen.",
    )
    add_grant(zauber_id, 1)

    mysterium_id = add_ability(
        "Mysterium",
        "Jeder Mystiker erhält seine Zauber und Fähigkeiten von einem göttlichen Mysterium. Dieses "
        "Mysterium gewährt zudem zusätzliche Klassenfertigkeiten und andere Besondere Fähigkeiten. Der "
        "Mystiker muss ein Mysterium auf der 1. Stufe auswählen, diese Entscheidung kann anschließend "
        "nicht mehr verändert werden.",
    )
    add_grant(mysterium_id, 1)

    mysteriumszauber_id = add_ability(
        "Mysteriumszauber",
        "Auf der 2. Stufe und alle zwei weiteren Stufen danach erlernt der Mystiker einen neuen Zauber "
        "abhängig von seinem gewählten Mysterium, zusätzlich zu den auf Tabelle: Dem Mystiker bekannte "
        "Zauber angegebenen Zaubern. Diese Zauber können auf späteren Stufen nicht für andere Zauber "
        "eingetauscht werden.",
    )
    for level in range(2, 19, 2):
        add_grant(mysteriumszauber_id, level)

    mystikerfluch_id = add_ability(
        "Mystikerfluch",
        "Jeder Mystiker ist mit einem Fluch belegt. Dieser kommt jedoch sowohl mit einem Vorteil, als "
        "auch einem Nachteil daher. Auf der 1. Stufe wählt der Mystiker einen Fluch aus, dessen Wahl "
        "nicht mehr verändert werden kann. Nur durch die Hilfe einer Gottheit, oder eines ähnlich "
        "mächtigen Wesens, kann der Fluch vom Mystiker genommen werden.",
    )
    add_grant(mystikerfluch_id, 1)

    for curse in curses:
        cid = add_ability(curse["name"], curse["text"])
        add_grant(cid, 1, curse_choice_id[curse["name"]])

    stossgebete_id = add_ability(
        "Stoßgebete",
        "Der Mystiker erlernt eine Anzahl von Stoßgebeten (Zauber des Grades 0.), wie auf Tabelle: Dem "
        "Mystiker bekannte Zauber unter Bekannte Zauber angegeben. Diese Zauber werden normal gewirkt, "
        "nur dass sie nicht verbraucht werden und erneut eingesetzt werden können.",
    )
    add_grant(stossgebete_id, 1)

    offenbarung_id = add_ability(
        "Offenbarung",
        "Auf der 1., der 3. und danach alle vier weiteren Stufen (7. Stufe, 11. Stufe, usw.) enthüllt "
        "sich dem Mystiker ein neues Geheimnis seines Mysteriums, welches ihm neue Fähigkeiten verleiht. "
        "Der Mystiker muss eine Offenbarung von der Liste der verfügbaren Offenbarungen seines Mysteriums "
        "auswählen. Sollte eine Offenbarung erst auf einer späteren Stufe ausgewählt werden, erhält der "
        "Mystiker alle Fähigkeiten und Boni entsprechend seiner aktuellen Stufe. Wenn nichts anderes "
        "angegeben wird, ist das Einsetzen der Fähigkeit einer Offenbarung eine Standard-Aktion.",
    )
    for level in (1, 3, 7, 11, 15, 19):
        add_grant(offenbarung_id, level)

    # 100 revelation effect abilities, one BaseClassAbilityGrant each
    # (option_choice_id = that revelation's own choice, level = 1, same
    # nominal-level convention as Schurke's individual tricks - the real
    # timing is tracked via CharacterClassOption.grant_id against the
    # Offenbarung slot above, not this grant's own `level`).
    for mystery in MYSTERY_ORDER:
        for rev in mysteries[mystery]["revelations"]:
            cname = revelation_choice_name(mystery, rev["name"])
            aid = add_ability(cname, rev["text"])
            add_grant(aid, 1, revelation_choice_id[(mystery, rev["name"])])

    for mystery in MYSTERY_ORDER:
        aid = add_ability(f"Letzte Offenbarung ({mystery})", mysteries[mystery]["final_revelation_text"])
        add_grant(aid, 20, mystery_choice_id[mystery])

    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)

    # ---- base_class_skills.json ----
    class_skills = load("base_class_skills.json")
    # Drop the placeholder Orakel rows (6 rows incl. the wrong "Sprachenkunde").
    class_skills = [r for r in class_skills if r["base_class_id"] != str(ORAKEL_ID)]
    for name in BASE_CLASS_SKILLS:
        class_skills.append(
            {
                "id": uid("mystiker-classskill", name),
                "base_class_id": str(ORAKEL_ID),
                "skill_id": skill_id_by_name[name],
                "option_choice_id": None,
            }
        )
    for mystery, bonus_skills in MYSTERY_BONUS_SKILLS.items():
        for name in bonus_skills:
            class_skills.append(
                {
                    "id": uid("mystiker-classskill", mystery, name),
                    "base_class_id": str(ORAKEL_ID),
                    "skill_id": skill_id_by_name[name],
                    "option_choice_id": mystery_choice_id[mystery],
                }
            )
    save("base_class_skills.json", class_skills)

    # ---- base_class_spells_known.json ----
    known = load("base_class_spells_known.json")
    known = [r for r in known if r["base_class_id"] != str(ORAKEL_ID)]
    for level, grades in KNOWN_SPELLS_TABLE.items():
        for grade, count in grades.items():
            known.append(
                {
                    "id": uid("mystiker-known", str(level), str(grade)),
                    "base_class_id": str(ORAKEL_ID),
                    "level": level,
                    "grade": grade,
                    "count": count,
                }
            )
    save("base_class_spells_known.json", known)

    print("Mysteries:", len(mysteries))
    print("Curses:", len(curses))
    print("Revelation choices:", len(revelation_choice_id))
    print("New abilities:", len(abilities))
    print("New grants:", len(grants))
    print("Done.")


if __name__ == "__main__":
    main()
