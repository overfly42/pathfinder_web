from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseSkill, BaseSkillSpecialization

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
def list_skills(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    skills = db.scalars(select(BaseSkill).order_by(BaseSkill.name)).all()
    return [
        {
            "id": str(skill.id),
            "name": skill.name,
            "ability": skill.ability,
            "isBackground": skill.is_background,
            "hasSpecialization": skill.has_specialization,
        }
        for skill in skills
    ]


@router.get("/specializations")
def list_skill_specializations(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    """Suggested specializations for `has_specialization` skills (Handwerk/
    Beruf/Auftreten) — see `BaseSkillSpecialization`'s docstring. A player can
    also type a specialization not in this list (`custom_specialization` on
    the character-side skill rank)."""
    specializations = db.scalars(select(BaseSkillSpecialization).order_by(BaseSkillSpecialization.name)).all()
    return [
        {
            "id": str(specialization.id),
            "skillId": str(specialization.skill_id),
            "name": specialization.name,
            # No handler family exists yet for specializations — see this
            # model's own docstring for the anticipated future case (a class
            # ability keyed to a specific specialization like "Beruf
            # (Seemann)"). Always False until one does.
            "hasHandler": False,
        }
        for specialization in specializations
    ]
