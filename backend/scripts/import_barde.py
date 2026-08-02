"""Import the Barde (Bard) base class from
http://prd.5footstep.de/Grundregelwerk/Klassen/Barde into the seed JSON
files. Barde already had a correct `base_classes.json` row (hit dice W8, GAB
3/4, good Reflex/Will saves, 6 + INT skill points, CH casting, arcane
spontaneous) and a `base_class_spells.json` placeholder (8 spells, left
untouched here - full arcane spell list is a separate, larger gap, same
scope boundary as every other caster class import), but:

- `base_class_skills.json` had 20 rows, one of them wrong (`Mit Tieren
  umgehen` isn't a Barde class skill per the source's "Klassenfertigkeiten"
  line) and 9 missing (Beruf, Einschüchtern, Entfesselungskunst, Handwerk,
  Klettern, Schätzen, Wissen (Baukunst), Wissen (Gewölbekunde), Wissen
  (Geographie) - the source lists "Wissen (Alle)", same convention as the
  Magier import).
- Zero `BaseClassAbility`/`Grant` rows existed at all (no Bardenauftritt, no
  Bardenwissen, nothing) - added all 22 class-wide features from the page's
  "Klassenmerkmale" section, same depth as every other class import (catalog
  row + description text only, no computation - composition vs computation
  split from CLAUDE.md). Repeating/scaling features (Lied des Mutes, Lied
  des Erfolgs, Vielseitiger Auftritt, Gelehrter) use one ability row with
  multiple level-gated grants, same pattern as Kleriker's Energie
  fokussieren / Schurke's Hinterhältiger Angriff.
- `base_class_spells_known.json` ("Tabelle: Anzahl Bekannter Zauber") only
  had levels 1-6, and 3 of those rows were wrong (grade-2 count at levels
  4/5/6 was off by one: 1/2/3 instead of the source's 2/3/4). Replaced with
  the full, verified level 1-20 table.

No option group added for Vielseitiger Auftritt (Versatile Performance):
unlike domains/bloodlines/mysteries, its 9 performance-type choices
(Blasinstrumente, Gesang, Komik, ...) don't grant distinct named powers -
they're a skill-substitution list, closer to a talent-pool pick (like
Kämpfer's bonus feat or Waldläufer's combat style talent) than an
enumerable power set, so it stays prose-only for now, same scope decision
made for those.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database - run the normal seed scripts afterward):
    cd backend && python scripts/import_barde.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("6a0f2c9b-3e0a-4c9e-9f2b-2f5e7a6b9d10")

BARDE_ID = uuid.UUID("d86ed793-9019-4df6-a004-ded7e21c760b")

# Klassenfertigkeiten (Grundregelwerk): Akrobatik (GE), Auftreten (CH), Beruf
# (WE), Bluffen (CH), Diplomatie (CH), Einschüchtern (CH), Entfesselungskunst
# (GE), Fingerfertigkeit (GE), Handwerk (IN), Heimlichkeit (GE), Klettern
# (ST), Magischen Gegenstand benutzen (CH), Motiv erkennen (WE), Schätzen
# (IN), Sprachenkunde (IN), Verkleiden (CH), Wahrnehmung (WE), Wissen (Alle)
# (IN), Zauberkunde (IN). "Mit Tieren umgehen" is NOT on this list.
SKILLS_TO_ADD = [
    "Beruf",
    "Einschüchtern",
    "Entfesselungskunst",
    "Handwerk",
    "Klettern",
    "Schätzen",
    "Wissen (Baukunst)",
    "Wissen (Gewölbekunde)",
    "Wissen (Geographie)",
]
SKILL_TO_REMOVE = "Mit Tieren umgehen"

# "Tabelle: Anzahl Bekannter Zauber", grade -> count, per character level.
SPELLS_KNOWN = {
    1: {0: 4, 1: 2},
    2: {0: 5, 1: 3},
    3: {0: 6, 1: 4},
    4: {0: 6, 1: 4, 2: 2},
    5: {0: 6, 1: 4, 2: 3},
    6: {0: 6, 1: 4, 2: 4},
    7: {0: 6, 1: 5, 2: 4, 3: 2},
    8: {0: 6, 1: 5, 2: 4, 3: 3},
    9: {0: 6, 1: 5, 2: 4, 3: 4},
    10: {0: 6, 1: 5, 2: 5, 3: 4, 4: 2},
    11: {0: 6, 1: 6, 2: 5, 3: 4, 4: 3},
    12: {0: 6, 1: 6, 2: 5, 3: 4, 4: 4},
    13: {0: 6, 1: 6, 2: 5, 3: 5, 4: 4, 5: 2},
    14: {0: 6, 1: 6, 2: 6, 3: 5, 4: 4, 5: 3},
    15: {0: 6, 1: 6, 2: 6, 3: 5, 4: 4, 5: 4},
    16: {0: 6, 1: 6, 2: 6, 3: 5, 4: 5, 5: 4, 6: 2},
    17: {0: 6, 1: 6, 2: 6, 3: 6, 4: 5, 5: 4, 6: 3},
    18: {0: 6, 1: 6, 2: 6, 3: 6, 4: 5, 5: 4, 6: 4},
    19: {0: 6, 1: 6, 2: 6, 3: 6, 4: 5, 5: 5, 6: 4},
    20: {0: 6, 1: 6, 2: 6, 3: 6, 4: 6, 5: 5, 6: 5},
}


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


def fix_class_skills() -> None:
    skills = load("base_skills.json")
    skill_id_by_name = {row["name"]: row["id"] for row in skills}
    for name in SKILLS_TO_ADD + [SKILL_TO_REMOVE]:
        assert name in skill_id_by_name, f"missing skill: {name}"

    class_skills = load("base_class_skills.json")
    class_skills = [
        row
        for row in class_skills
        if not (row["base_class_id"] == str(BARDE_ID) and row["skill_id"] == skill_id_by_name[SKILL_TO_REMOVE])
    ]
    existing = {row["skill_id"] for row in class_skills if row["base_class_id"] == str(BARDE_ID)}
    for name in SKILLS_TO_ADD:
        sid = skill_id_by_name[name]
        if sid in existing:
            continue
        class_skills.append(
            {
                "id": uid("barde-classskill", name),
                "base_class_id": str(BARDE_ID),
                "skill_id": sid,
                "option_choice_id": None,
            }
        )
    save("base_class_skills.json", class_skills)


def fix_spells_known() -> None:
    rows = load("base_class_spells_known.json")
    rows = [row for row in rows if row["base_class_id"] != str(BARDE_ID)]
    for level, grades in SPELLS_KNOWN.items():
        for grade, count in grades.items():
            rows.append(
                {
                    "id": uid("barde-spellsknown", str(level), str(grade)),
                    "base_class_id": str(BARDE_ID),
                    "level": level,
                    "grade": grade,
                    "count": count,
                }
            )
    save("base_class_spells_known.json", rows)


def add_abilities() -> None:
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")

    def add_ability(name: str, description: str) -> str:
        aid = uid("barde-ability", name)
        abilities.append({"id": aid, "name": name, "description": description})
        return aid

    def add_grant(ability_id: str, level: int) -> None:
        grants.append(
            {
                "id": uid("barde-grant", ability_id, str(level)),
                "base_class_id": str(BARDE_ID),
                "ability_id": ability_id,
                "option_choice_id": None,
                "level": level,
            }
        )

    weapons_id = add_ability(
        "Umgang mit Waffen und Rüstungen",
        "Ein Barde ist im Umgang mit allen einfachen Waffen geschult. Zudem kann er mit Kurzbogen, "
        "Kurzschwert, Langschwert, Peitsche, Rapier und Totschläger umgehen. Barden können leichte "
        "Rüstungen tragen und sind im Umgang mit Schilden (außer Turmschilden) geübt. Ein Barde kann, "
        "während er eine leichte Rüstung und einen Schild trägt, zaubern, ohne für arkane Zauberpatzer "
        "würfeln zu müssen. Trägt er jedoch mittelschwere oder schwere Rüstung, riskiert er, wie jeder "
        "andere arkane Zauberkundige, einen Zauberpatzer, wenn der Zauber Gesten verlangt. Sein Vorteil, "
        "leichte Rüstung tragen zu dürfen, bezieht sich nur auf die Zauber, die er als Barde erhält. "
        "Verfügt er durch eine andere Klasse über arkane Zauber, so wird er bei diesen normal von der "
        "Chance für Zauberpatzer betroffen.",
    )
    add_grant(weapons_id, 1)

    zauber_id = add_ability(
        "Zauber",
        "Ein Barde kann arkane Zauber wirken, die er aus der Zauberliste für Barden auswählt. Er kann "
        "alle Zauber wirken, die er kennt, ohne sie vorbereiten zu müssen. Jeder Bardenzauber hat eine "
        "verbale Komponente (Gesang, Dichtkunst, Musik). Um einen Zauber zu lernen oder um ihn "
        "anzuwenden, muss ein Barde mindestens über ein Charisma von 10 + Grad des Zaubers verfügen. Der "
        "Schwierigkeitsgrad von Rettungswürfen gegen die Zauber des Barden ist 10 + Grad des Zaubers + "
        "CH-Modifikator des Barden. Wie andere Zauberkundige kann ein Barde nur eine bestimmte Menge von "
        "Zaubern je Stufe pro Tag wirken. Zusätzlich erhält er Bonuszauber für einen hohen Charismawert. "
        "Die Zauberauswahl des Barden ist sehr begrenzt. Ein Barde beginnt das Spiel mit vier Zaubern des "
        "0. Grads und zwei Zaubern des 1. Grads seiner Wahl. Jede Stufe erhält er einen oder mehrere "
        "Zauber hinzu, wie in Tabelle: Anzahl Bekannter Zauber zu erkennen ist. (Anders als die tägliche "
        "Anzahl von Zaubern wird diese Zahl nicht durch das Charisma des Barden verändert.) Wenn er die "
        "5. Stufe erreicht, und dann alle drei weiteren Stufen (8., 11., usw.), kann der Barde einen "
        "Zauber, den er kennt, gegen einen neuen austauschen. Er verliert dann den alten Zauber und "
        "ersetzt ihn durch einen neuen. Beide Zauber müssen den gleichen Grad haben und sie müssen "
        "mindestens einen Grad niedriger sein als der höchste Grad des Zaubers, den der Barde zur "
        "Verfügung hat. Der Barde kann auf einer Stufe aber nur einen Zauber wechseln und muss sich dafür "
        "entscheiden, sobald er neue Zauber erhält. Ein Barde muss seine Zauber nicht vorbereiten, "
        "sondern kann jeden Zauber wirken, den er kennt, vorausgesetzt er hat noch ausreichend Zauber pro "
        "Tag zur Verfügung.",
    )
    add_grant(zauber_id, 1)

    wissen_id = add_ability(
        "Bardenwissen",
        "Ein Barde addiert seine halbe Bardenstufe (mindestens 1) auf alle Wissensproben und er kann "
        "jede Wissensfertigkeit ungeübt benutzen.",
    )
    add_grant(wissen_id, 1)

    auftritt_id = add_ability(
        "Bardenauftritt",
        "Ein Barde ist darin geübt, seine Fertigkeit im Auftreten einzusetzen, um damit einen magischen "
        "Effekt auf jene in seiner Umgebung zu wirken, einschließlich sich selbst, wenn er es will. Er "
        "kann diese Fähigkeit für eine Anzahl von Runden am Tag in der Höhe seines CH-Modifikators +4 "
        "einsetzen. Beim Erreichen jeder weiteren Stufe verlängert sich der Einsatz um 2 zusätzliche "
        "Runden pro Tag. Jede Runde kann der Barde einen beliebigen seiner Auftritte zum Besten geben, "
        "die er gemeistert hat, wie es durch seine Stufe angegeben ist. Einen Bardenauftritt zu beginnen, "
        "ist eine Standard-Aktion, aber ihn in weiteren Runden aufrecht zu erhalten, ist eine Freie "
        "Aktion. Der Wechsel eines Bardenauftritts von einem zu einem anderen Effekt erfordert das "
        "Beenden des vorigen Auftritts, um den neuen Auftritt mit einer Standard-Aktion zu beginnen. Ein "
        "Bardenauftritt kann nicht gestört werden, aber er endet sofort, wenn der Barde getötet, "
        "gelähmt, betäubt oder bewusstlos geschlagen wird oder anders daran gehindert wird, eine Freie "
        "Aktion einzusetzen, um den Bardenauftritt aufrecht zu erhalten. Ein Barde kann nicht mehr als "
        "einen Auftritt gleichzeitig bewirken. Ab der 7. Stufe kann ein Barde einen Bardenauftritt im "
        "Rahmen einer Bewegungsaktion beginnen. Ab der 13. Stufe kann er einen Bardenauftritt als "
        "Schnelle Aktion beginnen. Jeder Bardenauftritt hat sichtbare Komponenten, hörbare Komponenten "
        "oder beides. Wenn ein Bardenauftritt eine hörbare Komponente hat, müssen die Ziele in der Lage "
        "sein, den Barden zu hören, damit der Auftritt seine Wirkung entfalten kann, und solche Auftritte "
        "sind auch abhängig von der Sprache. Ein tauber Barde erhält eine 20 % Fehlschlagchance, wenn er "
        "einen Auftritt wagt, bei dem es aufs Hören ankommt. Erleidet der Barde einen solchen Fehlschlag, "
        "so zählt der Versuch dennoch gegen die tägliche Gesamtdauer. Taube Wesen sind immun gegen "
        "Bardenauftritte mit hörbaren Komponenten. Wenn ein Bardenauftritt eine sichtbare Komponente hat, "
        "müssen die Ziele in der Lage sein, den Barden zu sehen, damit der Auftritt seine Wirkung "
        "entfalten kann. Ein blinder Barde erhält eine 50 % Fehlschlagchance, wenn er einen Auftritt "
        "wagt, bei dem es aufs Sehen ankommt. Erleidet der Barde einen solchen Fehlschlag, so zählt der "
        "Versuch dennoch gegen die tägliche Gesamtdauer. Blinde Wesen sind immun gegen Bardenauftritte "
        "mit sichtbaren Komponenten.",
    )
    add_grant(auftritt_id, 1)

    bannlied_id = add_ability(
        "Bannlied",
        "Ein Barde lernt auf der 1. Stufe, wie man einen magischen Effekt bannt, der auf Schall basiert "
        "(nur eine verbale Zauberkomponente reicht hierfür nicht aus). Während des Bannlieds macht der "
        "Barde jede Runde einen Fertigkeitswurf für Auftreten (Blas-, Saiten-, Schlag-, oder "
        "Tasteninstrumente oder Gesang). Jede Kreatur innerhalb von 9 m (inklusive des Barden selbst), "
        "die von einem Schall- oder auf Sprache basierenden magischen Effekt betroffen ist, kann das "
        "Resultat dieses Wurfs anstelle ihres Rettungswurfs benutzen, wenn dieser besser ist. Ist eine "
        "Kreatur innerhalb des Wirkungsbereichs schon Opfer eines Schall- oder auf Sprache basierenden, "
        "nicht augenblicklichen Effekts, erhält sie jede Runde, in der sie das Bannlied hört, einen "
        "erneuten Rettungswurf. Die Kreatur muss dabei jedoch das Ergebnis des Fertigkeitswurfs in "
        "Auftreten anstelle ihres eigenen Rettungswurfs anwenden. Das Bannlied funktioniert nur bei "
        "Effekten, die einen Rettungswurf erlauben. Das Bannlied ist auf eine hörbare Komponente "
        "angewiesen.",
    )
    add_grant(bannlied_id, 1)

    ablenkung_id = add_ability(
        "Ablenkung",
        "Ein Barde kann ab der 1. Stufe diesen Auftritt einsetzen, um einen magischen Effekt, der auf "
        "Sicht basiert, zu bannen. Jede Runde kann er einen Wurf für Auftreten ablegen (Schauspielkunst, "
        "Komik, Tanzen oder Redekunst). Jede Kreatur innerhalb von 9 m (inklusive des Barden selbst), die "
        "von einer Illusion (Einbildung oder Täuschung) betroffen wird, kann den Fertigkeitswurf in "
        "Auftreten des Barden anstelle seines Rettungswurfs nutzen, wenn dieser höher ist. Ist eine "
        "Kreatur im Wirkungsbereich bereits von einer nicht augenblicklichen Illusion (Einbildung oder "
        "Täuschung) betroffen, erhält sie jede Runde, in der sie die Ablenkung erblickt, einen neuen "
        "Rettungswurf, für den sie das Ergebnis des Fertigkeitswurfs in Auftreten anstelle ihres eigenen "
        "Rettungswurfs nehmen muss. Ablenkung wirkt nur, wenn der Effekt einen Rettungswurf zulässt. "
        "Ablenkung ist auf eine sichtbare Komponente angewiesen.",
    )
    add_grant(ablenkung_id, 1)

    faszinieren_id = add_ability(
        "Faszinieren",
        "Ein Barde kann diese Fähigkeit ab der 1. Stufe nutzen, um mit Hilfe von Musik oder Poesie eine "
        "oder mehrere Kreaturen zu faszinieren. Damit eine Kreatur davon betroffen werden kann, muss "
        "diese innerhalb von 27 m sein, den Barden sowohl hören als auch sehen können und in der Lage "
        "sein, ihm Aufmerksamkeit zu schenken. Auch der Barde muss die Ziele sehen können. Ablenkungen, "
        "wie durch einen Kampf in der Nähe, verhindern das Wirken dieses Bardenauftritts. Für jeweils "
        "drei Stufen ab der 1. kann der Barde eine weitere Kreatur einbeziehen. Jede Kreatur innerhalb "
        "der Reichweite muss einen Willenswurf (SG 10 + ½ Bardenstufe + CH-Modifikator des Barden) "
        "bestehen, um den Effekt zu negieren. Gelingt der Kreatur der Willenswurf, kann der Barde "
        "innerhalb der nächsten 24 Stunden nicht versuchen, sie ein weiteres Mal zu faszinieren. "
        "Misslingt der Rettungswurf, sitzt das Ziel ruhig da und betrachtet den Auftritt, ohne eine "
        "andere Aktion zu unternehmen, solange der Barde den Auftritt weiterhin aufrechterhält. Während "
        "die Kreatur fasziniert ist, erhält sie einen Malus von –4 auf Fertigkeitsproben, die als "
        "Reaktion gemacht werden, wie zum Beispiel Wahrnehmung. Jede mögliche Gefahr erlaubt dem Ziel "
        "einen neuen Willenswurf. Jede offensichtliche Bedrohung, wie das Ziehen einer Waffe, das Wirken "
        "eines Zauberspruchs oder das Richten einer Waffe auf das Ziel, beendet den Effekt automatisch. "
        "Faszinieren ist eine Verzauberungs-(Zwang) und geistesbeeinflussende Fähigkeit. Faszinieren ist "
        "auf sichtbare und hörbare Komponenten angewiesen, um zu wirken.",
    )
    add_grant(faszinieren_id, 1)

    mut_id = add_ability(
        "Lied des Mutes",
        "Ein Barde kann ab der 1. Stufe mit diesem Auftritt den Mut seiner Verbündeten (inklusive seiner "
        "selbst) verbessern, stärkt sie gegen Furcht und verbessert ihre Kampfkraft. Die Verbündeten "
        "müssen in der Lage sein, den Barden zu hören, um von dieser Fähigkeit zu profitieren. Ein "
        "Verbündeter erhält einen Moralbonus von +1 auf Rettungswürfe gegen Bezaubern und Furcht. "
        "Zusätzlich erhält er einen Kompetenzbonus von +1 auf Angriffswürfe und Waffen-Schadenswürfe. Ab "
        "der 5. Stufe und alle weiteren sechs Stufen erhöht sich dieser Bonus um +1 bis zu einem Maximum "
        "von +4 auf der 17. Stufe. Das Lied des Mutes ist eine geistesbeeinflussende Fähigkeit. Das Lied "
        "des Mutes ist auf sichtbare oder hörbare Komponenten angewiesen. Der Barde muss zu Beginn seines "
        "Auftritts auswählen, welche Art der Komponente er verwendet.",
    )
    for level in (1, 5, 11, 17):
        add_grant(mut_id, level)

    tricks_id = add_ability(
        "Zaubertricks",
        "Der Barde lernt eine Anzahl von Zaubertricks oder Zaubern des 0. Grads, wie in der Tabelle: "
        "Anzahl Bekannte Zauber angegeben ist. Diese Zauber werden wie andere Zauber gewirkt. Sie können "
        "jedoch beliebig oft am Tag gewirkt werden.",
    )
    add_grant(tricks_id, 1)

    bewandert_id = add_ability(
        "Bewandert",
        "Auf der 2. Stufe wird der Barde resistent gegen Bardenauftritte von anderen und gegen "
        "Schalleffekte generell. Er erhält einen Bonus von +4 auf Rettungswürfe gegen Bardenauftritt, "
        "Schallangriffe und sprachabhängige Effekte.",
    )
    add_grant(bewandert_id, 2)

    vielseitig_id = add_ability(
        "Vielseitiger Auftritt",
        "Auf der 2. Stufe kann der Barde eine Art der Fertigkeit Auftreten auswählen. Er kann den Bonus "
        "in dieser Fertigkeit anstelle seiner Boni in den dazugehörigen Fertigkeiten einsetzen. Wenn er "
        "auf diese Art und Weise seine Fertigkeit ersetzt, verwendet er den gesamten Fertigkeitsbonus, "
        "Bonus für einen Klassenbonus mit eingerechnet, egal ob die ersetzte Fertigkeit eine "
        "Klassenfertigkeit ist, oder der Barde darin noch keinen Rang hat. Auf der sechsten Stufe und "
        "alle weiteren vier Stufen kann der Barde eine weitere Art des Auftretens fürs Ersetzen "
        "auswählen. Die Arten des Auftretens und ihre dazugehörigen Fertigkeiten sind: Blasinstrumente "
        "(Diplomatie, Mit Tieren umgehen), Gesang (Bluffen, Motiv erkennen), Komik (Bluffen, "
        "Einschüchtern), Redekunst (Diplomatie, Motiv erkennen), Saiteninstrumente (Bluffen, "
        "Diplomatie), Schauspielkunst (Bluffen, Verkleiden), Schlaginstrumente (Mit Tieren umgehen, "
        "Einschüchtern), Tanzen (Akrobatik, Fliegen), Tasteninstrumente (Diplomatie, Einschüchtern).",
    )
    for level in (2, 6, 10, 14, 18):
        add_grant(vielseitig_id, level)

    erfolg_id = add_ability(
        "Lied des Erfolgs",
        "Ein Barde der 3. oder höheren Stufe kann diese Fähigkeit dazu nutzen, einen Verbündeten bei der "
        "Bewältigung einer Aufgabe zu unterstützen. Der Verbündete muss sich innerhalb von 9 m in der "
        "Nähe des Barden befinden und diesen hören können. Der Verbündete erhält einen Kompetenzbonus von "
        "+2 auf Würfe für eine bestimmte Fertigkeit, solange er den Auftritt des Barden hört. Dieser "
        "Bonus erhöht sich um +1 für alle weiteren vier Stufen, die der Barde nach der 3. Stufe erreicht "
        "hat (+3 auf der 7. Stufe, +4 auf der 11., +5 auf der 15. und +6 auf der 19. Stufe). Manch eine "
        "Aufgabe lässt sich nicht mit Hilfe dieser Fähigkeit unterstützen, wie zum Beispiel ein "
        "Fertigkeitswurf in Heimlichkeit. Der SL kann daher den Einsatz dieser Fähigkeit in solchen "
        "Fällen verbieten. Der Barde kann diese Fähigkeit nicht auf sich selbst wirken. Das Lied des "
        "Erfolgs ist auf hörbare Komponenten angewiesen.",
    )
    for level in (3, 7, 11, 15, 19):
        add_grant(erfolg_id, level)

    gelehrter_id = add_ability(
        "Gelehrter",
        "Auf der 5. Stufe wird der Barde ein wahrer Gelehrter. Er kann bei jeder Wissensfertigkeit, in "
        "der er Ränge hat, 10 nehmen, wenn er dies wünscht. Ein Mal pro Tag kann der Barde bei einer "
        "Wissensprobe als Standard-Aktion 20 nehmen. Er kann dies für jeweils sechs Stufen über der 5. "
        "Stufe ein weiteres Mal pro Tag nutzen, bis zu einem Maximum von drei Mal auf der 17. Stufe.",
    )
    for level in (5, 11, 17):
        add_grant(gelehrter_id, level)

    einfluesterung_id = add_ability(
        "Einflüsterung",
        "Ein Barde der 6. oder einer höheren Stufe kann eine Einflüsterung (wie der gleichnamige Zauber) "
        "gegen ein Ziel versuchen, das bereits fasziniert ist. Diese Fähigkeit unterbricht nicht die "
        "Auswirkungen vom Faszinieren, aber es erfordert eine Standard-Aktion, um sie zu aktivieren "
        "(zusätzlich zu der Freien Aktion, um das Faszinieren aufrecht zu erhalten). Ein Barde kann diese "
        "Fähigkeit mehr als ein Mal gegen eine einzelne Kreatur während eines einzelnen Auftritts "
        "einsetzen. Eine Einflüsterung zählt für den Barden nicht gegen sein tägliches Pensum an "
        "Bardenauftritten. Ein Willenswurf (SG 10 + ½ Stufe des Barden + CH-Modifikator des Barden) "
        "negiert den Effekt. Diese Fähigkeit betrifft nur ein einzelnes Ziel. Einflüsterung ist eine "
        "Verzauberungs- (Zwang) und geistesbeeinflussende Fähigkeit, die sprachabhängig und auf hörbare "
        "Komponenten angewiesen ist.",
    )
    add_grant(einfluesterung_id, 6)

    klagelied_id = add_ability(
        "Klagelied",
        "Ein Barde der 8. oder einer höheren Stufe kann diese Fähigkeit dazu nutzen, um Furcht in den "
        "Herzen seiner Feinde zu säen, die sie erschüttert sein lässt. Um von dem Klagelied betroffen zu "
        "werden, muss das Ziel innerhalb von 9 m in der Nähe des Barden sein und ihn hören und sehen "
        "können. Der Effekt hält an, solange das Ziel in der Reichweite ist und der Barde den Auftritt "
        "weiter führt. Dieser Auftritt kann eine Kreatur nicht verängstigen oder in Panik verfallen "
        "lassen, auch wenn die Ziele schon vorher durch einen anderen Effekt erschüttert sind. Das "
        "Klagelied ist ein geistesbeeinflussender Furchteffekt und ist auf hörbare und sichtbare "
        "Komponenten angewiesen.",
    )
    add_grant(klagelied_id, 8)

    groesse_id = add_ability(
        "Lied der Größe",
        "Ein Barde der 9. oder einer höheren Stufe kann diesen Auftritt einsetzen, um in sich selbst oder "
        "bei einem einzelnen willigen Verbündeten innerhalb von 9 Metern wahre Größe zu erzeugen und die "
        "Kampffähigkeiten zu verbessern. Für jeweils drei Stufen über der 9. kann der Barde einen "
        "weiteren Verbündeten mit einbeziehen (zwei auf der 12. Stufe, drei auf der 15. Stufe und vier "
        "auf der 18. Stufe). Der Verbündete muss den Barden sehen und hören können. Eine Kreatur, die von "
        "dem Lied der Größe betroffen wird, erhält zwei Bonustrefferwürfel (2W10), die entsprechende "
        "Anzahl als Temporäre Trefferpunkte (diese Punkte aus den Bonustrefferwürfeln werden um den "
        "KO-Modifikator abgewandelt, falls vorhanden), einen Kompetenzbonus von +2 auf Angriffe und einen "
        "Kompetenzbonus von +1 auf Zähigkeitswürfe. Die Trefferwürfel zählen auch bei Effekten, die "
        "trefferwürfelabhängig sind. Das Lied der Größe ist eine geistesbeeinflussende Fähigkeit und ist "
        "auf hörbare und sichtbare Komponenten angewiesen.",
    )
    add_grant(groesse_id, 9)

    tausendsassa_id = add_ability(
        "Tausendsassa",
        "Auf der 10. Stufe kann der Barde jede Fertigkeit nutzen, selbst wenn sie normalerweise nur "
        "trainiert genutzt werden darf. Ab der 16. Stufe zählen alle Fertigkeiten als Klassenfertigkeiten. "
        "Auf der 19. Stufe kann er für jede Fertigkeit 10 nehmen, selbst wenn dies normalerweise nicht "
        "gestattet ist.",
    )
    add_grant(tausendsassa_id, 10)

    erfrischend_id = add_ability(
        "Erfrischender Auftritt",
        "Ein Barde der 12. oder einer höheren Stufe kann seinen Auftritt nutzen, um einen Effekt herbei "
        "zu rufen, der wie Massen-Schwere Wunden heilen (Bardenstufe entspricht der Zauberstufe) wirkt. "
        "Zusätzlich hebt der Auftritt noch die Effekte erschöpft, kränkelnd und erschüttert auf. Um die "
        "Effekte dieses Auftritts einsetzen zu können, muss der Barde diesen Auftritt 4 Runden lang "
        "ununterbrochen aufführen. Die Ziele müssen den Barden während dieses Auftritts hören und sehen "
        "können. Ein Erfrischender Auftritt betrifft alle Ziele, die während der Auftritts innerhalb von "
        "9 m geblieben sind. Der Erfrischende Auftritt ist auf hörbare und sichtbare Komponenten "
        "angewiesen.",
    )
    add_grant(erfrischend_id, 12)

    furcht_id = add_ability(
        "Lied der Furcht",
        "Ein Barde der 14. oder einer höheren Stufe kann seine Gegner in Angst versetzten. Ein Gegner, "
        "der den Barden hören kann und sich innerhalb von 9 m in der Nähe des Barden aufhält, wird von "
        "dem Effekt betroffen und kann einen Willenswurf (SG 10 + ½ Bardenstufe + CH-Modifikator des "
        "Barden) machen, um ihn zu negieren. Gelingt dem Gegner dies, ist er für 24 Stunden gegen diese "
        "Fähigkeit immun. Misslingt der Rettungswurf, ist das Ziel verängstigt und ergreift die Flucht, "
        "solange es den Auftritt des Barden hören kann. Das Lied der Furcht ist auf hörbare Komponenten "
        "angewiesen.",
    )
    add_grant(furcht_id, 14)

    heldenmut_id = add_ability(
        "Lied des Heldenmuts",
        "Ein Barde der 15. oder einer höheren Stufe kann in sich selbst oder bei einem Verbündeten "
        "innerhalb von 9 m besonderen Heldenmut hervorrufen. Für jeweils drei Stufen über der 15. kann "
        "der Barde mit diesem Lied einen weiteren Verbündeten betreffen. Um das Lied des Heldenmuts zu "
        "wirken, müssen alle betroffenen Verbündeten den Barden sehen und hören können. Ein vom "
        "Heldenmut erfülltes Wesen erhält einen Moralbonus von +4 auf Rettungswürfe und einen "
        "Ausweichbonus von +4 auf die Rüstungsklasse. Dieser Effekt dauert so lange an, wie die "
        "betroffenen Ziele in der Lage sind dem Auftritt zu folgen. Das Lied des Heldenmutes ist ein "
        "geistesbeeinflussender Effekt, der auf hörbare und sichtbare Komponenten angewiesen ist.",
    )
    add_grant(heldenmut_id, 15)

    masseneinfluesterung_id = add_ability(
        "Masseneinflüsterung",
        "Ein Barde der 18. oder einer höheren Stufe kann diese Fähigkeit nutzen, die genau wie "
        "Einflüsterung funktioniert, nur dass eine beliebige Anzahl von Kreaturen betroffen wird, die "
        "schon fasziniert sind. Masseneinflüsterung ist eine Verzauberungs- (Zwang) und "
        "geistesbeeinflussende Fähigkeit, die sprachabhängig ist und auf hörbare Komponenten angewiesen "
        "ist.",
    )
    add_grant(masseneinfluesterung_id, 18)

    melodie_id = add_ability(
        "Tödliche Melodie",
        "Auf der 20. Stufe kann ein Barde diesen Auftritt einsetzen, um einen Gegner vor Freude oder "
        "Kummer sterben zu lassen. Um betroffen zu sein, muss das Ziel den Barden sehen und hören können, "
        "wie er seinen Auftritt für eine Volle Runde aufrecht erhält, und innerhalb von 9 m sein. Das "
        "Opfer kann den Effekt mit einem Willenswurf (SG 10 + ½ Bardenstufe + CH-Modifikator des Barden) "
        "abwenden. Gelingt der Rettungswurf, ist das Ziel für 1W4 Runden wankend und kann für die "
        "nächsten 24 Stunden nicht mehr Opfer dieser Fähigkeit werden. Misslingt der Rettungswurf, stirbt "
        "das Ziel. Tödliche Melodie ist ein geistesbeeinflussender Todeseffekt, der auf hörbare und "
        "sichtbare Komponenten angewiesen ist.",
    )
    add_grant(melodie_id, 20)

    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)

    print("New abilities:", len(abilities))
    print("New grants:", len(grants))


def main() -> None:
    fix_class_skills()
    fix_spells_known()
    add_abilities()
    print("Done.")


if __name__ == "__main__":
    main()
