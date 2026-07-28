from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseRace, Character, User
from ..schemas.character import CharacterCreate, CharacterRead, CharacterUpdate

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.post("", response_model=CharacterRead, status_code=201)
def create_character(body: CharacterCreate, db: Annotated[Session, Depends(get_db)]) -> Character:
    if db.get(User, body.user_id) is None:
        raise HTTPException(status_code=422, detail="Unknown user_id")
    if db.get(BaseRace, body.race_id) is None:
        raise HTTPException(status_code=422, detail="Unknown race_id")

    character = Character(
        name=body.name,
        user_id=body.user_id,
        race_id=body.race_id,
        class_name=body.class_name,
        level=1,
        hit_points=body.hit_points,
    )
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


@router.patch("/{character_id}", response_model=CharacterRead)
def rename_character(
    character_id: UUID, body: CharacterUpdate, db: Annotated[Session, Depends(get_db)]
) -> Character:
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    character.name = body.name
    db.commit()
    db.refresh(character)
    return character


@router.delete("/{character_id}", status_code=204)
def delete_character(character_id: UUID, db: Annotated[Session, Depends(get_db)]) -> None:
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    db.delete(character)
    db.commit()
