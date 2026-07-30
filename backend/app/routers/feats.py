from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseFeat

router = APIRouter(prefix="/api/feats", tags=["feats"])


@router.get("")
def list_feats(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    feats = db.scalars(select(BaseFeat).order_by(BaseFeat.name)).all()
    return [
        {"id": str(feat.id), "name": feat.name, "description": feat.description, "type": feat.type}
        for feat in feats
    ]
