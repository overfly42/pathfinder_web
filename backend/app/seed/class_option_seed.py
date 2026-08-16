"""Populates `base_class_option_groups`/`base_class_option_choices` from
`backend/app/fixtures/seed/base_class_option_groups.json` and
`base_class_option_choices.json` — DB-shaped, one file per table, explicit
`id` on every row, same convention as `skill_seed.py`. Replaces
`classes.json`'s `optionGroups` arrays as the source of truth for what a
class offers; `classes.json` is only where these rows were originally
authored from, not read at request time anymore.

Idempotent: each row is upserted by its own `id`, safe to re-run. Requires
`base_classes` to already be seeded (`class_seed.seed_classes`) since
`base_class_option_groups` rows FK into it — same "caller's responsibility"
convention every other seed module in this package uses (no seed function
calls another internally).

`base_class_option_choices.race_id` (2026-08-16, Advanced Race Guide
favored-class-bonus options, `scripts/import_favored_class_bonus_halbork.py`)
is the one exception to that convention: `seed_races` is called here
directly rather than left to 45+ existing call sites across the test suite
to each remember a new, easy-to-miss cross-domain dependency forever
(`base_classes` only ever gained *test-visible* callers after this module
already existed, so the original convention never had to survive a schema
change like this one) — `seed_races` is itself idempotent, so calling it
here even when a caller already seeded races elsewhere is a no-op, not a
correctness risk.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.class_option_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.base_class import BaseClassOptionChoice, BaseClassOptionGroup
from .race_seed import seed_races

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
    seed_races(db)

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
