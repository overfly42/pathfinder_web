"""One-time backfill for `BaseItem.is_light`: populates whether a weapon row
counts as "light" for Waffenfinesse (`rules/feats.py`'s `WAFFENFINESSE`) from
the PRD import's `subgroup` column (`backend/app/fixtures/imported/
waffen_prd_import.json`), the same source `backfill_weapon_hands.py` already
uses for `hands`.

`subgroup == "Leichte Waffen"` -> `True`, every other classified subgroup ->
`False`, unclassified (no PRD `subgroup` at all) -> left unset. Matched
primarily by `id`, falling back to an exact `name` match, same as
`backfill_weapon_hands.py` (see that script's docstring for why both are
needed).

`FINESSE_EXCEPTIONS` then forces `True` on PF1e's named non-light
Waffenfinesse exceptions (Rapier, Peitsche, Stachelkette, Elfisches
Krummschwert) regardless of their real subgroup/weight class — RAW lets the
feat apply to these by name even though none of them is actually a light
weapon. `is_light` is therefore scoped to "Waffenfinesse-eligible", not a
literal weight-class flag (see `BaseItem.is_light`'s docstring).

Idempotent, safe to re-run. Run once with the project venv active:
    cd backend && python scripts/backfill_weapon_is_light.py
"""

import json
from pathlib import Path

IMPORTED_PATH = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "imported" / "waffen_prd_import.json"
SEED_PATH = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed" / "base_items.json"

FINESSE_EXCEPTIONS = {"Rapier", "Peitsche", "Stachelkette", "Elf. Krummschwert"}


def main() -> None:
    imported_rows = json.loads(IMPORTED_PATH.read_text(encoding="utf-8"))
    imported_by_id = {row["id"]: row for row in imported_rows}
    imported_by_name = {row["name"]: row for row in imported_rows}
    seed_rows = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    updated = 0
    for row in seed_rows:
        if row.get("category") != "weapon":
            continue
        if row["name"] in FINESSE_EXCEPTIONS:
            row["is_light"] = True
            updated += 1
            continue
        imported_row = imported_by_id.get(row["id"]) or imported_by_name.get(row["name"])
        if imported_row is None:
            continue
        subgroup = imported_row.get("subgroup")
        if subgroup is None:
            continue
        row["is_light"] = subgroup == "Leichte Waffen"
        updated += 1

    SEED_PATH.write_text(json.dumps(seed_rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Backfilled is_light on {updated} weapon rows.")


if __name__ == "__main__":
    main()
