"""Transforms `import_wondrous_items_prd.py`'s staging JSON into
`base_items.json`-shaped rows and merges them in (roadmap.md's "Wondrous-
Item-Katalog mit echter Attributsboni-Wirkung", decided 2026-08-04). Mirrors
`build_weapon_abilities_seed.py`'s role for the weapon-abilities catalog.

Three things happen here that the import script deliberately left raw:

1. `slot_raw` (German prose, e.g. "Handgelenke (GRW Hände)") is mapped to a
   `rules.equipment_slots` paperdoll slot key via `SLOT_TEXT_TO_KEY`. Unmapped
   values are skipped with a printed warning rather than guessed - none were
   observed in the 2026-08-04 import (both source pages fully covered), but
   the check stays as a tripwire against future re-imports.

2. `price_raw` (e.g. "4.000 GM (+2), 16.000 GM (+4), 36.000 GM (+6)") becomes
   a numeric price two ways:
   - `ABILITY_BONUS_ITEMS` names the 6 unambiguous single-attribute items
     (see roadmap.md's decision - the other attribute-boosting items grant a
     player-chosen or multi-attribute bonus and are deliberately left
     unstructured, same "don't guess" policy as everywhere else in this
     project's imports). Each becomes 3 rows, one per (+2/+4/+6) tier, each
     with its own parsed price and `granted_ability`/`ability_bonus`.
   - Every other item becomes exactly one row: the first GM amount found in
     `price_raw` is used as `price`; if there was more than one amount (a
     tiered or multi-variant price the app doesn't structure, e.g. the AC-
     deflection rings' +1..+5 tiers, or named-variant compound prices), the
     full raw price string is prefixed onto `description` so nothing is
     lost - matches this project's "quick reference, not a simulator"
     stance (see roadmap.md). "Preis verschieden" (Ionensteine's per-variant
     sub-table) has no amount at all; `price` falls back to 0, same flagged-
     placeholder convention `import_waffen_prd.py` uses for missing prices.

3. `activation`/`uses_per_day`/`max_charges` are deliberately left null for
   this bulk import - the prose ("einmal pro Tag", "3 Mal pro Tag", "immer
   aktiv", ...) is too varied to regex reliably without silently misreading
   some items, and getting this wrong is worse than leaving it blank for a
   manual pass (same reasoning as `BaseFeat.sub_choice_type` only tagging
   the 7 feats whose own text unambiguously named a choice, rather than
   guessing at the rest). A generic `BaseWondrousItem`-style HANDLERS
   registry isn't needed here since these fields are already-computed
   (composition) data, not behavior.

A single hand-authored "Zauberstab" row (category "wand") is added directly
in this script rather than scraped - PF1e wands aren't a fixed named
catalog, each instance stores its own spell (`CharacterGear.stored_spell_id`)
and charge count, see roadmap.md.

Usage:
    python build_wondrous_items_seed.py [-i staging.json]
"""

from __future__ import annotations

import argparse
import json
import re
import uuid
from pathlib import Path

STAGING_DEFAULT = "../app/fixtures/imported/wondrous_items_prd_import.json"
SEED_PATH = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed" / "base_items.json"

# Stable namespace so re-running the script produces the same item ids
# instead of fresh random UUIDs on every run.
NAMESPACE = uuid.UUID("7b2e9f4a-1c8d-4e6b-9a3f-5d7c2b8e1f4a")
WAND_ID = uuid.uuid5(NAMESPACE, "prd-wondrous-item-Zauberstab")

PRICE_RE = re.compile(r"([\d.]+)\s*GM")

# raw "Ausrüstungsplatz" text (base word before any "(...)" note) -> paperdoll
# slot key from rules/equipment_slots.py's SLOT_DEFINITIONS.
SLOT_TEXT_TO_KEY = {
    "Kopf": "kopf",
    "Stirn": "stirnband",
    "Augen": "augen",
    "Hals": "hals",
    "Schultern": "schultern",
    "Oberkörper": "brust",
    "Handgelenke": "handgelenke",
    "Arme": "handgelenke",
    "Körper": "koerper",
    "Gürtel": "guertel",
    "Hände": "haende",
    "Füße": "fuesse",
    "Ring": "ring",
}

# The 6 unambiguous single-attribute-bonus items (roadmap.md's decision) ->
# (ability code, {tier: crafting-cost-tier price already in price_raw}).
ABILITY_BONUS_ITEMS = {
    "Gürtel der großen Konstitution": "constitution",
    "Gürtel der Riesenstärke": "strength",
    "Gürtel der unglaublichen Geschicklichkeit": "dexterity",
    "Stirnreif der enormen Intelligenz": "intelligence",
    "Stirnreif der erwachten Weisheit": "wisdom",
    "Stirnreif des verführerischen Charismas": "charisma",
}


def parse_slot(slot_raw: str) -> str | None:
    base = slot_raw.split("(")[0].strip()
    return SLOT_TEXT_TO_KEY.get(base)


def parse_prices(price_raw: str) -> list[tuple[float, int | None]]:
    """Returns (amount, tier) pairs - tier is the "+N" in "4.000 GM (+2)" if
    present, else None. Amount has German thousand-separator dots stripped."""
    pairs = []
    for match in re.finditer(r"([\d.]+)\s*GM(?:\s*\(\+(\d+)\))?", price_raw):
        amount = float(match.group(1).replace(".", ""))
        tier = int(match.group(2)) if match.group(2) else None
        pairs.append((amount, tier))
    return pairs


def build_generic_row(entry: dict, item_id: uuid.UUID) -> dict:
    prices = parse_prices(entry["price_raw"])
    description = entry["description"]
    if len(prices) <= 1:
        price = prices[0][0] if prices else 0.0
    else:
        price = prices[0][0]
        note = f"Preis: {entry['price_raw']}."
        description = f"{note} {description}" if description else note
    return {
        "id": str(item_id),
        "name": entry["name"],
        "category": entry["category"],
        "price": price,
        "slot": parse_slot(entry["slot_raw"]),
        "weight_lb": None if entry["weight_raw"] == "-" else entry["weight_raw"],
        "description": description,
    }


def build_ability_bonus_rows(entry: dict, ability: str) -> list[dict]:
    prices = {tier: amount for amount, tier in parse_prices(entry["price_raw"]) if tier is not None}
    rows = []
    for tier in (2, 4, 6):
        if tier not in prices:
            continue
        item_id = uuid.uuid5(NAMESPACE, f"prd-wondrous-item-{entry['name']}-{tier}")
        rows.append(
            {
                "id": str(item_id),
                "name": f"{entry['name']} +{tier}",
                "category": entry["category"],
                "price": prices[tier],
                "slot": parse_slot(entry["slot_raw"]),
                "weight_lb": None if entry["weight_raw"] == "-" else entry["weight_raw"],
                "description": entry["description"],
                "granted_ability": ability,
                "ability_bonus": tier,
            }
        )
    return rows


def build_wand_row() -> dict:
    return {
        "id": str(WAND_ID),
        "name": "Zauberstab",
        "category": "wand",
        "price": 0.0,
        "slot": None,
        "weight_lb": None,
        "description": (
            "Ein Zauberstab speichert einen einzigen Zauber des 4. Grads oder niedriger, "
            "nutzbar bis zu 50 Mal. Welcher Zauber gespeichert ist und wie viele Ladungen "
            "noch verbleiben, wird pro Charakter-Exemplar erfasst (siehe stored_spell_id/"
            "charges_remaining). Kosten für einen neuen Zauberstab: Zaubergrad x "
            "Erschafferstufe x 750 GM - hier nicht berechnet, siehe "
            "http://prd.5footstep.de/Grundregelwerk/MagischeGegenstaende/Zauberstaebe."
        ),
        "activation": "activatable",
        "max_charges": 50,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", default=STAGING_DEFAULT)
    args = parser.parse_args()

    entries = json.loads(Path(args.input).read_text(encoding="utf-8"))

    new_rows = [build_wand_row()]
    skipped_slots: list[str] = []
    for entry in entries:
        ability = ABILITY_BONUS_ITEMS.get(entry["name"])
        if ability:
            new_rows.extend(build_ability_bonus_rows(entry, ability))
            continue
        item_id = uuid.uuid5(NAMESPACE, f"prd-wondrous-item-{entry['category']}-{entry['name']}")
        row = build_generic_row(entry, item_id)
        base_slot = entry["slot_raw"].split("(")[0].strip().lower()
        if row["slot"] is None and base_slot not in ("keiner", "-", ""):
            skipped_slots.append(f"{entry['name']} ({entry['slot_raw']})")
        new_rows.append(row)

    existing = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    existing_by_id = {row["id"]: row for row in existing}
    for row in new_rows:
        existing_by_id[row["id"]] = row

    SEED_PATH.write_text(
        json.dumps(list(existing_by_id.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Merged {len(new_rows)} rows into {SEED_PATH} (total {len(existing_by_id)}).")
    if skipped_slots:
        print(f"{len(skipped_slots)} items with an unmapped slot text: {skipped_slots}")


if __name__ == "__main__":
    main()
