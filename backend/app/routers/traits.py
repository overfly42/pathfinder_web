from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseTrait

router = APIRouter(prefix="/api/traits", tags=["traits"])


@router.get("")
def list_traits(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    traits = db.scalars(select(BaseTrait).order_by(BaseTrait.name)).all()
    return [
        {"id": str(trait.id), "name": trait.name, "description": trait.description, "area": trait.area}
        for trait in traits
    ]
