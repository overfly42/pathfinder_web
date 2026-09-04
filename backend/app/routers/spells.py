from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseClass, BaseClassOptionChoice, BaseClassSpell, BaseClassSpellGrant, BaseSpell

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


@router.get("/granted-spells-by-choice")
def get_granted_spells_by_choice(db: Annotated[Session, Depends(get_db)]) -> dict[str, dict[str, list[dict]]]:
    """`BaseClassSpellGrant` rows (a fixed spell a class automatically adds to
    a character's spellbook for free once a specific one-time option choice
    is made and the granting class level is reached — Hexenmeister's
    Blutlinie, Hexe's Schutzherr, Mystiker's `heilfokus`/Kurieren-Verletzen)
    grouped by root class name, then by the granting `BaseClassOptionChoice`
    name, so the creation/level-up wizard can show "these are already yours"
    next to whichever choice(s) the player picked, the same way
    `/api/spells-by-class`'s grade-0 spells are shown for arcane-prepared
    casters — see `SpellsStep.tsx`.

    `grade` is resolved the same way `routers/characters.py`'s spell-pick
    validation does (`root.effective_spell_list_class_id`'s own
    `base_class_spells` rows) since `BaseClassSpellGrant` itself only stores
    the granting class level, not the spell's grade for that class."""
    roots = db.scalars(select(BaseClass).where(BaseClass.arch_class_of.is_(None))).all()
    root_by_id = {root.id: root for root in roots}

    grade_by_class_and_spell: dict[UUID, dict[UUID, int]] = {}
    for row in db.scalars(select(BaseClassSpell)).all():
        grade_by_class_and_spell.setdefault(row.base_class_id, {})[row.spell_id] = row.grade

    choice_names = {row.id: row.name for row in db.scalars(select(BaseClassOptionChoice)).all()}
    spell_names = {row.id: row.name for row in db.scalars(select(BaseSpell)).all()}

    result: dict[str, dict[str, list[dict]]] = {}
    for grant in db.scalars(select(BaseClassSpellGrant)).all():
        root = root_by_id.get(grant.base_class_id)
        choice_name = choice_names.get(grant.option_choice_id) if grant.option_choice_id else None
        if root is None or choice_name is None:
            continue
        grade = grade_by_class_and_spell.get(root.effective_spell_list_class_id, {}).get(grant.spell_id)
        if grade is None:
            continue
        result.setdefault(root.name, {}).setdefault(choice_name, []).append(
            {"id": str(grant.spell_id), "name": spell_names[grant.spell_id], "grade": grade, "level": grant.level}
        )

    for by_choice in result.values():
        for entries in by_choice.values():
            entries.sort(key=lambda s: (s["level"], s["name"]))
    return result
