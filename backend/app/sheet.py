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

from collections import Counter
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
    BaseWeaponSpecialAbility,
    Character,
    RaceAbilityGrant,
)
from .routers.characters import _class_def
from .routers.races import race_ability_score_mods
from .rules.equipment_slots import SLOT_CATEGORY, SLOT_DEFINITIONS, SLOT_TO_ITEM_SLOT
from .rules.modifiers import Modifier, ModifierTarget, stack
from .rules.speed import class_speed_bonus, jump_skill_bonus, race_speed
from .rules.progression import ability_mod, effective_ability_scores, max_hit_points
from .rules.weapon_abilities import resolve as resolve_weapon_ability

ABILITY_LABELS = {"ST": "STÄ", "GE": "GES", "KO": "KON", "IN": "INT", "WE": "WEI", "CH": "CHA"}
SAVE_LABELS = {"fort": "Zähigkeit", "ref": "Reflex", "will": "Willen"}
# Which ability modifier each save adds on top of Character.saves' base
# class-progression bonus (`rules/progression.py`'s `class_save_bonus`) —
# that property has no DB access for race/flex-adjusted scores, so the
# ability-mod addition happens here, alongside this module's other
# `effective_ability_scores`-dependent display math.
SAVE_ABILITY = {"fort": "KO", "ref": "GE", "will": "WE"}

# BaseItem.granted_ability's English code -> the sheet/Character's own
# German ability-score key (roadmap.md's "Wondrous-Item-Katalog mit echter
# Attributsboni-Wirkung", decided 2026-08-04).
ABILITY_CODE_TO_KEY = {
    "strength": "ST",
    "dexterity": "GE",
    "constitution": "KO",
    "intelligence": "IN",
    "wisdom": "WE",
    "charisma": "CH",
}


def _gear_ability_bonuses(db: Session, character: Character) -> dict[str, int]:
    """Enhancement bonuses to ability scores from equipped wondrous items
    (e.g. a "Gürtel der großen Konstitution +2" adds 2 to KO while
    equipped) — only the `BaseItem.granted_ability`/`ability_bonus` subset
    is structured this way, see that catalog's docstring for why the rest
    stays freetext. Only *equipped* gear counts (`equipped_slot` set), same
    as `_build_equipment`'s AC logic; `stack()` applied per ability in case
    two equipped items ever grant the same one (same-type bonuses don't
    stack in PF1e)."""
    equipped_item_ids = [g.item_id for g in character.gear if g.equipped_slot]
    if not equipped_item_ids:
        return {}
    items = db.scalars(
        select(BaseItem).where(BaseItem.id.in_(equipped_item_ids), BaseItem.granted_ability.is_not(None))
    ).all()
    modifiers_by_key: dict[str, list[Modifier]] = {}
    for item in items:
        key = ABILITY_CODE_TO_KEY.get(item.granted_ability)
        if key is None:
            continue
        modifiers_by_key.setdefault(key, []).append(
            Modifier(
                source=item.name,
                type="enhancement",
                value=item.ability_bonus or 0,
                target=ModifierTarget.SCORE,
                target_id=key,
            )
        )
    return {key: stack(mods) for key, mods in modifiers_by_key.items()}


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
    for key, bonus in _gear_ability_bonuses(db, character).items():
        effective_scores[key] = effective_scores.get(key, 0) + bonus
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
    armor_class, equipment_slots = _build_equipment(db, character, dex_mod)

    level_counts_by_root_id: dict[UUID, int] = {}
    for lvl in character.levels:
        level_counts_by_root_id[lvl.base_class_id] = level_counts_by_root_id.get(lvl.base_class_id, 0) + 1

    granted_ability_ids = _granted_class_ability_ids(db, character, level_counts_by_root_id)
    base_speed = race_speed(db, character.race_id) or 9
    total_speed = base_speed + class_speed_bonus(granted_ability_ids)

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
        "speed": f"{total_speed} m",
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
            {
                "key": key,
                "label": label,
                "value": _fmt(character.saves[key] + ability_mods[SAVE_ABILITY[key]]),
            }
            for key, label in SAVE_LABELS.items()
        ],
        "combat": [
            {"key": "bab", "label": "Grundangriffsbonus (GAB)", "value": _fmt(bab)},
            {"key": "cmb", "label": "Kampfmanöverbonus (KMB)", "value": _fmt(bab + str_mod)},
            {"key": "cmd", "label": "Kampfmanöverabwehr (KMD)", "value": str(10 + bab + str_mod + dex_mod)},
        ],
        "skills": _build_skills(db, character, level_counts_by_root_id, ability_mods, total_speed),
        "feats": _build_feats(db, character),
        "traits": _described(db, BaseTrait, character.trait_ids),
        "classFeatures": _build_class_features(db, granted_ability_ids),
        "raceAbilities": _build_race_abilities(db, character.race_id),
        "spellsKnown": _build_spell_grades(db, character, "used"),
        "gear": _build_gear(db, character),
        "equipmentSlots": equipment_slots,
        "spellbook": _build_spell_grades(db, character, "prepared"),
        "actions": [],
        "effectsActive": [],
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
            }
            for entry in character.classes
        ],
        "abilityScores": character.ability_scores,
        "feats": [entry["name"] for entry in _build_feats(db, character)],
        "traits": [row["name"] for row in _described(db, BaseTrait, character.trait_ids)],
        "skillRanks": character.skill_ranks,
        "spellsKnown": spells_known,
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


AKROBATIK_SKILL_ID = UUID("61a2cb21-fcda-4a2d-8fb5-8ed12133c648")


def _build_skills(
    db: Session,
    character: Character,
    level_counts_by_root_id: dict[UUID, int],
    ability_mods: dict[str, int],
    total_speed: int,
) -> list[dict]:
    skill_ranks = {UUID(skill_id): ranks for skill_id, ranks in character.skill_ranks.items() if ranks > 0}

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
        entry = {"key": str(skill.id), "label": skill.name, "value": _fmt(ranks + ab_mod + class_bonus)}
        if skill.id == AKROBATIK_SKILL_ID:
            # Springen-specific Volksbonus (rules/speed.py's jump_skill_bonus)
            # — doesn't apply to Akrobatik's other uses (Balancieren,
            # Abrollen, ...), so it's surfaced as a note rather than folded
            # into the displayed value above.
            jump_bonus = jump_skill_bonus(total_speed)
            entry["note"] = (
                f"Sprung (Hoch-/Weitsprung): {_fmt(jump_bonus)} bei {total_speed} m Bewegungsrate "
                "(Volksbonus/-malus von 4 pro volle 3 m über/unter 9 m, gilt nur für Sprünge)"
            )
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

    capped_dex_mod = dex_mod if max_dex_bonus is None else min(dex_mod, max_dex_bonus)
    armor_class = 10 + capped_dex_mod + stack(modifiers)

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

    return armor_class, equipment_slots
