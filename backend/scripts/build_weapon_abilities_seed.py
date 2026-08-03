"""Transforms `../app/fixtures/imported/waffeneigenschaften_prd_import.json`
(`import_waffeneigenschaften_prd.py`'s staging output, one row per named
magic weapon special ability, with review-only fields like `price_modifier`/
`bonus_equivalent_conflict`) into the DB-shaped
`../app/fixtures/seed/base_weapon_special_abilities.json` consumed by
`app.seed.weapon_ability_seed` — same "staging file has extra fields for
human review, seed file is the trimmed DB row shape" split as
`build_feats_seed.py`.

Only `BaseWeaponSpecialAbility`'s own four content fields are kept (`name`,
`bonus_equivalent`, `applicable_categories`, `restriction_note`,
`description`) per roadmap.md's "Magische Verzauberung/Material als
Berechnung statt Freitext" decision — no price/roll data, this catalog is
composition-only (CLAUDE.md), never evaluated by rule logic.

Ids are deterministic (`uuid5` off a fixed namespace + the ability's own
name), so rerunning this script reproduces the same ids and
`app.seed.weapon_ability_seed`'s upsert-by-id stays idempotent across reruns
— names are stable (they're the PRD's own canonical ability names, source of
truth for matching), so hashing the name is safe here, unlike
`build_feats_seed.py`'s requirement-row hash which deliberately hashes
content instead.

Usage:
    python build_weapon_abilities_seed.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

IMPORT_PATH = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "imported" / "waffeneigenschaften_prd_import.json"
SEED_PATH = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed" / "base_weapon_special_abilities.json"

NAMESPACE = uuid.UUID("c3f6a1e2-9d4b-4a7c-8e1f-2b6d9a3c5f8e")


def main() -> None:
    staging = json.loads(IMPORT_PATH.read_text(encoding="utf-8"))

    seed_rows = []
    for row in staging:
        ability_id = uuid.uuid5(NAMESPACE, row["name"])
        seed_rows.append(
            {
                "id": str(ability_id),
                "name": row["name"],
                "bonus_equivalent": row["bonus_equivalent"],
                "applicable_categories": row["categories"],
                "restriction_note": row["restriction_note"],
                "description": row["description"],
            }
        )

    SEED_PATH.write_text(json.dumps(seed_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(seed_rows)} abilities to {SEED_PATH}")


if __name__ == "__main__":
    main()
