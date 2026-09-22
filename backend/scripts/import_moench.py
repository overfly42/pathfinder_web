"""Import the (Grundregelwerk core) Mönch's class shell from
http://prd.5footstep.de/Grundregelwerk/Klassen/Moench.

`hit_dice`/`bab_progression`/`fort_save`/`ref_save`/`wil_save`/
`skill_points_base` on `base_classes.json`'s existing Mönch row were already
correct (W8, 3/4 GAB, all three good saves, 4 + IN) — verified against
"Tabelle: Mönch", not re-written.

What this script does:
- Fixes `base_class_skills.json`: the existing 11 rows wrongly included
  Heilkunde (Heal is not on the Monk's class-skill list in core PF1e) and
  were missing 4 real class skills (Auftreten, Beruf, Handwerk, Reiten) —
  corrected to the page's own 14-skill list. The 10 rows that were already
  correct keep their original row ids (looked up by skill name against the
  existing rows, not regenerated) so re-running this script doesn't create
  duplicate rows once seeded into the database — only Heilkunde's row is
  dropped and 4 fresh rows added. (An earlier version of this script
  regenerated all 14 ids from scratch, which produced 10 duplicate DB rows
  the first time it was seeded, since `skill_seed.py`'s upsert-by-id never
  deletes a row whose id disappears from the fixture — fixed before that
  version was committed; see the one-off DB cleanup this required, noted in
  `todos.md`/the commit that added this class.)
- Adds the 24 class features as `BaseClassAbility`/`BaseClassAbilityGrant`
  rows: Umgang mit Waffen und Rüstungen (1), Rüstungsklassenbonus (1),
  Schlaghagel (1), Waffenloser Schlag (1), Betäubender Schlag (1), Bonustalent
  (1/2/6/10/14/18, one ability with six grants, same repeated-grant shape as
  Kämpfer's Bonus-Kampftalent), Entrinnen (2), Schnelle Bewegung (3),
  Manövertraining (3), Ruhiger Geist (3), Ki-Vorrat (4/7/10/16, one ability
  with four grants — the table re-lists it at each level with a different
  material it overcomes), Sturz abbremsen (4/6/8/10/12/14/16/18/20, one
  ability with nine grants — the table re-lists it at every even level from
  4 with an increasing distance), Hochsprung (5), Reinheit des Körpers (5),
  Unversehrtheit des Körpers (7), Verbessertes Entrinnen (9), Diamantkörper
  (11), Weiter Schritt (12), Diamantseele (13), Vibrierende Handfläche (15),
  Zeitloser Körper (17), Sprache von Sonne und Mond (17), Körper lösen (19),
  Perfektes Selbst (20).
- Wires the two feats the class shell grants automatically, for free, no
  pick spent (`BaseClassAbilityGrantedFeat`, same mechanism as every other
  class's weapon/armor proficiency ability): Waffenloser Schlag ->
  Verbesserter waffenloser Schlag (Improved Unarmed Strike); Betäubender
  Schlag -> Betäubender Schlag (Stunning Fist) itself, ignoring its normal
  prerequisites, per the page's own text.
- Wires Bonustalent's closed feat list as `BaseClassAbilityFeatOption` rows
  (`feat_id`, not `feat_type` — this is a fixed list, not "any combat feat"
  like Kämpfer's slot): 7 feats from 1st level (Ausweichen, Geschosse
  abwehren, Improvisierter Fernkampf, Improvisierter Nahkampf, Kampfreflexe,
  Skorpionstachel, Verbesserter Ringkampf), 6 more from 6th
  (`min_level=6`: Gorgonenfaust, Beweglichkeit, Verbesserter Ansturm,
  Verbessertes Entwaffnen, Verbesserte Finte, Verbessertes Zu-Fall-bringen),
  4 more from 10th (`min_level=10`: Geschosse fangen, Medusenzorn,
  Tänzelnder Angriff, Verbesserter Kritischer Treffer). All 17 feats already
  exist in `base_feats.json` — checked before writing this script.
- Registers Bonustalent's ability id in `rules/feat_slots.py`'s
  `BONUS_FEAT_SLOT_ABILITY_IDS` — without this, the seeded feat-option rows
  would exist but `class_bonus_feat_slot_count` wouldn't count them toward
  `featMax`, same as Kämpfer's own entry there.

Deliberately out of scope, same "don't guess, don't migrate unrelated
content" principle as every other class pass (CLAUDE.md):
- No handler-side computation at all (unarmed damage progression by size,
  Ki-Vorrat's point pool, flurry's extra-attack count/penalty, AC bonus
  scaling, Betäubender Schlag's per-level condition options, Vibrierende
  Handfläche's death effect, etc.) — composition only. The unarmed-damage
  progression table (by monk level, small/medium/large) is folded into
  Waffenloser Schlag's own description as prose, same treatment Barbar gave
  its rage-bonus numbers.
- "Ehemalige Mönche" (losing the ability to advance as a Mönch on becoming
  non-lawful) is prose about a consequence, not a granted class feature at a
  level — no `BaseClassAbilityGrant` shape fits it, and no alignment field
  exists on `characters` to check against anyway. Left unmodeled, same as
  Barbar's "Ehemaliger Barbar".
- Archetypes are out of scope here entirely; see
  `import_meister_aller_kampfstile.py` and `import_scaled_fist_archetype.py`
  for the two archetypes added alongside this pass.

Run with the project venv active (this only writes the fixture JSON files
plus one code edit, it doesn't touch the database — run the normal seed
scripts afterward):
    cd backend && python scripts/import_moench.py
    python -m app.seed.class_skill_seed  # via app.seed.skill_seed, see below
    python -m app.seed.class_ability_seed
    python -m app.seed.class_ability_option_seed
    python -m app.seed.class_ability_granted_feat_seed
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("ce077089-5253-44db-ba96-a58552024ba0")

MOENCH_ID = "4ed3adcc-31e6-408d-a554-5e76a368df9d"

CORRECT_CLASS_SKILLS = [
    "Akrobatik",
    "Auftreten",
    "Beruf",
    "Einschüchtern",
    "Entfesselungskunst",
    "Handwerk",
    "Heimlichkeit",
    "Klettern",
    "Motiv erkennen",
    "Reiten",
    "Schwimmen",
    "Wahrnehmung",
    "Wissen (Geschichte)",
    "Wissen (Religion)",
]

STURZ_ABBREMSEN_LEVELS = [4, 6, 8, 10, 12, 14, 16, 18, 20]
KI_VORRAT_LEVELS = [4, 7, 10, 16]
BONUSTALENT_LEVELS = [1, 2, 6, 10, 14, 18]

WAFFENLOSER_SCHLAG_DESC = (
    "Auf der 1. Stufe erhält der Mönch das Talent Verbesserter waffenloser Schlag als Bonustalent. Er kann mit "
    "seiner Faust, den Ellenbogen, Knien oder den Füßen angreifen. Das heißt, ein Mönch kann auch wenn er seine "
    "Hände voll hat noch unbewaffnete Angriffe durchführen. Für einen Mönch gibt es so etwas wie eine Zweithand "
    "nicht. Er addiert auch auf den Schaden aller unbewaffneten Angriffe seinen vollen Stärkebonus.\n\n"
    "Üblicherweise verursacht der Mönch mit seinen unbewaffneten Angriffen tödlichen Schaden. Er kann sich jedoch "
    "entscheiden, nichttödlichen Schaden zu machen, ohne Abzüge hinzunehmen. Die gleiche Wahl hat er während eines "
    "Ringkampfes.\n\n"
    "Der waffenlose Angriff des Mönchs zählt sowohl als hergestellte als auch als natürliche Waffe, wenn es um "
    "Zaubersprüche und Effekte geht, die Angriffe verbessern.\n\n"
    "Ein Mönch verursacht mit seinen waffenlosen Angriffen mehr Schaden als ein normaler Nahkämpfer. Für einen "
    "mittelgroßen Mönch: 1W6 (Stufe 1-3), 1W8 (4-7), 1W10 (8-11), 2W6 (12-15), 2W8 (16-19), 2W10 (20). Ein kleiner "
    "Mönch verursacht weniger (1W4 / 1W6 / 1W8 / 1W10 / 2W6 / 2W8), ein großer Mönch mehr (1W8 / 2W6 / 2W8 / 3W6 / "
    "3W8 / 4W8)."
)

BONUSTALENT_DESC = (
    "Auf der 1., der 2. und dann alle vier weiteren Stufen darf der Mönch ein Bonustalent auswählen. Er muss dieses "
    "Talent aus der folgenden Liste wählen: Ausweichen, Geschosse abwehren, Improvisierter Fernkampf, Improvisierter "
    "Nahkampf, Kampfreflexe, Skorpionstachel, Verbesserter Ringkampf. Auf der 6. Stufe kommen folgende Talente zu "
    "dieser Liste hinzu: Gorgonenfaust, Beweglichkeit, Verbesserter Ansturm, Verbessertes Entwaffnen, Verbesserte "
    "Finte, Verbessertes Zu-Fall-bringen. Mit dem Erreichen der 10. Stufe stehen weitere Talente zur Verfügung: "
    "Geschosse fangen, Medusenzorn, Tänzelnder Angriff, Verbesserter Kritischer Treffer. Der Mönch muss für diese "
    "Talente die normalen Voraussetzungen nicht erfüllen."
)

# (name, levels, description)
CLASS_FEATURES: list[tuple[str, list[int], str]] = [
    (
        "Umgang mit Waffen und Rüstungen",
        [1],
        "Der Mönch ist im Umgang mit Armbrüsten (leicht oder schwer), Beilen, Dolchen, Kamas, Kampfstäben, Keulen, "
        "Kurzspeeren, Kurzschwertern, Nunchakus, Sais, Schleudern, Shuriken, Sianghams, Speeren und Wurfspeeren "
        "geübt.\n\n"
        "Er ist mit keinerlei Rüstungen oder Schilden vertraut.\n\n"
        "Sollte der Mönch Rüstung tragen, ein Schild benutzen oder mit mehr als einer leichten Traglast belastet "
        "sein, verliert er seinen Rüstungsklassenbonus, seine Schnelle Bewegung und den Schlaghagel.",
    ),
    (
        "Rüstungsklassenbonus",
        [1],
        "(AF) Wenn der Mönch nicht gerüstet oder belastet ist, kann er seinen Weisheitsbonus (wenn er einen hat) "
        "zu seiner Rüstungsklasse und seiner Kampfmanöververteidigung addieren. Zusätzlich erhält er auf der 4. "
        "Stufe einen RK- und KMV-Bonus von +1. Dieser Bonus erhöht sich alle weiteren vier Stufen um eins, bis zu "
        "einem Maximum von +5 auf der 20. Stufe.\n\n"
        "Dieser Bonus hilft dem Mönch auch gegen Berührungsangriffe und wenn er auf dem falschen Fuß erwischt wird. "
        "Er verliert den Bonus jedoch, wenn er bewegungsunfähig ist, wenn er hilflos ist, wenn er eine Rüstung "
        "trägt, wenn er einen Schild einsetzt, oder wenn er eine mittlere oder schwere Last trägt.",
    ),
    (
        "Schlaghagel",
        [1],
        "(AF) Ab der 1. Stufe kann ein Mönch mit einer Vollen Aktion einen Schlaghagel austeilen. Wenn er dies "
        "möchte, erhält er einen zusätzlichen Angriff mit einem Malus von -2 auf alle Angriffswürfe, als würde er "
        "das Talent Kampf mit zwei Waffen einsetzen. Diese Angriffe können jede beliebige Kombination aus "
        "Unbewaffneten Angriffen oder Angriffen mit einer speziellen Mönchswaffe (Kama, Kampfstab, Nunchaku, Sai, "
        "Siangham und Shuriken) nehmen, als würde er das Talent Kampf mit zwei Waffen einsetzen (unabhängig davon, "
        "ob er die Voraussetzungen dafür erfüllt oder nicht). Für den Zweck dieses Angriffes entspricht der "
        "Grund-Angriffsbonus des Mönchs seiner Klassenstufe. Für alle anderen Einsatzmöglichkeiten verwendet der "
        "Mönch seinen normalen Grund-Angriffsbonus.\n\n"
        "Ab der 8. Stufe kann ein Mönch zwei zusätzliche Angriffe ausführen, wenn er seine Gegner mit einem "
        "Schlaghagel eindeckt, als würde er das Talent Verbesserter Kampf mit zwei Waffen einsetzen (unabhängig "
        "davon, ob er die Voraussetzungen erfüllt oder nicht).\n\n"
        "Ab der 15. Stufe erhält der Mönch drei zusätzliche Angriffe bei dem Einsatz eines Schlaghagels, als ob er "
        "das Talent Mächtiger Kampf mit zwei Waffen einsetzen würde (unabhängig davon, ob er die Voraussetzungen "
        "erfüllt oder nicht).\n\n"
        "Der Mönch erhält auf jeden Angriff im Schlaghagel seinen vollen Stärkebonus, egal ob er den Angriff mit "
        "seiner Zweithand oder mit einer beidhändigen Waffe ausführt. Ein Mönch kann einen unbewaffneten Angriff "
        "auch durch ein Kampfmanöver der Arten Entwaffnen, Gegenstand zerschmettern oder Zu Fall bringen ersetzen. "
        "Der Mönch kann während des Schlaghagels keine Waffe benutzen, die keine Mönchswaffe ist. Ein Mönch mit "
        "natürlichen Waffen kann diese weder in einem Schlaghagel einsetzen, noch kann er seine natürlichen "
        "Angriffe zusätzlich zu dem Schlaghagel ausführen.",
    ),
    ("Waffenloser Schlag", [1], WAFFENLOSER_SCHLAG_DESC),
    (
        "Betäubender Schlag",
        [1],
        "(AF) Auf der 1. Stufe erhält der Mönch Betäubender Schlag als Bonustalent, auch wenn er nicht die "
        "Voraussetzungen dafür erfüllt. Auf der 4. Stufe und alle weiteren 4 Stufen danach erhält der Mönch die "
        "Möglichkeit, dem Ziel des Betäubenden Schlages einen neuen Zustand zuzufügen. Dieser Zustand ersetzt das "
        "Betäuben des Ziels für eine Runde und ein erfolgreicher Rettungswurf lässt den neuen Zustand auch "
        "weiterhin nicht wirksam werden. Ab der 4. Stufe kann er sich dafür entscheiden, sein Ziel erschöpft sein "
        "zu lassen. Ab der 8. Stufe kann er sein Ziel für eine Minute kränkelnd machen. Ab der 12. Stufe kann er "
        "sein Ziel für 1W6+1 Runden wankend machen. Ab der 16. Stufe kann er sein Ziel permanent erblinden oder "
        "taub werden lassen. Ab der 20. Stufe kann er sich dafür entscheiden, dass sein Ziel für 1W6+1 Runden "
        "gelähmt ist. Der Mönch muss sich dafür entscheiden, welchen Zustand er anwendet, bevor der Angriffswurf "
        "gemacht wird. Diese Effekte addieren sich nicht mit sich selber, aber zusätzliche Treffer erhöhen die "
        "Dauer des Zustandes.",
    ),
    ("Bonustalent", BONUSTALENT_LEVELS, BONUSTALENT_DESC),
    (
        "Entrinnen",
        [2],
        "(AF) Wenn ein Mönch, der mindestens die 2. Stufe erreicht hat, einen Reflexwurf durchführt, um nur halben "
        "Schaden zu erleiden, nimmt er bei gelungenem Rettungswurf keinen Schaden. Entrinnen kann der Mönch nur "
        "nutzen, wenn er leichte oder keine Rüstung trägt. Ein hilfloser Mönch profitiert nicht von dieser "
        "Fähigkeit.",
    ),
    (
        "Schnelle Bewegung",
        [3],
        "(AF) Ab der 3. Stufe erhält der Mönch einen Verbesserungsbonus zu seiner Bewegungsrate. Ein Mönch, der "
        "Rüstung oder mehr als eine leichte Last trägt, verliert diesen Bonus.",
    ),
    (
        "Manövertraining",
        [3],
        "(AF) Ab der 3. Stufe benutzt der Mönch seine Stufe als Grund-Angriffsbonus, um seinen Kampfmanöverbonus "
        "zu ermitteln (die Kampfmanöververteidigung ist davon nicht betroffen). Der Grund-Angriffsbonus, den er "
        "durch andere Klassen erhält, ist hiervon nicht betroffen und wird normal addiert.",
    ),
    (
        "Ruhiger Geist",
        [3],
        "(AF) Auf der 3. Stufe erhält ein Mönch einen Bonus von +2 auf Rettungswürfe gegen Zauber und Effekte der "
        "Zauberschule Verzauberung.",
    ),
    (
        "Ki-Vorrat",
        KI_VORRAT_LEVELS,
        "(ÜF) Ab der 4. Stufe erhält der Mönch einen Vorrat an Ki-Punkten, eine Art übernatürlicher Energie, mit "
        "der er beeindruckende Taten vollführen kann. Die Anzahl an Punkten im Ki-Vorrat eines Mönchs entspricht "
        "seiner halben Stufe plus seinen WE-Modifikator. Solange er noch mindestens einen Punkt in seinem Vorrat "
        "hat, kann er Ki-Schläge ausführen. Auf der 4. Stufe zählt sein unbewaffneter Angriff, dank Ki-Schlag, als "
        "magische Waffe, um Schadensreduzierung und Härte zu überwinden. Ab der 7. Stufe zählen sie als Kaltes "
        "Eisen und Silber, ab der 10. Stufe als rechtschaffene Waffe und ab der 16. Stufe als Adamantwaffe um "
        "Schadensreduzierungen und Härte zu überwinden.\n\n"
        "Wenn der Mönch einen Schlaghagel nutzt, kann er einen Ki-Punkt aus seinem Vorrat ausgeben, um einen "
        "weiteren Angriff mit seinem höchsten Angriffsbonus durchzuführen. Zudem kann er einen Ki-Punkt ausgeben, "
        "um seine Bewegungsrate für eine Runde um 6 m zu erhöhen. Für einen Ki-Punkt erhält der Mönch eine Runde "
        "lang einen Ausweichbonus von +4 auf seine Rüstungsklasse. Der Einsatz einer solchen Fähigkeit zählt als "
        "Schnelle Aktion. Der Mönch erhält weitere Fähigkeiten, seine Ki-Punkte zu nutzen, wenn er weiter "
        "aufsteigt.\n\n"
        "Der Ki-Vorrat frischt sich nach acht Stunden Rast oder Meditation wieder auf. Diese Stunden brauchen "
        "nicht direkt aufeinander zu folgen.",
    ),
    (
        "Sturz abbremsen",
        STURZ_ABBREMSEN_LEVELS,
        "(AF) Ein Mönch, der mindestens die 4. Stufe erreicht hat und höchstens eine Armlänge von einer Wand "
        "entfernt ist, kann diese nutzen, um einen Sturz abzuschwächen. Wenn er diese Fähigkeit erhält, wird die "
        "Sturzhöhe zur Bestimmung des Schadens, den er erhält, um 6 m reduziert. Wenn er seine Mönchstufen "
        "verbessert, erhöht sich diese Zahl (9 m ab Stufe 6, 12 m ab Stufe 8, 15 m ab Stufe 10, 18 m ab Stufe 12, "
        "21 m ab Stufe 14, 24 m ab Stufe 16, 27 m ab Stufe 18), bis er auf der 20. Stufe in Reichweite einer Wand "
        "einen Sturz von jeglicher Höhe abfangen kann.",
    ),
    (
        "Hochsprung",
        [5],
        "(AF) Ab der 5. Stufe addiert der Mönch seine Stufe zu allen Fertigkeitswürfen auf Akrobatik, um horizontal "
        "oder vertikal zu springen. Außerdem kann er bei seinen Würfen auf Akrobatik immer davon ausgehen, dass er "
        "einen Anlauf gehabt hätte. Mit der Ausgabe eines Ki-Punkts erhält der Mönch als Schnelle Aktion für eine "
        "Runde einen Bonus von +20 auf seinen Wurf für Akrobatik, um zu springen.",
    ),
    (
        "Reinheit des Körpers",
        [5],
        "(AF) Ab der 5. Stufe ist der Mönch gegen alle Krankheiten, auch übernatürliche und magische, immun.",
    ),
    (
        "Unversehrtheit des Körpers",
        [7],
        "(AF) Ab der 7. Stufe kann ein Mönch mit einer Standard-Aktion seine eigenen Wunden heilen. Er muss zwei "
        "Ki-Punkte ausgeben und kann dann Trefferpunkte in Höhe seiner Stufe heilen.",
    ),
    (
        "Verbessertes Entrinnen",
        [9],
        "(AF) Ab der 9. Stufe verbessert sich die Fähigkeit eines Mönchs, einem Angriff zu entrinnen. Ist der Mönch "
        "einem Angriff ausgesetzt, der einen Reflexwurf für halben Schaden erlaubt, erhält er bei einem gelungenen "
        "Rettungswurf wie bisher keinen Schaden, aber bei einem misslungenen Wurf erleidet er nun nur den halben "
        "Schaden. Ein hilfloser Mönch kann diese Fähigkeit nicht nutzen.",
    ),
    (
        "Diamantkörper",
        [11],
        "(ÜF) Auf der 11. Stufe erhält der Mönch Immunität gegen jede Art von Giften.",
    ),
    (
        "Weiter Schritt",
        [12],
        "(ÜF) Ab der 12. Stufe vermag sich der Mönch zwischen den Dimensionen zu bewegen, wie mit dem Zauber "
        "Dimensionstür. Um diese Fähigkeit zu nutzen, muss der Mönch zwei Ki-Punkte ausgeben. Als Zauberstufe für "
        "diesen Effekt zählt seine Mönchsstufe. Er kann keine anderen Wesen mit sich nehmen, wenn er diese "
        "Fähigkeit einsetzt.",
    ),
    (
        "Diamantseele",
        [13],
        "(AF) Ab der 13. Stufe erhält der Mönch eine Zauberresistenz von 10 + seiner aktuellen Mönchstufe. Um den "
        "Mönch mit einem Zauber zu betreffen, muss ein Zauberwirker mit einer Zauberstufenprobe (1W20 + "
        "Zauberstufe) die Zauberresistenz des Mönchs erreichen oder übertreffen.",
    ),
    (
        "Vibrierende Handfläche",
        [15],
        "(ÜF) Ab der 15. Stufe kann der Mönch den Körper eines Gegners in Vibration versetzen, die später dann, "
        "sollte es der Mönch wünschen, tödlich wirkt. Er kann die Vibrierende Handfläche ein Mal pro Tag einsetzen "
        "und muss dies ankündigen, bevor er den Angriffswurf durchführt. Kreaturen, die nicht von kritischen "
        "Treffern betroffen werden können, sind immun gegen diese Fähigkeit. Trifft der Mönch ansonsten mit seinem "
        "Angriff und verursacht er bei seinem Ziel Schaden, wurde die Fähigkeit erfolgreich eingesetzt. Nach dem "
        "Treffer kann der Mönch innerhalb einer Anzahl von Tagen, die seiner Mönchsstufe entspricht, versuchen, "
        "sein Opfer zu töten. Der Mönch muss sich den Tod des Ziels nur wünschen (als Freie Aktion). Gelingt dem "
        "Opfer kein Zähigkeitswurf (SG: 10 + ½ Stufe des Mönchs + dem WE-Modifikator des Mönchs), stirbt es. "
        "Gelingt der Rettungswurf, ist das Ziel nicht mehr in Gefahr durch diesen Einsatz der Fähigkeit. Ein Mönch "
        "kann nicht mehr als eine Vibrierende Handfläche zur gleichen Zeit aktiv haben. Setzt der Mönch seine "
        "Vibrierende Handfläche ein, während eine andere Anwendung der Fähigkeit noch wirkt, erlischt der frühere "
        "Effekt.",
    ),
    (
        "Zeitloser Körper",
        [17],
        "(AF) Mit dem Erreichen der 17. Stufe nimmt der Mönch keine Attributsverschlechterungen durch das Altern "
        "mehr hin und kann auch nicht auf magische Weise altern. Veränderungen, die er vorher erhalten hat, bleiben "
        "dadurch unverändert. Boni für das Alter erhält er weiterhin und er stirbt auch, wenn seine Zeit gekommen "
        "ist.",
    ),
    (
        "Sprache von Sonne und Mond",
        [17],
        "(AF) Ein Mönch der 17. oder höheren Stufe vermag, die Sprache einer jeden lebenden Kreatur zu sprechen.",
    ),
    (
        "Körper lösen",
        [19],
        "(ÜF) Mit dem Erreichen der 19. Stufe erhält der Mönch die Fähigkeit, sich für eine Minute in einen "
        "ätherischen Zustand zu versetzen, wie durch den Zauber Ätherische Gestalten. Diese Fähigkeit einzusetzen, "
        "entspricht einer Bewegungsaktion und kostet den Mönch drei Ki-Punkte. Diese Fähigkeit betrifft nur den "
        "Mönch selber und kann nicht eingesetzt werden, um jemand anderen ätherisch zu machen.",
    ),
    (
        "Perfektes Selbst",
        [20],
        "Auf der 20. Stufe wird der Mönch ein magisches Wesen. Ab dann zählt er für Zauber und magische Effekte "
        "nicht mehr als Humanoider (oder welcher Art der Mönch vorher war), sondern als Externar. Zudem erhält er "
        "eine Schadensreduzierung von 10/Chaos, mit der er vom Schaden jedes Angriffs, der nicht mit einer "
        "chaotischen Waffe oder mit einer natürlichen Waffe von einem Wesen mit der Unterkategorie chaotisch "
        "durchgeführt wurde, zehn Punkte abziehen kann. Anders als sonstige Externare kann der Mönch jedoch, "
        "ebenso wie es seiner bisherigen Art entspricht, von den Toten wiedererweckt werden.",
    ),
]

# Bonustalent's closed feat list (name, min_level beyond the slot's own
# granting level — None for the 7 feats available from the first slot).
BONUSTALENT_FEATS: list[tuple[str, int | None]] = [
    ("Ausweichen", None),
    ("Geschosse abwehren", None),
    ("Improvisierter Fernkampf", None),
    ("Improvisierter Nahkampf", None),
    ("Kampfreflexe", None),
    ("Skorpionstachel", None),
    ("Verbesserter Ringkampf", None),
    ("Gorgonenfaust", 6),
    ("Beweglichkeit", 6),
    ("Verbesserter Ansturm", 6),
    ("Verbessertes Entwaffnen", 6),
    ("Verbesserte Finte", 6),
    ("Verbessertes Zu-Fall-bringen", 6),
    ("Geschosse fangen", 10),
    ("Medusenzorn", 10),
    ("Tänzelnder Angriff", 10),
    ("Verbesserter Kritischer Treffer", 10),
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
    class_id = MOENCH_ID

    # ---- base_class_skills.json ----
    skills = load("base_skills.json")
    skill_id_by_name = {row["name"]: row["id"] for row in skills}
    skill_name_by_id = {row["id"]: row["name"] for row in skills}
    for name in CORRECT_CLASS_SKILLS:
        assert name in skill_id_by_name, f"missing skill: {name}"

    class_skills = load("base_class_skills.json")
    existing_moench_rows = [row for row in class_skills if row["base_class_id"] == class_id]
    existing_row_id_by_skill_name = {
        skill_name_by_id[row["skill_id"]]: row["id"]
        for row in existing_moench_rows
        if row["skill_id"] in skill_name_by_id
    }
    class_skills = [row for row in class_skills if row["base_class_id"] != class_id]
    for name in CORRECT_CLASS_SKILLS:
        row_id = existing_row_id_by_skill_name.get(name) or uid("moench-classskill", name)
        class_skills.append(
            {
                "id": row_id,
                "base_class_id": class_id,
                "skill_id": skill_id_by_name[name],
                "option_choice_id": None,
            }
        )
    save("base_class_skills.json", class_skills)

    # ---- base_class_abilities.json + base_class_ability_grants.json ----
    abilities = load("base_class_abilities.json")
    existing_ability_ids = {a["id"] for a in abilities}

    grants = load("base_class_ability_grants.json")
    own_grant_ids = {
        uid("moench-shell-grant", uid("moench-shell-ability", name), str(level))
        for name, levels, _description in CLASS_FEATURES
        for level in levels
    }
    grants = [g for g in grants if g["id"] not in own_grant_ids]

    ability_id_by_name: dict[str, str] = {}

    def add_ability(name: str, description: str) -> str:
        aid = uid("moench-shell-ability", name)
        ability_id_by_name[name] = aid
        if aid not in existing_ability_ids:
            abilities.append({"id": aid, "name": name, "description": description})
            existing_ability_ids.add(aid)
        return aid

    def add_grant(ability_id: str, level: int) -> None:
        grants.append(
            {
                "id": uid("moench-shell-grant", ability_id, str(level)),
                "base_class_id": class_id,
                "ability_id": ability_id,
                "option_choice_id": None,
                "level": level,
            }
        )

    for name, levels, description in CLASS_FEATURES:
        aid = add_ability(name, description)
        for level in levels:
            add_grant(aid, level)

    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)

    # ---- base_class_ability_granted_feats.json ----
    feats = load("base_feats.json")
    feat_id_by_name = {row["name"]: row["id"] for row in feats}

    granted_feats = load("base_class_ability_granted_feats.json")
    own_granted_feat_ids = {
        uid("moench-shell-grantedfeat", ability_id_by_name[ability_name], feat_id_by_name[feat_name])
        for ability_name, feat_name in (
            ("Waffenloser Schlag", "Verbesserter waffenloser Schlag"),
            ("Betäubender Schlag", "Betäubender Schlag"),
        )
    }
    granted_feats = [row for row in granted_feats if row["id"] not in own_granted_feat_ids]
    for ability_name, feat_name in (
        ("Waffenloser Schlag", "Verbesserter waffenloser Schlag"),
        ("Betäubender Schlag", "Betäubender Schlag"),
    ):
        ability_id = ability_id_by_name[ability_name]
        feat_id = feat_id_by_name[feat_name]
        granted_feats.append(
            {"id": uid("moench-shell-grantedfeat", ability_id, feat_id), "ability_id": ability_id, "feat_id": feat_id}
        )
    save("base_class_ability_granted_feats.json", granted_feats)

    # ---- base_class_ability_feat_options.json (Bonustalent) ----
    feat_options = load("base_class_ability_feat_options.json")
    bonustalent_id = ability_id_by_name["Bonustalent"]
    own_feat_option_ids = {
        uid("moench-bonustalent-option", bonustalent_id, feat_id_by_name[feat_name])
        for feat_name, _min_level in BONUSTALENT_FEATS
    }
    feat_options = [row for row in feat_options if row["id"] not in own_feat_option_ids]
    for feat_name, min_level in BONUSTALENT_FEATS:
        feat_id = feat_id_by_name[feat_name]
        feat_options.append(
            {
                "id": uid("moench-bonustalent-option", bonustalent_id, feat_id),
                "ability_id": bonustalent_id,
                "option_choice_id": None,
                "feat_type": None,
                "feat_id": feat_id,
                "min_level": min_level,
            }
        )
    save("base_class_ability_feat_options.json", feat_options)

    print("Class skills replaced:", len(CORRECT_CLASS_SKILLS))
    print("Class features imported:", len(CLASS_FEATURES))
    print("Total grants (this class):", len([g for g in grants if g["base_class_id"] == class_id]))
    print("Granted feats wired:", 2)
    print("Bonustalent feat options wired:", len(BONUSTALENT_FEATS))
    print("Bonustalent ability id (add to rules/feat_slots.py's BONUS_FEAT_SLOT_ABILITY_IDS):", bonustalent_id)
    print("Done.")


if __name__ == "__main__":
    main()
