"""Populates `base_traits` from `backend/app/fixtures/seed/base_traits.json` —
DB-shaped, one row per trait with an explicit `id`, same convention as
`feat_seed.py`. Replaces the old frontend-shaped `backend/app/fixtures/traits.json`
(superseded, not deleted).

Idempotent: each row is upserted by its own `id`, safe to re-run.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.trait_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.trait import BaseTrait

SEED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "seed"


def _load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def seed_traits(db: Session) -> None:
    for row in _load("base_traits.json"):
        row_id = UUID(row["id"])
        instance = db.get(BaseTrait, row_id)
        fields = {k: v for k, v in row.items() if k != "id"}
        if instance is None:
            db.add(BaseTrait(id=row_id, **fields))
        else:
            for key, value in fields.items():
                setattr(instance, key, value)

    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_traits(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
