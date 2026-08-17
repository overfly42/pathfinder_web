"""Populates `base_items` from `backend/app/fixtures/seed/base_items.json` —
DB-shaped, one row per item with an explicit `id` and a `category` tag
(weapon/armor/shield/gear/tool/consumable), same convention as
`feat_seed.py`/`trait_seed.py`. Replaces the old frontend-shaped
`backend/app/fixtures/items.json` (superseded, not deleted).

Idempotent: each row is upserted by its own `id`, safe to re-run.

`seed_item_granted_spells` (separate, not called from `main()`) populates
`base_item_granted_spells` from `base_item_granted_spells.json` — requires
both `seed_items` here and `spell_seed.seed_spells` to have already run
(foreign keys into `base_items`/`base_spells`), same "document the
dependency, don't auto-chain it" convention `spell_seed.py`'s own docstring
uses for its `class_seed`/`class_option_seed` dependency.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.item_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.item import BaseItem, BaseItemGrantedSpell

SEED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "seed"


def _load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def seed_items(db: Session) -> None:
    for row in _load("base_items.json"):
        row_id = UUID(row["id"])
        instance = db.get(BaseItem, row_id)
        fields = {k: v for k, v in row.items() if k != "id"}
        if instance is None:
            db.add(BaseItem(id=row_id, **fields))
        else:
            for key, value in fields.items():
                setattr(instance, key, value)

    db.commit()


def seed_item_granted_spells(db: Session) -> None:
    """Populates `base_item_granted_spells` from
    `backend/app/fixtures/seed/base_item_granted_spells.json` — requires
    `seed_items`/`spell_seed.seed_spells` to have already run (foreign keys
    into `base_items`/`base_spells`)."""
    for row in _load("base_item_granted_spells.json"):
        row_id = UUID(row["id"])
        instance = db.get(BaseItemGrantedSpell, row_id)
        fields = {
            k: (UUID(v) if k in ("item_id", "spell_id") else v)
            for k, v in row.items()
            if k != "id"
        }
        if instance is None:
            db.add(BaseItemGrantedSpell(id=row_id, **fields))
        else:
            for key, value in fields.items():
                setattr(instance, key, value)

    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_items(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
