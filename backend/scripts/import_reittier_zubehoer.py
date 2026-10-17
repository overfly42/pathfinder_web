"""Riding gear for mounts and animal companions — roadmap slice 10's
remaining item "gear for companions". Fetches the PRD item pages and adds
the rows to `base_items.json` (category "gear", like the other adventuring
gear; prices in GM):

- http://prd.5footstep.de/Grundregelwerk/Ausruestung/Sattel — Militär-,
  Pack- und Reitsattel, each also as "Exotischer …" (for unusual mounts).
- …/Satteltaschen, …/Zaumzeug.

Their effects are the rider's (Militärsattel: +2 Reiten to stay in the
saddle) or plain storage — descriptive. Barding ("Pferdeharnisch") is no
item of its own: any armor worn by a non-humanoid companion is barding
(`sheet.py`), only its price differs (PRD "Rüstungen für ungewöhnliche
Kreaturen").

Run with the project venv active:
    cd backend && python scripts/import_reittier_zubehoer.py
    python -m app.seed.item_seed
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_companion_species import fetch_text  # noqa: E402

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
ID_NAMESPACE = uuid.UUID("2c7e9a1b-4d3f-4b8e-9c6a-1f0e2d3c4b5a")
BASE_URL = "http://prd.5footstep.de/Grundregelwerk/Ausruestung/"
PRICE_RE = re.compile(r"^\|?\s*(\d+) GM\s*\|")


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def parse_prices(text: str) -> list[tuple[str, int]]:
    """(name, price) from a page's "Gegenstand | Preis | Gewicht" table: a
    price line belongs to the name on the line before it (or on the same
    line); "Exotischer Sattel |" starts a group whose rows get the prefix."""
    rows: list[tuple[str, int]] = []
    prefix = ""
    previous = ""
    for line in text.split("\n"):
        if line.startswith("Exotischer Sattel"):
            prefix = "Exotischer "
            previous = ""
            continue
        same_line = re.match(r"^([^|]+?)\s*\|\s*(\d+) GM\s*\|", line)
        if same_line and not same_line.group(1).startswith("Gegenstand"):
            rows.append((same_line.group(1).strip(), int(same_line.group(2))))
        elif (price := PRICE_RE.match(line)) and previous:
            rows.append((prefix + previous, int(price.group(1))))
        if ":" in line and not line.startswith("|"):
            break  # the description starts
        previous = line.strip().rstrip("|").strip()
    return rows


def main() -> None:
    items = load()
    added = []
    for page in ("Sattel", "Satteltaschen", "Zaumzeug"):
        for name, price in parse_prices(fetch_text(BASE_URL + page)):
            row = {"id": uid("item", name), "name": name, "category": "gear", "price": price, "masterwork_price_delta": None}
            if any(item["name"] == name and item["id"] != row["id"] for item in items):
                continue  # already in the catalog under another id
            items = [item for item in items if item["id"] != row["id"]] + [row]
            added.append((name, price))
    (SEED_DIR / "base_items.json").write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, price in added:
        print(f"{name}: {price} GM")


def load() -> list[dict]:
    return json.loads((SEED_DIR / "base_items.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
