"""Import the Kleriker (Cleric) base class from
http://prd.5footstep.de/Grundregelwerk/Klassen/Kleriker into the seed JSON
files. Kleriker already had a real `base_classes.json` row (hit dice/BAB/
saves/skill points/casting ability all verified correct against the page -
see todos.md), a domain `BaseClassOptionGroup`, and 9 of its 13 real class
skills - but the 8 domain choices were LLM-guessed placeholders (short names
like "Kriegsdomäne"/"Leben" that don't match any real domain, and only 8 of
the page's 33 domains), and the class had zero `BaseClassAbility`/`Grant`
rows at all (no Channel Energy, no domain powers, nothing).

The page content was fetched and hand-parsed (regex over the flattened
`<div id="page">` text, splitting on each domain's `<h4>` header) into
`app/fixtures/imported/kleriker_domains_prd_import.json` in the conversation
this was scoped from - the parser itself isn't checked in, only its output.
This script is the second half: turn that parsed JSON (plus the class's
other, hand-transcribed core features) into seed rows, same "hand-authored
id, upsert-by-id" shape as every other `app/fixtures/seed/*.json` file.

What this script does NOT attempt, and why:
- No `BaseClassSpell`/`BaseClassSpellGrant` rows. Kleriker had zero spell
  rows before this (see todos.md's 2026-08-02 Mystiker Nachtrag - this was
  already flagged as a separate, larger pre-existing gap: the Grundregelwerk
  Kleriker spell list runs to several hundred spells across 10 levels, and
  only ~102 spells exist in `base_spells.json` at all today). Each domain's
  "Domänenzauber:" (bonus spell) list is still captured in the parsed import
  for future use, just not turned into `BaseClassSpellGrant` rows here.
- No handler-side computation for any domain power or Energie fokussieren
  (rules/`s job once a slice needs it - composition only, per CLAUDE.md).

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database - run the normal seed scripts afterward):
    cd backend && python scripts/import_kleriker.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"
IMPORTED = FIXTURES / "imported" / "kleriker_domains_prd_import.json"

ID_NAMESPACE = uuid.UUID("f3b6e0f0-3a8e-4b1e-9b8e-1a5c6d7e8f90")

KLERIKER_ID = uuid.UUID("1e6e60de-d72f-4910-b19d-55ca11e14190")
DOMAIN_GROUP_ID = uuid.UUID("7b82d11f-eae8-4e79-bb43-aaad60d728ff")

# Klassenfertigkeiten (Grundregelwerk): Beruf (WE), Diplomatie (CH), Handwerk
# (IN), Heilkunde (WE), Motiv erkennen (WE), Schätzen (IN), Sprachenkunde
# (IN), Wissen (Adel) (IN), Wissen (Arkanes) (IN), Wissen (Geschichte) (IN),
# Wissen (Die Ebenen) (IN), Wissen (Religion) (IN), Zauberkunde (IN).
BASE_CLASS_SKILLS = [
    "Beruf",
    "Diplomatie",
    "Handwerk",
    "Heilkunde",
    "Motiv erkennen",
    "Schätzen",
    "Sprachenkunde",
    "Wissen (Adel)",
    "Wissen (Arkanes)",
    "Wissen (Geschichte)",
    "Wissen (Die Ebenen)",
    "Wissen (Religion)",
    "Zauberkunde",
]

# "Tabelle: Kleriker"'s "Speziell" column: Energie fokussieren's die count
# grows every 2 levels starting at 1st (1W6, 2W6, ... 10W6 at 19th).
ENERGIE_FOKUSSIEREN_LEVELS = list(range(1, 20, 2))


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
    domains = json.loads(IMPORTED.read_text(encoding="utf-8"))
    assert len(domains) == 33, len(domains)

    skills = load("base_skills.json")
    skill_id_by_name = {row["name"]: row["id"] for row in skills}
    for name in BASE_CLASS_SKILLS:
        assert name in skill_id_by_name, f"missing skill: {name}"

    # ---- base_class_skills.json: add the 4 missing skills ----
    # (Diplomatie/Heilkunde/Wissen(Religion)/Zauberkunde/Motiv erkennen/
    # Sprachenkunde/Wissen(Adel)/Wissen(Die Ebenen)/Wissen(Geschichte) were
    # already correct - only Beruf/Handwerk/Schätzen/Wissen(Arkanes) were
    # missing from the page's 13-skill list.)
    class_skills = load("base_class_skills.json")
    existing = {row["skill_id"] for row in class_skills if row["base_class_id"] == str(KLERIKER_ID)}
    for name in BASE_CLASS_SKILLS:
        sid = skill_id_by_name[name]
        if sid in existing:
            continue
        class_skills.append(
            {
                "id": uid("kleriker-classskill", name),
                "base_class_id": str(KLERIKER_ID),
                "skill_id": sid,
                "option_choice_id": None,
            }
        )
    save("base_class_skills.json", class_skills)

    # ---- base_class_option_choices.json: replace the 8 guessed domains with all 33 real ones ----
    choices = load("base_class_option_choices.json")
    choices = [c for c in choices if c["group_id"] != str(DOMAIN_GROUP_ID)]

    domain_choice_id: dict[str, str] = {}
    for d in domains:
        cid = uid("domain-choice", d["name"])
        domain_choice_id[d["name"]] = cid
        choices.append({"id": cid, "group_id": str(DOMAIN_GROUP_ID), "name": d["name"]})

    assert len({(c["group_id"], c["name"]) for c in choices}) == len(choices), "duplicate (group_id, name)"
    save("base_class_option_choices.json", choices)

    # ---- base_class_abilities.json + base_class_ability_grants.json ----
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    # Drop nothing pre-existing - Kleriker had zero ability/grant rows before this.

    def add_ability(name: str, description: str) -> str:
        aid = uid("kleriker-ability", name)
        abilities.append({"id": aid, "name": name, "description": description})
        return aid

    def add_grant(ability_id: str, level: int, option_choice_id: str | None = None) -> None:
        grants.append(
            {
                "id": uid("kleriker-grant", ability_id, str(level), option_choice_id or ""),
                "base_class_id": str(KLERIKER_ID),
                "ability_id": ability_id,
                "option_choice_id": option_choice_id,
                "level": level,
            }
        )

    weapons_id = add_ability(
        "Umgang mit Waffen und Rüstungen",
        "Der Kleriker ist im Umgang mit allen einfachen Waffen, mit allen leichten und mittelschweren "
        "Rüstungen und mit allen Schilden (außer Turmschilden) geübt. Zusätzlich ist er in der "
        "bevorzugten Waffe seiner Gottheit geschult.",
    )
    add_grant(weapons_id, 1)

    aura_id = add_ability(
        "Aura",
        "Der Kleriker einer bösen, chaotischen, guten oder rechtschaffenen Gottheit strahlt eine starke "
        "Aura entsprechend der Gesinnung der Gottheit aus (siehe den Zauber Böses entdecken).",
    )
    add_grant(aura_id, 1)

    zauber_id = add_ability(
        "Zauber",
        "Ein Kleriker wirkt göttliche Zauber, die er aus der Zauberliste für Kleriker auswählt. Einige "
        "Zauber aus der Liste können jedoch der Ethik oder Moral seiner Gesinnung widersprechen und "
        "stehen ihm somit nicht zur Verfügung. Ein Kleriker muss seine Zauber vorher auswählen und "
        "vorbereiten. Um einen Zauber vorbereiten und wirken zu können, muss der Kleriker mindestens "
        "eine Weisheit von 10 + Grad des Zaubers besitzen. Der Schwierigkeitsgrad des Rettungswurfs "
        "gegen die Zauber eines Klerikers ist 10 + Grad des Zaubers + WE-Modifikator des Charakters. "
        "Kleriker meditieren oder beten, um ihre Zauber zu erhalten. Ein Kleriker muss eine Stunde pro "
        "Tag auswählen, die er in besinnlicher Ruhe oder Andacht verbringt, um seine Zauber "
        "wiederzuerlangen. Während seiner Meditation wählt er dann die Zauber für den Tag aus.",
    )
    add_grant(zauber_id, 1)

    energie_id = add_ability(
        "Energie fokussieren",
        "Jeder Kleriker kann, unabhängig von seiner Gesinnung, mit Hilfe seines heiligen oder unheiligen "
        "Symbols über seinen Glauben Energie fokussieren, um damit eine Welle göttlicher Macht in Form "
        "von positiver oder negativer Energie frei zu setzen. Ein guter Kleriker kann nur positive "
        "Energie fokussieren, um damit Untote zu verletzen oder wahlweise lebende Kreaturen zu heilen. "
        "Ein böser Kleriker kann nur negative Energie fokussieren, um damit wahlweise lebende Wesen zu "
        "verletzen oder Untote zu heilen. Ein neutraler Kleriker muss sich entscheiden, ob er positive "
        "oder negative Energie fokussieren möchte; ist diese Wahl einmal getroffen, kann sie nicht mehr "
        "geändert werden. Das Fokussieren von Energie erzeugt einen Impuls, der alle Wesen eines Typs "
        "(lebendig oder untot) in einem Umkreis von 9 Metern um den Kleriker betrifft. Die Menge an "
        "Schadenspunkten, die geheilt oder verursacht werden, entspricht 1W6 Schadenspunkten + je 1W6 "
        "Schadenspunkten für alle weiteren 2 Stufen jenseits der 1., die der Kleriker erreicht hat (2W6 "
        "auf der 3. Stufe, 3W6 auf der 5. usw.). Kreaturen, die durch das Fokussieren von Energie Schaden "
        "erleiden, können den Schaden mit einem erfolgreichen Willenswurf halbieren (SG 10 + halbe "
        "Klerikerstufe + CH-Modifikator). Ein Kleriker kann diese Fähigkeit (3 + CH-Modifikator des "
        "Klerikers) Mal pro Tag einsetzen. Dies ist eine Standard-Aktion, die keinen Gelegenheitsangriff "
        "verursacht. Der Kleriker muss außerdem in der Lage sein, sein heiliges Symbol zu präsentieren, "
        "um diese Fähigkeit einsetzen zu können.",
    )
    for level in ENERGIE_FOKUSSIEREN_LEVELS:
        add_grant(energie_id, level)

    domaenen_id = add_ability(
        "Domänen",
        "Ein Kleriker sucht sich zwei Domänen von denen aus, die zu seiner Gottheit gehören. Ein "
        "Kleriker kann nur dann eine der Gesinnungsdomänen (Böses, Chaos, Gutes oder Ordnung) wählen, "
        "wenn seine eigene Gesinnung seiner Wahl entspricht. Jede Domäne bietet, abhängig von der Stufe "
        "des Klerikers, Domänenkräfte und eine Anzahl von Bonuszaubern. Der Kleriker erhält außerdem "
        "einen zusätzlichen Platz für Domänenzauber für jeden Grad an Zaubern, den er wirken kann. Wenn "
        "sich ein Domänenzauber nicht auf der Zauberliste für den Kleriker befindet, kann er ihn nur in "
        "dem Platz für Domänenzauber vorbereiten. Domänenzauber können nicht für das spontane Zaubern "
        "eingesetzt werden.",
    )
    add_grant(domaenen_id, 1)

    gebet_id = add_ability(
        "Gebet",
        "Der Kleriker kann eine Anzahl von Gebeten vorbereiten, die der Anzahl von Zaubern des 0. Grads "
        "in der Tabelle entspricht. Diese Zauber werden in Bezug auf Dauer und andere Variablen genau "
        "wie die anderen Zauber des Klerikers gehandhabt, nur dass sie nicht verbraucht werden, wenn der "
        "Kleriker sie wirkt, und erneut eingesetzt werden können.",
    )
    add_grant(gebet_id, 1)

    spontan_id = add_ability(
        "Spontanes Zaubern",
        "Ein guter Kleriker (oder ein neutraler Kleriker, der einen guten Gott verehrt) kann vorbereitete "
        "Zauberkraft nutzen, um sie in Heilung zu wandeln. Der Kleriker kann einen seiner vorbereiteten "
        "Zauber aufgeben, der weder Gebet noch Domänenzauber ist, um einen Heilzauber desselben Grades zu "
        "wirken. Als Heilzauber zählt jeder Zauber mit der Bezeichnung heilen im Titel. Ein böser Kleriker "
        "(oder ein neutraler Kleriker, der eine böse Gottheit verehrt) kann keinen Zauber in einen "
        "Heilzauber umwandeln, jedoch in einen Verletzungszauber des gleichen Grades (mit Wunden "
        "verursachen im Titel). Ein Kleriker, der weder gut noch böse ist, muss sich entscheiden, ob er "
        "Wunden heilen oder Wunden verursachen spontan zaubern möchte. Diese Wahl bestimmt auch, ob er "
        "positive (heilen) oder negative (Wunden verursachen) Energie fokussieren kann.",
    )
    add_grant(spontan_id, 1)

    gesinnungszauber_id = add_ability(
        "Böse, Chaotische, Gute und Rechtschaffene Zauber",
        "Ein Kleriker kann keinen Zauber wirken, dessen Gesinnung seiner oder der seiner Gottheit (falls "
        "er eine anbetet) entgegensteht. Zauber, die eine bestimmte Gesinnung voraussetzen, tragen eine "
        "entsprechende Bezeichnung in der Zauberbeschreibung.",
    )
    add_grant(gesinnungszauber_id, 1)

    bonussprachen_id = add_ability(
        "Bonussprachen",
        "Ein Kleriker kann, zusätzlich zu der Auswahl seines Volks, Bonussprachen aus der folgenden "
        "Liste wählen: Abyssisch, Celestisch und Infernalisch (die Sprache von bösen, chaotischen, "
        "guten oder rechtschaffenen Externaren).",
    )
    add_grant(bonussprachen_id, 1)

    ehemalige_id = add_ability(
        "Ehemalige Kleriker",
        "Ein Kleriker, der grob gegen die Gebote seines Glaubens verstößt, verliert all seine Zauber und "
        "Klassenmerkmale, außer dem Umgang mit Rüstungen, Schilden und einfachen Waffen. Er kann nicht "
        "weiter als Kleriker dieses Gottes aufsteigen, bis er Buße tut (siehe die Beschreibung des "
        "Zaubers Buße).",
    )
    add_grant(ehemalige_id, 1)

    # 33 domains x (1 overview + 2 named powers) = 99 domain ability rows,
    # each gated on that domain's own option_choice_id.
    for d in domains:
        cid = domain_choice_id[d["name"]]
        overview_id = add_ability(f"Verliehene Fähigkeiten ({d['name']})", d["granted"])
        add_grant(overview_id, 1, cid)
        for power in d["powers"]:
            aid = add_ability(power["name"], power["text"])
            add_grant(aid, power["level"], cid)

    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)

    print("Domains:", len(domains))
    print("New abilities:", len(abilities))
    print("New grants:", len(grants))
    print("Done.")


if __name__ == "__main__":
    main()
