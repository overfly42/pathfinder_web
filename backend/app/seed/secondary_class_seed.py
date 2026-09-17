"""Populates `base_secondary_class_ability_grants` from
`backend/app/fixtures/seed/base_secondary_class_ability_grants.json` — the
Sekundärklasse alternate rule's own grant table (see
`models/base_class.py`'s `BaseSecondaryClassAbilityGrant`). Same
"DB-shaped, one file, hand-owned ids, idempotent upsert" convention as
`race_seed.py` — the row ids are the only link between this data and any
future per-class content pass.

Starts empty (this is the architecture pass — see roadmap.md): a future
class-content pass adds rows here, one class at a time, the same way race/
class content already gets added.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.secondary_class_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models import BaseSecondaryClassAbilityGrant

SEED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "seed"


def seed_secondary_class_abilities(db: Session) -> None:
    rows = json.loads((SEED_DIR / "base_secondary_class_ability_grants.json").read_text(encoding="utf-8"))
    for row in rows:
        row_id = UUID(row["id"])
        fields = {
            **{
                k: v
                for k, v in row.items()
                if k not in ("id", "secondary_base_class_id", "ability_id", "option_choice_id")
            },
            "secondary_base_class_id": UUID(row["secondary_base_class_id"]),
            "ability_id": UUID(row["ability_id"]),
            "option_choice_id": UUID(row["option_choice_id"]) if row.get("option_choice_id") else None,
        }
        instance = db.get(BaseSecondaryClassAbilityGrant, row_id)
        if instance is None:
            db.add(BaseSecondaryClassAbilityGrant(id=row_id, **fields))
        else:
            for key, value in fields.items():
                setattr(instance, key, value)
    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_secondary_class_abilities(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
