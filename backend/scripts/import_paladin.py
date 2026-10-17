"""Import the (Grundregelwerk core) Paladin's class shell from
http://prd.5footstep.de/Grundregelwerk/Klassen/Paladin — roadmap slice 10,
step 0b ("Paladin as a complete class"), the prerequisite for the Paladin's
mount as an animal-companion source.

`hit_dice`/`bab_progression`/`fort_save`/`ref_save`/`wil_save`/
`skill_points_base` on `base_classes.json`'s existing Paladin row were
already correct (W10, full GAB, good Fort/Will, 2 + IN) — verified against
"Tabelle: Paladin", not re-written. The `favored_class_bonus` option group
already existed too.

What this script does:
- `base_classes.json`: sets the Paladin's `casting_ability` (CH) and
  `spell_tradition` (divine) — both were null — and `allowed_alignments`
  (["LG"], "Gesinnung: Rechtschaffen Gut"); the Druide's row gets its
  "any neutral component" list in the same pass (roadmap: the alignment
  field is built once, here, for both classes).
- `classes.json`: the Paladin's `spellType` "none" -> "divine-prepared".
- Fixes `base_class_skills.json`: the existing 7 rows were missing Beruf,
  Mit Tieren umgehen and Zauberkunde — corrected to the page's 10. Existing
  rows keep their ids (same "look up by skill name" shape as
  `import_druide.py`).
- Adds the class features as `BaseClassAbility`/`BaseClassAbilityGrant`
  rows (1st–20th level). Böses niederstrecken and the weapon variant of
  Göttlicher Bund are persistent self effects (activated like Kampfrausch);
  everything with a per-day count gets its handler in
  `rules/classes/paladin.py`.
- "Gnade" is a recurring option group (`mercy`, label = the slot ability's
  name, granted at 3/6/9/12/15/18 — `rules/class_options.py`'s
  occurrence convention): 16 choices with `min_level` 3/6/9/12 and
  `requires_choice_id` for the three PRD prerequisites (Entkräftet ->
  Erschöpft, Übelkeit -> Kränkelnd, Verängstigt -> Erschüttert). Each choice
  grants its own "Gnade: …" ability so the sheet lists what was picked.
- "Göttlicher Bund" is a one-time option group (`divine_bond`, granted at
  5): "Waffe" grants "Göttlicher Bund: Waffe" (the weapon spirit), "Reittier"
  grants "Göttlicher Bund: Reittier" (the trigger ability slice 10's
  `BaseCompanionLevelSource` will key on) plus "Reittier herbeirufen".
- Proficiencies via `BaseClassAbilityGrantedFeat` (simple + martial weapons,
  light/medium/heavy armor, shields — no tower shields).
- Spell list: `base_class_spells.json` rows straight from the already-
  fetched PRD spell index (`zauber_prd_import.json`'s `grades_by_class`
  "Paladin" key, same backfill as `import_kampfmagus.py`). Spells only the
  Paladin casts had no `base_spells.json` row yet (`build_spells_seed.py`
  dropped them, the Paladin had no `spell_tradition`) — they're added here
  from `zauber_prd_details.json`, built exactly the way
  `build_spells_seed.py` builds a row. Run `build_spell_components_seed.py`
  afterward for their components (idempotent).
- Spells per day: not here — `build_spells_per_day_seed.py` lists the
  Paladin with the Waldläufer (identical table and grade-unlock levels).

Deliberately out of scope (descriptive text only for now):
- Weapon-spirit special abilities (spending the bonus on Heilig, Schärfe,
  …) — the bonus itself is applied as a temporary enhancement on the chosen
  weapon, the special abilities are text.
- Auras' effects on allies, the immunities, DR 5/10/Böses — no sheet
  section models immunities or damage reduction yet.
- Mount death / weapon destroyed penalties (−1 attack/damage for 30 days)
  — a condition, not class logic.
- The mount itself (roadmap slice 10 steps 1–3).
- "Ehemaliger Paladin"/code of conduct — descriptive.
- Paladin archetypes.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database — run the normal seed scripts afterward):
    cd backend && python scripts/import_paladin.py
    python scripts/build_spells_per_day_seed.py
    python scripts/build_spell_components_seed.py
    python -m app.seed.class_seed
    python -m app.seed.skill_seed
    python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed
    python -m app.seed.class_ability_granted_feat_seed
    python -m app.seed.spell_seed
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"
IMPORTED_DIR = FIXTURES / "imported"

ID_NAMESPACE = uuid.UUID("8d2e4f61-7a3b-4c5d-9e0f-1a2b3c4d5e6f")

PALADIN_ID = "561465fe-7c72-4e47-b58e-05a8dbbf0a3e"
DRUIDE_ID = "2835c712-7129-41fe-a61e-8ef05de2e0cf"

PALADIN_ALIGNMENTS = ["LG"]
DRUIDE_ALIGNMENTS = ["NG", "LN", "N", "CN", "NE"]

CORRECT_CLASS_SKILLS = [
    "Beruf",
    "Diplomatie",
    "Handwerk",
    "Heilkunde",
    "Mit Tieren umgehen",
    "Motiv erkennen",
    "Reiten",
    "Wissen (Adel)",
    "Wissen (Religion)",
    "Zauberkunde",
]

PROFICIENCY_FEATS = [
    "Umgang mit einfachen Waffen",
    "Umgang mit Kriegswaffen",
    "Umgang mit Rüstungen (leichte)",
    "Umgang mit Rüstungen (mittelschwere)",
    "Umgang mit Rüstungen (schwere)",
    "Umgang mit Schilden",
]

BOESES_NIEDERSTRECKEN_DESC = (
    "(ÜF) Ein Mal pro Tag kann der Paladin die Mächte des Guten anrufen, um ihm in seinem Kampf gegen das Böse "
    "zur Seite zu stehen. Als Schnelle Aktion wählt er ein sichtbares Ziel zum Niederstrecken aus. Wenn das Ziel "
    "von böser Gesinnung ist, dann addiert er seinen CH-Bonus (wenn er einen hat) zu allen Angriffswürfen hinzu "
    "und addiert seine Paladinstufe zum Schaden, die er seinem Ziel durch Böses niederstrecken zufügt. Ist das "
    "Ziel der Fähigkeit Böses niederstrecken gar ein Externar der Unterkategorie böse, ein böse gesinnter Drache "
    "oder ein Untoter, erhöht sich der Bonusschaden auf den ersten erfolgreichen Angriff auf 2 Punkte je "
    "Paladinstufe. Unabhängig vom Ziel umgehen Angriffe zum Niederstrecken eines bösen Ziels jedwede "
    "Schadensreduzierung, die die Kreatur haben mag.\n\n"
    "Außerdem erhält der Paladin einen Ablenkungsbonus in Höhe seines CH-Bonus (wenn er einen hat) zu seiner "
    "Rüstungsklasse gegen Angriffe, die das Ziel seines Niederstreckens macht. Sollte der Paladin einen Gegner "
    "als Ziel aussuchen, der nicht böse ist, verpufft das Niederstrecken ohne jegliche Wirkung.\n\n"
    "Die Effekte des Niederstreckens bleiben so lange aktiv, bis das Ziel tot ist oder bis der Paladin eine "
    "ausgiebige Rast einlegt und die Fähigkeit zum Niederstrecken von Bösem wieder erlangt. Auf der 4. Stufe und "
    "dann alle drei weiteren Stufen kann der Paladin die Fähigkeit ein weiteres Mal pro Tag bis zu einem Maximum "
    "von sieben Mal täglich auf der 19. Stufe einsetzen, wie es in der Tabelle angegeben ist."
)

HANDAUFLEGEN_DESC = (
    "(ÜF) Ab der 2. Stufe kann der Paladin durch Berührung bei sich selber oder bei Verbündeten Wunden heilen. "
    "Er kann diese Fähigkeit so oft pro Tag nutzen, wie es seiner halben Paladinstufe plus seinem "
    "CH-Modifikator entspricht. Mit einer Anwendung kann er Trefferpunkte in Höhe von je 1W6 Schadenspunkten pro "
    "2 Paladinstufen heilen. Um diese Fähigkeit einzusetzen, muss der Paladin eine Standard-Aktion aufwenden, "
    "außer er wählt sich selbst. In diesem Fall ist das Handauflegen nur eine Schnelle Aktion. Der Paladin "
    "braucht nur eine freie Hand zum Handauflegen.\n\n"
    "Alternativ kann der Paladin Handauflegen nutzen, um Untoten Schaden zuzufügen, anstatt zu heilen, und "
    "verursacht damit 1W6 Punkte Schaden für jeweils 2 Paladinstufen, die er hat. Um die Fähigkeit auf diese "
    "Art zu nutzen, muss dem Paladin ein Berührungsangriff gelingen. Dieser Angriff provoziert keinen "
    "Gelegenheitsangriff. Untote erhalten keinen Rettungswurf gegen diesen Schaden."
)

GNADE_DESC = (
    "(ÜF) Auf der 3. Stufe und alle weiteren drei Stufen danach kann sich der Paladin eine Gnade auswählen. "
    "Jede Gnade fügt einen weiteren Effekt zum Handauflegen hinzu. Immer dann, wenn der Paladin Handauflegen "
    "einsetzt, um bei einem Ziel Schaden zu heilen, erhält das Ziel außerdem die zusätzlichen Effekte aller "
    "Gnaden, die dem Paladin gewährt worden sind. Eine Gnade kann einen Zustand verschwinden lassen, der von "
    "einem Fluch, einer Krankheit oder einem Gift verursacht wurde, ohne das Gebrechen selber zu kurieren. "
    "Solche Zustände kehren nach einer Stunde wieder zurück, wenn nicht das Gebrechen selbst von einer Gnade "
    "kuriert worden ist.\n\n"
    "Auf der 3. Stufe stehen Erschöpft, Erschüttert und Kränkelnd zur Wahl, ab der 6. Stufe zusätzlich "
    "Benommen, Krank und Wankend, ab der 9. Stufe Entkräftet, Übelkeit, Verängstigt, Verflucht und Vergiftet, "
    "ab der 12. Stufe Betäubt, Blind, Gelähmt und Taub.\n\n"
    "Diese Fähigkeiten sind kumulativ. Zum Beispiel heilt das Handauflegen eines Paladins der 12. Stufe 6W6 "
    "Punkte Schaden, könnte die Zustände erschöpft und entkräftet entfernen und zusätzlich Krankheit kurieren "
    "und Gift neutralisieren. Sobald ein Zustand oder Zaubereffekt als Gnade ausgewählt worden ist, lässt sich "
    "dies nicht mehr ändern."
)

ZAUBER_DESC = (
    "Beginnend mit der 4. Stufe kann der Paladin eine kleine Anzahl von Zaubern pro Tag wirken. Er entnimmt "
    "seine Zauber der Paladin Zauberliste. Er muss seine Zauber im Vorhinein auswählen und vorbereiten.\n\n"
    "Um einen Zauber vorzubereiten, muss der Paladin mindestens einen Charismawert von 10 + Grad des Zaubers "
    "haben. Der Schwierigkeitsgrad von Rettungswürfen gegen die Zauber des Paladins ist 10 + Grad des Zaubers + "
    "CH-Modifikator des Paladins.\n\n"
    "Wie andere Zauberanwender kann auch der Paladin nur eine begrenze Zahl von Zaubern pro Tag wirken. Die "
    "tägliche Anzahl seiner Zauber ist der Tabelle zu entnehmen. Der Paladin erhält Bonuszauber für hohes "
    "Charisma (siehe Tabelle: Attributsmodifikatoren und zusätzliche Zauber pro Tag). Sollte in der Tabelle "
    "unter einem Zaubergrad die Anzahl 0 stehen, bedeutet das, der Paladin erhält nur dann einen Zauber dieses "
    "Grades, wenn er über Bonuszauber aufgrund seines Charismas verfügt.\n\n"
    "Ein Paladin muss jeden Tag eine Stunde in stillem Gebet und Meditation verbringen, um seine täglichen "
    "Zauber zu erhalten. Der Paladin kann jeden Zauber aus der Paladin-Zauberliste wählen, vorausgesetzt er "
    "verfügt über eine ausreichend hohe Stufe, ihn zu wirken. Er muss seine Zauber bei seiner täglichen "
    "Meditation auswählen. Bis zur 4. Stufe hat der Paladin keine Zauberstufe. Ab der 4. Stufe zählt dann seine "
    "Paladinstufe – 3 als Zauberstufe."
)

GOETTLICHER_BUND_DESC = (
    "(ZF) Mit dem Erreichen der 5. Stufe formt der Paladin einen göttlichen Bund mit seiner Gottheit. Dieser "
    "Bund kann sich in einer von zwei Formen manifestieren (Waffe oder Reittier). Ist die Form einmal gewählt, "
    "kann sie nicht geändert werden."
)

BUND_WAFFE_DESC = (
    "(ZF) Der Paladin kann seine Waffe mit Hilfe einer Standard-Aktion verbessern, indem er einen göttlichen "
    "Geist herbeiruft, der je eine Minute pro Paladinstufe bleibt. Einmal herbeigerufen, lässt der Geist die "
    "Waffe mit einem Licht erstrahlen, das die Umgebung wie eine Fackel erleuchtet. Ab der 5. Stufe des "
    "Paladins erhält seine Waffe einen Verbesserungsbonus von +1. Für jeweils drei weitere Stufen erhöht sich "
    "der Bonus um +1, bis zu einem Maximum von +6 auf der 20. Stufe. Dieser Bonus kann zu bestehenden Boni der "
    "Waffe bis zu einem Maximum von +5 addiert werden oder genutzt werden, um eine der folgenden "
    "Waffeneigenschaften zu erhalten: Aufflammen, Flammeninferno, Gnade, Grundsatz, Heilig, Schärfe, "
    "Schnelligkeit, Schutz oder Strahlendes Licht. Das Hinzufügen verbraucht einen Bonus aus dem Göttlichen "
    "Bund, der den Kosten dieser Waffeneigenschaft entspricht. Diese Fähigkeiten werden zu den anderen "
    "Eigenschaften hinzugefügt, die die Waffe schon hat, addieren sich aber nicht, wenn diese Eigenschaft schon "
    "vorhanden ist. Ist die Waffe nicht magisch, muss der Paladin erst einmal einen Bonus von +1 wählen, bevor "
    "er andere Effekte nutzen kann. Der Bonus und die Waffeneigenschaften werden festgelegt, wenn der Geist "
    "herbeigerufen wird, und können nicht geändert werden, bis der Geist erneut gerufen wird. Der göttliche "
    "Geist gewährt einem anderen Träger als dem Paladin keinen Bonus, aktiviert den Bonus aber wieder, wenn der "
    "Paladin die Waffe zurückerhält. Im Falle einer Doppelwaffe gilt der Bonus nur für ein Ende. Auf der 5. "
    "Stufe kann der Paladin den Bund ein Mal pro Tag wirken. Alle vier weiteren Stufen erhält er eine Anwendung "
    "pro Tag hinzu, bis zu einem Maximum von vier Mal auf der 17. Stufe.\n\n"
    "Sollte die mit göttlichem Geist beseelte Waffe zerstört werden, verliert der Paladin seinen Bund für 30 "
    "Tage, oder bis er eine Stufe aufsteigt, je nach dem, was vorher eintritt. Während dieser 30 Tage erleidet "
    "der Paladin einen Malus von –1 auf Angriffe und Waffenschaden."
)

BUND_REITTIER_DESC = (
    "(ZF) Der Paladin erlangt die Dienste eines loyalen, starken und ungewöhnlich intelligenten Reittiers für "
    "seinen Kreuzzug gegen das Böse. Dieses Reittier ist üblicherweise ein schweres Streitross (für einen "
    "mittelgroßen Paladin) oder ein Kriegspony (für einen kleinen Paladin), obwohl auch exotischere Reittiere, "
    "wie z.B. ein Eber, ein Hund oder ein Kamel möglich sind. Dieses Reittier verhält sich wie der Tiergefährte "
    "eines Druiden, wobei der Charakter seine Paladinstufe als seine effektive Druidenstufe ansetzt. Reittiere "
    "im göttlichen Bund haben eine Intelligenz von mindestens 6.\n\n"
    "Ab der 11. Stufe erhält das Reittier die Celestische Schablone und wird zu einer Magischen Bestie, wenn es "
    "darum geht zu bestimmen, welche Zauber auf das Reittier wirken. Ab der 15. Stufe erhält das Reittier "
    "Zauberresistenz in Höhe der Paladinstufe des Reiters +11.\n\n"
    "Sollte das Reittier sterben, verschwindet es sofort und lässt jede Ausrüstung zurück, die es trug. Der "
    "Paladin kann dann 30 Tage lang, oder bis er eine Stufe aufsteigt, wenn dies vorher passiert, kein Reittier "
    "mehr herbeirufen. Der Paladin erleidet während dieser 30 Tage einen Malus von –1 auf Angriffe und "
    "Waffenschaden."
)

REITTIER_HERBEIRUFEN_DESC = (
    "(ZF) Ein Mal pro Tag kann der Paladin eine Volle Aktion aufwenden und sein Reittier an seine Seite rufen. "
    "Diese Fähigkeit entspricht dem Zauber eines Grades in Höhe eines Drittels der Stufe des Paladins. Das "
    "Reittier erscheint sofort direkt neben dem Paladin. Der Paladin kann diese Fähigkeit einmal am Tag ab der "
    "5. Stufe einsetzen, und ein weiteres Mal für alle vier weiteren Paladinstufen, bis zu einem Maximum von "
    "viermal am Tag ab der 17. Stufe."
)

# (name, levels, description, extra BaseClassAbility columns)
CLASS_FEATURES: list[tuple[str, list[int], str, dict]] = [
    (
        "Umgang mit Waffen und Rüstungen",
        [1],
        "Der Paladin ist im Umgang mit allen einfachen Waffen und Kriegswaffen sowie mit allen Rüstungen und mit "
        "allen Schilden (außer mit Turmschilden) geübt.",
        {},
    ),
    (
        "Aura des Guten",
        [1],
        "(AF) Die Macht der Aura des Guten (siehe den Zauber Gutes entdecken) des Paladins entspricht seiner "
        "Stufe in dieser Klasse.",
        {},
    ),
    (
        "Böses entdecken",
        [1],
        "(ZF) Ein Paladin kann diese Fähigkeit nach Belieben wie den Zauber Böses entdecken nutzen. Er kann sich "
        "im Rahmen einer Bewegungsaktion auf einen einzelnen Gegenstand oder ein Individuum innerhalb von 18 m "
        "konzentrieren und damit herausfinden, ob das Ziel böse ist und die Stärke seiner Aura erkennen, als hätte "
        "er das Ziel 3 Runden lang studiert. Während er sich auf ein Ziel konzentriert, kann der Paladin nicht die "
        "böse Gesinnung in anderen Wesen oder Objekten entdecken.",
        {},
    ),
    (
        "Böses niederstrecken",
        [1],
        BOESES_NIEDERSTRECKEN_DESC,
        {"is_persistent_effect": True, "activation_scope": "self"},
    ),
    (
        "Göttliche Würde",
        [2],
        "(ÜF) Auf der 2. Stufe erhält der Paladin seinen CH-Bonus (wenn er einen hat) auf alle Rettungswürfe.",
        {},
    ),
    ("Handauflegen", [2], HANDAUFLEGEN_DESC, {}),
    (
        "Aura der Tapferkeit",
        [3],
        "(ÜF) Auf der 3. Stufe wird der Paladin immun gegen jede Art von Furcht, sei sie natürlichen oder "
        "magischen Ursprungs. Zudem erhält jeder Verbündete, wenn er sich innerhalb von 3 m um den Paladin "
        "befindet, einen Moralbonus von +4 auf seine Rettungswürfe gegen Furcht. Diese Fähigkeit wirkt nur, wenn "
        "der Paladin bei Bewusstsein ist. Ist er bewusstlos oder tot, kann er seinen Verbündeten keinen Bonus "
        "mehr gewähren.",
        {},
    ),
    (
        "Göttliche Gesundheit",
        [3],
        "(AF) Auf der 3. Stufe wird der Paladin immun gegen alle Krankheiten, selbst wenn diese übernatürlichen "
        "oder magischen Ursprungs sind.",
        {},
    ),
    # Slot ability of the `mercy` option group — its name must equal the
    # group's label (`rules/class_options.py`).
    ("Gnade", [3, 6, 9, 12, 15, 18], GNADE_DESC, {}),
    (
        "Positive Energie fokussieren",
        [4],
        "(ÜF) Mit dem Erreichen der 4. Stufe erhält der Paladin die übernatürliche Fähigkeit, positive Energie "
        "zu fokussieren. Der Einsatz dieser Fähigkeit verbraucht zwei Anwendungen seines Handauflegens. Er nutzt "
        "die Fähigkeit zum Energie fokussieren, wie es ein Kleriker mit seiner Paladinstufe tun würde. Dies ist "
        "eine auf Charisma basierende Fähigkeit.",
        {},
    ),
    ("Zauber", [4], ZAUBER_DESC, {}),
    # Slot ability of the `divine_bond` option group (same name = label rule).
    ("Göttlicher Bund", [5], GOETTLICHER_BUND_DESC, {}),
    (
        "Aura der Entschlossenheit",
        [8],
        "(ÜF) Ab der 8. Stufe ist der Paladin gegen Zaubersprüche und zauberähnliche Effekte der "
        "Bezauberungsmagie immun. Verbündete, die sich innerhalb von 3 m in der Nähe des Paladins aufhalten, "
        "bekommen einen Moralbonus von +4 auf ihre Rettungswürfe gegen Bezauberungseffekte.\n\n"
        "Diese Fähigkeit wirkt nur, wenn der Paladin bei Bewusstsein ist. Der Bonus fällt weg, wenn er bewusstlos "
        "oder tot ist.",
        {},
    ),
    (
        "Aura der Gerechtigkeit",
        [11],
        "(ÜF) Ab der 11. Stufe kann der Paladin zwei Anwendungen von Böses niederstrecken ausgeben, um allen "
        "Verbündeten innerhalb von 3 m die Fähigkeit Böses niederstrecken mit seinen Boni zu verleihen. Die "
        "Verbündeten müssen diese Fähigkeit bis zur nächsten Runde des Paladins eingesetzt haben. Diese Boni "
        "halten eine Minute. Der Einsatz dieser Fähigkeit ist eine Freie Aktion. Böse Kreaturen profitieren "
        "nicht von dieser Fähigkeit.",
        {},
    ),
    (
        "Aura des Glaubens",
        [14],
        "(ÜF) Ab der 14. Stufe gelten die Waffen des Paladins als gut gesonnen für den Zweck, "
        "Schadensreduzierungen zu überwinden. Jeder Angriff, der innerhalb von 3 m um den Paladin gegen Feinde "
        "geführt wird, zählt ebenfalls als gut gesonnen, um die Schadensreduzierung zu überwinden.\n\n"
        "Diese Fähigkeit funktioniert nur, solange der Paladin bei Bewusstsein ist, nicht wenn er tot oder "
        "bewusstlos ist.",
        {},
    ),
    (
        "Aura der Rechtschaffenheit",
        [17],
        "(ÜF) Ab der 17. Stufe erhält der Paladin eine Schadensreduzierung von 5/Böses und ist immun gegen "
        "Zauber der Schule Verzauberung: Zwang und zauberähnliche Fähigkeiten dieser Art. Verbündete, die sich "
        "innerhalb von 3 m um den Paladin befinden, erhalten einen Rettungswurfbonus von +4 gegen entsprechende "
        "Effekte und Zauber.\n\n"
        "Diese Fähigkeit funktioniert nur, solange der Paladin bei Bewusstsein ist, nicht wenn er tot oder "
        "bewusstlos ist.",
        {},
    ),
    (
        "Heiliger Streiter",
        [20],
        "(ÜF) Mit dem Erreichen der 20. Stufe wird der Paladin ein Gefäß für die Macht seiner Gottheit. Seine "
        "Schadensreduzierung steigt auf 10/Böses. Wenn er Böses niederstrecken gegen einen bösen Externar "
        "anwendet, wird dieser im Falle eines Treffers zu dem Ziel des Zaubers Verbannung (die Waffe und das "
        "heilige Symbol des Paladins zählen als Objekte, die die Kreatur hasst). Die Paladinstufe wirkt für diesen "
        "Effekt als Zauberstufe. Nachdem der Effekt der Verbannung und der Schaden aus dem Angriff das Ziel "
        "getroffen haben, endet das Niederstrecken sofort. Immer wenn der Paladin außerdem seine positive Energie "
        "fokussiert, erzielt er das höchst mögliche Ergebnis beim zu heilenden Schaden.",
        {},
    ),
    (
        "Verhaltenskodex",
        [1],
        "Ein Paladin muss von rechtschaffen guter Gesinnung sein und verliert alle Fähigkeiten, außer Waffen- und "
        "Rüstungsfähigkeiten, sollte er jemals willentlich eine böse Tat begehen.\n\n"
        "Außerdem muss ein Paladin legitime Autoritäten akzeptieren, sich ehrenvoll verhalten (nicht lügen, "
        "betrügen, Gift verwenden und so weiter), jenen in Not helfen (solange diese die Hilfe nicht für böse oder "
        "chaotische Zwecke nutzen) und diejenigen bestrafen, die Unschuldige bedrohen oder angreifen.\n\n"
        "Gefährten: Während er ohne weiteres mit jedem gut oder neutral gesonnenen Abenteurer reisen kann, "
        "vermeidet er es, mit bösen Kreaturen zusammen zu arbeiten und mit jemandem zu kooperieren, der seine "
        "moralischen Werte fortwährend verletzt. Unter außergewöhnlichen Umständen kann der Paladin sich mit einer "
        "bösen Kreatur verbünden, aber nur wenn es darum geht, etwas aus der Welt zu schaffen, was er als ein "
        "größeres Übel ansieht. Ein Paladin sollte während einer solch ungewöhnlichen Allianz regelmäßig Buße tun, "
        "und sollte die Zusammenarbeit sofort beenden, wenn er der Meinung ist, dass diese Allianz mehr schadet, "
        "als dass sie Gutes bringt. Ein Paladin nimmt nur rechtschaffen gute Anhänger und Mietlinge in seinen "
        "Dienst.",
        {},
    ),
    (
        "Ehemaliger Paladin",
        [1],
        "Ein Paladin, der seine Gesinnung ändert, eine böse Tat vollführt oder gegen seinen Verhaltenskodex "
        "verstößt, verliert alle Paladinzauber und -fähigkeiten (außer den Umgang mit Waffen und Rüstungen). Er "
        "kann dann auch nicht weiter als Paladin aufsteigen. Erst wenn er angemessen Buße getan hat (siehe den "
        "Zauber Buße), kann er seine Fähigkeiten und Aufstiegsmöglichkeiten wiedererlangen.",
        {},
    ),
]

MERCY_GROUP = {"key": "mercy", "label": "Gnade", "max_choices": 6, "is_secondary_class_initial_pick": False}
DIVINE_BOND_GROUP = {
    "key": "divine_bond",
    "label": "Göttlicher Bund",
    "max_choices": 1,
    "is_secondary_class_initial_pick": False,
}

# (choice name, min level, prerequisite choice name, effect text)
MERCIES: list[tuple[str, int, str | None, str]] = [
    ("Erschöpft", 3, None, "Das Ziel ist nicht mehr erschöpft."),
    ("Erschüttert", 3, None, "Das Ziel ist nicht mehr erschüttert."),
    ("Kränkelnd", 3, None, "Das Ziel ist nicht mehr kränkelnd."),
    ("Benommen", 6, None, "Das Ziel ist nicht mehr benommen."),
    (
        "Krank",
        6,
        None,
        "Das Handauflegen des Paladins arbeitet auch wie Krankheit kurieren, wobei die Paladinstufe als "
        "Zauberstufe eingesetzt wird.",
    ),
    ("Wankend", 6, None, "Das Ziel ist nicht mehr wankend, außer es hat genau 0 Trefferpunkte."),
    (
        "Entkräftet",
        9,
        "Erschöpft",
        "Das Ziel ist nicht mehr entkräftet. Der Paladin muss die Gnade Erschöpft gewählt haben, bevor er diese "
        "Gnade auswählen kann.",
    ),
    (
        "Übelkeit",
        9,
        "Kränkelnd",
        "Das Ziel ist nicht mehr von Übelkeit geplagt. Der Paladin muss die Gnade Kränkelnd gewählt haben, bevor "
        "er diese Gnade auswählen kann.",
    ),
    (
        "Verängstigt",
        9,
        "Erschüttert",
        "Das Ziel ist nicht mehr verängstigt. Der Paladin muss die Gnade Erschüttert gewählt haben, bevor er "
        "diese Gnade auswählen kann.",
    ),
    (
        "Verflucht",
        9,
        None,
        "Das Handauflegen des Paladins arbeitet auch wie Fluch brechen, wobei die Paladinstufe als Zauberstufe "
        "eingesetzt wird.",
    ),
    (
        "Vergiftet",
        9,
        None,
        "Das Handauflegen des Paladins arbeitet auch wie Gift neutralisieren, wobei die Paladinstufe als "
        "Zauberstufe eingesetzt wird.",
    ),
    ("Betäubt", 12, None, "Das Ziel ist nicht mehr betäubt."),
    ("Blind", 12, None, "Das Ziel ist nicht mehr blind."),
    ("Gelähmt", 12, None, "Das Ziel ist nicht mehr gelähmt."),
    ("Taub", 12, None, "Das Ziel ist nicht mehr taub."),
]

# (choice name, [(ability name, description, extra columns)])
DIVINE_BONDS: list[tuple[str, list[tuple[str, str, dict]]]] = [
    (
        "Waffe",
        [("Göttlicher Bund: Waffe", BUND_WAFFE_DESC, {"is_persistent_effect": True, "activation_scope": "self"})],
    ),
    (
        "Reittier",
        [
            ("Göttlicher Bund: Reittier", BUND_REITTIER_DESC, {}),
            ("Reittier herbeirufen", REITTIER_HERBEIRUFEN_DESC, {}),
        ],
    ),
]

SCHOOL_PREFIX_RE = re.compile(r"[\(\[]")
SCHOOL_ALIASES = {"Erkenntniszauber": "Erkenntnis"}


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def load(filename: str, directory: Path = SEED_DIR) -> list[dict]:
    return json.loads((directory / filename).read_text(encoding="utf-8"))


def save(filename: str, rows: list[dict], directory: Path = SEED_DIR) -> None:
    deduped: dict[str, dict] = {}
    for row in rows:
        deduped[row["id"]] = row
    (directory / filename).write_text(
        json.dumps(list(deduped.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def primary_school(school_text: str | None) -> str:
    """Same as `build_spells_seed.py`'s own helper."""
    if not school_text:
        return ""
    name = SCHOOL_PREFIX_RE.split(school_text)[0].strip()
    return SCHOOL_ALIASES.get(name, name)


def main() -> None:
    class_id = PALADIN_ID

    # ---- base_classes.json / classes.json ----
    base_classes = load("base_classes.json")
    for row in base_classes:
        if row["id"] == PALADIN_ID:
            row.update(casting_ability="CH", spell_tradition="divine", allowed_alignments=PALADIN_ALIGNMENTS)
        elif row["id"] == DRUIDE_ID:
            row["allowed_alignments"] = DRUIDE_ALIGNMENTS
    save("base_classes.json", base_classes)

    class_defs = json.loads((FIXTURES / "classes.json").read_text(encoding="utf-8"))
    for class_def in class_defs:
        if class_def["name"] == "Paladin":
            class_def["spellType"] = "divine-prepared"
    (FIXTURES / "classes.json").write_text(json.dumps(class_defs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---- base_class_skills.json ----
    skills = load("base_skills.json")
    skill_id_by_name = {row["name"]: row["id"] for row in skills}
    skill_name_by_id = {row["id"]: row["name"] for row in skills}
    for name in CORRECT_CLASS_SKILLS:
        assert name in skill_id_by_name, f"missing skill: {name}"

    class_skills = load("base_class_skills.json")
    existing_row_id_by_skill_name = {
        skill_name_by_id[row["skill_id"]]: row["id"]
        for row in class_skills
        if row["base_class_id"] == class_id and row.get("option_choice_id") is None and row["skill_id"] in skill_name_by_id
    }
    class_skills = [
        row for row in class_skills if not (row["base_class_id"] == class_id and row.get("option_choice_id") is None)
    ]
    for name in CORRECT_CLASS_SKILLS:
        class_skills.append(
            {
                "id": existing_row_id_by_skill_name.get(name) or uid("paladin-classskill", name),
                "base_class_id": class_id,
                "skill_id": skill_id_by_name[name],
                "option_choice_id": None,
            }
        )
    save("base_class_skills.json", class_skills)

    # ---- base_class_option_groups.json / base_class_option_choices.json ----
    groups = load("base_class_option_groups.json")
    mercy_group_id = uid("paladin-group", MERCY_GROUP["key"])
    bond_group_id = uid("paladin-group", DIVINE_BOND_GROUP["key"])
    groups.append({"id": mercy_group_id, "base_class_id": class_id, **MERCY_GROUP})
    groups.append({"id": bond_group_id, "base_class_id": class_id, **DIVINE_BOND_GROUP})
    save("base_class_option_groups.json", groups)

    choices = load("base_class_option_choices.json")
    mercy_choice_ids = {name: uid("paladin-mercy", name) for name, _level, _req, _text in MERCIES}
    for name, min_level, requires, _text in MERCIES:
        choices.append(
            {
                "id": mercy_choice_ids[name],
                "group_id": mercy_group_id,
                "name": name,
                "min_level": min_level,
                "requires_choice_id": mercy_choice_ids[requires] if requires else None,
                "race_id": None,
            }
        )
    bond_choice_ids = {name: uid("paladin-divine-bond", name) for name, _abilities in DIVINE_BONDS}
    for name, _abilities in DIVINE_BONDS:
        choices.append(
            {
                "id": bond_choice_ids[name],
                "group_id": bond_group_id,
                "name": name,
                "min_level": None,
                "requires_choice_id": None,
                "race_id": None,
            }
        )
    save("base_class_option_choices.json", choices)

    # ---- base_class_abilities.json + base_class_ability_grants.json ----
    abilities = load("base_class_abilities.json")
    abilities_by_id = {a["id"]: a for a in abilities}
    grants = load("base_class_ability_grants.json")

    def add_ability(name: str, description: str, extra: dict) -> str:
        aid = uid("paladin-ability", name)
        row = {"id": aid, "name": name, "description": description, **extra}
        if aid in abilities_by_id:
            abilities_by_id[aid].update(row)
        else:
            abilities.append(row)
            abilities_by_id[aid] = row
        return aid

    def add_grant(ability_id: str, level: int, option_choice_id: str | None = None) -> None:
        grants.append(
            {
                "id": uid("paladin-grant", ability_id, str(level), option_choice_id or ""),
                "base_class_id": class_id,
                "ability_id": ability_id,
                "option_choice_id": option_choice_id,
                "level": level,
            }
        )

    ability_id_by_name: dict[str, str] = {}
    for name, levels, description, extra in CLASS_FEATURES:
        aid = add_ability(name, description, extra)
        ability_id_by_name[name] = aid
        for level in levels:
            add_grant(aid, level)

    # A mercy's grant level is its own tier's level (3/6/9/12), so the sheet
    # never lists it before the Paladin could have picked it.
    for name, min_level, _requires, text in MERCIES:
        aid = add_ability(f"Gnade: {name}", f"(ÜF) {text}", {})
        ability_id_by_name[f"Gnade: {name}"] = aid
        add_grant(aid, min_level, mercy_choice_ids[name])

    for choice_name, choice_abilities in DIVINE_BONDS:
        for name, description, extra in choice_abilities:
            aid = add_ability(name, description, extra)
            ability_id_by_name[name] = aid
            add_grant(aid, 5, bond_choice_ids[choice_name])

    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)

    # ---- base_class_ability_granted_feats.json ----
    feat_id_by_name = {row["name"]: row["id"] for row in load("base_feats.json")}
    proficiency_ability_id = ability_id_by_name["Umgang mit Waffen und Rüstungen"]
    granted_feats = load("base_class_ability_granted_feats.json")
    for feat_name in PROFICIENCY_FEATS:
        feat_id = feat_id_by_name[feat_name]
        granted_feats.append(
            {
                "id": uid("paladin-grantedfeat", proficiency_ability_id, feat_id),
                "ability_id": proficiency_ability_id,
                "feat_id": feat_id,
            }
        )
    save("base_class_ability_granted_feats.json", granted_feats)

    # ---- base_spells.json + base_class_spells.json ----
    # Same id-then-name match as `import_kampfmagus.py` (a reconciled legacy
    # spell keeps its old hand-seeded id); a spell with neither gets a new
    # row built from its PRD detail page, under the PRD import's own id.
    spell_import = load("zauber_prd_import.json", IMPORTED_DIR)
    details_by_id = {d["id"]: d for d in load("zauber_prd_details.json", IMPORTED_DIR)}
    spells = load("base_spells.json")
    spell_ids = {s["id"] for s in spells}
    spell_id_by_name = {s["name"]: s["id"] for s in spells}
    class_spells = [r for r in load("base_class_spells.json") if r["base_class_id"] != class_id]
    added_spells: list[str] = []
    missing_details: list[str] = []
    seen: set[str] = set()
    for entry in spell_import:
        grade = entry.get("grades_by_class", {}).get("Paladin")
        if grade is None or entry["id"] in seen:
            continue
        seen.add(entry["id"])
        spell_id = entry["id"] if entry["id"] in spell_ids else spell_id_by_name.get(entry["name"])
        if spell_id is None:
            detail = details_by_id.get(entry["id"])
            if detail is None:
                missing_details.append(entry["name"])
                continue
            spell_id = entry["id"]
            spells.append(
                {
                    "id": spell_id,
                    "name": detail["name"],
                    "school": primary_school(detail.get("school_text") or entry.get("school")),
                    "description": detail["full_description"],
                    "casting_time": detail.get("casting_time"),
                    "range": detail.get("range"),
                    "target_or_area": detail.get("target_or_area"),
                    "duration": detail.get("duration"),
                    "saving_throw": detail.get("saving_throw"),
                    "spell_resistance": detail.get("spell_resistance"),
                }
            )
            spell_ids.add(spell_id)
            spell_id_by_name[detail["name"]] = spell_id
            added_spells.append(detail["name"])
        class_spells.append(
            {"id": uid("paladin-spell", spell_id), "base_class_id": class_id, "spell_id": spell_id, "grade": grade}
        )
    spells.sort(key=lambda s: s["name"])
    save("base_spells.json", spells)
    save("base_class_spells.json", class_spells)

    print("Class skills:", len(CORRECT_CLASS_SKILLS))
    print("Class features:", len(CLASS_FEATURES), "+", len(MERCIES), "mercies +", "divine bond abilities")
    print("Paladin spells:", len([r for r in class_spells if r["base_class_id"] == class_id]))
    print("New base_spells rows:", len(added_spells))
    if missing_details:
        print("Skipped (no PRD detail page):", missing_details)
    for name in (
        "Böses niederstrecken",
        "Göttliche Würde",
        "Handauflegen",
        "Positive Energie fokussieren",
        "Aura der Gerechtigkeit",
        "Göttlicher Bund: Waffe",
        "Göttlicher Bund: Reittier",
        "Reittier herbeirufen",
    ):
        print(f"{name}: {ability_id_by_name[name]}")
    print("Done.")


if __name__ == "__main__":
    main()
