"""Import the four Kampfmagus archetypes from
http://prd.5footstep.de/AusbauregelnIIKampf/Archetypen/Kampfmagus (Kensai,
Seelenschmied, Skirnir, Zauberstreiter) into the seed JSON files. Same shape
as `import_ork_archetypes.py`: one archetype `BaseClass` row per archetype
(`arch_class_of` = `KAMPFMAGUS_ID`, from `import_kampfmagus.py` - run that
script first), new `BaseClassAbility`/`BaseClassAbilityGrant` rows under
each archetype's own class id, `BaseClassAbilityReplacement` rows scoping
each to the specific parent Kampfmagus grant(s) it replaces. Unlike the Ork
script, the parent grant ids aren't hand-copied literals (Kampfmagus is
brand new, not a pre-existing row this script could paste ids from) - they're
looked up at runtime by `(ability name, level)` against whatever
`import_kampfmagus.py` actually seeded, so a wording/level fix there can't
silently desync this script's replacement targets.

**Replacement vs. addition, decided the same way `import_ork_archetypes.py`
already does**: a feature only gets a `BaseClassAbilityReplacement` row when
its own PRD text says "Dieses Klassenmerkmal ersetzt X" (naming the exact
parent feature(s)). Three archetype features use "kann dieses Klassenmerkmal
nur einsetzen, wenn ..." (a usage restriction) or "kann diese Fähigkeit mit
... einsetzen" (an extension) instead of "ersetzt" - Seelenschmied's
restricted Kampfzauberei/Zauberschlag (only while wielding the bound weapon)
and Skirnir's extended Zauberschlag (also usable with a shield bash). These
are added as the archetype's own new `BaseClassAbility` rows with NO
replacement row, same precedent as the Ork script's Fetischmaske/
Konstitutionsabhängig (added, nothing named as replaced). All three
archetypes' own "Vermindertes Zauberwirken" paragraph (one fewer spell slot
per grade) is modeled the same way for a different reason: there is no
`BaseClassSpellsKnown`/slot-count field for arcane-prepared classes at all
(`known.count` is unused/nullable for that spell type - see
`import_kampfmagus.py`'s docstring and `rules/spells.py`), so there is
nothing this schema could replace even if the text said "ersetzt" - added as
a plain descriptive ability, granted at 1st, with no replacement and no
mechanical effect, same "real boundary, not a time question" call every
other class script makes for something its schema can't express yet.

Each archetype's own "Arkana: Die folgenden Arkana sind für den Archetypen
... geeignet: ..." footnote (restricting/recommending a subset of the 39
Arkana `import_kampfmagus.py` seeded) is also deliberately NOT modeled:
`BaseClassOptionChoice` has exactly one scoping column for "only legal for
some characters" (`race_id`), no `archetype_id` equivalent - adding one
would be new schema, not a data change, and every Arkanum in these lists
already exists as a normal Kampfmagus-wide choice a character of that
archetype can simply pick anyway (the footnote is a recommendation, not a
hard restriction stated as "kann nur ... wählen").

No handler-side computation for any of this - composition only, per
CLAUDE.md.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database - run import_kampfmagus.py first, then the
normal seed scripts afterward):
    cd backend && python scripts/import_kampfmagus.py
    python scripts/import_kampfmagus_archetypes.py
    python -m app.seed.class_seed
    python -m app.seed.skill_seed
    python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("2d8f4a6c-9b1e-4c3a-8f5d-6a7b8c9d0e1f")

KAMPFMAGUS_ID = "cebfc2a3-02fc-561a-8467-7f88ba567b01"

VERMINDERTES_ZAUBERWIRKEN = (
    "Ein {name} besitzt pro Zaubergrad einen Zauberplatz weniger. Sollte dies die tägliche Anzahl der "
    "verfügbaren Zauber eines Grades auf 0 reduzieren, kann er nur dann Zauber dieses Grades wirken, "
    "wenn er Bonuszauber aufgrund seiner Intelligenz für diesen Grad erhält."
)

WAFFENFOKUS_FEAT_ID = "bd72fbe8-e7ae-4eb0-b74c-fbc295f306c8"

# (name, levels, description, replaces=[(ability_name, level), ...], granted_feat_ids)
Feature = tuple[str, list[int], str, list[tuple[str, int]], list[str]]

KENSAI_FEATURES: list[Feature] = [
    (
        "Umgang mit Waffen und Rüstungen (Kensai)",
        [1],
        "Ein Kensai ist geübt im Umgang mit Einfachen Waffen und einer einzelnen Kriegswaffe oder "
        "Exotischen Waffe seiner Wahl. Ein Kensai ist nicht geübt im Umgang mit Rüstungen oder "
        "Schilden und erleidet die normale Patzerchance bei arkanen Zaubern, wenn er "
        "Kampfmaguszauber in Rüstung wirkt. Dieses Klassenmerkmal ersetzt Umgang mit Waffen und "
        "Rüstungen.",
        [("Umgang mit Waffen und Rüstungen", 1)],
        [],
    ),
    (
        "Gewitzte Verteidigung",
        [1],
        "(AF) Mit Beginn der 1. Stufe erhält ein Kensai das Klassenmerkmal Gewitzte Verteidigung, "
        "wenn er seine ausgewählte Waffe führt. Dies ist identisch mit dem Klassenmerkmal der "
        "Duellanten-Prestigeklasse; er ist bei der Wahl seiner ausgewählten Waffe aber nicht "
        "eingeschränkt.",
        [],
        [],
    ),
    (
        "Waffenfokus (Kensai)",
        [1],
        "(AF) Mit Beginn der 1. Stufe erhält ein Kensai Waffenfokus mit seiner ausgewählten Waffe.",
        [],
        [WAFFENFOKUS_FEAT_ID],
    ),
    (
        "Perfekter Schlag",
        [4],
        "(AF) Mit Beginn der 4. Stufe kann ein Kensai, welcher mit seiner ausgewählten Waffe sein "
        "Ziel trifft, 1 Punkt seines Arkanen Vorrats einsetzen, um den Waffenschaden zu maximieren; "
        "zusätzlicher Schaden wie Präzisionsschaden, Schaden aufgrund Kritischer Treffer sowie "
        "magischer Waffeneigenschaften oder Zauberschlag wird aber normal ausgewürfelt. Sollte der "
        "Kensai einen Kritischen Treffer bestätigen, kann er stattdessen 2 Punkte seines Arkanen "
        "Vorrats einsetzen, um den Kritischen Schadensmultiplikator seiner Waffe um 1 zu erhöhen. "
        "Dieses Klassenmerkmal ersetzt Zauberrückruf.",
        [("Zauberrückruf", 4)],
        [],
    ),
    (
        "Kämpferausbildung (Kensai)",
        [7],
        "(AF) Hinsichtlich der Voraussetzungen für Talente hat ein Kensai mit Beginn der 7. Stufe "
        "eine effektive Kämpferstufe in Höhe seiner Stufe als Kampfmagus -3. Sollte er über Stufen "
        "als Kämpfer verfügen, so sind diese kumulativ. Er erhält den Vorteil solcher Talente aber "
        "nur im Umgang mit seiner ausgewählten Waffe. Dieses Klassenmerkmal ersetzt Wissensvorrat.",
        [("Wissensvorrat", 7)],
        [],
    ),
    (
        "Iaijutsu",
        [7],
        "(AF) Mit Beginn der 7. Stufe addiert ein Kensai neben seinem GE-Modifikator auch seinen "
        "IN-Modifikator auf seine Initiativewürfe (Minimum 0). Ein Kensai kann mit seiner "
        "bevorzugten Waffe auch Gelegenheitsangriffe ausführen, wenn er sich auf dem falschen Fuß "
        "befindet, und seine bevorzugte Waffe mit einer Freien Aktion ziehen, wenn dies Teil des "
        "Gelegenheitsangriffes ist. Dieses Klassenmerkmal ersetzt das Klassenmerkmal Mittelschwere "
        "Rüstung.",
        [("Mittelschwere Rüstung", 7)],
        [],
    ),
    (
        "Kritische Perfektion",
        [9],
        "(AF) Mit Beginn der 9. Stufe addiert ein Kensai bei seiner bevorzugten Waffe seinen "
        "IN-Bonus (Minimum 0) auf Bestätigungswürfe für Kritische Treffer. Ferner behandelt er "
        "seine Stufe als Kampfmagus anstatt seinen Grundangriffsbonus als Voraussetzung für das "
        "Talent Kritischer-Treffer-Fokus und alle Talente, für welche dieses Talent eine "
        "Voraussetzung ist - nur bei der bevorzugten Waffe des Kensai. Dieses Klassenmerkmal "
        "ersetzt das Arkanum, welches ein Kampfmagus mit der 9. Stufe erhält.",
        [("Arkanum", 9)],
        [],
    ),
    (
        "Überlegene Reflexe",
        [11],
        "(AF) Mit Beginn der 11. Stufe kann ein Kensai in einer Runde eine Anzahl von "
        "Gelegenheitsangriffen in Höhe seines IN-Modifikators ausführen (Minimum 1). Dieser Effekt "
        "ist kumulativ mit dem Talent Kampfreflexe. Dieses Klassenmerkmal ersetzt Verbesserter "
        "Zauberrückruf.",
        [("Verbesserter Zauberrückruf", 11)],
        [],
    ),
    (
        "Iaijutsu-Fokus",
        [13],
        "(AF) Mit Beginn der 13. Stufe kann ein Kensai stets während einer Überraschungsrunde "
        "handeln und seine Waffe mit einer Schnellen Aktion ziehen, auch wenn er als auf dem "
        "Falschen Fuß erwischt gilt. Während einer Überraschungsrunde oder wenn er einen Gegner auf "
        "dem falschen Fuß erwischt, addiert er seinen IN-Modifikator auf seine Schadenswürfe mit "
        "seiner ausgewählten Waffe (Minimum 0). Dieses Klassenmerkmal ersetzt Schwere Rüstung.",
        [("Schwere Rüstung", 13)],
        [],
    ),
    (
        "Iaijutsu-Meister",
        [19],
        "(AF) Mit Beginn der 19. Stufe wird der Initiativewurf eines Kensai immer automatisch als "
        "natürliche 20 behandelt und er gilt niemals als Überrascht. Dieses Klassenmerkmal ersetzt "
        "Mächtiger Zugang zu Zaubern.",
        [("Mächtiger Zugang zu Zaubern", 19)],
        [],
    ),
    (
        "Waffenmeisterschaft (Kensai)",
        [20],
        "(AF) Mit Beginn der 20. Stufe erhält ein Kensai Waffenmeisterschaft mit seiner bevorzugten "
        "Waffe. Dies entspricht dem Klassenmerkmal des Kämpfers. Dieses Klassenmerkmal ersetzt "
        "Wahrer Kampfmagus.",
        [("Wahrer Kampfmagus", 20)],
        [],
    ),
]

SEELENSCHMIED_FEATURES: list[Feature] = [
    (
        "Arkane Bindung (Seelenschmied)",
        [1],
        "(ÜF) Mit Beginn der 1. Stufe erhält ein Seelenschmied eine Waffe als Gegenstand einer "
        "Arkanen Verbindung. Dieses Klassenmerkmal ist identisch mit dem Klassenmerkmal des "
        "Magiers, allerdings kann der Seelenschmied nur mit einer Waffe eine Bindung eingehen, "
        "nicht mit einem Vertrauten oder Gegenstand.",
        [],
        [],
    ),
    (
        "Kampfzauberei (Seelenschmied)",
        [1],
        "(ÜF) Ein Seelenschmied kann das Klassenmerkmal Kampfzauberei nur einsetzen, wenn er seine "
        "gebundene Waffe führt.",
        [],
        [],
    ),
    (
        "Zauberschlag (Seelenschmied)",
        [2],
        "(ÜF) Ein Seelenschmied kann das Klassenmerkmal Zauberschlag nur einsetzen, wenn er seine "
        "gebundene Waffe führt.",
        [],
        [],
    ),
    (
        "Bindung festigen",
        [4],
        "(ÜF) Mit Beginn der 4. Stufe kann ein Seelenschmied 1 Punkt seines Arkanen Vorrats "
        "aufwenden, um die Härte und Trefferpunkte seines gebundenen Gegenstandes in Höhe seiner "
        "Stufe als Kampfmagus zu erhöhen. Diese Trefferpunkte halten an, bis sie verbraucht werden "
        "oder der Seelenschmied wieder Zauber vorbereitet. Mehrere Anwendungen dieser Fähigkeit "
        "sind nicht mit sich selbst kumulativ. Dieses Klassenmerkmal ersetzt Zauberrückruf.",
        [("Zauberrückruf", 4)],
        [],
    ),
    (
        "Meisterschmied",
        [7],
        "(AF) Ein Seelenschmied addiert seine Stufe als Kampfmagus als Bonus auf seine "
        "Fertigkeitswürfe für Handwerk, um Waffen, Schilde und Rüstungen herzustellen (auch beim "
        "Talent Magische Waffen und Rüstungen herstellen). Mit Beginn der 7. Stufe legt ein "
        "Seelenschmied 1/10 des Preises von Waffen, Schilden und Rüstungen zugrunde, um die "
        "Herstellungsdauer nichtmagischer Gegenstände zu berechnen, und benötigt nur die Hälfte der "
        "Zeit, um magische Waffen und Rüstungen zu verzaubern. Dieses Klassenmerkmal ersetzt "
        "Wissensvorrat.",
        [("Wissensvorrat", 7)],
        [],
    ),
    (
        "Umschmieden",
        [11],
        "(ÜF) Indem er 1 Punkt seines Arkanen Vorrats einsetzt, kann ein Seelenschmied mit Beginn "
        "der 11. Stufe mit einer Standard-Aktion bei einem beschädigten Gegenstand durch Berührung "
        "eine Anzahl von Trefferpunkten in Höhe seiner Stufe als Kampfmagus wiederherstellen. Um "
        "einen zerstörten Gegenstand zu reparieren, benötigt er 1 Minute und Materialien im Wert "
        "von ¼ des Verkaufswertes des Gegenstandes und stellt ihn mit 1 TP wieder her; um die "
        "Verzauberungen eines zerstörten magischen Gegenstandes wiederherzustellen, muss er "
        "zusätzliche Punkte seines Arkanen Vorrats in Höhe der Zauberstufe des Gegenstandes "
        "einsetzen (mit einer temporären negativen Stufe, deren Höhe von der Zauberstufe des "
        "Gegenstandes im Vergleich zu seiner eigenen abhängt, außer bei seiner gebundenen Waffe). "
        "Dieses Klassenmerkmal ersetzt Verbesserter Zauberrückruf.",
        [("Verbesserter Zauberrückruf", 11)],
        [],
    ),
    (
        "Zerstörerischer Gegenschlag",
        [16],
        "(ÜF) Mit Beginn der 16. Stufe provoziert ein Gegner, der einen magischen Gegenstand "
        "innerhalb des Bedrohungsbereichs des Seelenschmieds aktiviert, einen Gelegenheitsangriff "
        "durch diesen - entweder gegen das Ziel oder gegen den Gegenstand, um ihn zu zerschmettern "
        "(dessen Effekte dann aufgehoben werden). Dieses Klassenmerkmal ersetzt Gegenschlag.",
        [("Gegenschlag", 16)],
        [],
    ),
    (
        "Augenblickliche Wiederherstellung",
        [19],
        "(ÜF) Mit Beginn der 19. Stufe kann ein Seelenschmied mit einer Berührung einen zerstörten "
        "Gegenstand mit einer Standard-Aktion wiederherstellen, ohne dabei einen Gelegenheitsangriff "
        "zu provozieren. Dieses Klassenmerkmal ersetzt Mächtiger Zugang zu Zaubern.",
        [("Mächtiger Zugang zu Zaubern", 19)],
        [],
    ),
]

SKIRNIR_FEATURES: list[Feature] = [
    (
        "Arkane Verbindung (Skirnir)",
        [1],
        "(ÜF) Mit Beginn der 1. Stufe erhält ein Skirnir einen Schild (keinen Turmschild) als "
        "Gegenstand einer Arkanen Verbindung. Dieses Klassenmerkmal ist identisch mit dem "
        "Klassenmerkmal des Magiers, allerdings kann der Skirnir nur mit einem Schild eine Bindung "
        "eingehen, nicht mit einem Vertrauten oder Gegenstand.",
        [],
        [],
    ),
    (
        "Arkaner Vorrat (Skirnir)",
        [1],
        "Mit Beginn der 1. Stufe kann ein Skirnir seinen Arkanen Vorrat nutzen, um auch seinem "
        "Schild (statt nur einer Waffe) einen Verbesserungsbonus zu verleihen - die Kosten hierfür "
        "werden separat bezahlt. Ab der 5. Stufe kann er seinen Schild zudem mit den folgenden "
        "besonderen Eigenschaften versehen: Belebung, Geschosse anziehend, Geschossabwehr, "
        "Schmettern, Blendend, Bollwerk (jedes), Zauberresistenz (jede).",
        [],
        [],
    ),
    (
        "Schild des Skirnirs",
        [1],
        "(AF) Mit Beginn der 1. Stufe ist ein Skirnir geübt im Umgang mit allen Schilden, auch "
        "Turmschilden. Er unterliegt keiner arkanen Patzerchance, wenn er beim Wirken von "
        "Kampfmaguszaubern einen Schild trägt. Hinsichtlich schildbezogener Talente besitzt der "
        "Skirnir eine effektive Kämpferstufe in Höhe seiner Stufe als Kampfmagus. Dieses "
        "Klassenmerkmal ersetzt Kampfzauberei.",
        [("Kampfzauberei", 1)],
        [],
    ),
    (
        "Zauberschlag (Skirnir)",
        [1],
        "(ÜF) Mit Beginn der 1. Stufe kann ein Skirnir die Fähigkeit Zauberschlag auch mit einem "
        "Schildstoß statt einer Waffe einsetzen.",
        [],
        [],
    ),
    (
        "Schildvorrat",
        [4],
        "(AF) Mit Beginn der 4. Stufe kann ein Skirnir mit einer Freien Aktion 1 Punkt seines "
        "Arkanen Vorrats einsetzen, um beim defensiven Zaubern seinen Schildbonus auf die RK (ohne "
        "eventuelle Verbesserungsboni) auf seine Konzentrationswürfe hinzuzuaddieren. Er kann "
        "ferner jedes Vorratsschlag-Arkanum in Verbindung mit einem Berührungsangriff oder einem "
        "Schildstoß mit seinem Schild nutzen. Dieses Klassenmerkmal ersetzt Zauberrückruf.",
        [("Zauberrückruf", 4)],
        [],
    ),
    (
        "Zaubertragender Schild",
        [7],
        "(ÜF) Mit Beginn der 7. Stufe kann ein Skirnir mit einer Standard-Aktion einen "
        "Kampfmaguszauber in seinem Schild einlagern, indem er pro Grad des Zaubers 1 Punkt seines "
        "Arkanen Vorrats einsetzt. Dies funktioniert wie die Waffeneigenschaft Zauberspeicher, wird "
        "aber nur bei einem erfolgreichen Schildstoß aktiviert und ist nicht auf Zauber des maximal "
        "3. Grades beschränkt. Dieses Klassenmerkmal ersetzt Wissensvorrat.",
        [("Wissensvorrat", 7)],
        [],
    ),
    (
        "Geschützte Kampfzauberei",
        [8],
        "(ÜF) Mit Beginn der 8. Stufe erhält ein Skirnir das Klassenmerkmal Kampfzauberei, jedoch "
        "nur, wenn er seinen mit ihm verbundenen Schild führt. Ein Skirnir kann seine Schildhand für "
        "die Gestik von Kampfmaguszaubern nutzen, gibt dabei aber bis zum Beginn seines nächsten "
        "Zuges seinen Schildbonus auf RK auf (außer bei einer Tartsche). Mit Beginn der 14. Stufe "
        "erlangt er die Vorteile von Verbesserte Kampfzauberei; mit Beginn der 19. Stufe behält er "
        "seinen Schildbonus auf RK auch bei Kampfzauberei mit Schild. Dieses Klassenmerkmal ersetzt "
        "Verbesserte Kampfzauberei, Mächtige Kampfzauberei und Mächtiger Zugang zu Zaubern.",
        [("Verbesserte Kampfzauberei", 8), ("Mächtige Kampfzauberei", 14), ("Mächtiger Zugang zu Zaubern", 19)],
        [],
    ),
    (
        "Mächtiger Zaubertragender Schild",
        [16],
        "(ÜF) Mit Beginn der 16. Stufe kann ein Skirnir einen gespeicherten Zauber mit einer "
        "Augenblicklichen Aktion aktivieren, nachdem er im Kampf getroffen wurde, und ihn auf sich "
        "selbst oder die Kreatur wirken, die ihn getroffen hat. Dieses Klassenmerkmal ersetzt "
        "Gegenschlag.",
        [("Gegenschlag", 16)],
        [],
    ),
]

ZAUBERSTREITER_FEATURES: list[Feature] = [
    (
        "Zauberschlag im Fernkampf",
        [4],
        "(AF) Mit Beginn der 4. Stufe kann ein Zauberstreiter einen Fernkampfzauber, der auf ein "
        "einzelnes Ziel mit einem Berührungsangriff wirkt, mit einer Fernkampfwaffe übermitteln - "
        "selbst wenn der Zauber normalerweise mehrere Ziele betreffen kann, kommt nur ein einzelnes "
        "Geschoss, Strahl oder ein Effekt zur Anwendung. Mit Beginn der 11. Stufe kann ein "
        "Zauberstreiter, der so einen Zauber mit mehreren möglichen Zielen übermittelt, mit jedem "
        "Angriff im Rahmen eines Vollen Angriffs einen weiteren Strahl, eine Linie oder einen Effekt "
        "übermitteln (bis zum Maximum, das der Zauber erlaubt); jeder Effekt, der nicht in derselben "
        "Runde genutzt wird, ist verloren. Dieses Klassenmerkmal ersetzt Zauberrückruf und "
        "Verbesserter Zauberrückruf.",
        [("Zauberrückruf", 4), ("Verbesserter Zauberrückruf", 11)],
        [],
    ),
    (
        "Waffentraining (Zauberstreiter)",
        [6],
        "(AF) Mit Beginn der 6. Stufe erhält ein Zauberstreiter das Klassenmerkmal Waffentraining "
        "(entspricht dem gleichnamigen Klassenmerkmal des Kämpfers). Alle weiteren sechs Stufen als "
        "Kampfmagus fügt er eine zusätzliche Waffengruppe hinzu (bis zu einem Maximum von 3 Gruppen "
        "auf der 18. Stufe); mit jeder weiteren Waffengruppe steigen die Boni auf Angriffs- und "
        "Schadenswürfe bei den bereits gewählten Gruppen um zusätzlich +1. Dieses Klassenmerkmal "
        "ersetzt die Arkana, welche der Kampfmagus ansonsten mit der 6., 12. und 18. Stufe erhält.",
        [("Arkanum", 6), ("Arkanum", 12), ("Arkanum", 18)],
        [],
    ),
    (
        "Kämpferausbildung (Zauberstreiter)",
        [7],
        "(AF) Mit Beginn der 7. Stufe hat ein Zauberstreiter eine effektive Kämpferstufe in Höhe "
        "seiner Kampfmagusstufe -3 hinsichtlich der Qualifikation für Talente. Ab der 10. Stufe "
        "behandelt er seine Stufen als Kampfmagus als Kämpferstufen hinsichtlich der "
        "Kämpferausbildung. Sollte er über Stufen als Kämpfer verfügen, so sind diese kumulativ. "
        "Dieses Klassenmerkmal ersetzt Wissensvorrat und die Kämpferausbildung, die der Kampfmagus "
        "auf der 10. Stufe erlangt.",
        [("Wissensvorrat", 7), ("Kämpferausbildung", 10)],
        [],
    ),
    (
        "Rüstungstraining",
        [8],
        "(AF) Mit Beginn der 8. Stufe erhält ein Zauberstreiter Rüstungstraining wie das "
        "gleichnamige Klassenmerkmal des Kämpfers. Mit der 14. Stufe erhält er Rüstungstraining 2. "
        "Dieses Klassenmerkmal ersetzt Verbesserte Kampfzauberei und Mächtige Kampfzauberei.",
        [("Verbesserte Kampfzauberei", 8), ("Mächtige Kampfzauberei", 14)],
        [],
    ),
    (
        "Rüstungsmeisterschaft (Zauberstreiter)",
        [20],
        "(AF) Mit Beginn der 20. Stufe erhält ein Zauberstreiter in Rüstung SR 5/-. Dieses "
        "Klassenmerkmal ersetzt Wahrer Kampfmagus.",
        [("Wahrer Kampfmagus", 20)],
        [],
    ),
]

ARCHETYPES: list[tuple[str, list[Feature]]] = [
    ("Kensai", KENSAI_FEATURES),
    ("Seelenschmied", SEELENSCHMIED_FEATURES),
    ("Skirnir", SKIRNIR_FEATURES),
    ("Zauberstreiter", ZAUBERSTREITER_FEATURES),
]


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


def import_archetype(
    archetype_name: str,
    features: list[Feature],
    classes: list[dict],
    abilities: list[dict],
    grants: list[dict],
    replacements: list[dict],
    kampfmagus_grant_id_by_name_level: dict[tuple[str, int], str],
) -> str:
    archetype_id = uid("kampfmagus-archetype", archetype_name)

    classes[:] = [c for c in classes if c["id"] != archetype_id]
    classes.append(
        {
            "id": archetype_id,
            "name": archetype_name,
            "hit_dice": None,
            "arch_class_of": KAMPFMAGUS_ID,
            "casting_ability": None,
            "spell_tradition": None,
            "bab_progression": None,
            "fort_save": None,
            "ref_save": None,
            "wil_save": None,
            "skill_points_base": None,
        }
    )

    own_ability_ids = {uid("kampfmagus-archetype-ability", archetype_id, name) for name, *_ in features}
    own_ability_ids.add(uid("kampfmagus-archetype-ability", archetype_id, "Vermindertes Zauberwirken"))
    abilities[:] = [a for a in abilities if a["id"] not in own_ability_ids]
    grants[:] = [g for g in grants if g["base_class_id"] != archetype_id]
    replacements[:] = [r for r in replacements if r["archetype_class_id"] != archetype_id]

    # Every archetype's "Vermindertes Zauberwirken" - descriptive only, no
    # schema hook to replace (see this script's docstring).
    vz_id = uid("kampfmagus-archetype-ability", archetype_id, "Vermindertes Zauberwirken")
    abilities.append(
        {
            "id": vz_id,
            "name": "Vermindertes Zauberwirken",
            "description": VERMINDERTES_ZAUBERWIRKEN.format(name=archetype_name),
        }
    )
    grants.append(
        {
            "id": uid("kampfmagus-archetype-grant", vz_id, "1"),
            "base_class_id": archetype_id,
            "ability_id": vz_id,
            "option_choice_id": None,
            "level": 1,
        }
    )

    for name, levels, description, replaces, granted_feat_ids in features:
        ability_id = uid("kampfmagus-archetype-ability", archetype_id, name)
        abilities.append({"id": ability_id, "name": name, "description": description})

        for level in levels:
            grant_id = uid("kampfmagus-archetype-grant", ability_id, str(level))
            grants.append(
                {
                    "id": grant_id,
                    "base_class_id": archetype_id,
                    "ability_id": ability_id,
                    "option_choice_id": None,
                    "level": level,
                }
            )

        for replaced_name, replaced_level in replaces:
            replaced_grant_id = kampfmagus_grant_id_by_name_level[(replaced_name, replaced_level)]
            replacements.append(
                {
                    "id": uid("kampfmagus-archetype-replacement", ability_id, replaced_grant_id),
                    "archetype_class_id": archetype_id,
                    "ability_id": ability_id,
                    "replaces_grant_id": replaced_grant_id,
                }
            )

        # granted_feat_ids handled by the caller via base_class_ability_granted_feats.json
        features_granted_feats.setdefault(ability_id, granted_feat_ids)

    return archetype_id


features_granted_feats: dict[str, list[str]] = {}


def main() -> None:
    classes = load("base_classes.json")
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    replacements = load("base_class_ability_replacements.json")
    feat_grants = load("base_class_ability_granted_feats.json")

    ability_name_by_id = {a["id"]: a["name"] for a in abilities}
    kampfmagus_grant_id_by_name_level = {
        (ability_name_by_id[g["ability_id"]], g["level"]): g["id"]
        for g in grants
        if g["base_class_id"] == KAMPFMAGUS_ID and g["option_choice_id"] is None
    }

    archetype_ids = {}
    for archetype_name, features in ARCHETYPES:
        archetype_ids[archetype_name] = import_archetype(
            archetype_name,
            features,
            classes,
            abilities,
            grants,
            replacements,
            kampfmagus_grant_id_by_name_level,
        )

    feat_grants[:] = [fg for fg in feat_grants if fg["ability_id"] not in features_granted_feats]
    for ability_id, feat_ids in features_granted_feats.items():
        for i, feat_id in enumerate(feat_ids):
            feat_grants.append(
                {
                    "id": uid("kampfmagus-archetype-granted-feat", ability_id, str(i)),
                    "ability_id": ability_id,
                    "feat_id": feat_id,
                }
            )

    save("base_classes.json", classes)
    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)
    save("base_class_ability_replacements.json", replacements)
    save("base_class_ability_granted_feats.json", feat_grants)

    # classes.json: archetypes are computed generically from BaseClass.arch_class_of
    # (see main.py's get_classes docstring, 2026-08-16) - no fixture edit needed there.

    for name, class_id in archetype_ids.items():
        print(f"{name} class id:", class_id)
    print("Done.")


if __name__ == "__main__":
    main()
