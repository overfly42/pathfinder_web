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
    BaseClassOptionChoice,
    BaseClassOptionGroup,
    BaseClassSpell,
    BaseFeat,
    BaseItem,
    BaseRace,
    BaseSkill,
    BaseTrait,
    Character,
    CharacterClass,
    CharacterClassOption,
    CharacterFeat,
    CharacterGear,
    CharacterLevel,
    CharacterRacialChoice,
    CharacterSkillRank,
    CharacterSpell,
    CharacterTrait,
    User,
)
from ..rules.feat_slots import base_feat_count, class_bonus_feat_slot_count, race_grants_bonus_feat
from ..rules.point_buy import spent_points
from ..rules.progression import is_valid_rolled_hit_points
from ..rules.spells import arcane_prepared_budget, known_grades, spontaneous_known_budget
from ..schemas.character import CharacterCreate, CharacterRead, CharacterUpdate, ClassSelection, SpellbookAdd
from .races import race_ability_score_mods, race_has_flex, resolve_alt_trait, resolve_flex_ability_id

router = APIRouter(prefix="/api/characters", tags=["characters"])

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _class_def(class_name: str) -> dict | None:
    """Rules content (archetypes/skill points/...) for a root class, straight
    from `classes.json` — `BaseClass` only carries identity plus the
    structural bits (hit_dice, arch_class_of) that need a real FK. Option
    groups are no longer read from here — see `_validate_options`."""
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


def _skill_points_total(classes: list[ClassSelection], roots: list[BaseClass], int_mod: int) -> int:
    """Mirrors the frontend's `skillPointsTotal` (creationCalculations.ts):
    per class-taken, max(1, class's base skill points + INT modifier) times
    the levels taken in it, summed across all classes. `roots` is
    index-aligned with `classes` (both come from the same `zip` elsewhere in
    this module) — `BaseClass.skill_points_base`, not `classes.json`, is the
    source of truth now."""
    total = 0
    for selection, root in zip(classes, roots):
        total += max(1, root.skill_points_base + int_mod) * selection.level
    return total


def _feat_max(
    db: Session, race_id: UUID, classes: list[ClassSelection], replaced_ability_ids: set[UUID]
) -> int:
    """Base feat progression plus bonus feat slots granted by race or class,
    resolved from real data rather than a hardcoded class name — see
    `rules/feat_slots.py`. Mirrors the frontend's `featMax`
    (creationCalculations.ts)."""
    total_level = sum(selection.level for selection in classes)
    max_feats = base_feat_count(total_level)

    if race_grants_bonus_feat(db, race_id, replaced_ability_ids):
        max_feats += 1

    max_feats += class_bonus_feat_slot_count(db, classes)

    return max_feats


def _validate_options(db: Session, root: BaseClass, options: dict[str, list[str]]) -> None:
    """Validates submitted option-group choices (e.g. Kleriker's `domain`)
    against `base_class_option_groups`/`base_class_option_choices` — real
    tables now (see `app/seed/class_option_seed.py`), not `classes.json`."""
    groups = db.scalars(select(BaseClassOptionGroup).where(BaseClassOptionGroup.base_class_id == root.id)).all()
    groups_by_key = {group.key: group for group in groups}
    for group_key, choices in options.items():
        group = groups_by_key.get(group_key)
        if group is None:
            raise HTTPException(status_code=422, detail=f"Unknown option group '{group_key}' for {root.name}")
        if len(choices) > group.max_choices:
            raise HTTPException(status_code=422, detail=f"Too many choices for option group '{group_key}'")
        valid_choice_names = {
            choice.name
            for choice in db.scalars(
                select(BaseClassOptionChoice).where(BaseClassOptionChoice.group_id == group.id)
            ).all()
        }
        for choice in choices:
            if choice not in valid_choice_names:
                raise HTTPException(
                    status_code=422, detail=f"Invalid choice '{choice}' for option group '{group_key}'"
                )


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

    for selection, root in zip(body.classes, roots):
        _validate_options(db, root, selection.options)

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

    alt_trait_ability_ids: list[UUID] = []
    seen_replaced_ability_ids: set[UUID] = set()
    for trait_name in body.alt_traits:
        resolved = resolve_alt_trait(db, body.race_id, trait_name)
        if resolved is None:
            raise HTTPException(status_code=422, detail=f"Unknown alt_trait '{trait_name}' for this race")
        ability_id, replaces = resolved
        if replaces & seen_replaced_ability_ids:
            raise HTTPException(
                status_code=422, detail=f"alt_trait '{trait_name}' conflicts with another chosen alt_trait"
            )
        seen_replaced_ability_ids |= replaces
        alt_trait_ability_ids.append(ability_id)

    total_level = sum(selection.level for selection in body.classes)

    # Player-entered HP roll for every level except the character's very
    # first (always maxed automatically) - see CharacterCreate.hit_points.
    hit_dice_by_level: dict[int, int] = {}
    running_level_for_hit_dice = 0
    for selection, root in zip(body.classes, roots):
        for _ in range(selection.level):
            running_level_for_hit_dice += 1
            hit_dice_by_level[running_level_for_hit_dice] = root.hit_dice

    submitted_hit_points: dict[int, int] = {}
    for level_str, value in body.hit_points.items():
        try:
            level_num = int(level_str)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid hit_points level '{level_str}'") from exc
        submitted_hit_points[level_num] = value

    if set(submitted_hit_points) != set(range(2, total_level + 1)):
        raise HTTPException(
            status_code=422, detail=f"hit_points must include exactly one entry for each of levels 2..{total_level}"
        )
    for level_num, value in submitted_hit_points.items():
        hit_dice = hit_dice_by_level[level_num]
        if not is_valid_rolled_hit_points(hit_dice, value):
            raise HTTPException(
                status_code=422, detail=f"hit_points for level {level_num} must be between 1 and {hit_dice}"
            )

    race_mods = race_ability_score_mods(db, body.race_id)

    def _effective_ability_mod(ability: str) -> int:
        score = body.ability_scores[ability] + race_mods.get(ability, 0)
        if body.flex_ability == ability:
            score += 2
        return (score - 10) // 2

    if body.skill_ranks:
        valid_skill_ids = set(db.scalars(select(BaseSkill.id)).all())
        for skill_id_str, ranks in body.skill_ranks.items():
            try:
                skill_id = UUID(skill_id_str)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=f"Invalid skill id '{skill_id_str}'") from exc
            if skill_id not in valid_skill_ids:
                raise HTTPException(status_code=422, detail=f"Unknown skill id '{skill_id_str}'")
            if ranks > total_level:
                raise HTTPException(status_code=422, detail=f"Ranks for skill '{skill_id_str}' exceed character level")

        budget = _skill_points_total(body.classes, roots, _effective_ability_mod("IN"))
        if sum(body.skill_ranks.values()) > budget:
            raise HTTPException(status_code=422, detail="Skill ranks exceed available skill points")

    if body.feat_ids:
        max_feats = _feat_max(db, body.race_id, body.classes, seen_replaced_ability_ids)
        if len(body.feat_ids) > max_feats:
            raise HTTPException(status_code=422, detail="Too many feats chosen for character level")
        valid_feat_ids = set(db.scalars(select(BaseFeat.id)).all())
        for feat_id in body.feat_ids:
            if feat_id not in valid_feat_ids:
                raise HTTPException(status_code=422, detail=f"Unknown feat id '{feat_id}'")

    if body.trait_ids:
        traits_by_id = {
            trait.id: trait for trait in db.scalars(select(BaseTrait).where(BaseTrait.id.in_(body.trait_ids))).all()
        }
        for trait_id in body.trait_ids:
            if trait_id not in traits_by_id:
                raise HTTPException(status_code=422, detail=f"Unknown trait id '{trait_id}'")
        areas = [traits_by_id[trait_id].area for trait_id in body.trait_ids]
        if len(set(areas)) != len(areas):
            raise HTTPException(status_code=422, detail="trait_ids must not include two traits from the same area")

    if body.spell_ids:
        level_by_root_id: dict[UUID, int] = {}
        for selection, root in zip(body.classes, roots):
            level_by_root_id[root.id] = level_by_root_id.get(root.id, 0) + selection.level

        for base_class_id_str, spell_ids in body.spell_ids.items():
            try:
                base_class_id = UUID(base_class_id_str)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=f"Invalid base_class_id '{base_class_id_str}'") from exc
            class_level = level_by_root_id.get(base_class_id)
            if class_level is None:
                raise HTTPException(status_code=422, detail="spell_ids references a class this character isn't taking")
            root = next(r for r in roots if r.id == base_class_id)

            class_def = _class_def(root.name) or {}
            spell_type = class_def.get("spellType", "none")
            if spell_type not in ("spontaneous", "arcane-prepared"):
                raise HTTPException(status_code=422, detail=f"{root.name} has no known-spell list to choose from")

            grade_by_spell_id = {
                row.spell_id: row.grade
                for row in db.scalars(select(BaseClassSpell).where(BaseClassSpell.base_class_id == base_class_id)).all()
            }
            for spell_id in spell_ids:
                if spell_id not in grade_by_spell_id:
                    raise HTTPException(status_code=422, detail=f"Spell not on {root.name}'s spell list")

            if spell_type == "spontaneous":
                budget = spontaneous_known_budget(db, base_class_id, class_level)
                picked_by_grade: dict[int, int] = {}
                for spell_id in spell_ids:
                    grade = grade_by_spell_id[spell_id]
                    picked_by_grade[grade] = picked_by_grade.get(grade, 0) + 1
                for grade, picked_count in picked_by_grade.items():
                    if picked_count > budget.get(grade, 0):
                        raise HTTPException(
                            status_code=422, detail=f"Too many grade {grade} spells known for {root.name}"
                        )
            else:  # arcane-prepared
                mandatory_grade0 = {sid for sid, grade in grade_by_spell_id.items() if grade == 0}
                submitted = set(spell_ids)
                if not mandatory_grade0.issubset(submitted):
                    raise HTTPException(
                        status_code=422, detail=f"{root.name}'s spellbook must include all grade-0 spells"
                    )
                non_grade0 = submitted - mandatory_grade0
                accessible_grades = known_grades(db, base_class_id, class_level)
                for spell_id in non_grade0:
                    if grade_by_spell_id[spell_id] not in accessible_grades:
                        raise HTTPException(
                            status_code=422, detail=f"Grade {grade_by_spell_id[spell_id]} not yet accessible for {root.name}"
                        )
                ability_mod = _effective_ability_mod(root.casting_ability) if root.casting_ability else 0
                budget = arcane_prepared_budget(class_level, ability_mod)
                if len(non_grade0) > budget:
                    raise HTTPException(status_code=422, detail=f"Too many spells chosen for {root.name}'s spellbook")

    if body.gear:
        valid_item_ids = set(db.scalars(select(BaseItem.id)).all())
        for selection in body.gear:
            if selection.item_id not in valid_item_ids:
                raise HTTPException(status_code=422, detail=f"Unknown item id '{selection.item_id}'")

    character = Character(
        name=body.name,
        user_id=body.user_id,
        race_id=body.race_id,
        ability_score_st=body.ability_scores["ST"],
        ability_score_ge=body.ability_scores["GE"],
        ability_score_ko=body.ability_scores["KO"],
        ability_score_in=body.ability_scores["IN"],
        ability_score_we=body.ability_scores["WE"],
        ability_score_ch=body.ability_scores["CH"],
        point_budget=body.point_budget,
    )
    if flex_ability_id is not None:
        character.racial_choices.append(CharacterRacialChoice(ability_id=flex_ability_id))
    for ability_id in alt_trait_ability_ids:
        character.racial_choices.append(CharacterRacialChoice(ability_id=ability_id))
    for selection in body.gear:
        character.gear.append(CharacterGear(item_id=selection.item_id, quantity=selection.quantity))

    # The root of the first submitted class is favored by default — matches
    # the class picker's row order, not something the wizard asks for yet.
    favored_root_id = roots[0].id
    seen_root_ids: set[UUID] = set()
    seen_archetype_ids_by_root: dict[UUID, set[UUID]] = {}

    running_level = 0
    last_level_row: CharacterLevel | None = None
    for selection, root, archetypes in zip(body.classes, roots, archetypes_per_selection):
        for _ in range(selection.level):
            running_level += 1
            hit_points = root.hit_dice if running_level == 1 else submitted_hit_points[running_level]
            last_level_row = CharacterLevel(level=running_level, base_class_id=root.id, hit_points=hit_points)
            character.levels.append(last_level_row)
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

    # requirements_v2.md §2: HP = sum of Hit Dice from all classes + CON mod
    # x character level. A freshly created character starts at full health,
    # so this is also the initial `current_hit_points` (damage tracking is a
    # later `PATCH .../hp` concern, see todos.md).
    character.current_hit_points = sum(level.hit_points for level in character.levels) + _effective_ability_mod(
        "KO"
    ) * total_level

    if last_level_row is not None:
        for skill_id_str, ranks in body.skill_ranks.items():
            if ranks > 0:
                last_level_row.skill_ranks.append(CharacterSkillRank(skill_id=UUID(skill_id_str), ranks=ranks))
        for feat_id in body.feat_ids:
            last_level_row.feats.append(CharacterFeat(feat_id=feat_id))
        for trait_id in body.trait_ids:
            last_level_row.traits.append(CharacterTrait(trait_id=trait_id))
        for base_class_id_str, spell_ids in body.spell_ids.items():
            base_class_id = UUID(base_class_id_str)
            for spell_id in spell_ids:
                last_level_row.spells.append(CharacterSpell(base_class_id=base_class_id, spell_id=spell_id))

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


@router.post("/{character_id}/spellbook", response_model=CharacterRead, status_code=201)
def add_to_spellbook(character_id: UUID, body: SpellbookAdd, db: Annotated[Session, Depends(get_db)]) -> Character:
    """In-play "add a spell to the spellbook" (`requirements_v2.md` §2.2:
    managed like inventory, not just at creation/level-up). Arcane-prepared
    classes only — spontaneous casters only ever learn new spells at
    level-up (`rules/spells.py`), and divine-prepared casters already have
    the full class list available, nothing to add. Uncapped (no server-side
    limit): gold/downtime cost for scribing a new spell isn't tracked yet."""
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    root = db.get(BaseClass, body.base_class_id)
    if root is None or root.arch_class_of is not None:
        raise HTTPException(status_code=422, detail="Unknown base_class_id")
    class_level = sum(1 for level in character.levels if level.base_class_id == root.id)
    if class_level == 0:
        raise HTTPException(status_code=422, detail="This character isn't taking that class")

    class_def = _class_def(root.name) or {}
    if class_def.get("spellType") != "arcane-prepared":
        raise HTTPException(status_code=422, detail=f"{root.name} doesn't manage a spellbook this way")

    class_spell = db.scalar(
        select(BaseClassSpell).where(
            BaseClassSpell.base_class_id == root.id, BaseClassSpell.spell_id == body.spell_id
        )
    )
    if class_spell is None:
        raise HTTPException(status_code=422, detail=f"Spell not on {root.name}'s spell list")
    if class_spell.grade != 0 and class_spell.grade not in known_grades(db, root.id, class_level):
        raise HTTPException(status_code=422, detail=f"Grade {class_spell.grade} not yet accessible for {root.name}")

    already_known = any(
        entry.base_class_id == root.id and entry.spell_id == body.spell_id
        for level in character.levels
        for entry in level.spells
    )
    if already_known:
        raise HTTPException(status_code=422, detail="Spell is already in the spellbook")

    last_level = character.levels[-1]
    last_level.spells.append(CharacterSpell(base_class_id=root.id, spell_id=body.spell_id))
    db.commit()
    db.refresh(character)
    return character


@router.delete("/{character_id}/spellbook/{spell_id}", status_code=204)
def remove_from_spellbook(character_id: UUID, spell_id: UUID, db: Annotated[Session, Depends(get_db)]) -> None:
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    entries = [entry for level in character.levels for entry in level.spells if entry.spell_id == spell_id]
    if not entries:
        raise HTTPException(status_code=404, detail="Spell not found in spellbook")
    for entry in entries:
        db.delete(entry)
    db.commit()


@router.delete("/{character_id}", status_code=204)
def delete_character(character_id: UUID, db: Annotated[Session, Depends(get_db)]) -> None:
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    db.delete(character)
    db.commit()
