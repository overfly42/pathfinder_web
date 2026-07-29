from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseClass, BaseRace, Character, CharacterAbilityChoice, CharacterLevel, User
from ..rules.point_buy import spent_points
from ..schemas.character import CharacterCreate, CharacterRead, CharacterUpdate
from .races import race_has_flex, resolve_flex_ability_id

router = APIRouter(prefix="/api/characters", tags=["characters"])


def resolve_base_class_id(db: Session, class_name: str) -> UUID | None:
    base_class = db.scalar(select(BaseClass).where(BaseClass.name == class_name))
    return base_class.id if base_class is not None else None


@router.post("", response_model=CharacterRead, status_code=201)
def create_character(body: CharacterCreate, db: Annotated[Session, Depends(get_db)]) -> Character:
    if db.get(User, body.user_id) is None:
        raise HTTPException(status_code=422, detail="Unknown user_id")
    if db.get(BaseRace, body.race_id) is None:
        raise HTTPException(status_code=422, detail="Unknown race_id")

    base_class_ids = [resolve_base_class_id(db, selection.class_name) for selection in body.classes]
    if any(base_class_id is None for base_class_id in base_class_ids):
        raise HTTPException(status_code=422, detail="Unknown class_name")

    if spent_points(body.ability_scores) > body.point_budget:
        raise HTTPException(status_code=422, detail="Ability scores exceed the chosen point-buy budget")

    has_flex = race_has_flex(db, body.race_id)
    if has_flex and body.flex_ability is None:
        raise HTTPException(status_code=422, detail="This race requires choosing a flex ability bonus")
    if not has_flex and body.flex_ability is not None:
        raise HTTPException(status_code=422, detail="This race does not grant a flex ability bonus")

    flex_ability_id = None
    if body.flex_ability is not None:
        flex_ability_id = resolve_flex_ability_id(db, body.race_id, body.flex_ability)
        if flex_ability_id is None:
            raise HTTPException(status_code=422, detail="Unknown flex_ability for this race")

    character = Character(
        name=body.name,
        user_id=body.user_id,
        race_id=body.race_id,
        current_hit_points=body.current_hit_points,
        ability_score_st=body.ability_scores["ST"],
        ability_score_ge=body.ability_scores["GE"],
        ability_score_ko=body.ability_scores["KO"],
        ability_score_in=body.ability_scores["IN"],
        ability_score_we=body.ability_scores["WE"],
        ability_score_ch=body.ability_scores["CH"],
        point_budget=body.point_budget,
    )
    if flex_ability_id is not None:
        character.ability_choices.append(CharacterAbilityChoice(ability_id=flex_ability_id))

    running_level = 0
    for selection, base_class_id in zip(body.classes, base_class_ids):
        for _ in range(selection.level):
            running_level += 1
            character.levels.append(CharacterLevel(level=running_level, base_class_id=base_class_id))

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
