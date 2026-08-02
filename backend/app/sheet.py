"""Serializes a database-backed `Character` into the frontend's full sheet
shape (`frontend/src/types/character.ts`'s `Character` interface) — the
"thick" read-side counterpart to `create_character`'s persistence
(`routers/characters.py`). Composition (which feats/traits/spells/etc. a
character has) is already resolved by `Character`'s own properties
(`feat_ids`, `trait_ids`, ...); this module's job is purely the display
computation — joining those ids to their catalog rows and formatting values
— the same composition-vs-computation split as everywhere else (CLAUDE.md).

Subsystems that genuinely don't exist yet are left as honest empty defaults,
not fabricated placeholder content:
- `equipmentSlots`: armor/shield (roadmap slice 4) are real — equip state and
  AC contribution come from `CharacterGear`/`BaseItem.ac_bonus`. The other 12
  wondrous-item slots (rings, belts, ...) have no real catalog content yet,
  so they're listed (for the paperdoll's fixed layout) with empty options.
- `actions` catalog and `effectsActive` (roadmap slice 6).
- Per-day spell prepare/cast tracking (roadmap slice 6) — `spellsKnown`
  (`used`) and `spellbook` (`prepared`) both list every known spell with
  their tracking flag always `False`.

Likewise `armorClass`/`combat`'s CMB/CMD assume an unarmored, Medium
creature: `BaseRace` has no size field yet, so no size modifier is applied
(a Small race like Halfling/Gnome should get +1 AC/attack, -1 CMB/CMD in
real PF1e — not modeled here)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    BaseClass,
    BaseClassAbility,
    BaseClassAbilityGrant,
    BaseClassAbilityReplacement,
    BaseClassOptionChoice,
    BaseClassOptionGroup,
    BaseClassSkill,
    BaseClassSpell,
    BaseFeat,
    BaseItem,
    BaseRace,
    BaseRaceAbility,
    BaseSkill,
    BaseSpell,
    BaseTrait,
    Character,
    RaceAbilityGrant,
)
from .routers.characters import _class_def
from .routers.races import race_ability_score_mods
from .rules.equipment_slots import SLOT_CATEGORY, SLOT_DEFINITIONS
from .rules.modifiers import Modifier, stack
from .rules.speed import race_speed
from .rules.progression import ability_mod, effective_ability_scores, max_hit_points

ABILITY_LABELS = {"ST": "STÄ", "GE": "GES", "KO": "KON", "IN": "INT", "WE": "WEI", "CH": "CHA"}
SAVE_LABELS = {"fort": "Zähigkeit", "ref": "Reflex", "will": "Willen"}


def _fmt(mod: int) -> str:
    return ("+" if mod >= 0 else "") + str(mod)


def build_character_sheet(character: Character, db: Session) -> dict:
    race = db.get(BaseRace, character.race_id)
    classes = character.classes
    favored = next((c for c in classes if c["is_favored"]), classes[0] if classes else None)
    class_name = favored["class_name"] if favored else ""
    archetype = ", ".join(favored["archetypes"]) if favored and favored["archetypes"] else "Keiner"

    race_mods = race_ability_score_mods(db, character.race_id)
    effective_scores = effective_ability_scores(character.ability_scores, race_mods, character.flex_ability)
    ability_mods = {ability: ability_mod(score) for ability, score in effective_scores.items()}

    total_level = character.level
    hp_max = max_hit_points([lvl.hit_points for lvl in character.levels], ability_mods["KO"], total_level)
    # Legacy characters created before HP was computed at all may still have
    # a null current_hit_points (see Character.current_hit_points's
    # docstring) — fall back to full health rather than send `null` for a
    # field the frontend types as a plain number.
    hp_current = character.current_hit_points if character.current_hit_points is not None else hp_max

    str_mod = ability_mods["ST"]
    dex_mod = ability_mods["GE"]
    bab = character.bab
    armor_class, equipment_slots = _build_equipment(db, character, dex_mod)

    level_counts_by_root_id: dict[UUID, int] = {}
    for lvl in character.levels:
        level_counts_by_root_id[lvl.base_class_id] = level_counts_by_root_id.get(lvl.base_class_id, 0) + 1

    return {
        "id": str(character.id),
        "name": character.name,
        "race": race.name if race else "",
        "className": class_name,
        "archetype": archetype,
        "level": total_level,
        "hp": {"current": hp_current, "max": hp_max},
        "armorClass": armor_class,
        "initiative": _fmt(dex_mod),
        "speed": race_speed(db, character.race_id) or "9 m",
        "roundLabel": "Runde 1",
        "abilities": [
            {
                "key": ability,
                "label": ABILITY_LABELS[ability],
                "score": effective_scores[ability],
                "mod": _fmt(ability_mods[ability]),
            }
            for ability in ("ST", "GE", "KO", "IN", "WE", "CH")
        ],
        "saves": [
            {"key": key, "label": label, "value": _fmt(character.saves[key])} for key, label in SAVE_LABELS.items()
        ],
        "combat": [
            {"key": "bab", "label": "Grundangriffsbonus (GAB)", "value": _fmt(bab)},
            {"key": "cmb", "label": "Kampfmanöverbonus (KMB)", "value": _fmt(bab + str_mod)},
            {"key": "cmd", "label": "Kampfmanöverabwehr (KMD)", "value": str(10 + bab + str_mod + dex_mod)},
        ],
        "skills": _build_skills(db, character, level_counts_by_root_id, ability_mods),
        "feats": _described(db, BaseFeat, character.feat_ids),
        "traits": _described(db, BaseTrait, character.trait_ids),
        "classFeatures": _build_class_features(db, character, level_counts_by_root_id),
        "raceAbilities": _build_race_abilities(db, character.race_id),
        "spellsKnown": _build_spell_grades(db, character, "used"),
        "gear": _build_gear(db, character),
        "equipmentSlots": equipment_slots,
        "spellbook": _build_spell_grades(db, character, "prepared"),
        "actions": [],
        "effectsActive": [],
    }


def _described(db: Session, model: type, ids: list[UUID]) -> list[dict]:
    if not ids:
        return []
    rows = db.scalars(select(model).where(model.id.in_(ids))).all()
    return [{"key": str(row.id), "name": row.name, "description": row.description} for row in rows]


def _build_skills(
    db: Session,
    character: Character,
    level_counts_by_root_id: dict[UUID, int],
    ability_mods: dict[str, int],
) -> list[dict]:
    skill_ranks = {UUID(skill_id): ranks for skill_id, ranks in character.skill_ranks.items() if ranks > 0}
    if not skill_ranks:
        return []

    class_skill_ids: set[UUID] = set()
    if level_counts_by_root_id:
        # option_choice_id IS NULL only: unconditional class skills. Mystery-
        # conditional additions (Mystiker/Oracle) exist in the table but
        # aren't cross-referenced against this character's actual
        # CharacterClassOption picks yet - composition is real data, this
        # computation is still open (same "not yet enforced" state as every
        # other option-gated pool in this codebase, see todos.md).
        class_skill_ids = set(
            db.scalars(
                select(BaseClassSkill.skill_id).where(
                    BaseClassSkill.base_class_id.in_(level_counts_by_root_id),
                    BaseClassSkill.option_choice_id.is_(None),
                )
            ).all()
        )

    skills = {skill.id: skill for skill in db.scalars(select(BaseSkill).where(BaseSkill.id.in_(skill_ranks))).all()}

    result = []
    for skill_id, ranks in skill_ranks.items():
        skill = skills.get(skill_id)
        if skill is None:
            continue
        ab_mod = ability_mods.get(skill.ability, 0)
        class_bonus = 3 if skill_id in class_skill_ids else 0
        result.append({"key": str(skill_id), "label": skill.name, "value": _fmt(ranks + ab_mod + class_bonus)})
    return result


def _build_class_features(
    db: Session, character: Character, level_counts_by_root_id: dict[UUID, int]
) -> list[dict]:
    if not level_counts_by_root_id:
        return []

    # Archetypes don't have independent levels — an archetype's own grants
    # (`BaseClassAbilityGrant.base_class_id` = the archetype's id, see that
    # model's docstring) are gated against the level count of the root class
    # they're taken with, same as the root's own grants.
    root_id_by_class_id: dict[UUID, UUID] = {root_id: root_id for root_id in level_counts_by_root_id}
    archetype_ids: set[UUID] = set()
    for membership in character.class_memberships:
        base_class = membership.base_class
        if base_class.arch_class_of in level_counts_by_root_id:
            root_id_by_class_id[base_class.id] = base_class.arch_class_of
            archetype_ids.add(base_class.id)

    chosen_option_ids: set[UUID] = set()
    for option in character.class_options:
        choice_row = db.scalar(
            select(BaseClassOptionChoice)
            .join(BaseClassOptionGroup, BaseClassOptionGroup.id == BaseClassOptionChoice.group_id)
            .where(
                BaseClassOptionGroup.base_class_id == option.base_class_id,
                BaseClassOptionGroup.key == option.group_key,
                BaseClassOptionChoice.name == option.choice,
            )
        )
        if choice_row is not None:
            chosen_option_ids.add(choice_row.id)

    grants = db.scalars(
        select(BaseClassAbilityGrant).where(BaseClassAbilityGrant.base_class_id.in_(root_id_by_class_id))
    ).all()

    replaced_grant_ids: set[UUID] = set()
    if archetype_ids:
        replaced_grant_ids = set(
            db.scalars(
                select(BaseClassAbilityReplacement.replaces_grant_id).where(
                    BaseClassAbilityReplacement.archetype_class_id.in_(archetype_ids)
                )
            ).all()
        )

    ability_ids: set[UUID] = set()
    for grant in grants:
        if grant.id in replaced_grant_ids:
            continue
        if grant.level > level_counts_by_root_id[root_id_by_class_id[grant.base_class_id]]:
            continue
        if grant.option_choice_id is not None and grant.option_choice_id not in chosen_option_ids:
            continue
        ability_ids.add(grant.ability_id)

    return _described(db, BaseClassAbility, list(ability_ids))


def _build_race_abilities(db: Session, race_id: UUID) -> list[dict]:
    grants = db.scalars(
        select(RaceAbilityGrant).where(RaceAbilityGrant.race_id == race_id, RaceAbilityGrant.is_alternate.is_(False))
    ).all()
    return _described(db, BaseRaceAbility, [grant.ability_id for grant in grants])


def _build_spell_grades(db: Session, character: Character, flag_name: str) -> list[dict]:
    by_grade: dict[int, list[dict]] = {}
    for base_class_id_str, spell_ids in character.spell_ids.items():
        root = db.get(BaseClass, UUID(base_class_id_str))
        if root is None or not spell_ids:
            continue
        class_def = _class_def(root.name) or {}
        if class_def.get("spellType") not in ("spontaneous", "arcane-prepared"):
            continue

        grade_by_spell_id = {
            row.spell_id: row.grade
            for row in db.scalars(
                select(BaseClassSpell).where(
                    BaseClassSpell.base_class_id == root.id, BaseClassSpell.spell_id.in_(spell_ids)
                )
            ).all()
        }
        spells = {spell.id: spell for spell in db.scalars(select(BaseSpell).where(BaseSpell.id.in_(spell_ids))).all()}
        for spell_id in spell_ids:
            spell = spells.get(spell_id)
            if spell is None:
                continue
            grade = grade_by_spell_id.get(spell_id, 0)
            by_grade.setdefault(grade, []).append(
                {"key": str(spell_id), "name": spell.name, flag_name: False}
            )

    return [{"grade": grade, "locked": False, "spells": spells} for grade, spells in sorted(by_grade.items())]


def _build_gear(db: Session, character: Character) -> list[dict]:
    if not character.gear:
        return []
    items = {item.id: item for item in db.scalars(select(BaseItem).where(BaseItem.id.in_(
        [g.item_id for g in character.gear]
    ))).all()}
    result = []
    for gear_row in character.gear:
        item = items.get(gear_row.item_id)
        if item is None:
            continue
        # id is the item's own id, not the CharacterGear row's — matches
        # PATCH/DELETE .../gear/{item_id}'s path param (item_id is already a
        # stable per-character key, `CharacterGear.character_id`+`item_id` is
        # unique), so the frontend can call those endpoints directly.
        entry = {"id": str(gear_row.item_id), "name": item.name, "qty": gear_row.quantity}
        if gear_row.enhancement:
            entry["enhancement"] = f"+{gear_row.enhancement}"
        if gear_row.properties:
            entry["properties"] = gear_row.properties
        result.append(entry)
    return result


def _build_equipment(db: Session, character: Character, dex_mod: int) -> tuple[int, list[dict]]:
    """Armor class + paperdoll slots from equipped gear (roadmap slice 4).
    Only armor ("ruestung") and shield ("schild") have real `BaseItem.ac_bonus`
    data (`rules/equipment_slots.SLOT_CATEGORY`) — the other 12 slots render
    with empty options (see this module's docstring)."""
    if not character.gear:
        return 10 + dex_mod, [{**slot_def, "options": [], "selected": ""} for slot_def in SLOT_DEFINITIONS]

    items = {
        item.id: item
        for item in db.scalars(select(BaseItem).where(BaseItem.id.in_([g.item_id for g in character.gear]))).all()
    }
    gear_by_slot = {g.equipped_slot: g for g in character.gear if g.equipped_slot}

    modifiers: list[Modifier] = []
    max_dex_bonus: int | None = None
    for slot_key, category in SLOT_CATEGORY.items():
        gear_row = gear_by_slot.get(slot_key)
        item = items.get(gear_row.item_id) if gear_row else None
        if item is None:
            continue
        modifiers.append(Modifier(source=item.name, type=category, value=(item.ac_bonus or 0) + gear_row.enhancement))
        if category == "armor":
            max_dex_bonus = item.max_dex_bonus

    capped_dex_mod = dex_mod if max_dex_bonus is None else min(dex_mod, max_dex_bonus)
    armor_class = 10 + capped_dex_mod + stack(modifiers)

    owned_by_category: dict[str, list[BaseItem]] = {}
    for gear_row in character.gear:
        item = items.get(gear_row.item_id)
        if item is not None:
            owned_by_category.setdefault(item.category, []).append(item)

    equipment_slots = []
    for slot_def in SLOT_DEFINITIONS:
        required_category = SLOT_CATEGORY.get(slot_def["key"])
        options: list[dict] = []
        selected = ""
        if required_category is not None:
            options = [
                {"value": str(candidate.id), "label": candidate.name}
                for candidate in owned_by_category.get(required_category, [])
            ]
            equipped = gear_by_slot.get(slot_def["key"])
            if equipped is not None:
                selected = str(equipped.item_id)
        equipment_slots.append({**slot_def, "options": options, "selected": selected})

    return armor_class, equipment_slots
