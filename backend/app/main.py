import json
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .db import get_db
from .models import (
    BaseClass,
    BaseClassAbilityGrant,
    BaseClassOptionChoice,
    BaseClassOptionGroup,
    BaseClassSkill,
    BaseClassSpellsKnown,
    Character,
)
from .routers import characters, conditions, feats, items, races, skills, spells, traits, users, weapon_abilities
from .rules.class_options import ability_ids_by_name, group_occurrence_levels
from .rules.feat_slots import BONUS_FEAT_SLOT_ABILITY_IDS
from .sheet import build_character_history, build_character_progression, build_character_sheet

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
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(races.router)
app.include_router(skills.router)
app.include_router(feats.router)
app.include_router(traits.router)
app.include_router(spells.router)
app.include_router(items.router)
app.include_router(weapon_abilities.router)
app.include_router(conditions.router)
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
    return build_character_sheet(character, db)


@app.get("/api/characters/{character_id}/progression")
def get_character_progression(character_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    filename = PROGRESSION_FIXTURES.get(character_id)
    if filename is not None:
        return load_fixture(filename)

    # Not one of the two mock progression fixtures — try a real character,
    # same dual-path pattern as get_character above.
    try:
        parsed_id = UUID(character_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Character not found") from exc

    character = db.get(Character, parsed_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return build_character_progression(character, db)


@app.get("/api/characters/{character_id}/history")
def get_character_history(character_id: str, db: Annotated[Session, Depends(get_db)]) -> list:
    """Standalone level-up history log (roadmap.md slice 7, thin) — the level-
    up wizard itself reads history off `.../progression`'s `history` field,
    but this exposes the same reconstruction on its own. The two mock
    fixture ids have no real `CharacterLevel` rows to reconstruct from, so
    they just return an empty log rather than 404ing."""
    if character_id in PROGRESSION_FIXTURES:
        return []

    try:
        parsed_id = UUID(character_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Character not found") from exc

    character = db.get(Character, parsed_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return build_character_history(character, db)


# Reference data for the character-creation and level-up wizards.
# One resource endpoint per entity rather than a single bundle, so a screen
# only fetches what it needs (e.g. level-up needs classes/feats/skills but
# not races/items) and each resource can grow independently. Still static
# fixture reads for now, no DB, no filtering/query params — except races
# (roadmap slice 2, see routers/races.py), skills (roadmap slice 3, see
# routers/skills.py) and feats (roadmap slice 3, see routers/feats.py),
# which are real database tables; classes' identity/hit_dice/archetype-
# hierarchy/class-skills/option-groups are also DB-backed
# (BaseClass/BaseClassSkill/BaseClassOptionGroup/BaseClassOptionChoice) even
# though this endpoint still layers that onto the rest of classes.json's
# fixture content (skill points, spell type, archetype names).


@app.get("/api/classes")
def get_classes(db: Annotated[Session, Depends(get_db)]) -> list:
    """`classes.json`'s content (spell type/archetypes) stays fixture, joined
    by `name`, except `classSkills`, `optionGroups`, `bonusFeatLevels` and
    `skillPointsBase`: those fields are overwritten here with real rows from
    `base_class_skills`, `base_class_option_groups`/`base_class_option_choices`
    and `base_class_ability_grants` (roadmap slice 3) instead of the
    fixture's own copies, now that they're real tables — see
    `routers/skills.py`, `app/seed/class_option_seed.py` and
    `app/seed/class_ability_seed.py`. `bonusFeatLevels` (which levels of this
    class grant a bonus feat slot, e.g. Kämpfer's 1st and every even level)
    lets the frontend compute `featMax` without hardcoding a class name —
    see `rules/feat_slots.py`. `id` (the root `BaseClass` id — `null` if this
    class name has no matching root row) is exposed so the frontend can key
    `CharacterCreate.spell_ids`/`spellbook` calls by `base_class_id`, same
    reasoning as `castingAbility`/`spellTradition`/`spellsKnownByLevel`
    (roadmap slice 3's spellbook pass, see `rules/spells.py`). `babProgression`/
    `fortSave`/`refSave`/`willSave` (roadmap slice 3's HP/BAB/save item)
    likewise come straight from `BaseClass`, letting a future sheet/level-up
    UI mirror `rules/progression.py`'s math without hardcoding per-class
    progression. Each `optionGroups` entry also carries `occurrenceLevels`
    (`rules/class_options.py`'s `group_occurrence_levels`, 2026-08-16) — empty
    for a one-time pick, otherwise the levels at which the frontend should
    treat the group as newly available/countable; `ClassStep.tsx` uses this
    purely as backend-computed data (which levels exist), `_validate_options`
    (`routers/characters.py`) is what actually enforces it."""
    classes = load_fixture("classes.json")
    roots = db.scalars(select(BaseClass).where(BaseClass.arch_class_of.is_(None))).all()
    root_id_by_name = {root.name: root.id for root in roots}
    roots_by_id = {root.id: root for root in roots}

    # option_choice_id IS NULL only: a class's unconditional base skill list.
    # Mystery-conditional additions (Mystiker/Oracle - each Mysterium adds its
    # own extra class skills) live on the same table but are only real once a
    # character has actually picked that choice, same reasoning as why
    # optionGroups' choices aren't merged into this field either.
    class_skills = db.scalars(select(BaseClassSkill).where(BaseClassSkill.option_choice_id.is_(None))).all()
    skill_ids_by_root_id: dict = {}
    for row in class_skills:
        skill_ids_by_root_id.setdefault(row.base_class_id, []).append(str(row.skill_id))

    choice_names_by_group_id: dict = {}
    for choice in db.scalars(select(BaseClassOptionChoice)).all():
        choice_names_by_group_id.setdefault(choice.group_id, []).append(choice.name)
    ability_ids_by_name_map = ability_ids_by_name(db)
    option_groups_by_root_id: dict = {}
    for group in db.scalars(select(BaseClassOptionGroup)).all():
        option_groups_by_root_id.setdefault(group.base_class_id, []).append(
            {
                "key": group.key,
                "label": group.label,
                "max": group.max_choices,
                "choices": choice_names_by_group_id.get(group.id, []),
                # Empty for a one-time creation-time pick (domain/bloodline/
                # school - always available); non-empty for a recurring pick
                # (Kampfrauschkraft/Trick/Offenbarung) - the levels (in this
                # root class) at which one more occurrence opens up. The
                # frontend uses this purely as backend-computed data (which
                # occurrence levels exist, full stop) to decide whether to
                # render the group at a given class-row level and to cap how
                # many picks are legal so far - `_validate_options`
                # (`routers/characters.py`) is what actually enforces both,
                # server-side, using this exact same function.
                "occurrenceLevels": group_occurrence_levels(db, group, ability_ids_by_name_map),
            }
        )

    bonus_feat_levels_by_root_id: dict = {}
    bonus_feat_grants = db.scalars(
        select(BaseClassAbilityGrant).where(BaseClassAbilityGrant.ability_id.in_(BONUS_FEAT_SLOT_ABILITY_IDS))
    ).all()
    for grant in bonus_feat_grants:
        bonus_feat_levels_by_root_id.setdefault(grant.base_class_id, []).append(grant.level)

    # {root_id: {level: {grade: count | None}}} — count is null for
    # arcane-prepared classes (grade-gating only, see rules/spells.py); the
    # frontend's spell-picker budget math (creationCalculations.ts) mirrors
    # the backend's rules/spells.py against this same table.
    known_by_root_id: dict = {}
    for row in db.scalars(select(BaseClassSpellsKnown)).all():
        by_level = known_by_root_id.setdefault(row.base_class_id, {})
        by_level.setdefault(str(row.level), {})[str(row.grade)] = row.count

    for class_def in classes:
        root_id = root_id_by_name.get(class_def["name"])
        root = roots_by_id.get(root_id) if root_id else None
        class_def["id"] = str(root_id) if root_id else None
        class_def["classSkills"] = skill_ids_by_root_id.get(root_id, []) if root_id else []
        class_def["optionGroups"] = option_groups_by_root_id.get(root_id, []) if root_id else []
        class_def["bonusFeatLevels"] = sorted(bonus_feat_levels_by_root_id.get(root_id, [])) if root_id else []
        class_def["castingAbility"] = root.casting_ability if root else None
        class_def["spellTradition"] = root.spell_tradition if root else None
        class_def["spellsKnownByLevel"] = known_by_root_id.get(root_id, {}) if root_id else {}
        class_def["babProgression"] = root.bab_progression if root else None
        class_def["hitDice"] = root.hit_dice if root else None
        class_def["fortSave"] = root.fort_save if root else None
        class_def["refSave"] = root.ref_save if root else None
        class_def["willSave"] = root.wil_save if root else None
        if root is not None:
            class_def["skillPointsBase"] = root.skill_points_base
    return classes


@app.get("/api/abilities")
def get_abilities() -> list:
    return load_fixture("abilities.json")


@app.get("/api/point-buy-costs")
def get_point_buy_costs() -> dict:
    return load_fixture("point_buy_costs.json")


@app.get("/api/effects")
def get_effects() -> list:
    return load_fixture("effects.json")


# Recurring per-class choices gated by level (e.g. a barbarian's new
# Kampfrauschkraft at every even level), one occurrence at a time. Distinct
# from /api/classes' optionGroups, which exposes every occurrence's worth of
# choices flatly (creation submits every earned pick for a group in one go,
# not incrementally) — this endpoint is for the level-up wizard's
# ClassChoiceStep specifically, which picks exactly one new occurrence per
# level-up.
@app.get("/api/class-level-options")
def get_class_level_options(db: Annotated[Session, Depends(get_db)]) -> dict:
    """Computed from the real `base_class_option_groups`/
    `base_class_option_choices`/`base_class_ability_grants` tables — this
    used to read a static `class_level_options.json` fixture, which had gone
    stale against those tables (wrong group keys, a handful of leftover
    placeholder choices instead of e.g. Barbar's real ~54-choice
    Kampfrauschkraft catalog) and so silently under-offered or omitted
    picks in the level-up wizard.

    A `BaseClassOptionGroup` counts as "recurring" here if some
    `BaseClassAbility` whose *name* matches the group's own `label` has more
    than one unconditional (`option_choice_id IS NULL`) `BaseClassAbilityGrant`
    for this root class at different levels — the same "one shared slot
    ability, several per-level grant rows" pattern `BaseClassAbilityGrant`'s
    own docstring describes (Kämpfer's bonus feat, Schurke's Trick, Barbar's
    Kampfrauschkraft, ...). A group with only a single such grant (e.g.
    Waldläufer's one-time Bund des Jägers at level 4) is a one-time pick, not
    a recurring one, and is left out — same for a group with no matching
    ability at all (e.g. Kleriker's `domain`, Waldläufer's `enemy`/`terrain`,
    whose recurrence isn't backed by real grant data yet, see todos.md).
    Omitted rather than guessed at, the same "honest empty default, not
    fabricated content" convention `sheet.py` uses throughout.

    `"max"` is always 1 here, not the group's own `max_choices` — that field
    is the *lifetime* total across every occurrence in a character's whole
    career (e.g. Kampfrauschkraft's 10, one per even level 2-20), whereas
    each recurring *occurrence* (what this endpoint's `"levels"` enumerates)
    only ever grants exactly one pick in every class this heuristic has
    found so far (Kampfrauschkraft, Trick, Offenbarung) — conflating the two
    used to let the level-up wizard offer picking up to `max_choices` (10)
    choices in a single level-up instead of 1. `routers/characters.py`'s
    level-up endpoint enforces the same "at most 1 per group per level-up"
    rule server-side, and also checks each choice's
    `BaseClassOptionChoice.min_level` (e.g. Kampfrauschkraft's "Innere
    Zähigkeit" needs Barbar 8) — both were the not-yet-enforced "phase 5" in
    roadmap.md's "Pick from a restricted list" section, now done for the
    level-up path specifically (creation's own `_validate_options` call
    gained the same `min_level` check too). This is not a player-facing rules
    reference, so a choice gated behind a higher `min_level` (e.g.
    Kampfrauschkraft's "Innere Zähigkeit" needing Barbar 8) must not appear
    at all at an occurrence below that level — `"choices"` is keyed per
    occurrence level (`"choicesByLevel"`) rather than returned as one flat
    list, so `ClassChoiceStep` only ever renders what's actually legal to
    pick and has nothing left to filter itself."""
    choices_by_group_id: dict[UUID, list[BaseClassOptionChoice]] = {}
    for choice in db.scalars(select(BaseClassOptionChoice)).all():
        choices_by_group_id.setdefault(choice.group_id, []).append(choice)

    ability_ids_by_name_map = ability_ids_by_name(db)
    class_names_by_root_id = {root.id: root.name for root in db.scalars(select(BaseClass)).all()}

    result: dict[str, list[dict]] = {}
    for group in db.scalars(select(BaseClassOptionGroup)).all():
        class_name = class_names_by_root_id.get(group.base_class_id)
        if group.label not in ability_ids_by_name_map or class_name is None:
            continue
        levels = group_occurrence_levels(db, group, ability_ids_by_name_map)
        if len(levels) < 2:
            continue
        group_choices = choices_by_group_id.get(group.id, [])
        choices_by_level = {
            level: [choice.name for choice in group_choices if choice.min_level is None or choice.min_level <= level]
            for level in levels
        }
        result.setdefault(class_name, []).append(
            {
                "key": group.key,
                "label": group.label,
                # This occurrence's own pick count, not the group's lifetime
                # max_choices - see the docstring above.
                "max": 1,
                "choicesByLevel": choices_by_level,
                "levels": levels,
            }
        )
    return result
