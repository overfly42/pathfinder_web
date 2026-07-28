"""Populates `base_races`/`base_race_abilities`/`race_ability_grants`/
`race_ability_replacements` from the per-table JSON files in
`backend/app/fixtures/seed/`. Those files are DB-shaped (one file per table,
explicit `id` on every row) rather than frontend-shaped like the old
`races.json` — the row ids are the only link between this data and
`backend/app/rules/race_abilities.py`'s handlers, so they're fixed, hand-owned
values, not derived at seed time.

Idempotent: each row is upserted by its own `id`, safe to re-run.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.race_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.race import BaseRace, BaseRaceAbility, RaceAbilityGrant, RaceAbilityReplacement

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


def seed_races(db: Session) -> None:
    for row in _load("base_races.json"):
        _upsert(db, BaseRace, row)
    db.flush()

    for row in _load("base_race_abilities.json"):
        _upsert(db, BaseRaceAbility, row)
    db.flush()

    for row in _load("race_ability_grants.json"):
        _upsert(db, RaceAbilityGrant, {**row, "race_id": UUID(row["race_id"]), "ability_id": UUID(row["ability_id"])})
    db.flush()

    for row in _load("race_ability_replacements.json"):
        _upsert(
            db,
            RaceAbilityReplacement,
            {
                **row,
                "base_race_id": UUID(row["base_race_id"]),
                "ability_id": UUID(row["ability_id"]),
                "replaces_ability_id": UUID(row["replaces_ability_id"]),
            },
        )

    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_races(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
