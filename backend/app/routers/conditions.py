from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseCondition

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
        }
        for condition in conditions
    ]
