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
    BaseClassAbility,
    BaseClassOptionChoice,
    BaseClassOptionGroup,
    BaseClassSpell,
    BaseCondition,
    BaseFeat,
    BaseItem,
    BaseRace,
    BaseSkill,
    BaseSpell,
    BaseTrait,
    BaseWeaponSpecialAbility,
    Character,
    CharacterClass,
    CharacterClassOption,
    CharacterEffect,
    CharacterFeat,
    CharacterGear,
    CharacterGearSpecialAbility,
    CharacterLevel,
    CharacterRacialChoice,
    CharacterSkillRank,
    CharacterSpell,
    CharacterTrait,
    User,
)
from ..rules.effective_scores import full_effective_ability_scores
from ..rules.equipment_slots import SLOT_CATEGORY, SLOT_TO_ITEM_SLOT
from ..rules.feat_slots import base_feat_count, class_bonus_feat_slot_count, race_grants_bonus_feat
from ..rules.point_buy import spent_points
from ..rules.progression import ability_mod, effective_ability_scores, is_valid_rolled_hit_points, max_hit_points
from ..rules.skill_points import race_grants_bonus_skill_point_per_level
from ..rules.spells import arcane_prepared_budget, known_grades, spontaneous_known_budget
from ..schemas.character import (
    AdvanceTime,
    CharacterCreate,
    CharacterRead,
    CharacterUpdate,
    ClassSelection,
    EffectActivate,
    EffectRead,
    EffectSaveResult,
    FeatSelection,
    GearSelection,
    GearUpdate,
    HpAdjust,
    LevelUp,
    SlotUpdate,
    SpellbookAdd,
)
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


def _skill_points_total(
    classes: list[ClassSelection], roots: list[BaseClass], int_mod: int, race_bonus_per_level: int = 0
) -> int:
    """Mirrors the frontend's `skillPointsTotal` (creationCalculations.ts):
    per class-taken, max(1, class's base skill points + INT modifier) times
    the levels taken in it, summed across all classes. `roots` is
    index-aligned with `classes` (both come from the same `zip` elsewhere in
    this module) — `BaseClass.skill_points_base`, not `classes.json`, is the
    source of truth now. `race_bonus_per_level` (e.g. Human's "Geschult") is
    a flat extra rank per *character* level, not per class-taken — see
    `rules/skill_points.py`."""
    total = 0
    total_level = 0
    for selection, root in zip(classes, roots):
        total += max(1, root.skill_points_base + int_mod) * selection.level
        total_level += selection.level
    return total + race_bonus_per_level * total_level


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


def _validate_feat_sub_choice(
    db: Session, feat: BaseFeat, selection: FeatSelection, known_spell_schools: set[str]
) -> None:
    """Enforces `BaseFeat.sub_choice_type` against one submitted
    `FeatSelection` (roadmap.md's "Talent-Sub-Wahl-Schema") — which of
    `chosen_weapon_id`/`chosen_skill_id`/`chosen_spell_school` must be set,
    and what it must resolve against, depends on the feat itself, so this
    can't live in the schema layer (`FeatSelection.at_most_one_sub_choice`
    only checks that at most one is set at all, not which one is required)."""
    sub_choice_type = feat.sub_choice_type
    if sub_choice_type is None:
        if selection.chosen_weapon_id or selection.chosen_skill_id or selection.chosen_spell_school:
            raise HTTPException(status_code=422, detail=f"'{feat.name}' does not take a sub-choice")
        return

    if sub_choice_type == "weapon":
        if selection.chosen_weapon_id is None:
            raise HTTPException(status_code=422, detail=f"'{feat.name}' requires a chosen_weapon_id")
        weapon = db.get(BaseItem, selection.chosen_weapon_id)
        if weapon is None or weapon.category != "weapon":
            raise HTTPException(status_code=422, detail=f"chosen_weapon_id for '{feat.name}' is not a known weapon")
    elif sub_choice_type == "skill":
        if selection.chosen_skill_id is None:
            raise HTTPException(status_code=422, detail=f"'{feat.name}' requires a chosen_skill_id")
        if db.get(BaseSkill, selection.chosen_skill_id) is None:
            raise HTTPException(status_code=422, detail=f"chosen_skill_id for '{feat.name}' is not a known skill")
    elif sub_choice_type == "spell_school":
        if selection.chosen_spell_school is None:
            raise HTTPException(status_code=422, detail=f"'{feat.name}' requires a chosen_spell_school")
        if selection.chosen_spell_school not in known_spell_schools:
            raise HTTPException(
                status_code=422, detail=f"chosen_spell_school for '{feat.name}' is not a known spell school"
            )


def _validate_options(db: Session, root: BaseClass, options: dict[str, list[str]], character_level: int) -> None:
    """Validates submitted option-group choices (e.g. Kleriker's `domain`)
    against `base_class_option_groups`/`base_class_option_choices` — real
    tables now (see `app/seed/class_option_seed.py`), not `classes.json`.
    `character_level` is the character's level *in this root class*
    (summed across every `ClassSelection` row for it, for creation; the
    receiving class's own new level, for a level-up) — checked against each
    submitted choice's `BaseClassOptionChoice.min_level` (e.g. Mystiker's
    Offenbarung choices each carry their own threshold; Kampfrauschkraft's
    "Innere Zähigkeit" needs Barbar 8). `None` means no threshold beyond the
    group's own grant level, so nothing to check."""
    groups = db.scalars(select(BaseClassOptionGroup).where(BaseClassOptionGroup.base_class_id == root.id)).all()
    groups_by_key = {group.key: group for group in groups}
    for group_key, choices in options.items():
        group = groups_by_key.get(group_key)
        if group is None:
            raise HTTPException(status_code=422, detail=f"Unknown option group '{group_key}' for {root.name}")
        if len(choices) > group.max_choices:
            raise HTTPException(status_code=422, detail=f"Too many choices for option group '{group_key}'")
        choices_by_name = {
            choice.name: choice
            for choice in db.scalars(
                select(BaseClassOptionChoice).where(BaseClassOptionChoice.group_id == group.id)
            ).all()
        }
        for choice in choices:
            choice_row = choices_by_name.get(choice)
            if choice_row is None:
                raise HTTPException(
                    status_code=422, detail=f"Invalid choice '{choice}' for option group '{group_key}'"
                )
            if choice_row.min_level is not None and character_level < choice_row.min_level:
                raise HTTPException(
                    status_code=422,
                    detail=f"'{choice}' requires {root.name} level {choice_row.min_level} (currently {character_level})",
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

    level_by_root_id: dict[UUID, int] = {}
    for selection, root in zip(body.classes, roots):
        level_by_root_id[root.id] = level_by_root_id.get(root.id, 0) + selection.level

    for selection, root in zip(body.classes, roots):
        _validate_options(db, root, selection.options, level_by_root_id[root.id])

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
    effective_scores = effective_ability_scores(body.ability_scores, race_mods, body.flex_ability)

    def _effective_ability_mod(ability: str) -> int:
        return ability_mod(effective_scores[ability])

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

        race_skill_bonus = 1 if race_grants_bonus_skill_point_per_level(db, body.race_id, seen_replaced_ability_ids) else 0
        budget = _skill_points_total(body.classes, roots, _effective_ability_mod("IN"), race_skill_bonus)
        if sum(body.skill_ranks.values()) > budget:
            raise HTTPException(status_code=422, detail="Skill ranks exceed available skill points")

    if body.feats:
        max_feats = _feat_max(db, body.race_id, body.classes, seen_replaced_ability_ids)
        if len(body.feats) > max_feats:
            raise HTTPException(status_code=422, detail="Too many feats chosen for character level")
        selected_feat_ids = {selection.feat_id for selection in body.feats}
        feats_by_id = {
            feat.id: feat for feat in db.scalars(select(BaseFeat).where(BaseFeat.id.in_(selected_feat_ids))).all()
        }
        known_spell_schools = set(db.scalars(select(BaseSpell.school).distinct()).all())
        for selection in body.feats:
            feat = feats_by_id.get(selection.feat_id)
            if feat is None:
                raise HTTPException(status_code=422, detail=f"Unknown feat id '{selection.feat_id}'")
            _validate_feat_sub_choice(db, feat, selection, known_spell_schools)

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
                casting_ability_mod = _effective_ability_mod(root.casting_ability) if root.casting_ability else 0
                budget = arcane_prepared_budget(class_level, casting_ability_mod)
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
                choice_row = db.scalar(
                    select(BaseClassOptionChoice)
                    .join(BaseClassOptionGroup, BaseClassOptionGroup.id == BaseClassOptionChoice.group_id)
                    .where(
                        BaseClassOptionGroup.base_class_id == root.id,
                        BaseClassOptionGroup.key == group_key,
                        BaseClassOptionChoice.name == choice,
                    )
                )
                character.class_options.append(
                    CharacterClassOption(
                        base_class_id=root.id,
                        group_key=group_key,
                        choice=choice,
                        choice_id=choice_row.id if choice_row is not None else None,
                        level=last_level_row,
                    )
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

    # A freshly created character starts undamaged — max HP itself
    # (requirements_v2.md §2: sum of Hit Dice from all classes + CON mod x
    # character level) is derived at read time (`sheet.py`), not stored;
    # `damage_taken` is the only HP-related state persisted here (damage
    # tracking beyond creation is a later `PATCH .../hp` concern, see
    # todos.md).
    character.damage_taken = 0

    if last_level_row is not None:
        for skill_id_str, ranks in body.skill_ranks.items():
            if ranks > 0:
                last_level_row.skill_ranks.append(CharacterSkillRank(skill_id=UUID(skill_id_str), ranks=ranks))
        for selection in body.feats:
            last_level_row.feats.append(
                CharacterFeat(
                    feat_id=selection.feat_id,
                    chosen_weapon_id=selection.chosen_weapon_id,
                    chosen_skill_id=selection.chosen_skill_id,
                    chosen_spell_school=selection.chosen_spell_school,
                )
            )
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


@router.patch("/{character_id}/hp", response_model=CharacterRead)
def adjust_hp(character_id: UUID, body: HpAdjust, db: Annotated[Session, Depends(get_db)]) -> Character:
    """Applies damage (negative `delta`) or healing (positive `delta`) to a
    character's current HP. Only `Character.damage_taken` is ever
    persisted — remaining HP is always derived (`hp_max - damage_taken`,
    same formula as `sheet.py`'s display), so this endpoint just moves that
    one column, clamped to PF1e's real HP range: `damage_taken` is bounded
    to `[0, hp_max + con_score]`, i.e. current HP can never exceed `hp_max`
    (healing past full is wasted, not stored as overheal) and can't drop
    below `-con_score` (PF1e RAW death threshold: a character dies at
    negative HP equal to their full Constitution *score*, not modifier —
    beyond that point further damage no longer changes the stored value).

    `hp_max`/`con_score` here use the same `full_effective_ability_scores`
    (gear bonuses, ability damage, race/flex) that `sheet.py`'s
    `build_character_sheet` reads from, so a CON-boosting item (e.g. a
    "Gürtel der großen Konstitution") affects both consistently — this used
    to read only base/race/flex scores, silently under-computing `hp_max`
    (by the item's CON-mod bonus per level) and the death floor (by the raw
    bonus) for anyone wearing one."""
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    race_mods = race_ability_score_mods(db, character.race_id)
    effective_scores = full_effective_ability_scores(db, character, race_mods)
    con_score = effective_scores["KO"]
    con_mod = ability_mod(con_score)
    hp_max = max_hit_points([level.hit_points for level in character.levels], con_mod, character.level)

    new_damage_taken = (character.damage_taken or 0) - body.delta
    character.damage_taken = max(0, min(new_damage_taken, hp_max + con_score))

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


@router.post("/{character_id}/gear", response_model=CharacterRead, status_code=201)
def add_gear(character_id: UUID, body: GearSelection, db: Annotated[Session, Depends(get_db)]) -> Character:
    """In-play "add to inventory" (roadmap slice 4) — unlike creation's
    `gear` validator, which rejects duplicate item_ids within one
    submission, adding an already-owned item here just increases its
    quantity (picking up another torch), rather than erroring."""
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    item = db.get(BaseItem, body.item_id)
    if item is None:
        raise HTTPException(status_code=422, detail="Unknown item_id")

    existing = next((g for g in character.gear if g.item_id == body.item_id), None)
    if existing is not None:
        existing.quantity += body.quantity
    else:
        # New instance starts "full" — matches roadmap.md's "Wondrous-Item-
        # Katalog" decision that the catalog only declares the maximum,
        # per-instance counters are `CharacterGear` state.
        character.gear.append(
            CharacterGear(
                item_id=body.item_id,
                quantity=body.quantity,
                charges_remaining=item.max_charges,
                uses_remaining_today=item.uses_per_day,
            )
        )
    db.commit()
    db.refresh(character)
    return character


@router.patch("/{character_id}/gear/{item_id}", response_model=CharacterRead)
def update_gear(
    character_id: UUID, item_id: UUID, body: GearUpdate, db: Annotated[Session, Depends(get_db)]
) -> Character:
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    gear_row = next((g for g in character.gear if g.item_id == item_id), None)
    if gear_row is None:
        raise HTTPException(status_code=404, detail="Item not found in inventory")

    if body.quantity is not None:
        gear_row.quantity = body.quantity
    if body.enhancement is not None:
        gear_row.enhancement = body.enhancement
    if body.properties is not None:
        gear_row.properties = body.properties
    if body.special_ability_ids is not None:
        known_ids = set(
            db.scalars(
                select(BaseWeaponSpecialAbility.id).where(BaseWeaponSpecialAbility.id.in_(body.special_ability_ids))
            ).all()
        )
        unknown_ids = set(body.special_ability_ids) - known_ids
        if unknown_ids:
            raise HTTPException(status_code=422, detail=f"Unknown special_ability_ids: {sorted(map(str, unknown_ids))}")
        gear_row.special_abilities = [CharacterGearSpecialAbility(ability_id=ability_id) for ability_id in body.special_ability_ids]
    if body.stored_spell_id is not None:
        item = db.get(BaseItem, item_id)
        if item is None or item.category != "wand":
            raise HTTPException(status_code=422, detail="stored_spell_id is only valid for a wand")
        if db.get(BaseSpell, body.stored_spell_id) is None:
            raise HTTPException(status_code=422, detail="Unknown stored_spell_id")
        gear_row.stored_spell_id = body.stored_spell_id
    db.commit()
    db.refresh(character)
    return character


@router.patch("/{character_id}/gear/{item_id}/use", response_model=CharacterRead)
def use_gear(character_id: UUID, item_id: UUID, db: Annotated[Session, Depends(get_db)]) -> Character:
    """Consume one use of an item's trackable counter (roadmap.md's
    "Wondrous-Item-Katalog mit echter Attributsboni-Wirkung", decided
    2026-08-04) — a wand's `charges_remaining` if it has one (never resets on
    its own), else an "N-mal pro Tag" item's `uses_remaining_today` (reset by
    `POST /{character_id}/rest`). Items with neither (permanent, or
    unlimited-use "aktivierbar" items — see `toggle_gear` for those) have
    nothing to consume."""
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    gear_row = next((g for g in character.gear if g.item_id == item_id), None)
    if gear_row is None:
        raise HTTPException(status_code=404, detail="Item not found in inventory")

    if gear_row.charges_remaining is not None:
        if gear_row.charges_remaining <= 0:
            raise HTTPException(status_code=422, detail="No charges remaining")
        gear_row.charges_remaining -= 1
    elif gear_row.uses_remaining_today is not None:
        if gear_row.uses_remaining_today <= 0:
            raise HTTPException(status_code=422, detail="No uses remaining today")
        gear_row.uses_remaining_today -= 1
    else:
        raise HTTPException(status_code=422, detail="This item has no trackable charges/uses")

    db.commit()
    db.refresh(character)
    return character


@router.patch("/{character_id}/gear/{item_id}/toggle", response_model=CharacterRead)
def toggle_gear(character_id: UUID, item_id: UUID, db: Annotated[Session, Depends(get_db)]) -> Character:
    """Flip `is_active` for an unlimited-use "aktivierbar" item whose effect
    is toggled rather than consumed (e.g. Energieschildring: +2 RK only
    while active) — see roadmap.md's "Wondrous-Item-Katalog mit echter
    Attributsboni-Wirkung", decided 2026-08-04."""
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    gear_row = next((g for g in character.gear if g.item_id == item_id), None)
    if gear_row is None:
        raise HTTPException(status_code=404, detail="Item not found in inventory")
    item = db.get(BaseItem, item_id)
    if item is None or item.activation != "activatable":
        raise HTTPException(status_code=422, detail="This item cannot be toggled active/inactive")

    gear_row.is_active = not gear_row.is_active
    db.commit()
    db.refresh(character)
    return character


@router.post("/{character_id}/rest", response_model=CharacterRead)
def rest(character_id: UUID, db: Annotated[Session, Depends(get_db)]) -> Character:
    """Deliberately narrow pull-forward of roadmap slice 5's "rest" concept
    (decided 2026-08-04, see roadmap.md's "Wondrous-Item-Katalog mit echter
    Attributsboni-Wirkung") — resets every equipped-or-owned item's
    `uses_remaining_today` back to its catalog `uses_per_day`. Does not touch
    `charges_remaining` (wand charges never auto-reset) or `is_active`
    (toggled items keep their state across a rest)."""
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    if not character.gear:
        return character

    items = {
        item.id: item
        for item in db.scalars(
            select(BaseItem).where(BaseItem.id.in_([g.item_id for g in character.gear]))
        ).all()
    }
    for gear_row in character.gear:
        item = items.get(gear_row.item_id)
        if item is not None and item.uses_per_day is not None:
            gear_row.uses_remaining_today = item.uses_per_day

    db.commit()
    db.refresh(character)
    return character


ROUND_CONVERSION = {"round": 1, "minute": 10, "hour": 600}


def _get_character_effect(character: Character, effect_id: UUID) -> CharacterEffect:
    effect = next((e for e in character.effects if e.id == effect_id), None)
    if effect is None:
        raise HTTPException(status_code=404, detail="Effect not found")
    return effect


@router.post("/{character_id}/effects", response_model=EffectRead, status_code=201)
def activate_effect(
    character_id: UUID, body: EffectActivate, db: Annotated[Session, Depends(get_db)]
) -> CharacterEffect:
    """Activates a persistent effect (roadmap slice 5) — whether this
    specific character actually knows/has the referenced spell/ability isn't
    checked here (slice 6's "legality checks"), only that the reference
    resolves and, for spell/class_ability, is flagged `is_persistent_effect`."""
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    if body.source_type == "spell":
        spell = db.get(BaseSpell, body.source_id)
        if spell is None or not spell.is_persistent_effect:
            raise HTTPException(status_code=422, detail="Not a persistent-effect spell")
    elif body.source_type == "class_ability":
        ability = db.get(BaseClassAbility, body.source_id)
        if ability is None or not ability.is_persistent_effect:
            raise HTTPException(status_code=422, detail="Not a persistent-effect class ability")
    else:
        if db.get(BaseCondition, body.source_id) is None:
            raise HTTPException(status_code=422, detail="Unknown condition")

    effect = CharacterEffect(
        character_id=character_id,
        source_type=body.source_type,
        source_id=body.source_id,
        level=body.level,
        incubation_remaining=body.incubation_remaining,
        duration_remaining=body.duration_remaining,
        frequency_rounds=body.frequency_rounds,
        next_check_in=body.frequency_rounds,
        successes_required=body.successes_required,
    )
    db.add(effect)
    db.commit()
    db.refresh(effect)
    return effect


@router.delete("/{character_id}/effects/{effect_id}", status_code=204)
def remove_effect(character_id: UUID, effect_id: UUID, db: Annotated[Session, Depends(get_db)]) -> None:
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    effect = _get_character_effect(character, effect_id)
    db.delete(effect)
    db.commit()


@router.post("/{character_id}/effects/{effect_id}/save-result", response_model=EffectRead)
def record_effect_save_result(
    character_id: UUID, effect_id: UUID, body: EffectSaveResult, db: Annotated[Session, Depends(get_db)]
) -> EffectRead:
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    effect = _get_character_effect(character, effect_id)
    if effect.frequency_rounds is None:
        raise HTTPException(status_code=422, detail="This effect has no periodic save to record")

    effect.next_check_in = effect.frequency_rounds
    cured = False
    if body.success:
        effect.successes_current += 1
        cured = effect.successes_required is not None and effect.successes_current >= effect.successes_required
    else:
        effect.successes_current = 0

    # Built from the still-attached, not-yet-committed row rather than
    # returned after commit: if `cured`, the row is about to be deleted, and
    # a deleted-then-expired ORM instance can't be re-read for serialization.
    result = EffectRead.model_validate(effect)
    if cured:
        db.delete(effect)
    db.commit()
    return result


@router.post("/{character_id}/advance-time", response_model=list[EffectRead])
def advance_time(
    character_id: UUID, body: AdvanceTime, db: Annotated[Session, Depends(get_db)]
) -> list[CharacterEffect]:
    """Ticks every active effect's countdowns forward by one unit (roadmap
    slice 5) — round=1/minute=10/hour=600, same conversion the mock's time
    buttons already use. "day" is a full rest: plain-duration effects (no
    `frequency_rounds`) are removed outright; frequency-tracked ones
    (poison/disease) are left alone, since surviving a rest is correct PF1e
    behavior for those, unlike the old mock's blanket clear."""
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    remaining: list[CharacterEffect] = []
    if body.unit == "day":
        for effect in character.effects:
            if effect.frequency_rounds is None:
                db.delete(effect)
            else:
                remaining.append(effect)
    else:
        rounds = ROUND_CONVERSION[body.unit]
        for effect in character.effects:
            if effect.incubation_remaining is not None:
                effect.incubation_remaining = max(0, effect.incubation_remaining - rounds)
            if effect.duration_remaining is not None:
                effect.duration_remaining = max(0, effect.duration_remaining - rounds)
            if effect.next_check_in is not None:
                effect.next_check_in = max(0, effect.next_check_in - rounds)

            if effect.frequency_rounds is None and effect.duration_remaining == 0:
                db.delete(effect)
            else:
                remaining.append(effect)

    db.commit()
    for effect in remaining:
        db.refresh(effect)
    return remaining


@router.delete("/{character_id}/gear/{item_id}", status_code=204)
def remove_gear(character_id: UUID, item_id: UUID, db: Annotated[Session, Depends(get_db)]) -> None:
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    gear_row = next((g for g in character.gear if g.item_id == item_id), None)
    if gear_row is None:
        raise HTTPException(status_code=404, detail="Item not found in inventory")
    db.delete(gear_row)
    db.commit()


@router.put("/{character_id}/slots/{slot_key}", response_model=CharacterRead)
def update_slot(
    character_id: UUID, slot_key: str, body: SlotUpdate, db: Annotated[Session, Depends(get_db)]
) -> Character:
    """Equip/unequip into one of the paperdoll slots. `rules/equipment_slots.py`'s
    `SLOT_CATEGORY` gives the required `BaseItem.category`; for the 12
    wondrous/ring slots, which share a category between several slots,
    `SLOT_TO_ITEM_SLOT` additionally checks `BaseItem.slot` against the
    requested slot key (both ring slots accept `BaseItem.slot == "ring"`)."""
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    required_category = SLOT_CATEGORY.get(slot_key)
    if required_category is None:
        raise HTTPException(status_code=422, detail=f"Unknown or unsupported slot '{slot_key}'")
    required_item_slot = SLOT_TO_ITEM_SLOT.get(slot_key)

    # Unequip whatever currently holds this slot (only one item per slot).
    for gear_row in character.gear:
        if gear_row.equipped_slot == slot_key:
            gear_row.equipped_slot = None

    if body.item_id is not None:
        gear_row = next((g for g in character.gear if g.item_id == body.item_id), None)
        if gear_row is None:
            raise HTTPException(status_code=422, detail="Item is not in this character's inventory")
        item = db.get(BaseItem, body.item_id)
        if (
            item is None
            or item.category != required_category
            or (required_item_slot is not None and item.slot != required_item_slot)
        ):
            raise HTTPException(status_code=422, detail=f"Item does not fit slot '{slot_key}'")
        gear_row.equipped_slot = slot_key

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


def _class_selections_and_roots(db: Session, character: Character) -> tuple[list[ClassSelection], list[BaseClass]]:
    """Reconstructs the character's current classes-taken as `ClassSelection`s
    plus their resolved root `BaseClass` rows — the exact shape
    `_skill_points_total`/`_feat_max` accept — so `level_up_character` can
    call those creation-time budget functions unchanged, once for the
    character's classes before this level and once after, and diff the two
    for this level's own delta rather than writing new budget arithmetic."""
    selections = [ClassSelection.model_validate(entry) for entry in character.classes]
    roots = [resolve_root_class(db, selection.class_name) for selection in selections]
    return selections, roots


def _apply_target_to_selections(
    classes_before: list[ClassSelection],
    roots_before: list[BaseClass],
    receiving_root: BaseClass,
    is_new_class: bool,
) -> tuple[list[ClassSelection], list[BaseClass]]:
    """The character's classes-taken *after* this level-up: either the
    receiving class's level bumped by one, or (multiclassing) a brand-new
    level-1 entry appended."""
    if is_new_class:
        new_selection = ClassSelection(class_name=receiving_root.name, level=1)
        return classes_before + [new_selection], roots_before + [receiving_root]

    classes_after = [
        ClassSelection(
            class_name=selection.class_name,
            level=selection.level + 1 if root.id == receiving_root.id else selection.level,
            archetypes=selection.archetypes,
            options=selection.options,
        )
        for selection, root in zip(classes_before, roots_before)
    ]
    return classes_after, roots_before


def _character_replaced_ability_ids(db: Session, character: Character) -> set[UUID]:
    """Reconstructs `create_character`'s `seen_replaced_ability_ids` for an
    already-existing character, from its stored alt-trait *names*
    (`Character.alt_traits`) rather than a fresh request body — re-resolves
    each name via the same `resolve_alt_trait` creation uses, since the
    'replaces' ability-id set is derived from the trait name at lookup time,
    not itself persisted anywhere."""
    replaced: set[UUID] = set()
    for trait_name in character.alt_traits:
        resolved = resolve_alt_trait(db, character.race_id, trait_name)
        if resolved is not None:
            _, replaces = resolved
            replaced |= replaces
    return replaced


@router.post("/{character_id}/level-up", response_model=CharacterRead, status_code=201)
def level_up_character(character_id: UUID, body: LevelUp, db: Annotated[Session, Depends(get_db)]) -> Character:
    """Adds exactly one new `CharacterLevel` to an existing character
    (roadmap slice 7, thin). Reuses creation's own validation/budget
    functions wherever possible (see module docstrings on
    `_class_selections_and_roots`/`_apply_target_to_selections`) rather than
    re-deriving PF1e's level-up math a second time."""
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    classes_before, roots_before = _class_selections_and_roots(db, character)
    new_total_level = character.level + 1

    if body.target.mode == "existing":
        receiving_root = next((root for root in roots_before if root.id == body.target.base_class_id), None)
        if receiving_root is None:
            raise HTTPException(
                status_code=422, detail="target.base_class_id is not one of this character's classes"
            )
        is_new_class = False
        new_archetypes: list[BaseClass] = []
    else:
        receiving_root = resolve_root_class(db, body.target.class_name)
        if any(root.id == receiving_root.id for root in roots_before):
            raise HTTPException(
                status_code=422,
                detail=f"Character already has the class '{receiving_root.name}' — use target.mode 'existing'",
            )
        new_archetypes = [resolve_archetype(db, receiving_root, name) for name in body.target.archetypes]
        is_new_class = True

    classes_after, roots_after = _apply_target_to_selections(classes_before, roots_before, receiving_root, is_new_class)
    receiving_class_level = next(
        selection.level for selection, root in zip(classes_after, roots_after) if root.id == receiving_root.id
    )

    is_favored_level = not is_new_class and any(
        membership.base_class_id == receiving_root.id and membership.is_favored
        for membership in character.class_memberships
    )
    if body.favored_class_bonus is not None and not is_favored_level:
        raise HTTPException(
            status_code=422, detail="favored_class_bonus only applies when leveling up in the favored class"
        )
    if body.favored_class_bonus is None and is_favored_level:
        raise HTTPException(
            status_code=422, detail="This level is in the favored class — favored_class_bonus is required"
        )

    if is_new_class:
        _validate_options(db, receiving_root, body.target.options, receiving_class_level)

    if not is_valid_rolled_hit_points(receiving_root.hit_dice, body.hit_points):
        raise HTTPException(status_code=422, detail=f"hit_points must be between 1 and {receiving_root.hit_dice}")

    ability_increase_eligible = new_total_level % 4 == 0
    if body.ability_increase is not None and not ability_increase_eligible:
        raise HTTPException(status_code=422, detail="ability_increase is only granted every 4th character level")
    if body.ability_increase is None and ability_increase_eligible:
        raise HTTPException(
            status_code=422, detail="This level grants an ability score increase — ability_increase is required"
        )
    if body.ability_increase is not None:
        column = f"ability_score_{body.ability_increase.lower()}"
        setattr(character, column, getattr(character, column) + 1)

    if body.target.mode == "existing" and body.existing_level_options:
        if any(len(choices) > 1 for choices in body.existing_level_options.values()):
            raise HTTPException(
                status_code=422,
                detail="Only one pick is allowed per recurring option group at a single level-up",
            )
        _validate_options(db, receiving_root, body.existing_level_options, receiving_class_level)

    seen_replaced_ability_ids = _character_replaced_ability_ids(db, character)
    race_mods = race_ability_score_mods(db, character.race_id)
    effective_scores = effective_ability_scores(character.ability_scores, race_mods, character.flex_ability)

    def _effective_ability_mod(ability: str) -> int:
        return ability_mod(effective_scores[ability])

    race_skill_bonus = (
        1 if race_grants_bonus_skill_point_per_level(db, character.race_id, seen_replaced_ability_ids) else 0
    )
    favored_skill_bonus = 1 if body.favored_class_bonus == "skill" else 0
    skill_budget_delta = (
        _skill_points_total(classes_after, roots_after, _effective_ability_mod("IN"), race_skill_bonus)
        - _skill_points_total(classes_before, roots_before, _effective_ability_mod("IN"), race_skill_bonus)
        + favored_skill_bonus
    )
    if sum(body.skill_ranks.values()) > skill_budget_delta:
        raise HTTPException(status_code=422, detail="skill_ranks exceed the skill points gained at this level")

    valid_skill_ids = set(db.scalars(select(BaseSkill.id)).all())
    existing_skill_ranks = character.skill_ranks
    for skill_id_str, new_ranks in body.skill_ranks.items():
        try:
            skill_id = UUID(skill_id_str)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid skill id '{skill_id_str}'") from exc
        if skill_id not in valid_skill_ids:
            raise HTTPException(status_code=422, detail=f"Unknown skill id '{skill_id_str}'")
        # Per PF1e (http://prd.5footstep.de/Grundregelwerk/Fertigkeiten-erwerben):
        # the only cap on a single skill is total ranks <= character level -
        # a previously-untrained skill may legally gain more than 1 new rank
        # in one level-up, not just +1.
        if existing_skill_ranks.get(skill_id_str, 0) + new_ranks > new_total_level:
            raise HTTPException(status_code=422, detail=f"Ranks for skill '{skill_id_str}' would exceed character level")

    feat_budget_delta = _feat_max(db, character.race_id, classes_after, seen_replaced_ability_ids) - _feat_max(
        db, character.race_id, classes_before, seen_replaced_ability_ids
    )
    if len(body.feats) > feat_budget_delta:
        raise HTTPException(status_code=422, detail="Too many feats chosen for this level")
    feats_by_id: dict[UUID, BaseFeat] = {}
    if body.feats:
        selected_feat_ids = {selection.feat_id for selection in body.feats}
        feats_by_id = {
            feat.id: feat for feat in db.scalars(select(BaseFeat).where(BaseFeat.id.in_(selected_feat_ids))).all()
        }
        known_spell_schools = set(db.scalars(select(BaseSpell.school).distinct()).all())
        already_known = {
            (entry["feat_id"], entry["chosen_weapon_id"], entry["chosen_skill_id"], entry["chosen_spell_school"])
            for entry in character.feats
        }
        for selection in body.feats:
            feat = feats_by_id.get(selection.feat_id)
            if feat is None:
                raise HTTPException(status_code=422, detail=f"Unknown feat id '{selection.feat_id}'")
            _validate_feat_sub_choice(db, feat, selection, known_spell_schools)
            key = (
                selection.feat_id,
                selection.chosen_weapon_id,
                selection.chosen_skill_id,
                selection.chosen_spell_school,
            )
            if key in already_known:
                raise HTTPException(status_code=422, detail=f"'{feat.name}' with this sub-choice is already known")

    class_spell: BaseClassSpell | None = None
    if body.spell_id is not None:
        class_def = _class_def(receiving_root.name) or {}
        spell_type = class_def.get("spellType", "none")
        if spell_type not in ("spontaneous", "arcane-prepared"):
            raise HTTPException(status_code=422, detail=f"{receiving_root.name} has no known-spell list to choose from")
        class_spell = db.scalar(
            select(BaseClassSpell).where(
                BaseClassSpell.base_class_id == receiving_root.id, BaseClassSpell.spell_id == body.spell_id
            )
        )
        if class_spell is None:
            raise HTTPException(status_code=422, detail=f"Spell not on {receiving_root.name}'s spell list")
        already_known_spells = set(character.spell_ids.get(str(receiving_root.id), []))
        if body.spell_id in already_known_spells:
            raise HTTPException(status_code=422, detail="Spell is already known")

        if spell_type == "spontaneous":
            budget = spontaneous_known_budget(db, receiving_root.id, receiving_class_level)
            known_at_grade = db.scalars(
                select(BaseClassSpell.spell_id).where(
                    BaseClassSpell.base_class_id == receiving_root.id,
                    BaseClassSpell.grade == class_spell.grade,
                    BaseClassSpell.spell_id.in_(already_known_spells),
                )
            ).all()
            if len(known_at_grade) >= budget.get(class_spell.grade, 0):
                raise HTTPException(
                    status_code=422, detail=f"No grade {class_spell.grade} spell slots available at this level"
                )
        else:  # arcane-prepared
            if class_spell.grade == 0:
                raise HTTPException(status_code=422, detail="Grade-0 spells are already known automatically")
            accessible_grades = known_grades(db, receiving_root.id, receiving_class_level)
            if class_spell.grade not in accessible_grades:
                raise HTTPException(
                    status_code=422, detail=f"Grade {class_spell.grade} not yet accessible for {receiving_root.name}"
                )
            casting_ability_mod = (
                _effective_ability_mod(receiving_root.casting_ability) if receiving_root.casting_ability else 0
            )
            budget = arcane_prepared_budget(receiving_class_level, casting_ability_mod)
            known_non_grade0 = sum(
                1
                for row in db.scalars(
                    select(BaseClassSpell.grade).where(
                        BaseClassSpell.base_class_id == receiving_root.id,
                        BaseClassSpell.spell_id.in_(already_known_spells),
                    )
                ).all()
                if row != 0
            )
            if known_non_grade0 >= budget:
                raise HTTPException(status_code=422, detail="No spellbook slots available at this level")

    favored_hp_bonus = 1 if body.favored_class_bonus == "hp" else 0
    new_level = CharacterLevel(
        level=new_total_level,
        base_class_id=receiving_root.id,
        hit_points=body.hit_points + favored_hp_bonus,
        ability_increase=body.ability_increase,
    )
    character.levels.append(new_level)

    if is_new_class:
        character.class_memberships.append(CharacterClass(base_class_id=receiving_root.id, is_favored=False))
        for archetype in new_archetypes:
            character.class_memberships.append(CharacterClass(base_class_id=archetype.id))
        for group_key, choices in body.target.options.items():
            for choice in choices:
                choice_row = db.scalar(
                    select(BaseClassOptionChoice)
                    .join(BaseClassOptionGroup, BaseClassOptionGroup.id == BaseClassOptionChoice.group_id)
                    .where(
                        BaseClassOptionGroup.base_class_id == receiving_root.id,
                        BaseClassOptionGroup.key == group_key,
                        BaseClassOptionChoice.name == choice,
                    )
                )
                character.class_options.append(
                    CharacterClassOption(
                        base_class_id=receiving_root.id,
                        group_key=group_key,
                        choice=choice,
                        choice_id=choice_row.id if choice_row is not None else None,
                        level=new_level,
                    )
                )
    elif body.existing_level_options:
        for group_key, choices in body.existing_level_options.items():
            for choice in choices:
                choice_row = db.scalar(
                    select(BaseClassOptionChoice)
                    .join(BaseClassOptionGroup, BaseClassOptionGroup.id == BaseClassOptionChoice.group_id)
                    .where(
                        BaseClassOptionGroup.base_class_id == receiving_root.id,
                        BaseClassOptionGroup.key == group_key,
                        BaseClassOptionChoice.name == choice,
                    )
                )
                character.class_options.append(
                    CharacterClassOption(
                        base_class_id=receiving_root.id,
                        group_key=group_key,
                        choice=choice,
                        choice_id=choice_row.id if choice_row is not None else None,
                        level=new_level,
                    )
                )

    for skill_id_str, new_ranks in body.skill_ranks.items():
        new_level.skill_ranks.append(CharacterSkillRank(skill_id=UUID(skill_id_str), ranks=new_ranks))
    for selection in body.feats:
        new_level.feats.append(
            CharacterFeat(
                feat_id=selection.feat_id,
                chosen_weapon_id=selection.chosen_weapon_id,
                chosen_skill_id=selection.chosen_skill_id,
                chosen_spell_school=selection.chosen_spell_school,
            )
        )
    if body.spell_id is not None:
        new_level.spells.append(CharacterSpell(base_class_id=receiving_root.id, spell_id=body.spell_id))

    db.commit()
    db.refresh(character)
    return character
