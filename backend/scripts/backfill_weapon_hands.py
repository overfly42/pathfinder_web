"""One-time backfill for `BaseItem.hands` (roadmap.md's Slice-4 weapon-slot
item, 2026-08-11): populates the "one"/"two" hands classification on every
weapon row in `backend/app/fixtures/seed/base_items.json` from the PRD
import's `subgroup` column (`backend/app/fixtures/imported/
waffen_prd_import.json`).

`subgroup` maps cleanly to hands for melee/firearm weapons
(Zweihandwaffen/Zweihändige Feuerwaffen* -> "two", Einhandwaffen/Leichte
Waffen/Einhändige Feuerwaffen* -> "one") but the PRD's single
"Fernkampfwaffen" heading mixes bows/most crossbows (two-handed) with hand
crossbows and every thrown weapon (one-handed) under one bucket with no
further column to disambiguate — `FERNKAMPFWAFFEN_HANDS` below is a
hand-checked classification of that subgroup's 36 names against the PRD
text, not a name-pattern guess.

Matched primarily by `id`, falling back to an exact `name` match: 9 of the 16
old placeholder weapon rows kept their original id when `import_waffen_prd.py`
enriched them in place (roadmap.md's "Waffenkatalog ohne Kampfwerte" — "9
matchen exakt einen PRD-Namen ... (ID/Preis unverändert)"), so an id-only
lookup misses them even though their damage/critical/etc. fields already came
from the PRD row under that name. The remaining 7 placeholder rows
(Streitkolben, Handaxt, Kompositlangbogen, "Armbrust, leicht"/"Armbrust,
schwer", Wurfmesser, Wurfnetz) match no PRD row by id *or* name and are left
with `hands` unset — they have no PRD data to classify from at all.

Idempotent, safe to re-run. Run once with the project venv active:
    cd backend && python scripts/backfill_weapon_hands.py
"""

import json
from pathlib import Path

IMPORTED_PATH = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "imported" / "waffen_prd_import.json"
SEED_PATH = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed" / "base_items.json"

FERNKAMPFWAFFEN_HANDS = {
    # Two-handed: bows and every crossbow except the hand crossbow variants.
    "Doppelarmbrust": "two",
    "Halblingsschleuderstab": "two",
    "Kompositbogen, kurz": "two",
    "Kompositbogen, lang": "two",
    "Kurzbogen": "two",
    "Langbogen": "two",
    "Leichte Armbrust": "two",
    "Leichte Repetierarmbrust": "two",
    "Leichte Unterwasserarmbrust": "two",
    "Schwere Armbrust": "two",
    "Schwere Repetierarmbrust": "two",
    "Schwere Unterwasserarmbrust": "two",
    # One-handed: hand crossbows, slings, blowguns, and every thrown weapon.
    "Amentum": "one",
    "Atlatl": "one",
    "Atlatlwurfpfeil": "one",
    "Blasrohr": "one",
    "Bolas": "one",
    "Bumerang": "one",
    "Chakram": "one",
    "Fangnetz": "one",
    "Handarmbrust": "one",
    "Hunga-Munga": "one",
    "Kestros": "one",
    "Kestroswurfpfeil (10)": "one",
    "Lasso": "one",
    "Netz": "one",
    "Pfeilröhre": "one",
    "Pilum": "one",
    "Repetierhandarmbrust": "one",
    "Schleuder": "one",
    "Schuriken (5)": "one",
    "Seilpfeil": "one",
    "Vergiftete Sand-Röhre": "one",
    "Wurfpfeil": "one",
    "Wurfschild": "one",
    "Wurfspeer": "one",
}


def hands_for(imported_row: dict) -> str | None:
    subgroup = imported_row.get("subgroup")
    if subgroup is None:
        return None
    if subgroup == "Zweihandwaffen" or subgroup.startswith("Zweihändige Feuerwaffen"):
        return "two"
    if subgroup in ("Einhandwaffen", "Leichte Waffen", "Waffenlose Angriffe") or subgroup.startswith(
        "Einhändige Feuerwaffen"
    ):
        return "one"
    if subgroup == "Fernkampfwaffen":
        classified = FERNKAMPFWAFFEN_HANDS.get(imported_row["name"])
        if classified is None:
            raise ValueError(f"No hands classification for Fernkampfwaffen row {imported_row['name']!r}")
        return classified
    raise ValueError(f"Unrecognized subgroup {subgroup!r} for {imported_row['name']!r}")


def main() -> None:
    imported_rows = json.loads(IMPORTED_PATH.read_text(encoding="utf-8"))
    imported_by_id = {row["id"]: row for row in imported_rows}
    imported_by_name = {row["name"]: row for row in imported_rows}
    seed_rows = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    updated = 0
    for row in seed_rows:
        if row.get("category") != "weapon":
            continue
        imported_row = imported_by_id.get(row["id"]) or imported_by_name.get(row["name"])
        if imported_row is None:
            continue
        hands = hands_for(imported_row)
        if hands is not None:
            row["hands"] = hands
            updated += 1

    SEED_PATH.write_text(json.dumps(seed_rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Backfilled hands on {updated} weapon rows.")


if __name__ == "__main__":
    main()
