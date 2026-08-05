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
        {"id": str(condition.id), "name": condition.name, "description": condition.description}
        for condition in conditions
    ]
