"""Import the 10 Erweiterungsregeln/Expertenregeln Hexenmeister (Sorcerer)
bloodlines from
http://prd.5footstep.de/Expertenregeln/Klassen/Grundklassen/Hexenmeister
(Aquatische, Arktische, Immergrüne, Proteanische, Schatten-, Schlangen-,
Sternen-, Sturm-, Tiefen-, Traumblutlinie) into the seed JSON files.

These are full, independent bloodlines - same shape as the 10 Grundregelwerk
bloodlines already seeded (`base_class_option_choices.json`'s `bloodline`
group): one class skill, 9 bonus spells (odd levels 3-19), 8 bonus feats
(shared "Talent des Blutes" ability, scoped via `option_choice_id`), and 6
own `BaseClassAbility` rows (arcana "Geheimnis des Blutes" + 5 named powers
at 1st/3rd/9th/15th/20th). No relation to `import_hexenmeister_wildblooded.py`
- these are the *base* bloodlines several of that script's wildblooded
variants are associated with (e.g. Meeresblutlinie -> Aquatische Blutlinie),
which is why those 10 wildblooded variants were deliberately skipped until
now (see that script's docstring and todos.md).

Spell/feat names are matched against the already-seeded catalogs
(`base_spells.json`, `base_feats.json` - not the raw 1500-row
`imported/talente_prd_import.json` staging catalog, only ~1/5 of which was
ever promoted into `base_feats.json`/the database) by exact name; the
one mismatch found (`"Unsichtbarer Diener"` vs. this project's catalog name
`"Unsichtbare Hand: Diener"`) is aliased below. Parenthetical qualifiers on
the PRD's bonus-spell lines (e.g. "Elementaraura* (nur Kälte)",
"Monster herbeizaubern III (nur Reptilien)") are stripped for name matching
and then dropped - `BaseClassSpellGrant` has no field for a restriction
note, same schema boundary already accepted for the original 10 bloodlines.

`is_persistent_effect`/`activation_scope` are set only for powers that grant
a self-activated transformation/movement mode with a per-day duration
(natural weapons, flight, earth-glide, incorporeality, a self-buff aura) -
matched against the exact pattern already used for Klauen/Schwingen des
Himmels/Körperlose Gestalt/etc. in the existing 10 bloodlines (see
`BaseClassAbility`'s docstring in `models/base_class.py`).

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database):
    cd backend && python scripts/import_hexenmeister_experten_bloodlines.py
    python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed
    python -m app.seed.class_ability_option_seed
    python -m app.seed.skill_seed
    python -m app.seed.spell_seed
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("9c3e7b5a-2f4d-4a6e-8b1c-5d9a3e7f2c6b")
HEXENMEISTER_ID = "ceb02ad1-268c-4a1c-a7c9-ea8a1cbbe67e"

SPELL_NAME_ALIASES = {
    "Unsichtbarer Diener": "Unsichtbare Hand: Diener",
}

BONUS_SPELL_LEVELS = [3, 5, 7, 9, 11, 13, 15, 17, 19]

# (name, level, description, is_persistent_effect, activation_scope)
Power = tuple[str, int, str, bool, str | None]

# (choice_name, class_skill_name, arcana_description, bonus_spell_names[9],
#  bonus_feat_names[8], powers[5])
Bloodline = tuple[str, str, str, list[str], list[str], list[Power]]

BLOODLINES: list[Bloodline] = [
    (
        "Aquatische Blutlinie",
        "Schwimmen",
        "Immer wenn der Hexenmeister einen Zauber der Unterart Wasser wirkt, erhält er einen "
        "Bonus von +1 auf seine Zauberstufe. Herbeigezauberte Kreaturen mit einer "
        "Schwimm-Bewegungsrate oder der Unterart Aquatisch oder Wasser erhalten einen "
        "Moralbonus von +1 auf ihre Angriffs- und Schadenswürfe.",
        [
            "Wasserstrahl", "Wellenritt", "Wasserkugel", "Geysir", "Wasser kontrollieren",
            "Bestiengestalt IV", "Monster herbeizaubern VII", "Mantel der See", "Weltenwoge",
        ],
        [
            "Abhärtung", "Athlet", "Ausweichen", "Beweglichkeit", "Defensives Kampftraining",
            "Fertigkeitsfokus", "Lautlos zaubern", "Trank brauen",
        ],
        [
            (
                "Hauch der Austrocknung",
                1,
                "(ZF) Ab der 1. Stufe kann der Hexenmeister als Standard-Aktion einen "
                "Berührungsangriff im Nahkampf durchführen, welcher 1W6 Punkte nicht-tödlichen "
                "Schaden +1 Schadenspunkt für alle zwei Stufen als Hexenmeister verursacht, und "
                "das Ziel für 1 Runde kränkeln lässt. Schlicke, Pflanzen und Kreaturen der "
                "Unterart Aquatisch oder Wasser erleiden tödlichen Schaden. Der Hexenmeister "
                "kann diese Fähigkeit täglich in Höhe seines CH-Modifikators +3 einsetzen.",
                False,
                None,
            ),
            (
                "Aquatische Anpassung",
                3,
                "(AF) Ab der 3. Stufe hat der Hexenmeister eine Schwimm-Bewegungsrate von 9 m. "
                "Ab der 9. Stufe erhält er die Besondere Eigenschaft Amphibie und entwickelt "
                "eine Fettschicht, die ihm einen Bonus auf seine natürliche Rüstung von +1 sowie "
                "Kälteresistenz 5 verleiht. Im Wasser erhält er Blindgespür 9 m. Auf der 15. "
                "Stufe steigt die Schwimm-Bewegungsrate auf 18 m und die Reichweite von "
                "Blindgespür im Wasser auf 18 m.",
                False,
                None,
            ),
            (
                "Aquatische Telepathie",
                9,
                "(ÜF) Auf der 9. Stufe erhält der Hexenmeister telepathische Kräfte mit einer "
                "Reichweite von 30 m, mit denen er mit Kreaturen der Unterart Aquatisch oder "
                "Wasser, bzw. welche über eine Schwimm-Bewegungsrate verfügen, kommunizieren "
                "kann, egal ob sie intelligent sind oder nicht. Er kann auf solche Wesen "
                "täglich Einflüsterung in Höhe seines CH-Modifikators +3 wirken. Hierzu sind "
                "weder hör- noch sichtbare Komponenten erforderlich. Ab der 15. Stufe kann der "
                "Hexenmeister einmal am Tag die Dienste einer Aquatischen, Wasser- oder mit "
                "einer Schwimm-Bewegungsrate versehenden Kreatur einfordern, als bediene er "
                "sich Aufforderung oder Mächtiger Verbündeter aus den Ebenen.",
                False,
                None,
            ),
            (
                "Hochwasser",
                15,
                "(ZF) Ab der 15. Stufe kann der Hexenmeister einen Wasseranstieg wie mit Wasser "
                "kontrollieren verursachen, auch wenn kein Wasser in der Nähe vorhanden ist. Das "
                "erschaffene Wasser ist stationär und fließt nicht aus dem Bereich, in dem es "
                "erschaffen wurde. Nach 1 Runde pro Stufe als Hexenmeister verflüchtigt es sich "
                "wieder. Ab der 20. Stufe werden die Auswirkungen des Effektes verdoppelt. Der "
                "Hexenmeister kann diese Fähigkeit einmal am Tag einsetzen.",
                False,
                None,
            ),
            (
                "Tiefes Wesen",
                20,
                "(AF) Auf der 20. Stufe erhält der Hexenmeister Blindgespür 18 m und sein Körper "
                "wird von feinen, glatten Schuppen bedeckt, die ihm SR 10/Stich, "
                "Kälteresistenz 20 und andauernde Bewegungsfreiheit verleihen. Unter Wasser "
                "erhält er Entrinnen und Blindsicht 36 m, ferner ist er immun gegen Schaden "
                "aufgrund von hohem Wasserdruck in den Tiefen des Meeres.",
                False,
                None,
            ),
        ],
    ),
    (
        "Arktische Blutlinie",
        "Überlebenskunst",
        "Wenn der Hexenmeister einen Kältezauber wirkt, steigt der SG des Rettungswurfes um +1.",
        [
            "Person vergrößern", "Wut", "Elementaraura", "Eiswand", "Kältekegel", "Umwandlung",
            "Riesengestalt I", "Polarstrahl", "Meteoritenschwarm",
        ],
        [
            "Abhärtung", "Arkaner Schlag", "Ausdauer", "Fertigkeitsfokus", "Heftiger Angriff",
            "Umgang mit exotischen Waffen", "Unverwüstlich", "Zauber verstärken",
        ],
        [
            (
                "Kalter Stahl",
                1,
                "(ZF) Auf der 1. Stufe kann der Hexenmeister eine Waffe oder bis zu 50 "
                "Munitionsgeschosse mit einer Standard-Aktion berühren und für eine Anzahl von "
                "Runden in Höhe seiner halben Stufe als Hexenmeister (Minimum 1) die Eigenschaft "
                "Eis verleihen. Ab der 9. Stufe kann er ihnen stattdessen die Eigenschaft "
                "Eisinferno verleihen, allerdings wird die Wirkungsdauer halbiert. Der "
                "Hexenmeister kann diese Fähigkeit täglich in Höhe seines CH-Modifikators +3 "
                "einsetzen.",
                False,
                None,
            ),
            (
                "Eisläufer",
                3,
                "(AF) Auf der 3. Stufe erhält der Hexenmeister Kälteresistenz 5 und kann sich "
                "ohne Spuren zu hinterlassen und ohne Mali hinnehmen zu müssen über Schnee und "
                "vereiste Oberflächen bewegen. Auf der 9. Stufe steigt die Kälteresistenz auf "
                "10 und er kann auf vereisten Oberflächen klettern, als würde er "
                "Spinnenklettern verwenden.",
                False,
                None,
            ),
            (
                "Schneeschleuder",
                9,
                "(ÜF) Ab der 9. Stufe ignoriert der Hexenmeister Tarnung und Mali auf seine "
                "Fertigkeitswürfe für Wahrnehmung in natürlichem oder magischem Schnee, Eis, "
                "Nebel und ähnlichen Wetterbedingungen. Darüber hinaus kann er sich täglich in "
                "einen Mantel aus wirbelndem Schnee für eine Anzahl von Runden in Höhe seiner "
                "Stufe als Hexenmeister hüllen. Dies funktioniert wie der Zauber Feuerschild "
                "(Kälteschild), welcher jedoch kein Licht abgibt. Dies gewährt eine "
                "Fehlschlagschance von 20%, dass Angriffe den Hexenmeister verfehlen und er "
                "erhält einen Bonus auf seine Fertigkeitswürfe für Heimlichkeit in Höhe seiner "
                "halben Stufe als Hexenmeister in Eis- und Schneegebieten. Er kann diese "
                "Fähigkeit ab der 9. Stufe einmal am Tag verwenden sowie ein weiteres Mal auf "
                "der 17. Stufe und drei Mal auf der 20. Stufe.",
                True,
                "self",
            ),
            (
                "Schneesturm",
                15,
                "(ZF) Ab der 15. Stufe kann der Hexenmeister einen ungezügelten Wintersturm um "
                "sich herum erschaffen. Dies funktioniert wie Windkontrolle, allerdings wird bis "
                "auf das Auge des Sturmes, in welchem sich der Hexenmeister befindet, das ganze "
                "Gebiet wie durch einen Schneesturm betroffen. Jeder im Gebiet wird extremer "
                "Kälte ausgesetzt. Diese Fähigkeit kann einmal am Tag eingesetzt werden.",
                False,
                None,
            ),
            (
                "Kind des Uralten Winters",
                20,
                "(ÜF) Auf der 20. Stufe gehört der Hexenmeister fortan der Unterart Kälte an und "
                "wird immun gegen Entkräftung, Erschöpfung, Hinterhältige Angriffe und "
                "Kritische Treffer. Allerdings erhält er auch Empfindlichkeit gegen Feuer.",
                False,
                None,
            ),
        ],
    ),
    (
        "Immergrüne Blutlinie",
        "Wissen (Natur)",
        "Wenn der Hexenmeister einen Zauber mit Reichweite Persönlich wirkt, verhärtet sich "
        "seine Haut und verleiht ihm für 1W4 Runden einen Bonus auf seine natürliche Rüstung "
        "in Höhe des Zaubergrades. Dieser Bonus ist nicht kumulativ mit anderen Boni auf "
        "natürliche Rüstung.",
        [
            "Verstricken", "Rindenhaut", "Mit Pflanzen sprechen", "Pflanzen befehligen",
            "Dornenwand", "Pflanzentor", "Pflanzengestalt III", "Pflanzen beleben",
            "Modernder Schlurfer",
        ],
        [
            "Abhärtung", "Ausdauer", "Behände Bewegung", "Fertigkeitsfokus",
            "Geschmeidige Bewegung", "Leichtfüßigkeit", "Zauber ausdehnen",
            "Zauberstecken herstellen",
        ],
        [
            (
                "Ranke",
                1,
                "(ZF) Auf der 1. Stufe kann der Hexenmeister mit einer Standard-Aktion für 1 "
                "Runde eine 4,50 m lange, belebte Ranke erschaffen, welche aus seiner Hand "
                "entspringt. Mit dieser Ranke kann er eines der folgenden Manöver durchführen: "
                "Entwaffnen, Entreißen oder Zu-Fall-bringen. Bei diesem nimmt er statt seines "
                "KMB seine Stufe als Hexenmeister + seinen CH-Modifikator. Der Hexenmeister "
                "kann diese Fähigkeit täglich in Höhe seines CH-Modifikators +3 einsetzen.",
                False,
                None,
            ),
            (
                "Photosynthese",
                3,
                "(AF) Ab der 3. Stufe nährt sich der Hexenmeister von der Essenz der Natur. Sein "
                "Bedarf an Nahrung und Schlaf sinkt, als würde er einen Versorgungsring tragen. "
                "Er erhält einen Volksbonus von +2 auf Rettungswürfe gegen Gift und "
                "Schlafeffekte. Ab der 9. Stufe steigt dieser Bonus auf +4.",
                False,
                None,
            ),
            (
                "Massen-Pflanzenverwandlung",
                9,
                "(ZF) Ab der 9. Stufe kann der Hexenmeister mit einer Vollen Aktion die Größe "
                "und Gesundheit von pflanzlichem Leben verändern, als würde er Pflanzenwachstum "
                "oder Pflanzen schrumpfen wirken. Alternativ kann er einmal am Tag eine "
                "bereitwillige nicht-pflanzliche Kreatur pro Stufe als Hexenmeister verwandeln, "
                "als würde er Baum wirken. Die Kreaturen dürfen voneinander nicht weiter als "
                "9 m entfernt sein. Ab der 15. Stufe kann er Kreaturen wie mit Pflanzengestalt I "
                "verwandeln, ab der 20. Stufe wie mit Pflanzengestalt II.",
                False,
                None,
            ),
            (
                "Wurzeln schlagen",
                15,
                "(AF) Ab der 15. Stufe kann der Hexenmeister sich mit einer Bewegungsaktion im "
                "Boden verwurzeln. Seine Bewegungsrate sinkt auf 1,50 m. Im Gegenzug erhält er "
                "dafür einen Bonus von +4 auf seine natürliche Rüstung und einen Bonus von +10 "
                "auf seine KMV gegen Ansturm, Überrennen, Versetzen und Zu-Fall-bringen. Darüber "
                "hinaus erhält er Erschütterungssinn 9 m und Schnelle Heilung 1. Er kann diese "
                "Fähigkeit täglich für eine Anzahl von Minuten in Höhe seiner Stufe als "
                "Hexenmeister einsetzen. Diese Zeit muss nicht aufeinander folgen, wird jedoch "
                "in Einheiten von jeweils 1 Minute berechnet.",
                True,
                "self",
            ),
            (
                "Hüter der Bäume",
                20,
                "(ÜF) Auf der 20. Stufe manifestiert sich das Erbe des Hexenmeisters "
                "vollständig. Er erhält einen Natürlichen Rüstungsbonus von +4, wird immun "
                "gegen Betäubung, Gift, Lähmung, Schlaf, Verwandlung und erhält "
                "Erschütterungssinn 9 m, selbst wenn er sich nicht verwurzelt.",
                False,
                None,
            ),
        ],
    ),
    (
        "Proteanische Blutlinie",
        "Wissen (Die Ebenen)",
        "Die magischen Schöpfungen und Verwandlungen des Hexenmeisters sind schwer wieder "
        "aufzuheben. Der SG um Zauber der Unterart Verwandlung oder Herbeirufung (Erschaffung) "
        "des Hexenmeisters zu bannen steigt um +4.",
        [
            "Entropieschild", "Verschwimmen", "Gasförmige Gestalt", "Verwirrung",
            "Höhere Erschaffung", "Auflösung", "Mächtige Verwandlung", "Beliebiges verwandeln",
            "Gestaltwandel",
        ],
        [
            "Abhärtung", "Defensives Kampftraining", "Fertigkeitsfokus", "Flinke Manöver",
            "Große Zähigkeit", "Verbesserte Große Zähigkeit", "Zauberfokus",
            "Zauberreichweite erhöhen",
        ],
        [
            (
                "Protoplasma",
                1,
                "(ZF) Auf der 1. Stufe kann der Hexenmeister eine Kugel aus Protoplasma "
                "erschaffen und nach seinen Feinden schleudern. Die Reichweite beträgt 9 m. Das "
                "Protoplasma wirkt wie ein Verstrickungsbeutel, der zudem jede Runde einer "
                "verstrickten Kreatur 1 Punkt Säureschaden zufügt. Das Protoplasma löst sich "
                "nach 1W3 Runden auf. Der Hexenmeister kann diese Fähigkeit täglich in Höhe "
                "seines CH-Modifikators +3 einsetzen.",
                False,
                None,
            ),
            (
                "Proteanische Resistenz",
                3,
                "(AF) Auf der 3. Stufe erhält der Hexenmeister Säureresistenz 5 und einen Bonus "
                "von +2 auf seine Rettungswürfe gegen Effekte und Zauber der Unterart "
                "Verwandlung und Versteinerung. Ab der 9. Stufe steigen die Säureresistenz auf "
                "10 und der Bonus auf den Rettungswurf auf +4.",
                False,
                None,
            ),
            (
                "Realitätsverzerrung",
                9,
                "(ZF) Ab der 9. Stufe kann der Hexenmeister sich mit einem beweglichen Feld "
                "veränderlicher Realität umgeben, dessen Radius 3 m beträgt. Dies entspricht "
                "Fester Nebel, verleiht aber weder Tarnung, noch blockiert es die Sichtlinie. "
                "Die Bewegungsrate wird von der Aura nicht beeinflusst. Angriffe von außerhalb "
                "der Aura gegen Ziele innerhalb der Aura besitzen eine Fehlschlagschance von "
                "20%. Der Hexenmeister kann diese Fähigkeit täglich für eine Anzahl von Runden "
                "in Höhe seiner Stufe als Hexenmeister nutzen. Diese Zeit muss nicht aufeinander "
                "folgen.",
                True,
                "self",
            ),
            (
                "Realitätsriss",
                15,
                "(ZF) Ab der 15. Stufe kann der Hexenmeister einmal am Tag die Fäden der "
                "Realität entzerren und ihnen folgen, während sie sich wieder ordnen. Dies "
                "funktioniert wie Dimensionstür und erschafft zugleich eine Masse Schwarzer "
                "Tentakel am vorherigen Standort des Hexenmeisters. Beide Effekte verwenden die "
                "Stufe des Hexenmeisters als Zauberstufe. Ab der 20. Stufe kann er diese "
                "Fähigkeit zwei Mal am Tag einsetzen.",
                False,
                None,
            ),
            (
                "Avatar des Chaos",
                20,
                "(AF) Auf der 20. Stufe wird der Hexenmeister von der Essenz des reinen Chaos "
                "erfüllt. Er wird immun gegen Säure, Versteinerung und Verwandlung (außer auf "
                "sich selbst gezaubert). Darüber hinaus erhält er einen Bonus von +2 auf den SG "
                "von Rettungswürfen und auf Würfe um die Zauberresistenz von Kreaturen der "
                "Unterart Ordnung zu überwinden.",
                False,
                None,
            ),
        ],
    ),
    (
        "Schattenblutlinie",
        "Heimlichkeit",
        "Wenn der Hexenmeister einen Zauber der Unterart Dunkelheit oder der Unterart der "
        "Schatten wirkt, erhält er für 1W4 Runden einen Situationsbonus in Höhe des "
        "Zaubergrades auf seine Fertigkeitswürfe für Heimlichkeit.",
        [
            "Schwächestrahl", "Dunkelsicht", "Tiefere Dunkelheit", "Schattenbeschwörung",
            "Schattenhervorrufung", "Schattenreise", "Wort der Macht: Blindheit",
            "Mächtige Schattenbeschwörung", "Schatten",
        ],
        [
            "Akrobat", "Ausweichen", "Blind kämpfen", "Fertigkeitsfokus", "Lautlos zaubern",
            "Schnelle Waffenbereitschaft", "Waffenfinesse", "Verstohlenheit",
        ],
        [
            (
                "Schattenschlag",
                1,
                "(ZF) Auf der 1. Stufe kann der Hexenmeister mit einer Standard-Aktion einen "
                "Berührungsangriff im Nahkampf ausführen, der 1W4 Punkte nicht-tödlichen Schaden "
                "+1 Punkt für jeweils zwei Stufen als Hexenmeister verursacht. Das Ziel ist "
                "zudem für 1 Runde geblendet, außer es handelt sich um eine Kreatur mit "
                "Dämmer- oder Dunkelsicht. Der Hexenmeister kann diese Fähigkeit täglich in "
                "Höhe seines CH-Modifikators +3 einsetzen.",
                False,
                None,
            ),
            (
                "Nachtauge",
                3,
                "(AF) Auf der 3. Stufe erhält der Hexenmeister Dunkelsicht 9 m, und auf der 9. "
                "Stufe Dunkelsicht 18 m. Sollte er bereits über Dunkelsicht verfügen, steigt "
                "diese um +9 m bzw. +18 m.",
                False,
                None,
            ),
            (
                "Schattenquell",
                9,
                "(ZF) Ab der 9. Stufe kann der Hexenmeister die Fertigkeit Heimlichkeit "
                "benutzen, selbst wenn er beobachtet wird und weder Deckung noch Tarnung hat, "
                "solange er sich höchstens 3 m weit von einem anderen Schatten als seinem "
                "eigenen entfernt befindet. Wenn er sich in einem Bereich schwachen Lichts oder "
                "in Dunkelheit befindet, kann er mit einer Standard-Aktion die Positionen "
                "zweier bereitwilliger Verbündeter austauschen, die nicht jeweils weiter als "
                "18 m vom Hexenmeister entfernt sein dürfen. Soweit nicht anders vermerkt, "
                "entspricht dies Dimensionstür. Er kann die Fähigkeit auf der 9. Stufe einmal "
                "am Tag anwenden, und ein weiteres Mal jeweils ab der 17. und der 20. Stufe.",
                False,
                None,
            ),
            (
                "Umhüllende Dunkelheit",
                15,
                "(ZF) Ab der 15. Stufe kann der Hexenmeister einen Bereich mit Tieferer "
                "Dunkelheit erzeugen, durch welchen er ohne Mali hindurchsehen kann. In der "
                "Dunkelheit gelten alle Wesen außer dem Hexenmeister als verstrickt, sofern sie "
                "nicht Bewegungsfreiheit oder ähnlichen Effekten unterliegen. Diese Fähigkeit "
                "kann einmal am Tag eingesetzt werden.",
                False,
                None,
            ),
            (
                "Schattenmeister",
                20,
                "(ÜF) Ab der 20. Stufe kann der Hexenmeister perfekt in jeder Art von Dunkelheit "
                "sehen. Sollte er Schattenbeschwörung oder Schattenhervorrufung wirken, so sind "
                "seine Schöpfungen um 20% realer und erhalten die Vorteile des Talentes "
                "Verstärkte Herbeizauberung.",
                False,
                None,
            ),
        ],
    ),
    (
        "Schlangenblutlinie",
        "Diplomatie",
        "Die Überredungskünste des Hexenmeisters können selbst auf Bestien einwirken. Wenn er "
        "einen geistesbeeinflussenden Effekt oder sprachabhängigen Zauber wirkt, sind auch "
        "Tiere, magische Bestien und monströse Humanoide betroffen, als wären sie Humanoide, "
        "welche die Sprache des Hexenmeisters verstehen können.",
        [
            "Hypnose", "Gift verzögern", "Monster herbeizaubern III", "Vergiften",
            "Monster festhalten", "Masseneinflüsterung", "Monster herbeizaubern VII",
            "Unwiderstehlicher Tanz", "Monster beherrschen",
        ],
        [
            "Beredsamkeit", "Fertigkeitsfokus", "Geschickte Hände", "Im Kampf zaubern",
            "Kampfreflexe", "Lautlos zaubern", "Täuscher", "Verstohlenheit",
        ],
        [
            (
                "Schlangenzahn",
                1,
                "(AF) Auf der 1. Stufe kann der Hexenmeister sich als Freie Aktion Fangzähne "
                "wachsen lassen. Diese werden als natürliche Waffen behandelt und verursachen "
                "1W4 Schadenspunkte + dem ST-Modifikator des Hexenmeisters (1W3, falls der "
                "Hexenmeister der Größenkategorie Klein angehört) + Gift (Biss - Verletzung; "
                "Rettungswurf ZÄH SG 10 + ½ Stufe als Hexenmeister + KO-Modifikator; Frequenz "
                "1/Runde für 6 Runden; Effekt 1 KO-Schaden; Heilung 1 Rettungswurf). Ab der 5. "
                "Stufe gelten diese Fangzähne als magisch hinsichtlich des Umgehens von "
                "Schadensreduzierung, und der Giftschaden steigt auf 1W2 KO-Schaden. Ab der 7. "
                "Stufe erfordert das Gift zur Heilung 2 Rettungswürfe. Ab der 11. Stufe steigt "
                "der Giftschaden auf 1W4 KO-Schaden. Der Hexenmeister kann diese Fähigkeit "
                "täglich in Höhe seines CH-Modifikators +3 einsetzen.",
                True,
                "self",
            ),
            (
                "Schlangenfreund",
                3,
                "(AF) Ab der 3. Stufe kann der Hexenmeister beliebig Mit Tieren sprechen bei "
                "Reptilien anwenden (inklusive diverser Arten von Dinosauriern, Eidechsen und "
                "anderer kaltblütiger Kreaturen). Darüber hinaus erhält er einen "
                "Vipernvertrauten. Seine effektive Stufe als Magier entspricht dabei seiner "
                "Stufe als Hexenmeister -2.",
                False,
                None,
            ),
            (
                "Schlangenhaut",
                9,
                "(AF) Auf der 9. Stufe erhält der Hexenmeister einen Bonus von +1 auf seine "
                "natürliche Rüstung, einen Volksbonus von +2 auf seine Rettungswürfe gegen Gift "
                "und einen Bonus von +2 auf seine Fertigkeitswürfe für Entfesselungskunst. "
                "Diese Boni steigen auf der 13. Stufe und der 17. Stufe um weitere +1.",
                False,
                None,
            ),
            (
                "Schlangenbrut",
                15,
                "(ZF) Ab der 15. Stufe kann der Hexenmeister eine Masse sich windender Schlangen "
                "herbeizaubern. Dies funktioniert wie Kriechender Tod, wobei das Gift des "
                "Schwarmes KO-Schaden verursacht und jedes Wesen außer ihm, das sich auf "
                "demselben Feld wie der Schwarm befindet, verstrickt wird. Diese Fähigkeit kann "
                "einmal am Tag eingesetzt werden.",
                False,
                None,
            ),
            (
                "Schlangenseele",
                20,
                "(ÜF) Auf der 20. Stufe erhält der Hexenmeister die Unterart Gestaltwandler und "
                "kann nach Belieben die Gestalt eines schlangenartigen Humanoiden (wie der "
                "Zauber Gestalt verändern) oder einer Schlange der Größenkategorie Winzig bis "
                "Riesig annehmen (wie der Zauber Bestiengestalt III). Er behält die Fähigkeit "
                "zu sprechen und Zauber mit Sprachkomponenten zu wirken, wenn er sich "
                "verwandelt. Er wird ferner immun gegen Gift und Lähmung. Er kann seine "
                "Fangzähne beliebig oft einsetzen und sogar wählen, welchem Attribut sein Gift "
                "Schaden zufügen soll.",
                True,
                "self",
            ),
        ],
    ),
    (
        "Sternenblutlinie",
        "Wissen (Natur)",
        "Wenn der Hexenmeister einen Zauber der Unterart Hervorrufung wirkt, sind Ziele, denen "
        "ihr Rettungswurf misslingt, für 1 Runde pro Grad des Zaubers von kleinen glänzenden "
        "Sternenlichtern geblendet.",
        [
            "Unsichtbarer Diener", "Glitzerstaub", "Flimmern", "Gewittersturm herbeirufen",
            "Überlandflug", "Abstoßung", "Schwerkraft umkehren", "Mächtige Ausspähende Augen",
            "Meteoritenschwarm",
        ],
        [
            "Abhärtung", "Ausdauer", "Ausweichen", "Blind kämpfen", "Eiserner Wille",
            "Fertigkeitsfokus", "Schnell zaubern", "Verbesserter Eiserner Wille",
        ],
        [
            (
                "Meteoritenregen",
                1,
                "(ZF) Auf der 1. Stufe kann der Hexenmeister mit einer Standard-Aktion einen "
                "Regen kleiner Meteoriten herbeizaubern, welche in einem säulenförmigen Bereich "
                "von 1,50 m Durchmesser und 9 m Höhe niedergehen, mit einer Reichweite von 9 m. "
                "Die Meteoriten verursachen 1W4 Punkte Feuerschaden + 1 Punkt für jeweils 2 "
                "Stufen als Hexenmeister. Ein erfolgreicher Reflexwurf gegen SG 10 + ½ Stufe "
                "des Hexenmeisters + dem CH-Modifikator des Hexenmeisters schützt vor dem "
                "Schaden. Der Hexenmeister kann diese Fähigkeit täglich in Höhe seines "
                "CH-Modifikators +3 einsetzen.",
                False,
                None,
            ),
            (
                "Leerewandler",
                3,
                "(AF) Auf der 3. Stufe erhält der Hexenmeister Dämmersicht sowie Feuer- und "
                "Kälteresistenz 5. Ab der 9. Stufe muss er nicht mehr atmen, so als trüge er "
                "eine Anpassungshalskette.",
                False,
                None,
            ),
            (
                "Nordlicht",
                9,
                "(ZF) Ab der 9. Stufe kann der Hexenmeister ein dünnes Geflecht aus "
                "kaskadierenden Farben erschaffen. Diese Fähigkeit funktioniert wie Feuerwand, "
                "verursacht jedoch Kälteschaden und gibt keinerlei Wärme ab. Eine Seite des "
                "Nordlichtgeflechts, nach Wahl des Hexenmeisters, fasziniert bis zu 2 TW an "
                "Kreaturen pro Stufe des Hexenmeisters mit einer Reichweite von 3 m. Ein "
                "Willenswurf gegen SG 10 + ½ Stufe des Hexenmeisters + dem CH-Modifikator des "
                "Hexenmeisters hebt den Effekt auf. Der Hexenmeister kann diese Fähigkeit "
                "täglich für eine Anzahl von Runden in Höhe seiner Stufe als Hexenmeister "
                "anwenden. Diese Runden müssen nicht aufeinander folgen.",
                False,
                None,
            ),
            (
                "Zum Mond schießen",
                15,
                "(ZF) Ab der 15. Stufe steigt die Zauberstufe des Hexenmeisters um +3, wenn er "
                "Zauber der Unterart Teleportation einsetzt. Darüber hinaus kann er einmal am "
                "Tag eine einzelne Kreatur innerhalb von 9 m in die Leere des Raumes "
                "teleportieren. Der Kreatur steht ein Willenswurf gegen SG 10 + ½ Stufe des "
                "Hexenmeisters + dem CH-Modifikator des Hexenmeisters gegen diesen Effekt zu. "
                "Bei einem Fehlschlag steht der Kreatur jede Runde als Volle Aktion ein "
                "weiterer Rettungswurf zu, um zurückkehren zu können. Während sie in der "
                "luftlosen Leere gefangen ist, erleidet die Kreatur jede Runde 6W6 Punkte an "
                "Kälteschaden und muss die Luft anhalten, sonst beginnt sie zu ersticken.",
                False,
                None,
            ),
            (
                "Sternenkind",
                20,
                "(AF) Ab der 20. Stufe ist der Hexenmeister gegen Kälte und Blindheit immun. Er "
                "kann perfekt in natürlicher und magischer Dunkelheit sehen. Darüber hinaus "
                "erhält er Schnelle Heilung 1, wenn er sich nachts im Freien aufhält.",
                False,
                None,
            ),
        ],
    ),
    (
        "Sturmblutlinie",
        "Wissen (Natur)",
        "Wenn der Hexenmeister einen Elektrizitäts- oder Schallzauber wirkt, erhöht sich der SG "
        "des Rettungswurfes um +1.",
        [
            "Schockgriff", "Windstoß", "Blitz", "Brüllen", "Überlandflug", "Kugelblitz",
            "Wetterkontrolle", "Wirbelwind", "Sturm der Vergeltung",
        ],
        [
            "Ausweichen", "Fernschuss", "Fertigkeitsfokus", "Große Zähigkeit", "Kernschuss",
            "Schnell wie der Wind", "Tödliche Zielgenauigkeit", "Zauberreichweite erhöhen",
        ],
        [
            (
                "Donnerstab",
                1,
                "(ZF) Auf der 1. Stufe kann der Hexenmeister als Standard-Aktion eine Waffe "
                "berühren und ihr die Eigenschaft Blitz für eine Anzahl von Runden in Höhe "
                "seiner halben Stufe (Minimum 1) als Hexenmeister verleihen. Ab der 9. Stufe "
                "kann er stattdessen für die Hälfte der Zeit einer Waffe die Eigenschaft "
                "Blitzinferno verleihen. Der Hexenmeister kann diese Fähigkeit täglich in Höhe "
                "seines CH-Modifikators +3 einsetzen.",
                False,
                None,
            ),
            (
                "Sturmkind",
                3,
                "(AF) Auf der 3. Stufe erhält der Hexenmeister Elektrizitäts- und "
                "Schallresistenz 5 und behandelt Windeffekte als eine Kategorie schwächer. Ab "
                "der 9. Stufe behandelt er Windeffekte um zwei Kategorien schwächer und erhält "
                "Blindgespür 18 m gegen Tarnung durch natürlichen oder magischen Nebel oder "
                "Wettereffekte.",
                False,
                None,
            ),
            (
                "Donnerkeil",
                9,
                "(ZF) Ab der 9. Stufe kann der Hexenmeister auf Befehl eine blitzartige "
                "Entladung von oben herab regnen lassen, welche in einem zylindrischen Bereich "
                "mit einem Radius von 1,50 m und einer Höhe von 18 m einschlägt. Die Entladung "
                "verursacht 1W6 Schadenspunkte pro Stufe des Hexenmeisters (die Hälfte des "
                "Schadens ist Elektrizitätsschaden, die andere Hälfte Schallschaden). Ein "
                "Reflexwurf gegen SG 10 + ½ Stufe des Hexenmeisters + dem CH-Modifikator des "
                "Hexenmeisters halbiert den Schaden. Kreaturen, deren Rettungswürfe misslingen, "
                "sind für 1 Runde taub. Der Hexenmeister kann diese Fähigkeit auf der 9. Stufe "
                "einmal am Tag, auf der 17. Stufe zweimal am Tag und auf der 20. Stufe dreimal "
                "am Tag einsetzen.",
                False,
                None,
            ),
            (
                "Blitzgestalt",
                15,
                "(ZF) Ab der 15. Stufe kann der Hexenmeister mit einer Vollen Aktion zu einem "
                "lebenden Blitz werden und in gerader Linie bis zum Zehnfachen seiner "
                "Bewegungsrate zurücklegen, ohne dabei Gelegenheitsangriffe zu provozieren. "
                "Kreaturen in seinem Weg erleiden die Auswirkungen der Fähigkeit Donnerkeil. "
                "Der Weg kann nicht durch Kreaturen blockiert werden, jedoch durch feste "
                "Objekte, sofern diese nicht auf 0 Trefferpunkte reduziert wurden. Der "
                "Hexenmeister kann diese Fähigkeit täglich für eine Anzahl von Runden in Höhe "
                "seiner Stufe als Hexenmeister einsetzen.",
                True,
                "self",
            ),
            (
                "Sturmfürst",
                20,
                "(AF) Auf der 20. Stufe wird der Hexenmeister eins mit dem Sturm. Er erlangt "
                "Immunität gegen Taubheit, Betäubung und Windeffekte und erhält Blindsicht "
                "36 m gegen Tarnung durch natürlichen oder magischen Nebel oder Wettereffekte. "
                "Einmal am Tag kann er bei einem Angriff mit Elektrizität oder Schalleffekten "
                "gegen ihn auf seinen Rettungswurf verzichten und stattdessen die Energie "
                "absorbieren. Er erleidet keinen Schaden, sondern heilt 1 Trefferpunkt pro 3 "
                "Schadenspunkte.",
                False,
                None,
            ),
        ],
    ),
    (
        "Tiefenblutlinie",
        "Wissen (Gewölbekunde)",
        "Wenn der Hexenmeister und sein Ziel sich beide unter der Erde befinden, steigen die "
        "Schwierigkeitsgrade der Rettungswürfe gegen seine Zauber um +1.",
        [
            "Rasches Graben", "Dunkelsicht", "Versanden", "Steinhaut", "Steindornen",
            "Erzählende Steine", "Metall oder Stein zurücktreiben", "Erdbeben",
            "Zerschmetternde Felsen",
        ],
        [
            "Behände Bewegung", "Blind kämpfen", "Fertigkeitsfokus", "Geschmeidige Bewegung",
            "Gestenlos zaubern", "Ring schmieden", "Verstohlenheit", "Wachsamkeit",
        ],
        [
            (
                "Beben",
                1,
                "(ZF) Auf der 1. Stufe kann der Hexenmeister mit einer Standard-Aktion den "
                "Boden unter einer einzelnen Kreatur innerhalb von 9 m zum Erbeben bringen. "
                "Dies funktioniert, als würde er das Kampfmanöver Zu-Fall-bringen gegen das "
                "Ziel mit seiner Stufe als Hexenmeister plus seines CH-Modifikator statt seines "
                "KMB einsetzen. Der Hexenmeister kann diese Fähigkeit täglich in Höhe seines "
                "CH-Modifikators +3 einsetzen.",
                False,
                None,
            ),
            (
                "Felsseher",
                3,
                "(ÜF) Auf der 3. Stufe erhält der Hexenmeister Steingespür wie ein Zwerg. "
                "Sollte er ein Zwerg sein, so steigt sein Bonus auf +4. Auf der 9. Stufe erhält "
                "er Erschütterungssinn auf 9 m. Ab der 15. Stufe kann er durch feste "
                "Gegenstände sehen, als würde er einen Röntgenblickring verwenden. Dies kann er "
                "täglich für eine Anzahl von Runden in Höhe seiner Stufe als Hexenmeister. Die "
                "Runden müssen nicht aufeinander folgen.",
                False,
                None,
            ),
            (
                "Kristallscherbe",
                9,
                "(ZF) Ab der 9. Stufe kann der Hexenmeister eine Metall- oder Steinwaffe (oder "
                "bis zu 50 Munitionsgeschosse) mit einer Standard-Aktion berühren und ihnen für "
                "1 Minute die Eigenschaft Verderben gegen Kreaturen der Erde, Schlicke oder "
                "Konstrukte aus Stein oder Metall verleihen. Er kann diese Fähigkeit auf der 9. "
                "Stufe einmal am Tag, auf der 17. Stufe zweimal am Tag und auf der 20. Stufe "
                "dreimal am Tag benutzen.",
                False,
                None,
            ),
            (
                "Durch Erde gleiten",
                15,
                "(AF) Ab der 15. Stufe kann der Hexenmeister durch natürliche Erde und Stein "
                "gleiten wie ein Fisch durchs Wasser. Seine Grab-Bewegungsrate entspricht seiner "
                "halben normalen Bewegungsrate. Er kann diese Fähigkeit täglich für eine Anzahl "
                "von Minuten in Höhe seiner Stufe als Hexenmeister verwenden. Diese Minuten "
                "müssen nicht aufeinander folgen, werden jedoch in Einheiten von 1 Minute "
                "berechnet.",
                True,
                "self",
            ),
            (
                "Stärke des Steines",
                20,
                "(ÜF) Auf der 20. Stufe wird das Fleisch des Hexenmeisters hart wie Stein. Er "
                "erhält SR 10/Adamant und wird immun gegen Versteinerung. Er erleidet keine "
                "Mali, wenn er sich durch enge Räume quetscht und ist immer gegen Ansturm, "
                "Ringkampf, Versetzen, Zerren und Zu-Fall-bringen sowie alle Effekte und "
                "Fähigkeiten, die ihn in irgendeiner Weise gegen seinen Willen bewegen, immun, "
                "solange er auf dem Boden steht.",
                False,
                None,
            ),
        ],
    ),
    (
        "Traumblutlinie",
        "Motiv erkennen",
        "Wenn der Hexenmeister eine einzelne Kreatur mit einem Zauber betrifft, erhält er für "
        "1 Runde einen Verständnisbonus auf seine RK und Rettungswürfe gegen Zauber und "
        "Angriffe von dieser Kreatur in Höhe des halben Zaubergrades des Zaubers (Minimum +1).",
        [
            "Schlaf", "Vorahnung", "Tiefschlaf", "Weissagung", "Traum", "Schattenreise",
            "Vision", "Moment der Eingebung", "Astrale Projektion",
        ],
        [
            "Beredsamkeit", "Blind kämpfen", "Defensive Kampfweise", "Fertigkeitsfokus",
            "Täuscher", "Verbesserte Finte", "Wachsamkeit", "Zaubergrad erhöhen",
        ],
        [
            (
                "Schlaflied",
                1,
                "(ZF) Auf der 1. Stufe kann der Hexenmeister täglich Schlaflied als "
                "Zauberähnliche Fähigkeit in Höhe seines CH-Modifikators +3 einsetzen. Der "
                "Effekt hält 1 Minute an und erfordert keine Konzentration. Der Malus auf "
                "Rettungswürfe gegen Schlafeffekte steigt auf -4.",
                False,
                None,
            ),
            (
                "Vorausschauender Kämpfer",
                3,
                "(ÜF) Das Verständnis, welches der Hexenmeister über die Zukunft erlangt, "
                "verleiht ihm einen Vorteil im Kampf. Ab der 3. Stufe erhält er einen "
                "Verständnisbonus von +1 auf seine Initiative. Dieser Bonus steigt alle vier "
                "weiteren Stufen um zusätzliche +1.",
                False,
                None,
            ),
            (
                "Traumformer",
                9,
                "(ZF) Ab der 9. Stufe kann der Hexenmeister die Träume anderer manipulieren, "
                "einsehen oder mit ihrem Unterbewusstsein spielen. Diese Fähigkeit erlaubt ihm, "
                "die Erinnerungen seines Zieles wie mit Erinnerung verändern zu beeinflussen "
                "oder ihm Fragen zu stellen ähnlich wie Mit Toten sprechen. Ein erfolgreicher "
                "Willenswurf gegen SG 10 + ½ Stufe des Hexenmeisters + dem CH-Modifikator des "
                "Hexenmeisters + weitere Modifikationen (wie beispielsweise beim Zauber "
                "Albtraum) hebt den Effekt auf. Der Hexenmeister kann diese Fähigkeit auf der "
                "9. Stufe einmal am Tag, auf der 17. Stufe zweimal am Tag und auf der 20. Stufe "
                "dreimal am Tag benutzen.",
                False,
                None,
            ),
            (
                "Somnus Auge",
                15,
                "(ZF) Ab der 15. Stufe kann der Hexenmeister einmal am Tag sein Bewusstsein "
                "projizieren, als würde er Arkanes Auge verwenden. Ferner kann er das Arkanes "
                "Auge jederzeit sichtbar werden lassen. In diesem Fall ist es nicht länger "
                "beweglich, fungiert aber als Symbol des Schlafs für jeden, der es sieht.",
                False,
                None,
            ),
            (
                "Solipsismus",
                20,
                "(AF) Ab der 20. Stufe kann der Hexenmeister in die Traumwelt eintreten, wobei "
                "er immer mehr aus der Welt um ihn herum verblasst. Er kann täglich für 1 "
                "Minute pro Stufe als Hexenmeister körperlos werden. Die Zeit muss nicht "
                "aufeinander folgen, wird aber in Einheiten von jeweils 1 Minute berechnet. Er "
                "erhält die Unterart Körperlos und nimmt nur halben Schaden durch körperliche "
                "magische Angriffe (nichtmagische Waffen und Gegenstände verursachen keinen "
                "Schaden). Seine Zauber verursachen bei körperlichen Wesen nur halben Schaden, "
                "Zauber und Fähigkeiten, die keinen Schaden verursachen, funktionieren normal.",
                True,
                "self",
            ),
        ],
    ),
]


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, rows: list[dict]) -> None:
    deduped: dict[str, dict] = {}
    for row in rows:
        deduped[row["id"]] = row
    path.write_text(json.dumps(list(deduped.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def strip_qualifier(name: str) -> str:
    return re.sub(r"\s*\(.*?\)\s*$", "", name).strip()


def main() -> None:
    choices = load(SEED_DIR / "base_class_option_choices.json")
    groups = load(SEED_DIR / "base_class_option_groups.json")
    abilities = load(SEED_DIR / "base_class_abilities.json")
    grants = load(SEED_DIR / "base_class_ability_grants.json")
    feat_options = load(SEED_DIR / "base_class_ability_feat_options.json")
    spell_grants = load(SEED_DIR / "base_class_spell_grants.json")
    skills = load(SEED_DIR / "base_class_skills.json")

    feats_catalog = load(SEED_DIR / "base_feats.json")
    feat_id_by_name = {f["name"]: f["id"] for f in feats_catalog}
    spells_catalog = load(SEED_DIR / "base_spells.json")
    spell_id_by_name = {s["name"]: s["id"] for s in spells_catalog}
    skill_catalog = load(SEED_DIR / "base_skills.json")
    skill_id_by_name = {s["name"]: s["id"] for s in skill_catalog}

    bloodline_group = next(g for g in groups if g["base_class_id"] == HEXENMEISTER_ID and g["key"] == "bloodline")
    group_id = bloodline_group["id"]

    talent_des_blutes_ability_id = next(
        a["id"] for a in abilities if a["name"] == "Talent des Blutes" and a["id"] in {
            g["ability_id"] for g in grants if g["base_class_id"] == HEXENMEISTER_ID and g["option_choice_id"] is None
        }
    )

    new_choices: list[dict] = []
    new_abilities: list[dict] = []
    new_grants: list[dict] = []
    new_feat_options: list[dict] = []
    new_spell_grants: list[dict] = []
    new_skills: list[dict] = []
    unresolved: list[str] = []

    for choice_name, skill_name, arcana_description, spell_names, feat_names, powers in BLOODLINES:
        choice_id = uid("hexenmeister-experten-bloodline-choice", choice_name)
        new_choices.append({"id": choice_id, "group_id": group_id, "name": choice_name})

        arcana_id = uid("hexenmeister-experten-bloodline-ability", choice_id, "arcana")
        new_abilities.append(
            {
                "id": arcana_id,
                "name": f"Geheimnis des Blutes ({choice_name})",
                "description": arcana_description,
            }
        )
        new_grants.append(
            {
                "id": uid("hexenmeister-experten-bloodline-grant", choice_id, "arcana"),
                "base_class_id": HEXENMEISTER_ID,
                "ability_id": arcana_id,
                "option_choice_id": choice_id,
                "level": 1,
            }
        )

        for power_name, level, description, is_persistent, activation_scope in powers:
            power_id = uid("hexenmeister-experten-bloodline-ability", choice_id, power_name)
            ability_row: dict = {"id": power_id, "name": power_name, "description": description}
            if is_persistent:
                ability_row["is_persistent_effect"] = True
                ability_row["activation_scope"] = activation_scope
            new_abilities.append(ability_row)
            new_grants.append(
                {
                    "id": uid("hexenmeister-experten-bloodline-grant", choice_id, power_name),
                    "base_class_id": HEXENMEISTER_ID,
                    "ability_id": power_id,
                    "option_choice_id": choice_id,
                    "level": level,
                }
            )

        for i, raw_name in enumerate(spell_names):
            name = strip_qualifier(raw_name.rstrip("*").strip())
            name = SPELL_NAME_ALIASES.get(name, name)
            spell_id = spell_id_by_name.get(name)
            if spell_id is None:
                unresolved.append(f"{choice_name}: spell {raw_name!r}")
                continue
            new_spell_grants.append(
                {
                    "id": uid("hexenmeister-experten-bloodline-spell-grant", choice_id, spell_id, str(BONUS_SPELL_LEVELS[i])),
                    "base_class_id": HEXENMEISTER_ID,
                    "option_choice_id": choice_id,
                    "spell_id": spell_id,
                    "level": BONUS_SPELL_LEVELS[i],
                }
            )

        for feat_name in feat_names:
            feat_id = feat_id_by_name.get(strip_qualifier(feat_name))
            if feat_id is None:
                unresolved.append(f"{choice_name}: feat {feat_name!r}")
                continue
            new_feat_options.append(
                {
                    "id": uid("hexenmeister-experten-bloodline-feat-option", choice_id, feat_id),
                    "ability_id": talent_des_blutes_ability_id,
                    "option_choice_id": choice_id,
                    "feat_type": None,
                    "feat_id": feat_id,
                }
            )

        skill_id = skill_id_by_name.get(skill_name)
        if skill_id is None:
            unresolved.append(f"{choice_name}: skill {skill_name!r}")
        else:
            new_skills.append(
                {
                    "id": uid("hexenmeister-experten-bloodline-skill", choice_id, skill_id),
                    "base_class_id": HEXENMEISTER_ID,
                    "skill_id": skill_id,
                    "option_choice_id": choice_id,
                }
            )

    save(SEED_DIR / "base_class_option_choices.json", choices + new_choices)
    save(SEED_DIR / "base_class_abilities.json", abilities + new_abilities)
    save(SEED_DIR / "base_class_ability_grants.json", grants + new_grants)
    save(SEED_DIR / "base_class_ability_feat_options.json", feat_options + new_feat_options)
    save(SEED_DIR / "base_class_spell_grants.json", spell_grants + new_spell_grants)
    save(SEED_DIR / "base_class_skills.json", skills + new_skills)

    print(f"Wrote {len(new_choices)} bloodline choices, {len(new_abilities)} abilities,")
    print(f"  {len(new_grants)} grants, {len(new_feat_options)} feat options,")
    print(f"  {len(new_spell_grants)} spell grants, {len(new_skills)} skill rows.")
    if unresolved:
        print(f"WARNING: {len(unresolved)} unresolved reference(s):")
        for entry in unresolved:
            print(f"  {entry}")


if __name__ == "__main__":
    main()
