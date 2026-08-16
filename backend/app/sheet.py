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
- Per-day spell prepare/cast tracking (roadmap slice 6) — `spellsKnown`
  (`used`) and `spellbook` (`prepared`) both list every known spell with
  their tracking flag always `False`.

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
    BaseCondition,
    BaseFeat,
    BaseItem,
    BaseRace,
    BaseRaceAbility,
    BaseSkill,
    BaseSpell,
    BaseTrait,
    BaseWeaponSpecialAbility,
    Character,
    CharacterGear,
)
from .routers.characters import _class_def
from .routers.races import effective_race_ability_ids, race_ability_score_mods, race_skill_modifiers
from .rules.context import CharacterContext
from .rules.daily_limits import remaining_today
from .rules.effective_scores import ability_damage_totals, full_effective_ability_scores
from .rules.equipment_slots import SLOT_CATEGORY, SLOT_DEFINITIONS, SLOT_TO_ITEM_SLOT
from .rules.favored_class_bonuses import HANDLERS as FAVORED_CLASS_BONUS_HANDLERS
from .rules.favored_class_bonuses import SHORT_LABELS as FAVORED_CLASS_BONUS_SHORT_LABELS
from .rules.favored_class_bonuses import pick_counts as favored_class_bonus_pick_counts
from .rules.feats import HEFTIGER_ANGRIFF, power_attack_bonus
from .rules.handlers import DAILY_LIMITS, NATURAL_ATTACK_HANDLERS, character_modifiers, situational_skill_notes
from .rules.modifiers import Modifier, ModifierTarget, SkillNote, contributing, group_by_target, stack
from .rules.speed import class_speed_bonus, jump_skill_note, race_speed
from .rules.progression import ability_mod, max_hit_points
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

    level_counts_by_root_id: dict[UUID, int] = {}
    for lvl in character.levels:
        level_counts_by_root_id[lvl.base_class_id] = level_counts_by_root_id.get(lvl.base_class_id, 0) + 1
    granted_ability_ids = _granted_class_ability_ids(db, character, level_counts_by_root_id)

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
        granted_ability_ids=granted_ability_ids,
        active_effects=character.effects,
        gear_item_ids=frozenset(g.item_id for g in character.gear),
        level_counts_by_root_id=level_counts_by_root_id,
        favored_class_bonus_pick_counts=favored_class_bonus_pick_counts(character),
    )
    # Every Modifier from a composition source that doesn't already have its
    # own dedicated, repeat-count-aware resolution pipeline — feats, traits,
    # active effects (`rules/handlers.py`'s `character_modifiers`; race/class
    # granted-ability ids are deliberately excluded there, see its
    # docstring) — plus a race's own SKILL-target grants (`race_skill_modifiers`,
    # e.g. Halb-Ork's Einschüchternd — SCORE/SPEED already have their own
    # dedicated path, see that function's docstring) and gear's own AC bonus
    # (armor/shield `ac_bonus`, any slot's `enhancement`). Combined into one
    # raw list *before* stacking, not stacked separately per source and
    # added: two same-type bonuses (e.g. a composition "armor" bonus and a
    # gear "armor" bonus) must not both apply, and `stack()` can only enforce
    # that within a single call (`rules/modifiers.py`'s `stack_by_target`
    # docstring). Grouped by target once here and threaded into
    # AC/saves/speed/skills below as plain dict lookups rather than each one
    # re-filtering/re-stacking.
    items, gear_by_slot = _gear_lookup(db, character)
    gear_ac_modifiers, max_dex_bonus = _gear_ac_modifiers(items, gear_by_slot)
    all_modifiers = character_modifiers(context) + race_skill_modifiers(db, character.race_id)
    # Grouped once here (`rules/modifiers.py`'s `group_by_target`), rather
    # than each consumer below re-filtering the same flat list — `stacked`
    # (the summed total per target, what AC/saves/speed/skills actually add
    # up) and `groups` (the raw per-target Modifier list, what the AC/skill
    # breakdowns below read `contributing()` off of) both come from this one
    # pass.
    groups = group_by_target(all_modifiers + gear_ac_modifiers)
    stacked = {key: stack(group) for key, group in groups.items()}

    capped_dex_mod = dex_mod if max_dex_bonus is None else min(dex_mod, max_dex_bonus)
    armor_class = 10 + capped_dex_mod + stacked.get((ModifierTarget.AC, None), 0)
    armor_class_breakdown = _ac_breakdown(capped_dex_mod, groups)
    equipment_slots = _build_equipment(character, items, gear_by_slot)

    base_speed = race_speed(db, character.race_id) or 9
    total_speed = base_speed + class_speed_bonus(context) + stacked.get((ModifierTarget.SPEED, None), 0)
    gear = _build_gear(db, character)
    melee_attack_bonus = stacked.get((ModifierTarget.ATTACK, None), 0)
    melee_damage_bonus = stacked.get((ModifierTarget.DAMAGE, None), 0)
    race_ability_ids = effective_race_ability_ids(
        db, character.race_id, {choice.ability_id for choice in character.racial_choices}
    )
    weapon_attacks = _build_weapon_attacks(
        items, gear_by_slot, gear, bab, str_mod, dex_mod, melee_attack_bonus, melee_damage_bonus, context
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
        ],
        "skills": _build_skills(
            db, character, level_counts_by_root_id, ability_mods, total_speed, stacked, groups, context
        ),
        "feats": _build_feats(db, character),
        "traits": _described(db, BaseTrait, character.trait_ids),
        "classFeatures": _build_class_features(db, granted_ability_ids),
        "raceAbilities": _build_race_abilities(db, race_ability_ids),
        "favoredClassBonusOptions": _favored_class_bonus_options(db, favored_root_id, character.race_id),
        "favoredClassBonuses": _build_favored_class_bonuses(db, character),
        "spellsKnown": _build_spell_grades(db, character, "used"),
        "gear": gear,
        "weaponAttacks": weapon_attacks,
        "equipmentSlots": equipment_slots,
        "spellbook": _build_spell_grades(db, character, "prepared"),
        "actions": _build_actions(db, character, granted_ability_ids, gear),
        "effectsActive": [],
        "activeEffects": _build_active_effects(db, character, context),
        "activatableSpells": _build_activatable_spells(db, character),
        "activatableClassAbilities": _build_activatable_class_abilities(db, character, context, granted_ability_ids),
        "activatableFeats": _build_activatable_feats(db, character),
        "externalClassAbilities": _build_external_class_abilities(db),
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
        "traits": [row["name"] for row in _described(db, BaseTrait, character.trait_ids)],
        # Alternate-trait names (not the flex ability-score pick) - needed by
        # the level-up wizard to tell whether a race's skill-point-per-level
        # bonus (e.g. Human's Geschult) was traded away, same "replaces"
        # check creation's own skillPointsTotal does.
        "altTraits": character.alt_traits,
        "skillRanks": character.skill_ranks,
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
        skill_names = [
            skill.name for skill in (db.get(BaseSkill, entry.skill_id) for entry in level.skill_ranks) if skill
        ]
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
    return [{"key": str(row.id), "name": row.name, "description": row.description} for row in rows]


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
        result.append({"key": str(entry.id), "name": name, "description": feat.description})
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
    skill_ranks = {UUID(skill_id): ranks for skill_id, ranks in character.skill_ranks.items() if ranks > 0}

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

    # Every skill usable untrained belongs on the sheet even at 0 ranks
    # (PF1e core's "Trained Only" column, `BaseSkill.trained_only`) — a
    # trained-only skill only shows up once ranks are actually invested.
    skills = db.scalars(
        select(BaseSkill).where(
            (BaseSkill.trained_only.is_(False)) | (BaseSkill.id.in_(skill_ranks))
        )
    ).all()

    result = []
    for skill in skills:
        ranks = skill_ranks.get(skill.id, 0)
        ab_mod = ability_mods.get(skill.ability, 0)
        class_bonus = 3 if skill.id in class_skill_ids else 0
        # Unconditional feat/race/class-ability skill bonuses (e.g.
        # Einschüchternde Kraft's ST modifier on Einschüchtern,
        # `rules/feats.py`; Halb-Ork's Einschüchternd, `race_skill_modifiers`
        # above) — 0 for every skill without such a handler, same "wired
        # ahead of the first producer" convention `ModifierTarget.SKILL` was
        # declared under.
        handler_bonus = stacked.get((ModifierTarget.SKILL, str(skill.id)), 0)
        base_value = ranks + ab_mod + class_bonus + handler_bonus
        entry = {"key": str(skill.id), "label": skill.name, "value": _fmt(base_value)}
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
        # themselves.
        notes = [
            f"{note.title}: {_fmt(base_value + note.value)} gesamt "
            f"({skill.name} {_fmt(base_value)} + {note.modifier_label} {_fmt(note.value)}{note.detail})"
            for note in notes_by_skill.get(skill.id, [])
        ]
        if notes:
            entry["note"] = "; ".join(notes)
        result.append(entry)
    return result


def _granted_class_ability_ids(
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


def _favored_class_bonus_race_choices(
    db: Session, favored_root_id: UUID | None, race_id: UUID
) -> list[BaseClassOptionChoice]:
    """This class's own race-scoped favored-class-bonus alternates (e.g.
    Half-Ork Barbar's "Halb-Ork (Barbar)",
    `scripts/import_favored_class_bonus_halbork.py`) — never includes
    "hp"/"skill", which aren't `BaseClassOptionChoice` rows at all (see
    `routers/characters.py`'s `level_up_character`). Empty without a
    favored class. Shared by `_favored_class_bonus_options` (names, for the
    wizard's pick list) and `_favored_class_bonus_descriptions` (name ->
    rules text, for the wizard's summary step) so both read the same query
    once instead of each re-deriving it."""
    if favored_root_id is None:
        return []
    return db.scalars(
        select(BaseClassOptionChoice)
        .join(BaseClassOptionGroup, BaseClassOptionGroup.id == BaseClassOptionChoice.group_id)
        .where(
            BaseClassOptionGroup.base_class_id == favored_root_id,
            BaseClassOptionGroup.key == "favored_class_bonus",
            BaseClassOptionChoice.race_id.is_(None) | (BaseClassOptionChoice.race_id == race_id),
        )
    ).all()


def _favored_class_bonus_options(db: Session, favored_root_id: UUID | None, race_id: UUID) -> list[str]:
    """Which values are currently legal for `LevelUp.favored_class_bonus`
    for this character's one favored class — "hp"/"skill" (the two stable
    literals every class offers) plus this class's own race-scoped
    alternates. The level-up wizard renders this list directly — no
    client-side race filtering needed, same reasoning `race_skill_modifiers`'s
    docstring gives for keeping composition-vs-character-scoped filtering
    server-side."""
    choices = _favored_class_bonus_race_choices(db, favored_root_id, race_id)
    return ["hp", "skill", *(choice.name for choice in choices)]


def _favored_class_bonus_descriptions(db: Session, favored_root_id: UUID | None, race_id: UUID) -> dict[str, str]:
    """Choice name -> full rules text, for this class's own race-scoped
    favored-class-bonus alternates only ("hp"/"skill" excluded — the
    level-up wizard already has fixed, friendly text for those two). Lets
    the wizard's summary step ("Zusammenfassung", 2026-08-16 — a player
    picking e.g. "Halb-Ork (Barbar)" saw no indication anywhere of what that
    choice actually does) show the real rules text instead of just the bare
    catalog name."""
    choices = _favored_class_bonus_race_choices(db, favored_root_id, race_id)
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
    choices = _favored_class_bonus_race_choices(db, favored_root_id, race_id)
    return {choice.name: FAVORED_CLASS_BONUS_SHORT_LABELS.get(choice.id, choice.name) for choice in choices}


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
            }
        )
    return result


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


def _build_activatable_spells(db: Session, character: Character) -> list[dict]:
    """Known spells flagged `is_persistent_effect` (roadmap slice 5) — the
    subset a player can activate as a tracked `CharacterEffect` via
    `POST .../effects`. Kept separate from `spellsKnown`/`spellbook` (cast/
    prepare tracking, an unrelated concern) rather than adding a field to
    those existing shapes. Empty for every character today since no spell
    is seeded with the flag set yet — same "wiring ready, no content yet"
    state `BaseCondition`/`EFFECT_HANDLERS` started in."""
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
            description = f"{max(0, remaining)} von {total} Runden heute übrig"
        results.append({"key": str(ability.id), "name": ability.name, "description": description})
    return results


def _build_actions(
    db: Session, character: Character, granted_ability_ids: Counter[UUID], gear: list[dict]
) -> list[dict]:
    """Aktionen panel (roadmap slice 6, thin cut) — only the subset of
    already-activatable data this character has: persistent-effect spells
    known, persistent-effect class abilities granted (self/both scope only —
    `externalClassAbilities` represents what *other* characters can receive
    from this one, not this character's own action), persistent-effect feats
    (2026-08-16, e.g. Heftiger Angriff), and activatable gear. No action-cost
    data exists anywhere in the schema, so `tag` is always `None` rather than
    a guessed value; no usable-now/legality filtering either (a thick-pass
    follow-up) — every activatable-flagged entry is listed, with remaining
    charges/uses folded honestly into its description text instead of
    hidden.

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
        actions += [
            {
                "id": f"ability-{ability.id}",
                "icon": "⚔️",
                "name": ability.name,
                "tag": None,
                "description": ability.description,
                "sourceType": "class_ability",
                "sourceId": str(ability.id),
            }
            for ability in abilities
        ]

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
                "incubationRemaining": effect.incubation_remaining,
                "durationRemaining": effect.duration_remaining,
                "frequencyRounds": effect.frequency_rounds,
                "nextCheckIn": effect.next_check_in,
                "successesCurrent": effect.successes_current,
                "successesRequired": effect.successes_required,
                "dailyLimitRemaining": max(0, remaining) if remaining is not None else None,
                "dailyLimitTotal": DAILY_LIMITS[effect.source_id](context) if remaining is not None else None,
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
    bows), also not modeled. `gear_entries` (this module's own already-built
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
    explicitly a *melee* attack/damage trade-off, GRW S. 124)."""
    gear_entries_by_item_id = {entry["id"]: entry for entry in gear_entries}
    results = []
    for slot_key, hand_label in _WEAPON_HAND_LABELS.items():
        gear_row = gear_by_slot.get(slot_key)
        item = items.get(gear_row.item_id) if gear_row is not None else None
        if item is None or item.category != "weapon":
            continue

        is_ranged = item.weapon_range is not None
        power_attack = (
            None if is_ranged else _power_attack_effect(bab, context, item.hands, slot_key == "nebenwaffe")
        )
        power_attack_penalty = power_attack[0] if power_attack is not None else 0
        power_attack_damage = power_attack[1] if power_attack is not None else 0

        attack_ability_mod = dex_mod if is_ranged else str_mod + melee_attack_bonus
        attack_bonuses = _iterative_attack_bonuses(
            bab, bab + attack_ability_mod + gear_row.enhancement + power_attack_penalty
        )

        damage_parts: list[str] = []
        if item.damage_medium:
            damage_str_mod = (
                0 if is_ranged else _weapon_damage_str_mod(str_mod, item.hands, slot_key == "nebenwaffe")
            )
            flat_damage = (
                damage_str_mod + gear_row.enhancement + (0 if is_ranged else melee_damage_bonus) + power_attack_damage
            )
            piece = item.damage_medium + (_fmt(flat_damage) if flat_damage else "")
            if item.damage_type:
                piece += f" {item.damage_type}"
            damage_parts.append(piece)

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
        if power_attack is not None:
            result["note"] = "Heftiger Angriff aktiv"
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
    ignores `context` entirely and is always present once granted."""
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

    ability_ids = sorted(set(race_ability_ids) | set(class_ability_ids), key=str)
    results = []
    for ability_id in ability_ids:
        handler = NATURAL_ATTACK_HANDLERS.get(ability_id)
        if handler is None:
            continue
        attack = handler(context)
        if attack is None:
            continue
        result = {
            "key": f"natural-{ability_id}",
            "hand": "Naturangriff",
            "name": attack.name,
            "attackBonus": "/".join(_fmt(attack_bonus) for _ in range(attack.count)),
            "damage": f"{attack.damage_dice}{_fmt(flat_damage) if flat_damage else ''} {attack.damage_type}",
        }
        if power_attack is not None:
            result["note"] = "Heftiger Angriff aktiv"
        results.append(result)
    return results
