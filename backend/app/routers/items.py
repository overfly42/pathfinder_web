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
        {
            "id": str(item.id),
            "name": item.name,
            "category": item.category,
            "price": item.price,
            "acBonus": item.ac_bonus,
            "maxDexBonus": item.max_dex_bonus,
            "damageSmall": item.damage_small,
            "damageMedium": item.damage_medium,
            "critical": item.critical,
            "weaponRange": item.weapon_range,
            "damageType": item.damage_type,
            "weaponType": item.weapon_type,
            "special": item.special,
            "weightLb": item.weight_lb,
            "description": item.description,
            "slot": item.slot,
            "activation": item.activation,
            "usesPerDay": item.uses_per_day,
            "maxCharges": item.max_charges,
            "grantedAbility": item.granted_ability,
            "abilityBonus": item.ability_bonus,
        }
        for item in items
    ]
