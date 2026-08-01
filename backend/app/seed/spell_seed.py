"""Populates the spell tables from `backend/app/fixtures/seed/base_spells.json`,
`base_spell_components.json`, `base_class_spells.json`,
`base_class_spells_known.json`, and `base_class_spell_grants.json` —
DB-shaped, same idempotent upsert-by-id convention as `feat_seed.py`/
`trait_seed.py`. Replaces the old frontend-shaped
`backend/app/fixtures/spells_by_class.json` (superseded, not deleted).
Requires `class_seed.py` to have already run (foreign keys into
`base_classes`), and — since `base_class_spell_grants.json` rows are
gated by bloodline (`option_choice_id`) — `class_option_seed.py` too.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.spell_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.spell import BaseClassSpell, BaseClassSpellGrant, BaseClassSpellsKnown, BaseSpell, BaseSpellComponent

SEED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "seed"


def _load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def _upsert(db: Session, model: type, row: dict, *, fk_fields: tuple[str, ...] = ()) -> None:
    row_id = UUID(row["id"])
    fields = {k: (UUID(v) if k in fk_fields and v is not None else v) for k, v in row.items() if k != "id"}
    instance = db.get(model, row_id)
    if instance is None:
        db.add(model(id=row_id, **fields))
    else:
        for key, value in fields.items():
            setattr(instance, key, value)


def seed_spells(db: Session) -> None:
    for row in _load("base_spells.json"):
        _upsert(db, BaseSpell, row)
    db.flush()

    for row in _load("base_spell_components.json"):
        _upsert(db, BaseSpellComponent, row, fk_fields=("spell_id",))
    for row in _load("base_class_spells.json"):
        _upsert(db, BaseClassSpell, row, fk_fields=("base_class_id", "spell_id"))
    for row in _load("base_class_spells_known.json"):
        _upsert(db, BaseClassSpellsKnown, row, fk_fields=("base_class_id",))
    for row in _load("base_class_spell_grants.json"):
        _upsert(db, BaseClassSpellGrant, row, fk_fields=("base_class_id", "option_choice_id", "spell_id"))

    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_spells(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
