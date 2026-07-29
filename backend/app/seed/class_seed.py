"""Populates `base_classes` from `backend/app/fixtures/seed/base_classes.json` —
identity rows only (id + name), used as the FK target for
`CharacterLevel.base_class_id`. Class rules content (skill points, class
skills, archetypes, spell type, ...) stays in `classes.json`, joined by name
at read time; `name` here is the only link between the two.

Idempotent: each row is upserted by its own `id`, safe to re-run.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.class_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.base_class import BaseClass

SEED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "seed"


def _load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def _upsert(db: Session, model: type, row: dict) -> None:
    row_id = UUID(row["id"])
    instance = db.get(model, row_id)
    fields = {k: v for k, v in row.items() if k != "id"}
    if instance is None:
        db.add(model(id=row_id, **fields))
    else:
        for key, value in fields.items():
            setattr(instance, key, value)


def seed_classes(db: Session) -> None:
    for row in _load("base_classes.json"):
        _upsert(db, BaseClass, row)
    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_classes(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
