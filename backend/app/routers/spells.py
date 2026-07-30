from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseClass, BaseClassSpell, BaseSpell

router = APIRouter(prefix="/api", tags=["spells"])


@router.get("/spells")
def list_spells(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    spells = db.scalars(select(BaseSpell).order_by(BaseSpell.name)).all()
    return [
        {"id": str(spell.id), "name": spell.name, "school": spell.school, "description": spell.description}
        for spell in spells
    ]


@router.get("/spells-by-class")
def get_spells_by_class(db: Annotated[Session, Depends(get_db)]) -> dict[str, list[dict]]:
    """Replaces the old frontend-shaped `spells_by_class.json` (bare name
    lists, no grade) — real `base_class_spells` rows now, grouped by root
    class name so the frontend picker can key off `id` instead of `name`,
    same convention as feats/traits. Only classes with a fixed known-spell
    list appear here (spontaneous/arcane-prepared) — divine-prepared/none
    classes have no rows in `base_class_spells` to begin with."""
    roots = db.scalars(select(BaseClass).where(BaseClass.arch_class_of.is_(None))).all()
    name_by_root_id = {root.id: root.name for root in roots}

    rows = db.scalars(select(BaseClassSpell)).all()
    result: dict[str, list[dict]] = {}
    for row in rows:
        class_name = name_by_root_id.get(row.base_class_id)
        if class_name is None:
            continue
        result.setdefault(class_name, []).append(
            {"id": str(row.spell_id), "name": row.spell.name, "grade": row.grade}
        )
    for spells in result.values():
        spells.sort(key=lambda s: (s["grade"], s["name"]))
    return result
