"""Populates `base_skills`/`base_class_skills` from
`backend/app/fixtures/seed/base_skills.json` and `base_class_skills.json` —
DB-shaped, one file per table, explicit `id` on every row, same convention as
`race_seed.py`/`class_seed.py`. Replaces the old frontend-shaped
`backend/app/fixtures/skills.json` (superseded, not deleted) and
`classes.json`'s `classSkills` arrays.

Idempotent: each row is upserted by its own `id`, safe to re-run. Requires
`base_classes` to already be seeded (`class_seed.seed_classes`) since
`base_class_skills` rows FK into it, and `base_class_option_choices`
(`class_option_seed.seed_class_options`) for any row with a non-null
`option_choice_id` (Mystiker/Oracle's per-Mysterium bonus class skills).

Run with the project venv active and the database up:
    cd backend && python -m app.seed.skill_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.skill import BaseClassSkill, BaseSkill

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


def seed_skills(db: Session) -> None:
    for row in _load("base_skills.json"):
        _upsert(db, BaseSkill, row)
    db.flush()

    for row in _load("base_class_skills.json"):
        fields = {**row, "base_class_id": UUID(row["base_class_id"]), "skill_id": UUID(row["skill_id"])}
        if fields.get("option_choice_id") is not None:
            fields["option_choice_id"] = UUID(fields["option_choice_id"])
        _upsert(db, BaseClassSkill, fields)

    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_skills(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
