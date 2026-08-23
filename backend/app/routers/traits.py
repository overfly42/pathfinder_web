from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseTrait
from ..rules.handlers import HANDLERS

router = APIRouter(prefix="/api/traits", tags=["traits"])


@router.get("")
def list_traits(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    traits = db.scalars(select(BaseTrait).order_by(BaseTrait.name)).all()
    return [
        {
            "id": str(trait.id),
            "name": trait.name,
            "description": trait.description,
            "area": trait.area,
            # camelCase on the wire to match the frontend's `TraitDef.skillChoiceAbility`
            # — same "backend picks the JSON shape a consumer wants" precedent as
            # `routers/feats.py`'s `subChoiceType`.
            "skillChoiceAbility": trait.skill_choice_ability,
            "hasHandler": trait.id in HANDLERS,
        }
        for trait in traits
    ]
