"""Populates `base_conditions` from `backend/app/fixtures/seed/base_conditions.json`
(roadmap slice 5) — DB-shaped, one row per condition/poison/disease with an
explicit `id`, same convention as `trait_seed.py`. Built by
`scripts/build_conditions_seed.py` (standard conditions hand-transcribed,
poisons/diseases fetched from the PRD).

Idempotent: each row is upserted by its own `id`, safe to re-run.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.condition_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.effect import BaseCondition

SEED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "seed"


def _load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def seed_conditions(db: Session) -> None:
    for row in _load("base_conditions.json"):
        row_id = UUID(row["id"])
        instance = db.get(BaseCondition, row_id)
        fields = {k: v for k, v in row.items() if k != "id"}
        if instance is None:
            db.add(BaseCondition(id=row_id, **fields))
        else:
            for key, value in fields.items():
                setattr(instance, key, value)

    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_conditions(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
