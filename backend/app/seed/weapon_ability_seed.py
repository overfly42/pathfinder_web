"""Populates `base_weapon_special_abilities` from
`backend/app/fixtures/seed/base_weapon_special_abilities.json`
(`backend/scripts/build_weapon_abilities_seed.py`'s output) — DB-shaped, one
row per named magic weapon special ability, same convention as
`race_seed.py`/`item_seed.py`.

Idempotent: each row is upserted by its own `id`, safe to re-run.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.weapon_ability_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.item import BaseWeaponSpecialAbility

SEED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "seed"


def seed_weapon_abilities(db: Session) -> None:
    rows = json.loads((SEED_DIR / "base_weapon_special_abilities.json").read_text(encoding="utf-8"))
    for row in rows:
        row_id = UUID(row["id"])
        instance = db.get(BaseWeaponSpecialAbility, row_id)
        fields = {k: v for k, v in row.items() if k != "id"}
        if instance is None:
            db.add(BaseWeaponSpecialAbility(id=row_id, **fields))
        else:
            for key, value in fields.items():
                setattr(instance, key, value)

    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_weapon_abilities(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
