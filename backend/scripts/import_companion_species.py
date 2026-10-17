"""Animal companion species, progression and entitlements — roadmap slice
10, step 2b. Fetches the PRD pages, parses them and writes the seed
fixtures; it doesn't touch the database.

Written so a further source is a new `SPECIES_SOURCES` entry, not a new
script: every PRD page that lists companion species in the Druide page's
statblock format ("Name" / "Spielwerte zu Beginn:" / "Größe:" /
"Bewegungsrate:" / "RK:" / "Angriff:" / "Attributswerte:" / "Besondere
Eigenschaften:" / "Besondere Angriffe:" / "Aufstieg auf die vierte|siebte
Stufe:") goes through the same parser (`parse_species`).

What it writes:
- `base_races.json`: one row per species (`companion_kind`
  "animal_companion", `creature_type` "Tier", `source`), kept out of the
  player race picker.
- `base_race_abilities.json`: the species' special abilities with their PRD
  text (Monsterhandbuch "Allgemeine Monsterregeln", the Krokodil/Gepard/
  Kamel/Vielfraß entries, Mit Tieren umgehen's "Kampfausbildung" for
  "kampfsicher"); Dämmersicht reuses the existing row.
- `base_companion_species_stages.json` (+ `_abilities`): starting statblock
  and the 4th/7th-level advancement per species.
- `base_companion_progression.json` (+ `_abilities`): "Tabelle: Tiergefährte".
- `base_classes.json`/`base_class_abilities.json`/`base_class_skills.json`:
  the pseudo class "Tiergefährte" (W8, ¾ GAB, good Ref/Fort, 2 + IN) and
  its abilities (Verbindung, Zauber teilen, Entrinnen, Hingabe,
  Mehrfachangriff, Verbessertes Entrinnen).
- `base_companion_slot_grants.json` (+ `_slot_species.json`): one "primary"
  animal-companion entitlement per trigger ability with its species list.

Natural attacks: damage type and primary/secondary come from the
Monsterhandbuch's "Tabelle: Natürliche Angriffe nach Grössenkategorie"
(`ATTACK_KINDS`); a footnote "1" on an attack name (Pferd's "Hufe1") also
marks it secondary. An "… oder …" alternative and a special attack that
isn't part of the normal attack routine (Krallen against a grappled foe,
Würgen, Spucken) carry `alternative: true`.

Run with the project venv active:
    cd backend && python scripts/import_companion_species.py
    python -m app.seed.class_seed && python -m app.seed.race_seed
    python -m app.seed.skill_seed && python -m app.seed.class_ability_seed
    python -m app.seed.companion_seed
"""

from __future__ import annotations

import html
import json
import re
import urllib.request
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
ID_NAMESPACE = uuid.UUID("4e1b7c2a-9d3f-4a6e-b8c5-7f0a1d2e3b4c")

# (url, source label, text marker the species list starts after)
SPECIES_SOURCES: list[tuple[str, str, str]] = [
    ("http://prd.5footstep.de/Grundregelwerk/Klassen/Druide", "Grundregelwerk: Druide", "Auswahl einer Tierart"),
]
PROGRESSION_SOURCE = "http://prd.5footstep.de/Grundregelwerk/Klassen/Druide"

COMPANION_CLASS_NAME = "Tiergefährte"
DAEMMERSICHT_ABILITY_ID = "753a04ab-cabf-4bcc-9377-f5da1d737ac5"

SIZES = {
    "mini": "Mini",
    "winzig": "Winzig",
    "sehr klein": "Sehr klein",
    "klein": "Klein",
    "mittelgroß": "Mittelgroß",
    "groß": "Groß",
    "riesig": "Riesig",
    "gigantisch": "Gigantisch",
    "kolossal": "Kolossal",
}
SPEED_KEYS = {"Klettern": "climb", "Schwimmen": "swim", "Fliegen": "fly", "Graben": "burrow"}

# Natural attack -> (damage type, secondary by nature), Monsterhandbuch table.
ATTACK_KINDS: dict[str, tuple[str, bool]] = {
    "Biss": ("H/S/W", False),
    "Durchbohren": ("S", False),
    "Huf": ("W", True),
    "Hufe": ("W", True),
    "Klaue": ("H/W", False),
    "Klauen": ("H/W", False),
    "Krallen": ("H", False),
    "Schwanzschlag": ("W", True),
}

# Special abilities: name -> description (PRD text). Keys are matched
# case-insensitively against the statblock's "Besondere …" entries.
ABILITY_TEXTS: dict[str, str] = {
    "Geruchssinn": (
        "(AF) Diese besondere Fähigkeit erlaubt es den Kreaturen, die sie besitzen, die Annäherung von Feinden zu "
        "entdecken, sie anhand ihres Geruchs in ihrem Versteck ausfindig zu machen und ihre oder andere "
        "Geruchsspuren zu verfolgen. Kreaturen mit der Fähigkeit Geruchssinn können ihnen vertraute Gerüche "
        "genauso leicht erkennen, wie Menschen einen vertrauten Anblick wiedererkennen."
    ),
    "Blindgespür": (
        "(AF) Mit Hilfe ihrer übrigen Sinne, zum Beispiel einem guten Geruchssinn oder einem guten Gehör, kann eine "
        "Kreatur mit Blindgespür Dinge wahrnehmen, die sie nicht sehen kann. Die Kreatur muss für gewöhnlich keine "
        "Würfe auf Wahrnehmung ausführen, um den genauen Standort eines Wesens innerhalb der Reichweite ihres "
        "Blindgespürs zu bestimmen, solange sie freie Schusslinie zu dem Wesen hat. Allerdings hat jeder Gegner, "
        "den die Kreatur mit Blindgespür nicht sehen kann, gegen diese nach wie vor vollständige Tarnung. Die "
        "Kreatur hat also bei Angriffen auf Gegner mit Tarnung nach wie vor die normale Fehlschlagchance. Die "
        "Bewegung einer Kreatur mit Blindgespür wird nach wie vor durch ihre Sicht beeinflusst. Kreaturen mit "
        "Blindgespür verlieren außerdem genau wie andere Kreaturen ihren Geschicklichkeitsbonus auf die "
        "Rüstungsklasse, wenn sie von Kreaturen angegriffen werden, die sie nicht sehen können."
    ),
    "Anspringen": (
        "(AF) Wenn eine Kreatur mit dieser besonderen Fähigkeit einen Sturmangriff ausführt, kann sie einen vollen "
        "Angriff machen (eingeschlossen Krallenangriffe, falls die Kreatur auch diese besondere Fähigkeit besitzt)."
    ),
    "Ergreifen": (
        "(AF) Wenn eine Kreatur mit diesem besonderen Angriff einen Treffer mit dem jeweiligen Angriff erzielt (im "
        "Normalfall ein Klauen- oder Bissangriff), verursacht sie den normalen Schaden und versucht gleichzeitig "
        "mit einer Freien Aktion einen Ringkampf zu starten. Dabei riskiert sie keinen Gelegenheitsangriff. Diese "
        "hat die Wahl, ob sie einen normalen Ringkampf beginnen möchte oder ob sie einfach den Körperteil, mit dem "
        "sie Ergreifen eingesetzt hat, dazu verwenden möchte, den Gegner festzuhalten. Im zweiten Fall erhält sie "
        "einen Malus von -20 auf ihren Kampfmanöverwurf, mit dem sie den Ringkampf beginnen und aufrecht erhalten "
        "will, gilt aber nicht selbst als im Ringkampf befindlich. Ein erfolgreicher Haltegriff verursacht nur dann "
        "Extraschaden, wenn die Kreatur auch noch über den besonderen Angriff Würgen verfügt. Wenn die Kreatur "
        "ihren Gegner nicht würgt, verursacht sie mit jedem erfolgreichen Wurf auf Ringkampf, den sie in "
        "aufeinander folgenden Runden erzielt, automatisch den Schaden, der auch durch den Angriff verursacht "
        "wird, mit dem sie den Haltegriff einleitete. In dem anderen Fall verursacht sie auch zusätzlichen "
        "Würgeschaden (dessen Höhe in der Beschreibung der Kreatur angegeben ist)."
    ),
    "Krallen": (
        "(AF) Kreaturen mit diesem besonderen Angriff erhalten unter gewissen Umständen zusätzliche natürliche "
        "Angriffe. Das ist meistens der Fall, wenn sie sich mit einem Gegner im Ringkampf befinden. Zusätzlich zu "
        "den Optionen, die allen Ringkämpfern offen stehen, erhält ein Monster mit der Fähigkeit Krallen zwei "
        "zusätzliche Klauenangriffe, die es nur gegen einen festgehaltenen Feind einsetzen kann. Monster mit der "
        "Fähigkeit Krallen müssen ihren Zug bereits im Ringkampf befindlich beginnen, wenn sie die Krallen "
        "einsetzen wollen, können also nicht in derselben Runde einen Ringkampf starten und ihre Klauen einsetzen."
    ),
    "Würgen": (
        "(AF) Kreaturen, die diesen besonderen Angriff besitzen, können ihre Gegner zerquetschen, indem sie "
        "Wuchtschaden verursachen, wenn ihnen ein Wurf auf Ringkampf gelingt (dieser Effekt gilt zusätzlich zu "
        "allen anderen durch einen erfolgreichen Wurf auf Ringkampf verursachten Effekten, inklusive "
        "Zusatzschaden)."
    ),
    "Todesrolle": (
        "(AF) Wenn die Kreatur einen Gegner ihrer Größenkategorie oder kleiner in den Ringkampf verwickelt hat, "
        "kann sie mit einem erfolgreichen Ringkampfangriff eine Todesrolle ausführen. Das Tier klammert sich an "
        "seinen Gegner, zieht seine Beine an den Rumpf und beginnt herumzurollen, wobei es an seinem Opfer reißt. "
        "Dieses erleidet den Bissschaden der Kreatur und wird zu Boden geworfen. Ist die Kreatur bei dem Versuch "
        "erfolgreich, bleibt sie im Ringkampf."
    ),
    "Sprint": "(AF) Die Kreatur kann einmal in der Minute ihre Bewegungsrate auf Land für eine Runde auf 12 m erhöhen.",
    "Sprinten": (
        "(AF) Die Kreatur kann einmal in der Stunde bei einem Sturmangriff das 10fache ihrer Bewegungsrate "
        "erreichen."
    ),
    "Zu-Fall-bringen": (
        "(AF) Kreaturen mit dem besonderen Angriff Zu-Fall-bringen können versuchen ihre Gegner mit einer Freien "
        "Aktion zu Fall zu bringen, ohne dabei einen Gelegenheitsangriff zu provozieren. Dazu müssen sie mit einem "
        "bestimmten Angriff einen Treffer erzielen. Wenn der Versuch fehlschlägt, wird die angreifende Kreatur "
        "nicht selbst zu Boden geworfen."
    ),
    "Wildheit": (
        "(AF) Wilde Kreaturen bleiben auch dann bei Bewusstsein und kampffähig, wenn ihre TP unter 0 fallen. Die "
        "Kreatur befindet sich im Zustand wankend und verliert in jeder Runde 1 TP. Wenn die Anzahl der TP dem "
        "negativen Konstitutionswert der jeweiligen Kreatur entspricht, stirbt diese."
    ),
    "Gift": (
        "(AF) Kreaturen mit dieser Fähigkeit können diejenigen, die sie angreifen, vergiften. Der Rettungswurf "
        "gegen ein Gift ist meistens ein Zähigkeitswurf gegen SG 10 + 1/2 Volkstrefferwürfel + KO-Modifikator der "
        "vergiftenden Kreatur. Gifte können durch Gift neutralisieren und ähnliche Effekte geheilt werden."
    ),
    "Kampfrausch": "(AF) Die Kreatur kann wie ein Barbar in Kampfrausch verfallen, für 6 Runden am Tag.",
    "Spucken": (
        "(AF) Einmal in der Stunde kann die Kreatur ihren Mageninhalt hochwürgen und diesen auf ein einzelnes Ziel "
        "innerhalb von 3 m spucken (Berührungsangriff im Fernkampf). Das Ziel ist für 1W4 Runden kränkelnd."
    ),
    "Luft anhalten": (
        "(AF) Die Kreatur kann für einen Zeitraum entsprechend ihres Konstitutionsattributswertes x 6 in Minuten "
        "die Luft anhalten, ehe sie zu ertrinken droht."
    ),
    "Kampfsicher": (
        "(AF) Das Tier ist dazu ausgebildet, einen Reiter in den Kampf zu tragen (Kampfausbildung): es kennt die "
        "Tricks Angreifen, Bei Fuß gehen, Kommen, Verteidigen, Wachen und Zurückziehen."
    ),
}
ABILITY_ALIASES = {"zu fall bringen": "Zu-Fall-bringen", "kampfsicher": "Kampfsicher"}

# The pseudo class's own abilities (PRD "Speziell"), by name.
COMPANION_ABILITY_TEXTS: dict[str, str] = {
    "Verbindung": (
        "(AF) Der Meister kann mit dem Gefährten als Freie Aktion umgehen und ihn mit einer Bewegungsaktion "
        "antreiben, selbst wenn er keinen Rang in Mit Tieren umgehen haben sollte. Der Meister erhält einen "
        "Situationsbonus von +4 auf alle Würfe auf Tierempathie und Mit Tieren umgehen, die den Gefährten betreffen."
    ),
    "Zauber teilen": (
        "(AF) Der Meister kann Zauber, die er nur auf sich selber sprechen könnte, auch auf den Gefährten wirken "
        "(als Zauber mit der Reichweite Berührung). Dies können auch Zauber sein, die normalerweise keinen Effekt "
        "auf Tiere haben. Zauber, die auf diese Art gewirkt werden, müssen von einer Klasse kommen, die einen "
        "Tiergefährten gewährt. Diese Fähigkeit erlaubt es nicht, mit einem Tiergefährten Eigenschaften zu teilen, "
        "die keine Zauber sind, auch wenn sie wie Zauber funktionieren."
    ),
    "Entrinnen": (
        "(AF) Ist der Gefährte einem Angriff ausgesetzt, der einen Reflexwurf für halben Schaden erlaubt, erhält der "
        "Gefährte bei gelungenem Rettungswurf keinen Schaden."
    ),
    "Hingabe": "(AF) Der Gefährte erhält einen Moralbonus von +4 auf Willenswürfe gegen Verzauberungen und Verzauberungseffekte.",
    "Mehrfachangriff": (
        "Der Gefährte erhält, sofern er es nicht schon hat, Mehrfachangriff als Bonustalent, wenn er über drei oder "
        "mehr natürliche Angriffe verfügt. Hat er keine drei natürlichen Angriffe, erhält er einen zusätzlichen "
        "Angriff mit einer seiner natürlichen Waffen, wenn auch mit einem Malus von –5."
    ),
    "Verbessertes Entrinnen": (
        "(AF) Ist der Gefährte einem Angriff ausgesetzt, der einen Reflexwurf für halben Schaden erlaubt, erhält der "
        "Gefährte bei gelungenem Rettungswurf keinen und bei misslungenem Wurf nur halben Schaden."
    ),
}
COMPANION_CLASS_SKILLS = ["Akrobatik", "Fliegen", "Heimlichkeit", "Klettern", "Schwimmen", "Wahrnehmung"]

# Entitlements: trigger (class, ability name, choice name) -> species list.
# A species entry is a PRD species name, optionally with master sizes/min level.
DRUID_LIST = "druid"
SLOT_GRANTS: list[tuple[str, str, str, str | list]] = [
    ("Druide", "Tiergefährte (Druide)", "Tiergefährte", DRUID_LIST),
    ("Kleriker", "Tiergefährte", "Domäne der Tiere", DRUID_LIST),
    ("Hexenmeister", "Tiergefährte", "Sylvanische Blutlinie", DRUID_LIST),
    (
        "Waldläufer",
        "Tiergefährte (Bund des Jägers)",
        "Tiergefährte",
        # PRD Waldläufer list; "Schreckensratte" isn't a Druide species and
        # has no statblock yet, so it's left out.
        ["Dachs", "Hund", "Kamel", "Pferd", "Pony", "Raubkatze, Klein", "Giftschlange", "Würgeschlange", "Vogel",
         "Wolf", "Hai"],
    ),
    (
        "Paladin",
        "Göttlicher Bund: Reittier",
        "Reittier",
        [("Pferd", ["Mittelgroß"], None), ("Pony", ["Klein"], None), "Wildschwein", "Hund", "Kamel"],
    ),
    (
        "Mystiker",
        "Gebundenes Reittier",
        "Gebundenes Reittier",
        [("Kamel", ["Mittelgroß"], None), ("Pferd", ["Mittelgroß"], None), ("Pony", ["Klein"], None),
         ("Wolf", ["Klein"], None), ("Wildschwein", ["Klein"], 4), ("Hund", ["Klein"], 4)],
    ),
]

KEY_RE = re.compile(
    r"^(Größe|Bewegungsrate|RK|Angriff|Attributswerte|Besondere Eigenschaften|Besondere Angriffe)\s*:?\s*(.*)$"
)
ADVANCEMENT_RE = re.compile(r"^Aufstieg auf die (vierte|siebte) Stufe:?\s*$")
ATTACK_RE = re.compile(r"^(?:(\d+)\s+)?(.+?)(1)?\s*\((.*)\)$")
DICE_RE = re.compile(r"^(\d+W\d+)\s*(?:(?:plus|\+)\s*(.*))?$")


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


def fetch_text(url: str) -> str:
    """The page's content block as plain text lines (scripts/README.md §2)."""
    raw = urllib.request.urlopen(url, timeout=30).read().decode("iso-8859-1")
    block = re.search(r'<div id="page" class="page">(.*?)<script type="text/javascript">', raw, re.S).group(1)
    text = re.sub(r"<br\s*/?>", "\n", block)
    text = re.sub(r"</(p|h\d|tr|li|div)>", "\n", text)
    text = re.sub(r"</t[dh]>", " | ", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text).replace("&nbsp;", " "))
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.strip() for line in text.split("\n") if line.strip())


def split_top_level(text: str, separators: tuple[str, ...]) -> list[tuple[str, str | None]]:
    """Splits on `separators` outside parentheses; returns (part, the
    separator that preceded it)."""
    parts: list[tuple[str, str | None]] = []
    depth = 0
    current = ""
    previous: str | None = None
    i = 0
    while i < len(text):
        char = text[i]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if depth == 0:
            match = next((sep for sep in separators if text.startswith(sep, i)), None)
            if match is not None:
                parts.append((current.strip(), previous))
                previous = match
                current = ""
                i += len(match)
                continue
        current += char
        i += 1
    if current.strip():
        parts.append((current.strip(), previous))
    return parts


def parse_attacks(text: str) -> list[dict]:
    attacks = []
    for part, separator in split_top_level(text, (", ", " oder ")):
        match = ATTACK_RE.match(part)
        if match is None:
            raise ValueError(f"unparsed attack: {part!r}")
        count, name, footnote, inner = match.groups()
        dice_match = DICE_RE.match(inner.strip())
        damage_type, secondary = ATTACK_KINDS.get(name, ("H/S/W", True))
        attacks.append(
            {
                "name": name,
                "count": int(count) if count else 1,
                "dice": dice_match.group(1) if dice_match else None,
                "damage_type": damage_type if dice_match else None,
                "secondary": secondary or footnote == "1",
                "note": (dice_match.group(2) if dice_match else inner.strip()) or None,
                "alternative": separator == " oder " or dice_match is None,
            }
        )
    return attacks


def parse_ability_list(text: str) -> list[tuple[str, str | None]]:
    """"Anspringen, Ergreifen, Krallen (1W6)" -> [(canonical name, detail)]."""
    result = []
    for part, _separator in split_top_level(text, (", ",)):
        match = re.match(r"^(.+?)\s*(?:\((.*)\))?$", part)
        name, detail = match.group(1).strip(), match.group(2)
        canonical = ABILITY_ALIASES.get(name.lower(), name)
        canonical = next((key for key in ABILITY_TEXTS if key.lower() == canonical.lower()), canonical)
        result.append((canonical, detail))
    return result


def parse_species(text: str, start_marker: str) -> list[dict]:
    """Every statblock after `start_marker`: a name line followed by
    "Spielwerte zu Beginn:"."""
    lines = text.split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith(start_marker))
    lines = lines[start + 1 :]
    species: list[dict] = []
    current: dict | None = None
    stage: dict | None = None
    for index, line in enumerate(lines):
        if index + 1 < len(lines) and lines[index + 1].startswith("Spielwerte zu Beginn"):
            current = {"name": line, "stages": []}
            species.append(current)
            stage = None
            continue
        if current is None:
            continue
        if line.startswith("Spielwerte zu Beginn"):
            stage = {"level": 1, "fields": {}}
            current["stages"].append(stage)
            continue
        advancement = ADVANCEMENT_RE.match(line)
        if advancement:
            stage = {"level": 4 if advancement.group(1) == "vierte" else 7, "fields": {}}
            current["stages"].append(stage)
            continue
        key = KEY_RE.match(line)
        if key and stage is not None:
            stage["fields"][key.group(1)] = key.group(2).strip()
        elif re.match(r"^\d", line) and stage is not None:
            continue  # footnote line ("1Dies ist eine sekundäre natürliche Waffe …")
        elif stage is not None and not key:
            # A line that isn't a statblock key ends the list.
            if stage["fields"]:
                break
    return species


def parse_scores(text: str, absolute: bool) -> dict[str, int]:
    scores = {}
    for ability, sign, value in re.findall(r"\b(ST|GE|KO|IN|WE|CH)\s*([+\-–]?)\s*(\d+)", text):
        number = int(value)
        if sign in ("-", "–"):
            number = -number
        scores[ability] = number
    if absolute:
        assert set(scores) == {"ST", "GE", "KO", "IN", "WE", "CH"}, text
    return scores


def parse_speeds(text: str) -> tuple[dict[str, int], str | None]:
    speeds: dict[str, int] = {}
    maneuverability = None
    for part in text.split(","):
        part = part.strip()
        match = re.match(r"^(?:(Klettern|Schwimmen|Fliegen|Graben)\s+)?(\d+)\s*m(?:\s*\((.+)\))?$", part)
        if match is None:
            raise ValueError(f"unparsed speed: {part!r}")
        mode, meters, extra = match.groups()
        speeds[SPEED_KEYS[mode] if mode else "land"] = int(meters)
        if mode == "Fliegen" and extra:
            maneuverability = {"normal": "Durchschnittlich"}.get(extra, extra.capitalize())
    return speeds, maneuverability


def short_name(name: str) -> str:
    """"Raubkatze, Klein (Gepard, Leopard)" -> "Raubkatze, Klein"."""
    return re.sub(r"\s*\(.*\)$", "", name).strip()


def main() -> None:
    races = load("base_races.json")
    race_abilities = load("base_race_abilities.json")
    stages_out: list[dict] = []
    stage_abilities_out: list[dict] = []

    ability_id_by_name: dict[str, str] = {"Dämmersicht": DAEMMERSICHT_ABILITY_ID}
    for name, description in ABILITY_TEXTS.items():
        aid = uid("species-ability", name)
        ability_id_by_name[name] = aid
        race_abilities.append({"id": aid, "name": name, "description": description})

    race_id_by_short_name: dict[str, str] = {}
    for url, source_label, marker in SPECIES_SOURCES:
        for spec in parse_species(fetch_text(url), marker):
            short = short_name(spec["name"])
            race_id = uid("species", short)
            race_id_by_short_name[short] = race_id
            races.append(
                {
                    "id": race_id,
                    "code": "companion-" + re.sub(r"[^a-z0-9]+", "-", short.lower()).strip("-"),
                    "name": spec["name"],
                    "short_description": f"Tiergefährte ({source_label})",
                    "companion_kind": "animal_companion",
                    "creature_type": "Tier",
                    "source": source_label,
                }
            )
            for stage in spec["stages"]:
                fields = stage["fields"]
                is_base = stage["level"] == 1
                row = {
                    "id": uid("stage", short, str(stage["level"])),
                    "race_id": race_id,
                    "level": stage["level"],
                    "size": SIZES[fields["Größe"].lower()] if "Größe" in fields else None,
                    "natural_armor": int(re.search(r"\+(\d+)", fields["RK"]).group(1)) if "RK" in fields else 0,
                    "ability_scores": parse_scores(fields.get("Attributswerte", ""), absolute=is_base),
                    "speeds": None,
                    "fly_maneuverability": None,
                    "natural_attacks": parse_attacks(fields["Angriff"]) if "Angriff" in fields else None,
                }
                if is_base:
                    row["speeds"], row["fly_maneuverability"] = parse_speeds(fields["Bewegungsrate"])
                    assert row["size"] is not None, spec["name"]
                abilities: list[tuple[str, str | None]] = []
                for key in ("Besondere Eigenschaften", "Besondere Angriffe"):
                    if key in fields:
                        abilities += parse_ability_list(fields[key])
                # Riders inside an attack ("Biss (1W6 plus Zu Fall bringen)", "plus Gift"),
                # and a dice-less special attack that is itself an ability (Spucken).
                for attack in row["natural_attacks"] or []:
                    if attack["dice"] is None and attack["name"] in ABILITY_TEXTS:
                        abilities.append((attack["name"], None))
                    for rider in ("Zu Fall bringen", "Zu-Fall-bringen", "Gift"):
                        if attack["note"] and rider.lower() in attack["note"].lower():
                            abilities.append((ABILITY_ALIASES.get(rider.lower(), rider), None))
                for name, detail in abilities:
                    if name not in ability_id_by_name:
                        raise ValueError(f"unknown species ability {name!r} ({spec['name']})")
                    # A detail with dice is an extra attack (Krallen = rake,
                    # Würgen = constrict); other details are notes on the stage's attacks.
                    if detail and re.match(r"^\d+W\d+$", detail):
                        row["natural_attacks"] = (row["natural_attacks"] or _inherited_attacks(stages_out, race_id)) + [
                            {
                                "name": name,
                                "count": 2 if name == "Krallen" else 1,
                                "dice": detail,
                                "damage_type": "H" if name == "Krallen" else "W",
                                "secondary": False,
                                "note": "nur gegen einen festgehaltenen Gegner" if name == "Krallen" else "bei gelungenem Ringkampfwurf",
                                "alternative": True,
                            }
                        ]
                    elif detail and name == "Gift":
                        for attack in row["natural_attacks"] or []:
                            if attack["note"] and "gift" in attack["note"].lower():
                                attack["note"] = f"Gift ({detail})"
                    stage_abilities_out.append(
                        {
                            "id": uid("stage-ability", row["id"], name),
                            "stage_id": row["id"],
                            "ability_id": ability_id_by_name[name],
                        }
                    )
                stages_out.append(row)
            print(f"{spec['name']}: {len(spec['stages'])} stages")

    save("base_races.json", races)
    save("base_race_abilities.json", race_abilities)
    save("base_companion_species_stages.json", stages_out)
    save("base_companion_species_stage_abilities.json", stage_abilities_out)

    # ---- progression ----
    progression = []
    text = fetch_text(PROGRESSION_SOURCE)
    lines = text.split("\n")
    header = lines.index(next(line for line in lines if line.startswith("Stufe | TW |")))
    companion_abilities = load("base_class_abilities.json")
    class_ability_ids = {}
    for name, description in COMPANION_ABILITY_TEXTS.items():
        aid = uid("companion-ability", name)
        class_ability_ids[name] = aid
        companion_abilities.append({"id": aid, "name": name, "description": description})
    save("base_class_abilities.json", companion_abilities)
    progression_abilities = []
    for line in lines[header + 1 : header + 21]:
        cells = [cell.strip() for cell in line.split("|")]
        level, hd, _bab, _ref, _wil, _zah, _skills, _feats, nat, strdex, tricks, special = cells[:12]
        progression.append(
            {
                "id": uid("progression", level),
                "level": int(level),
                "hit_dice": int(hd),
                "natural_armor": int(nat.replace("+", "")),
                "str_dex_bonus": int(strdex.replace("+", "")),
                "bonus_tricks": int(tricks),
            }
        )
        for name in [s.strip() for s in special.split(",")]:
            if name in class_ability_ids:
                progression_abilities.append(
                    {"id": uid("progression-ability", level, name), "level": int(level), "ability_id": class_ability_ids[name]}
                )
            else:
                assert name in ("-", "Erhöhung eines Attributwertes"), name
    assert len(progression) == 20
    save("base_companion_progression.json", progression)
    save("base_companion_progression_abilities.json", progression_abilities)

    # ---- pseudo class ----
    base_classes = load("base_classes.json")
    companion_class_id = uid("class", COMPANION_CLASS_NAME)
    base_classes.append(
        {
            "id": companion_class_id,
            "name": COMPANION_CLASS_NAME,
            "hit_dice": 8,
            "arch_class_of": None,
            "casting_ability": None,
            "spell_tradition": None,
            "bab_progression": 0.75,
            "fort_save": True,
            "ref_save": True,
            "wil_save": False,
            "skill_points_base": 2,
            "is_companion_class": True,
        }
    )
    save("base_classes.json", base_classes)
    skill_id_by_name = {s["name"]: s["id"] for s in load("base_skills.json")}
    class_skills = load("base_class_skills.json")
    for name in COMPANION_CLASS_SKILLS:
        class_skills.append(
            {
                "id": uid("class-skill", name),
                "base_class_id": companion_class_id,
                "skill_id": skill_id_by_name[name],
                "option_choice_id": None,
            }
        )
    save("base_class_skills.json", class_skills)

    # ---- entitlements ----
    class_id_by_name = {c["name"]: c["id"] for c in base_classes if c["arch_class_of"] is None}
    groups = {g["id"]: g for g in load("base_class_option_groups.json")}
    choices = load("base_class_option_choices.json")
    ability_name_by_id = {a["id"]: a["name"] for a in companion_abilities}
    grants = load("base_class_ability_grants.json")
    slot_grants, slot_species = [], []
    for class_name, ability_name, choice_name, species_list in SLOT_GRANTS:
        class_id = class_id_by_name[class_name]
        choice_ids = {c["id"] for c in choices if c["name"] == choice_name and groups[c["group_id"]]["base_class_id"] == class_id}
        ability_ids = {
            g["ability_id"]
            for g in grants
            if g["base_class_id"] == class_id
            and g["option_choice_id"] in choice_ids
            and ability_name_by_id[g["ability_id"]] == ability_name
        }
        assert len(ability_ids) == 1, (class_name, ability_name, ability_ids)
        ability_id = ability_ids.pop()
        slot_id = uid("slot", ability_id, "primary")
        slot_grants.append(
            {
                "id": slot_id,
                "class_ability_id": ability_id,
                "track": "animal_companion",
                "slot_key": "primary",
                "level_offset": 0,
                "divisor": 1,
                "minimum": None,
            }
        )
        entries = list(race_id_by_short_name) if species_list == DRUID_LIST else species_list
        for entry in entries:
            name, sizes, min_level = entry if isinstance(entry, tuple) else (entry, None, None)
            slot_species.append(
                {
                    "id": uid("slot-species", slot_id, name),
                    "slot_grant_id": slot_id,
                    "race_id": race_id_by_short_name[name],
                    "master_sizes": sizes,
                    "min_level": min_level,
                }
            )
    save("base_companion_slot_grants.json", slot_grants)
    save("base_companion_slot_species.json", slot_species)
    print("Species:", len(race_id_by_short_name), "| stages:", len(stages_out), "| slots:", len(slot_grants))
    print("Companion class:", companion_class_id)


def _inherited_attacks(stages: list[dict], race_id: str) -> list[dict]:
    """The latest earlier stage's attacks — an advancement that only adds a
    special attack (Würgen) still keeps the base attacks."""
    for stage in reversed(stages):
        if stage["race_id"] == race_id and stage["natural_attacks"] is not None:
            return [dict(attack) for attack in stage["natural_attacks"]]
    return []


if __name__ == "__main__":
    main()
