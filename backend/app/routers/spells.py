from typing import Annotated
from uuid import UUID

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


@router.get("/spell-schools")
def list_spell_schools(db: Annotated[Session, Depends(get_db)]) -> list[str]:
    """Distinct `BaseSpell.school` values, sorted — feeds the picker for
    feats whose `BaseFeat.sub_choice_type` is "spell_school" (Zauberfokus,
    Mächtiger Zauberfokus). School isn't its own catalog table (see
    `BaseSpell.school`'s docstring), so this is the only place a "what
    schools exist" list can come from."""
    schools = db.scalars(select(BaseSpell.school).distinct()).all()
    return sorted(schools)


@router.get("/spells-by-class")
def get_spells_by_class(db: Annotated[Session, Depends(get_db)]) -> dict[str, list[dict]]:
    """Replaces the old frontend-shaped `spells_by_class.json` (bare name
    lists, no grade) — real `base_class_spells` rows now, grouped by root
    class name so the frontend picker can key off `id` instead of `name`,
    same convention as feats/traits. Only classes with a fixed known-spell
    list appear here (spontaneous/arcane-prepared) — divine-prepared/none
    classes have no rows in `base_class_spells` to begin with.

    Groups by each root's own `effective_spell_list_class_id`
    (`BaseClass`'s docstring) rather than a spell row's raw `base_class_id`
    directly — a class whose spell *selection* is drawn from another
    class's list wholesale (Mystiker -> Kleriker, RAW: Oracle has no
    independent spell list) still needs its own key in this dict, showing
    that other class's spells, not to be silently absent just because it
    owns no `base_class_spells` rows of its own."""
    roots = db.scalars(select(BaseClass).where(BaseClass.arch_class_of.is_(None))).all()

    rows_by_class_id: dict[UUID, list[BaseClassSpell]] = {}
    for row in db.scalars(select(BaseClassSpell)).all():
        rows_by_class_id.setdefault(row.base_class_id, []).append(row)

    result: dict[str, list[dict]] = {}
    for root in roots:
        rows = rows_by_class_id.get(root.effective_spell_list_class_id)
        if not rows:
            continue
        result[root.name] = sorted(
            ({"id": str(row.spell_id), "name": row.spell.name, "grade": row.grade} for row in rows),
            key=lambda s: (s["grade"], s["name"]),
        )
    return result
