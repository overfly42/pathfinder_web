import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# id -> fixture filename. No database yet; this is a static mock data source.
CHARACTER_FIXTURES = {
    "1": "character_1.json",
}

# id -> fixture filename for the level-up wizard's baseline "character being
# leveled" view. Kept separate from CHARACTER_FIXTURES/character_1.json since
# it's a different shape (raw classes/base ability scores for progression,
# not the sheet's computed/display shape) until the backend has one real
# character domain model instead of two mock views of the same character.
PROGRESSION_FIXTURES = {
    "1": "progression_1.json",
}

app = FastAPI(title="Pathfinder Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def load_fixture(filename: str) -> Any:
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/characters/{character_id}")
def get_character(character_id: str) -> dict:
    filename = CHARACTER_FIXTURES.get(character_id)
    if filename is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return load_fixture(filename)


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
# fixture reads for now, no DB, no filtering/query params.
@app.get("/api/races")
def get_races() -> list:
    return load_fixture("races.json")


@app.get("/api/classes")
def get_classes() -> list:
    return load_fixture("classes.json")


@app.get("/api/feats")
def get_feats() -> list:
    return load_fixture("feats.json")


@app.get("/api/traits")
def get_traits() -> list:
    return load_fixture("traits.json")


@app.get("/api/skills")
def get_skills() -> list:
    return load_fixture("skills.json")


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


# Recurring per-class choices gated by level (e.g. a ranger's 2nd favored
# enemy at level 5), distinct from /api/classes' optionGroups which are
# one-time level-1 picks. Used by the level-up wizard only.
@app.get("/api/class-level-options")
def get_class_level_options() -> dict:
    return load_fixture("class_level_options.json")
