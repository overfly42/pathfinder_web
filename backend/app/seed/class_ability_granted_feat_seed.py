"""Populates `base_class_ability_granted_feats` from
`backend/app/fixtures/seed/base_class_ability_granted_feats.json` — one row
per (weapon/armor proficiency) class ability variant and the `BaseFeat` it
inherently confers, e.g. every "Umgang mit Waffen und Rüstungen" variant
mapped to its matching "Umgang mit ..." proficiency feats (skipped for
variants whose weapon list doesn't line up with a whole-category feat, e.g.
Magier's fixed dagger/quarterstaff/crossbow list, or only partially covered,
e.g. Kensai only gets the "einfache Waffen" row — its free choice of one
martial/exotic weapon has no whole-category feat to map to and no sub-choice
mechanism on class abilities to record which one, see `rules/proficiency.py`).
Same idempotent upsert-by-id convention as `class_ability_option_seed.py`.

Read at request time by `routers/feats.py`'s `_character_prereq_state` — see
`BaseClassAbilityGrantedFeat`'s docstring in `models/base_class.py` for why
this is a separate always-on grant rather than a `BaseClassAbilityFeatOption`
slot.

Requires `base_class_abilities` (`class_ability_seed.seed_class_abilities`)
and `base_feats` (`feat_seed.seed_feats`) to already be seeded.

Run with the project venv active and the database up:
    cd backend && python -m app.seed.class_ability_granted_feat_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.base_class import BaseClassAbilityGrantedFeat

SEED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "seed"


def seed_class_ability_granted_feats(db: Session) -> None:
    rows = json.loads((SEED_DIR / "base_class_ability_granted_feats.json").read_text(encoding="utf-8"))
    for row in rows:
        row_id = UUID(row["id"])
        fields = {"ability_id": UUID(row["ability_id"]), "feat_id": UUID(row["feat_id"])}
        instance = db.get(BaseClassAbilityGrantedFeat, row_id)
        if instance is None:
            db.add(BaseClassAbilityGrantedFeat(id=row_id, **fields))
        else:
            for key, value in fields.items():
                setattr(instance, key, value)

    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_class_ability_granted_feats(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
