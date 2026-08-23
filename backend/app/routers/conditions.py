from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseCondition
from ..rules.effects import EFFECT_HANDLERS

router = APIRouter(prefix="/api/conditions", tags=["conditions"])


@router.get("")
def list_conditions(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    conditions = db.scalars(select(BaseCondition).order_by(BaseCondition.name)).all()
    return [
        {
            "id": str(condition.id),
            "name": condition.name,
            "description": condition.description,
            "type": condition.type,
            "defaultIncubationRounds": condition.default_incubation_rounds,
            "defaultDurationRounds": condition.default_duration_rounds,
            "defaultFrequencyRounds": condition.default_frequency_rounds,
            "defaultSuccessesRequired": condition.default_successes_required,
            # See `todos.md`'s "Effekt-Handler-Inventar" — most conditions
            # still only have a classification decision pending, no
            # `EFFECT_HANDLERS[id]` entry yet.
            "hasHandler": condition.id in EFFECT_HANDLERS,
        }
        for condition in conditions
    ]
