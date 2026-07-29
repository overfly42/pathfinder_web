import json
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .db import get_db
from .models import BaseClass, BaseClassSkill, Character
from .routers import characters, races, skills, users
from .schemas.character import CharacterRead

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# id -> fixture filename. No database yet; this is a static mock data source.
CHARACTER_FIXTURES = {
    "1": "character_1.json",
    "2": "character_2.json",
}

# id -> fixture filename for the level-up wizard's baseline "character being
# leveled" view. Kept separate from CHARACTER_FIXTURES/character_1.json since
# it's a different shape (raw classes/base ability scores for progression,
# not the sheet's computed/display shape) until the backend has one real
# character domain model instead of two mock views of the same character.
PROGRESSION_FIXTURES = {
    "1": "progression_1.json",
    "2": "progression_2.json",
}

app = FastAPI(title="Pathfinder Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(races.router)
app.include_router(skills.router)
app.include_router(characters.router)


def load_fixture(filename: str) -> Any:
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/health")
def get_health(db: Annotated[Session, Depends(get_db)]) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/characters/{character_id}")
def get_character(character_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    filename = CHARACTER_FIXTURES.get(character_id)
    if filename is not None:
        return load_fixture(filename)

    # Not one of the two mock sheet fixtures — try a real (slice 2) character.
    # Its shape is minimal (no computed AC/abilities/etc. yet — that's a later
    # "thick" pass), unlike the fixtures above.
    try:
        parsed_id = UUID(character_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Character not found") from exc

    character = db.get(Character, parsed_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return CharacterRead.model_validate(character).model_dump(mode="json")


@app.get("/api/characters/{character_id}/progression")
def get_character_progression(character_id: str) -> dict:
    filename = PROGRESSION_FIXTURES.get(character_id)
    if filename is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return load_fixture(filename)


# Reference data for the character-creation and level-up wizards.
# One resource endpoint per entity rather than a single bundle, so a screen
# only fetches what it needs (e.g. level-up needs classes/feats/skills but
# not races/items) and each resource can grow independently. Still static
# fixture reads for now, no DB, no filtering/query params — except races
# (roadmap slice 2, see routers/races.py) and skills (roadmap slice 3, see
# routers/skills.py), which are real database tables; classes' identity/
# hit_dice/archetype-hierarchy/class-skills are also DB-backed (BaseClass/
# BaseClassSkill) even though this endpoint still layers that onto the rest
# of classes.json's fixture content.


@app.get("/api/classes")
def get_classes(db: Annotated[Session, Depends(get_db)]) -> list:
    """`classes.json`'s content (skill points/spell type/archetypes/option
    groups) stays fixture, joined by `name`, except `classSkills`: that field
    is overwritten here with real skill ids from `base_class_skills`
    (roadmap slice 3) instead of the old fixture-key strings, since skills
    are now a real table (`BaseSkill`) — see `routers/skills.py`."""
    classes = load_fixture("classes.json")
    roots = db.scalars(select(BaseClass).where(BaseClass.arch_class_of.is_(None))).all()
    root_id_by_name = {root.name: root.id for root in roots}
    class_skills = db.scalars(select(BaseClassSkill)).all()
    skill_ids_by_root_id: dict = {}
    for row in class_skills:
        skill_ids_by_root_id.setdefault(row.base_class_id, []).append(str(row.skill_id))

    for class_def in classes:
        root_id = root_id_by_name.get(class_def["name"])
        class_def["classSkills"] = skill_ids_by_root_id.get(root_id, []) if root_id else []
    return classes


@app.get("/api/feats")
def get_feats() -> list:
    return load_fixture("feats.json")


@app.get("/api/traits")
def get_traits() -> list:
    return load_fixture("traits.json")


@app.get("/api/abilities")
def get_abilities() -> list:
    return load_fixture("abilities.json")


@app.get("/api/spells-by-class")
def get_spells_by_class() -> dict:
    return load_fixture("spells_by_class.json")


@app.get("/api/point-buy-costs")
def get_point_buy_costs() -> dict:
    return load_fixture("point_buy_costs.json")


@app.get("/api/items")
def get_items() -> list:
    return load_fixture("items.json")


@app.get("/api/effects")
def get_effects() -> list:
    return load_fixture("effects.json")


# Recurring per-class choices gated by level (e.g. a ranger's 2nd favored
# enemy at level 5), distinct from /api/classes' optionGroups which are
# one-time level-1 picks. Used by the level-up wizard only.
@app.get("/api/class-level-options")
def get_class_level_options() -> dict:
    return load_fixture("class_level_options.json")
