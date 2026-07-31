"""Populates `base_classes` from `backend/app/fixtures/seed/base_classes.json` —
each row is either a root class (`arch_class_of` null) or one archetype
variant of exactly one parent (`arch_class_of` = the parent's id), per
`readme.md`'s ER diagram. `name` joins back to `classes.json` for skill
points/class skills/spell type/etc.; `hit_dice`/`bab_progression`/
`fort_save`/`ref_save`/`wil_save` are only set on root rows.

Idempotent: each row is upserted by its own `id`, safe to re-run. Root rows
are upserted (and flushed) before archetype rows, since the latter's
`arch_class_of` FK must point at an already-persisted parent.

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


def _upsert_base_class(db: Session, row: dict) -> None:
    row_id = UUID(row["id"])
    arch_class_of = UUID(row["arch_class_of"]) if row["arch_class_of"] is not None else None
    fields = {
        "name": row["name"],
        "hit_dice": row["hit_dice"],
        "arch_class_of": arch_class_of,
        "casting_ability": row.get("casting_ability"),
        "spell_tradition": row.get("spell_tradition"),
        "bab_progression": row.get("bab_progression"),
        "fort_save": row.get("fort_save"),
        "ref_save": row.get("ref_save"),
        "wil_save": row.get("wil_save"),
        "skill_points_base": row.get("skill_points_base"),
    }
    instance = db.get(BaseClass, row_id)
    if instance is None:
        db.add(BaseClass(id=row_id, **fields))
    else:
        for key, value in fields.items():
            setattr(instance, key, value)


def seed_classes(db: Session) -> None:
    rows = _load("base_classes.json")
    for row in rows:
        if row["arch_class_of"] is None:
            _upsert_base_class(db, row)
    db.flush()

    for row in rows:
        if row["arch_class_of"] is not None:
            _upsert_base_class(db, row)
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
