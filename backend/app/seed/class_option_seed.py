"""Populates `base_class_option_groups`/`base_class_option_choices` from
`backend/app/fixtures/seed/base_class_option_groups.json` and
`base_class_option_choices.json` — DB-shaped, one file per table, explicit
`id` on every row, same convention as `skill_seed.py`. Replaces
`classes.json`'s `optionGroups` arrays as the source of truth for what a
class offers; `classes.json` is only where these rows were originally
authored from, not read at request time anymore.

Idempotent: each row is upserted by its own `id`, safe to re-run. Requires
`base_classes` to already be seeded (`class_seed.seed_classes`) since
`base_class_option_groups` rows FK into it.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.class_option_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.base_class import BaseClassOptionChoice, BaseClassOptionGroup

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


def seed_class_options(db: Session) -> None:
    for row in _load("base_class_option_groups.json"):
        _upsert(db, BaseClassOptionGroup, {**row, "base_class_id": UUID(row["base_class_id"])})
    db.flush()

    for row in _load("base_class_option_choices.json"):
        fields = {**row, "group_id": UUID(row["group_id"])}
        if fields.get("requires_choice_id") is not None:
            fields["requires_choice_id"] = UUID(fields["requires_choice_id"])
        _upsert(db, BaseClassOptionChoice, fields)

    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_class_options(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
