"""Populates `base_class_abilities`/`base_class_ability_grants` from
`backend/app/fixtures/seed/base_class_abilities.json` and
`base_class_ability_grants.json` — DB-shaped, one file per table, explicit
`id` on every row, same convention as `race_seed.py`/`class_seed.py`.

Today this only seeds Krieger's (Fighter's) recurring bonus combat feat: one
shared `BaseClassAbility` catalog row ("Bonus-Kampftalent") granted via
several `BaseClassAbilityGrant` rows, one per granting level (1st and every
even level) — `BaseClassAbilityGrant`'s unique constraint includes `level`
precisely so the same ability can recur this way instead of needing a
near-duplicate catalog row per level. Other classes with bonus-feat-shaped
features (e.g. a Wizard's periodic bonus feat, a Rogue talent that grants a
feat) are deliberately not modeled yet — add more catalog/grant rows the
same way, tagged in `rules/feat_slots.py`'s `BONUS_FEAT_SLOT_ABILITY_IDS`,
when that data is needed. Not a general class-features model — see
`BaseClassAbility`'s docstring.

Idempotent: each row is upserted by its own `id`, safe to re-run. Requires
`base_classes` to already be seeded (`class_seed.seed_classes`) since
`base_class_ability_grants` rows FK into it.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.class_ability_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.base_class import BaseClassAbility, BaseClassAbilityGrant

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


def seed_class_abilities(db: Session) -> None:
    for row in _load("base_class_abilities.json"):
        _upsert(db, BaseClassAbility, row)
    db.flush()

    for row in _load("base_class_ability_grants.json"):
        _upsert(
            db,
            BaseClassAbilityGrant,
            {
                **row,
                "base_class_id": UUID(row["base_class_id"]),
                "ability_id": UUID(row["ability_id"]),
                "option_choice_id": UUID(row["option_choice_id"]) if row["option_choice_id"] else None,
            },
        )

    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_class_abilities(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
