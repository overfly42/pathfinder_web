"""Populates `base_feats` from `backend/app/fixtures/seed/base_feats.json` —
DB-shaped, one row per feat with an explicit `id`, same convention as
`race_seed.py`/`class_seed.py`/`skill_seed.py`. Replaces the old
frontend-shaped `backend/app/fixtures/feats.json` (superseded, not deleted).

Idempotent: each row is upserted by its own `id`, safe to re-run.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.feat_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.feat import BaseFeat

SEED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "seed"


def _load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def seed_feats(db: Session) -> None:
    for row in _load("base_feats.json"):
        row_id = UUID(row["id"])
        instance = db.get(BaseFeat, row_id)
        fields = {k: v for k, v in row.items() if k != "id"}
        if instance is None:
            db.add(BaseFeat(id=row_id, **fields))
        else:
            for key, value in fields.items():
                setattr(instance, key, value)

    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_feats(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
