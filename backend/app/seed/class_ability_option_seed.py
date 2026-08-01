"""Populates `base_class_ability_feat_options`/`base_class_ability_spell_options`
from `backend/app/fixtures/seed/base_class_ability_feat_options.json` and
`base_class_ability_spell_options.json` — DB-shaped, one file per table, same
idempotent upsert-by-id convention as `class_ability_seed.py`.

These are the eligibility-pool tables from `roadmap.md`'s "pick from a
restricted list" plan: a row's presence is what makes a `BaseClassAbility`
a feat/spell slot at all (`ability_id` with no rows here just isn't one) —
see `BaseClassAbilityFeatOption`/`BaseClassAbilitySpellOption`'s docstrings
in `models/base_class.py` for the feat_type/feat_id (and spell_id/
source_class_id+source_grade) union-of-rows semantics.

Idempotent: each row is upserted by its own `id`, safe to re-run. Requires
`base_class_abilities` (`class_ability_seed.seed_class_abilities`),
`base_feats` (`feat_seed.seed_feats`), `base_class_option_choices`
(`class_option_seed.seed_class_options`), and — for the spell-option broad
filter's `source_class_id` — `base_classes` (`class_seed.seed_classes`) to
already be seeded.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.class_ability_option_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.base_class import BaseClassAbilityFeatOption, BaseClassAbilitySpellOption

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


def seed_class_ability_options(db: Session) -> None:
    for row in _load("base_class_ability_feat_options.json"):
        _upsert(db, BaseClassAbilityFeatOption, row, fk_fields=("ability_id", "option_choice_id", "feat_id"))
    for row in _load("base_class_ability_spell_options.json"):
        _upsert(
            db,
            BaseClassAbilitySpellOption,
            row,
            fk_fields=("ability_id", "option_choice_id", "spell_id", "source_class_id"),
        )

    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_class_ability_options(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
