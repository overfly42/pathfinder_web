"""Builds `../app/fixtures/seed/base_conditions.json` — the `BaseCondition`
catalog (roadmap slice 5) of standard PF1e conditions plus two prose pages
of example poisons/diseases from the PRD:

    http://prd.5footstep.de/Grundregelwerk/Anhang/BesondereFaehigkeiten/Gebrechen/Gifte
    http://prd.5footstep.de/Grundregelwerk/Anhang/BesondereFaehigkeiten/Gebrechen/Krankheiten

The ~33 standard conditions (Benommen, Verängstigt, ...) aren't on any PRD
page as structured data — they're hand-transcribed below, same "prose has to
be parsed/typed by convention, not by schema" situation `scripts/README.md`
describes for other non-indexed content. Poisons/diseases *are* structured
(a `<table>` for poisons, one `<h5>` stat block per disease) and are fetched
+ parsed here.

`BaseCondition` has `name`/`description`/`type` (see `models/effect.py`) —
`type` is just which of the three source lists below a row came from
("condition"/"poison"/"disease"), for a future picker UI to group/filter by;
a poison/disease's SG/Inkubationszeit/Frequenz/etc. still become one
formatted description block rather than separate columns, the same way
`BaseSpell.description` holds a spell's full text. Where that text states a
single fixed number (not a dice roll or a "-"), `_parse_defaults` below also
extracts it into the row's `default_incubation_rounds`/
`default_duration_rounds`/`default_frequency_rounds`/
`default_successes_required` (round-normalized) so the activation form can
pre-fill it; anything dice-based, unstated, or in an unsupported unit
(weeks — `CharacterEffect`/the frontend only model round/minute/hour/day)
is left `None` and still typed in by the player, read off `description`.

Ids are deterministic (`uuid5` off the condition's own name, `ID_NAMESPACE`
below) so reruns upsert cleanly via `app.seed.condition_seed` instead of
minting duplicates — same approach as `build_feats_seed.py`'s `_stable_id`.

Usage:
    cd backend && python scripts/build_conditions_seed.py
"""

from __future__ import annotations

import json
import re
import urllib.request
import uuid
from html import unescape
from pathlib import Path

GIFTE_URL = "http://prd.5footstep.de/Grundregelwerk/Anhang/BesondereFaehigkeiten/Gebrechen/Gifte"
KRANKHEITEN_URL = "http://prd.5footstep.de/Grundregelwerk/Anhang/BesondereFaehigkeiten/Gebrechen/Krankheiten"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed" / "base_conditions.json"

ID_NAMESPACE = uuid.UUID("2c6a1a2e-6c3a-4b8a-9e1a-3f6a2c6a1a2e")

TAG_RE = re.compile(r"<[^>]+>")
PAGE_RE = re.compile(r'<div id="page" class="page">(.*?)<script type="text/javascript">', re.DOTALL)


def strip_tags(value: str) -> str:
    value = TAG_RE.sub("", value)
    return unescape(value.replace("&nbsp;", " ")).strip()


def fetch_page(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "pathfinder_web-import/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("iso-8859-1")


def _page_content(html: str) -> str:
    return PAGE_RE.search(html).group(1)


# --- 1. Standard conditions (Grundregelwerk, Anhang/Zustaende) ---------------
# Hand-transcribed, not fetched: this page (like the Hexenmeister bloodline
# list in import_hexenmeister_bloodlines.py) isn't behind any PRD datatable.

CORE_CONDITIONS: list[tuple[str, str]] = [
    (
        "Benommen",
        "Eine benommene Kreatur kann nicht normal handeln, hat aber keinen Malus auf die RK.\n\n"
        "Benommenheit währt üblicherweise 1 Runde lang.",
    ),
    (
        "Beschädigt",
        "Gegenstände, die mehr Schaden genommen haben, als es der Hälfte ihrer gesamten Trefferpunkte "
        "entspricht, sind beschädigt. Das heißt, dass sie ihre eigentliche Aufgabe nicht mehr effektiv "
        "ausüben können. Der Zustand beschädigt hat je nach Gegenstand die folgenden Auswirkungen:\n\n"
        "Handelt es sich bei dem Gegenstand um eine Waffe, erhalten Angriffe mit ihr einen Malus von -2 "
        "auf Angriffs- und Schadenswürfe. Kritische Treffer können nur noch bei einer natürlichen 20 "
        "erzielt werden und verursachen nur noch Schaden x2.\n"
        "Handelt es sich bei dem Gegenstand um eine Rüstung oder einen Schild, wird der RK-Bonus halbiert. "
        "Bei beschädigten Rüstungen wird außerdem der Rüstungsmalus auf Fertigkeiten verdoppelt.\n"
        "Handelt es sich bei dem Gegenstand um ein Werkzeug, das für eine Fertigkeit benötigt wird, "
        "erhalten Fertigkeitswürfe mit dem Gegenstand einen Malus von -2.\n"
        "Handelt es sich bei dem Gegenstand um einen Zauberstab oder einen Zauberstecken, verbraucht er "
        "bei einer Anwendung doppelt so viele Ladungen.\n"
        "Passt der Gegenstand in keine der eben angeführten Kategorien, hat der Zustand beschädigt keine "
        "Auswirkungen auf die Benutzung. Aber egal, zu welcher Art sie gehören, beschädigte Gegenstände "
        "sind immer nur 75 % ihres eigentlichen Preises wert.\n"
        "Handelt es sich um einen magischen Gegenstand, kann dieser nur mit Hilfe von Reparieren oder "
        "Ausbessern repariert werden, wenn der Zauber von einem Zaubernden gewirkt wird, dessen "
        "Zauberstufe mindestens so hoch ist wie die des Gegenstands.\n\n"
        "Nichtmagische Gegenstände können entweder auf ähnliche Weise repariert werden oder mit einem "
        "erfolgreichen Wurf auf Handwerk auf den Handwerksberuf, der auch für die Erschaffung des "
        "Gegenstands notwendig ist. Der SG für den Wurf auf Handwerk liegt im Allgemeinen bei 20 und pro "
        "Schadenspunkt, der repariert werden soll, braucht es 1 Stunde Arbeit. Die meisten Handwerker "
        "nehmen 1/10 der Gesamtkosten für den Gegenstand, um solchen Schaden zu reparieren (mehr, wenn "
        "der Gegenstand schwer beschädigt oder ruiniert ist).",
    ),
    (
        "Betäubt",
        "Ein betäubter Charakter lässt alles fallen, was er hält, kann keine Aktionen ausführen, erhält "
        "einen Malus von -2 auf die RK und verliert seinen GE-Bonus auf die RK (falls vorhanden).",
    ),
    (
        "Bewusstlos",
        "Bewusstlose Kreaturen sind KO geschlagen und hilflos. Bewusstlosigkeit wird entweder durch "
        "negative Trefferpunkte hervorgerufen (aber nicht mehr als es dem Konstitutionswert der Kreatur "
        "entspricht) oder wenn der nichttödliche Schaden die momentanen Trefferpunkte der Kreatur "
        "übersteigt.",
    ),
    (
        "Blind",
        "Die betroffene Kreatur kann nichts sehen. Sie erhält einen Malus von -2 auf die RK, verliert den "
        "GE-Bonus auf die RK (falls vorhanden) und erhält einen Malus von -4 auf die meisten "
        "Fertigkeitswürfe, die auf Stärke oder Geschicklichkeit basieren, und auf konkurrierende Würfe "
        "auf Wahrnehmung. Alle Würfe und Handlungen, die von der Sehfähigkeit abhängen (wie etwa lesen "
        "und von der Sicht abhängige Würfe auf Wahrnehmung), misslingen automatisch. Alle Gegner haben "
        "gegenüber der betroffenen Kreatur vollständige Tarnung (Fehlschlagschance von 50 %). Blinde "
        "müssen einen Wurf auf Akrobatik (SG 10) machen, um sich schneller als mit ihrer halben "
        "Bewegungsrate bewegen zu können. Kreaturen, denen dieser Wurf nicht gelingt, fallen zu Boden. "
        "Charaktere, die über längere Zeit blind sind, können sich daran gewöhnen und einige der "
        "Nachteile überwinden.",
    ),
    (
        "Blutung",
        "Eine Kreatur, die Schaden durch Blutverlust erleidet, nimmt zu Beginn ihres Zuges die angegebene "
        "Menge an Schaden. Blutungen können mit einem erfolgreichen Wurf auf Heilkunde (SG 15) gestoppt "
        "werden oder mit Hilfe eines Zaubers, der Schaden an den Trefferpunkten heilt (selbst wenn es "
        "sich bei dem Schaden durch Blutung um Attributsschaden handelt). Manche Blutungseffekte "
        "verursachen Attributsschaden oder sogar Attributsentzug. Blutungseffekte sind nicht miteinander "
        "kumulativ, außer sie verursachen unterschiedliche Arten von Schaden. Wird ein Charakter von "
        "zwei oder mehr Blutungseffekten betroffen, welche dieselbe Art von Schaden verursachen, wende "
        "den schlimmeren Effekt an. In diesem Fall ist ein Attributsentzug schlimmer als ein "
        "Attributsschaden.",
    ),
    (
        "Entkräftet",
        "Ein entkräfteter Charakter kann sich nur mit seiner halben Bewegungsrate fortbewegen, kann nicht "
        "rennen und keine Sturmangriffe ausführen und erhält einen Malus von -6 auf Stärke und "
        "Geschicklichkeit. Hat ein entkräfteter Charakter sich 1 Stunde lang ausgeruht, ist er nur noch "
        "erschöpft. Ein erschöpft Charakter wird wieder entkräftet, wenn er etwas macht, das ihn "
        "normalerweise erschöpfen würde.",
    ),
    (
        "Erschöpft",
        "Ein erschöpfter Charakter kann weder rennen, noch Sturmangriffe ausführen und erhält einen "
        "Malus von -2 auf Stärke und Geschicklichkeit. Macht der Erschöpfte irgendetwas, das ihn "
        "normalerweise erschöpfen würde, wird er dadurch entkräftet. Hat der Charakter sich 8 Stunden "
        "lang ausgeruht, ist er nicht länger erschöpft.",
    ),
    (
        "Erschüttert",
        "Ein erschütterter Charakter erhält einen Malus von -2 auf Angriffs-, Rettungs-, Fertigkeits- "
        "und Attributswürfe. Erschüttert ist ein weniger schlimmer Zustand der Furcht als verängstigt "
        "oder in Panik.",
    ),
    (
        "Fasziniert",
        "Eine faszinierte Kreatur ist von einem übernatürlichen oder einem Zaubereffekt fasziniert. Sie "
        "steht oder sitzt ganz ruhig und macht nichts, außer den Effekt zu beobachten, der sie "
        "fasziniert. Die Kreatur erhält einen Malus von -4 auf Fertigkeitswürfe, mit denen sie auf "
        "etwas reagiert, wie etwa Würfe auf Wahrnehmung. Immer wenn sich dem Faszinierten eine "
        "potentielle Gefahr nähert, darf er einen erneuten Rettungswurf gegen den faszinierenden Effekt "
        "machen. Offensichtliche Gefahren, wie jemand, der eine Waffe zieht oder einen Zauber wirkt oder "
        "eine Fernkampfwaffe auf den Faszinierten richtet, brechen den Effekt sofort. Die Verbündeten "
        "des Faszinierten können diesen mit einer Standard-Aktion von dem Effekt befreien.",
    ),
    (
        "Geblendet",
        "Ein Geblendeter kann kaum etwas sehen, da seine Augen überreizt sind. Er erhält einen Malus von "
        "-1 auf Angriffswürfe und Würfe auf Wahrnehmung fürs Sehen.",
    ),
    (
        "Gelähmt",
        "Ein gelähmter Charakter ist auf der Stelle festgewurzelt und kann sich weder bewegen noch "
        "handeln. Er hat effektive Stärke- und Geschicklichkeitswerte von 0 und ist hilflos, kann aber "
        "noch rein geistige Aktionen ausführen. Eine geflügelte Kreatur, die gerade flog, als sie "
        "gelähmt wurde, kann nicht mehr mit den Flügeln schlagen und fällt. Ein gelähmter Schwimmer kann "
        "nicht mehr schwimmen und deshalb ertrinken. Jede Kreatur darf sich über ein Feld bewegen, auf "
        "dem ein Gelähmter steht, egal ob es sich um Verbündete oder Feinde handelt. Jedes Feld aber, "
        "auf dem ein Gelähmter steht, zählt als zwei Felder, wenn man sich darüber bewegen möchte.",
    ),
    (
        "Hilflos",
        "Ein hilfloser Charakter ist gelähmt, festgehalten, gefesselt, bewusstlos, schläft oder ist sonst "
        "auf irgendeine Weise vollkommen der Gnade seiner Feinde ausgeliefert. Ein Hilfloser wird "
        "behandelt, als hätte er eine Geschicklichkeit von 0 (Modifikator -5). Nahkampfangriffe gegen "
        "einen Hilflosen werden mit einem Bonus von +4 gemacht (entspricht dem Angreifen eines auf dem "
        "Boden Liegenden). Fernkampfangriffe erhalten keinen besonderen Bonus. Schurken können "
        "Hinterhältige Angriffe gegen Hilflose ausführen.\n\n"
        "Ein Gegner kann mit einer vollen Aktion auch einen Coup de Grace gegen einen Hilflosen "
        "ausführen. Er kann den Coup de Grace auch mit einem Bogen oder einer Armbrust ausführen, wenn "
        "er auf einem Feld steht, das an den Hilflosen angrenzt. Der Angreifer trifft automatisch und "
        "erzielt einen kritischen Treffer. (Ein Schurke kann auch noch den Schaden seines Hinterhältigen "
        "Angriffs addieren, wenn er einen Coup de Grace gegen einen Hilflosen ausführt.) Überlebt der "
        "Hilflose, muss er trotzdem einen Zähigkeitswurf (SG 10 + erlittener Schaden) machen. Bei einem "
        "Fehlschlag stirbt er. Das Ausführen eines Coup de Grace provoziert Gelegenheitsangriffe.\n\n"
        "Kreaturen, die gegen kritische Treffer immun sind, erleiden keinen kritischen Schaden und "
        "müssen auch keinen Zähigkeitswurf ablegen, um nicht durch einen Coup de Grace getötet zu "
        "werden.",
    ),
    (
        "Im Haltegriff",
        "Eine Kreatur im Haltegriff ist tatsächlich fest verschnürt und kann nur wenige Aktionen "
        "unternehmen. Sie kann sich nicht bewegen und gilt als auf dem falschen Fuß erwischt und erhält "
        "zusätzlich noch einen Malus von -4 auf ihre RK. Eine Kreatur im Haltegriff kann nur einige "
        "wenige Aktionen ausführen: Sie kann versuchen sich zu befreien, entweder mit Hilfe eines "
        "Kampfmanöverwurfs oder mit einem Wurf auf Entfesselungskunst. Sie kann verbale und geistige "
        "Aktionen ausführen, aber keine Zauber wirken, die eine Gesten- oder eine Materialkomponente "
        "benötigen. Eine Kreatur im Haltegriff, die einen Zauber wirken oder Zauberähnliche Fähigkeiten "
        "einsetzen möchte, muss einen Konzentrationswurf (SG 10 + KMB desjenigen, der sie im Haltegriff "
        "hat + Zaubergrad) machen. Bei einem Fehlschlag geht der Zauber verloren. Im Haltegriff ist eine "
        "schwerwiegendere Version des Zustands Ringend und die beiden Zustände sind nicht kumulativ.",
    ),
    (
        "In Panik",
        "Eine panische Kreatur muss alles fallen lassen, was sie festhält, und so schnell sie kann vor "
        "der Quelle ihrer Furcht und allen anderen Gefahren fliehen. Sie nimmt dabei einen zufällig "
        "ermittelten Weg und kann keine anderen Aktionen ausführen. Außerdem erhält die panische Kreatur "
        "einen Malus von -2 auf alle Rettungs-, Fertigkeits- und Attributswürfe. Wird sie in die Ecke "
        "gedrängt, kauert sich eine panische Kreatur zusammen und greift nicht an. Meist wird sie im "
        "Kampf die Aktion Volle Verteidigung einsetzen. Eine panische Kreatur kann ihre besonderen "
        "Fähigkeiten, auch Zauber, einsetzen, um zu fliehen, ja sie muss dies sogar tun, wenn dies den "
        "einzigen Weg darstellt zu fliehen.\n\n"
        "In Panik ist ein intensiverer Zustand der Furcht als verängstigt oder erschüttert.",
    ),
    (
        "Kampfunfähig",
        "Ein Charakter, der 0 TP oder negative TP hat, aber stabilisiert und bei Bewusstsein ist, ist "
        "kampfunfähig. Ein kampfunfähiger Charakter kann jede Runde eine Bewegungsaktion oder eine "
        "Standard-Aktion ausführen (nicht aber beides, er kann auch keine vollen Aktionen ausführen; er "
        "kann aber Schnelle, Augenblickliche und Freie Aktionen ausführen). Der Charakter bewegt sich "
        "mit seiner halben Bewegungsrate. Bei Bewegungsaktionen geht der Charakter nicht das Risiko "
        "weiterer Verletzungen ein, wenn er aber eine Standard-Aktion ausführt (oder eine andere Art von "
        "Aktion, die der Spielleiter für zu anstrengend hält – etwa manche freien Aktionen wie schnell "
        "zaubern), erleidet er 1 Schadenspunkt, nachdem er die Aktion vollendet hat. Solange die Aktion "
        "die TP des Charakters nicht erhöht, hat er dann negative TP und liegt damit im Sterben.\n\n"
        "Ein kampfunfähiger Charakter mit negativen TP kann seine TP auf natürliche Weise regenerieren, "
        "wenn ihm jemand hilft. Ansonsten darf er jeden Tag einen Konstitutionswurf (SG 10) machen, "
        "nachdem er 8 Stunden geruht hat, um seine TP auf natürliche Weise zu regenerieren. Der "
        "Charakter erhält einen Malus auf diesen Wurf welcher der Anzahl der negativen TP gleicht. "
        "Misslingt der Wurf verliert der Charakter noch 1 TP, wird dadurch jedoch nicht bewusstlos. Ist "
        "der Wurf einmal gelungen, beginnt der Charakter auf natürlichem Wege zu heilen und schwebt "
        "nicht länger in der Gefahr, Trefferpunkte zu verlieren.",
    ),
    (
        "Kauernd",
        "Der Charakter ist vor Angst gelähmt und kann nicht handeln. Außerdem erhält er einen Malus von "
        "-2 auf die RK und verliert seinen GE-Bonus auf die RK (falls vorhanden).",
    ),
    (
        "Körperlos",
        "Eine Kreatur, die körperlos ist, besitzt keinen physischen Körper. Körperlose Kreaturen sind "
        "gegen alle nichtmagischen Angriffsforrnen immun. Sie erleiden nur den halben Schaden (50 %) von "
        "magischen Waffen, Zaubern, zauberähnlichen Effekten und übernatürlichen Effekten. Körperlose "
        "Kreaturen erleiden den vollen Schaden von Angriffen durch andere körperlose Kreaturen und "
        "Effekte und von Energieeffekten.",
    ),
    (
        "Kränkelnd",
        "Der betroffene Charakter erhält einen Malus von -2 auf alle Angriffs-, Waffenschadens-, "
        "Rettungs-, Fertigkeits- und Attributswürfe.",
    ),
    (
        "Lebenskraftverlust",
        "Ein Charakter, der eine oder mehrere negative Stufen erhalten hat, die ihm permanent Stufen "
        "entziehen könnten. Hat das Opfer mindestens so viele negative Stufen wie Trefferwürfel, stirbt "
        "es. Weitere Informationen findest du im Abschnitt „Lebenskraftverlust und Negative Stufen“ auf "
        "Seite 562.",
    ),
    (
        "Liegend",
        "Der Charakter liegt auf dem Boden. Ein liegender Angreifer erhält einen Malus von -4 auf "
        "Angriffswürfe im Nahkampf und kann keine Fernkampfwaffen (außer Armbrüsten) benutzen. Ein "
        "liegender Verteidiger erhält einen Bonus von +4 auf seine RK gegen Fernkampfangriffe, aber "
        "einen Malus von -4 auf die RK gegen Nahkampfangriffe.\n\n"
        "Aufstehen gilt als Bewegungsaktion, die Gelegenheitsangriffe provoziert.",
    ),
    (
        "Ringend",
        "Eine ringende Kreatur wird durch eine andere Kreatur, eine Falle oder einen Effekt festgehalten. "
        "Ringende Kreaturen können sich nicht bewegen und erhalten einen Malus von -4 auf ihre "
        "Geschicklichkeit. Außerdem erhält eine ringende Kreatur einen Malus von -2 auf alle Angriffs- "
        "und Kampfmanöverwürfe, außer auf solche, um selbst jemanden in den Ringkampf zu verwickeln oder "
        "dem ringenden Zustand zu entkommen. Des Weiteren können ringende Kreaturen keine Aktionen "
        "ausführen, für die sie beide Hände bräuchten. Ein ringender Charakter, der zaubern möchte, muss "
        "einen Konzentrationswurf (SG 10 + KMB desjenigen, der ihn in den Ringkampf verwickelt hat + "
        "Zaubergrad) machen. Misslingt dieser Wurf, geht der Zauber verloren. Ringende Kreaturen können "
        "keine Gelegenheitsangriffe ausführen.\n\n"
        "Einer ringenden Kreatur ist es nicht möglich, Heimlichkeit einzusetzen, um sich vor demjenigen "
        "zu verstecken, der sie in den Ringkampf verwickelt hat, selbst wenn ihr eine besondere "
        "Fähigkeit, wie etwa Meisterliches Verstecken, dies erlauben würde. Wenn eine ringende Kreatur "
        "unsichtbar wird, entweder mit Hilfe eines Zaubers oder einer anderen Fähigkeit, erhält sie "
        "einen Situationsbonus von +2 auf ihre KMV, um den Ringkampf zu vermeiden. Ansonsten erhält sie "
        "keine Vorteile.",
    ),
    (
        "Stabilisiert",
        "Ein Charakter, der im Sterben liegt und zwar noch negative Trefferpunkte hat, aber keine "
        "Trefferpunkte mehr verliert, ist stabilisiert. Er stirbt also nicht mehr, ist aber noch "
        "bewusstlos. Ist der Charakter durch die Hilfe eines anderen Charakters stabilisiert worden (wie "
        "durch einen Wurf auf Heilkunde oder durch magische Heilung), verliert er keine Trefferpunkte "
        "mehr. Der Charakter darf jede Stunde einen Konstitutionswurf (SG 10) machen, um wieder zu "
        "Bewusstsein zu kommen und dann kampfunfähig zu sein (selbst wenn die Trefferpunkte immer noch "
        "negativ sind). Der Charakter erhält einen Malus auf diesen Wurf, welcher der Anzahl seiner "
        "negativen Trefferpunkte gleicht.\n\n"
        "Hat der Charakter sich selbst ohne fremde Hilfe stabilisiert, besteht immer noch die Gefahr, "
        "dass er Trefferpunkte verliert. Er darf jede Stunde einen Konstitutionswurf machen, um sich zu "
        "stabilisieren (wie ein Charakter, dem geholfen wurde). Bei einem Misserfolg verliert er jedoch "
        "1 weiteren TP.",
    ),
    (
        "Sterbend",
        "Eine sterbende Kreatur ist bewusstlos und dem Tode nahe. Kreaturen mit negativen Trefferpunkten, "
        "die nicht stabilisiert sind, liegen im Sterben. Eine sterbende Kreatur kann keine Aktionen "
        "ausführen. Wenn der sterbende Charakter wieder am Zug ist, nachdem er auf einen negativen "
        "TP-Wert gesunken ist (aber noch nicht tot ist), und in allen darauf folgenden Runden, muss er "
        "einen Konstitutionswurf (SG 10) machen, um sich zu stabilisieren. Der Charakter erhält einen "
        "Malus auf diesen Wurf, welcher dem momentanen negativen Wert seiner TP entspricht. Ein "
        "Charakter, der stabilisiert ist, muss diesen Wurf nicht machen. Eine natürliche 20 bei diesem "
        "Wurf, bedeutet einen automatischen Erfolg. Misslingt der Wurf, verliert der Charakter 1 "
        "Trefferpunkt. Wenn eine sterbende Kreatur so viele negative TP hat, wie es ihrem "
        "Konstitutionswert entspricht, stirbt sie.",
    ),
    (
        "Taub",
        "Ein tauber Charakter kann nichts hören. Er erhält einen Malus von -4 auf Initiativewürfe und "
        "Würfe auf Wahrnehmung fürs Lauschen misslingen ihm automatisch. Außerdem erhält er einen Malus "
        "von -4 auf konkurrierende Würfe auf Wahrnehmung und Zauber mit verbaler Komponente verpatzt er "
        "zu 20 %. Charaktere, die über lange Zeit taub sind, können sich an die Nachteile dieses "
        "Zustands gewöhnen und einige von ihnen überwinden.",
    ),
    (
        "Tot",
        "Entweder sind die Trefferpunkte des Charakters auf einen negativen Wert gesunken, welcher dem "
        "Konstitutionswert entspricht, seine Konstitution ist auf 0 gesunken oder er wurde schlagartig "
        "von einem Zauber oder Effekt getötet. Die Seele des Charakters verlässt seinen Körper. "
        "Verstorbene können zwar nicht von normaler oder magischer Heilung profitieren, aber mit Hilfe "
        "von Magie wieder zum Leben erweckt werden. Solange die Leiche nicht auf magische Weise "
        "konserviert wird, verrottet sie ganz normal. Magie, die einen toten Charakter wieder zum Leben "
        "erweckt, stellt meist auch den Körper wieder her und macht den Charakter entweder vollkommen "
        "gesund oder versetzt ihn in den Zustand zum Zeitpunkt des Todes (je nach Zauber oder "
        "Gegenstand). In beiden Fällen muss der erweckte Charakter sich aber keine Sorgen um "
        "Totenstarre, Verrottung oder andere Zustände machen, welche eine Leiche betreffen können.",
    ),
    (
        "Übelkeit",
        "Kreaturen, denen übel ist, haben eine Magenverstimmung. Sie sind nicht in der Lage anzugreifen, "
        "Zauber zu wirken, sich auf Zauber zu konzentrieren oder irgendetwas anderes zu tun, das ihre "
        "Aufmerksamkeit beanspruchen würde. Ein Charakter, dem übel ist, kann pro Runde nur eine "
        "Bewegungsaktion ausführen.",
    ),
    (
        "Unsichtbar",
        "Kreaturen, die unsichtbar sind, können nicht mit Hilfe des Sehsinns wahrgenommen werden. Eine "
        "unsichtbare Kreatur erhält einen Bonus von +2 auf Angriffswürfe gegen Gegner, die sie sehen "
        "kann und kann deren GE-Boni auf die RK (falls vorhanden) ignorieren. Siehe ansonsten "
        "Unsichtbarkeit bei den besonderen Fähigkeiten.",
    ),
    (
        "Verängstigt",
        "Eine verängstigte Kreatur flieht vor der Quelle ihrer Furcht so gut sie kann. Kann sie nicht "
        "fliehen, darf sie kämpfen. Ein Verängstigter erhält einen Malus von -2 auf alle Angriffs-, "
        "Rettungs-, Fertigkeits- und Attributswürfe. Er kann aber besondere Fähigkeiten, auch Zauber, "
        "einsetzen, um zu fliehen. Ja der Charakter muss diese Mittel sogar einsetzen, wenn es ihm sonst "
        "nicht möglich ist zu fliehen. Verängstigt gleicht dem Zustand Erschüttert, außer dass die "
        "Kreatur fliehen muss, wenn ihr dies möglich ist. In Panik ist ein noch intensiverer Zustand der "
        "Furcht.",
    ),
    (
        "Versteinert",
        "Ein versteinerter Charakter wurde zu Stein verwandelt und gilt als bewusstlos. Entstehen an "
        "einem versteinerten Charakter Risse oder zerbricht er, bleibt er unversehrt, wenn die "
        "abgebrochenen Körperteile bei der Zurückverwandlung in Fleisch wieder mit dem Körper verbunden "
        "werden. Ist der Körper des Charakters aber unvollständig, wenn er zurückverwandelt wird, bleibt "
        "er so und der Charakter erleidet möglicherweise einen permanenten Verlust an Trefferpunkten "
        "und/oder eine bleibende Behinderung.",
    ),
    (
        "Verstrickt",
        "Ein verstrickter Charakter ist in seiner Bewegung eingeschränkt. Solange seine Fesseln nicht an "
        "einem unbeweglichen Objekt befestigt sind oder von einer Kraft festgehalten werden, kann er "
        "sich aber noch bewegen. Eine verstrickte Kreatur bewegt sich mit ihrer halben Bewegungsrate, "
        "kann nicht rennen oder Sturmangriffe ausführen, erhält einen Malus von -2 auf alle "
        "Angriffswürfe und einen Malus von -4 auf Geschicklichkeit. Ein verstrickter Charakter, der "
        "versucht, einen Zauber zu wirken, muss einen erfolgreichen Konzentrationswurf (SG 15 + "
        "Zaubergrad) machen, oder er verliert den Zauber.",
    ),
    (
        "Verwirrt",
        "Eine verwirrte Kreatur ist durcheinander und kann nicht normal handeln. Sie kann Freund nicht "
        "von Feind unterscheiden und behandelt einfach alle anderen Kreaturen als Feinde. Verbündete, "
        "die einen für das Ziel vorteilhaften Zauber auf die verwirrte Kreatur wirken wollen, müssen "
        "einen erfolgreichen Berührungsangriff im Nahkampf ausführen. Wird eine verwirrte Kreatur "
        "angegriffen, greift sie ihren Angreifer ebenfalls an, bis dieser entweder tot oder außer "
        "Sichtreichweite ist.\n\n"
        "Würfle zu Beginn des Zuges einer verwirrten Kreatur auf der folgenden Tabelle, um zu ermitteln, "
        "wie sie sich in der Runde verhalten wird.\n\n"
        "W% 01-25: Verhält sich normal.\n"
        "W% 26-50: Macht nichts, außer zusammenhangslos vor sich hin zu brabbeln.\n"
        "W% 51-75: Fügt sich selbst mit einem Gegenstand, den sie in der Hand hält, 1W8 Schadenspunkte "
        "plus ST-Modifikator zu.\n"
        "W% 76-100: Greift die nächste Kreatur an (ein Vertrauter zählt in diesem Fall als Teil der "
        "verwirrten Kreatur).\n\n"
        "Ein Verwirrter, dem es nicht möglich ist, die angegebene Handlung auszuführen, brabbelt "
        "zusammenhangslos vor sich hin. Angreifer erhalten jedoch keine besonderen Vorteile, wenn sie "
        "einen Verwirrten angreifen. Eine verwirrte Kreatur, die angegriffen wird, greift in ihrem "
        "nächsten Zug automatisch den Angreifer an, wenn sie in diesem Zug noch verwirrt ist. Denk "
        "daran, dass eine verwirrte Kreatur keine Gelegenheitsangriffe gegen Feinde ausführen wird, die "
        "sie nicht sowieso schon angreift (entweder auf Grund ihrer Handlung in diesem Zug oder weil sie "
        "gerade angegriffen wurde).",
    ),
    (
        "Wankend",
        "Eine wankende Kreatur kann pro Runde eine Bewegungsaktion oder eine Standard-Aktion (nicht aber "
        "beides, auch keine volle Aktion) ausführen. Sie kann aber immer noch schnelle und sofortige "
        "Aktionen unternehmen. Eine Kreatur, die genauso viel Betäubungsschaden wie momentane "
        "Trefferpunkte hat, gerät ins Wanken.",
    ),
]


# --- 2. Poisons (PRD example table) ------------------------------------------

def fetch_poisons() -> list[tuple[str, str]]:
    content = _page_content(fetch_page(GIFTE_URL))
    table = re.search(r"<table.*?</table>", content, re.DOTALL).group(0)
    rows = re.findall(r'<tr class="userrow">(.*?)</tr>', table, re.DOTALL)
    entries = []
    for row in rows:
        if "<td" not in row:
            continue  # header row
        cells = [strip_tags(c) for c in re.findall(r'<td class="usercell">(.*?)</td>', row, re.DOTALL)]
        name, art, sg, inkubation, frequenz, effekt, heilung, kosten = cells
        description = (
            f"Art: {art}. SG: {sg}. Inkubationszeit: {inkubation}. Frequenz: {frequenz}. "
            f"Effekt: {effekt}. Heilung: {heilung}. Preis: {kosten}."
        )
        entries.append((name, description))
    return entries


# --- 3. Diseases (PRD per-entry stat blocks) ---------------------------------

def fetch_diseases() -> list[tuple[str, str]]:
    content = _page_content(fetch_page(KRANKHEITEN_URL))
    parts = re.split(r'<h5><span class="cl-stat-block-title">', content)[1:]
    entries = []
    for part in parts:
        name_match = re.match(r"(.*?)</span></h5>", part, re.DOTALL)
        name = strip_tags(name_match.group(1))
        rest = part[name_match.end():]
        cut = rest.find('<!--notypo--><a name="p')
        body_html = rest[:cut] if cut != -1 else rest
        description = re.sub(r"\n{2,}", "\n", strip_tags(body_html)).strip()
        entries.append((name, description))
    return entries


# --- 4. Structured defaults parsed out of the formatted description -------
# Only handles a single fixed "N Unit"/"N/Unit" value — dice rolls ("1W4
# Tage"), "-" (not stated/incurable), and units this app doesn't model
# (weeks) all fall through to None, same as any other unparseable case.

_ROUND_UNITS = {
    "rd": 1, "runde": 1, "runden": 1,
    "min": 10, "minute": 10, "minuten": 10,
    "std": 600, "stunde": 600, "stunden": 600,
    "tag": 14400, "tage": 14400,
}
_NUM_UNIT_RE = re.compile(r"^\s*(\d+)\s*/?\s*([A-Za-zÄäÖöÜü]+)[./]*\s*$")
_POISON_FIELDS_RE = re.compile(
    r"Inkubationszeit:\s*(?P<inkubation>.*?)\s*Frequenz:\s*(?P<frequenz>.*?)\s*Effekt:.*?"
    r"Heilung:\s*(?P<heilung>.*?)\s*Preis:",
    re.DOTALL,
)
_DISEASE_FIELDS_RE = re.compile(
    r"Inkubationszeit\s+(?P<inkubation>.*?);\s*Frequenz\s+(?P<frequenz>.*?)\s*\n.*?"
    r"Heilung\s+(?P<heilung>\d+)\s+aufeinander",
    re.DOTALL,
)
_CONDITION_DURATION_RE = re.compile(
    r"währt üblicherweise (\d+) (Runde|Runden|Minute|Minuten|Stunde|Stunden|Tag|Tage)"
)


def _parse_fixed_value(raw: str) -> int | None:
    """'10 Min.' -> 100 (rounds). '1/Rd.' -> 1. '-'/dice/unsupported unit -> None."""
    raw = raw.strip().rstrip(".").strip()
    if not raw or raw == "-" or re.search(r"\bW\d", raw, re.IGNORECASE):
        return None
    match = _NUM_UNIT_RE.match(raw)
    if not match:
        return None
    value, unit = match.groups()
    rounds = _ROUND_UNITS.get(unit.lower())
    return int(value) * rounds if rounds else None


def _parse_rate(raw: str) -> int | None:
    """Frequency cell like '1/Rd. für 6 Rd.' -> just the leading 'N/Unit' interval."""
    head = re.split(r"\s+für\b|,", raw.strip())[0].strip()
    return _parse_fixed_value(head)


def _parse_cure(raw: str) -> int | None:
    """'2 aufeinander folgende Rettungswürfe' / '1 Rettungswurf' -> the leading count."""
    match = re.match(r"^\s*(\d+)\b", raw.strip())
    return int(match.group(1)) if match else None


def _parse_defaults(description: str, type_: str) -> dict[str, int | None]:
    defaults = {
        "default_incubation_rounds": None,
        "default_duration_rounds": None,
        "default_frequency_rounds": None,
        "default_successes_required": None,
    }
    if type_ == "poison":
        match = _POISON_FIELDS_RE.search(description)
    elif type_ == "disease":
        match = _DISEASE_FIELDS_RE.search(description)
    else:
        duration_match = _CONDITION_DURATION_RE.search(description)
        if duration_match:
            value, unit = duration_match.groups()
            defaults["default_duration_rounds"] = int(value) * _ROUND_UNITS[unit.lower()]
        return defaults
    if match:
        defaults["default_incubation_rounds"] = _parse_fixed_value(match.group("inkubation"))
        defaults["default_frequency_rounds"] = _parse_rate(match.group("frequenz"))
        defaults["default_successes_required"] = _parse_cure(match.group("heilung"))
    return defaults


def main() -> None:
    entries: list[tuple[str, str, str]] = (
        [(name, description, "condition") for name, description in CORE_CONDITIONS]
        + [(name, description, "poison") for name, description in fetch_poisons()]
        + [(name, description, "disease") for name, description in fetch_diseases()]
    )
    rows = [
        {
            "id": str(uuid.uuid5(ID_NAMESPACE, name)),
            "name": name,
            "description": description,
            "type": type_,
            **_parse_defaults(description, type_),
        }
        for name, description, type_ in entries
    ]
    OUTPUT_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} conditions to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
