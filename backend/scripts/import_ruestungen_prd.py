"""Armor and shields from the PRD's "Tabelle: Rüstungen und Schilde"
(http://prd.5footstep.de/Grundregelwerk/Ausruestung/Ruestungen) into
`base_items.json`, with the Rüstungsmalus (`armor_check_penalty`) the
catalog didn't have (todos.md, 2026-08-20).

- Every armor/shield row of the table becomes a catalog item (category
  "armor"/"shield", `ac_bonus`, `max_dex_bonus` — the tower shield's +2 too
  —, `armor_weight_class` from the table's section, price, weight, the
  masterwork surcharge of 150 GM). Rows
  already in the catalog under the same name are updated in place.
- The four mock-era rows that predate any PRD import get their PRD name and
  values (their ids stay, so nothing referencing them breaks): "Halbplatte"
  (+9) is the PRD's Plattenpanzer (+8), "Vollplatte" the Ritterrüstung,
  "Lederrüstung, verstärkt" the Beschlagene Lederrüstung, "Rundschild"
  (9 GM, +1) the Leichter Stahlschild.
- "Brustplatte des Freibeuters" (a Brustplatte +1, magic and so masterwork)
  gets the Brustplatte's −4 lowered by masterwork: −3.

Run with the project venv active:
    cd backend && python scripts/import_ruestungen_prd.py
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
ID_NAMESPACE = uuid.UUID("3f9b2d6e-8a1c-4e7f-b5d3-6c0a9e2f4b18")
SOURCE = "http://prd.5footstep.de/Grundregelwerk/Ausruestung/Ruestungen"

SECTIONS = {
    "Leichte Rüstungen": ("armor", "light"),
    "Mittelschwere Rüstungen": ("armor", "medium"),
    "Schwere Rüstungen": ("armor", "heavy"),
    "Schilde": ("shield", None),
}
# Mock-era catalog row id -> its PRD name.
LEGACY_NAMES = {
    "be4ac20e-7875-4731-9c3f-769be0565dff": "Plattenpanzer",  # was "Halbplatte"
    "f6f79fd0-e822-400b-b6e9-df23bb9e0b8f": "Ritterrüstung",  # was "Vollplatte"
    "495054d7-729b-49a8-821b-182f1ec03cc4": "Beschlagene Lederrüstung",  # was "Lederrüstung, verstärkt"
    "222bf999-2f07-4726-ac36-c66894835191": "Leichter Stahlschild",  # was "Rundschild"
}
MASTERWORK_PRICE_DELTA = 150
FREIBEUTER_ID = "56e7bfc0-104e-4680-91c3-fd94ffbfd8f2"
FREIBEUTER_CHECK_PENALTY = -3  # Brustplatte −4, masterwork (magic armor) +1


def _number(cell: str) -> int | None:
    """"+5" -> 5, "- 1" -> -1, "-" -> None; footnote digits after a bonus
    ("+43" is "+4" with footnote 3) are cut off by the caller."""
    cell = cell.replace(" ", "")
    if cell in ("-", ""):
        return None
    return int(cell)


def parse_table(text: str) -> list[dict]:
    lines = text.split("\n")
    start = max(i for i, line in enumerate(lines) if line.startswith("Tabelle: Rüstungen und Schilde"))
    rows = []
    category = weight_class = None
    for line in lines[start + 1 :]:
        heading = line.rstrip(" |")
        if heading == "Extras":
            break
        if heading in SECTIONS:
            category, weight_class = SECTIONS[heading]
            continue
        cells = [cell.strip() for cell in line.split("|")]
        if category is None or len(cells) < 8:
            continue
        name, price, bonus, max_dex, penalty, _failure, _speed_9, _speed_6, weight = cells[:9]
        bonus = re.match(r"^\+(\d)", bonus).group(1)  # "+43": footnote 3
        rows.append(
            {
                "name": name,
                "category": category,
                "price": float(price.replace(" GM", "").replace(".", "")),
                "ac_bonus": int(bonus),
                "max_dex_bonus": _number(max_dex),
                "armor_check_penalty": _number(penalty) or 0,
                "armor_weight_class": weight_class,
                "weight_lb": weight,
            }
        )
    return rows


def main() -> None:
    path = SEED_DIR / "base_items.json"
    items = json.loads(path.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in items}
    for item_id, name in LEGACY_NAMES.items():
        by_id[item_id]["name"] = name
    by_name = {item["name"]: item for item in items if item["category"] in ("armor", "shield")}

    for row in parse_table(fetch_text(SOURCE)):
        existing = by_name.get(row["name"])
        if existing is None:
            existing = {"id": str(uuid.uuid5(ID_NAMESPACE, row["name"]))}
            items.append(existing)
            by_name[row["name"]] = existing
        # "Eine Rüstung oder ein Schild in Meisterarbeitsqualität kostet 150 GM
        # mehr als die normale Version."
        existing.update(row, masterwork_price_delta=MASTERWORK_PRICE_DELTA)
        print(f"{row['name']}: +{row['ac_bonus']}, Malus {row['armor_check_penalty']}, {row['armor_weight_class'] or 'Schild'}")
    by_id[FREIBEUTER_ID]["armor_check_penalty"] = FREIBEUTER_CHECK_PENALTY
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
