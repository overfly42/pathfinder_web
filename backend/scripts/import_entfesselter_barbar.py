"""Import the Entfesselter Barbar (Unchained Barbarian) base class from
http://prd.5footstep.de/Alternativregeln/Klassen/Barbar into the seed JSON
files.

The page explicitly frames this as an "Alternativklasse" ("Ein Charakter
kann nicht über Stufen in beiden Klassen verfügen") - a full standalone
replacement for the Grundregelwerk Barbar, not an archetype of it (its rage
mechanic is fundamentally different: flat combat bonuses + temporary hit
points instead of ability-score bonuses, and most rage powers work
continuously while raging instead of once per rage). Modeled the same way
Mystiker was modeled relative to Kleriker: a second root `BaseClass` row
(`arch_class_of=None`), not `BaseClass.archetypes` of the existing Barbar
row - same hit die/BAB/saves/skill points, own id, own everything else.

The page names ~46 further rage powers as "reused unmodified" from two other
books, without repeating their rule text (each lives on its own PRD page):
32 from Expertenregeln (Benebelter Säufer, Beschütztes Leben, Bestientotem
and its two totem-chain tiers, Chaostotem's three tiers, Faustkämpfer's two
tiers, Flüssiger Mut, Geistertotem's three tiers, Grölender Säufer,
Scheusaltotem's three tiers, Schleudern's three tiers, Schleuder- und
Sturmangriff, Stichelnder Prahler, Temperamentvolles Ross, Torkelnder
Säufer, Überwältigender Vorstoß, Überwältigendes Niederrennen, Wildes
Reittier's two tiers, Wildes Trampeln's two tiers, Zauberstörer) plus 14
from Ausbauregeln II: Kampf (Beschütztes Leben (Mächtiges), Drachentotem and
its two related powers, Geisterwüter, Körperkeule, Schwarmtotem and its two
related powers, Urtümlicher Geruchssinn, Verzauberung zerschmettern,
Weltenschlangentotem and its two related powers) - see
http://prd.5footstep.de/Alternativregeln/Klassen/Barbar's own allow-list
text for the exact two name lists.

The 32 Expertenregeln ones are transcribed into `RAGE_POWERS` below
(2026-08-16, from
http://prd.5footstep.de/Expertenregeln/Klassen/Grundklassen/Barbar/Kampfrauschkraefte),
faithfully close to that source since the unchained page states they apply
"ohne Veränderungen" - unlike this file's own 54 unchained-specific powers,
which are deliberately reworded where Pathfinder Unchained's rage mechanic
changed the underlying math (see `import_barbar_rage_powers.py`'s docstring
for a worked example of that divergence).

What this script still does NOT attempt, and why (see todos.md for the full
writeup):
- The 14 Ausbauregeln II: Kampf rage powers (Drachentotem, Schwarmtotem,
  Weltenschlangentotem, ...) remain unimported - out of scope for the
  Expertenregeln pass above, same "bewusst nicht importiert - echte Grenze,
  keine Zeitfrage" boundary as Mystiker's ~90 unlinked domain spells.
- Nachtsicht's prerequisite ("Dämmersicht or Dunkelsicht racial trait, OR
  the Dämmersicht rage power") is a 3-way OR across two different domains
  (a `BaseRaceAbility` and a `BaseClassOptionChoice`) - `BaseClassOptionChoice.
  requires_choice_id` can only point at one other choice in the same class,
  so this can't be expressed today. Left with `requires_choice_id=None`;
  the racial-or-power alternative is still spelled out in the ability's own
  description text as flavor, just not enforced.
- Repeatable rage powers (Erhöhte Schadensreduzierung/Bodenbrecher Mächtiger/
  Schneller Fuß up to 3x, Energieresistenz once per energy type) get one
  `BaseClassOptionChoice` row each, same as every other rage power - nothing
  in the schema (or in Rogue's Trick, the closest precedent) models "may be
  picked more than once", so repeat selection isn't enforced.
- No handler-side computation for any of this (scaling numbers, rage-power
  activation, stance mutual exclusion, cross-class Reflexbewegung/
  Gefahreninstinkt stacking with Schurke's Reflexbewegung/Fallengespür) -
  composition only, per CLAUDE.md; catalog row + description text, same
  depth as every other class import.

Run with the project venv active (this only writes the fixture JSON files,
it doesn't touch the database - run the normal seed scripts afterward):
    cd backend && python scripts/import_entfesselter_barbar.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"

ID_NAMESPACE = uuid.UUID("9c1d2e3f-4a5b-4c6d-8e7f-0a1b2c3d4e5f")

ENTFESSELTER_BARBAR_ID = uuid.uuid5(ID_NAMESPACE, "entfesselter-barbar-class")

BASE_CLASS_SKILLS = [
    "Akrobatik",
    "Einschüchtern",
    "Handwerk",
    "Klettern",
    "Mit Tieren umgehen",
    "Reiten",
    "Schwimmen",
    "Überlebenskunst",
    "Wahrnehmung",
    "Wissen (Natur)",
]

KAMPFRAUSCHKRAFT_LEVELS = list(range(2, 21, 2))
GEFAHRENINSTINKT_LEVELS = [3, 6, 9, 12, 15, 18]
SCHADENSREDUZIERUNG_LEVELS = [7, 10, 13, 16, 19]

# (name, tag, min_level, requires-rage-power-name, description)
RAGE_POWERS: list[tuple[str, str, int | None, str | None, str]] = [
    (
        "Aberglaube",
        "AF",
        None,
        None,
        "Der Barbar erhält einen Kompetenzbonus von +2 auf Rettungswürfe, um Zaubern und "
        "zauberähnlichen Fähigkeiten zu widerstehen. Dieser Bonus steigt um 1 pro 4 Barbarenstufen, "
        "über welche der Charakter verfügt. Der Barbar kann kein williges Ziel für einen Zauberspruch "
        "sein und muss daher Rettungswürfe auch gegen Zauber seiner Verbündeten ablegen.",
    ),
    (
        "Animalische Wut",
        "AF",
        None,
        None,
        "Der Barbar erhält einen Bissangriff. Dies ist ein natürlicher Primärangriff, welcher 1W4 "
        "Schadenspunkte im Falle eines mittelgroßen Barbaren und 1W3 Schadenspunkte im Falle eines "
        "kleinen Barbaren verursacht (zuzüglich eines möglichen ST-Modifikators). Sollte der "
        "Bissangriff als Teil eines Vollen Angriffes eingesetzt werden, bei dem der Barbar auch "
        "hergestellte Waffen nutzt, erfolgt der Bissangriff mit dem vollen GAB des Barbaren -5 und es "
        "wird nur der halbe ST-Modifikator zum Schadenswurf addiert. Der Barbar kann im Ringkampf "
        "einen Bissangriff als Teil der Aktion zum Weiterführen oder Entkommen aus dem Ringkampf "
        "einsetzen. Gelingt der Bissangriff, erhält der Barbar bis zum Ende der Runde einen Bonus von "
        "+2 auf seine Kampfmanöver für Ringkampf gegen das Ziel.",
    ),
    (
        "Benebelter Säufer",
        "AF",
        None,
        None,
        "Nimmt der Barbar Alkohol zu sich, kann er einen neuen Rettungswurf gegen einen der folgenden "
        "Zustände ablegen, die ihn betreffen: Blind, Geblendet, Verwirrt, Taub, Erschöpft, Ermüdet, "
        "Verängstigt, Übelkeit, Panisch, Erschüttert, Kränkelnd. Bei Erfolg wird der Effekt für die Dauer des "
        "Kampfrausches unterdrückt. Auf dieselbe Weise kann er auch einen neuen Rettungswurf gegen eine "
        "Vergiftung ablegen. Ein gelungener Rettungswurf zählt als bestandener Rettungswurf; ein misslungener "
        "Rettungswurf hat keine weiteren Nachteile zur Folge.",
    ),
    (
        "Beschütztes Leben",
        "AF",
        None,
        None,
        "Sollte der Barbar unter 0 Trefferpunkte reduziert werden, wird 1 Schadenspunkt pro Barbarenstufe in "
        "nichttödlichen Schaden umgewandelt. Befindet sich der Barbar aufgrund von tödlichem Schaden im "
        "negativen Trefferpunktebereich, stabilisiert er sich automatisch.",
    ),
    (
        "Bestientotem, Schwächeres",
        "ÜF",
        None,
        None,
        "Der Barbar erhält zwei Klauenangriffe. Diese Angriffe sind Primärangriffe und werden mit dem vollen "
        "Grund-Angriffsbonus ausgeführt. Die Klauen verursachen 1W6 Punkte Hiebschaden (1W4 falls klein) "
        "zuzüglich des ST-Modifikators des Barbaren.",
    ),
    (
        "Bestientotem",
        "ÜF",
        6,
        "Bestientotem, Schwächeres",
        "Der Barbar erhält einen Bonus von +1 auf seine natürliche Rüstung. Dieser Bonus steigt um weitere +1 "
        "pro 4 Barbarenstufen.",
    ),
    (
        "Bestientotem, Mächtiges",
        "ÜF",
        10,
        "Bestientotem",
        "Der Barbar erhält die besondere Kraft Anspringen, wodurch er im Anschluss an einen Sturmangriff "
        "einen Vollen Angriff durchführen kann. Der Schaden seiner Klauen steigt auf 1W8 (1W6 falls klein) "
        "und sie verursachen bei einem Kritischen Treffer den dreifachen Schaden.",
    ),
    (
        "Blutender Schlag",
        "AF",
        8,
        "Machtvolle Kampfhaltung",
        "Solange der Barbar die Machtvolle Kampfhaltung einnimmt, kann er einen Angriff ausführen, der "
        "seine Gegner heftig bluten lässt. Er kann ein Mal pro Runde einen seiner Angriffe "
        "Blutungsschaden in Höhe des halben Bonusschadens verursachen lassen, den er durch Machtvolle "
        "Kampfhaltung erlangt. Dieser Blutungsschaden umgeht Schadensreduzierung, ist aber nicht mit "
        "sich selbst kumulativ.",
    ),
    (
        "Bodenbrecher",
        "AF",
        6,
        None,
        "Der Barbar kann als Volle Aktion den Boden um sich herum angreifen. Dieser Angriff trifft "
        "automatisch und verursacht normalen Schaden. Sollte der Barbar dabei die Härte des Bodens mit "
        "seinem Schaden übertreffen, werden das von ihm belegte und alle daran angrenzenden Felder zu "
        "Schwierigem Gelände. Alle anderen Kreaturen auf diesen Feldern müssen einen Reflexwurf gegen "
        "SG 15 ablegen, um nicht den Zustand Liegend zu erleiden.",
    ),
    (
        "Bodenbrecher, Mächtiger",
        "AF",
        8,
        "Bodenbrecher",
        "Wenn der Barbar die Kampfrauschkraft Bodenbrecher nutzt, kann er den Radius des Effektes um "
        "1,50 m erhöhen. Diese Kampfrauschkraft kann bis zu drei Mal gewählt werden, ihre Effekte sind "
        "kumulativ.",
    ),
    (
        "Chaostotem, Schwächeres",
        "ÜF",
        None,
        None,
        "Der Barbar erhält einen Ablenkungsbonus von +1 auf seine Rüstungsklasse gegen Angriffe "
        "rechtschaffener Kreaturen sowie einen Resistenzbonus von +1 auf Rettungswürfe gegen Verwirrung, "
        "Wahnsinn, Verwandlung und rechtschaffene Effekte. Dieser Bonus steigt um weitere +1 für jede weitere "
        "Kampfrauschkraft des Chaostotems, über die der Barbar verfügt.",
    ),
    (
        "Chaostotem",
        "ÜF",
        6,
        "Chaostotem, Schwächeres",
        "Die Gestalt des Barbaren wird von Chaos erfüllt. Er erhält einen Bonus von +4 auf Fertigkeitswürfe "
        "für Entfesselungskunst und eine Chance von 25%, den zusätzlichen Schaden durch Kritische Treffer und "
        "Hinterhältige Angriffe zu ignorieren.",
    ),
    (
        "Chaostotem, Mächtiges",
        "ÜF",
        10,
        "Chaostotem",
        "Der Barbar erhält Schadensreduzierung/Rechtschaffen in Höhe der halben Barbarenstufe. Seine Waffen "
        "und natürlichen Waffen gelten als chaotisch, um Schadensreduzierung zu überwinden.",
    ),
    (
        "Dämmersicht",
        "AF",
        None,
        None,
        "Die Sinne des Barbaren schärfen sich und er erhält Dämmersicht.",
    ),
    (
        "Einschüchterndes Niederstarren",
        "AF",
        None,
        None,
        "Der Barbar addiert seinen ST-Modifikator anstelle seines CH-Modifikators auf alle "
        "Fertigkeitswürfe für Einschüchtern, um einen Gegner zu demoralisieren. Er kann einen "
        "Einschüchterungsversuch gegen einen angrenzenden Gegner als Bewegungsaktion statt als "
        "Standard-Aktion ablegen, um diesen zu demoralisieren. Bei Erfolg erleidet der Gegner solange "
        "den Zustand Erschüttert, wie der gegenwärtige Kampfrausch des Barbaren anhält.",
    ),
    (
        "Elementare Kampfhaltung",
        "ÜF",
        4,
        None,
        "Wenn der Barbar diese Kampfhaltung einnimmt, wählt er eine Energieart (Elektrizität, Feuer, "
        "Kälte oder Säure). Seine Nahkampfangriffe verursachen 1 zusätzlichen Schadenspunkt der "
        "gewählten Energieart. Mit der 8. Stufe steigt dieser Schaden auf 1W6. Mit der 12. Stufe "
        "verursachen die Kritischen Treffer des Barbaren zusätzliche 1W10 Energieschadenspunkte "
        "derselben Art (2W10 bei Waffen die bei einem Kritischen Treffer dreifachen Schaden "
        "verursachen, bzw. 3W10 bei Waffen die bei einem Kritischen Treffer vierfachen Schaden "
        "verursachen). Dies ist eine Kampfrauschkraft der Kategorie Kampfhaltung.",
    ),
    (
        "Energieabsorption",
        "ÜF",
        12,
        "Energieresistenz",
        "Der Barbar kann ein Mal am Tag die Energie eines einzelnen Angriffes absorbieren, sofern er "
        "der Energieart mittels seiner Kampfrauschkraft Energieresistenz widersteht. Er nimmt keinen "
        "Schaden durch den Angriff und legt auch keinen Rettungswurf ab. Stattdessen erhöht er die "
        "Anzahl der temporären Trefferpunkte, die er beim Beginn des Kampfrauschs erlangt, um die "
        "Hälfte des Schadens, den er ohne die Energieresistenz erlitten hätte. Mit der 16. Stufe kann "
        "der Barbar ein Mal vor Ende seines Kampfrausches die gespeicherte Energie als Odemwaffe in "
        "einer 18 m-Linie oder einem 9 m-Kegel freisetzen. Diese Odemwaffe verursacht Schaden in Höhe "
        "der vollen Schadensmenge, welche der Barbar durch den absorbierten Effekt erlitten hätte "
        "(REF, SG 10 + ½ Barbarenstufe + KO-Modifikator des Barbaren, halbiert). Der Barbar behält die "
        "durch diese Fähigkeit erlangten temporären Trefferpunkte auch nach Entfesseln der Odemwaffe.",
    ),
    (
        "Energieresistenz",
        "AF",
        None,
        None,
        "Der Barbar erhält Resistenz gegen eine Energieart (Elektrizität, Feuer, Kälte, Säure oder "
        "Schall) in Höhe seiner halben Barbarenstufe (Minimum 1). Beginnend mit der 8. Stufe erhält er "
        "eine begrenzte Immunität gegen dieselbe Energieart (wie Schutz vor Energien). Er kann 2 "
        "Schadenspunkte pro Stufe absorbieren und wendet zunächst immer seine Energieresistenz zuerst "
        "an. Die Energieart wird mit Wahl dieser Kampfrauschkraft ausgewählt und kann später nicht "
        "mehr geändert werden. Diese Kampfrauschkraft kann mehrfach gewählt werden, muss aber jedes "
        "Mal einer anderen Energieart zugeordnet werden.",
    ),
    (
        "Erhöhte Schadensreduzierung",
        "AF",
        8,
        None,
        "Die Schadenreduzierung des Barbaren steigt im Kampfrausch um 2/-. Ein Barbar kann diese Kraft "
        "bis zu drei Mal wählen; die Wirkung ist kumulativ.",
    ),
    (
        "Erneuerte Gesundheit",
        "AF",
        None,
        None,
        "Der Barbar ignoriert pro 2 Barbarenstufen den Effekt von 1 Punkt Attributsschaden oder malus "
        "(maximal 10). Mit der 6. Stufe kann er ferner 1 negative Stufe pro 4 Barbarenstufen "
        "ignorieren. Sobald der Kampfrausch endet, erleidet er jedoch die vollständigen Effekte von "
        "Attributsmali, -schäden oder negativen Stufen.",
    ),
    (
        "Erneuerte Lebenskraft",
        "AF",
        4,
        None,
        "Der Barbar kann bei sich selbst als Standard-Aktion 1W8 + KO-Modifikator Trefferpunkte "
        "heilen. Pro jeweils 4 Stufen, die der Barbar jenseits der 4. Barbarenstufe besitzt, heilt er "
        "bei sich weitere 1W8 TP (maximal 5W8 mit der 20. Stufe). Diese Kampfrauschkraft kann nur "
        "einmal am Tag eingesetzt werden.",
    ),
    (
        "Faustkämpfer",
        "AF",
        None,
        None,
        "Der Barbar wird behandelt, als besäße er das Talent Verbesserter waffenloser Schlag. Besitzt er "
        "dieses Talent bereits, verursachen seine waffenlosen Schläge 1W6 Schadenspunkte (1W4 falls klein).",
    ),
    (
        "Faustkämpfer, Mächtiger",
        "AF",
        None,
        "Faustkämpfer",
        "Der Barbar wird behandelt, als besäße er das Talent Kampf mit zwei Waffen, wenn er waffenlose "
        "Angriffe ausführt.",
    ),
    (
        "Fleischwunde",
        "AF",
        10,
        None,
        "Der Barbar kann es ein Mal am Tag vereiteln, durch einen Angriff schweren Schaden zu "
        "erleiden, indem er einen Zähigkeitswurf ablegt, dessen SG dem Schaden entspricht, welchen er "
        "durch den Angriff erleiden würde. Bei Erfolg erleidet er keinen Schaden; misslingt der "
        "Rettungswurf, erleidet er durch den Angriff halben Schaden und dieser Schaden wird zu "
        "Nichttödlichem Schaden konvertiert. Der Barbar muss sich für den Einsatz dieser Fähigkeit "
        "entscheiden, nachdem der Angriffswurf erfolgt ist, aber bevor der Schaden ausgewürfelt wurde.",
    ),
    (
        "Flüssiger Mut",
        "AF",
        None,
        None,
        "Der Barbar kann seinen Moralbonus auf Rettungswürfe gegen geistesbeeinflussende Effekte um +1 für "
        "jedes im Kampfrausch konsumierte alkoholische Getränk erhöhen (maximal ein Getränk pro 4 "
        "Barbarenstufen).",
    ),
    (
        "Furchtlose Wut",
        "AF",
        12,
        None,
        "Der Barbar ist gegen die Zustände Erschüttert und Verängstigt (nicht aber gegen Panisch) "
        "immun.",
    ),
    (
        "Geistertotem, Schwächeres",
        "ÜF",
        None,
        None,
        "Der Barbar wird von Geisterfetzen umgeben, die seine Feinde verfolgen. Diese Fetzen können pro Runde "
        "einen Hieb-Angriff mit dem vollen Angriffsbonus des Barbaren zuzüglich seines CH-Modifikators "
        "ausführen. Dieser verursacht 1W4 Punkte Schaden durch negative Energie zuzüglich des CH-Modifikators "
        "des Barbaren.",
    ),
    (
        "Geistertotem",
        "ÜF",
        6,
        "Geistertotem, Schwächeres",
        "Die den Barbaren umgebenden Geisterfetzen erschweren es Feinden, ihn zu treffen. Sie gewähren ihm "
        "eine Fehlschlagschance von 20% gegen Fernkampfangriffe sowie gegen Nahkampfangriffe von Kreaturen, "
        "die sich nicht auf angrenzenden Feldern befinden (üblicherweise Angriffe mit Reichweite).",
    ),
    (
        "Geistertotem, Mächtiges",
        "ÜF",
        10,
        "Geistertotem",
        "Die Geisterfetzen des Barbaren werden allen Gegnern auf angrenzenden Feldern gefährlich. Lebende "
        "Feinde, die sich zu Beginn seines Zuges auf einem angrenzenden Feld befinden, nehmen 1W8 Punkte "
        "Schaden durch negative Energie. Zudem können die Geisterfetzen nun auch Gegner bis zu 4,50 m "
        "Entfernung angreifen; ihr Hieb-Angriff verursacht dabei 1W6 Punkte Schaden durch negative Energie.",
    ),
    (
        "Geruchssinn",
        "AF",
        None,
        None,
        "Der Barbar erhält die Fähigkeit Geruchssinn und kann diese nutzen, um unsichtbare oder "
        "anderweitig seiner Sicht entzogene Feinde aufzuspüren.",
    ),
    (
        "Geschärfte Treffsicherheit",
        "AF",
        8,
        "Zielsichere Kampfhaltung",
        "Während der Barbar seine Zielsichere Kampfhaltung aufrechterhält, ignoriert er die "
        "Fehlschlagschance für Tarnung und behandelt Vollständige Tarnung als normale Tarnung. Er "
        "ignoriert ferner alle Mali durch Deckung mit Ausnahme von jenen, die aus Vollständiger "
        "Deckung resultieren.",
    ),
    (
        "Geweckte Wut",
        "AF",
        None,
        None,
        "Der Barbar kann sich sogar dann in einen Kampfrausch versetzen, wenn er erschöpft ist. Sollte "
        "er den Zustand Erschöpft besitzen, wenn er sich in Kampfrausch versetzt, verliert er diesen "
        "Zustand, erhält aber keine temporären Trefferpunkte. Sobald dieser Kampfrausch dann endet, "
        "erleidet der Barbar für 10 Minuten den Zustand Entkräftet.",
    ),
    (
        "Grölender Säufer",
        "AF",
        None,
        None,
        "Der Barbar erhält einen Moralbonus von +1 auf Fertigkeitswürfe für Einschüchtern sowie auf den SG "
        "der Rettungswürfe gegen von ihm hervorgerufene Furchteffekte für jedes im Kampfrausch konsumierte "
        "alkoholische Getränk, bis zu einem Maximum von +1 pro 4 Barbarenstufen.",
    ),
    (
        "Hexenjäger",
        "AF",
        None,
        "Aberglaube",
        "Der Barbar erhält einen Bonus von +1 auf Schadenswürfe gegen Kreaturen, welche Zauber wirken "
        "können oder über zauberähnliche Fähigkeiten verfügen. Dieser Bonus steigt um 1 pro 4 "
        "Barbarenstufen, über welche der Charakter verfügt. Sollte der Barbar zudem einen Kritischen "
        "Treffer gegen eine Kreatur bestätigen, die unter einem anhaltenden, vorteilhaften Effekt "
        "steht, wird dieser Effekt für 1 Runde unterdrückt (sollte die Kreatur unter mehreren "
        "passenden Effekten stehen, wird einer davon zufällig ausgewählt).",
    ),
    (
        "Hindurchstürmen",
        "AF",
        None,
        None,
        "Wenn der Barbar einen Sturmangriff ausführt, kann er einen seiner Verbündeten aus dem Weg "
        "schieben. Solange der Verbündete sich nicht angrenzend zum Ziel des Sturmangriffes befindet, "
        "zählt er als nicht im Weg befindlich. Dies verändert nicht die Position des Verbündeten, "
        "sondern erlaubt dem Barbaren lediglich, an ihm vorbei zu kommen.",
    ),
    (
        "Hindurchstürmen, Mächtiges",
        "AF",
        8,
        "Hindurchstürmen",
        "Dies funktioniert wie Hindurchstürmen, gilt aber für eine beliebige Anzahl von Verbündeten, "
        "sofern sie sich nicht zum Ziel des Sturmangriffes angrenzend befinden.",
    ),
    (
        "Innere Zähigkeit",
        "AF",
        8,
        None,
        "Der Barbar ist gegen die Zustände Kränkelnd und Übelkeit immun.",
    ),
    (
        "Kampfschrei",
        "AF",
        8,
        "Einschüchterndes Niederstarren",
        "Der Barbar kann als Standard-Aktion einen furchteinflößenden Kampfschrei ausstoßen. Alle "
        "Feinde innerhalb von 9 m, welche bereits durch den Barbaren den Zustand Erschüttert erhalten "
        "haben (dies geschieht meist im Rahmen von Einschüchtern), müssen einen Willenswurf gegen SG "
        "10 + ½ Barbarenstufe + ST-Modifikator ablegen, um nicht für 1W4+1 Runden den Zustand Panisch "
        "zu erhalten. Im Anschluss ist ein Gegner unabhängig vom Ausgang seines Willenswurfes gegen "
        "diese Fähigkeit für 24 Stunden immun.",
    ),
    (
        "Kein Entkommen",
        "AF",
        None,
        None,
        "Der Barbar ist in der Lage dazu, sich als Augenblickliche Aktion bis zum Doppelten seiner "
        "Bewegungsrate zu bewegen. Der Barbar kann diese Fähigkeit nur dann einsetzen, wenn ein "
        "angrenzender Gegner sich mit einer Rückzugsaktion von ihm entfernt. Der Barbar muss die "
        "Bewegung zu dem Feind angrenzend beenden, der sich zurückgezogen hat. Die Bewegung des "
        "Barbaren verursacht normal Gelegenheitsangriffe.",
    ),
    (
        "Kraftvolle Kampfhaltung",
        "AF",
        None,
        None,
        "Der Barbar kann auf unglaubliche Kraftreserven zurückgreifen. Er erhält einen "
        "Kompetenzbonus von +1 auf Kampfmanöverwürfe und seine KMV. Diese Boni steigen um 1 pro 4 "
        "Barbarenstufen, über welche der Charakter verfügt. Ferner erhält er einen Kompetenzbonus von "
        "+8 auf Stärkewürfe, um Gegenstände zu stemmen, zu schieben, zu verbiegen, zu zerbrechen oder "
        "zu zerschmettern (dieser Bonus kommt nicht bei Kampfmanövern zur Anwendung). Dies ist eine "
        "Kampfrauschkraft der Kategorie Kampfhaltung.",
    ),
    (
        "Kritische Stellen schützen",
        "AF",
        8,
        "Wachsame Kampfhaltung",
        "Während der Barbar seine Wachsame Kampfhaltung einnimmt, erhält er gegen Kritische "
        "Bestätigungswürfe einen zusätzlichen Ausweichbonus von +4 auf seine RK.",
    ),
    (
        "Mächtiger Schlag",
        "AF",
        12,
        None,
        "Der Barbar kann einen Kritischen Treffer automatisch bestätigen. Diese Kraft wird als "
        "Augenblickliche Aktion genutzt, sobald der Barbar bei einem Angriff eine Kritische Bedrohung "
        "erzielt. Sie kann nur ein Mal am Tag eingesetzt werden.",
    ),
    (
        "Machtvolle Kampfhaltung",
        "AF",
        None,
        None,
        "Der Barbar kann sich auf seine Wildheit konzentrieren. Er erhält einen Bonus von +1 auf "
        "Nahkampf- und Wurfwaffenschadenswürfe. Dieser Bonus steigt um 1 pro 4 Barbarenstufen, über "
        "welche der Charakter verfügt. Dies ist eine Kampfrauschkraft der Kategorie Kampfhaltung.",
    ),
    (
        "Magiefresser",
        "ÜF",
        10,
        "Aberglaube",
        "Wenn dem Barbar ein Rettungswurf gelingt, um einem Zauber, einer übernatürlichen oder einer "
        "zauberähnlichen Fähigkeit zu widerstehen, erhält er temporäre Trefferpunkte in Höhe des "
        "Zaubergrades des Effektes (im Falle von Zaubern und zauberähnlichen Fähigkeiten) oder in Höhe "
        "des halben HG der Quelle (im Falle von übernatürlichen Fähigkeiten). Diese temporären "
        "Trefferpunkte verschwinden mit dem Ende des Kampfrausches; sie sind mit jenen temporären "
        "Trefferpunkten kumulativ, welche der Barbar durch seinen Kampfrausch erlangt, nicht aber mit "
        "anderen temporären Trefferpunkten, die er durch diese Fähigkeit erhält.",
    ),
    (
        "Nachtsicht",
        "AF",
        None,
        None,
        "Die Sinne des Barbaren werden außergewöhnlich scharf und er erhält Dunkelsicht 18 m. Sollte "
        "er bereits über Dunkelsicht verfügen, steigt deren Reichweite um 18 m. Um diese Kraft wählen "
        "zu können, muss der Barbar entweder das Volksmerkmal Dämmersicht oder Dunkelsicht besitzen, "
        "oder aber über die Kampfrauschkraft Dämmersicht verfügen. (Diese Voraussetzung ist eine OR-"
        "Verknüpfung aus einem Volksmerkmal und einer Kampfrauschkraft und wird aktuell nicht "
        "erzwungen - siehe todos.md.)",
    ),
    (
        "Niederschlagen",
        "AF",
        None,
        None,
        "Der Barbar kann ein Mal pro Runde anstelle eines Nahkampfangriffes einen Kampfmanöverwurf für "
        "Ansturm mit seinem vollen KMV ausführen, egal welchen Angriff er dadurch ersetzt. Bei Erfolg "
        "erleidet das Ziel Schaden in Höhe des ST-Bonus des Barbaren und wird wie normal "
        "zurückgestoßen. Der Barbar bewegt sich nicht mit seinem Ziel mit. Dieser Ansturm provoziert "
        "keine Gelegenheitsangriffe.",
    ),
    (
        "Perfekte Klarheit",
        "AF",
        None,
        "Ruhige Kampfhaltung",
        "Während der Barbar sich in der Ruhigen Kampfhaltung befindet, kann er bei jeder "
        "Fehlschlagschance und jedem Willenswurf zum Anzweifeln von Illusionen zwei Mal würfeln und "
        "das für ihn bessere Ergebnis wählen.",
    ),
    (
        "Reflexartiges Ausweichen",
        "AF",
        6,
        "Wachsame Kampfhaltung",
        "Während der Barbar sich in der Wachsamen Kampfhaltung befindet, kann er seinen "
        "Ausweichbonus auf seine RK zusätzlich als Bonus auf Reflexwürfe addieren.",
    ),
    (
        "Regenerative Kampfhaltung",
        "AF",
        4,
        None,
        "Der Barbar erlangt beständig Gesundheit zurück. Zu Beginn seines Zuges erhält er 1 temporären "
        "Trefferpunkt pro 4 Stufen als Barbar zurück (maximal 5 temporäre TP pro Runde). Er kann auf "
        "diese Weise nicht mehr temporäre Trefferpunkte zurückerlangen, als die Anzahl, welche er "
        "durch den Kampfrausch erhält. Dies ist eine Kampfrauschkraft der Kategorie Kampfhaltung.",
    ),
    (
        "Ruhige Kampfhaltung",
        "AF",
        None,
        None,
        "Der Barbar kann sich in einen Zustand der inneren Ruhe versetzen. Während er diese "
        "Kampfhaltung nutzt, erhält er aus seinem Kampfrausch neben den temporären Trefferpunkten "
        "keine Vorteile, aber auch keine Nachteile (d.h. auch keinen Malus auf seine RK und keine "
        "Einschränkungen hinsichtlich der ihm möglichen Handlungen). Er verbraucht aber weiterhin "
        "Runden an Kampfrausch. Dies ist eine Kampfrauschkraft der Kategorie Kampfhaltung.",
    ),
    (
        "Scheusaltotem, Schwächeres",
        "ÜF",
        None,
        None,
        "Dem Barbaren wachsen ein Paar großer Hörner, mit denen er einen Durchbohren-Angriff ausführen kann. "
        "Dies ist ein Primärangriff, außer der Barbar greift zusätzlich mit Waffen an – dann ist es ein "
        "Sekundärangriff mit vollem Grund-Angriffsbonus (-5 als Sekundärangriff). Das Durchbohren verursacht "
        "1W8 Punkte Stichschaden (1W6 falls klein) zuzüglich des ST-Modifikators des Barbaren (halber ST- "
        "Modifikator bei einem Sekundärangriff).",
    ),
    (
        "Scheusaltotem",
        "ÜF",
        6,
        "Scheusaltotem, Schwächeres",
        "Dutzende gefährlicher Stacheln wachsen aus dem Körper des Barbaren. Jeder, der ihn mit einer "
        "Nahkampfwaffe, einem waffenlosen Schlag oder einer natürlichen Waffe angreift, nimmt 1W6 Punkte "
        "Stichschaden.",
    ),
    (
        "Scheusaltotem, Mächtiges",
        "ÜF",
        10,
        "Scheusaltotem",
        "Der Barbar ist von einer Aura der Bedrohung umgeben. Gute Kreaturen auf angrenzenden Feldern sind "
        "erschüttert und nehmen zu Beginn seines Zuges 2W6 Punkte Hiebschaden, da sich dutzende kleiner "
        "Schnittwunden auf ihrem Körper öffnen. Neutrale Kreaturen auf angrenzenden Feldern sind erschüttert, "
        "nehmen aber keinen Schaden. Böse Kreaturen sind nicht betroffen.",
    ),
    (
        "Schleudern, Schwächeres",
        "AF",
        None,
        None,
        "Der Barbar kann als Volle Aktion mit beiden Händen einen Gegenstand hochheben und schleudern, der "
        "eine Größenkategorie kleiner ist als er selbst, oder mit einer Hand einen Gegenstand, der zwei "
        "Größenkategorien kleiner ist. Der Gegenstand zählt als improvisierte Waffe mit einer Grundreichweite "
        "von 3 m und verursacht Schaden wie ein fallender Gegenstand zuzüglich des ST-Modifikators des "
        "Barbaren (halbiert, sollte der Gegenstand nicht aus Stein, Metall oder ähnlichem Material bestehen). "
        "Dies ist ein Fernkampf-Berührungsangriff; dem Ziel steht ein Reflexwurf gegen SG 10 + ½ "
        "Barbarenstufe + ST-Modifikator des Barbaren zu, um den Schaden zu halbieren. Der Barbar kann das "
        "Talent Heftiger Angriff in Verbindung mit dieser Kraft wie bei einer Einhand- oder Zweihandwaffe "
        "einsetzen.",
    ),
    (
        "Schleudern",
        "AF",
        8,
        "Schleudern, Schwächeres",
        "Wie Schwächeres Schleudern, jedoch kann der Barbar die Grundreichweite um 6 m erhöhen oder einen "
        "Gegenstand der nächsten Größenkategorie schleudern.",
    ),
    (
        "Schleudern, Mächtiges",
        "AF",
        12,
        "Schleudern",
        "Wie Schleudern, jedoch kann der Barbar die Grundreichweite um 9 m erhöhen oder einen Gegenstand der "
        "übernächsten Größenkategorie schleudern.",
    ),
    (
        "Schleuder- und Sturmangriff",
        "AF",
        6,
        "Schleudern, Schwächeres",
        "Bei einem Sturmangriff kann der Barbar im Laufen eine zusätzliche Waffe ziehen und werfen. Der "
        "übliche Angriffsbonus von +2 für den Sturmangriff gilt sowohl für den Wurf als auch für den "
        "abschließenden Nahkampfangriff. Der Barbar muss sich mindestens 3 m bewegt haben, bevor er die "
        "Wurfwaffe einsetzen kann, und weitere 3 m, bevor er den abschließenden Nahkampfangriff ausführt. Er "
        "muss zu Beginn des Sturmangriffes eine Wurfwaffe in der Hand oder eine Hand frei haben.",
    ),
    (
        "Schmähende Kampfhaltung",
        "AF",
        12,
        None,
        "Der Barbar kann seine Verteidigung vernachlässigen und sich zugleich darauf vorbereiten, "
        "verheerende Gegenangriffe zu führen. Gegner erhalten einen Bonus von +4 auf Angriffs- und "
        "Schadenswürfe gegen den Barbaren, während er diese Kampfhaltung nutzt. Allerdings provoziert "
        "jeder gegen den Barbaren geführte Angriff einen Gelegenheitsangriff durch diesen. Dies ist "
        "eine Kampfrauschkraft der Kategorie Kampfhaltung.",
    ),
    (
        "Schnelle Reflexe",
        "AF",
        None,
        None,
        "Der Barbar kann einen zusätzlichen Gelegenheitsangriff pro Runde ausführen.",
    ),
    (
        "Schneller Fuß",
        "AF",
        None,
        None,
        "Der Barbar erhält einen Verbesserungsbonus von 3 m auf seine Bewegungsrate an Land. Ein "
        "Barbar kann diese Kampfrauschkraft bis zu drei Mal wählen, die Effekte sind kumulativ.",
    ),
    (
        "Sprinten",
        "AF",
        4,
        "Schneller Fuß",
        "Der Barbar addiert seine halbe Bewegungsrate auf die Entfernung, die er im Rennen oder bei "
        "einem Sturmangriff zurücklegen kann.",
    ),
    (
        "Starker Geist",
        "AF",
        8,
        None,
        "Der Barbar kann einen misslungenen Willenswurf am Ende seines nächsten Zuges gegen denselben "
        "SG wiederholen. Sollte dieser zweite Rettungswurf gelingen, wird der Barbar so behandelt, als "
        "sei ihm der erste Rettungswurf bereits gelungen, wodurch der Effekt aufgehoben oder reduziert "
        "wird, je nachdem wie es der Zauber oder Effekt bestimmt.",
    ),
    (
        "Stichelnder Prahler",
        "AF",
        6,
        None,
        "Der Barbar kann versuchen, eine Kreatur mit einem Fertigkeitswurf für Einschüchtern zu "
        "demoralisieren, um sie zum Angriff auf sich zu provozieren. Bei Erfolg ist das Ziel erschüttert, "
        "solange es den Barbaren sehen kann und dieser sich im Kampfrausch befindet, oder bis es ihn im "
        "Nahkampf angreift. Der Barbar erhält einen Situationsbonus von +2 auf den Wurf für jedes im "
        "Kampfrausch konsumierte alkoholische Getränk. Dies ist ein sprachabhängiger, geistesbeeinflussender "
        "Effekt mit hörbaren Komponenten.",
    ),
    (
        "Temperamentvolles Ross",
        "ÜF",
        6,
        "Wildes Reittier",
        "Ist der Barbar beritten, erhält sein Reittier Schadensreduzierung/Magie in Höhe der halben "
        "Barbarenstufe. Die natürlichen Waffen des Reittieres gelten als magisch, um Schadensreduzierung zu "
        "überwinden.",
    ),
    (
        "Torkelnder Säufer",
        "AF",
        None,
        None,
        "Der Barbar erhält einen Ausweichbonus von +1 auf seine Rüstungsklasse für jedes im Kampfrausch "
        "konsumierte alkoholische Getränk, bis zu einem Maximum von +1 pro 4 Barbarenstufen.",
    ),
    (
        "Tödliche Treffsicherheit",
        "AF",
        4,
        "Zielsichere Kampfhaltung",
        "Sollte der Barbar in seiner Zielsicheren Kampfhaltung eine Kritische Bedrohung erzielen, "
        "addiert er den doppelten Bonus, welchen er durch seine Haltung erhält, auf den "
        "Bestätigungswurf.",
    ),
    (
        "Unerwarteter Schlag",
        "AF",
        8,
        None,
        "Der Barbar kann einen Gelegenheitsangriff gegen einen Gegner ausführen, welcher ein vom "
        "Barbaren bedrohtes Feld betritt. Dabei ist es egal, ob die Bewegung normalerweise einen "
        "Gelegenheitsangriff provozieren würde. Der Barbar kann diese Fähigkeit nur dann nutzen, wenn "
        "sich auf den übrigen von ihm bedrohten Feldern keine Gegner befinden.",
    ),
    (
        "Verkrüppelnder Schlag",
        "AF",
        8,
        None,
        "Ein Mal am Tag kann der Barbar, wenn ihm ein Angriff gelingt, dem Ziel 1 Punkt ST- oder "
        "GE-Schaden zufügen. Dieser Schaden steigt um 1 Punkt pro 4 Barbarenstufen, über die der "
        "Charakter verfügt.",
    ),
    (
        "Vernichtende Treffsicherheit",
        "AF",
        16,
        "Zielsichere Kampfhaltung",
        "Während der Barbar sich in seiner Zielsicheren Kampfhaltung befindet, steigt der "
        "Schadensmultiplikator für Kritische Treffer um 1 (ein Multiplikator von x2 wird zu x3 usw.).",
    ),
    (
        "Wachsame Kampfhaltung",
        "AF",
        None,
        None,
        "Der Barbar kann eine defensive Haltung einnehmen. Diese verleiht ihm für die Dauer seines "
        "aktuellen Kampfrausches einen Ausweichbonus von +1 auf seine Rüstungsklasse. Dieser Bonus "
        "steigt um 1 pro 4 Barbarenstufen, über welche der Charakter verfügt. Dies ist eine "
        "Kampfrauschkraft der Kategorie Kampfhaltung.",
    ),
    (
        "Waghalsige Kampfhaltung",
        "AF",
        None,
        None,
        "Der Barbar kann schwungvoll angreifen, vernachlässigt dabei aber seine Verteidigung. Er "
        "erhält einen Bonus von +1 auf Angriffswürfe und einen Malus von -1 auf seine RK. Dieser Bonus "
        "und dieser Malus steigen um 1 pro 4 Barbarenstufen, über welche der Charakter verfügt. Dies "
        "ist eine Kampfrauschkraft der Kategorie Kampfhaltung.",
    ),
    (
        "Wildes Reittier",
        "AF",
        None,
        None,
        "Reitet der Barbar, erhält sein Reittier die Vorteile eines Kampfrausches. Dies gilt, solange der "
        "Barbar beritten ist oder sich auf einem zu seinem Reittier angrenzenden Feld befindet. Der "
        "Kampfrausch des Reittieres kostet den Barbaren für jede Runde, in der es davon profitiert, 1 "
        "zusätzliche Runde seines eigenen Kampfrausches; er kann sich entscheiden, diese Kosten nicht zu "
        "zahlen, wodurch das Reittier keinen Kampfrausch erhält.",
    ),
    (
        "Wildes Reittier, Mächtiges",
        "AF",
        8,
        "Wildes Reittier",
        "Reitet der Barbar, erhält sein Reittier für die Dauer des Kampfrausches zusätzlich alle Vorteile "
        "jeder dauerhaft wirkenden Kampfrauschkraft des Barbaren. Kampfrauschkräfte, die zur Aktivierung eine "
        "Aktion erfordern (auch Freie Aktionen), gewähren dem Reittier ihre Vorteile dagegen nicht.",
    ),
    (
        "Wildes Trampeln",
        "AF",
        8,
        "Wildes Reittier",
        "Reitet der Barbar, erhält sein Reittier einen Trampelangriff. Dieser verursacht 1W8 Schadenspunkte "
        "bei einem mittelgroßen, 2W6 bei einem großen und 2W8 bei einem riesigen Reittier, jeweils zuzüglich "
        "des 1½-fachen ST-Modifikators des Reittieres. Ein erfolgreicher Reflexwurf gegen SG 10 + ½ "
        "Barbarenstufe + ST-Modifikator des Reittieres halbiert den Schaden. Kreaturen im Weg des Reittieres "
        "oder die vom Reittier durchquerte Felder bedrohen, können einen Gelegenheitsangriff entweder gegen "
        "das Reittier oder gegen den Barbaren ausführen, aber nicht gegen beide.",
    ),
    (
        "Wildes Trampeln, Mächtiges",
        "AF",
        12,
        "Wildes Trampeln",
        "Das Reittier des Barbaren kann mit seinem Trampelangriff auch Kreaturen bis zu seiner eigenen Größe "
        "betreffen. Zudem kann es als Freie Aktion das Kampfmanöver Überrennen gegen eine Kreatur ausführen, "
        "die ihren Reflexwurf gegen das Trampeln nicht bestanden hat oder darauf verzichtet hat, um "
        "stattdessen einen Gelegenheitsangriff auszuführen.",
    ),
    (
        "Wildheit inspirieren",
        "AF",
        None,
        "Waghalsige Kampfhaltung",
        "Während der Barbar seine Waghalsige Kampfhaltung innehat, verleiht er allen willigen "
        "Verbündeten innerhalb von 9 m Entfernung den Boni und den Malus dieser Haltung.",
    ),
    (
        "Wuterfüllter Sprung",
        "AF",
        None,
        None,
        "Wenn der Barbar einen Fertigkeitswurf für Akrobatik zum Springen ausführt, wird er stets so "
        "behandelt, als hätte er Anlauf genommen. Ferner erhält er einen Bonus von +8 auf "
        "Fertigkeitswürfe für Akrobatik zum Springen. Sollte sein Wurf scheitern, halbiert er die "
        "gestürzte Entfernung hinsichtlich der Berechnung des anfallenden Sturzschadens.",
    ),
    (
        "Wuterfülltes Klettern",
        "AF",
        None,
        None,
        "Der Barbar erhält eine Bewegungsrate für Klettern in Höhe seiner halben Bewegungsrate an Land "
        "(rechne zuvor den Effekt seines Klassenmerkmales Schnelle Bewegung hinzu). Er kann diese "
        "Bewegungsrate für Klettern nicht nutzen, um an Oberflächen zu klettern, deren SG jenseits von "
        "20 liegt. Er erhält ferner einen Verbesserungsbonus von +8 auf Fertigkeitswürfe für Klettern.",
    ),
    (
        "Wuterfülltes Schwimmen",
        "AF",
        None,
        None,
        "Der Barbar erhält eine Bewegungsrate für Schwimmen in Höhe seiner halben Bewegungsrate an "
        "Land (rechne zuvor den Effekt seines Klassenmerkmales Schnelle Bewegung hinzu). Er erhält "
        "ferner einen Verbesserungsbonus von +8 auf Fertigkeitswürfe für Schwimmen.",
    ),
    (
        "Zauberstörer",
        "AF",
        8,
        "Aberglaube",
        "Der Barbar erhält für die Dauer des Kampfrausches das Bonustalent Zauberstörer.",
    ),
    (
        "Zeichen der Geister",
        "ÜF",
        None,
        None,
        "Der Barbar wurde von den Geistern in Form einer beeindruckenden Tätowierung, Narbe oder eines "
        "Geburtsmales gezeichnet. Er kann die Gunst der Geister ein Mal am Tag als Schnelle Aktion "
        "nutzen, um einen gerade ausgeführten W20-Wurf um +1W6 zu erhöhen. Dieser Bonus steigt um 1 "
        "pro 4 Barbarenstufen, über die der Charakter verfügt. Er kann diese Fähigkeit nutzen, wenn "
        "das Ergebnis des W20-Wurfes schon feststeht.",
    ),
    (
        "Zertrümmerer",
        "AF",
        None,
        None,
        "Wenn der Barbar ein Kampfmanöver für Gegenstand zerschmettern oder einen Angriff gegen einen "
        "Gegenstand ausführt, den niemand am Leib oder in Händen trägt, ignoriert er 1 Punkt an Härte "
        "des Gegenstandes pro Barbarenstufe, über die er verfügt.",
    ),
    (
        "Zielsichere Kampfhaltung",
        "AF",
        None,
        None,
        "Der Barbar kann genaue Schläge landen. Er erhält einen Kompetenzbonus von +1 auf Nahkampf- "
        "und Wurfwaffenangriffswürfe. Dieser Bonus steigt um 1 pro 4 Barbarenstufen, über welche der "
        "Charakter verfügt. Dies ist eine Kampfrauschkraft der Kategorie Kampfhaltung.",
    ),
    (
        "Zu-Fall-bringende Kampfhaltung",
        "AF",
        None,
        None,
        "Der Barbar kann sich darauf konzentrieren, seine Gegner niederzuwerfen. Ein Mal pro Runde "
        "kann er anstelle eines Nahkampfangriffes ein Kampfmanöver für Zu-Fall-Bringen gegen ein Ziel "
        "ausführen, welches keine Gelegenheitsangriffe provoziert, und bei Erfolg dem Ziel den Zustand "
        "Liegend verleihen. Dies ist eine Kampfrauschkraft der Kategorie Kampfhaltung.",
    ),
    (
        "Überwältigender Vorstoß",
        "AF",
        None,
        None,
        "Der Barbar verursacht Schaden in Höhe seines ST-Modifikators, wenn er das Kampfmanöver Überrennen "
        "erfolgreich durchführt.",
    ),
    (
        "Überwältigendes Niederrennen",
        "AF",
        6,
        "Überwältigender Vorstoß",
        "Der Barbar kann versuchen, mehr als ein Ziel pro Runde zu überrennen. Für jeden Überrennen-Wurf nach "
        "dem ersten erhält er einen Malus von -2 auf seinen KMB.",
    ),
]

assert len(RAGE_POWERS) == 86, len(RAGE_POWERS)


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
    class_id = str(ENTFESSELTER_BARBAR_ID)

    # ---- base_classes.json ----
    classes = load("base_classes.json")
    classes = [c for c in classes if c["id"] != class_id]
    classes.append(
        {
            "id": class_id,
            "name": "Entfesselter Barbar",
            "hit_dice": 12,
            "arch_class_of": None,
            "casting_ability": None,
            "spell_tradition": None,
            "bab_progression": 1.0,
            "fort_save": True,
            "ref_save": False,
            "wil_save": False,
            "skill_points_base": 4,
        }
    )
    save("base_classes.json", classes)

    # ---- base_class_skills.json ----
    skills = load("base_skills.json")
    skill_id_by_name = {row["name"]: row["id"] for row in skills}
    for name in BASE_CLASS_SKILLS:
        assert name in skill_id_by_name, f"missing skill: {name}"

    class_skills = load("base_class_skills.json")
    class_skills = [row for row in class_skills if row["base_class_id"] != class_id]
    for name in BASE_CLASS_SKILLS:
        class_skills.append(
            {
                "id": uid("entfesselter-barbar-classskill", name),
                "base_class_id": class_id,
                "skill_id": skill_id_by_name[name],
                "option_choice_id": None,
            }
        )
    save("base_class_skills.json", class_skills)

    # ---- base_class_option_groups.json ----
    groups = load("base_class_option_groups.json")
    groups = [g for g in groups if g["base_class_id"] != class_id]
    kampfrauschkraft_group_id = uid("entfesselter-barbar-group", "kampfrauschkraft")
    groups.append(
        {
            "id": kampfrauschkraft_group_id,
            "base_class_id": class_id,
            "key": "kampfrauschkraft",
            "label": "Kampfrauschkraft",
            "max_choices": len(KAMPFRAUSCHKRAFT_LEVELS),
        }
    )
    save("base_class_option_groups.json", groups)

    # ---- base_class_option_choices.json ----
    choices = load("base_class_option_choices.json")
    choices = [c for c in choices if c["group_id"] != kampfrauschkraft_group_id]

    choice_id_by_power: dict[str, str] = {}
    for name, _tag, _min_level, _requires, _desc in RAGE_POWERS:
        choice_id_by_power[name] = uid("entfesselter-barbar-choice", name)

    for name, _tag, min_level, requires, _desc in RAGE_POWERS:
        choices.append(
            {
                "id": choice_id_by_power[name],
                "group_id": kampfrauschkraft_group_id,
                "name": name,
                "min_level": min_level,
                "requires_choice_id": choice_id_by_power[requires] if requires else None,
            }
        )
    save("base_class_option_choices.json", choices)

    # ---- base_class_abilities.json + base_class_ability_grants.json ----
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    grants = [g for g in grants if g["base_class_id"] != class_id]
    existing_ability_ids = {a["id"] for a in abilities}

    def add_ability(name: str, description: str) -> str:
        aid = uid("entfesselter-barbar-ability", name)
        if aid not in existing_ability_ids:
            abilities.append({"id": aid, "name": name, "description": description})
            existing_ability_ids.add(aid)
        return aid

    def add_grant(ability_id: str, level: int, option_choice_id: str | None = None) -> None:
        grants.append(
            {
                "id": uid("entfesselter-barbar-grant", ability_id, str(level), option_choice_id or ""),
                "base_class_id": class_id,
                "ability_id": ability_id,
                "option_choice_id": option_choice_id,
                "level": level,
            }
        )

    weapons_id = add_ability(
        "Umgang mit Waffen und Rüstungen",
        "Ein Barbar ist im Umgang mit allen einfachen Waffen und allen Kriegswaffen, leichten "
        "Rüstungen, mittelschweren Rüstungen und Schilden (außer Turmschilden) geübt.",
    )
    add_grant(weapons_id, 1)

    kampfrausch_id = add_ability(
        "Kampfrausch",
        "Ein Barbar kann auf seine inneren Kraftreserven und seine Wildheit zurückgreifen, um "
        "zusätzliche Kampfkraft zu Erlangen. Beginnend mit der 1. Stufe kann ein Barbar pro Tag für "
        "eine Anzahl von Runden in Kampfrausch verfallen, welche der Höhe seines KO-Modifikators +4 "
        "entspricht. Mit Erreichen jeder weiteren Stufe erhält er 2 weitere Runden an Kampfrausch pro "
        "Tag. Kurzfristige Erhöhungen seiner Konstitution (wie z.B. durch den Zauber Ausdauer des "
        "Ochsen) erhöhen die Anzahl von Runden jedoch nicht, die der Barbar pro Tag in Kampfrausch "
        "verfallen kann. Der Barbar kann als Freie Aktion in Kampfrausch verfallen. Nach 8 Stunden "
        "Rast erhält er seine volle Anzahl an Runden zurück, welche er täglich in Kampfrausch "
        "verbringen kann; diese Rast muss nicht an einem Stück gehalten werden. Im Kampfrausch erhält "
        "ein Barbar einen Bonus von +2 auf Nahkampfangriffs- und -schadenswürfe, Wurfwaffenschadenswürfe "
        "und Willenswürfe. Zugleich erhält er einen Malus von -2 auf seine Rüstungsklasse. Er erhält "
        "ferner für die Dauer seines Kampfrausches 2 temporäre Trefferpunkte pro Trefferwürfel; diese "
        "temporären Trefferpunkte gehen als erste verloren, wenn der Barbar Schaden erleidet und werden "
        "nicht erneuert, sollte weniger als eine Minute zwischen dem Ende eines Kampfrausches und dem "
        "Beginn des nächsten vergehen. Im Kampfrausch kann ein Barbar keine charisma-, geschicklichkeits- "
        "oder intelligenzbasierenden Fertigkeiten mit Ausnahme von Akrobatik, Einschüchtern, Fliegen und "
        "Reiten nutzen, sowie keine Fähigkeiten, die Geduld und/oder Konzentration erfordern, wie z.B. "
        "das Wirken von Zaubern. Ein Barbar kann seinen Kampfrausch als Freie Aktion beenden und erhält "
        "sodann für 1 Minute den Zustand Erschöpft. Während ein Barbar den Zustand Erschöpft oder "
        "Entkräftet hat, kann er nicht in einen Kampfrausch verfallen. Ansonsten kann er beliebig oft am "
        "Tag in Kampfrausch verfallen, insofern er über Runden an Kampfrausch verfügt. Sollte der Barbar "
        "bewusstlos werden, endet sein Kampfrausch augenblicklich.",
    )
    add_grant(kampfrausch_id, 1)

    schnelle_bewegung_id = add_ability(
        "Schnelle Bewegung",
        "Die Bewegungsrate an Land ist bei einem Barbaren um 3 m höher als für sein Volk üblich. Dies "
        "gilt nur, wenn er gar keine, leichte oder mittelschwere Rüstung trägt und keine schwere Last "
        "mit sich führt. Dieser Bonus wird angewandt, noch bevor die Bewegungsrate des Barbaren durch "
        "getragene Lasten oder Rüstungen modifiziert wird. Dieser Bonus ist kumulativ mit allen "
        "anderen Boni des Barbaren auf seine Bewegungsrate an Land.",
    )
    add_grant(schnelle_bewegung_id, 1)

    kampfrauschkraft_slot_id = add_ability(
        "Kampfrauschkraft",
        "Wenn ein Barbar neue Erfahrungsstufen erlangt, lernt er zugleich seinen Kampfrausch auf "
        "andere Weise zu nutzen. Beginnend mit der 2. Stufe – und dann mit jeder weiteren geraden "
        "Klassenstufe als Barbar – erhält er eine neue Kampfrauschkraft. Ein Barbar kann von "
        "Kampfrauschkräften nur dann profitieren, wenn und solange er sich im Kampfrausch befindet. "
        "Manche Kräfte sind während eines Kampfrausches immer aktiv, während andere erfordern, dass "
        "der Barbar eine Aktion nutzt, um sie zu aktivieren. Sofern nicht anders angegeben, kann er "
        "eine bestimmte Kraft nicht mehrmals auswählen. Einige der folgenden Kampfrauschkräfte sind "
        "Kampfhaltungen. Zum Aktivieren einer Kampfhaltung ist eine Bewegungsaktion erforderlich. Ein "
        "Barbar kann stets nur eine Kampfhaltung aktiviert haben. Sollte er eine Kampfrauschkraft der "
        "Kategorie Kampfhaltung aktivieren, während er bereits eine Kampfhaltung aktiv nutzt, endet "
        "die aktuelle Kampfhaltung augenblicklich und wird durch die neue ersetzt. Der Barbar kann "
        "eine aktive Kampfhaltung absichtlich zu Beginn seines Zuges als Freie Aktion beenden, "
        "andernfalls hält sie bis zum Ende des Kampfrausches an.",
    )
    for level in KAMPFRAUSCHKRAFT_LEVELS:
        add_grant(kampfrauschkraft_slot_id, level)

    reflexbewegung_id = add_ability(
        "Reflexbewegung",
        "Beginnend mit der 2. Stufe erlangt der Barbar die Gabe, auf Bedrohungen reagieren, bevor es "
        "seine Sinne ihm eigentlich erlauben. Er kann nicht mehr auf dem Falschen Fuß angetroffen "
        "werden und verliert auch nicht mehr seinen Geschicklichkeitsbonus auf seine RK, wenn der "
        "Angreifer unsichtbar ist. Er verliert noch immer seinen GE-Bonus auf die RK, wenn er "
        "bewegungsunfähig ist. Ein Barbar mit dieser Fähigkeit kann allerdings weiterhin seinen "
        "Geschicklichkeitsbonus auf die Rüstungsklasse verlieren, wenn der Gegner erfolgreich eine "
        "Finte gegen ihn ausführt. Sollte der Barbar die Fähigkeit Reflexbewegung bereits durch eine "
        "andere Klasse besitzen, erhält er stattdessen Verbesserte Reflexbewegung. (Diese "
        "klassenübergreifende Sonderregel wird aktuell nicht ausgewertet - siehe todos.md.)",
    )
    add_grant(reflexbewegung_id, 2)

    gefahreninstinkt_id = add_ability(
        "Gefahreninstinkt",
        "Ab der 3. Stufe erhält der Barbar einen Bonus von +1 auf seine Reflexwürfe, um Fallen "
        "auszuweichen, sowie einen Ausweichbonus von +1 auf seine Rüstungsklasse gegen Angriffe von "
        "Fallen. Ferner erhält er einen Bonus von +1 auf Fertigkeitswürfe für Wahrnehmung, um nicht "
        "von Gegnern überrascht zu werden. Diese Boni steigen alle weiteren 3 Stufen als Barbar um 1 "
        "(maximal +6 mit der 18. Stufe). Diese Fähigkeit zählt als Fallengespür hinsichtlich der "
        "Voraussetzungen von Talenten und Klassenvoraussetzungen und kann durch jedes Klassenmerkmal "
        "eines Archetypen ersetzt werden, welches Fallengespür ersetzt. Die durch diese Fähigkeit "
        "erlangten Boni sind mit den durch Fallengespür erlangten kumulativ, sofern der Barbar durch "
        "eine andere Klasse über die Fähigkeit Fallengespür verfügt.",
    )
    for level in GEFAHRENINSTINKT_LEVELS:
        add_grant(gefahreninstinkt_id, level)

    verbesserte_reflexbewegung_id = add_ability(
        "Verbesserte Reflexbewegung",
        "Ab der 5. Stufe kann der Barbar nicht mehr in die Zange genommen werden. Ein Gegner kann den "
        "Barbaren auch nicht mehr mit einem Hinterhältigen Angriff attackieren, den ihm ein in die "
        "Zange nehmen ermöglichen würde, es sei denn, der Gegner besitzt vier Klassenstufen mehr in "
        "der Klasse, die ihm das Klassenmerkmal Hinterhältiger Angriff verleiht, als der Barbar über "
        "Barbarenstufen verfügt. Sollte der Barbar bereits durch eine andere Klasse über die Fähigkeit "
        "Reflexbewegung verfügen, werden seine Stufen in dieser anderen Klasse auf seine effektive "
        "Barbarenstufe für diesen Vergleich addiert.",
    )
    add_grant(verbesserte_reflexbewegung_id, 5)

    schadensreduzierung_id = add_ability(
        "Schadensreduzierung",
        "Mit Erlangen der 7. Stufe erhält der Barbar Schadensreduzierung. Er zieht jedes Mal, wenn er "
        "durch eine Waffe oder einen natürlichen Angriff Schaden nimmt, einen Punkt von diesem Schaden "
        "ab. Mit der 10. Stufe – und dann allen weiteren 3 Stufen – steigt seine Schadensreduzierung "
        "um 1 Punkt (bis zu 5 Punkten mit der 19. Stufe). Die Schadensreduzierung kann einen Schaden "
        "auf 0, aber nicht unter 0 senken.",
    )
    for level in SCHADENSREDUZIERUNG_LEVELS:
        add_grant(schadensreduzierung_id, level)

    starker_kampfrausch_id = add_ability(
        "Starker Kampfrausch",
        "Beginnend mit der 11. Stufe steigen die Boni eines Barbaren auf Nahkampfangriffs-, "
        "Nahkampfschadens-, Wurfwaffenschadens- und Willenswürfe im Kampfrausch auf +3. Ferner steigt "
        "die Anzahl der beim Beginn des Kampfrauschs erlangten temporären Trefferpunkte auf 3 TP pro "
        "Trefferwürfel.",
    )
    add_grant(starker_kampfrausch_id, 11)

    unbeugsamer_wille_id = add_ability(
        "Unbeugsamer Wille",
        "Ab der 14. Stufe erhält der Barbar während seines Kampfrauschs einen Bonus von +4 auf "
        "Willenswürfe gegen Zauber der Schule der Verzauberungen. Dieser Bonus ist mit anderen "
        "Modifikatoren kumulativ, wie etwa dem Moralbonus auf Willenswürfe, den der Barbar im "
        "Kampfrausch erhält.",
    )
    add_grant(unbeugsamer_wille_id, 14)

    unermuedlicher_kampfrausch_id = add_ability(
        "Unermüdlicher Kampfrausch",
        "Ab der 17. Stufe erleidet der Barbar am Ende seines Kampfrauschs nicht mehr den Zustand "
        "Erschöpft. Sollte er binnen 1 Minute nach Beendigung des letzten Kampfrausches erneut einen "
        "Kampfrausch beginnen, erlangt er durch diesen keine temporären Trefferpunkte.",
    )
    add_grant(unermuedlicher_kampfrausch_id, 17)

    maechtiger_kampfrausch_id = add_ability(
        "Mächtiger Kampfrausch",
        "Mit der 20. Stufe steigen die Boni eines Barbaren auf Nahkampfangriffs-, "
        "Nahkampfschadens-, Wurfwaffenschadens- und Willenswürfe im Kampfrausch auf +4. Ferner steigt "
        "die Anzahl der beim Beginn des Kampfrauschs erlangten temporären Trefferpunkte auf 4 TP pro "
        "Trefferwürfel.",
    )
    add_grant(maechtiger_kampfrausch_id, 20)

    # 54 rage powers, each its own ability, choice-gated within the
    # `kampfrauschkraft` group (same "grant level=1, real gate is the
    # choice's own min_level" convention as Schurke's Trick).
    for name, tag, _min_level, _requires, description in RAGE_POWERS:
        aid = add_ability(name, f"({tag}) {description}")
        add_grant(aid, 1, choice_id_by_power[name])

    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)

    print("Rage powers:", len(RAGE_POWERS))
    print("Total abilities:", len(abilities))
    print("Total grants (this class):", len([g for g in grants if g["base_class_id"] == class_id]))
    print("Done.")


if __name__ == "__main__":
    main()
