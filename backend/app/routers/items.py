from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseItem

router = APIRouter(prefix="/api/items", tags=["items"])


@router.get("")
def list_items(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    items = db.scalars(select(BaseItem).order_by(BaseItem.category, BaseItem.name)).all()
    return [
        {"id": str(item.id), "name": item.name, "category": item.category, "price": item.price} for item in items
    ]
