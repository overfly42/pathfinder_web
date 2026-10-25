"""Populates the companion catalog tables (roadmap slice 10): level sources
(`scripts/build_companion_level_sources.py`, step 1) and species stages,
progression and entitlements (`scripts/import_companion_species.py`, step
2b), familiar species/table/entitlements (`scripts/import_familiars.py`,
step 4), tricks and trainings (`scripts/import_companion_tricks.py`, step
5), one fixture file per table.

Idempotent: each row is upserted by its own `id`. Requires `base_races`,
`base_classes`, `base_class_abilities` and `base_feats` to be seeded first
(foreign keys).

Run with the project venv active and the database up:
    cd backend && python -m app.seed.companion_seed
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..models import (
    BaseCompanionLevelSource,
    BaseCompanionProgression,
    BaseCompanionProgressionAbility,
    BaseCompanionSlotGrant,
    BaseCompanionSlotSpecies,
    BaseCompanionSpeciesStage,
    BaseCompanionSpeciesStageAbility,
    BaseCompanionTrick,
    BaseCompanionTrickPurpose,
    BaseCompanionTrickPurposeTrick,
    BaseFamiliarProgression,
    BaseFamiliarProgressionAbility,
)

SEED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "seed"

_UUID_FIELDS = {
    "class_ability_id", "feat_id", "root_class_id", "race_id", "stage_id", "ability_id", "slot_grant_id",
    "required_ability_id", "variant_of_id", "purpose_id", "trick_id",
}

# Foreign-key order.
_TABLES: tuple[tuple[str, type], ...] = (
    ("base_companion_level_sources.json", BaseCompanionLevelSource),
    ("base_companion_species_stages.json", BaseCompanionSpeciesStage),
    ("base_companion_species_stage_abilities.json", BaseCompanionSpeciesStageAbility),
    ("base_companion_progression.json", BaseCompanionProgression),
    ("base_companion_progression_abilities.json", BaseCompanionProgressionAbility),
    ("base_familiar_progression.json", BaseFamiliarProgression),
    ("base_familiar_progression_abilities.json", BaseFamiliarProgressionAbility),
    ("base_companion_slot_grants.json", BaseCompanionSlotGrant),
    ("base_companion_slot_species.json", BaseCompanionSlotSpecies),
    ("base_companion_tricks.json", BaseCompanionTrick),
    ("base_companion_trick_purposes.json", BaseCompanionTrickPurpose),
    ("base_companion_trick_purpose_tricks.json", BaseCompanionTrickPurposeTrick),
)


def _upsert_all(db: Session, filename: str, model: type) -> None:
    rows = json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))
    for row in rows:
        row_id = UUID(row["id"])
        fields = {key: value for key, value in row.items() if key != "id"}
        for key in _UUID_FIELDS & fields.keys():
            fields[key] = UUID(fields[key]) if fields[key] else None
        instance = db.get(model, row_id)
        if instance is None:
            db.add(model(id=row_id, **fields))
        else:
            for key, value in fields.items():
                setattr(instance, key, value)
    db.flush()


def seed_companions(db: Session) -> None:
    for filename, model in _TABLES:
        _upsert_all(db, filename, model)
    db.commit()


def main() -> None:
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_companions(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
