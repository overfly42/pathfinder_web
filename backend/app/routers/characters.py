import json
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    BaseClass,
    BaseRace,
    Character,
    CharacterAbilityChoice,
    CharacterClass,
    CharacterClassOption,
    CharacterLevel,
    User,
)
from ..rules.point_buy import spent_points
from ..schemas.character import CharacterCreate, CharacterRead, CharacterUpdate
from .races import race_has_flex, resolve_flex_ability_id

router = APIRouter(prefix="/api/characters", tags=["characters"])

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _class_def(class_name: str) -> dict | None:
    """Rules content (archetypes/optionGroups/skill points/...) for a root
    class, straight from `classes.json` — `BaseClass` only carries identity
    plus the structural bits (hit_dice, arch_class_of) that need a real FK."""
    classes = json.loads((FIXTURES_DIR / "classes.json").read_text(encoding="utf-8"))
    return next((c for c in classes if c["name"] == class_name), None)


def resolve_root_class(db: Session, class_name: str) -> BaseClass:
    """Resolves a submitted class_name to its root `BaseClass` row — what
    every `CharacterLevel` for this class-taken points at. Written as its own
    function (not inlined in `create_character`) so a future level-up
    endpoint can reuse it per new level, not just at creation."""
    root = db.scalar(select(BaseClass).where(BaseClass.name == class_name, BaseClass.arch_class_of.is_(None)))
    if root is None:
        raise HTTPException(status_code=422, detail="Unknown class_name")
    return root


def resolve_archetype(db: Session, root: BaseClass, archetype_name: str) -> BaseClass:
    """Resolves a named archetype to its `BaseClass` row, scoped to `root` —
    zero or more of these can apply to one class-taken (see `CharacterClass`),
    unlike the root itself."""
    variant = db.scalar(select(BaseClass).where(BaseClass.name == archetype_name, BaseClass.arch_class_of == root.id))
    if variant is None:
        raise HTTPException(status_code=422, detail=f"Unknown archetype '{archetype_name}' for class '{root.name}'")
    return variant


def _validate_options(class_name: str, options: dict[str, list[str]]) -> None:
    class_def = _class_def(class_name) or {}
    groups_by_key = {group["key"]: group for group in class_def.get("optionGroups", [])}
    for group_key, choices in options.items():
        group = groups_by_key.get(group_key)
        if group is None:
            raise HTTPException(status_code=422, detail=f"Unknown option group '{group_key}' for {class_name}")
        if len(choices) > group["max"]:
            raise HTTPException(status_code=422, detail=f"Too many choices for option group '{group_key}'")
        for choice in choices:
            if choice not in group["choices"]:
                raise HTTPException(status_code=422, detail=f"Invalid choice '{choice}' for option group '{group_key}'")


@router.post("", response_model=CharacterRead, status_code=201)
def create_character(body: CharacterCreate, db: Annotated[Session, Depends(get_db)]) -> Character:
    if db.get(User, body.user_id) is None:
        raise HTTPException(status_code=422, detail="Unknown user_id")
    if db.get(BaseRace, body.race_id) is None:
        raise HTTPException(status_code=422, detail="Unknown race_id")

    roots = [resolve_root_class(db, selection.class_name) for selection in body.classes]
    archetypes_per_selection = [
        [resolve_archetype(db, root, name) for name in selection.archetypes]
        for selection, root in zip(body.classes, roots)
    ]

    for selection in body.classes:
        _validate_options(selection.class_name, selection.options)

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

    # The root of the first submitted class is favored by default — matches
    # the class picker's row order, not something the wizard asks for yet.
    favored_root_id = roots[0].id
    seen_root_ids: set[UUID] = set()
    seen_archetype_ids_by_root: dict[UUID, set[UUID]] = {}

    running_level = 0
    for selection, root, archetypes in zip(body.classes, roots, archetypes_per_selection):
        for _ in range(selection.level):
            running_level += 1
            character.levels.append(CharacterLevel(level=running_level, base_class_id=root.id))
        for group_key, choices in selection.options.items():
            for choice in choices:
                character.class_options.append(
                    CharacterClassOption(base_class_id=root.id, group_key=group_key, choice=choice)
                )

        if root.id not in seen_root_ids:
            seen_root_ids.add(root.id)
            character.class_memberships.append(
                CharacterClass(base_class_id=root.id, is_favored=root.id == favored_root_id)
            )

        seen_archetype_ids = seen_archetype_ids_by_root.setdefault(root.id, set())
        for archetype in archetypes:
            if archetype.id in seen_archetype_ids:
                continue
            seen_archetype_ids.add(archetype.id)
            character.class_memberships.append(CharacterClass(base_class_id=archetype.id))

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
