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
- `actions` catalog (roadmap slice 6, thin cut): only the subset of
  already-activatable data a character has (persistent-effect spells known,
  persistent-effect class abilities granted, activatable gear — see
  `_build_actions`). No action-cost/type field exists anywhere in the schema
  (`BaseSpell`/`BaseFeat`/`BaseItem`), so every entry's `tag` is `None`
  rather than a guessed value, and there's no usable-now/legality filtering
  yet — a thick-pass follow-up. `effectsActive` stays a hardcoded `[]`, but
  only because it's the older mock seal system's field (icon/amount/variant,
  `/api/effects`) — real active effects (roadmap slice 5) are now served
  separately as `activeEffects`/`activatableSpells`/
  `activatableClassAbilities`/`externalClassAbilities`, see
  `_build_active_effects` below.
- Per-day spell prepare/cast tracking (roadmap slice 6) is real for arcane-
  and divine-prepared classes (`_build_prepared_spell_grades`). Spontaneous
  casters (Barde/Hexenmeister/Mystiker) deliberately get no `spellsKnown`/
  `spellbook` entries at all for now, rather than a stale placeholder — they
  need a structurally different per-grade slot pool (no per-spell
  "prepared" step, any known spell can fill any same-grade slot), not an
  extension of the arcane-/divine-prepared shape above, so this is an honest
  gap left for a follow-up rather than the old always-`False` placeholder.

Likewise `armorClass`/`combat`'s CMB/CMD assume an unarmored, Medium
creature: `BaseRace` has no size field yet, so no size modifier is applied
(a Small race like Halfling/Gnome should get +1 AC/attack, -1 CMB/CMD in
real PF1e — not modeled here)."""

from collections import Counter, defaultdict
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
    BaseClassSpellsKnown,
    BaseCondition,
    BaseFeat,
    BaseItem,
    BaseItemGrantedSpell,
    BaseRace,
    BaseRaceAbility,
    BaseSkill,
    BaseSkillSpecialization,
    BaseSpell,
    BaseSpellComponent,
    BaseTrait,
    BaseWeaponSpecialAbility,
    Character,
    CharacterGear,
)
from .routers.characters import _class_def
from .routers.races import effective_race_ability_ids, race_ability_score_mods, race_skill_modifiers
from .rules.class_options import favored_class_bonus_race_choices
from .rules.context import CharacterContext
from .rules.daily_limits import remaining_today
from .rules.effective_scores import ability_damage_totals, full_effective_ability_scores
from .rules.equipment_slots import SLOT_CATEGORY, SLOT_DEFINITIONS, SLOT_TO_ITEM_SLOT
from .rules.favored_class_bonuses import HANDLERS as FAVORED_CLASS_BONUS_HANDLERS
from .rules.favored_class_bonuses import SHORT_LABELS as FAVORED_CLASS_BONUS_SHORT_LABELS
from .rules.favored_class_bonuses import pick_counts as favored_class_bonus_pick_counts
from .rules.classes.kampfmagus import KENSAI_WEAPON_CHOICE_ABILITY_ID, KENSAI_WEAPON_FOCUS_ABILITY_ID
from .rules.feats import (
    HEFTIGER_ANGRIFF,
    WAFFENFINESSE,
    WAFFENFOKUS,
    WAFFENFOKUS_ATTACK_BONUS,
    power_attack_bonus,
)
from .rules.handlers import (
    DAILY_LIMIT_UNIT_LABEL,
    DAILY_LIMITS,
    NATURAL_ATTACK_HANDLERS,
    WEAPON_BONUS_DAMAGE_HANDLERS,
    WEAPON_ENHANCEMENT_HANDLERS,
    WEAPON_PROFICIENCY_HANDLERS,
    character_modifiers,
    granted_ability_modifiers,
    has_mechanical_effect,
    situational_skill_notes,
)
from .rules.modifiers import Modifier, ModifierTarget, SkillNote, contributing, group_by_target, stack
from .rules.proficiency import (
    DUAL_NATURE_WEAPON_FEAT_IDS,
    NOT_PROFICIENT_ATTACK_PENALTY,
    class_granted_proficiency_feat_ids,
    known_weapon_types,
)
from .rules.speed import class_speed_bonus, jump_skill_note, race_speed
from .rules.progression import ability_mod, max_hit_points
from .rules.spells import known_grades, total_spell_slots
from .rules.weapon_abilities import resolve as resolve_weapon_ability

ABILITY_LABELS = {"ST": "STÄ", "GE": "GES", "KO": "KON", "IN": "INT", "WE": "WEI", "CH": "CHA"}
SAVE_LABELS = {"fort": "Zähigkeit", "ref": "Reflex", "will": "Willen"}
# Which ability modifier each save adds on top of Character.saves' base
# class-progression bonus (`rules/progression.py`'s `class_save_bonus`) —
# that property has no DB access for race/flex-adjusted scores, so the
# ability-mod addition happens here, alongside this module's other
# `effective_ability_scores`-dependent display math.
SAVE_ABILITY = {"fort": "KO", "ref": "GE", "will": "WE"}
SAVE_TARGET = {"fort": ModifierTarget.SAVE_FORT, "ref": ModifierTarget.SAVE_REF, "will": ModifierTarget.SAVE_WILL}

def _fmt(mod: int) -> str:
    return ("+" if mod >= 0 else "") + str(mod)


def build_character_sheet(character: Character, db: Session) -> dict:
    race = db.get(BaseRace, character.race_id)
    classes = character.classes
    favored = next((c for c in classes if c["is_favored"]), classes[0] if classes else None)
    class_name = favored["class_name"] if favored else ""
    archetype = ", ".join(favored["archetypes"]) if favored and favored["archetypes"] else "Keiner"
    favored_membership = next((m for m in character.class_memberships if m.is_favored), None)
    favored_root_id = favored_membership.base_class_id if favored_membership else None

    race_mods = race_ability_score_mods(db, character.race_id)
    effective_scores = full_effective_ability_scores(db, character, race_mods)
    ability_damage = ability_damage_totals(character)

    level_counts_by_root_id: dict[UUID, int] = {}
    for lvl in character.levels:
        level_counts_by_root_id[lvl.base_class_id] = level_counts_by_root_id.get(lvl.base_class_id, 0) + 1
    granted_ability_ids = granted_class_ability_ids(db, character, level_counts_by_root_id)
    # Resolved ahead of `chosen_weapon_ids` below (not just where
    # `_build_natural_attacks` needs it further down) so a race ability like
    # Elf's "Elfische Waffenvertrautheit" can fold its named weapons into
    # that same set.
    race_ability_ids = effective_race_ability_ids(
        db, character.race_id, {choice.ability_id for choice in character.racial_choices}
    )
    class_granted_weapon_feat_ids = class_granted_proficiency_feat_ids(db, granted_ability_ids)
    # Weapon a class ability's own one-off choice named (`CharacterClassAbilityWeaponChoice`,
    # e.g. Kensai's kensai weapon) — keyed by ability id, read once here for
    # both the proficiency and Weapon-Focus folding right below.
    weapon_choice_by_ability_id = {
        choice.ability_id: choice.weapon_id for choice in character.class_ability_weapon_choices
    }
    # A picked "Umgang mit exotischen Waffen" names one specific weapon
    # rather than the whole category (`rules/proficiency.py`'s module
    # docstring); Kensai's own weapon choice is a proficiency for that exact
    # weapon the same way. Gathered here, once, the same way `character.feat_ids`
    # itself is flattened across every level's picks. A race ability's own
    # fixed named-weapon list (`rules/handlers.py`'s `WEAPON_PROFICIENCY_HANDLERS`,
    # e.g. Elf's "Elfische Waffenvertrautheit") folds in the same way, for
    # every race ability id this character actually has.
    chosen_weapon_ids = (
        frozenset(
            entry.chosen_weapon_id
            for level in character.levels
            for entry in level.feats
            if entry.feat_id in DUAL_NATURE_WEAPON_FEAT_IDS and entry.chosen_weapon_id is not None
        )
        | ({weapon_choice_by_ability_id[KENSAI_WEAPON_CHOICE_ABILITY_ID]}
           if KENSAI_WEAPON_CHOICE_ABILITY_ID in weapon_choice_by_ability_id else set())
        | frozenset(
            item_id
            for ability_id in race_ability_ids
            for item_id in WEAPON_PROFICIENCY_HANDLERS.get(ability_id, ())
        )
    )
    # Weapon Focus's +1 attack bonus applies to a player's own ordinary
    # Waffenfokus pick (`CharacterFeat.chosen_weapon_id`) and, for free, to a
    # Kensai's kensai weapon via their separate "Waffenfokus (Kensai)"
    # ability grant (`rules/classes/kampfmagus.py`'s module docstring) —
    # folded into one set so `_build_weapon_attacks` has a single check
    # regardless of source.
    weapon_focus_weapon_ids = frozenset(
        entry.chosen_weapon_id
        for level in character.levels
        for entry in level.feats
        if entry.feat_id == WAFFENFOKUS and entry.chosen_weapon_id is not None
    ) | (
        {weapon_choice_by_ability_id[KENSAI_WEAPON_CHOICE_ABILITY_ID]}
        if KENSAI_WEAPON_FOCUS_ABILITY_ID in granted_ability_ids
        and KENSAI_WEAPON_CHOICE_ABILITY_ID in weapon_choice_by_ability_id
        else set()
    )

    # `requires_active_ability_id` for whichever of this character's granted
    # abilities actually have it set (most don't — `.is_not(None)` keeps this
    # dict small) — feeds `CharacterContext.requirement_met`, the one query
    # every rage-power-shaped ability (Erneuerte Lebenskraft, Bestientotem,
    # ...) needs instead of each handler hardcoding what gates it.
    requires_active_ability_id: dict[UUID, UUID] = {}
    if granted_ability_ids:
        requires_active_ability_id = {
            row.id: row.requires_active_ability_id
            for row in db.scalars(
                select(BaseClassAbility).where(
                    BaseClassAbility.id.in_(list(granted_ability_ids)),
                    BaseClassAbility.requires_active_ability_id.is_not(None),
                )
            ).all()
        }

    # Fetched here, ahead of `context` below, so its two AC-gate fields
    # (`equipped_armor_weight_class`/`has_shield_equipped`) can be populated
    # from the same lookup the AC computation further down already needs —
    # see `_gear_ac_modifiers`'s own call further below, which reuses these
    # same `items`/`gear_by_slot` rather than re-querying.
    items, gear_by_slot = _gear_lookup(db, character)
    armor_gear_row = gear_by_slot.get("ruestung")
    armor_item = items.get(armor_gear_row.item_id) if armor_gear_row else None
    shield_gear_row = gear_by_slot.get("schild")
    equipped_weapon_ids = frozenset(
        gear_row.item_id
        for slot_key in ("hauptwaffe", "nebenwaffe")
        if (gear_row := gear_by_slot.get(slot_key)) is not None
    )

    # The character's raw `CharacterContext` (`rules/context.py`) — built
    # once here, fully populated, and threaded into every handler family
    # below rather than each one re-deriving its own slice of character
    # state, per `readme.md`'s "Request pipeline" step 2. `ability_scores`
    # is the already-fully-resolved effective scores (race/flex/gear/damage,
    # `rules/effective_scores.py`), not raw base scores — a handler reading
    # it (e.g. a future Skill-Focus-style threshold) sees the same total the
    # sheet itself displays.
    context = CharacterContext(
        ability_scores=effective_scores,
        skill_ranks={UUID(skill_id): ranks for skill_id, ranks in character.skill_ranks.items()},
        feat_ids=frozenset(character.feat_ids),
        trait_ids=frozenset(character.trait_ids),
        trait_skill_choices=character.trait_skill_choices,
        granted_ability_ids=granted_ability_ids,
        active_effects=character.effects,
        gear_item_ids=frozenset(g.item_id for g in character.gear),
        level_counts_by_root_id=level_counts_by_root_id,
        favored_class_bonus_pick_counts=favored_class_bonus_pick_counts(character),
        requires_active_ability_id=requires_active_ability_id,
        class_granted_proficiency_feat_ids=class_granted_weapon_feat_ids,
        chosen_weapon_ids=chosen_weapon_ids,
        weapon_focus_weapon_ids=weapon_focus_weapon_ids,
        equipped_armor_weight_class=armor_item.armor_weight_class if armor_item else None,
        has_shield_equipped=shield_gear_row is not None and items.get(shield_gear_row.item_id) is not None,
        equipped_weapon_ids=equipped_weapon_ids,
        kensai_chosen_weapon_id=weapon_choice_by_ability_id.get(KENSAI_WEAPON_CHOICE_ABILITY_ID),
    )
    # Every Modifier from a composition source that doesn't already have its
    # own dedicated, repeat-count-aware resolution pipeline — feats, traits,
    # active effects (`rules/handlers.py`'s `character_modifiers`; race/class
    # granted-ability ids are deliberately excluded there, see its
    # docstring) — plus a race's own SKILL-target grants (`race_skill_modifiers`,
    # e.g. Halb-Ork's Einschüchternd — SCORE/SPEED already have their own
    # dedicated path, see that function's docstring), granted class
    # abilities' own AC-target grants (`granted_ability_modifiers`, e.g.
    # Bestientotem's natural armor bonus — the same per-grant path
    # `class_speed_bonus` uses for SPEED, generalized), and gear's own AC
    # bonus (armor/shield `ac_bonus`, any slot's `enhancement`). Combined
    # into one raw list *before* stacking, not stacked separately per source
    # and added: two same-type bonuses (e.g. a composition "armor" bonus and
    # a gear "armor" bonus) must not both apply, and `stack()` can only
    # enforce that within a single call (`rules/modifiers.py`'s
    # `stack_by_target` docstring). Grouped by target once here and threaded
    # into AC/saves/speed/skills below as plain dict lookups rather than
    # each one re-filtering/re-stacking. `items`/`gear_by_slot` were already
    # fetched above, ahead of `context`.
    gear_ac_modifiers, max_dex_bonus = _gear_ac_modifiers(items, gear_by_slot)
    all_modifiers = (
        character_modifiers(context)
        + race_skill_modifiers(db, character.race_id)
        + granted_ability_modifiers(context, target=ModifierTarget.AC)
    )
    # Grouped once here (`rules/modifiers.py`'s `group_by_target`), rather
    # than each consumer below re-filtering the same flat list — `stacked`
    # (the summed total per target, what AC/saves/speed/skills actually add
    # up) and `groups` (the raw per-target Modifier list, what the AC/skill
    # breakdowns below read `contributing()` off of) both come from this one
    # pass.
    groups = group_by_target(all_modifiers + gear_ac_modifiers)
    stacked = {key: stack(group) for key, group in groups.items()}

    # A SCORE-target Modifier (e.g. Erschöpft's -2 ST/GE, `rules/effects.py`)
    # only reaches `stacked` above, not `effective_scores` itself — race/flex/
    # gear/ability-damage adjustments are already baked into `effective_scores`
    # before `context` is even built (`rules/effective_scores.py`), so an
    # active-effect penalty needs its own fold-in step here, applied before
    # `ability_mods`/HP/str_mod/dex_mod are derived from it below so every
    # downstream consumer (saves, skills, attacks, CMB/CMD, HP) sees the
    # penalized score, not the pre-effect one.
    #
    # `pre_effect_scores` is captured *before* that fold-in purely so the
    # "abilities" section below can show a value-origin tooltip for whichever
    # penalty/bonus actually moved the score (same `breakdown`/`formatBreakdown`
    # pattern `armorClassBreakdown`/`SkillEntry.breakdown` already use) — race/
    # gear/ability-damage stay a single opaque "Basis" line (not itemized
    # further, since `full_effective_ability_scores` doesn't expose those
    # separately either) while feat/trait/active-effect contributions
    # (`contributing()` on the SCORE group) get their own labeled line.
    pre_effect_scores = dict(effective_scores)
    ability_score_breakdowns: dict[str, list[dict]] = {}
    for ability in effective_scores:
        contributing_score_mods = contributing(groups.get((ModifierTarget.SCORE, ability), []))
        if contributing_score_mods:
            ability_score_breakdowns[ability] = [
                {"label": "Basis", "value": pre_effect_scores[ability]},
                *({"label": m.source, "value": m.value} for m in contributing_score_mods),
            ]
        bonus = stacked.get((ModifierTarget.SCORE, ability), 0)
        if bonus:
            effective_scores[ability] += bonus
    ability_mods = {ability: ability_mod(score) for ability, score in effective_scores.items()}

    total_level = character.level
    hp_max = max_hit_points([lvl.hit_points for lvl in character.levels], ability_mods["KO"], total_level)
    # Legacy characters created before HP was computed at all may still have
    # a null damage_taken (see Character.damage_taken's docstring) — treated
    # as undamaged. `hp.current` (remaining HP) is derived here, not stored;
    # only damage is persisted.
    damage_taken = character.damage_taken if character.damage_taken is not None else 0
    hp_current = hp_max - damage_taken

    str_mod = ability_mods["ST"]
    dex_mod = ability_mods["GE"]
    bab = character.bab

    capped_dex_mod = dex_mod if max_dex_bonus is None else min(dex_mod, max_dex_bonus)
    armor_class = 10 + capped_dex_mod + stacked.get((ModifierTarget.AC, None), 0)
    armor_class_breakdown = _ac_breakdown(capped_dex_mod, groups)
    non_dodge_ac_modifiers = [m for m in groups.get((ModifierTarget.AC, None), []) if m.type != "dodge"]
    armor_class_flat_footed = 10 + stack(non_dodge_ac_modifiers)
    armor_class_flat_footed_breakdown = _ac_breakdown_flat_footed(groups)
    equipment_slots = _build_equipment(character, items, gear_by_slot)

    base_speed = race_speed(db, character.race_id) or 9
    total_speed = base_speed + class_speed_bonus(context) + stacked.get((ModifierTarget.SPEED, None), 0)
    gear = _build_gear(db, character)
    melee_attack_bonus = stacked.get((ModifierTarget.ATTACK, None), 0)
    melee_damage_bonus = stacked.get((ModifierTarget.DAMAGE, None), 0)
    weapon_attacks = _build_weapon_attacks(
        items, gear_by_slot, gear, bab, str_mod, dex_mod, melee_attack_bonus, melee_damage_bonus, context,
        granted_ability_ids,
    ) + _build_natural_attacks(
        items,
        gear_by_slot,
        race_ability_ids,
        granted_ability_ids,
        context,
        bab,
        str_mod,
        melee_attack_bonus,
        melee_damage_bonus,
    )
    spellbook, spells_known = _build_prepared_spell_grades(
        db, character, level_counts_by_root_id, ability_mods, granted_ability_ids
    )
    concentration = _build_concentration(db, level_counts_by_root_id, ability_mods, stacked)

    return {
        "id": str(character.id),
        "name": character.name,
        "race": race.name if race else "",
        "className": class_name,
        "archetype": archetype,
        "level": total_level,
        "hp": {"current": hp_current, "max": hp_max, "temporary": character.temporary_hit_points},
        "armorClass": armor_class,
        "armorClassBreakdown": armor_class_breakdown,
        "armorClassFlatFooted": armor_class_flat_footed,
        "armorClassFlatFootedBreakdown": armor_class_flat_footed_breakdown,
        "initiative": _fmt(dex_mod),
        "speed": f"{total_speed} m",
        "roundLabel": "Runde 1",
        "abilities": [
            {
                "key": ability,
                "label": ABILITY_LABELS[ability],
                "score": effective_scores[ability],
                "mod": _fmt(ability_mods[ability]),
                "damage": ability_damage.get(ability, 0),
                **({"breakdown": ability_score_breakdowns[ability]} if ability in ability_score_breakdowns else {}),
            }
            for ability in ("ST", "GE", "KO", "IN", "WE", "CH")
        ],
        "saves": [
            {
                "key": key,
                "label": label,
                "value": _fmt(
                    character.saves[key]
                    + ability_mods[SAVE_ABILITY[key]]
                    + stacked.get((SAVE_TARGET[key], None), 0)
                ),
            }
            for key, label in SAVE_LABELS.items()
        ],
        "combat": [
            {"key": "bab", "label": "Grundangriffsbonus (GAB)", "value": _fmt(bab)},
            {
                "key": "cmb",
                "label": "Kampfmanöverbonus (KMB)",
                "value": _fmt(bab + str_mod + melee_attack_bonus),
            },
            {"key": "cmd", "label": "Kampfmanöverabwehr (KMD)", "value": str(10 + bab + str_mod + dex_mod)},
            *concentration,
        ],
        "skills": _build_skills(
            db, character, level_counts_by_root_id, ability_mods, total_speed, stacked, groups, context
        ),
        "feats": _build_feats(db, character),
        "traits": _build_traits(db, character),
        "classFeatures": _build_class_features(db, granted_ability_ids),
        "raceAbilities": _build_race_abilities(db, race_ability_ids),
        "favoredClassBonusOptions": _favored_class_bonus_options(db, favored_root_id, character.race_id),
        "favoredClassBonuses": _build_favored_class_bonuses(db, character),
        "spellsKnown": spells_known,
        "gear": gear,
        "weaponAttacks": weapon_attacks,
        "equipmentSlots": equipment_slots,
        "spellbook": spellbook,
        "actions": _build_actions(db, character, granted_ability_ids, gear, context),
        "effectsActive": [],
        "activeEffects": _build_active_effects(db, character, context)
        + _build_item_granted_effects(db, items, gear_by_slot),
        "activatableSpells": _build_activatable_spells(db, character),
        "activatableClassAbilities": _build_activatable_class_abilities(db, character, context, granted_ability_ids),
        "activatableFeats": _build_activatable_feats(db, character),
        "externalClassAbilities": _build_external_class_abilities(db),
        "externalSpells": _build_external_spells(db),
    }


def build_character_progression(character: Character, db: Session) -> dict:
    """The level-up wizard's baseline view of a character
    (`frontend/src/types/characterProgression.ts`'s `CharacterProgression`) —
    plain names/keys the wizard steps already expect (the same shape the mock
    `progression_1.json`/`progression_2.json` fixtures used before a real
    character could be leveled), not the sheet's fuller computed/display
    shape (`build_character_sheet`)."""
    race = db.get(BaseRace, character.race_id)

    spells_known: dict[str, list[str]] = {}
    for base_class_id_str, spell_ids in character.spell_ids.items():
        root = db.get(BaseClass, UUID(base_class_id_str))
        if root is None or not spell_ids:
            continue
        spells_known[root.name] = list(db.scalars(select(BaseSpell.name).where(BaseSpell.id.in_(spell_ids))).all())

    favored_membership = next((m for m in character.class_memberships if m.is_favored), None)
    favored_root_id = favored_membership.base_class_id if favored_membership else None

    return {
        "name": character.name,
        "race": race.name if race is not None else "",
        "classes": [
            {
                "id": entry["id"],
                "className": entry["class_name"],
                "level": entry["level"],
                "archetypes": entry["archetypes"],
                "options": entry["options"],
                "isFavored": entry["is_favored"],
            }
            for entry in character.classes
        ],
        "abilityScores": character.ability_scores,
        "feats": [entry["name"] for entry in _build_feats(db, character)],
        "traits": [row["name"] for row in _build_traits(db, character)],
        # Alternate-trait names (not the flex ability-score pick) - needed by
        # the level-up wizard to tell whether a race's skill-point-per-level
        # bonus (e.g. Human's Geschult) was traded away, same "replaces"
        # check creation's own skillPointsTotal does.
        "altTraits": character.alt_traits,
        "useBackgroundSkills": character.use_background_skills,
        "skillRanks": character.skill_ranks,
        # Per-(skill, specialization) breakdown, so the level-up wizard can
        # pre-seed an existing Handwerk/Beruf/Auftreten specialization
        # ("bereits N Ränge") as its own addable-to row instead of collapsing
        # every specialization of a skill into one number the way
        # `skillRanks` above does.
        "skillRankDetails": [
            {
                "skillId": str(entry["skill_id"]),
                "specializationId": str(entry["specialization_id"]) if entry["specialization_id"] else None,
                "customSpecialization": entry["custom_specialization"],
                "ranks": entry["ranks"],
            }
            for entry in character.skill_rank_details
        ],
        "spellsKnown": spells_known,
        "favoredClassBonusOptions": _favored_class_bonus_options(db, favored_root_id, character.race_id),
        "favoredClassBonusDescriptions": _favored_class_bonus_descriptions(db, favored_root_id, character.race_id),
        "favoredClassBonusShortLabels": _favored_class_bonus_short_labels(db, favored_root_id, character.race_id),
        "history": build_character_history(character, db),
    }


def build_character_history(character: Character, db: Session) -> list[dict]:
    """Reconstructs a level-up history log purely from `CharacterLevel` audit
    rows (level 1 is character creation, not a level-up event, so it's
    skipped) — no separate `history` table (roadmap.md slice 7's "thick"
    item); everything here was already written by `routers/characters.py`'s
    level-up endpoint, this just formats it. Shared by
    `build_character_progression`'s `history` field and the standalone
    `GET /api/characters/{id}/history` endpoint (`main.py`)."""
    level_ids = {level.base_class_id for level in character.levels}
    roots_by_id = {root.id: root for root in db.scalars(select(BaseClass).where(BaseClass.id.in_(level_ids))).all()}

    entries = []
    for level in character.levels:
        if level.level == 1:
            continue
        root = roots_by_id.get(level.base_class_id)
        parts = [f"{root.name if root is not None else '?'} Stufe {level.level}"]

        for feat_entry in level.feats:
            feat = db.get(BaseFeat, feat_entry.feat_id)
            if feat is not None:
                parts.append(f"Talent: {feat.name}")
        if level.ability_increase:
            parts.append(f"Attribut +1: {level.ability_increase}")
        skill_names = []
        for entry in level.skill_ranks:
            skill = db.get(BaseSkill, entry.skill_id)
            if skill is None:
                continue
            specialization_label = entry.custom_specialization
            if entry.specialization_id is not None:
                specialization = db.get(BaseSkillSpecialization, entry.specialization_id)
                specialization_label = specialization.name if specialization is not None else None
            skill_names.append(f"{skill.name} ({specialization_label})" if specialization_label else skill.name)
        if skill_names:
            parts.append(f"Fertigkeiten: {', '.join(skill_names)}")
        for spell_entry in level.spells:
            spell = db.get(BaseSpell, spell_entry.spell_id)
            if spell is not None:
                parts.append(f"Neuer Zauber: {spell.name}")

        entries.append(
            {
                "id": str(level.id),
                "date": level.created_at.date().isoformat() if level.created_at else "",
                "description": f"Stufe {level.level - 1} → {level.level}: {' · '.join(parts)}",
            }
        )
    return entries


def _described(db: Session, model: type, ids: list[UUID]) -> list[dict]:
    if not ids:
        return []
    rows = db.scalars(select(model).where(model.id.in_(ids))).all()
    return [
        {"key": str(row.id), "name": row.name, "description": row.description, "hasHandler": has_mechanical_effect(row.id)}
        for row in rows
    ]


def _build_feats(db: Session, character: Character) -> list[dict]:
    """Like `_described`, but one row per `CharacterFeat` pick rather than
    per distinct feat id — an open-choice feat (Waffenfokus, Fertigkeitsfokus,
    Zauberfokus, ...; see `BaseFeat.sub_choice_type`) can legitimately be
    taken more than once for different weapons/skills/schools, so `_described`'s
    dedup-by-id would otherwise collapse those into a single row and drop the
    sub-choice display entirely. The chosen weapon/skill/school is appended
    to the feat's name for display (e.g. "Waffenfokus (Langschwert)") — there's
    no separate structured field for it in the frontend's `Character` type."""
    entries = [entry for level in character.levels for entry in level.feats]
    if not entries:
        return []

    feats_by_id = {
        feat.id: feat
        for feat in db.scalars(select(BaseFeat).where(BaseFeat.id.in_({e.feat_id for e in entries}))).all()
    }
    weapon_ids = {e.chosen_weapon_id for e in entries if e.chosen_weapon_id is not None}
    weapons_by_id = (
        {item.id: item for item in db.scalars(select(BaseItem).where(BaseItem.id.in_(weapon_ids))).all()}
        if weapon_ids
        else {}
    )
    skill_ids = {e.chosen_skill_id for e in entries if e.chosen_skill_id is not None}
    skills_by_id = (
        {skill.id: skill for skill in db.scalars(select(BaseSkill).where(BaseSkill.id.in_(skill_ids))).all()}
        if skill_ids
        else {}
    )

    result = []
    for entry in entries:
        feat = feats_by_id.get(entry.feat_id)
        if feat is None:
            continue
        sub_choice_label = None
        if entry.chosen_weapon_id is not None:
            weapon = weapons_by_id.get(entry.chosen_weapon_id)
            sub_choice_label = weapon.name if weapon is not None else None
        elif entry.chosen_skill_id is not None:
            skill = skills_by_id.get(entry.chosen_skill_id)
            sub_choice_label = skill.name if skill is not None else None
        elif entry.chosen_spell_school is not None:
            sub_choice_label = entry.chosen_spell_school
        name = f"{feat.name} ({sub_choice_label})" if sub_choice_label else feat.name
        result.append(
            {
                "key": str(entry.id),
                "name": name,
                "description": feat.description,
                "hasHandler": has_mechanical_effect(feat.id),
            }
        )
    return result


def _build_traits(db: Session, character: Character) -> list[dict]:
    """Like `_described`, but appends the chosen skill to a trait's name for
    display (e.g. "Gewitztes Wortspiel (Bluffen)") when `CharacterTrait.
    chosen_skill_id` is set — same reasoning and shape as `_build_feats`'s
    own sub-choice label, sized for traits' one sub-choice kind."""
    entries = [entry for level in character.levels for entry in level.traits]
    if not entries:
        return []

    traits_by_id = {
        trait.id: trait
        for trait in db.scalars(select(BaseTrait).where(BaseTrait.id.in_({e.trait_id for e in entries}))).all()
    }
    skill_ids = {e.chosen_skill_id for e in entries if e.chosen_skill_id is not None}
    skills_by_id = (
        {skill.id: skill for skill in db.scalars(select(BaseSkill).where(BaseSkill.id.in_(skill_ids))).all()}
        if skill_ids
        else {}
    )

    result = []
    for entry in entries:
        trait = traits_by_id.get(entry.trait_id)
        if trait is None:
            continue
        skill = skills_by_id.get(entry.chosen_skill_id) if entry.chosen_skill_id is not None else None
        name = f"{trait.name} ({skill.name})" if skill is not None else trait.name
        # "key" stays the trait's own id (unlike `_build_feats`'s per-pick
        # `CharacterFeat.id`) — a trait can never be taken twice, so there's
        # no ambiguity forcing a per-instance key, and `BaseTrait.id` is what
        # every existing caller (`test_character_sheet.py`'s
        # `{t["key"] for t in body["traits"]} == {trait_id}`,
        # `buildSearchIndex.ts`) already expects.
        result.append(
            {
                "key": str(trait.id),
                "name": name,
                "description": trait.description,
                "hasHandler": has_mechanical_effect(trait.id),
            }
        )
    return result


def _ac_breakdown(
    capped_dex_mod: int, groups: dict[tuple[ModifierTarget, str | None], list[Modifier]]
) -> list[dict]:
    """Ordered `{label, value}` line items that sum to `armor_class` exactly
    (`10 + capped_dex_mod + stacked.get((AC, None), 0)`) — the frontend's
    value-origin tooltip. Only the `contributing()`-filtered survivors of the
    AC group are listed (`rules/modifiers.py`'s `contributing` docstring):
    PF1e's same-type-doesn't-stack rule means a suppressed same-type
    modifier never actually counted toward `armor_class`, so listing it here
    too would make the breakdown sum to more than the displayed total."""
    entries = [
        {"label": "Basis", "value": 10},
        {"label": "Geschicklichkeit", "value": capped_dex_mod},
    ]
    entries.extend(
        {"label": modifier.source, "value": modifier.value}
        for modifier in contributing(groups.get((ModifierTarget.AC, None), []))
    )
    return entries


def _ac_breakdown_flat_footed(groups: dict[tuple[ModifierTarget, str | None], list[Modifier]]) -> list[dict]:
    """Same shape as `_ac_breakdown`, for the RK a character has while
    denied their Dexterity bonus to AC ("auf dem falschen Fuß") — PF1e RAW
    drops both the Dex bonus and any dodge-type bonus in that case (e.g.
    Ausweichen, or a future Gewitzte-Verteidigung handler), so unlike
    `_ac_breakdown` there is no "Geschicklichkeit" line at all, and
    `type == "dodge"` modifiers are excluded before `contributing()` picks
    the survivors. Sums to `armor_class_flat_footed` exactly, same
    `contributing()`-only-lists-what-counted reasoning as `_ac_breakdown`."""
    non_dodge = [m for m in groups.get((ModifierTarget.AC, None), []) if m.type != "dodge"]
    entries = [{"label": "Basis", "value": 10}]
    entries.extend({"label": modifier.source, "value": modifier.value} for modifier in contributing(non_dodge))
    return entries


def _build_skills(
    db: Session,
    character: Character,
    level_counts_by_root_id: dict[UUID, int],
    ability_mods: dict[str, int],
    total_speed: int,
    stacked: dict[tuple[ModifierTarget, str | None], int],
    groups: dict[tuple[ModifierTarget, str | None], list[Modifier]],
    context: CharacterContext,
) -> list[dict]:
    # Per-(skill, specialization) ranks, grouped by base skill id — a
    # `has_specialization` skill (Handwerk/Beruf/Auftreten) fans out into one
    # row per specialization the character actually has; every other skill
    # still gets at most one row, same as before.
    ranks_by_skill: dict[UUID, list[dict]] = defaultdict(list)
    for entry in character.skill_rank_details:
        if entry["ranks"] > 0:
            ranks_by_skill[entry["skill_id"]].append(entry)

    specialization_ids = {
        entry["specialization_id"]
        for rows in ranks_by_skill.values()
        for entry in rows
        if entry["specialization_id"] is not None
    }
    specialization_names = {
        row.id: row.name
        for row in db.scalars(
            select(BaseSkillSpecialization).where(BaseSkillSpecialization.id.in_(specialization_ids))
        ).all()
    }

    # Every situational (never-folded-into-`value`) skill bonus this
    # character currently has, grouped by which skill it targets — scopes 1
    # (granted class ability) and 2 (feat) resolved generically via
    # `rules/handlers.py`'s `SITUATIONAL_SKILL_HANDLERS`, scope 3
    # (universal — currently just the jump bonus) called directly since it
    # has no id to look up (see that module's docstring for the full model).
    # Computed once, up front, rather than each skill row re-deriving it.
    notes_by_skill: dict[UUID, list[SkillNote]] = defaultdict(list)
    for note in [jump_skill_note(total_speed), *situational_skill_notes(context)]:
        notes_by_skill[note.skill_id].append(note)

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

    def _skill_entry(skill: BaseSkill, ranks: int, label: str, key: str) -> dict:
        ab_mod = ability_mods.get(skill.ability, 0)
        # PF1e RAW: the +3 class-skill bonus only applies once at least 1 rank
        # is invested — a class skill with 0 ranks is still untrained/no
        # better than a cross-class skill.
        class_bonus = 3 if ranks and skill.id in class_skill_ids else 0
        # Unconditional feat/race/class-ability skill bonuses (e.g.
        # Einschüchternde Kraft's ST modifier on Einschüchtern,
        # `rules/feats.py`; Halb-Ork's Einschüchternd, `race_skill_modifiers`
        # above) — 0 for every skill without such a handler, same "wired
        # ahead of the first producer" convention `ModifierTarget.SKILL` was
        # declared under. Keyed by the base skill id, not this row's specific
        # specialization — no handler targets one specialization yet (see
        # roadmap.md's deferred follow-up for the Wilder Seemann note below).
        handler_bonus = stacked.get((ModifierTarget.SKILL, str(skill.id)), 0)
        base_value = ranks + ab_mod + class_bonus + handler_bonus
        entry = {"key": key, "label": label, "value": _fmt(base_value)}
        # Value-origin tooltip: only the fixed components that actually
        # contributed (0-value ones dropped — a skill row is shown for every
        # untrained/non-class skill too, so most rows would otherwise carry
        # 2-3 always-zero lines) plus every `contributing()`-surviving
        # handler `Modifier` for this skill (feat/race bonuses, e.g.
        # Einschüchternde Kraft/Halb-Orks Einschüchternd). Sums to
        # `base_value` exactly, same reasoning as `_ac_breakdown`. Deliberately
        # excludes `notes_by_skill` (Wilder Seemann/jump) — those are
        # situational and never folded into `base_value` in the first place.
        breakdown = []
        if ranks:
            breakdown.append({"label": "Ränge", "value": ranks})
        if ab_mod:
            breakdown.append({"label": f"Attributsbonus ({ABILITY_LABELS[skill.ability]})", "value": ab_mod})
        if class_bonus:
            breakdown.append({"label": "Klassenfertigkeit", "value": class_bonus})
        breakdown.extend(
            {"label": modifier.source, "value": modifier.value}
            for modifier in contributing(groups.get((ModifierTarget.SKILL, str(skill.id)), []))
        )
        if breakdown:
            entry["breakdown"] = breakdown
        # The note shows the full ready-to-roll total (this skill's base
        # value + the situational bonus), not just the isolated bonus — a
        # player wants one usable number, not a formula piece to add up
        # themselves. Carried over onto every specialization row of a
        # `has_specialization` skill (e.g. every Beruf specialization the
        # character has gets the Wilder Seemann note, not just "Beruf
        # (Seemann)" specifically) — same imprecision `notes_by_skill`
        # already had before specializations existed, since no handler
        # targets one specific specialization yet.
        notes = [
            f"{note.title}: {_fmt(base_value + note.value)} gesamt "
            f"({label} {_fmt(base_value)} + {note.modifier_label} {_fmt(note.value)}{note.detail})"
            for note in notes_by_skill.get(skill.id, [])
        ]
        if notes:
            entry["note"] = "; ".join(notes)
        return entry

    result = []
    for skill in db.scalars(select(BaseSkill).order_by(BaseSkill.name)).all():
        if skill.has_specialization:
            # No generic/"ungeübt" fallback row — a Handwerk/Beruf/Auftreten
            # row only exists once a specialization has been picked and has
            # at least 1 rank.
            for row in ranks_by_skill.get(skill.id, []):
                specialization_label = (
                    specialization_names.get(row["specialization_id"])
                    if row["specialization_id"] is not None
                    else row["custom_specialization"]
                )
                # Ranks recorded before this feature existed have neither
                # field set — show them plainly (no dangling "(None)") rather
                # than losing the character's invested ranks off the sheet.
                label = f"{skill.name} ({specialization_label})" if specialization_label else skill.name
                key = f"{skill.id}#{row['specialization_id'] or row['custom_specialization'] or ''}"
                result.append(_skill_entry(skill, row["ranks"], label, key))
        else:
            # Every skill usable untrained belongs on the sheet even at 0
            # ranks (PF1e core's "Trained Only" column,
            # `BaseSkill.trained_only`) — a trained-only skill only shows up
            # once ranks are actually invested.
            rows = ranks_by_skill.get(skill.id, [])
            ranks = rows[0]["ranks"] if rows else 0
            if skill.trained_only and not ranks:
                continue
            result.append(_skill_entry(skill, ranks, skill.name, str(skill.id)))
    return result


def granted_class_ability_ids(
    db: Session, character: Character, level_counts_by_root_id: dict[UUID, int]
) -> Counter[UUID]:
    """Which `BaseClassAbility` ids this character actually has, resolved
    against their level count/archetype/option picks — shared by
    `_build_class_features` (display, only cares which ids are present) and
    `rules/speed.py`'s class-granted speed bonus (computation), so the two
    can never drift on what counts as "granted".

    A `Counter`, not a `set`: some abilities are one `BaseClassAbility` row
    with several level-gated `BaseClassAbilityGrant`s — a single feature
    whose description covers its own scaling in prose (e.g. Barbar's
    Schadensreduzierung, granted again at 10./13./16./19. Stufe to say "+1
    each time"), but occasionally a genuinely repeating flat bonus instead
    (e.g. Mönch's Schnelligkeit, +3 m at 3./6./9./12./15./18. Stufe, each
    repetition really is another +3 m). A plain set can't tell those apart;
    the count can — `_build_class_features` still just needs presence
    (`list(counter)`), but a speed-bonus handler keyed by ability id can
    multiply its per-grant value by how many of that ability's grants are
    currently met, so a repeating class feature is only computed once
    (here) rather than every consumer re-deriving it."""
    if not level_counts_by_root_id:
        return Counter()

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

    ability_counts: Counter[UUID] = Counter()
    for grant in grants:
        if grant.id in replaced_grant_ids:
            continue
        if grant.level > level_counts_by_root_id[root_id_by_class_id[grant.base_class_id]]:
            continue
        if grant.option_choice_id is not None and grant.option_choice_id not in chosen_option_ids:
            continue
        ability_counts[grant.ability_id] += 1

    return ability_counts


def _build_class_features(db: Session, granted_ability_ids: Counter[UUID]) -> list[dict]:
    return _described(db, BaseClassAbility, list(granted_ability_ids))


def _build_race_abilities(db: Session, race_ability_ids: set[UUID]) -> list[dict]:
    """`race_ability_ids` is `build_character_sheet`'s own
    `effective_race_ability_ids(...)` result — the character's *actual*
    trait set (base grants minus whichever a chosen alternate swapped away,
    plus the chosen alternates themselves), not every base grant
    unconditionally. Fixes a pre-existing gap: this used to query
    `RaceAbilityGrant` directly by `race_id` alone, so a chosen alt-trait
    (e.g. Halb-Ork's Reißzähne) never showed here and the trait it replaced
    (Orkische Wildheit) incorrectly still did."""
    return _described(db, BaseRaceAbility, list(race_ability_ids))


def _favored_class_bonus_options(db: Session, favored_root_id: UUID | None, race_id: UUID) -> list[str]:
    """Which values are currently legal for `LevelUp.favored_class_bonus`
    for this character's one favored class — "hp"/"skill" (the two stable
    literals every class offers) plus this class's own race-scoped
    alternates (`favored_class_bonus_race_choices`, shared with
    `routers/characters.py`'s creation-time validation). The level-up wizard
    renders this list directly — no client-side race filtering needed, same
    reasoning `race_skill_modifiers`'s docstring gives for keeping
    composition-vs-character-scoped filtering server-side."""
    choices = favored_class_bonus_race_choices(db, favored_root_id, race_id)
    return ["hp", "skill", *(choice.name for choice in choices)]


def _favored_class_bonus_descriptions(db: Session, favored_root_id: UUID | None, race_id: UUID) -> dict[str, str]:
    """Choice name -> full rules text, for this class's own race-scoped
    favored-class-bonus alternates only ("hp"/"skill" excluded — the
    level-up wizard already has fixed, friendly text for those two). Lets
    the wizard's summary step ("Zusammenfassung", 2026-08-16 — a player
    picking e.g. "Halb-Ork (Barbar)" saw no indication anywhere of what that
    choice actually does) show the real rules text instead of just the bare
    catalog name."""
    choices = favored_class_bonus_race_choices(db, favored_root_id, race_id)
    descriptions_by_choice_id = _ability_descriptions_by_choice_id(db, [choice.id for choice in choices])
    return {choice.name: descriptions_by_choice_id.get(choice.id, "") for choice in choices}


def _favored_class_bonus_short_labels(db: Session, favored_root_id: UUID | None, race_id: UUID) -> dict[str, str]:
    """Choice name -> short, button-sized label (`rules/favored_class_bonuses.py`'s
    `SHORT_LABELS`, e.g. "+1 Rd. Kampfrausch/Tag") for this class's own
    race-scoped alternates — the level-up wizard's picker chips show this
    instead of the bare catalog name, so a player doesn't need to hover to
    understand what a chip does (2026-08-16). Falls back to the catalog name
    itself for a choice with no short label yet, so a future race's
    alternates still render *something* before this dict is filled in for
    them."""
    choices = favored_class_bonus_race_choices(db, favored_root_id, race_id)
    return {choice.name: FAVORED_CLASS_BONUS_SHORT_LABELS.get(choice.id, choice.name) for choice in choices}


def build_favored_class_bonus_options(db: Session, base_class_id: UUID, race_id: UUID) -> dict:
    """Public entry point for `GET /api/favored-class-bonus-options` — the
    creation wizard's equivalent of `build_character_progression`'s
    `favoredClassBonusOptions`/`favoredClassBonusShortLabels`, keyed by an
    explicit base_class_id + race_id instead of an existing `Character` row,
    since creation has neither yet. Lets `ClassStep.tsx` offer the very same
    hp/skill/race-scoped-alternate picker `HitPointsStep.tsx` already uses
    at level-up, for the character's 1st-level favored-class bonus."""
    return {
        "options": _favored_class_bonus_options(db, base_class_id, race_id),
        "shortLabels": _favored_class_bonus_short_labels(db, base_class_id, race_id),
    }


def _ability_descriptions_by_choice_id(db: Session, choice_ids: list[UUID]) -> dict[UUID, str]:
    """A `BaseClassOptionChoice.id` -> its matching `BaseClassAbility`'s
    description text, via the `BaseClassAbilityGrant(option_choice_id=...)`
    link every option-group choice's description goes through (choices have
    no description column of their own, see `BaseClassOptionChoice`'s
    docstring). A choice with no matching grant is simply absent from the
    result."""
    if not choice_ids:
        return {}
    grants = db.scalars(
        select(BaseClassAbilityGrant).where(BaseClassAbilityGrant.option_choice_id.in_(choice_ids))
    ).all()
    ability_id_by_choice_id = {grant.option_choice_id: grant.ability_id for grant in grants}
    abilities = {
        ability.id: ability
        for ability in db.scalars(
            select(BaseClassAbility).where(BaseClassAbility.id.in_(ability_id_by_choice_id.values()))
        ).all()
    }
    return {
        choice_id: abilities[ability_id].description
        for choice_id, ability_id in ability_id_by_choice_id.items()
        if ability_id in abilities
    }


def _build_favored_class_bonuses(db: Session, character: Character) -> list[dict]:
    """Accumulated read-out for every race-scoped favored-class-bonus choice
    this character has ever picked (any favored class over their career,
    not just the current one) — mirrors `rules/progression.py`'s
    `max_hit_points`: `CharacterClassOption` rows are the one raw value per
    level, summed/derived here at read time, nothing pre-aggregated stored.
    "hp"/"skill" picks never appear here — they're not `BaseClassOptionChoice`
    rows at all (folded directly into `armorClass`.../HP/skill ranks
    already), so there's nothing extra to surface for them."""
    pick_counts = favored_class_bonus_pick_counts(character)
    if not pick_counts:
        return []

    choices = {
        choice.id: choice
        for choice in db.scalars(
            select(BaseClassOptionChoice).where(BaseClassOptionChoice.id.in_(pick_counts))
        ).all()
    }
    descriptions_by_choice_id = _ability_descriptions_by_choice_id(db, list(pick_counts))

    result = []
    for choice_id, count in pick_counts.items():
        choice = choices.get(choice_id)
        if choice is None:
            continue
        handler = FAVORED_CLASS_BONUS_HANDLERS.get(choice_id)
        result.append(
            {
                "key": str(choice_id),
                "name": choice.name,
                "description": descriptions_by_choice_id.get(choice_id, ""),
                "pickCount": count,
                # Absent handler (e.g. Mönch's two-effects-per-pick, Mystiker's
                # "+1 known spell") means there's no single accumulating
                # number - the description is the whole answer, see
                # `rules/favored_class_bonuses.py`'s own docstring.
                "currentBonus": handler(count) if handler is not None else None,
                "hasHandler": handler is not None,
            }
        )
    return result


def _build_concentration(
    db: Session,
    level_counts_by_root_id: dict[UUID, int],
    ability_mods: dict[str, int],
    stacked: dict[tuple[ModifierTarget, str | None], int],
) -> list[dict]:
    """PF1e's Konzentrationswurf (GRW S. 156): 1W20 + Zaubererstufe +
    Fähigkeitsmodifikator der Zauberklasse + jeder unbedingte
    `ModifierTarget.CONCENTRATION`-Bonus (e.g. Fokussierter Verstand's flat
    +2 trait bonus, `rules/traits.py`) — one `combat` entry per casting root
    class the character actually has levels in (`BaseClass.
    effective_casting_ability` set, the same field `_build_prepared_spell_grades`'s
    `casting_mod` already reads), so a multiclassed dual-caster (e.g. Magier/
    Kleriker) gets one labeled value per class instead of one conflated
    number — labels stay plain "Konzentration" for the overwhelmingly common
    single-caster-class case, only gaining a "(Klassenname)" suffix once
    there's more than one entry to tell apart. Applies to every casting
    class regardless of `spellType` (arcane-prepared/divine-prepared/
    spontaneous) — unlike `_build_prepared_spell_grades`, which only builds
    spellbook/known-spell display for prepared casters, a Konzentrationswurf
    applies identically to a spontaneous caster (Barde/Hexenmeister/
    Mystiker) too, and `casting_ability` alone already answers "is this
    class a caster at all" without needing that distinction.

    Caster level is simply that class's own `CharacterLevel` count — no
    class in this codebase's data reduces caster level itself (only spell
    slots, e.g. Kampfmagus's Kensai, `rules/classes/kampfmagus.py`), so class
    level doubles as caster level here, the same assumption
    `total_spell_slots` already makes. `stacked` (already folded/type-capped
    by `build_character_sheet`'s one shared `character_modifiers`/`stack()`
    pass, same source `saves`/`cmb` read their own targets from) is the
    *only* input for any bonus on top of that base — no separate lookup
    here, per CLAUDE.md's composition/computation split: a trait/feat with
    an unconditional bonus is a completely ordinary `HANDLERS` entry
    targeting `ModifierTarget.CONCENTRATION`, nothing about "concentration"
    as a stat needs its own special-cased pipeline.

    Doesn't fold in the *situational* Konzentration bonuses seeded as
    flavor text so far (Zäher Zauberer's defensive-cast +4, Arkane
    Konzentration's underwater +2, ...) — each only applies under one
    specific circumstance this sheet has no way to detect, the same "no
    trigger to hang a flat number on" reasoning `rules/handlers.py`'s
    `SITUATIONAL_SKILL_HANDLERS` docstring gives for Wilder Seemann — so
    they stay text-only on their own feat/trait entry rather than being
    silently baked into a number that would overstate every ordinary
    (non-defensive, non-underwater) cast. That's a genuine conditional-
    trigger problem, not a reason to bypass `HANDLERS`/`Modifier` in
    general — Fokussierter Verstand above needs none of that."""
    roots = []
    for base_class_id, class_level in level_counts_by_root_id.items():
        root = db.get(BaseClass, base_class_id)
        if root is not None and root.effective_casting_ability is not None:
            roots.append((root, class_level))
    bonus = stacked.get((ModifierTarget.CONCENTRATION, None), 0)
    return [
        {
            "key": f"concentration-{root.id}",
            "label": f"Konzentration ({root.name})" if len(roots) > 1 else "Konzentration",
            "value": _fmt(class_level + ability_mods.get(root.effective_casting_ability, 0) + bonus),
        }
        for root, class_level in roots
    ]


def _build_prepared_spell_grades(
    db: Session,
    character: Character,
    level_counts_by_root_id: dict[UUID, int],
    ability_mods: dict[str, int],
    granted_ability_ids: Counter[UUID],
) -> tuple[list[dict], list[dict]]:
    """Real prepared-spellcasting state (roadmap slice 6) for every arcane-
    or divine-prepared class the character has — replaces the old
    `_build_spell_grades` placeholder (both `used`/`prepared` hardcoded
    `False`, no persistence, no slot cap, and silently skipped divine-
    prepared classes entirely). Returns `(spellbook, spellsKnown)`:
    `spellbook` is the full candidate list per grade (arcane-prepared: the
    character's known spellbook, `CharacterSpell`; divine-prepared: the
    class's whole spell list, `BaseClassSpell`, at accessible grades — no
    spellbook, `requirements_v2.md` §2.2) with real `preparedCount`/
    `usedCount` per spell, driving the "Zauberbuch" prepare UI; `spellsKnown`
    is the same grades with `spells` filtered to `preparedCount > 0`,
    driving the "Zauber" cast bar — one query pass feeds both. `perDay`
    already reflects any archetype spell-slot reduction the character has
    granted (e.g. Kampfmagus's Kensai, `rules/classes/kampfmagus.py`), via
    `granted_ability_ids` -> `total_spell_slots`.

    Locked (not-yet-accessible) grades are still included in `spellbook`
    (`locked: True`, `availableAtLevel` the earliest future level a
    `base_class_spells_known` row exists for that grade) so the prepare UI
    can show what's coming, same shape the mock fixtures always used.

    Doesn't merge across multiple simultaneously-prepared-caster classes on
    the same character (a real but rare multiclass shape, e.g. Magier/
    Kleriker) — each class's grades are appended independently, so two
    classes sharing a grade number produce two separate entries rather than
    one merged/conflicting `perDay`. Good enough for every single-
    prepared-caster character this app has seeded so far; revisit if a real
    dual-prepared-caster character needs it."""
    spellbook: list[dict] = []

    for base_class_id, class_level in level_counts_by_root_id.items():
        root = db.get(BaseClass, base_class_id)
        if root is None:
            continue
        class_def = _class_def(root.name) or {}
        spell_type = class_def.get("spellType")
        if spell_type not in ("arcane-prepared", "divine-prepared"):
            continue

        class_spell_rows = db.scalars(select(BaseClassSpell).where(BaseClassSpell.base_class_id == root.id)).all()
        grade_by_spell_id = {row.spell_id: row.grade for row in class_spell_rows}
        all_grades = sorted({row.grade for row in class_spell_rows})
        accessible_grades = known_grades(db, root.id, class_level)

        if spell_type == "arcane-prepared":
            candidate_ids = character.spell_ids.get(str(root.id), [])
        else:
            candidate_ids = [row.spell_id for row in class_spell_rows if row.grade in accessible_grades]
        spells_by_id = {
            spell.id: spell for spell in db.scalars(select(BaseSpell).where(BaseSpell.id.in_(candidate_ids))).all()
        }
        prep_by_spell_id = {
            row.spell_id: row for row in character.spell_preparations if row.base_class_id == root.id
        }
        components_by_spell_id = (
            {
                row.spell_id: row
                for row in db.scalars(
                    select(BaseSpellComponent).where(
                        BaseSpellComponent.spell_id.in_(candidate_ids),
                        BaseSpellComponent.tradition == root.effective_spell_tradition,
                    )
                ).all()
            }
            if candidate_ids
            else {}
        )

        by_grade: dict[int, list[dict]] = defaultdict(list)
        for spell_id in candidate_ids:
            spell = spells_by_id.get(spell_id)
            if spell is None:
                continue
            grade = grade_by_spell_id.get(spell_id, 0)
            prep = prep_by_spell_id.get(spell_id)
            by_grade[grade].append(
                {
                    "key": str(spell_id),
                    "name": spell.name,
                    "baseClassId": str(root.id),
                    "preparedCount": prep.prepared_count if prep is not None else 0,
                    "usedCount": prep.used_count if prep is not None else 0,
                    "description": spell.description,
                    "components": _format_spell_components(components_by_spell_id.get(spell_id)),
                }
            )

        unlock_level_by_grade: dict[int, int] = {}
        for row in db.scalars(
            select(BaseClassSpellsKnown).where(
                BaseClassSpellsKnown.base_class_id == root.id, BaseClassSpellsKnown.grade.in_(all_grades)
            )
        ).all():
            current = unlock_level_by_grade.get(row.grade)
            if current is None or row.level < current:
                unlock_level_by_grade[row.grade] = row.level

        casting_mod = ability_mods.get(root.effective_casting_ability or "", 0)
        # Highest grade currently *accessible* (not the class's theoretical
        # max) — any ability-modifier bonus spell for a higher, still-locked
        # grade folds down into this one instead of being discarded (house
        # rule, `rules/spells.py`'s `folded_bonus_spells`).
        max_accessible_grade = max((g for g in accessible_grades if g >= 1), default=None)
        for grade in all_grades:
            locked = grade not in accessible_grades
            spells = sorted(by_grade.get(grade, []), key=lambda s: s["name"])
            grade_entry: dict = {"grade": grade, "locked": locked, "spells": spells}
            if locked:
                grade_entry["availableAtLevel"] = unlock_level_by_grade.get(grade)
            else:
                grade_entry["perDay"] = total_spell_slots(
                    db,
                    root.id,
                    class_level,
                    grade,
                    casting_mod,
                    granted_ability_ids,
                    fold_higher_grades_into_this_one=(grade == max_accessible_grade),
                )
            spellbook.append(grade_entry)

    spellbook.sort(key=lambda g: g["grade"])
    spells_known = []
    for grade_entry in spellbook:
        if grade_entry["locked"]:
            continue
        prepared_spells = [s for s in grade_entry["spells"] if s["preparedCount"] > 0]
        if prepared_spells:
            spells_known.append({**grade_entry, "spells": prepared_spells})
    return spellbook, spells_known


def _format_spell_components(component: BaseSpellComponent | None) -> str:
    """"V, S, M (Fledermausguano und Schwefel)"-style display string for the
    cast-confirmation popup — pre-formatted here rather than left to the
    frontend since it's a fixed, small set of flags plus optional
    descriptive text, the same "format for display in sheet.py" convention
    every other stat-block-shaped field on this sheet already follows (e.g.
    `_fmt`'s +/- signs). `None` (no `BaseSpellComponent` row for this
    spell/tradition — not every PRD spell page restates its own component
    line) renders as an explicit "—" rather than an empty string, so the
    popup can't be mistaken for "no components" vs. "not seeded"."""
    if component is None:
        return "—"
    parts = []
    if component.verbal:
        parts.append("V")
    if component.somatic:
        parts.append("S")
    if component.material:
        parts.append(f"M ({component.material_description})" if component.material_description else "M")
    if component.focus:
        parts.append(f"F ({component.focus_description})" if component.focus_description else "F")
    return ", ".join(parts) if parts else "—"


def _build_activatable_spells(db: Session, character: Character) -> list[dict]:
    """Known spells flagged `is_persistent_effect` (roadmap slice 5) — the
    subset a player can activate as a tracked `CharacterEffect` via
    `POST .../effects`. Kept separate from `spellsKnown`/`spellbook` (cast/
    prepare tracking, an unrelated concern) rather than adding a field to
    those existing shapes. Self-only by nature (`range` "Persönlich") is the
    typical shape here; a non-"Persönlich" spell the character themselves
    also knows still legitimately belongs in this list too (nothing stops a
    caster targeting themselves with their own Berührung spell) — see
    `_build_external_spells` for the counterpart that isn't gated by
    ownership at all."""
    all_spell_ids = {spell_id for ids in character.spell_ids.values() for spell_id in ids}
    if not all_spell_ids:
        return []
    spells = db.scalars(
        select(BaseSpell).where(BaseSpell.id.in_(all_spell_ids), BaseSpell.is_persistent_effect.is_(True))
    ).all()
    return [{"key": str(spell.id), "name": spell.name} for spell in spells]


def _build_activatable_feats(db: Session, character: Character) -> list[dict]:
    """Known feats flagged `is_persistent_effect` (2026-08-16, same idea as
    `_build_activatable_spells`/`_build_activatable_class_abilities`) — the
    subset a player can activate as a tracked `CharacterEffect` via
    `POST .../effects` (e.g. Heftiger Angriff). `defaultDurationRounds`
    pre-fills the frontend's activation-form duration field from
    `BaseFeat.default_duration_rounds`, same role `ConditionCatalogEntry`'s
    own default fields play for conditions/poisons/diseases — the player can
    still override it."""
    feat_ids = set(character.feat_ids)
    if not feat_ids:
        return []
    feats = db.scalars(
        select(BaseFeat).where(BaseFeat.id.in_(feat_ids), BaseFeat.is_persistent_effect.is_(True))
    ).all()
    return [
        {"key": str(feat.id), "name": feat.name, "defaultDurationRounds": feat.default_duration_rounds}
        for feat in feats
    ]


def _build_activatable_class_abilities(
    db: Session, character: Character, context: CharacterContext, granted_ability_ids: Counter[UUID]
) -> list[dict]:
    """Granted class abilities flagged `is_persistent_effect` — same idea as
    `_build_activatable_spells`, kept separate from `classFeatures` (display
    only) for the same reason. Filtered to `activation_scope` `"self"`/`"both"`
    (`BaseClassAbility`'s docstring) — an `"external"`-only ability like
    Barde's Lied des Erfolgs explicitly can't target its own owner, so it has
    no business in this character's own activation list even though they
    have it granted; see `_build_external_class_abilities` for that half.

    For an ability registered in `rules/handlers.py`'s `DAILY_LIMITS` (e.g.
    Kampfrausch), `description` carries the remaining-today count
    (`rules/daily_limits.py`'s `remaining_today`) — reuses
    `AvailableEntry.description`, already rendered as a tooltip in
    `RealEffectsPanel.tsx`, rather than adding a dedicated field for what's
    still only ever one ability."""
    if not granted_ability_ids:
        return []
    abilities = db.scalars(
        select(BaseClassAbility).where(
            BaseClassAbility.id.in_(list(granted_ability_ids)),
            BaseClassAbility.is_persistent_effect.is_(True),
            BaseClassAbility.activation_scope.in_(["self", "both"]),
        )
    ).all()
    results = []
    for ability in abilities:
        remaining = remaining_today(db, character, context, ability.id)
        description = None
        if remaining is not None:
            total = DAILY_LIMITS[ability.id](context)
            unit = DAILY_LIMIT_UNIT_LABEL.get(ability.id, "Runden")
            description = f"{max(0, remaining)} von {total} {unit} heute übrig"
        results.append(
            {
                "key": str(ability.id),
                "name": ability.name,
                "description": description,
                "defaultDurationRounds": ability.default_duration_rounds,
            }
        )
    return results


def _build_actions(
    db: Session, character: Character, granted_ability_ids: Counter[UUID], gear: list[dict], context: CharacterContext
) -> list[dict]:
    """Aktionen panel (roadmap slice 6, thin cut) — only the subset of
    already-activatable data this character has: persistent-effect spells
    known, persistent-effect class abilities granted (self/both scope only —
    `externalClassAbilities` represents what *other* characters can receive
    from this one, not this character's own action), persistent-effect feats
    (2026-08-16, e.g. Heftiger Angriff), discrete once-a-day class abilities
    with no duration to track (2026-08-20, e.g. Erneuerte Lebenskraft — see
    below), and activatable gear. No action-cost data exists anywhere in the
    schema, so `tag` is always `None` rather than a guessed value; no
    usable-now/legality filtering either (a thick-pass follow-up) — every
    activatable-flagged entry is listed, with remaining charges/uses folded
    honestly into its description text instead of hidden.

    `sourceType`/`sourceId` (and, for gear, `gearActionKind`) let the
    frontend route a click without re-deriving what an entry is: spell/
    class_ability/feat entries feed the same `POST .../effects` activation
    flow the Effekte panel's own picker already uses (same `sourceType`/
    `sourceId` shape as `EffectActivate`; a feat entry's `defaultDurationRounds`
    additionally pre-fills that flow's duration field, same as
    `_build_activatable_feats`); gear entries route to `PATCH .../gear/{id}/use`
    or `/toggle` depending on `gearActionKind`, decided once here rather than
    re-derived per click — `"use"` whenever the item has any consumable
    uses/charges (even if it's also toggleable, e.g. a wand), `"toggle"` only
    for a pure on/off item."""
    actions: list[dict] = []

    all_spell_ids = {spell_id for ids in character.spell_ids.values() for spell_id in ids}
    if all_spell_ids:
        spells = db.scalars(
            select(BaseSpell).where(BaseSpell.id.in_(all_spell_ids), BaseSpell.is_persistent_effect.is_(True))
        ).all()
        actions += [
            {
                "id": f"spell-{spell.id}",
                "icon": "✨",
                "name": spell.name,
                "tag": None,
                "description": spell.description,
                "sourceType": "spell",
                "sourceId": str(spell.id),
            }
            for spell in spells
        ]

    if granted_ability_ids:
        abilities = db.scalars(
            select(BaseClassAbility).where(
                BaseClassAbility.id.in_(list(granted_ability_ids)),
                BaseClassAbility.is_persistent_effect.is_(True),
                BaseClassAbility.activation_scope.in_(["self", "both"]),
            )
        ).all()
        # `requires_active_ability_id` (e.g. a Kampfrauschkraft only usable while
        # Kampfrausch is active) hides the action entirely rather than showing it
        # disabled — same reasoning as the daily-limited block below.
        abilities = [
            a for a in abilities if a.requires_active_ability_id is None or context.has_active(a.requires_active_ability_id)
        ]
        for ability in abilities:
            # `dailyLimitRemaining`/`dailyLimitTotal` (not `usesRemainingToday`/`usesPerDay`
            # below — that pair also tells `CharacterSheetPage.tsx`'s `handleActionClick` to
            # route the click through the simple "/use" endpoint instead of opening the full
            # activation modal, which would be wrong here: an ability in *this* block still
            # needs the modal to set a duration/target item, e.g. Kampfrausch, Arkaner Vorrat).
            # Same numbers `_build_active_effects`/`_build_activatable_class_abilities` already
            # expose for this ability, just also surfaced on its Aktionen-panel card.
            remaining = remaining_today(db, character, context, ability.id)
            actions.append(
                {
                    "id": f"ability-{ability.id}",
                    "icon": "⚔️",
                    "name": ability.name,
                    "tag": None,
                    "description": ability.description,
                    "sourceType": "class_ability",
                    "sourceId": str(ability.id),
                    "defaultDurationRounds": ability.default_duration_rounds,
                    "dailyLimitRemaining": max(0, remaining) if remaining is not None else None,
                    "dailyLimitTotal": DAILY_LIMITS[ability.id](context) if remaining is not None else None,
                }
            )

    feat_ids = set(character.feat_ids)
    if feat_ids:
        feats = db.scalars(
            select(BaseFeat).where(BaseFeat.id.in_(feat_ids), BaseFeat.is_persistent_effect.is_(True))
        ).all()
        actions += [
            {
                "id": f"feat-{feat.id}",
                "icon": "🎯",
                "name": feat.name,
                "tag": None,
                "description": feat.description,
                "sourceType": "feat",
                "sourceId": str(feat.id),
                "defaultDurationRounds": feat.default_duration_rounds,
            }
            for feat in feats
        ]

    # Discrete once-a-day class abilities with no duration to track as a `CharacterEffect`
    # (`ERNEUERTE_LEBENSKRAFT_ABILITY_ID`'s docstring) — a granted ability id registered in
    # `DAILY_LIMITS` but *not* flagged `is_persistent_effect` (that flag already covers Kampfrausch
    # above). `usesRemainingToday`/`usesPerDay` mirror the gear loop's own fields below so the
    # frontend can disable the card the same way once the daily use is spent, resetting with
    # everything else in `DAILY_LIMITS` on the next `advance-time`/`rest` call.
    daily_limited_granted_ids = [ability_id for ability_id in granted_ability_ids if ability_id in DAILY_LIMITS]
    if daily_limited_granted_ids:
        instant_abilities = db.scalars(
            select(BaseClassAbility).where(
                BaseClassAbility.id.in_(daily_limited_granted_ids),
                BaseClassAbility.is_persistent_effect.is_(False),
            )
        ).all()
        # Same `requires_active_ability_id` gate as the persistent-effect block above —
        # e.g. Erneuerte Lebenskraft only appears while Kampfrausch is active.
        instant_abilities = [
            a
            for a in instant_abilities
            if a.requires_active_ability_id is None or context.has_active(a.requires_active_ability_id)
        ]
        actions += [
            {
                "id": f"ability-use-{ability.id}",
                "icon": "⚔️",
                "name": ability.name,
                "tag": None,
                "description": ability.description,
                "sourceType": "class_ability",
                "sourceId": str(ability.id),
                "usesRemainingToday": max(0, remaining_today(db, character, context, ability.id) or 0),
                "usesPerDay": DAILY_LIMITS[ability.id](context),
            }
            for ability in instant_abilities
        ]

    for entry in gear:
        if entry.get("activation") != "activatable":
            continue
        description = entry["name"]
        if "usesRemainingToday" in entry:
            description += f" ({entry['usesRemainingToday']}/{entry['usesPerDay']} Anwendungen heute übrig)"
        if "chargesRemaining" in entry:
            description += f" ({entry['chargesRemaining']}/{entry['maxCharges']} Ladungen übrig)"
        # An item can have both consumable uses/charges and be toggleable at once (a wand: charges +
        # activation="activatable") — "use" wins in that case, since consuming a charge is the
        # dominant real intent; no seeded item needs a separate toggle affordance alongside it today.
        gear_action_kind = "use" if ("usesRemainingToday" in entry or "chargesRemaining" in entry) else "toggle"
        actions.append(
            {
                "id": f"gear-{entry['id']}",
                "icon": "🎒",
                "name": entry["name"],
                "tag": None,
                "description": description,
                "sourceType": "gear",
                "sourceId": entry["id"],
                "gearActionKind": gear_action_kind,
                # Guaranteed present: `_build_gear` sets it whenever `activation == "activatable"`,
                # the same condition already filtered on above. Surfaced so a toggle click has some
                # visible confirmation on the card itself — toggling doesn't create a `CharacterEffect`
                # row (gear active-state is deliberately its own thing, not routed through the
                # Effects system), so "Aktive Effekte" is the wrong place to look for it.
                "isActive": entry["isActive"],
            }
        )

    return actions


def _build_external_class_abilities(db: Session) -> list[dict]:
    """The catalog-wide counterpart to `_build_activatable_class_abilities`:
    persistent-effect class abilities whose `activation_scope` is
    `"external"`/`"both"` (`BaseClassAbility`'s docstring) — effects a
    character can receive from someone *else's* ability (Barde's Lied des
    Mutes on an ally who has no Barde levels at all). Not gated by this
    character's own granted abilities, same reasoning `conditionsCatalog` is
    offered to every character regardless of what they know."""
    abilities = db.scalars(
        select(BaseClassAbility).where(
            BaseClassAbility.is_persistent_effect.is_(True),
            BaseClassAbility.activation_scope.in_(["external", "both"]),
        )
    ).all()
    return [{"key": str(ability.id), "name": ability.name} for ability in abilities]


def _build_external_spells(db: Session) -> list[dict]:
    """The spell counterpart to `_build_external_class_abilities`: persistent-
    effect spells whose `range` isn't `"Persönlich"` — a touch/close/medium/
    long-range spell (e.g. Magierrüstung, "Berührung") can be cast on a
    character by *someone else's* caster, not only by the character
    themselves, so it's offered to every character regardless of whether
    they personally know it (same reasoning `conditionsCatalog` and
    `_build_external_class_abilities` already use). `range` "Persönlich"
    (self-only by definition, e.g. a Barde's own bardic performance-shaped
    spells) or unset/unparsed `range` data stays excluded here — those only
    ever show up via `_build_activatable_spells`'s known-spells gate."""
    spells = db.scalars(
        select(BaseSpell).where(
            BaseSpell.is_persistent_effect.is_(True),
            BaseSpell.range.is_not(None),
            BaseSpell.range != "Persönlich",
        )
    ).all()
    return [{"key": str(spell.id), "name": spell.name} for spell in spells]


def _build_active_effects(db: Session, character: Character, context: CharacterContext) -> list[dict]:
    """This character's active `CharacterEffect` rows (roadmap slice 5),
    resolved against whichever catalog `source_type` points at for a display
    name. Real backend-driven data — distinct from the older mock
    `effectsActive`/`/api/effects` seal system (icon/amount/variant) that
    predates this slice and still exists for the frontend's fixture
    characters; this key intentionally differs (`activeEffects`) so the two
    don't collide.

    `dailyLimitRemaining`/`dailyLimitTotal` (2026-08-12) are the one thing
    here not read straight off the `CharacterEffect` row — a `DAILY_LIMITS`
    ability (e.g. Kampfrausch) deliberately leaves `duration_remaining`
    unset (its pool lives in `CharacterAbilityUsage`, not the effect row, see
    `rules/classes/barbarian.py`), so without this the frontend's active-
    effect seal would show a bare "bis Entfernen" while raging instead of
    how many rounds are actually left today."""
    if not character.effects:
        return []

    ids_by_source: dict[str, set[UUID]] = {"condition": set(), "spell": set(), "class_ability": set(), "feat": set()}
    for effect in character.effects:
        ids_by_source[effect.source_type].add(effect.source_id)

    catalogs: dict[str, dict[UUID, object]] = {
        "condition": {
            row.id: row
            for row in db.scalars(select(BaseCondition).where(BaseCondition.id.in_(ids_by_source["condition"]))).all()
        }
        if ids_by_source["condition"]
        else {},
        "spell": (
            {row.id: row for row in db.scalars(select(BaseSpell).where(BaseSpell.id.in_(ids_by_source["spell"]))).all()}
            if ids_by_source["spell"]
            else {}
        ),
        "class_ability": (
            {
                row.id: row
                for row in db.scalars(
                    select(BaseClassAbility).where(BaseClassAbility.id.in_(ids_by_source["class_ability"]))
                ).all()
            }
            if ids_by_source["class_ability"]
            else {}
        ),
        "feat": (
            {row.id: row for row in db.scalars(select(BaseFeat).where(BaseFeat.id.in_(ids_by_source["feat"]))).all()}
            if ids_by_source["feat"]
            else {}
        ),
    }

    result = []
    for effect in character.effects:
        source = catalogs[effect.source_type].get(effect.source_id)
        if source is None:
            continue
        remaining = remaining_today(db, character, context, effect.source_id)
        result.append(
            {
                "id": str(effect.id),
                "sourceType": effect.source_type,
                "sourceId": str(effect.source_id),
                "name": source.name,
                # Only conditions carry a type ("condition"/"poison"/"disease") — spells/class
                # abilities have no equivalent subcategory, so this is the one field on this
                # dict that's frequently null. Lets the frontend pick a per-type icon without
                # a second round trip to the conditions catalog.
                "conditionType": source.type if effect.source_type == "condition" else None,
                "level": effect.level,
                "targetItemId": str(effect.target_item_id) if effect.target_item_id else None,
                "incubationRemaining": effect.incubation_remaining,
                "durationRemaining": effect.duration_remaining,
                "frequencyRounds": effect.frequency_rounds,
                "nextCheckIn": effect.next_check_in,
                "successesCurrent": effect.successes_current,
                "successesRequired": effect.successes_required,
                "dailyLimitRemaining": max(0, remaining) if remaining is not None else None,
                "dailyLimitTotal": DAILY_LIMITS[effect.source_id](context) if remaining is not None else None,
                # Every real `CharacterEffect` was itself put there by a player action (cast,
                # activated, applied), so it can always be taken away the same way — `False` is
                # reserved for `_build_item_granted_effects`' synthetic entries below, which have
                # no row to delete in the first place.
                "removable": True,
            }
        )
    return result


def _build_item_granted_effects(db: Session, items: dict[UUID, BaseItem], gear_by_slot: dict[str, CharacterGear]) -> list[dict]:
    """Synthesizes an `activeEffects`-shaped entry (see `_build_active_effects`)
    for every equipped item that permanently keeps its wearer under a spell's
    effect (`BaseItemGrantedSpell`, e.g. Brustplatte des Freibeuters ->
    permanently "Auf Wasser gehen") — derived fresh from the equipped-gear
    set on every sheet build rather than stored as a `CharacterEffect` row:
    unlike every other active effect, this one has no duration to count down
    and can't be independently canceled while the item stays equipped, so
    there is nothing for a stored row to actually track (see
    `BaseItemGrantedSpell`'s own docstring). `removable: False` is the
    frontend's cue to hide the seal's remove button for these.

    `id` is the `BaseItemGrantedSpell` catalog row's own id — stable across
    sheet builds (unlike a freshly minted id per call), and there is at most
    one equipped item per slot, so no per-character collision risk."""
    if not items:
        return []
    equipped_item_ids = {gear_row.item_id for gear_row in gear_by_slot.values()}
    if not equipped_item_ids:
        return []
    grants = db.scalars(
        select(BaseItemGrantedSpell).where(BaseItemGrantedSpell.item_id.in_(equipped_item_ids))
    ).all()
    if not grants:
        return []
    spells = {
        row.id: row for row in db.scalars(select(BaseSpell).where(BaseSpell.id.in_({g.spell_id for g in grants}))).all()
    }
    result = []
    for grant in grants:
        spell = spells.get(grant.spell_id)
        item = items.get(grant.item_id)
        if spell is None or item is None:
            continue
        result.append(
            {
                "id": str(grant.id),
                "sourceType": "spell",
                "sourceId": str(spell.id),
                "name": f"{spell.name} ({item.name})",
                "conditionType": None,
                "level": None,
                "incubationRemaining": None,
                "durationRemaining": None,
                "frequencyRounds": None,
                "nextCheckIn": None,
                "successesCurrent": 0,
                "successesRequired": None,
                "dailyLimitRemaining": None,
                "dailyLimitTotal": None,
                "removable": False,
            }
        )
    return result


def _build_gear(db: Session, character: Character) -> list[dict]:
    if not character.gear:
        return []
    items = {item.id: item for item in db.scalars(select(BaseItem).where(BaseItem.id.in_(
        [g.item_id for g in character.gear]
    ))).all()}
    ability_ids = {link.ability_id for gear_row in character.gear for link in gear_row.special_abilities}
    abilities = (
        {
            ability.id: ability
            for ability in db.scalars(
                select(BaseWeaponSpecialAbility).where(BaseWeaponSpecialAbility.id.in_(ability_ids))
            ).all()
        }
        if ability_ids
        else {}
    )
    spell_ids = {g.stored_spell_id for g in character.gear if g.stored_spell_id}
    spells = (
        {spell.id: spell for spell in db.scalars(select(BaseSpell).where(BaseSpell.id.in_(spell_ids))).all()}
        if spell_ids
        else {}
    )
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
        # Structured abilities (roadmap.md's "Magische Verzauberung/Material
        # als Berechnung statt Freitext") — resolved through the same
        # HANDLERS mechanism as every other ability/effect (CLAUDE.md),
        # distinct from `properties` above, which stays freetext for
        # anything not (yet) in the `BaseWeaponSpecialAbility` catalog.
        special_abilities = [
            resolve_weapon_ability(abilities[link.ability_id])
            for link in gear_row.special_abilities
            if link.ability_id in abilities
        ]
        if special_abilities:
            entry["specialAbilities"] = special_abilities
        # Usage/charge state (roadmap.md's "Wondrous-Item-Katalog mit echter
        # Attributsboni-Wirkung", decided 2026-08-04) — `chargesRemaining`/
        # `usesRemainingToday` only appear when the catalog item actually has
        # that kind of counter; `isActive` only for "aktivierbar" items.
        if item.activation is not None:
            entry["activation"] = item.activation
        if item.max_charges is not None:
            entry["chargesRemaining"] = gear_row.charges_remaining
            entry["maxCharges"] = item.max_charges
        if item.uses_per_day is not None:
            entry["usesRemainingToday"] = gear_row.uses_remaining_today
            entry["usesPerDay"] = item.uses_per_day
        if item.activation == "activatable":
            entry["isActive"] = gear_row.is_active
        if gear_row.stored_spell_id is not None:
            spell = spells.get(gear_row.stored_spell_id)
            if spell is not None:
                entry["storedSpell"] = spell.name
        result.append(entry)
    return result


def _gear_lookup(db: Session, character: Character) -> tuple[dict[UUID, BaseItem], dict[str, CharacterGear]]:
    """Shared prep step for `_gear_ac_modifiers`/`_build_equipment`: every
    equipped item's catalog row, and equipped gear keyed by slot — one query
    for both, computed once in `build_character_sheet` rather than each
    function re-fetching it."""
    if not character.gear:
        return {}, {}
    items = {
        item.id: item
        for item in db.scalars(select(BaseItem).where(BaseItem.id.in_([g.item_id for g in character.gear]))).all()
    }
    gear_by_slot = {g.equipped_slot: g for g in character.gear if g.equipped_slot}
    return items, gear_by_slot


def _gear_ac_modifiers(
    items: dict[UUID, BaseItem], gear_by_slot: dict[str, CharacterGear]
) -> tuple[list[Modifier], int | None]:
    """Raw AC `Modifier`s from equipped gear (armor/shield's real
    `BaseItem.ac_bonus`, any slot's `enhancement`), plus armor's
    `max_dex_bonus` cap. Returns the raw list, not a stacked total: the
    caller (`build_character_sheet`) combines it with composition-driven AC
    modifiers *before* stacking, so a same-type bonus from either source
    still only counts once (`rules/modifiers.py`'s `stack_by_target`
    docstring). Only armor ("ruestung") and shield ("schild") have real
    `ac_bonus` data (`rules/equipment_slots.SLOT_CATEGORY`) — other slots
    only contribute via `enhancement`, if set."""
    modifiers: list[Modifier] = []
    max_dex_bonus: int | None = None
    for slot_key, category in SLOT_CATEGORY.items():
        gear_row = gear_by_slot.get(slot_key)
        item = items.get(gear_row.item_id) if gear_row else None
        if item is None:
            continue
        modifiers.append(
            Modifier(
                source=item.name,
                type=category,
                value=(item.ac_bonus or 0) + gear_row.enhancement,
                target=ModifierTarget.AC,
            )
        )
        if category == "armor":
            max_dex_bonus = item.max_dex_bonus
    return modifiers, max_dex_bonus


def _build_equipment(
    character: Character, items: dict[UUID, BaseItem], gear_by_slot: dict[str, CharacterGear]
) -> list[dict]:
    """Paperdoll slot options from equipped gear (roadmap slice 4). Only
    armor ("ruestung") and shield ("schild") have real `BaseItem.ac_bonus`
    data (`rules/equipment_slots.SLOT_CATEGORY`) — the other 12 slots render
    with empty options (see this module's docstring). AC itself is computed
    by the caller (`build_character_sheet`, via `_gear_ac_modifiers` +
    `character_modifiers`, stacked together) — this function is display-only."""
    if not character.gear:
        return [{**slot_def, "options": [], "selected": ""} for slot_def in SLOT_DEFINITIONS]

    # Keyed by (category, BaseItem.slot) rather than category alone — several
    # paperdoll slots share category "wondrous"/"ring" (roadmap.md's
    # "Wondrous-Item-Katalog mit echter Attributsboni-Wirkung", decided
    # 2026-08-04), so a Gürtel-item must not show up as an option for the
    # Hals slot too.
    owned_by_category_slot: dict[tuple[str, str | None], list[BaseItem]] = {}
    for gear_row in character.gear:
        item = items.get(gear_row.item_id)
        if item is not None:
            owned_by_category_slot.setdefault((item.category, item.slot), []).append(item)

    equipment_slots = []
    for slot_def in SLOT_DEFINITIONS:
        required_category = SLOT_CATEGORY.get(slot_def["key"])
        required_item_slot = SLOT_TO_ITEM_SLOT.get(slot_def["key"])
        options: list[dict] = []
        selected = ""
        if required_category is not None:
            candidates = (
                owned_by_category_slot.get((required_category, required_item_slot), [])
                if required_item_slot is not None
                else [item for (cat, _), items_ in owned_by_category_slot.items() if cat == required_category for item in items_]
            )
            options = [{"value": str(candidate.id), "label": candidate.name} for candidate in candidates]
            equipped = gear_by_slot.get(slot_def["key"])
            if equipped is not None:
                selected = str(equipped.item_id)
        equipment_slots.append({**slot_def, "options": options, "selected": selected})

    return equipment_slots


_WEAPON_HAND_LABELS = {"hauptwaffe": "Hauptwaffe", "nebenwaffe": "Nebenhand"}


def _iterative_attack_bonuses(bab: int, flat_bonus: int) -> list[int]:
    """PF1e iterative attacks: a second/third/fourth attack joins at BAB
    6/11/16 (one extra per full 5 points of BAB from 6 up), each 5 lower
    than the last — e.g. BAB 7 -> [+7, +2]. `bab < 1` (a 0-or-negative
    total, e.g. a fresh level-1 poor-BAB caster) still gets the one attack."""
    count = 1 + (bab - 1) // 5 if bab >= 1 else 1
    return [flat_bonus - 5 * i for i in range(count)]


def _grip_scaled(value: int, hands: str | None, is_off_hand: bool) -> int:
    """PF1e's melee grip-based scaling: a two-handed weapon adds 150% of a
    bonus (floored), an off-hand weapon only 50% — a one-handed/light
    weapon in the main hand (neither case) gets the full value. Shared by
    `_weapon_damage_str_mod` (Str-to-damage) and `_power_attack_effect`
    (Heftiger Angriff's damage bonus) — the two PF1e melee-damage bonuses
    this exact scaling rule applies to."""
    if hands == "two":
        return (value * 3) // 2
    if is_off_hand:
        return value // 2
    return value


def _weapon_damage_str_mod(str_mod: int, hands: str | None, is_off_hand: bool) -> int:
    """PF1e's Str-to-damage scaling by grip (`_grip_scaled`) — but a
    negative Str mod (a penalty) is never scaled, only bonuses are (PF1e
    FAQ), unlike `_grip_scaled`'s other caller (Heftiger Angriff's bonus,
    which is never negative in the first place)."""
    if str_mod < 0:
        return str_mod
    return _grip_scaled(str_mod, hands, is_off_hand)


def _power_attack_effect(
    bab: int, context: CharacterContext, hands: str | None = None, is_off_hand: bool = False
) -> tuple[int, int] | None:
    """Heftiger Angriff's attack/damage trade-off (`rules/feats.py`'s
    `power_attack_bonus`), folded into a melee weapon/natural attack's own
    computed numbers only while the player has actually activated it
    (`context.active_effects`, `POST .../effects` with `source_type:
    "feat"`) — same "own-state toggle" pattern `_kampfrausch_entfesselter_barbar`
    already uses for its own id, not a `HANDLERS`/`Modifier` entry, since the
    damage half still needs per-weapon grip scaling (`_grip_scaled`) a single
    flat `ModifierTarget.DAMAGE` value can't represent. Returns the
    already-scaled `(attack_penalty, damage_bonus)` pair for the caller to
    add into its own attack-bonus/damage-dice computation; `None` when not
    currently active."""
    if not any(effect.source_id == HEFTIGER_ANGRIFF for effect in context.active_effects):
        return None
    attack_penalty, damage_bonus = power_attack_bonus(bab)
    return attack_penalty, _grip_scaled(damage_bonus, hands, is_off_hand)


def _class_weapon_bonus_damage(
    class_ability_ids: Counter[UUID], context: CharacterContext
) -> list[tuple[str, str]]:
    """Resolves `rules/handlers.py`'s `WEAPON_BONUS_DAMAGE_HANDLERS` against
    a character's granted class abilities — shared by `_build_weapon_attacks`
    (manufactured weapons) and `_build_natural_attacks` (claws/bites/...),
    since a rage power's extra elemental damage (e.g. Elementare
    Kampfhaltung while raging) is a property of the character's melee
    attacks in general, not of whichever weapon happens to be equipped —
    RAW doesn't distinguish "wielding a weapon" from "attacking unarmed/with
    natural weapons" for this kind of bonus."""
    return [
        bonus
        for ability_id in class_ability_ids
        if context.requirement_met(ability_id)
        and (handler := WEAPON_BONUS_DAMAGE_HANDLERS.get(ability_id)) is not None
        and (bonus := handler(context)) is not None
    ]


def _temp_weapon_enhancement_by_item_id(context: CharacterContext) -> dict[UUID, int]:
    """Resolves `rules/handlers.py`'s `WEAPON_ENHANCEMENT_HANDLERS` against
    every registered ability id unconditionally (unlike `_class_weapon_bonus_damage`
    above, this isn't scoped to the character's own granted abilities — an
    activatable effect like Arkaner Vorrat's weapon buff is only ever
    present in `context.active_effects` at all once actually activated, so
    there's no separate granted-ability gate to check first). Keyed by
    `BaseItem` id (`CharacterEffect.target_item_id`'s own key, see that
    field's docstring for why it's the item id and not the owning
    `CharacterGear` row's), summed in case more than one source ever
    targets the same item at once (PF1e RAW doesn't actually allow that for
    Arkaner Vorrat itself — "kann immer nur eine Waffe gleichzeitig
    verbessern" — but nothing stops a second, unrelated ability from doing
    the same someday); `_build_weapon_attacks` caps the combined total
    against the item's own permanent bonus at +5."""
    result: dict[UUID, int] = {}
    for handler in WEAPON_ENHANCEMENT_HANDLERS.values():
        resolved = handler(context)
        if resolved is None:
            continue
        item_id, bonus = resolved
        result[item_id] = result.get(item_id, 0) + bonus
    return result


def _build_weapon_attacks(
    items: dict[UUID, BaseItem],
    gear_by_slot: dict[str, CharacterGear],
    gear_entries: list[dict],
    bab: int,
    str_mod: int,
    dex_mod: int,
    melee_attack_bonus: int,
    melee_damage_bonus: int,
    context: CharacterContext,
    class_ability_ids: Counter[UUID],
) -> list[dict]:
    """Computed attack-bonus/damage-dice readout for whatever's equipped in
    the "hauptwaffe"/"nebenwaffe" paperdoll slots (roadmap.md's Slice-4
    weapon-slot item, 2026-08-11) — a static display number, not a dice
    roll (see `rules/weapon_abilities.py`'s module docstring: this app
    doesn't roll for the player). Attack uses Dex for a weapon with a
    `weapon_range` (thrown/projectile), Str otherwise — a simplification
    for thrown weapons (PF1e RAW still adds Str to *damage* for those, not
    modeled here, see `_weapon_damage_str_mod`'s ranged-is-zero handling
    below) and for projectile weapons that add a capped Str bonus (composite
    bows), also not modeled. A melee weapon also uses Dex instead when the
    character has Waffenfinesse (`rules/feats.py`'s `WAFFENFINESSE`) and
    `BaseItem.is_light` is set on the equipped item (light weapons plus
    PF1e's named non-light exceptions, see that field's docstring) — damage
    still uses `str_mod` either way, since the feat only affects the attack
    roll. `gear_entries` (this module's own already-built
    `_build_gear` output) is reused rather than re-querying
    `BaseWeaponSpecialAbility` a second time — its `specialAbilities` list
    already carries each ability's resolved `bonusDamage` (only the 8 flat
    on-hit energy abilities have one, see `weapon_abilities.py`), gated here
    on the equipped instance's own `CharacterGear.is_active`.

    `melee_attack_bonus`/`melee_damage_bonus` (`build_character_sheet`'s
    stacked `ModifierTarget.ATTACK`/`DAMAGE`, e.g. Kampfrausch's flat +2)
    are added to melee weapons only — this function's own `is_ranged` flag
    already conflates thrown-and-true-ranged (see above), so applying either
    bonus to every "ranged" item would incorrectly buff a bow; Kampfrausch's
    thrown-weapon-damage nuance is therefore a known, documented gap here
    too, not modeled.

    `context` only feeds Heftiger Angriff's attack/damage trade-off while
    actually activated (`_power_attack_effect`) — melee only, same reasoning
    as `melee_attack_bonus`/`melee_damage_bonus` above (Power Attack is
    explicitly a *melee* attack/damage trade-off, GRW S. 124).

    `class_ability_ids` (`build_character_sheet`'s `granted_ability_ids`,
    same argument `_build_natural_attacks` already takes) resolves
    `rules/handlers.py`'s `WEAPON_BONUS_DAMAGE_HANDLERS` — a granted class
    ability's own extra melee damage die while active (e.g. Elementare
    Kampfhaltung's energy damage while raging), same shape as gear's own
    `specialAbilities`-sourced `bonusDamage` just below, computed once here
    since it doesn't vary per weapon slot.

    A weapon whose `weapon_type` isn't among `context.class_granted_proficiency_feat_ids`/
    `context.feat_ids`'s resolved blanket categories (`rules/proficiency.py`'s
    `known_weapon_types`) *and* whose own id isn't in `context.chosen_weapon_ids`
    (a picked single-weapon-choice feat, a Kensai's free weapon choice, or a
    race ability's fixed named-weapon list, e.g. Elf's "Elfische
    Waffenvertrautheit")
    takes PF1e's flat -4 non-proficient penalty on the attack roll, surfaced
    as a "Nicht geübt" note — the one part of "Umgang mit Waffen und
    Rüstungen" that's actually computed today; the armor-proficiency/
    arcane-spell-failure parts of that same ability stay text-only (no ACP
    or spell-failure system exists yet, see `todos.md`). A weapon whose id
    is in `context.weapon_focus_weapon_ids` (a picked Waffenfokus, or a
    Kensai's own free grant of it for their kensai weapon) gets Weapon
    Focus's +1 the same way, folded into the same attack-bonus sum."""
    gear_entries_by_item_id = {entry["id"]: entry for entry in gear_entries}
    class_bonus_damage = _class_weapon_bonus_damage(class_ability_ids, context)
    known_types = known_weapon_types(context.class_granted_proficiency_feat_ids, context.feat_ids)
    temp_enhancement_by_item_id = _temp_weapon_enhancement_by_item_id(context)
    results = []
    for slot_key, hand_label in _WEAPON_HAND_LABELS.items():
        gear_row = gear_by_slot.get(slot_key)
        item = items.get(gear_row.item_id) if gear_row is not None else None
        if item is None or item.category != "weapon":
            continue
        # PF1e caps a weapon's *combined* enhancement bonus (permanent +
        # temporary, e.g. Kampfmagus's Arkaner Vorrat) at +5 regardless of
        # how many sources contribute — capped here, once, rather than at
        # each of the two use sites below.
        enhancement = min(5, gear_row.enhancement + temp_enhancement_by_item_id.get(gear_row.item_id, 0))

        is_ranged = item.weapon_range is not None
        power_attack = (
            None if is_ranged else _power_attack_effect(bab, context, item.hands, slot_key == "nebenwaffe")
        )
        power_attack_penalty = power_attack[0] if power_attack is not None else 0
        power_attack_damage = power_attack[1] if power_attack is not None else 0
        # A weapon's own `weapon_type` (simple/martial/exotic) unset means
        # its proficiency category isn't catalogued — no malus rather than
        # a false positive (`rules/proficiency.py`'s module docstring, e.g.
        # firearms today).
        is_proficient = (
            item.weapon_type is None or item.weapon_type in known_types or item.id in context.chosen_weapon_ids
        )
        proficiency_penalty = 0 if is_proficient else NOT_PROFICIENT_ATTACK_PENALTY
        weapon_focus_bonus = WAFFENFOKUS_ATTACK_BONUS if item.id in context.weapon_focus_weapon_ids else 0

        if is_ranged:
            attack_ability_mod = dex_mod
        elif WAFFENFINESSE in context.feat_ids and item.is_light:
            attack_ability_mod = dex_mod + melee_attack_bonus
        else:
            attack_ability_mod = str_mod + melee_attack_bonus
        attack_bonuses = _iterative_attack_bonuses(
            bab,
            bab
            + attack_ability_mod
            + enhancement
            + power_attack_penalty
            + proficiency_penalty
            + weapon_focus_bonus,
        )

        damage_parts: list[str] = []
        if item.damage_medium:
            damage_str_mod = (
                0 if is_ranged else _weapon_damage_str_mod(str_mod, item.hands, slot_key == "nebenwaffe")
            )
            flat_damage = (
                damage_str_mod + enhancement + (0 if is_ranged else melee_damage_bonus) + power_attack_damage
            )
            piece = item.damage_medium + (_fmt(flat_damage) if flat_damage else "")
            if item.damage_type:
                piece += f" {item.damage_type}"
            damage_parts.append(piece)
            if not is_ranged:
                damage_parts.extend(f"{dice} {damage_type}" for dice, damage_type in class_bonus_damage)

        entry = gear_entries_by_item_id.get(str(gear_row.item_id))
        for ability in (entry or {}).get("specialAbilities", []):
            bonus = ability.get("bonusDamage")
            if bonus and (not bonus["requiresActive"] or gear_row.is_active):
                damage_parts.append(f"{bonus['dice']} {bonus['type']}")

        result = {
            "key": slot_key,
            "hand": hand_label,
            "name": item.name,
            "attackBonus": "/".join(_fmt(bonus) for bonus in attack_bonuses),
            "damage": " + ".join(damage_parts) if damage_parts else "—",
        }
        notes = []
        if power_attack is not None:
            notes.append("Heftiger Angriff aktiv")
        temp_enhancement = temp_enhancement_by_item_id.get(gear_row.item_id, 0)
        if temp_enhancement:
            notes.append(f"Vorübergehender Verbesserungsbonus aktiv ({_fmt(temp_enhancement)})")
        if not is_proficient:
            notes.append(f"Nicht geübt ({_fmt(NOT_PROFICIENT_ATTACK_PENALTY)})")
        if notes:
            result["note"] = " · ".join(notes)
        results.append(result)
    return results


def _build_natural_attacks(
    items: dict[UUID, BaseItem],
    gear_by_slot: dict[str, CharacterGear],
    race_ability_ids: set[UUID],
    class_ability_ids: Counter[UUID],
    context: CharacterContext,
    bab: int,
    str_mod: int,
    melee_attack_bonus: int,
    melee_damage_bonus: int,
) -> list[dict]:
    """Bite/claw-style natural weapon attacks a character's race/class
    abilities grant (e.g. Halb-Ork's Reißzähne, Entfesselter Barbar's
    Bestientotem-Klauen, both `rules/handlers.py`'s `NATURAL_ATTACK_HANDLERS`)
    — appended to `_build_weapon_attacks`'s own list by
    `build_character_sheet` so both render in the sheet's one "Waffen"
    section; `WeaponAttack`'s shape is generic enough for either source, no
    frontend change needed.

    PF1e RAW: a natural weapon attack a character can make on its own (no
    manufactured weapon in either weapon slot) rolls at full BAB and full
    Str-to-damage — a "primary" natural attack. The moment any manufactured
    weapon is wielded (`hauptwaffe`/`nebenwaffe`), every natural attack
    becomes secondary instead: BAB-5 on the attack roll, only half (rounded
    down, never for an already-negative Str mod — same convention
    `_weapon_damage_str_mod` uses) Str-to-damage — regardless of which
    "hand" the natural weapon itself uses; even a bite becomes secondary
    once a sword is in hand. Applied uniformly to every natural attack the
    character has, not resolved per-source against each other — PF1e's FAQ
    ruling on stacking multiple *simultaneously primary* natural-attack
    sources (e.g. a racial bite granted alongside a rage power's claws)
    deliberately isn't modeled, a known simplification (see todos.md's
    "Rassengröße" entry for the sibling simplification on size-scaled
    damage dice).

    `melee_attack_bonus`/`melee_damage_bonus` (`build_character_sheet`'s
    already-stacked ATTACK/DAMAGE modifiers, e.g. Kampfrausch's flat +2)
    apply the same way they do to melee weapon attacks — rage's bonus
    covers natural weapons too under RAW.

    Not every granted ability's natural attack is unconditionally present:
    a rage power's claws (Entfesselter Barbar's Bestientotem) only manifest
    while actually raging, so its handler reads `context.active_effects`
    and returns `None` otherwise — same reasoning `_kampfrausch_entfesselter_barbar`
    already applies to its own flat Modifiers. A racial bite (Reißzähne)
    ignores `context` entirely and is always present once granted.

    A granted class ability's own extra melee damage die (e.g. Elementare
    Kampfhaltung's energy damage while raging) applies here too, via the
    same `_class_weapon_bonus_damage` helper `_build_weapon_attacks` uses —
    RAW doesn't limit that kind of bonus to manufactured weapons."""
    wields_weapon = any(
        (gear_row := gear_by_slot.get(slot)) is not None and items[gear_row.item_id].category == "weapon"
        for slot in _WEAPON_HAND_LABELS
    )
    # Natural attacks never get Power Attack's 150% two-handed scaling (no
    # "hands" concept for them at all, same simplification the Str-mod
    # halving just below already makes) — only the secondary-attack 50%
    # halving via `wields_weapon`, reusing `_power_attack_effect`'s
    # `is_off_hand` parameter for that same halving rule.
    power_attack = _power_attack_effect(bab, context, hands=None, is_off_hand=wields_weapon)
    power_attack_penalty = power_attack[0] if power_attack is not None else 0
    power_attack_damage = power_attack[1] if power_attack is not None else 0

    attack_bonus = bab + str_mod + melee_attack_bonus - (5 if wields_weapon else 0) + power_attack_penalty
    damage_str_mod = str_mod if str_mod < 0 or not wields_weapon else str_mod // 2
    flat_damage = damage_str_mod + melee_damage_bonus + power_attack_damage

    class_bonus_damage = _class_weapon_bonus_damage(class_ability_ids, context)
    ability_ids = sorted(set(race_ability_ids) | set(class_ability_ids), key=str)
    results = []
    for ability_id in ability_ids:
        if not context.requirement_met(ability_id):
            continue
        handler = NATURAL_ATTACK_HANDLERS.get(ability_id)
        if handler is None:
            continue
        attack = handler(context)
        if attack is None:
            continue
        damage_parts = [f"{attack.damage_dice}{_fmt(flat_damage) if flat_damage else ''} {attack.damage_type}"]
        damage_parts.extend(f"{dice} {damage_type}" for dice, damage_type in class_bonus_damage)
        result = {
            "key": f"natural-{ability_id}",
            "hand": "Naturangriff",
            "name": attack.name,
            "attackBonus": "/".join(_fmt(attack_bonus) for _ in range(attack.count)),
            "damage": " + ".join(damage_parts),
        }
        if power_attack is not None:
            result["note"] = "Heftiger Angriff aktiv"
        results.append(result)
    return results
