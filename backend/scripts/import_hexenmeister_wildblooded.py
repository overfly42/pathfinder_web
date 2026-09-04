"""Import the "Wilde Blutlinie" (Wildblooded) archetype for the Hexenmeister
(Sorcerer) from
http://prd.5footstep.de/AusbauregelnMagie/Zauberkundige/Hexenmeister/WildeBlutlinie
into the seed JSON files.

Wildblooded isn't modeled as a `BaseClass` archetype row (`arch_class_of`):
per its own PRD text, a wildblooded bloodline reuses its associated
bloodline's class skill, bonus spells and bonus feats unchanged, and only
swaps the bloodline arcana ("Geheimnis des Blutes") plus exactly one named
bloodline power for a different one — everything else (level, remaining
powers) stays identical. That is exactly the shape the existing `bloodline`
`BaseClassOptionGroup` already supports (one full, closed-choice bloodline
per pick), so each wildblooded variant is seeded as one more
`BaseClassOptionChoice` in that same group, not a new mechanism: its
unchanged powers/feats/spells/skill are new `BaseClass*` rows that
*reference* the associated bloodline's existing `ability_id`/`feat_id`/
`spell_id`/`skill_id` (scoped under the new choice id) rather than
duplicating their text, and only the swapped arcana/power get a genuinely
new `BaseClassAbility` row. No `BaseClassAbilityReplacement` row is needed
either — that table scopes an *archetype's* substitution against a fixed
parent grant, but each wildblooded choice here is a complete, independent
bloodline pick, not an archetype layered on top of one.

The PRD page lists 20 wildblooded bloodlines. The other 10 are tied to
Expertenregeln bloodlines (Proteanische, Tiefenblutlinie, Sturmblutlinie,
Schattenblutlinie, Arktische, Schlangen-, Immergrüne, Aquatische, Stern-,
Traumblutlinie — marked "**" on the PRD page) that weren't seeded in this
project until `import_hexenmeister_experten_bloodlines.py` added them - run
that script first, then this one, so all 20 WILDBLOODED tuples below can
resolve their associated bloodline's grants.

Two minor PRD typos silently corrected: "Sylvanische Blutline" -> "...
Blutlinie", "Lindwurmblutline" (mid-sentence) -> "...Blutlinie", and Eisige
Blutlinie's "ersetzt die Blutlinienkraft Schneeschleier" -> "Schneeschleuder"
(the actual power name on Arktische Blutlinie's own page, the only 9th-level
power it has). Leereberührte Blutlinie's "Schwarze Flocken" has no explicit
"ersetzt X" clause (it only says it "funktioniert genau wie Meteoritenregen,
nur das sie Kälteschaden verursacht"), but that's unambiguously Sternenblutlinie's
1st-level power by function and level, so it's modeled as a second explicit
replacement alongside "Feld der Leere"/Nordlicht - unusual among these 20 in
swapping two named powers instead of the minimum one, but the PRD's own
Wildblooded intro only guarantees "at least one." Visionäre Blutlinie's
un-leveled, un-named "Macht des Blutes" sentence (reduced sleep to recover
spells) has no power name/level/replacement target at all - folded into its
arcana description rather than invented as a phantom 7th ability grant.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database):
    cd backend && python scripts/import_hexenmeister_experten_bloodlines.py
    python scripts/import_hexenmeister_wildblooded.py
    python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed
    python -m app.seed.class_ability_option_seed
    python -m app.seed.skill_seed
    python -m app.seed.spell_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("7a5d6f3e-4b1c-4d8a-9e2f-3c6b8a1d5e9f")
HEXENMEISTER_ID = "ceb02ad1-268c-4a1c-a7c9-ea8a1cbbe67e"

MUTATIONSTABELLE = (
    "\n\nTabelle: Mutationsvorteile beim Gestaltwechsel (W12)\n"
    "1 Extreme Gelenkigkeit: +2 bei Würfen auf Entfesselungskunst\n"
    "2 Schwimmhäute: +2 bei Würfen auf Schwimmen\n"
    "3 Eiserner Griff: +2 bei Würfen auf Klettern und die KMV gegen Entwaffnen\n"
    "4 Facettenaugen: +2 bei Würfen auf Wahrnehmung\n"
    "5 Tarnung: +2 bei Würfen auf Heimlichkeit\n"
    "6 Dicke Haut: +1 auf natürliche Rüstung\n"
    "7 Zäh: +1 bei Zähigkeitswürfen\n"
    "8 Rege: +1 bei Reflexwürfen\n"
    "9 Wach: +1 bei Willenswürfen\n"
    "10 Schnell: Bewegungsrate +1,50 m\n"
    "11 Wild: +1 auf Angriffswürfe im Nahkampf\n"
    "12 Adleraugen: +1 auf Angriffswürfe im Fernkampf"
)

# (new_choice_name, associated_bloodline_choice_name, arcana_description,
#  [(new_power_name, level, description, replaces_ability_name, also_replaces_arcana,
#    is_persistent_effect, activation_scope), ...])
Power = tuple[str, int, str, str, bool, bool, str | None]
Wildblooded = tuple[str, str, str, list[Power]]

WILDBLOODED: list[Wildblooded] = [
    (
        "Blutlinie der Brutalität",
        "Dämonische Blutlinie",
        "Wenn du einen Zauber wirkst, der Trefferpunktschaden verursacht, erleidet ein Ziel "
        "deiner Wahl, welches von dem Zauber betroffen ist, 2 zusätzliche Schadenspunkte. Diese "
        "Fähigkeit wirkt sich nicht auf Zauber aus, die keinen Trefferpunktschaden machen (wie "
        "z. B. Zauber, die Attributsschaden machen).",
        [
            (
                "Schwingen des Abyss",
                9,
                "(ÜF) Auf der 9. Stufe kannst du dir ledrige Flügel wachsen lassen und täglich "
                "für eine Anzahl von Minuten gleich deiner Stufe als Hexenmeister fliegen. Die "
                "Fluggeschwindigkeit beträgt 18 m und die Manövrierfähigkeit ist gut. Die Dauer "
                "muss nicht zusammenhängend sein, wird aber in Einheiten zu je einer Minute "
                "berechnet. Diese Blutlinienkraft ersetzt Stärke des Abyss.",
                "Stärke des Abyss",
                False,
                True,
                "self",
            ),
        ],
    ),
    (
        "Blutlinie der Gelehrten",
        "Arkane Blutlinie",
        "Im Gegensatz zu den meisten Hexenmeistern nutzt du nicht die Kraft deiner "
        "Persönlichkeit, sondern deinen Intellekt, um deine mystischen Kräfte zu verstehen und "
        "zu meistern. Du benutzt Intelligenz statt Charisma, um deine Hexenmeister-"
        "Klassenmerkmale und -Effekte zu bestimmen, wie Bonuszauber pro Tag, die SG der "
        "Rettungswürfe gegen deine Zauber und die Anzahl der täglichen Anwendungen deiner "
        "Blutlinienkräfte. Du erhältst einen Bonus von +2 bei allen Würfen auf Wissen (Arkanes) "
        "und Zauberkunde.",
        [
            (
                "Arkanes Geschoss",
                1,
                "(ZF) Beginnend auf der 1. Stufe kannst du einen Strahl aus magischer Energie "
                "mit einer Standard-Aktion verschießen und damit ein beliebiges Ziel innerhalb "
                "von 9 m mit einem Berührungsangriff im Fernkampf angreifen. Dieser Strahl "
                "verursacht 1W4 Schadenspunkte +1 Punkt für jeweils zwei deiner Stufen als "
                "Hexenmeister. Dieser Schaden wird wie ein Zauber eines Grades gleich deiner "
                "halben Stufe als Hexenmeister und als Energieeffekt behandelt. Du kannst diese "
                "Fähigkeit täglich in Höhe deines CH-Modifikators +3 einsetzen. Diese "
                "Blutlinienkraft ersetzt Arkane Verbindung.",
                "Arkane Verbindung",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Blutlinie des Himmels",
        "Himmlische Blutlinie",
        "Im Gegensatz zu den meisten Hexenmeistern, deren angeborene Magie durch die Macht "
        "ihrer Persönlichkeit angetrieben wird, nutzt du reine Willenskraft, um deine Magie zu "
        "meistern und anzutreiben. Alle Klassenmerkmale und Effekte, die mit deiner Klasse als "
        "Hexenmeister in Verbindung stehen, basieren auf Weisheit statt Charisma, darunter deine "
        "täglichen Bonuszauber, der dir mögliche Höchstgrad an Zaubern und die SG der "
        "Rettungswürfe gegen deine Zauber. Du erhältst einen Bonus von +2 bei allen Würfen auf "
        "Heilkunde und Wissen (Religion).",
        [
            (
                "Heilige Zisterne",
                9,
                "(ÜF) Auf der 9. Stufe macht dich deine Blutlinie zu einem natürlichen "
                "Aufnahmegefäß für göttliche Energie. Du kannst einmal am Tag wie ein Kleriker "
                "mit deiner Stufe als Hexenmeister -4 Energie fokussieren. Diese Blutlinienkraft "
                "ersetzt Schwingen des Himmels.",
                "Schwingen des Himmels",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Höllische Blutlinie",
        "Teuflische Blutlinie",
        "Wenn du einen Zauber wirkst, erhältst du für eine Runde einen Bonus bei Würfen auf "
        "Einschüchtern gleich dem Grad des Zaubers.",
        [
            (
                "Zäh wie die Hölle",
                9,
                "(AF) Auf der 9. Stufe erhältst du einen innewohnenden Bonus von +2 auf deine "
                "Konstitution. Dieser Bonus steigt auf der 13. Stufe auf +4 und auf der 17. "
                "Stufe auf +6. Diese Blutlinienkraft ersetzt Höllenfeuer.",
                "Höllenfeuer",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Karmische Blutlinie",
        "Schicksalhafte Blutlinie",
        "Wenn du defensiv zauberst, weil dich eine Kreatur bedroht, und dein Konzentrationswurf "
        "scheitert, provoziert eine der dich bedrohenden Kreaturen einen Gelegenheitsangriff von "
        "dir oder einem Verbündeten, der benachbart zum Feind steht. Du entscheidest, welche "
        "Kreatur diesen Angriff provoziert, und welcher ihrer benachbarten Gegner den Angriff "
        "machen darf.",
        [
            (
                "Rache des Schicksals",
                1,
                "(ÜF) Beginnend auf der 1. Stufe kannst du mit einer Augenblicklichen Aktion "
                "eine Kreatur verfluchen, die dich im Nahkampf getroffen hat. Das Ziel erleidet "
                "für 1W4 Runden einen Malus von -2 auf alle Angriffs- und Schadenswürfe. Bei "
                "einem erfolgreichen Willenswurf gegen SG 10 + deine ½ Stufe als Hexenmeister + "
                "dein CH-Modifikator hat dieser Effekt keine Wirkung. Du kannst diese Fähigkeit "
                "täglich in Höhe deines CH-Modifikators +3 einsetzen. Diese Blutlinienkraft "
                "ersetzt Berührung des Schicksals.",
                "Berührung des Schicksals",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Lindwurmblutlinie",
        "Drachenblutlinie",
        "Wenn du einen Zauber der Energieart wirkst, welche zur Energieart deiner "
        "Lindwurmblutlinie passt, erhältst du einen Natürlichen Rüstungsbonus gleich dem Grad "
        "des Zaubers für 1W4 Runden.",
        [
            (
                "Elementarspucke",
                1,
                "(ÜF) Beginnend auf der 1. Stufe kannst du mit einer Standard-Aktion einen "
                "Elementarstrahl der Energieart deiner Lindwurmblutlinie verschießen. Ein "
                "beliebiger Feind innerhalb von 9 m kann das Ziel deines Berührungsangriffes im "
                "Fernkampf werden. Der Strahl verursacht 1W6 Schadenspunkte + 1 Punkte für "
                "jeweils zwei deiner Stufen als Hexenmeister. Du kannst diese Fähigkeit täglich "
                "in Höhe deines CH-Modifikators +3 einsetzen. Diese Blutlinienkraft ersetzt "
                "Klauen.",
                "Klauen",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Mutierte Blutlinie",
        "Abnormale Blutlinie",
        "Wenn du einen Zauber der Unterschule des Gestaltwechsels wirkst, kann ein Ziel "
        "deiner Wahl einen zufälligen Effekt von der Mutationstabelle erhalten. Dieser "
        "Bonus wirkt solange wie der Gestaltwechseleffekt auf dem Ziel liegt." + MUTATIONSTABELLE,
        [
            (
                "Hauch der Verzerrung",
                1,
                "(ZF) Beginnend mit der 1. Stufe erschaffst du kurze, verwirrende Veränderungen "
                "in der körperlichen Gestalt einer Kreatur. Diese Fähigkeit wirkt auf eine "
                "Kreatur innerhalb von 9 m, welche für 1 Runde benommen ist (RW Zähigkeit, keine "
                "Wirkung; SG 10 + deine ½ Stufe als Hexenmeister + dein CH-Modifikator). Du "
                "kannst diese Fähigkeit täglich in Höhe deines CH-Modifikators +3 einsetzen. "
                "Diese Blutlinienkraft ersetzt Säurestrahl.",
                "Säurestrahl",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Sylvanische Blutlinie",
        "Feenblutlinie",
        # Sylvanische Blutlinie has no bonus-spell-triggered arcana of its own -
        # "Tiergefährte" below counts as the arcana AND replaces a power (PRD:
        # "zählt als dein Geheimnis des Blutes und ersetzt zudem Berührung des
        # Lachens"), so there is no separate arcana ability/grant here at all.
        "",
        [
            (
                "Tiergefährte",
                1,
                "(AF) Du erhältst einen Tiergefährten. Deine effektive Druidenstufe für diese "
                "Fähigkeit entspricht deiner Stufe als Hexenmeister -3 (Minimum 1). Diese "
                "Blutlinienkraft zählt als dein Geheimnis des Blutes und ersetzt zudem "
                "Berührung des Lachens.",
                "Berührung des Lachens",
                True,
                False,
                None,
            ),
            (
                "Feenflügel",
                15,
                "(ÜF) Auf der 15. Stufe kannst du dir insektenartige Flügel aus dem Rücken "
                "wachsen lassen und um eine Größenkategorie schrumpfen, als hättest du Person "
                "verkleinern gewirkt. Du kannst diese Gestalt täglich für eine Minute pro Stufe "
                "als Hexenmeister aufrechterhalten. Diese Dauer muss nicht durchgehend sein, "
                "wird aber in Einheiten zu je einer Minute abgerechnet. Diese Blutlinienkraft "
                "ersetzt Feenmagie.",
                "Feenmagie",
                False,
                True,
                "self",
            ),
        ],
    ),
    (
        "Urzeitliche Blutlinie",
        "Elementare Blutlinie",
        "Wenn du einen Zauber der Energieart wirkst, die mit der Energieart deiner Elementaren "
        "Blutlinie übereinstimmt, verursacht der Zauber pro Schadenswürfel +1 Schadenspunkt.",
        [
            (
                "Elementare Herbeizauberung",
                9,
                "(ÜF) Auf der 9. Stufe erhalten von dir herbeigezauberte Kreaturen "
                "Energieresistenz 10 gegen die Energieart deiner Elementaren Blutlinie (sollte "
                "eine Kreatur bereits eine entsprechende Resistenz besitzen, steigt diese um "
                "+5), zudem verursachen ihre natürlichen Angriffe zusätzliche 1W6 Schaden "
                "derselben Energieart. Diese Blutlinienkraft ersetzt Elementare Verwüstung.",
                "Elementare Verwüstung",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Vampirblutlinie",
        "Blutlinie des Grabes",
        "Wenn du einen Zauber der Schule Nekromantie wirkst, ist deine effektive Zauberstufe um "
        "+1 erhöht.",
        [
            (
                "Blut ist Leben",
                1,
                "(ÜF) Auf der 1. Stufe kannst du dich vom Blut kürzlich Verstorbener nähren. Mit "
                "einer Standard-Aktion kannst du das Blut einer Kreatur trinken, die innerhalb "
                "der letzten Minute gestorben ist. Die Kreatur muss körperlich sein, mindestens "
                "derselben Größenkategorie wie du angehören und über Blut verfügen. Diese "
                "Fähigkeit heilt 1W6 Trefferpunkte und sättigt dich wie eine volle Mahlzeit. Du "
                "kannst diese Fähigkeit täglich in Höhe deines CH-Modifikators +3 einsetzen. "
                "Diese Blutlinienkraft ersetzt Grabeshauch.",
                "Grabeshauch",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Blutlinie der Anarchie",
        "Proteanische Blutlinie",
        "Wenn dir beim Zaubern ein Konzentrationswurf misslingt, wird der Effekt eines "
        "Zaubertricks erschaffen. Bestimme zufällig einen der dir bekannten Zaubertricks "
        "(solltest du z. B. sechs Zaubertricks kennen, würfle mit einem W6). Mit 50%iger "
        "Wahrscheinlichkeit wirkt der Zaubertrick auf ein Ziel deiner Wahl innerhalb von "
        "18 m, andernfalls wirkt er auf dich.",
        [
            (
                "Wilder Rückschlag",
                3,
                "(ÜF) Auf der 3. Stufe nimmt der Zauberwirker eines von dir gebannten oder "
                "mittels Gegenzauber aufgehobenen Zaubers 1W6 Schadenspunkte +1 Punkt pro Grad "
                "des betroffenen Zaubers. Diese Blutlinienkraft ersetzt Proteanische "
                "Resistenz.",
                "Proteanische Resistenz",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Blutlinie des Gesteins",
        "Tiefenblutlinie",
        "Wenn du einen Zauber der Unterschule der Herbeizauberung wirkst, erhält die "
        "herbeigezauberte Kreatur SR /Adamant gleich deine halbe Stufe als Hexenmeister "
        "(Minimum 1). Dies addiert sich nicht zu einer Schadensreduzierung, welche die "
        "Kreatur eventuell bereits besitzt.",
        [
            (
                "Eiserne Haut",
                9,
                "(ZF) Auf der 9. Stufe kannst du dir selbst mit einer Schnellen Aktion SR "
                "10/Adamant täglich für eine Anzahl von Runden gleich deiner Stufe als "
                "Hexenmeister verleihen. Die Runden müssen nicht zusammenhängend sein. Diese "
                "Blutlinienkraft ersetzt Kristallscherbe.",
                "Kristallscherbe",
                False,
                True,
                "self",
            ),
        ],
    ),
    (
        "Blutlinie des Windes",
        "Sturmblutlinie",
        "Wenn du dich draußen im Regen aufhältst, erhöht sich deine effektive Zauberstufe um "
        "+2.",
        [
            (
                "Windrufer",
                9,
                "(ZF) Auf der 9. Stufe kannst du den Winden befehlen, deinen Anweisungen für "
                "eine Minute pro Stufe als Hexenmeister zu folgen. Dies funktioniert wie "
                "Windkontrolle, du hast aber die Wahl, gegen alle von dir erschaffenen "
                "verstärkten Windeffekten immun zu sein. Die Dauer der Fähigkeit muss nicht "
                "fortlaufend sein, wird aber in Einheiten zu je einer Minute abgerechnet. Diese "
                "Blutlinienkraft ersetzt Donnerkeil.",
                "Donnerkeil",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Blutlinie des Zwielichts",
        "Schattenblutlinie",
        "Wenn du einen Zauber in einem Gebiet schwachen Lichts oder Dunkelheit wirkst, steigt "
        "deine effektive Zauberstufe um +1.",
        [
            (
                "Schattenmantel",
                1,
                "(ZF) Auf der 1. Stufe kannst du einem Ziel mit einer Standard-Aktion einen "
                "Schattenmantel verleihen. Dieser Mantel gibt dem Ziel einen Bonus bei Würfen "
                "auf Heimlichkeit in Gebieten mit schwachem oder keinem Licht gleich deiner "
                "halben Stufe als Hexenmeister für eine Runde pro zwei deiner Stufen als "
                "Hexenmeister (Minimum Bonus von +1 für eine Runde). Du kannst diese Fähigkeit "
                "täglich in Höhe deines CH-Modifikators +3 einsetzen. Diese Blutlinienkraft "
                "ersetzt Schattenschlag.",
                "Schattenschlag",
                False,
                True,
                "both",
            ),
        ],
    ),
    (
        "Eisige Blutlinie",
        "Arktische Blutlinie",
        "Wenn du einen Zauber der Kategorie Kälte wirkst, kannst du ein Ziel des Zaubers "
        "auswählen, welches zusätzlich für eine Runde verlangsamt wird (wie der Zauber "
        "Verlangsamen). Bei einem gelungenen Zähigkeitswurf gegen SG 10 + Grad des "
        "Kältezaubers + dein CH-Modifikator hat der Effekt keine Wirkung.",
        [
            (
                "Eiskalter Bolzen",
                9,
                "(ZF) Auf der 9. Stufe kannst du die Luft in einer Explosion mit 3 m Radius "
                "gefrieren lassen. Dies verursacht 1W6 Punkte Kälteschaden pro Stufe als "
                "Hexenmeister (RW REF halbiert). Der SG dieses Rettungswurfes ist gleich 10 + "
                "deine ½ Stufe als Hexenmeister + dein CH-Modifikator. Auf der 9. Stufe kannst "
                "du diese Fähigkeit ein Mal am Tag benutzen. Auf der 17. Stufe kannst du diese "
                "Fähigkeit zwei Mal und auf der 20. Stufe drei Mal am Tag nutzen. Diese Kraft "
                "hat eine Reichweite von 18 m und ersetzt die Blutlinienkraft Schneeschleuder.",
                "Schneeschleuder",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Giftige Blutlinie",
        "Schlangenblutlinie",
        "Du erhältst einen Bonus von +2 bei Würfen auf Akrobatik, Heimlichkeit und Klettern.",
        [
            (
                "Vergiften",
                3,
                "(ÜF) Auf der 3. Stufe kannst du mit einer Schnellen Aktion deine Nahkampfwaffe "
                "ablecken oder hineinbeißen, um sie mit einer Anwendung Schwarzviperngift zu "
                "versehen. Der SG des Giftes ist gleich 10 + deine ½ Stufe als Hexenmeister + "
                "dein CH-Modifikator. Du kannst diese Fähigkeit auf der 3. Stufe einmal am Tag "
                "benutzen und ein weiteres Mal am Tag für jeweils drei weitere Stufen. Das "
                "Gift kann nicht entfernt oder gelagert werden. Die Waffe verliert die "
                "Vorteile durch das Gift nach dem ersten erfolgreichen Angriff oder wenn eine "
                "Stunde verstrichen ist. Diese Blutlinienkraft ersetzt Schlangenfreund.",
                "Schlangenfreund",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Haingeborene Blutlinie",
        "Immergrüne Blutlinie",
        "Deine Macht des Zwangs kann sogar auf Pflanzenkreaturen einwirken. Wenn du einen "
        "geistesbeeinflussenden oder sprachabhängigen Zauber wirkst, wirkt dieser auch auf "
        "Kreaturen der Kategorie Pflanze, als wären es Humanoide, sofern sie deine Sprache "
        "verstehen können.",
        [
            (
                "Grüne Herbeizauberung",
                3,
                "(ÜF) Auf der 3. Stufe kannst du entscheiden, dass von dir mit "
                "Beschwörungszaubern (Herbeizauberung) herbeigezauberte Kreaturen grün und "
                "blättrig wirken. Der natürliche Rüstungsbonus solcher Kreaturen steigt um +2 "
                "und sie erhalten einen Bonus von +4 auf Rettungswürfe gegen Betäubung, Gift, "
                "Lähmung, Schlaf und Verwandlung. Diese Blutlinienkraft ersetzt Photosynthese.",
                "Photosynthese",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Leereberührte Blutlinie",
        "Sternenblutlinie",
        "Wenn du einen Hervorrufungszauber wirkst, kannst du ein betroffenes Ziel, dessen "
        "Rettungswurf gescheitert ist, auswählen, die würgende Luftlosigkeit der Leere zu "
        "erleiden, wodurch du es für eine Runde zum Schweigen bringst (wie Stille, aber nur "
        "ein Ziel). Dies ist eine übernatürliche Fähigkeit.",
        [
            (
                "Schwarze Flocken",
                1,
                "(ZF) Diese Fähigkeit funktioniert genau wie Meteoritenregen, nur dass sie "
                "Kälteschaden verursacht.",
                "Meteoritenregen",
                False,
                False,
                None,
            ),
            (
                "Feld der Leere",
                9,
                "(ZF) Auf der 9. Stufe kannst du einen Bereich erschaffen, der von der dunklen "
                "Leere beeinflusst wird. Diese Fähigkeit funktioniert wie Eissturm, das Gebiet "
                "unterliegt aber zusätzlich noch Tieferer Dunkelheit für eine Runde pro vier "
                "Stufen als Hexenmeister. Du kannst diese Fähigkeit auf der 3. Stufe ein Mal am "
                "Tag benutzen und ein weiteres Mal am Tag für jeweils weitere drei Stufen. "
                "Diese Blutlinienkraft ersetzt Nordlicht.",
                "Nordlicht",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Meeresblutlinie",
        "Aquatische Blutlinie",
        "Wenn du dich in einem Gewässer befindest, das groß genug ist, dass man darin "
        "treiben könnte, wird deine effektive Zauberstufe um +1 erhöht.",
        [
            (
                "Wasserstoß",
                1,
                "(ZF) Mit einer Standard-Aktion kannst du einen Wasserstrahl auf einen Gegner "
                "innerhalb von 9 m als Berührungsangriff im Fernkampf abschießen. Der Feind "
                "wird zu Boden geworfen und kann 1,50 m von dir weggeschoben werden, so du "
                "dies wünschst. Bei einem erfolgreichen Reflexwurf gegen SG 10 + deine ½ Stufe "
                "als Hexenmeister + deinen CH-Modifikator hat dieser Effekt keine Wirkung. Du "
                "kannst diese Fähigkeit täglich in Höhe deines CH-Modifikators +3 einsetzen. "
                "Diese Blutlinienkraft ersetzt Hauch der Austrocknung.",
                "Hauch der Austrocknung",
                False,
                False,
                None,
            ),
        ],
    ),
    (
        "Visionäre Blutlinie",
        "Traumblutlinie",
        # PRD's "Macht des Blutes" intro for this one is an actual (un-leveled,
        # un-named) mechanical sentence rather than pure flavor - folded in here
        # rather than invented as a phantom 7th ability grant (see module docstring).
        "Deine Träume geben Hinweise auf die Zukunft. Du benötigst nur eine Stunde Schlaf am "
        "Tag, um deine Zauber zurückzugewinnen. Natürlich kannst du immer noch nur einmal am "
        "Tag deine Zauberplätze zurückerhalten und riskierst Erschöpfung, wenn du nicht "
        "genug Ruhe erhältst.",
        [
            (
                "Visionen",
                9,
                "(ZF) Auf der 9. Stufe erhältst du im Schlaf Informationen durch prophetische "
                "Träume. Einmal am Tag kannst du im Schlaf Informationen über Handlungen in "
                "der nächsten Woche erhalten, als hättest du einen Erkenntniszauber gewirkt. "
                "Auf der 9. Stufe erhältst du Information hinsichtlich einer einzelnen Frage. "
                "Auf der 17. Stufe kannst du dir zwei Fragen im Schlaf beantworten lassen und "
                "auf der 20. Stufe drei Fragen. Diese Blutlinienkraft ersetzt Traumformer.",
                "Traumformer",
                False,
                False,
                None,
            ),
        ],
    ),
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


def main() -> None:
    groups = load("base_class_option_groups.json")
    choices = load("base_class_option_choices.json")
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    feat_options = load("base_class_ability_feat_options.json")
    spell_grants = load("base_class_spell_grants.json")
    skills = load("base_class_skills.json")

    bloodline_group = next(g for g in groups if g["base_class_id"] == HEXENMEISTER_ID and g["key"] == "bloodline")
    group_id = bloodline_group["id"]

    choice_by_name = {c["name"]: c for c in choices if c["group_id"] == group_id}
    ability_name_by_id = {a["id"]: a["name"] for a in abilities}

    new_choices: list[dict] = []
    new_abilities: list[dict] = []
    new_grants: list[dict] = []
    new_feat_options: list[dict] = []
    new_spell_grants: list[dict] = []
    new_skills: list[dict] = []

    for new_name, base_name, arcana_description, powers in WILDBLOODED:
        base_choice = choice_by_name[base_name]
        base_choice_id = base_choice["id"]
        new_choice_id = uid("hexenmeister-wildblooded-choice", new_name)

        new_choices.append({"id": new_choice_id, "group_id": group_id, "name": new_name})

        base_grants = sorted(
            (g for g in grants if g.get("option_choice_id") == base_choice_id),
            key=lambda g: g["level"],
        )
        replaced_names = {power[3] for power in powers}
        has_own_arcana_replacement = any(power[4] for power in powers)

        for grant in base_grants:
            ability_name = ability_name_by_id[grant["ability_id"]]
            is_arcana = ability_name.startswith("Geheimnis des Blutes")
            if is_arcana and has_own_arcana_replacement:
                continue  # merged into the power that "counts as" the arcana (e.g. Sylvanische Blutlinie)
            if ability_name in replaced_names:
                continue  # superseded by one of `powers` below
            if is_arcana:
                arcana_id = uid("hexenmeister-wildblooded-ability", new_choice_id, "arcana")
                new_abilities.append(
                    {
                        "id": arcana_id,
                        "name": f"Geheimnis des Blutes ({new_name})",
                        "description": arcana_description,
                    }
                )
                new_grants.append(
                    {
                        "id": uid("hexenmeister-wildblooded-grant", new_choice_id, "arcana"),
                        "base_class_id": HEXENMEISTER_ID,
                        "ability_id": arcana_id,
                        "option_choice_id": new_choice_id,
                        "level": grant["level"],
                    }
                )
            else:
                # Unchanged power: reference the associated bloodline's own
                # ability row instead of duplicating its text.
                new_grants.append(
                    {
                        "id": uid("hexenmeister-wildblooded-grant", new_choice_id, ability_name),
                        "base_class_id": HEXENMEISTER_ID,
                        "ability_id": grant["ability_id"],
                        "option_choice_id": new_choice_id,
                        "level": grant["level"],
                    }
                )

        for power_name, level, description, _replaces, _also_arcana, is_persistent, activation_scope in powers:
            power_id = uid("hexenmeister-wildblooded-ability", new_choice_id, power_name)
            ability_row: dict = {"id": power_id, "name": power_name, "description": description}
            if is_persistent:
                ability_row["is_persistent_effect"] = True
                ability_row["activation_scope"] = activation_scope
            new_abilities.append(ability_row)
            new_grants.append(
                {
                    "id": uid("hexenmeister-wildblooded-grant", new_choice_id, power_name),
                    "base_class_id": HEXENMEISTER_ID,
                    "ability_id": power_id,
                    "option_choice_id": new_choice_id,
                    "level": level,
                }
            )

        for fo in feat_options:
            if fo.get("option_choice_id") == base_choice_id:
                new_feat_options.append(
                    {
                        "id": uid(
                            "hexenmeister-wildblooded-feat-option",
                            new_choice_id,
                            str(fo.get("feat_id")),
                            str(fo.get("feat_type")),
                        ),
                        "ability_id": fo["ability_id"],
                        "option_choice_id": new_choice_id,
                        "feat_type": fo.get("feat_type"),
                        "feat_id": fo.get("feat_id"),
                    }
                )

        for sg in spell_grants:
            if sg.get("option_choice_id") == base_choice_id:
                new_spell_grants.append(
                    {
                        "id": uid("hexenmeister-wildblooded-spell-grant", new_choice_id, sg["spell_id"], str(sg["level"])),
                        "base_class_id": HEXENMEISTER_ID,
                        "option_choice_id": new_choice_id,
                        "spell_id": sg["spell_id"],
                        "level": sg["level"],
                    }
                )

        for sk in skills:
            if sk.get("option_choice_id") == base_choice_id:
                new_skills.append(
                    {
                        "id": uid("hexenmeister-wildblooded-skill", new_choice_id, sk["skill_id"]),
                        "base_class_id": HEXENMEISTER_ID,
                        "skill_id": sk["skill_id"],
                        "option_choice_id": new_choice_id,
                    }
                )

    save("base_class_option_choices.json", choices + new_choices)
    save("base_class_abilities.json", abilities + new_abilities)
    save("base_class_ability_grants.json", grants + new_grants)
    save("base_class_ability_feat_options.json", feat_options + new_feat_options)
    save("base_class_spell_grants.json", spell_grants + new_spell_grants)
    save("base_class_skills.json", skills + new_skills)

    print(f"Wrote {len(new_choices)} wildblooded bloodline choices.")
    print(f"  {len(new_abilities)} new abilities, {len(new_grants)} grants,")
    print(f"  {len(new_feat_options)} feat options, {len(new_spell_grants)} spell grants,")
    print(f"  {len(new_skills)} skill rows.")


if __name__ == "__main__":
    main()
