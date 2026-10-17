"""Populates `base_companion_level_sources` from
`backend/app/fixtures/seed/base_companion_level_sources.json` (written by
`scripts/build_companion_level_sources.py`) — roadmap slice 10, step 1.

Idempotent: each row is upserted by its own `id`. Requires
`base_classes`, `base_class_abilities` and `base_feats` to be seeded first
(foreign keys).

Run with the project venv active and the database up:
    cd backend && python -m app.seed.companion_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models import BaseCompanionLevelSource

SEED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "seed"

_UUID_FIELDS = ("class_ability_id", "feat_id", "root_class_id")


def seed_companion_level_sources(db: Session) -> None:
    rows = json.loads((SEED_DIR / "base_companion_level_sources.json").read_text(encoding="utf-8"))
    for row in rows:
        row_id = UUID(row["id"])
        fields = {key: value for key, value in row.items() if key != "id"}
        for key in _UUID_FIELDS:
            fields[key] = UUID(fields[key]) if fields.get(key) else None
        instance = db.get(BaseCompanionLevelSource, row_id)
        if instance is None:
            db.add(BaseCompanionLevelSource(id=row_id, **fields))
        else:
            for key, value in fields.items():
                setattr(instance, key, value)
    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_companion_level_sources(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
