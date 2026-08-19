from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseSkill

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
def list_skills(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    skills = db.scalars(select(BaseSkill).order_by(BaseSkill.name)).all()
    return [
        {"id": str(skill.id), "name": skill.name, "ability": skill.ability, "isBackground": skill.is_background}
        for skill in skills
    ]
