"""Tricks and trainings ("Aufgaben") of the skill Mit Tieren umgehen —
roadmap slice 10 step 5 (tricks as data). Source:
http://prd.5footstep.de/Grundregelwerk/Fertigkeiten/Mit-Tieren-umgehen

Writes three seed files (`app/seed/companion_seed.py` loads them):

- `base_companion_tricks.json` — the 12 tricks of "Tier einen Trick
  beibringen" (`name`, `dc`, `description`, `cost` 1), plus the variant
  "Angreifen (alle Wesen)": the PRD's "Ein Tier darauf zu trainieren, alle
  Wesen … anzugreifen, wird als zwei Tricks gewertet" as its own row with
  `cost` 2 and `variant_of_id` → Angreifen (it includes Angreifen; both
  can't be picked together). "Spuren suchen" gets `required_ability_id` =
  the companion species' "Geruchssinn" (`BaseRaceAbility`).
- `base_companion_trick_purposes.json` — the 7 trainings of "Ein Tier für
  eine Aufgabe ausbilden" (`name`, `dc`, `weeks`, `description`).
- `base_companion_trick_purpose_tricks.json` — which tricks each training
  contains, parsed from "kennt die Tricks …" (the PRD writes "Kunststück
  vorführen" there for the trick "Kunststück").

Checked against the hand-typed `TRICK_HELP` in
`frontend/src/lib/companionLevels.ts` while importing (2026-10-25): tricks,
DCs and contents match; the training is called "Ein Kunststück vorführen"
on the PRD (was "Kunststück vorführen").

Run with the project venv active:
    cd backend && python scripts/import_companion_tricks.py
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
ID_NAMESPACE = uuid.UUID("7d1c3b5e-2a4f-4e6b-9c8d-0f1e2a3b4c5d")
URL = "https://prd.5footstep.de/Grundregelwerk/Fertigkeiten/Mit-Tieren-umgehen"

# The companion species' "Geruchssinn" (`base_race_abilities.json`, the
# "(AF)" monster ability every scent species stage links).
GERUCHSSINN_ABILITY_ID = "f5a4bb9b-3c0f-50e5-984d-10e627305523"
SCENT_TRICKS = {"Spuren suchen"}
ALL_CREATURES_VARIANT = "Angreifen (alle Wesen)"

ENTRY_RE = re.compile(r"^(?P<name>[^():]+?) \(SG (?P<dc>\d+)\): (?P<text>.+)$")
WEEKS_RE = re.compile(r"(\d+|zwei|drei|vier|fünf|sechs) ?Wochen")
NUMBER_WORDS = {"zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6}
KNOWS_RE = re.compile(r"kennt die Tricks (.+?)\.")
# Name in a training's trick list -> trick name.
TRICK_ALIASES = {"Kunststück vorführen": "Kunststück"}


def fetch_text(url: str) -> str:
    """The page's content block as plain text lines. Not
    `import_companion_species.fetch_text`: the site moved to a new layout
    (checked 2026-10-25) — https, UTF-8, content in `<article
    id="page-show">` instead of `<div id="page" class="page">`
    (scripts/README.md)."""
    raw = urllib.request.urlopen(url, timeout=30).read().decode("utf-8")
    block = re.search(r'<article id="page-show">(.*?)</article>', raw, re.S).group(1)
    text = re.sub(r"<br\s*/?>", "\n", block)
    text = re.sub(r"</(p|h\d|tr|li|div)>", "\n", text)
    text = re.sub(r"</t[dh]>", " | ", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text).replace("&nbsp;", " ")).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.strip() for line in text.split("\n") if line.strip())


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def section(lines: list[str], start: str, end: str) -> list[str]:
    first = next(i for i, line in enumerate(lines) if line.startswith(start))
    last = next(i for i, line in enumerate(lines) if line.startswith(end))
    return lines[first + 1 : last]


def parse_entries(lines: list[str]) -> list[dict]:
    entries = []
    for line in lines:
        match = ENTRY_RE.match(line)
        if match:
            entries.append({"name": match["name"].strip(), "dc": int(match["dc"]), "description": match["text"].strip()})
    return entries


def main() -> None:
    lines = fetch_text(URL).split("\n")
    trick_entries = parse_entries(section(lines, "Tier einen Trick beibringen", "Ein Tier für eine Aufgabe ausbilden"))
    purpose_entries = parse_entries(section(lines, "Ein Tier für eine Aufgabe ausbilden", "Ein wildes Tier aufziehen"))
    if len(trick_entries) != 12 or len(purpose_entries) != 7:
        raise SystemExit(f"unexpected page shape: {len(trick_entries)} tricks, {len(purpose_entries)} trainings")

    tricks = []
    for entry in trick_entries:
        tricks.append(
            {
                "id": uid("trick", entry["name"]),
                **entry,
                "cost": 1,
                "required_ability_id": GERUCHSSINN_ABILITY_ID if entry["name"] in SCENT_TRICKS else None,
                "variant_of_id": None,
            }
        )
    angreifen = next(trick for trick in tricks if trick["name"] == "Angreifen")
    tricks.append(
        {
            "id": uid("trick", ALL_CREATURES_VARIANT),
            "name": ALL_CREATURES_VARIANT,
            "dc": angreifen["dc"],
            "description": angreifen["description"],
            "cost": 2,
            "required_ability_id": None,
            "variant_of_id": angreifen["id"],
        }
    )
    trick_ids = {trick["name"]: trick["id"] for trick in tricks}

    purposes = []
    purpose_tricks = []
    for entry in purpose_entries:
        weeks = WEEKS_RE.search(entry["description"])
        purpose_id = uid("purpose", entry["name"])
        purposes.append({"id": purpose_id, **entry, "weeks": int(NUMBER_WORDS.get(weeks[1], weeks[1]))})
        names = re.split(r", | und ", KNOWS_RE.search(entry["description"])[1])
        for name in names:
            trick_id = trick_ids[TRICK_ALIASES.get(name, name)]
            purpose_tricks.append({"id": uid("purpose-trick", entry["name"], name), "purpose_id": purpose_id, "trick_id": trick_id})

    for filename, rows in (
        ("base_companion_tricks.json", tricks),
        ("base_companion_trick_purposes.json", purposes),
        ("base_companion_trick_purpose_tricks.json", purpose_tricks),
    ):
        (SEED_DIR / filename).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{filename}: {len(rows)} rows")


if __name__ == "__main__":
    main()
