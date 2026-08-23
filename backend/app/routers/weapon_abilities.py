from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseWeaponSpecialAbility
from ..rules.weapon_abilities import HANDLERS

router = APIRouter(prefix="/api/weapon-abilities", tags=["weapon-abilities"])


@router.get("")
def list_weapon_abilities(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    abilities = db.scalars(select(BaseWeaponSpecialAbility).order_by(BaseWeaponSpecialAbility.name)).all()
    return [
        {
            "id": str(ability.id),
            "name": ability.name,
            "bonusEquivalent": ability.bonus_equivalent,
            "applicableCategories": ability.applicable_categories,
            "restrictionNote": ability.restriction_note,
            "description": ability.description,
            # Most abilities resolve through `_generic` (name/description only,
            # see that module's docstring) — only the ids in its own `HANDLERS`
            # (the togglable flat energy-damage abilities) get a distinct
            # computed effect.
            "hasHandler": ability.id in HANDLERS,
        }
        for ability in abilities
    ]
