"""Import the Kampfmagus (Magus) base class from
http://prd.5footstep.de/AusbauregelnMagie/Kampfmagus into the seed JSON
files: a brand-new root `BaseClass` row (this app had no Magus at all
before this script — no placeholder id, no `classes.json` entry), its class
skills, its "Zauber pro Tag" grade-access table, its 17 named class features
(everything except the Arkanum slot and the Bonustalent slot, each handled
separately below), the Arkanum slot ability plus a `BaseClassOptionGroup`
covering all 39 Arkana this app now knows about (20 from this page, plus 19
more from `import_kampfmagus_archetypes.py`'s companion page — merged into
one script since both need the same `KAMPFMAGUS_ID`/grant machinery and the
archetypes page's own Arkana are just as much "core Kampfmagus options" as
this page's, not archetype-exclusive), and the Bonustalent slot.

`hit_dice`/`bab_progression`/`fort_save`/`ref_save`/`wil_save`/
`skill_points_base` read off "Tabelle: Kampfmagus": W8, 3/4 BAB (matches the
GAB column exactly: +0/+1/+2/+3/+3/+4/+5/+6/+6/+7/+8/+9/+9/+10/+11/+12/+12/
+13/+14/+15 — the same progression Kleriker/Waldläufer use), good Fort
(matches the ZÄH column, 2+level/2) and Will (matches WIL, same formula),
poor Reflex (matches REF, level/3). Skill points: "2 + IN-Modifikator".

**Arkanum modeled the same shape as Schurke's `trick` group / Waldläufer's
`Kampfstiltalent`** (`rules/class_options.py`'s `group_occurrence_levels`
convention): one `BaseClassAbility` named exactly "Arkanum" (matching the
`BaseClassOptionGroup.label`) with unconditional (`option_choice_id=None`)
grants at 3rd/6th/9th/12th/15th/18th — those six grant levels *are* the
group's occurrence levels, derived generically, not hardcoded anywhere else.
Each individual Arkanum is then its own `BaseClassAbility` + a single
`option_choice_id`-scoped grant at `level=1` (a placeholder level, not tied
to any specific occurrence — same shape verified against Schurke's existing
Trick rows before writing this). `BaseClassOptionChoice.min_level` carries
each Arkanum's own level prerequisite (e.g. Bannender Schlag needs 9th)
independently of which of the six occurrence slots fills it, same as
Mystiker's Offenbarung tier gating. Two pairs of Arkana that require another
specific Arkanum first (Mächtiges Arkanes Bollwerk -> Arkanes Bollwerk;
Anhaftender/Donnernder/Überschlagender Vorratsschlag -> Vorratsschlag) use
`requires_choice_id`, the same cross-choice-in-one-group mechanism Mystiker's
Sternenmantel -> Firmament dependency already established.

Deliberately NOT modeled, same "real boundary, not a time question"
precedent every other class-import script documents:
- No `BaseClassSpell` rows *from hand-parsing this page's own "Zauberliste
  des Kampfmagus" prose* — every sibling class import (Barde/Kleriker/
  Mystiker) explicitly left this to a separate, larger effort. Unlike those,
  though, Kampfmagus's spell list turns out to already be sitting in
  `app/fixtures/imported/zauber_prd_import.json` (the PRD's own per-class
  bulk spell index, fetched once for `build_spells_seed.py` and including a
  `"Kampfmagus"` key in `grades_by_class` for every spell that page lists)
  — `build_spells_seed.py`'s own docstring says as much: "235 [spells] have
  grades only for classes with no spell_tradition yet (..., Kampfmagus, ...)
  and are dropped." Now that Kampfmagus has a `spell_tradition`, this
  script's `main()` backfills `base_class_spells.json` straight from that
  already-fetched import data (311 spells tagged `Kampfmagus`, 280 of which
  already have a `base_spells.json` row from the classes that already
  existed when `build_spells_seed.py` ran) instead of hand-transcribing the
  prose spell list — no re-fetch needed, no new spell rows invented. The 31
  Kampfmagus-only spells that got dropped by that earlier run (e.g.
  "Ablenkung", "Dimensionstür", the three Elementargestalt tiers, several
  Ausbauregeln: Magie-only spells) stay unseeded, same class of gap as
  Kleriker's/Mystiker's own deferred spell lists — a `build_spells_seed.py`
  rerun/extension, not this script's job.
- No `BaseClassAbilitySpellOption`/repeat-selection enforcement for
  Meisterliche Manöver or Zauberforschung (both explicitly repeatable per
  their own text) - same "nothing models 'may be picked more than once' yet"
  gap `import_entfesselter_barbar.py`'s docstring already flags for its own
  repeatable rage powers.
- No handler-side computation anywhere (Arkaner Vorrat's point pool,
  Kampfzauberei's attack-penalty math, Zauberschlag's touch-attack
  substitution, every Arkanum's actual mechanical effect) - composition
  only, per CLAUDE.md. Catalog row + description text, same depth as every
  other class import.
- "Zauber"/"Zauberbücher" (the general prepared-arcane-caster/spellbook
  rules paragraphs) aren't their own `BaseClassAbility` rows, same as
  Magier's own "Zauber"/"Zauberbücher" paragraphs never were - this app's
  arcane-prepared spellcasting model (`classes.json` `spellType`) already
  covers the mechanic; these paragraphs are prose about it, not a discrete
  leveled feature.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database - run the normal seed scripts afterward):
    cd backend && python scripts/import_kampfmagus.py
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
IMPORTED = FIXTURES / "imported"

ID_NAMESPACE = uuid.UUID("7a2c9e10-4b6d-4f8a-9c1e-3d5f7a9b1c2d")

KAMPFMAGUS_ID = str(uuid.uuid5(ID_NAMESPACE, "kampfmagus-class"))
ARKANUM_GROUP_ID = str(uuid.uuid5(ID_NAMESPACE, "kampfmagus-arkanum-group"))

# Klassenfertigkeiten (skill name -> base_skills.json id, from base_skills.json).
CLASS_SKILL_IDS = {
    "Beruf": "7cf08043-8422-400c-88de-960f094fe9e6",
    "Einschüchtern": "3c60b6e1-8c58-4ed0-9c3a-5e003b9da1cf",
    "Fliegen": "a71cd8ed-15b2-4594-9819-0e320071513c",
    "Handwerk": "f5624a2e-59b2-400b-84e6-a0310daba26b",
    "Klettern": "bf8d0e63-8a96-4a0e-baf9-06a1cac4e4c7",
    "Magischen Gegenstand benutzen": "7446d67a-7bc2-4455-877b-591500769be2",
    "Reiten": "ea28d7f8-2b92-42aa-93c9-89dd78987f09",
    "Schwimmen": "e5fa3283-96aa-49ee-8836-ba3062bae32d",
    "Wissen (Arkanes)": "0aa605c7-5afe-47cb-99df-ad187775333f",
    "Wissen (Die Ebenen)": "80b9c08a-4cef-40d1-b446-caefccbff302",
    "Wissen (Gewölbekunde)": "960179c4-5aed-4352-8b84-bd78a8c3a10e",
    "Zauberkunde": "8532ffd7-4849-4b27-b10b-1fd0c84b7ebe",
}

# Umgang mit Waffen und Rüstungen -> granted feats (base_feats.json ids).
SIMPLE_WEAPONS_FEAT_ID = "9d19039e-78b7-50ea-ab5c-ea65b81b8a06"
MARTIAL_WEAPONS_FEAT_ID = "1bf92ea9-226c-5975-bad1-d91e46aefdd3"
LIGHT_ARMOR_FEAT_ID = "12ff29e6-13a9-52d5-899d-1e72be8ffbf6"
MEDIUM_ARMOR_FEAT_ID = "f8d17fa6-e2a0-59b1-9c2b-d7352be3202a"
HEAVY_ARMOR_FEAT_ID = "38cd3d30-27d8-5cdc-a571-da1c2241ea7a"

# Zauberbrecher/Zauberstörer arcana each grant the matching bonus feat.
ZAUBERBRECHER_FEAT_ID = "d77f3862-3e24-5ad4-bc3d-2a5cec4486bd"
ZAUBERSTOERER_FEAT_ID = "ccdbfe93-9d86-5d79-b90c-f2862440b50f"

# "Tabelle: Kampfmagus", Zauber pro Tag columns (grade -> first level it's
# accessible at); grade 0/1 from 1st, then one more grade every 3 levels.
GRADE_FIRST_LEVEL = {0: 1, 1: 1, 2: 4, 3: 7, 4: 10, 5: 13, 6: 16}

# (name, levels, description, granted_feat_ids)
CORE_FEATURES: list[tuple[str, list[int], str, list[str]]] = [
    (
        "Umgang mit Waffen und Rüstungen",
        [1],
        "Der Kampfmagus ist im Umgang mit allen einfachen Waffen und Kriegswaffen geübt. Er ist "
        "außerdem im Tragen leichter Rüstung geübt. Er kann Kampfmaguszauber wirken, während er eine "
        "leichte Rüstung trägt, ohne dabei einen arkanen Patzer zu riskieren. Wie andere arkane "
        "Zauberkundige riskiert er einen arkanen Patzer, wenn er mittelschwere oder schwere Rüstung "
        "oder einen Schild trägt und der Zauber Gestik als Komponente besitzt. Ein Kampfmagus, der "
        "Stufen in mehreren Klassen besitzt, besitzt bei arkanen Zaubern anderer Klassen die übliche "
        "Chance eines arkanen Patzers.",
        [SIMPLE_WEAPONS_FEAT_ID, MARTIAL_WEAPONS_FEAT_ID, LIGHT_ARMOR_FEAT_ID],
    ),
    (
        "Arkaner Vorrat",
        [1],
        "(ÜF) Auf der 1. Stufe erhält der Kampfmagus einen Vorrat mystischer arkaner Energie, auf den "
        "er zurückgreifen kann, um seine Kräfte zu verstärken und seine Waffe zu verbessern. In diesem "
        "Vorrat befindet sich eine Anzahl an Punkten in Höhe seiner halben Stufe als Kampfmagus "
        "(Minimum 1) + seines IN-Modifikators. Der Vorrat erneuert sich ein Mal am Tag, wenn der "
        "Kampfmagus seine Zauber vorbereitet.\n\n"
        "Auf der 1. Stufe kann ein Kampfmagus 1 Punkt seines Vorrats aufwenden, um mit einer Schnellen "
        "Aktion einer von ihm gehaltenen Waffe für eine Minute einen Verbesserungsbonus von +1 zu "
        "verleihen. Für jeweils 4 weitere Stufen (ab der 5., 9. ...) erhält die Waffe einen weiteren "
        "Verbesserungsbonus von +1 bis zu einem Maximum von +5 auf der 17. Stufe. Diese Boni können auch "
        "zu Waffen hinzuaddiert werden, die bereits über einen Bonus verfügen, der Maximalbonus beträgt "
        "aber auch hier +5. Mehrere Anwendungen dieser Fähigkeit auf dieselbe Waffe während desselben "
        "Zeitraumes addieren sich nicht auf.\n\n"
        "Auf der 5. Stufe können diese Boni genutzt werden, um die folgenden Waffeneigenschaften zu "
        "verleihen: Aufflammen, Blitz, Blitzinferno, Eis, Eisinferno, Flammeninferno, Hinrichtung, "
        "Schärfe, Schnelligkeit oder Tanzen. Jede Eigenschaft verbraucht dabei einen Teil des Bonus "
        "entsprechend des Modifikators für den Grundpreis. Diese Eigenschaften können Waffen "
        "hinzugefügt werden, die bereits über besondere Eigenschaften verfügen, auf diese Weise doppelt "
        "vorhandene Fähigkeiten addieren sich aber nicht. Sollte es sich um eine nichtmagische Waffe "
        "handeln, muss sie zuerst mit einem Verbesserungsbonus von mindestens +1 versehen werden, ehe "
        "sie besondere Eigenschaften erhalten kann. Die Boni funktionieren nicht, wenn jemand anderes "
        "die Waffe führt. Ein Kampfmagus kann immer nur eine Waffe gleichzeitig verbessern.",
        [],
    ),
    (
        "Zaubertricks",
        [1],
        "Ein Kampfmagus kann eine Anzahl von Zaubertricks (Zaubern des Grades 0) jeden Tag vorbereiten, "
        "wie in Tabelle: Kampfmagus unter Zauber pro Tag aufgeführt. Diese Zauber werden wie andere "
        "Zauber gewirkt, aber dabei nicht verbraucht, sondern können beliebig oft am Tag eingesetzt "
        "werden.",
        [],
    ),
    (
        "Kampfzauberei",
        [1],
        "(AF) Auf der 1. Stufe erlernt ein Kampfmagus, zugleich Zauber zu wirken und seine Waffe zu "
        "führen. Dies funktioniert wie Kampf mit zwei Waffen, nur dass die Waffe in der Sekundärhand "
        "der gewirkte Zauber ist. Um diese Fähigkeit einzusetzen, muss der Kampfmagus mindestens eine "
        "Hand frei haben, während er eine leichte oder einhändige Kriegswaffe in der anderen führt. Mit "
        "einer Vollen Aktion kann er alle Angriffe mit der Nahkampfwaffe mit einem Malus von -2 "
        "ausführen und zugleich jeden Zauber von der Zauberliste des Kampfmagus wirken, der einen "
        "Zeitaufwand von einer Standard-Aktion besitzt. Jeder Angriffswurf, der als Teil des Zaubers "
        "gemacht wird, unterliegt ebenfalls diesem Malus. Sollte der Kampfmagus defensiv zaubern, kann "
        "er sich entscheiden, seine Angriffswürfe einem zusätzlichen Malus bis in Höhe seines "
        "IN-Modifikators zu unterwerfen, und diesen Wert als Situationsbonus seinem Konzentrationswurf "
        "hinzuzufügen. Ein Kampfmagus kann sich entscheiden, ob er zuerst zaubern oder zuerst mit "
        "seiner Waffe angreifen will. Sollte er über mehrere Angriffe verfügen, kann er nicht zwischen "
        "seinen Angriffen zaubern.",
        [],
    ),
    (
        "Zauberschlag",
        [2],
        "(ÜF) Auf der 2. Stufe kann ein Kampfmagus jeden Kampfmaguszauber mit der Reichweite Berührung "
        "als Teil eines Nahkampfangriffes mit seiner Waffe übertragen. Anstelle des freien "
        "Berührungsangriffes im Nahkampf, mit dem der Zauber normalerweise übertragen wird, kann er "
        "beim Wirken des Zaubers einen zusätzlichen Nahkampfangriff mit seiner Waffe mit seinem "
        "höchsten Grundangriffsbonus ausführen. Bei einem erfolgreichen Angriff verursacht er neben dem "
        "normalen Waffenschaden zusätzlich die Effekte des Zaubers. Sollte der Kampfmagus diesen "
        "Angriff im Rahmen seiner Fähigkeit Kampfzauberei ausführen, unterliegt der Nahkampfangriff "
        "allen Abzügen der Kampfzauberei. Dieser Angriff nutzt den kritischen Bedrohungsbereich der "
        "Waffe, aber der Zauber selbst hat bei einem erfolgreichen kritischen Treffer nur einen "
        "Schadensmodifikator von x2, während die Waffe ihren eigenen Modifikator für kritischen Schaden "
        "verwendet.",
        [],
    ),
    (
        "Zauberrückruf",
        [4],
        "(ÜF) Auf der 4. Stufe erlernt der Kampfmagus, unter Zuhilfenahme seines Arkanen Vorrats sich "
        "an Zauber zu erinnern, die er bereits gewirkt hat. Mit einer Schnellen Aktion kann er sich "
        "einen einzelnen Kampfmaguszauber ins Gedächtnis zurückrufen, den er an diesem Tag bereits "
        "vorbereitet und gewirkt hat. Hierbei muss er Punkte aus seinem Arkanen Vorrat in Höhe des "
        "Zaubergrades (Minimum 1 Punkt) aufwenden. Der Zauber gilt erneut als vorbereitet, als wäre er "
        "nicht gewirkt worden.",
        [],
    ),
    (
        "Wissensvorrat",
        [7],
        "(ÜF) Auf der 7. Stufe kann ein Kampfmagus beim Vorbereiten seiner Kampfmaguszauber einen oder "
        "mehrere Punkte seines Arkanen Vorrats nutzen, um pro Punkt einen Zauber von der Zauberliste "
        "des Kampfmagus vorzubereiten, der sich nicht in seinem Zauberbuch befindet. Das Maximum an "
        "Punkten, die er aufwenden kann, entspricht seinem IN-Modifikator. Diese Zauber sind keine "
        "zusätzlichen Zauber, sondern unterliegen der Beschränkung von maximalen Zaubern pro Tag. "
        "Sollte er diese Zauber nicht benutzen, bis er das nächste Mal seine Zauber vorbereitet, "
        "verliert er sie wieder.",
        [],
    ),
    (
        "Mittelschwere Rüstung",
        [7],
        "(AF) Auf der 7. Stufe erlernt ein Kampfmagus Umgang mit mittelschwerer Rüstung. Ein Kampfmagus "
        "kann Kampfmaguszauber in mittelschwerer Rüstung wirken, ohne einen arkanen Patzer zu "
        "riskieren. Wie andere arkane Zauberkundige auch, riskiert er immer noch einen arkanen Patzer, "
        "wenn er schwere Rüstung und/oder einen Schild trägt und der Zauber Gesten als Komponente "
        "besitzt.",
        [MEDIUM_ARMOR_FEAT_ID],
    ),
    (
        "Verbesserte Kampfzauberei",
        [8],
        "(AF) Auf der 8. Stufe verbessert sich die Fähigkeit des Kampfmagus, Zauber zu wirken und im "
        "Nahkampf anzugreifen. Wenn der Kampfmagus Kampfzauberei benutzt, erhält er einen Bonus von +2 "
        "auf seine Konzentrationswürfe, zusätzlich zu dem Bonus, den er eventuell erhält, indem er sich "
        "selbst einen Malus auf seinen Angriffswurf auferlegt.",
        [],
    ),
    (
        "Kämpferausbildung",
        [10],
        "(AF) Ab der 10. Stufe gilt die halbe Stufe des Kampfmagus als seine effektive Stufe als "
        "Kämpfer hinsichtlich der Voraussetzungen von Talenten. Sollte er Stufen als Kämpfer besitzen, "
        "addieren sich die Stufen entsprechend.",
        [],
    ),
    (
        "Verbesserter Zauberrückruf",
        [11],
        "(ÜF) Auf der 11. Stufe wird die Fähigkeit des Kampfmagus, sich an bereits gewirkte Zauber zu "
        "erinnern, effizienter. Wenn er sich einen Zauber ins Gedächtnis zurückruft, muss er nur noch "
        "Punkte seines Arkanen Vorrats in Höhe des halben Zaubergrades (Minimum 1) aufwenden. Ferner "
        "kann er mit einer Schnellen Aktion einen Zauber desselben Grades aus seinem Zauberbuch "
        "vorbereiten, statt sich einen gewirkten Zauber ins Gedächtnis zurückzurufen; hierzu muss er "
        "Punkte aus seinem Arkanen Vorrat in Höhe des Zaubergrades (Minimum 1) aufwenden. Auf derart "
        "vorbereitete Zauber können keine metamagischen Talente angewendet werden. Der Kampfmagus muss "
        "nicht sein Zauberbuch zur Hand haben, um einen Zauber auf diese Weise vorbereiten zu können.",
        [],
    ),
    (
        "Schwere Rüstung",
        [13],
        "(AF) Auf der 13. Stufe erhält ein Kampfmagus das Talent Umgang mit Schwerer Rüstung. Ein "
        "Kampfmagus kann Kampfmaguszauber in schwerer Rüstung wirken, ohne einen arkanen Patzer zu "
        "riskieren. Wie andere arkane Zauberkundige riskiert er immer noch einen arkanen Patzer, wenn "
        "er einen Schild trägt und der Zauber Gesten als Komponente besitzt.",
        [HEAVY_ARMOR_FEAT_ID],
    ),
    (
        "Mächtige Kampfzauberei",
        [14],
        "(AF) Auf der 14. Stufe gewinnt der Kampfmagus die Fähigkeit, Zauber und Nahkampfangriffe "
        "nahtlos auszuführen. Wenn er das Klassenmerkmal Kampfzauberei einsetzt, entspricht sein Bonus "
        "auf Konzentrationswürfe dem doppelten des Malus der Angriffswürfe, den er sich selbst "
        "auferlegt hat.",
        [],
    ),
    (
        "Gegenschlag",
        [16],
        "(AF) Auf der 16. Stufe provoziert jeder Gegner, der innerhalb der Reichweite des Kampfmagus "
        "defensiv zaubert, einen Gelegenheitsangriff durch den Kampfmagus nach Beendigung des Zaubers. "
        "Dieser Gelegenheitsangriff kann den Zauber nicht unterbrechen.",
        [],
    ),
    (
        "Mächtiger Zugang zu Zaubern",
        [19],
        "(ÜF) Auf der 19. Stufe erhält der Kampfmagus Zugang zu einer erweiterten Zauberliste. Er "
        "erlernt 14 Zauber von der Zauberliste für Magier und schreibt diese als Kampfmaguszauber "
        "gleichen Grades in sein Zauberbuch (zwei Zauber jeden Grades, Grad 0 und der Grade 1-6). Er "
        "kann die Gesten-Komponenten dieser Zauber ignorieren und sie wirken, ohne die Gefahr eines "
        "arkanen Zauberpatzers zu riskieren.",
        [],
    ),
    (
        "Wahrer Kampfmagus",
        [20],
        "(ÜF) Auf der 20. Stufe wird der Kampfmagus zum Meister des Kampfes und der Zauberei. Wenn er "
        "seine Fähigkeit Kampfzauberei nutzt, ist kein Konzentrationswurf mehr erforderlich, um einen "
        "Zauber defensiv zu wirken. Wenn der Kampfmagus Kampfzauberei nutzt und dieselbe Kreatur das "
        "Ziel seines Zaubers und seiner Nahkampfangriffe ist, kann er auswählen, entweder den SG des "
        "Rettungswurfes gegen seinen Zauber um +2 zu erhöhen, sich selbst einen Situationsbonus von +2 "
        "auf alle Würfe zum Überwinden von Zauberresistenz zu verleihen oder sich selbst einen "
        "Situationsbonus von +2 auf alle Angriffswürfe gegen das Ziel während seines Zuges zu "
        "verleihen.",
        [],
    ),
]

ARKANUM_SLOT_DESCRIPTION = (
    "Während ein Kampfmagus in seiner Klasse aufsteigt und Stufen hinzu gewinnt, erlernt er "
    "geheimnisvolle Arkana. Ein Kampfmagus erhält auf der 3. Stufe ein Arkanum und dann mit jeder "
    "weiteren dritten Klassenstufe als Kampfmagus (6., 9., 12., 15., 18.). Sofern es nicht anders "
    "beschrieben wird, kann ein Kampfmagus ein Arkanum nicht mehr als ein Mal wählen. Arkana, die sich "
    "auf Zauber auswirken, können nur Zauber von der Zauberliste des Kampfmagus modifizieren, außer die "
    "Beschreibung sagt etwas anderes aus."
)
ARKANUM_LEVELS = [3, 6, 9, 12, 15, 18]

BONUSTALENT_DESCRIPTION = (
    "Auf der 5. Stufe und dann alle weiteren sechs Stufen als Kampfmagus (11., 17.) erhält ein "
    "Kampfmagus 1 Bonustalent. Dabei muss es sich um ein Talent aus der Kategorie Kampf, Metamagie oder "
    "Erschaffung von Gegenständen handeln, dessen Voraussetzungen der Kampfmagus erfüllen muss."
)
BONUSTALENT_LEVELS = [5, 11, 17]

# (name, description, min_level, requires_arkanum_name, granted_feat_id)
ARKANA: list[tuple[str, str, int | None, str | None, str | None]] = [
    (
        "Arkane Genauigkeit",
        "(ÜF) Der Kampfmagus kann einen Punkt seines Arkanen Vorrats als Schnelle Aktion aufwenden, um "
        "sich selbst bis zum Ende seines Zuges einen Verständnisbonus in Höhe seines IN-Modifikators zu "
        "verleihen.",
        None,
        None,
        None,
    ),
    (
        "Ausgedehnte Studien",
        "(AF) Der Kampfmagus wählt eine andere seiner zauberkundigen Klassen aus. Er kann fortan "
        "Kampfzauberei und Zauberschlag in Verbindung mit den Zaubern der Zauberliste dieser Klasse "
        "nutzen. Der Kampfmagus muss mindestens die 6. Stufe erreicht haben und Stufen in mindestens "
        "einer anderen zauberkundigen Klasse besitzen, um dieses Arkanum auswählen zu können.",
        6,
        None,
        None,
    ),
    (
        "Bannender Schlag",
        "(ÜF) Der Kampfmagus kann einen oder mehr Punkte seines Arkanen Vorrats einsetzen, um mit einer "
        "Schnellen Aktion seine Waffe mit einer besonderen Kraft zu versehen. Falls die Waffe innerhalb "
        "der nächsten Minute eine Kreatur trifft, wird diese Kreatur das Ziel von Magie bannen mit "
        "einer ZS in Höhe der Klassenstufe des Kampfmagus. Der Kampfmagus muss mindestens die 9. Stufe "
        "erreicht haben, um dieses Arkanum auswählen zu können.",
        9,
        None,
        None,
    ),
    (
        "Direkte Berührung",
        "(AF) Der Kampfmagus kann Strahlenangriffe, welche Berührungsangriffe im Fernkampf erfordern, "
        "als Berührungsangriffe im Nahkampf übermitteln. Diese Zauber können zusammen mit dem "
        "Klassenmerkmal Zauberschlag gewirkt werden.",
        None,
        None,
        None,
    ),
    (
        "Eiliger Angriff",
        "(ÜF) Der Kampfmagus kann als Schnelle Aktion einen Punkt seines Arkanen Vorrats aufwenden, um "
        "sich schneller zu bewegen. Dies funktioniert wie der Zauber Hast, betrifft aber nur den "
        "Kampfmagus und hält für eine Anzahl von Runden in Höhe des IN-Modifikators des Kampfmagus an. "
        "Der Kampfmagus muss mindestens die 9. Stufe erreicht haben, um dieses Arkanum auswählen zu "
        "können.",
        9,
        None,
        None,
    ),
    (
        "Gestenlose Magie",
        "(ÜF) Der Kampfmagus kann ein Mal am Tag einen Zauber wirken, als wäre dieser durch das Talent "
        "Gestenlos zaubern modifiziert worden. Dies erhöht weder den Zeitaufwand, noch den Grad des "
        "Zaubers.",
        None,
        None,
        None,
    ),
    (
        "Konzentration",
        "(AF) Der Kampfmagus kann ein Mal am Tag einen Konzentrationswurf mit einem Bonus von +4 "
        "wiederholen. Er muss diese Fähigkeit einsetzen, nachdem der Wurf erfolgt ist, aber ehe das "
        "Ergebnis bestimmt wird. Der Kampfmagus muss den zweiten Wurf nehmen, selbst wenn dieser "
        "schlechter ausfällt.",
        None,
        None,
        None,
    ),
    (
        "Kritischer Schlag",
        "(ÜF) Wenn der Kampfmagus mit einer Nahkampfwaffe einen Kritischen Treffer erzielt, kann er ein "
        "Mal am Tag einen Zauber mit der Reichweite Berührung als Schnelle Aktion wirken und als Freie "
        "Aktion einen Berührungsangriff mit diesem Zauber gegen das Ziel des Kritischen Treffers "
        "ausführen. Der Kampfmagus muss die 12. Stufe erreicht haben, um dieses Arkanum auswählen zu "
        "können.",
        12,
        None,
        None,
    ),
    (
        "Lautlose Magie",
        "(ÜF) Der Kampfmagus kann ein Mal am Tag einen Zauber wirken, als wäre dieser durch das Talent "
        "Lautlos zaubern modifiziert worden. Dies erhöht weder den Zeitaufwand noch den Grad des "
        "Zaubers.",
        None,
        None,
        None,
    ),
    (
        "Maximierte Magie",
        "(ÜF) Der Kampfmagus kann ein Mal am Tag einen Zauber wirken, als wäre dieser durch das Talent "
        "Zaubereffekt maximieren modifiziert worden. Dies erhöht weder den Zeitaufwand, noch den Grad "
        "des Zaubers. Der Kampfmagus muss mindestens die 12. Stufe erreicht haben, um dieses Arkanum "
        "auswählen zu können.",
        12,
        None,
        None,
    ),
    (
        "Meisterliche Manöver",
        "(AF) Der Kampfmagus hat ein Kampfmanöver perfektioniert. Wenn er sich für dieses Arkanum "
        "entscheidet, wählt er zugleich ein Kampfmanöver aus. Immer wenn er dieses Manöver versucht "
        "einzusetzen, verwendet er künftig statt seines regulären Grundangriffsbonus der "
        "Kampfmagusklasse seine Stufe als Kampfmagus (und addiert eventuelle Grundangriffsboni aus "
        "anderen Klassen dann hinzu). Ein Kampfmagus kann dieses Arkanum mehr als ein Mal auswählen, "
        "muss aber jedes Mal ein anderes Kampfmanöver bestimmen.",
        None,
        None,
        None,
    ),
    (
        "Reflexion",
        "(ÜF) Der Kampfmagus kann mit einer Augenblicklichen Aktion einen oder mehr Punkte seines "
        "Arkanen Vorrats opfern, um einen Zauber auf den Wirker zurückzuwerfen. Dies funktioniert wie "
        "Zauber zurückwerfen, allerdings nur, wenn der Kampfmagus Punkte in Höhe des Zaubergrades "
        "aufgewendet hat; sollte er weniger Punkte eingesetzt haben, erhält er stattdessen einen "
        "Verständnisbonus in Höhe der eingesetzten Punkte auf seine Rettungswürfe gegen den Zauber, "
        "sofern ein solcher erlaubt ist. Der Kampfmagus muss mindestens die 15. Stufe erreicht haben, "
        "um dieses Arkanum auswählen zu können.",
        15,
        None,
        None,
    ),
    (
        "Schnelle Magie",
        "(ÜF) Der Kampfmagus kann ein Mal am Tag einen Zauber wirken, als wäre dieser durch das Talent "
        "Schnell zaubern modifiziert worden. Dies erhöht weder den Zeitaufwand, noch den Grad des "
        "Zaubers. Der Kampfmagus muss mindestens die 15. Stufe erreicht haben, um dieses Arkanum "
        "auswählen zu können.",
        15,
        None,
        None,
    ),
    (
        "Verstärkte Magie",
        "(ÜF) Der Kampfmagus kann ein Mal am Tag einen Zauber wirken, als wäre dieser durch das Talent "
        "Zauber verstärken modifiziert worden. Dies erhöht weder den Zeitaufwand, noch den Grad des "
        "Zaubers. Der Kampfmagus muss mindestens die 6. Stufe erreicht haben, um dieses Arkanum "
        "auswählen zu können.",
        6,
        None,
        None,
    ),
    (
        "Vertrauter",
        "(AF) Der Kampfmagus erhält einen Vertrauten. Seine Stufe als Kampfmagus entspricht dabei "
        "seiner effektiven Stufe als Magier. Dieser Vertraute folgt den Regeln, die unter dem "
        "Klassenmerkmal des Magiers Arkane Verbindung aufgeführt sind.",
        None,
        None,
        None,
    ),
    (
        "Vorratsschlag",
        "(ÜF) Der Kampfmagus kann mit einer Standard-Aktion einen Punkt seines Arkanen Vorrats "
        "aufwenden, um seine freie Hand mit Energie aufzuladen. Er kann als Teil dieser Handlung mit "
        "einer Freien Aktion einen Berührungsangriff im Nahkampf mit dieser Hand ausführen. Sollte der "
        "Berührungsangriff treffen, wird die Ladung freigesetzt und verursacht 2W6 Punkte "
        "Energieschaden (Elektrizität, Feuer, Kälte oder Säure; die Energieart bestimmt der Kampfmagus "
        "bei Aktivierung). Sollte der Kampfmagus sein Ziel verfehlen, kann er die Ladung für maximal "
        "eine Minute aufrechterhalten, ehe diese erlischt. Auf der 6. Stufe und dann alle drei weiteren "
        "Stufen steigt der Schaden um zusätzliche +1W6.",
        None,
        None,
        None,
    ),
    (
        "Zauberabwehr",
        "(ÜF) Der Kampfmagus kann mit einer Augenblicklichen Aktion einen Punkt seines Arkanen Vorrats "
        "aufwenden, um sich bis zum Ende seines nächsten Zuges einen Schildbonus auf seine RK in Höhe "
        "seines IN-Modifikators zu verleihen.",
        None,
        None,
        None,
    ),
    (
        "Zauberforschung",
        "(AF) Wenn ein Kampfmagus sich für dieses Arkanum entscheidet, wählt er einen Magierzauber "
        "eines Zaubergrades aus, den er als Kampfmagus wirken könnte, und fügt ihn seinem Zauberbuch "
        "und der Liste seiner bekannten Kampfmaguszauber hinzu. Er kann auch zwei Zauber auf diese "
        "Weise auswählen, allerdings müssen beide einen Grad niedriger sein als der höchste Grad an "
        "Kampfmaguszaubern, die er wirken kann. Ein Kampfmagus kann dieses Arkanum mehrmals auswählen.",
        None,
        None,
        None,
    ),
    (
        "Zauberstabmeisterschaft",
        "(ÜF) Wenn der Kampfmagus einen Zauberstab benutzt, berechnet er den SG jedes enthaltenen "
        "Zaubers mit seinem IN-Modifikator statt des Mindestmodifikators, der zum Wirken eines Zaubers "
        "dieses Grades erforderlich ist.",
        None,
        None,
        None,
    ),
    (
        "Zauberstabträger",
        "(ÜF) Der Kampfmagus kann im Rahmen seiner Kampfzauberei anstatt einen Zauber zu wirken einen "
        "Zauberstab oder Zauberstecken aktivieren.",
        None,
        None,
        None,
    ),
    # --- from http://prd.5footstep.de/AusbauregelnIIKampf/Archetypen/Kampfmagus ---
    (
        "Anhaftender Vorratsschlag",
        "(ÜF) Der Kampfmagus kann 1 zusätzlichen Punkt seines Arkanen Vorrats einsetzen, wenn er einen "
        "Vorratsschlag ausführt. Ein einzelnes Ziel seines Vorratsschlages erleidet den normalen "
        "Energieschaden und dann zu Beginn seines Zuges in der Folgerunde noch einmal die Hälfte dieses "
        "Schadens. Der Kampfmagus muss mindestens die 9. Stufe erreicht haben und über das Arkanum "
        "Vorratsschlag verfügen, bevor er dieses Arkanum auswählen kann.",
        9,
        "Vorratsschlag",
        None,
    ),
    (
        "Anhaltender Schmerz",
        "(ÜF) Nachdem der Kampfmagus ein Ziel mit einer Waffe getroffen hat, kann er mit einer "
        "Augenblicklichen Aktion 1 Punkt seines Arkanen Vorrats einsetzen. Bis zum Beginn des nächsten "
        "Zuges des Kampfmagus wird sämtlicher Schaden aufgrund dieses Angriffes als andauernder Schaden "
        "hinsichtlich Konzentrationswürfen des Zieles betrachtet.",
        None,
        None,
        None,
    ),
    (
        "Arkanes Bollwerk",
        "(ÜF) Der Kampfmagus kann mit einer Schnellen Aktion 1 Punkt seines Arkanen Vorrats einsetzen, "
        "um bis zum Beginn seines nächsten Zuges seinen Schildbonus auf die RK (eingeschlossen aller "
        "Verbesserungsboni) als Bonus auf seine Berührungs-RK zu behandeln.",
        None,
        None,
        None,
    ),
    (
        "Arkane Klinge",
        "(ÜF) Nachdem der Kampfmagus ein Ziel mit einer Hieb- oder Stichwaffe getroffen hat, kann er "
        "mit einer Augenblicklichen Aktion 1 Punkt seines Arkanen Vorrats einsetzen, um Blutungsschaden "
        "in Höhe seines IN-Modifikators zu verursachen (Minimum 0). Der Kampfmagus muss mindestens die "
        "9. Stufe erreicht haben, bevor er dieses Arkanum auswählen kann.",
        9,
        None,
        None,
    ),
    (
        "Arkaner Umhang",
        "(ÜF) Der Kampfmagus kann 1 Punkt seines Arkanen Vorrats einsetzen, um seinen IN-Bonus auf alle "
        "Fertigkeitswürfe für Heimlichkeit und Bluffen hinzuzuaddieren, mit denen er eine Ablenkung "
        "erschaffen möchte, um sich zu verstecken. Dieser Bonus hält 1 Minute an.",
        None,
        None,
        None,
    ),
    (
        "Ausdauernde Klinge",
        "(ÜF) Verbessert der Kampfmagus seine Waffe mittels seines Arkanen Vorrats, kann er 1 "
        "zusätzlichen Punkt einsetzen, um die Wirkungsdauer auf 1 Minute pro Stufe als Kampfmagus zu "
        "erhöhen. Der Kampfmagus muss mindestens die 6. Stufe erreicht haben, bevor er dieses Arkanum "
        "auswählen kann.",
        6,
        None,
        None,
    ),
    (
        "Ätherklinge",
        "(ÜF) Verzaubert der Kampfmagus seine Waffe mittels seines Arkanen Vorrats, kann er 1 "
        "zusätzlichen Punkt einsetzen, um die besonderen Eigenschaften Geisterhafte Berührung und "
        "Strahlendes Licht der Liste verfügbarer Optionen hinzuzufügen. Der Kampfmagus muss mindestens "
        "die 9. Stufe erreicht haben, bevor er dieses Arkanum auswählen kann.",
        9,
        None,
        None,
    ),
    (
        "Donnernder Vorratsschlag",
        "(ÜF) Der Kampfmagus kann 1 zusätzlichen Punkt seines Arkanen Vorrats einsetzen, wenn er einen "
        "Vorratsschlag ausführt. Sein Vorratsschlag verursacht Schallschaden und macht ein einzelnes "
        "Ziel für 1 Runde taub (SG 10 + ½ Stufe als Kampfmagus + IN-Modifikator). Der Kampfmagus muss "
        "mindestens die 6. Stufe erreicht haben und über das Arkanum Vorratsschlag verfügen, bevor er "
        "dieses Arkanum auswählen kann.",
        6,
        "Vorratsschlag",
        None,
    ),
    (
        "Exakter Schlag",
        "(AF) Der Kampfmagus kann mit einer Schnellen Aktion 2 Punkte seines Arkanen Vorrats einsetzen, "
        "um bis zum Ende seines Zuges alle seine Angriffe mit Nahkampfwaffen als Berührungsangriffe im "
        "Nahkampf auszuführen. Der Kampfmagus muss mindestens die 9. Stufe erreicht haben, bevor er "
        "dieses Arkanum auswählen kann.",
        9,
        None,
        None,
    ),
    (
        "Gesinnungsklinge",
        "(ÜF) Verbessert der Kampfmagus seine Waffe mittels seines Arkanen Vorrats, kann er 1 "
        "zusätzlichen Punkt einsetzen, um der Waffe die besondere Waffeneigenschaft Anarchie, "
        "Grundsatz, Heilig oder Unheilig zu verleihen. Ein Kampfmagus kann nur eine Waffeneigenschaft "
        "hinzufügen, welche seiner eigenen Gesinnung entspricht. Der Kampfmagus muss mindestens die 12. "
        "Stufe erreicht haben, bevor er dieses Arkanum auswählen kann.",
        12,
        None,
        None,
    ),
    (
        "Mächtiges Arkanes Bollwerk",
        "(ÜF) Wenn der Kampfmagus das Arkanum Arkanes Bollwerk einsetzt, kann er 1 zusätzlichen Punkt "
        "seines Arkanen Vorrats aufwenden, um bis zum Beginn seines nächsten Zuges seinen Schildbonus "
        "auf die RK zusätzlich als Bonus auf alle seine Reflexwürfe hinzuzuaddieren. Sollte er zum Ziel "
        "eines Effektes werden, der einen Reflexwurf erfordert, während er dieses Arkanum nutzt, kann "
        "er mit einer Augenblicklichen Aktion 2 Punkte seines Arkanen Vorrats einsetzen, um sich "
        "Reflexbewegung zu verleihen, oder 4 Punkte, um sich Verbesserte Reflexbewegung zu verleihen. "
        "Der Kampfmagus muss über das Arkanum Arkanes Bollwerk verfügen und mindestens die 12. Stufe "
        "erreicht haben, bevor er dieses Arkanum auswählen kann.",
        12,
        "Arkanes Bollwerk",
        None,
    ),
    (
        "Überschlagender Vorratsschlag",
        "(ÜF) Der Kampfmagus kann 1 zusätzlichen Punkt seines Arkanen Vorrats einsetzen, wenn er das "
        "Arkanum Vorratsschlag einsetzt. Sollte sein Angriff erfolgreich sein, kann er mit einer Freien "
        "Aktion innerhalb von 4,50 m eine Anzahl von Gegnern in Höhe seines IN-Modifikators (Minimum 0) "
        "zum Ziel eines Berührungsangriffes im Fernkampf machen; jene, die getroffen werden, erleiden "
        "denselben Energieschaden wie das Ausgangsziel. Der Kampfmagus muss mindestens die 12. Stufe "
        "erreicht haben und über das Arkanum Vorratsschlag verfügen, bevor er dieses Arkanum auswählen "
        "kann.",
        12,
        "Vorratsschlag",
        None,
    ),
    (
        "Verderbensklinge",
        "(ÜF) Verbessert der Kampfmagus seine Waffe mittels seines Arkanen Vorrats, kann er 1 "
        "zusätzlichen Punkt einsetzen, um der Waffe die besondere Waffeneigenschaft Verderben zu "
        "verleihen. Der Kampfmagus muss mindestens die 15. Stufe erreicht haben, bevor er dieses "
        "Arkanum auswählen kann.",
        15,
        None,
        None,
    ),
    (
        "Vorausschauende Verteidigung",
        "(ÜF) Nachdem der Kampfmagus ein Ziel mit einer Waffe getroffen hat, kann er mit einer "
        "Augenblicklichen Aktion 1 Punkt seines Arkanen Vorrats einsetzen. Der Kampfmagus erhält bis "
        "zum Beginn seines nächsten Zuges einen Bonus auf seine RK und Reflexwürfe in Höhe seines "
        "IN-Modifikators (Minimum 0) gegen Angriffe dieses Gegners. Der Kampfmagus muss mindestens die "
        "9. Stufe erreicht haben, bevor er dieses Arkanum auswählen kann.",
        9,
        None,
        None,
    ),
    (
        "Vorausschauender Angriff",
        "(ÜF) Nachdem der Kampfmagus ein Ziel mit einer Waffe getroffen hat, kann er mit einer "
        "Augenblicklichen Aktion 1 Punkt seines Arkanen Vorrats einsetzen. Dem Ziel wird bis zum Ende "
        "des nächsten Zuges des Kampfmagus der GE-Bonus auf die RK gegen die Angriffe des Kampfmagus "
        "verweigert. Der Kampfmagus muss mindestens die 6. Stufe erreicht haben, bevor er dieses "
        "Arkanum auswählen kann.",
        6,
        None,
        None,
    ),
    (
        "Zauberbrecher",
        "(AF) Der Kampfmagus erhält das Bonustalent Zauberbrecher. Der Kampfmagus muss mindestens die "
        "9. Stufe erreicht haben, bevor er dieses Arkanum auswählen kann.",
        9,
        None,
        ZAUBERBRECHER_FEAT_ID,
    ),
    (
        "Zauberstörer",
        "(AF) Der Kampfmagus erhält das Bonustalent Zauberstörer. Der Kampfmagus muss mindestens die "
        "6. Stufe erreicht haben, bevor er dieses Arkanum auswählen kann.",
        6,
        None,
        ZAUBERSTOERER_FEAT_ID,
    ),
    (
        "Zeptermeisterschaft",
        "(ÜF) Wenn der Kampfmagus ein Zauberzepter benutzt, berechnet er den SG von Rettungswürfen "
        "gegen die darin enthaltenen Zauber mit seinem IN-Modifikator (Minimum 0) anstelle des "
        "Minimum-Modifikators zum Wirken eines Zaubers dieses Grades.",
        None,
        None,
        None,
    ),
    (
        "Zepterträger",
        "(ÜF) Versucht der Kampfmagus mit Zaubern aus einem Zauberzepter die Zauberresistenz seines "
        "Gegners zu überwinden, darf er seinen IN-Bonus (Minimum 0) auf seine Zauberstufenwürfe "
        "hinzuaddieren. Er darf seinen Bonus ebenfalls hinzuaddieren, wenn er einen Zauberschlag durch "
        "ein Zauberzepter fokussiert.",
        None,
        None,
        None,
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
    classes = load("base_classes.json")
    classes[:] = [c for c in classes if c["id"] != KAMPFMAGUS_ID]
    classes.append(
        {
            "id": KAMPFMAGUS_ID,
            "name": "Kampfmagus",
            "hit_dice": 8,
            "arch_class_of": None,
            "casting_ability": "IN",
            "spell_tradition": "arcane",
            "bab_progression": 0.75,
            "fort_save": True,
            "ref_save": False,
            "wil_save": True,
            "skill_points_base": 2,
        }
    )
    save("base_classes.json", classes)

    class_skills = load("base_class_skills.json")
    class_skills[:] = [r for r in class_skills if r["base_class_id"] != KAMPFMAGUS_ID]
    for skill_name, skill_id in CLASS_SKILL_IDS.items():
        class_skills.append(
            {
                "id": uid("kampfmagus-skill", skill_name),
                "base_class_id": KAMPFMAGUS_ID,
                "skill_id": skill_id,
            }
        )
    save("base_class_skills.json", class_skills)

    known = load("base_class_spells_known.json")
    known[:] = [r for r in known if r["base_class_id"] != KAMPFMAGUS_ID]
    for level in range(1, 21):
        for grade, first_level in GRADE_FIRST_LEVEL.items():
            if level >= first_level:
                known.append(
                    {
                        "id": uid("kampfmagus-known", str(level), str(grade)),
                        "base_class_id": KAMPFMAGUS_ID,
                        "level": level,
                        "grade": grade,
                        "count": None,
                    }
                )
    save("base_class_spells_known.json", known)

    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    feat_grants = load("base_class_ability_granted_feats.json")
    feat_opts = load("base_class_ability_feat_options.json")
    groups = load("base_class_option_groups.json")
    choices = load("base_class_option_choices.json")

    own_ability_ids = {uid("kampfmagus-ability", name) for name, *_ in CORE_FEATURES}
    own_ability_ids |= {uid("kampfmagus-arkanum-slot"), uid("kampfmagus-bonustalent-slot")}
    own_ability_ids |= {uid("kampfmagus-arkanum", name) for name, *_ in ARKANA}
    abilities[:] = [a for a in abilities if a["id"] not in own_ability_ids]
    grants[:] = [g for g in grants if g["base_class_id"] != KAMPFMAGUS_ID]
    feat_grants[:] = [
        fg for fg in feat_grants if fg["ability_id"] not in own_ability_ids
    ]
    feat_opts[:] = [fo for fo in feat_opts if fo["ability_id"] not in own_ability_ids]
    groups[:] = [g for g in groups if g["id"] != ARKANUM_GROUP_ID]
    choices[:] = [c for c in choices if c["group_id"] != ARKANUM_GROUP_ID]

    for name, levels, description, granted_feat_ids in CORE_FEATURES:
        ability_id = uid("kampfmagus-ability", name)
        abilities.append({"id": ability_id, "name": name, "description": description})
        for level in levels:
            grants.append(
                {
                    "id": uid("kampfmagus-grant", ability_id, str(level)),
                    "base_class_id": KAMPFMAGUS_ID,
                    "ability_id": ability_id,
                    "option_choice_id": None,
                    "level": level,
                }
            )
        for i, feat_id in enumerate(granted_feat_ids):
            feat_grants.append(
                {"id": uid("kampfmagus-granted-feat", ability_id, str(i)), "ability_id": ability_id, "feat_id": feat_id}
            )

    # Arkanum slot: unconditional grants at 3/6/9/12/15/18 define the option
    # group's occurrence levels (rules/class_options.py's group_occurrence_levels).
    arkanum_slot_id = uid("kampfmagus-arkanum-slot")
    abilities.append({"id": arkanum_slot_id, "name": "Arkanum", "description": ARKANUM_SLOT_DESCRIPTION})
    for level in ARKANUM_LEVELS:
        grants.append(
            {
                "id": uid("kampfmagus-grant", arkanum_slot_id, str(level)),
                "base_class_id": KAMPFMAGUS_ID,
                "ability_id": arkanum_slot_id,
                "option_choice_id": None,
                "level": level,
            }
        )

    groups.append(
        {
            "id": ARKANUM_GROUP_ID,
            "base_class_id": KAMPFMAGUS_ID,
            "key": "arkanum",
            "label": "Arkanum",
            "max_choices": len(ARKANUM_LEVELS),
        }
    )

    choice_id_by_arkanum_name = {name: uid("kampfmagus-arkanum-choice", name) for name, *_ in ARKANA}
    for name, description, min_level, requires_name, granted_feat_id in ARKANA:
        choice_id = choice_id_by_arkanum_name[name]
        choices.append(
            {
                "id": choice_id,
                "group_id": ARKANUM_GROUP_ID,
                "name": name,
                "min_level": min_level,
                "requires_choice_id": choice_id_by_arkanum_name[requires_name] if requires_name else None,
                "race_id": None,
            }
        )
        ability_id = uid("kampfmagus-arkanum", name)
        abilities.append({"id": ability_id, "name": name, "description": description})
        grants.append(
            {
                "id": uid("kampfmagus-grant-arkanum", ability_id),
                "base_class_id": KAMPFMAGUS_ID,
                "ability_id": ability_id,
                "option_choice_id": choice_id,
                "level": 1,
            }
        )
        if granted_feat_id:
            feat_grants.append(
                {
                    "id": uid("kampfmagus-granted-feat-arkanum", ability_id),
                    "ability_id": ability_id,
                    "feat_id": granted_feat_id,
                }
            )

    # Bonustalent slot: same shape as Magier's/Kämpfer's own bonus-feat abilities.
    bonustalent_id = uid("kampfmagus-bonustalent-slot")
    abilities.append({"id": bonustalent_id, "name": "Bonustalent", "description": BONUSTALENT_DESCRIPTION})
    for level in BONUSTALENT_LEVELS:
        grants.append(
            {
                "id": uid("kampfmagus-grant", bonustalent_id, str(level)),
                "base_class_id": KAMPFMAGUS_ID,
                "ability_id": bonustalent_id,
                "option_choice_id": None,
                "level": level,
            }
        )
    for feat_type in ("combat", "metamagic", "item_creation"):
        feat_opts.append(
            {
                "id": uid("kampfmagus-bonustalent-option", feat_type),
                "ability_id": bonustalent_id,
                "option_choice_id": None,
                "feat_type": feat_type,
                "feat_id": None,
                "min_level": None,
            }
        )

    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)
    save("base_class_ability_granted_feats.json", feat_grants)
    save("base_class_ability_feat_options.json", feat_opts)
    save("base_class_option_groups.json", groups)
    save("base_class_option_choices.json", choices)

    # classes.json: name + spellType is all that's still authoritative there
    # (see main.py's get_classes docstring) - classSkills/optionGroups are
    # kept here too only for readability parity with sibling fixture rows,
    # the live endpoint overwrites both from the DB-shaped rows above.
    class_defs = json.loads((FIXTURES / "classes.json").read_text(encoding="utf-8"))
    class_defs[:] = [c for c in class_defs if c["name"] != "Kampfmagus"]
    class_defs.append(
        {
            "name": "Kampfmagus",
            "skillPointsBase": 2,
            "spellType": "arcane-prepared",
            "classSkills": [
                "beruf",
                "einschuechtern",
                "fliegen",
                "handwerk",
                "klettern",
                "umd",
                "reiten",
                "schwimmen",
                "wissen_arkanes",
                "wissen_die_ebenen",
                "wissen_gewoelbekunde",
                "zauberkunde",
            ],
            "optionGroups": [
                {
                    "key": "arkanum",
                    "label": "Arkanum",
                    "max": len(ARKANUM_LEVELS),
                    "choices": [name for name, *_ in ARKANA],
                }
            ],
        }
    )
    (FIXTURES / "classes.json").write_text(
        json.dumps(class_defs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # base_class_spells.json: backfill from the PRD's own already-fetched
    # per-class grade data (see this script's docstring) rather than
    # hand-parsing this page's prose spell list.
    spell_import = json.loads((IMPORTED / "zauber_prd_import.json").read_text(encoding="utf-8"))
    existing_spell_ids = {s["id"] for s in load("base_spells.json")}
    class_spells = load("base_class_spells.json")
    class_spells[:] = [r for r in class_spells if r["base_class_id"] != KAMPFMAGUS_ID]
    matched = 0
    skipped = 0
    for entry in spell_import:
        grade = entry.get("grades_by_class", {}).get("Kampfmagus")
        if grade is None:
            continue
        if entry["id"] not in existing_spell_ids:
            skipped += 1
            continue
        class_spells.append(
            {
                "id": uid("kampfmagus-spell", entry["id"]),
                "base_class_id": KAMPFMAGUS_ID,
                "spell_id": entry["id"],
                "grade": grade,
            }
        )
        matched += 1
    save("base_class_spells.json", class_spells)

    print("Kampfmagus class id:", KAMPFMAGUS_ID)
    print("Arkanum group id:", ARKANUM_GROUP_ID)
    print(f"base_class_spells: {matched} matched, {skipped} skipped (not in base_spells.json yet)")
    print("Done.")


if __name__ == "__main__":
    main()
