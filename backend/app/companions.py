"""Animal companions as `Character` rows — roadmap slice 10, step 2b.

A companion is an ordinary `Character` (`master_character_id` set, one
`CharacterLevel` per HD of the pseudo class "Tiergefährte"), so the sheet,
effects, HP, gear and print page work unchanged. What makes it a companion
is derived here at read time and never stored:

- **Effective level** (`companion_effective_level`) — the one function every
  caller goes through: the master's track level (`rules/companions.py`'s
  `master_effective_level`, with the slot's own offset), capped at the
  master's character level.
- **Progression** (`BaseCompanionProgression`) for that level: expected HD,
  natural armor and ST/GE bonus, bonus tricks, the class abilities unlocked
  so far (Verbindung, Entrinnen, …).
- **Species** (`BaseCompanionSpeciesStage`): size, natural armor, speeds,
  natural attacks and special abilities of the starting statblock plus the
  4th/7th-level advancement once reached — or +2 GE/+2 KO instead when the
  player chose that (`CharacterCompanion.advancement_choice`).

Entitlements (`BaseCompanionSlotGrant`) hang off granted class abilities,
so an archetype replacing the ability removes the entitlement for free. A
companion whose master lost the entitlement keeps its sheet, flagged
"ohne Anspruch", with its stats taken from the highest progression row its
current HD still matches.

Step 3 adds the choices and the master → companion channel:

- **HD sync** (`sync_companion_hit_dice`, upward only): when the master's
  level-up raises the effective level, the missing HD are appended with
  `choices_pending` set and no HP yet. Never removes HD — the app has no
  level removal, and a companion with more HD than its table row is shown
  as such instead.
- **Open HD** are filled lowest first by the level-up endpoint's companion
  mode (`routers/characters.py`'s `_complete_companion_level`): HP (if still
  open), skill ranks (2 + IN per HD, min. 1; only "Tierfertigkeiten" while
  IN < 3), feats ((HD + 1) // 2; the first may not require GAB +1) and the
  ability increase every 4th HD. A new companion's HD start open too.
- **Channel** (`rules/companions.py`'s `COMPANION_MODIFIER_HANDLERS`/
  `COMPANION_NOTE_HANDLERS`): the companion's context carries the master's
  raw composition (`companion_context_fields`).

Step 4 adds the familiar (track "familiar"): also a `Character`, but with
no levels at all — `_familiar_state` derives everything from its species
statblock, the familiar table for the master's familiar level and the
master himself (`FamiliarDerived`). It gives its master a bonus by species
(`rules/companions.py`'s `FAMILIAR_MASTER_HANDLERS`, fed by
`familiar_species_ids`).

Step 5 stores the tricks an animal companion knows
(`CharacterCompanionTrick`, written by `set_companion_tricks` and validated
by `rules/companions.py`'s `trick_errors`): bonus tricks up to the
progression row's `bonus_tricks`, trained ones up to the IN limit of the
sheet's effective IN. Nothing is deleted when a limit drops — the sheet
flags "zu viele Tricks" instead (`tricks_payload`).
"""

from collections import Counter
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    BaseClass,
    BaseCompanionLevelSource,
    BaseCompanionProgression,
    BaseCompanionProgressionAbility,
    BaseCompanionSlotGrant,
    BaseCompanionSlotSpecies,
    BaseCompanionSpeciesStage,
    BaseCompanionSpeciesStageAbility,
    BaseCompanionTrick,
    BaseCompanionTrickPurpose,
    BaseCompanionTrickPurposeTrick,
    BaseFamiliarProgression,
    BaseFamiliarProgressionAbility,
    BaseRace,
    BaseRaceAbility,
    Character,
    CharacterClass,
    CharacterCompanion,
    CharacterCompanionTrick,
    CharacterLevel,
)
from .rules.companions import (
    FAMILIAR_BASE_SAVES,
    TRACK_LABELS,
    TrackLevel,
    TrickPick,
    TrickPurposeRef,
    is_purpose_trick,
    master_companion_notes,
    master_effective_level,
    purpose_unavailable_reason,
    trick_errors,
    trick_limits,
    trick_unavailable_reason,
)
from .rules.context import CharacterContext
from .rules.favored_class_bonuses import pick_counts as favored_class_bonus_pick_counts
from .rules.feat_slots import base_feat_count
from .rules.feats import NaturalWeaponFacts
from .rules.modifiers import Modifier, ModifierTarget, NaturalAttack
from .rules.secondary_class import secondary_effective_level

# Speed key (`BaseCompanionSpeciesStage.speeds`) -> movement-mode target.
_SPEED_TARGETS = {
    "climb": ModifierTarget.CLIMB_SPEED,
    "swim": ModifierTarget.SWIM_SPEED,
    "fly": ModifierTarget.FLY_SPEED,
    "burrow": ModifierTarget.BURROW_SPEED,
}


@dataclass
class CompanionSlot:
    """One entitlement of a master: `level` is the effective level a
    companion in this slot has right now."""

    track: str
    slot_key: str
    level: int
    track_level: TrackLevel
    species: list[BaseRace]
    companion: Character | None


@dataclass
class CompanionState:
    master: Character
    link: CharacterCompanion
    effective_level: int | None
    track_level: TrackLevel | None
    orphaned: bool
    progression: BaseCompanionProgression | None
    size: str
    land_speed: int | None
    modifiers: list[Modifier] = field(default_factory=list)
    natural_attacks: list[NaturalAttack] = field(default_factory=list)
    species_ability_ids: set[UUID] = field(default_factory=set)
    progression_ability_ids: Counter[UUID] = field(default_factory=Counter)
    advanced: bool = False
    master_context: CharacterContext | None = None
    # Set only for a familiar (step 4): everything it takes from its master.
    familiar: "FamiliarDerived | None" = None
    # The combined natural armor bonus (species, advancement, table).
    natural_armor: int = 0
    # How many natural attacks the species' current statblock lists,
    # alternatives not counted (`CharacterContext.natural_attack_count`).
    natural_attack_count: int = 0


@dataclass
class FamiliarDerived:
    """A familiar's values taken from its master (PRD Magier, "Die Werte des
    Vertrauten"): it has no `CharacterLevel` rows of its own.

    - `level`: the master's character level ("gilt die Stufe des Meisters")
    - `bab`: the master's GAB
    - `base_saves`: per save the better of the familiar's (REF +2, WIL +0,
      ZÄH +2) and the master's base save
    - `hp_max`: half the master's maximum HP, rounded down
    - `skill_rank_details`: the master's ranks (a familiar's own single
      species rank isn't modeled — the master's are at least as high in
      every skill the master trained)
    - `feats`: the species' own feats (`[{feat_id, chosen_skill_id}]`)"""

    level: int
    bab: int
    base_saves: dict[str, int]
    hp_max: int
    skill_rank_details: list[dict]
    feats: list[dict]


def master_context(db: Session, master: Character) -> CharacterContext:
    """The raw composition `master_effective_level` reads — the same
    granted-ability resolution `sheet.py` does for the master's own sheet,
    Sekundärklasse included."""
    from .rules.secondary_class import secondary_granted_ability_ids_and_levels
    from .sheet import granted_class_ability_ids_with_roots

    level_counts: dict[UUID, int] = {}
    for level in master.levels:
        level_counts[level.base_class_id] = level_counts.get(level.base_class_id, 0) + 1
    granted, roots = granted_class_ability_ids_with_roots(db, master, level_counts)
    secondary_ids, secondary_levels = secondary_granted_ability_ids_and_levels(db, master)
    granted.update(secondary_ids)
    level_counts.update(secondary_levels)
    if master.secondary_base_class_id is not None:
        for ability_id in secondary_ids:
            roots[ability_id] = roots.get(ability_id, frozenset()) | {master.secondary_base_class_id}
    return CharacterContext(
        character_level=master.level,
        granted_ability_ids=granted,
        granting_root_ids_by_ability=roots,
        feat_ids=frozenset(master.feat_ids),
        level_counts_by_root_id=level_counts,
        favored_class_bonus_pick_counts=favored_class_bonus_pick_counts(master),
    )


def master_class_options(master: Character) -> dict[str, tuple[str, ...]]:
    """The master's class option picks by group key (the Waldläufer's
    "enemy"/"terrain", ...), for `CharacterContext.master_class_options`."""
    options: dict[str, list[str]] = {}
    for option in master.class_options:
        options.setdefault(option.group_key, []).append(option.choice)
    return {key: tuple(choices) for key, choices in options.items()}


def companion_context_fields(state: "CompanionState") -> dict:
    """The `CharacterContext` fields a companion's sheet sets from its
    master and species (`sheet.py`'s `build_character_sheet`)."""
    master_ctx = state.master_context
    return {
        "natural_attack_count": state.natural_attack_count,
        "master_granted_ability_ids": master_ctx.granted_ability_ids if master_ctx else Counter(),
        "master_favored_class_bonus_pick_counts": (
            master_ctx.favored_class_bonus_pick_counts if master_ctx else Counter()
        ),
        "master_class_options": master_class_options(state.master),
        "master_level_counts_by_root_id": master_ctx.level_counts_by_root_id if master_ctx else {},
        "companion_effective_level": state.effective_level,
    }


def _class_names(db: Session) -> dict[UUID, str]:
    return {row.id: row.name for row in db.scalars(select(BaseClass).where(BaseClass.arch_class_of.is_(None)))}


def _master_size(db: Session, master: Character) -> str:
    from .routers.races import effective_race_ability_ids
    from .rules.size import base_size

    return base_size(
        effective_race_ability_ids(db, master.race_id, {choice.ability_id for choice in master.racial_choices})
    )


def companion_slots(db: Session, master: Character, context: CharacterContext | None = None) -> list[CompanionSlot]:
    """Every entitlement `master` currently has, with the species it allows
    (filtered by the master's size and the slot's level) and the companion
    already filling it, if any."""
    context = context or master_context(db, master)
    triggered = [
        grant
        for grant in db.scalars(select(BaseCompanionSlotGrant)).all()
        if context.granted_ability_ids.get(grant.class_ability_id, 0) > 0
    ]
    if not triggered:
        return []
    sources = db.scalars(select(BaseCompanionLevelSource)).all()
    class_names = _class_names(db)
    master_size = _master_size(db, master)
    links = {(link.track, link.slot_key): link for link in db.scalars(
        select(CharacterCompanion).where(CharacterCompanion.master_character_id == master.id)
    )}

    slots: dict[tuple[str, str], CompanionSlot] = {}
    for grant in triggered:
        track_level = master_effective_level(grant.track, sources, context, class_names)
        if track_level is None:
            continue
        level = min(
            secondary_effective_level(
                track_level.level, offset=grant.level_offset, divisor=grant.divisor, minimum=grant.minimum
            ),
            context.character_level,
        )
        key = (grant.track, grant.slot_key)
        slot = slots.get(key)
        if slot is None:
            link = links.get((grant.track, grant.slot_key))
            slot = slots[key] = CompanionSlot(
                track=grant.track,
                slot_key=grant.slot_key,
                level=level,
                track_level=track_level,
                species=[],
                companion=db.get(Character, link.companion_character_id) if link else None,
            )
        slot.level = max(slot.level, level)
        for allowed in db.scalars(select(BaseCompanionSlotSpecies).where(BaseCompanionSlotSpecies.slot_grant_id == grant.id)):
            if allowed.master_sizes and master_size not in allowed.master_sizes:
                continue
            if allowed.min_level is not None and level < allowed.min_level:
                continue
            race = db.get(BaseRace, allowed.race_id)
            if race is not None and race not in slot.species:
                slot.species.append(race)
    for slot in slots.values():
        slot.species.sort(key=lambda race: race.name)
    return [slot for slot in slots.values() if slot.level >= 1]


def companion_effective_level(
    db: Session, master: Character, link: CharacterCompanion, context: CharacterContext | None = None
) -> tuple[int | None, TrackLevel | None]:
    """The companion's effective level ("effektive Druidenstufe") — `None`
    when the master no longer has the entitlement. The single function the
    sheet, creation, the HD sync and the level-up all use."""
    for slot in companion_slots(db, master, context):
        if slot.track == link.track and slot.slot_key == link.slot_key:
            return slot.level, slot.track_level
    return None, None


def progression_row(db: Session, level: int) -> BaseCompanionProgression | None:
    return db.scalar(select(BaseCompanionProgression).where(BaseCompanionProgression.level == level))


def _stages(db: Session, race_id: UUID) -> list[BaseCompanionSpeciesStage]:
    return list(
        db.scalars(
            select(BaseCompanionSpeciesStage)
            .where(BaseCompanionSpeciesStage.race_id == race_id)
            .order_by(BaseCompanionSpeciesStage.level)
        )
    )


def _natural_attacks(rows: list[dict], size: str) -> list[NaturalAttack]:
    return [
        NaturalAttack(
            name=row["name"],
            count=row["count"],
            damage_dice=row["dice"] or "",
            damage_type=row["damage_type"] or "",
            base_size=size,
            is_secondary=row["secondary"],
            note=row.get("note"),
            alternative=row.get("alternative", False),
        )
        for row in rows
    ]


def _speed_modifiers(stage: BaseCompanionSpeciesStage | None) -> list[Modifier]:
    """The species' climb/swim/fly/burrow speeds (land speed is read
    directly as the sheet's base speed)."""
    speeds = (stage.speeds or {}) if stage else {}
    return [
        Modifier(
            source="Tierart",
            type="base",
            value=speeds[key],
            target=target,
            detail=stage.fly_maneuverability if key == "fly" else None,
        )
        for key, target in _SPEED_TARGETS.items()
        if speeds.get(key)
    ]


def companion_state(db: Session, companion: Character) -> CompanionState | None:
    """Everything the companion's sheet derives from its master, progression
    and species — `None` for a character that isn't a companion."""
    if companion.master_character_id is None:
        return None
    link = db.scalar(select(CharacterCompanion).where(CharacterCompanion.companion_character_id == companion.id))
    master = db.get(Character, companion.master_character_id)
    if link is None or master is None:
        return None
    master_ctx = master_context(db, master)
    effective_level, track_level = companion_effective_level(db, master, link, master_ctx)
    if link.track == "familiar":
        return _familiar_state(db, companion, master, link, master_ctx, effective_level, track_level)
    orphaned = effective_level is None
    if orphaned:
        # Highest progression row the companion's current HD still matches.
        effective_level_for_stats = db.scalar(
            select(BaseCompanionProgression.level)
            .where(BaseCompanionProgression.hit_dice <= max(1, companion.level))
            .order_by(BaseCompanionProgression.level.desc())
        ) or 1
    else:
        effective_level_for_stats = effective_level
    progression = progression_row(db, effective_level_for_stats)

    stages = _stages(db, companion.race_id)
    base = stages[0] if stages else None
    advancements = [s for s in stages[1:] if s.level <= effective_level_for_stats]
    advanced = link.advancement_choice == "species" and bool(advancements)
    reached = ([base] if base else []) + (advancements if link.advancement_choice == "species" else [])

    size = base.size if base else "Mittelgroß"
    natural_armor = 0
    attacks: list[dict] = []
    deltas: list[tuple[str, str, int]] = []
    species_ability_ids: set[UUID] = set()
    for stage in reached:
        if stage.size:
            size = stage.size
        natural_armor += stage.natural_armor
        if stage.natural_attacks is not None:
            attacks = stage.natural_attacks
        if stage is not base:
            deltas += [(f"Aufstieg ({stage.level}. Stufe)", ability, value) for ability, value in stage.ability_scores.items()]
        species_ability_ids.update(
            db.scalars(
                select(BaseCompanionSpeciesStageAbility.ability_id).where(
                    BaseCompanionSpeciesStageAbility.stage_id == stage.id
                )
            )
        )
    if link.advancement_choice == "dex_con" and advancements:
        deltas += [("Aufstieg (GE/KO statt Tierart)", "GE", 2), ("Aufstieg (GE/KO statt Tierart)", "KO", 2)]

    modifiers: list[Modifier] = []
    if progression is not None:
        natural_armor += progression.natural_armor
        if progression.str_dex_bonus:
            deltas += [("Tiergefährte (ST/GE)", "ST", progression.str_dex_bonus), ("Tiergefährte (ST/GE)", "GE", progression.str_dex_bonus)]
    modifiers += [
        Modifier(source=source, type="untyped", value=value, target=ModifierTarget.SCORE, target_id=ability)
        for source, ability, value in deltas
    ]
    if natural_armor:
        # One combined bonus: the species' own, its advancement and the
        # table's "zusätzlich" natural armor all add up.
        modifiers.append(Modifier(source="Natürliche Rüstung", type="natural", value=natural_armor, target=ModifierTarget.AC))
    speeds = (base.speeds or {}) if base else {}
    modifiers += _speed_modifiers(base)

    progression_ability_ids: Counter[UUID] = Counter(
        db.scalars(
            select(BaseCompanionProgressionAbility.ability_id).where(
                BaseCompanionProgressionAbility.level <= effective_level_for_stats
            )
        )
    )
    return CompanionState(
        master=master,
        link=link,
        effective_level=effective_level,
        track_level=track_level,
        orphaned=orphaned,
        progression=progression,
        size=size,
        land_speed=speeds.get("land"),
        modifiers=modifiers,
        natural_attacks=_natural_attacks(attacks, size),
        species_ability_ids=species_ability_ids,
        progression_ability_ids=progression_ability_ids,
        advanced=advanced,
        master_context=master_ctx,
        natural_armor=natural_armor,
        natural_attack_count=sum(row["count"] for row in attacks if not row.get("alternative", False)),
    )


def _familiar_state(
    db: Session,
    familiar: Character,
    master: Character,
    link: CharacterCompanion,
    master_ctx: CharacterContext,
    effective_level: int | None,
    track_level: TrackLevel | None,
) -> CompanionState:
    """A familiar's derived sheet inputs (step 4): its species statblock,
    the familiar table row for the master's familiar level (natural armor
    bonus, IN, abilities) and the values it takes from its master
    (`FamiliarDerived`). An orphaned familiar keeps the 1st-level row."""
    from .sheet import build_character_sheet

    level_for_stats = min(effective_level or 1, 20)
    row = db.scalar(select(BaseFamiliarProgression).where(BaseFamiliarProgression.level == level_for_stats))
    stage = _stages(db, familiar.race_id)[0]
    modifiers = _speed_modifiers(stage)
    natural_armor = stage.natural_armor + (row.natural_armor if row else 0)
    if natural_armor:
        modifiers.append(Modifier(source="Natürliche Rüstung", type="natural", value=natural_armor, target=ModifierTarget.AC))
    if row is not None and row.intelligence != familiar.ability_score_in:
        modifiers.append(
            Modifier(
                source="Vertrauter (IN laut Tabelle)",
                type="untyped",
                value=row.intelligence - familiar.ability_score_in,
                target=ModifierTarget.SCORE,
                target_id="IN",
            )
        )
    modifiers += [
        Modifier(source="Volksmodifikator", type="racial", value=value, target=ModifierTarget.SKILL, target_id=skill_id)
        for skill_id, value in (stage.skill_modifiers or {}).items()
    ]
    species_ability_ids = set(
        db.scalars(
            select(BaseCompanionSpeciesStageAbility.ability_id).where(BaseCompanionSpeciesStageAbility.stage_id == stage.id)
        )
    )
    progression_ability_ids: Counter[UUID] = Counter(
        db.scalars(
            select(BaseFamiliarProgressionAbility.ability_id).where(
                BaseFamiliarProgressionAbility.level <= level_for_stats
            )
        )
    )
    master_saves = master.saves
    derived = FamiliarDerived(
        level=master.level,
        bab=master.bab,
        base_saves={key: max(FAMILIAR_BASE_SAVES[key], master_saves[key]) for key in FAMILIAR_BASE_SAVES},
        hp_max=build_character_sheet(master, db)["hp"]["max"] // 2,
        skill_rank_details=master.skill_rank_details,
        feats=stage.feats or [],
    )
    attacks = stage.natural_attacks or []
    return CompanionState(
        master=master,
        link=link,
        effective_level=effective_level,
        track_level=track_level,
        orphaned=effective_level is None,
        progression=None,
        size=stage.size or "Mittelgroß",
        land_speed=(stage.speeds or {}).get("land"),
        modifiers=modifiers,
        natural_attacks=_natural_attacks(attacks, stage.size or "Mittelgroß"),
        species_ability_ids=species_ability_ids,
        progression_ability_ids=progression_ability_ids,
        master_context=master_ctx,
        familiar=derived,
        natural_armor=natural_armor,
        natural_attack_count=sum(row["count"] for row in attacks if not row.get("alternative", False)),
    )


def familiar_species_ids(db: Session, master: Character) -> frozenset[UUID]:
    """The species of `master`'s familiars (`CharacterContext.familiar_species_ids`)."""
    return frozenset(
        db.scalars(
            select(Character.race_id)
            .join(CharacterCompanion, CharacterCompanion.companion_character_id == Character.id)
            .where(CharacterCompanion.master_character_id == master.id, CharacterCompanion.track == "familiar")
        )
    )


def companion_payload(state: CompanionState, companion: Character, context: CharacterContext | None = None) -> dict:
    """The companion sheet's own section: who the master is, where the level
    comes from, HD expected vs. present, bonus tricks."""
    track_level = state.track_level
    return {
        "master": {"id": str(state.master.id), "name": state.master.name},
        "track": state.link.track,
        "trackLabel": TRACK_LABELS[state.link.track],
        "slotKey": state.link.slot_key,
        "effectiveLevel": state.effective_level,
        "breakdown": (
            [{"label": c.label, "value": c.value, "detail": c.detail} for c in track_level.contributions]
            if track_level
            else []
        ),
        "orphaned": state.orphaned,
        "hitDice": state.familiar.level if state.familiar else companion.level,
        "expectedHitDice": state.progression.hit_dice if state.progression else None,
        "bonusTricks": state.progression.bonus_tricks if state.progression else 0,
        "advancementChoice": state.link.advancement_choice,
        "advanced": state.advanced,
        # Open HD (step 3): choices still to make in the level-up wizard's
        # companion mode, and how many of those still need their HP roll.
        "openHitDice": len(pending_levels(companion)),
        "openHitPoints": sum(1 for level in pending_levels(companion) if level.hit_points is None),
        # What the master shares that the sheet only describes (Waldläufer's
        # Erzfeinde, Paladin mount extras).
        "masterNotes": master_companion_notes(context) if context is not None else [],
    }


def companion_class(db: Session) -> BaseClass:
    return db.scalar(select(BaseClass).where(BaseClass.is_companion_class.is_(True)))


def _check_companion_hit_points(db: Session, slot: CompanionSlot, pseudo_class: BaseClass, hit_points: list[int]) -> None:
    """One W8 value per HD the slot's effective level has."""
    progression = progression_row(db, slot.level)
    if len(hit_points) != progression.hit_dice:
        raise HTTPException(
            status_code=422, detail=f"Expected {progression.hit_dice} hit point values (one per HD), got {len(hit_points)}"
        )
    if any(not 1 <= value <= pseudo_class.hit_dice for value in hit_points):
        raise HTTPException(status_code=422, detail=f"Each hit point value must be between 1 and {pseudo_class.hit_dice}")


def create_companion(
    db: Session,
    master: Character,
    *,
    track: str = "animal_companion",
    slot_key: str,
    species_id: UUID,
    name: str,
    hit_points: list[int],
    advancement_choice: str,
) -> Character:
    """Creates the companion `Character` for one of `master`'s free slots:
    species' starting scores, one pseudo-class level per HD of the current
    effective level, the given HP per HD (W8, the first one not maxed).
    Every HD starts with its choices open (`choices_pending`) — feats,
    skill ranks and ability increases are made in the level-up wizard's
    companion mode afterwards. A familiar (step 4) gets no levels and no
    HP values at all: everything it has comes from its master."""
    if master.master_character_id is not None:
        raise HTTPException(status_code=422, detail="A companion can't have companions of its own")
    slot = next((s for s in companion_slots(db, master) if s.track == track and s.slot_key == slot_key), None)
    if slot is None:
        raise HTTPException(status_code=422, detail=f"No {track} entitlement '{slot_key}'")
    if slot.companion is not None:
        raise HTTPException(status_code=422, detail=f"Slot '{slot_key}' already has a companion")
    species = next((race for race in slot.species if race.id == species_id), None)
    if species is None:
        raise HTTPException(status_code=422, detail="This species isn't allowed for this companion")
    pseudo_class = companion_class(db)
    if track == "familiar":
        if hit_points:
            raise HTTPException(status_code=422, detail="A familiar has no hit dice of its own (half its master's HP)")
    else:
        _check_companion_hit_points(db, slot, pseudo_class, hit_points)
    base = _stages(db, species.id)[0]

    companion = Character(
        name=name,
        user_id=master.user_id,
        race_id=species.id,
        ability_score_st=base.ability_scores["ST"],
        ability_score_ge=base.ability_scores["GE"],
        ability_score_ko=base.ability_scores["KO"],
        ability_score_in=base.ability_scores["IN"],
        ability_score_we=base.ability_scores["WE"],
        ability_score_ch=base.ability_scores["CH"],
        point_budget=None,
        master_character_id=master.id,
        damage_taken=0,
    )
    for hd, value in enumerate(hit_points, start=1):
        companion.levels.append(
            CharacterLevel(level=hd, base_class_id=pseudo_class.id, hit_points=value, choices_pending=True)
        )
    if track != "familiar":
        companion.class_memberships.append(CharacterClass(base_class_id=pseudo_class.id, is_favored=False))
    db.add(companion)
    db.flush()
    db.add(
        CharacterCompanion(
            master_character_id=master.id,
            companion_character_id=companion.id,
            track=slot.track,
            slot_key=slot_key,
            advancement_choice=advancement_choice,
        )
    )
    db.commit()
    db.refresh(companion)
    return companion


def slots_payload(db: Session, slots: list[CompanionSlot]) -> list[dict]:
    """The master sheet's view of its entitlements; `hitDice` is how many
    HP values creating a companion for this slot needs right now."""
    return [
        {
            "track": slot.track,
            "slotKey": slot.slot_key,
            "level": slot.level,
            # A familiar has no HD of its own: creating one takes no HP values.
            "hitDice": (
                0
                if slot.track == "familiar"
                else progression.hit_dice if (progression := progression_row(db, slot.level)) else None
            ),
            "species": [{"id": str(race.id), "name": race.name} for race in slot.species],
            "companion": {"id": str(slot.companion.id), "name": slot.companion.name} if slot.companion else None,
        }
        for slot in slots
    ]


def pending_levels(companion: Character) -> list[CharacterLevel]:
    """The companion's HD whose choices are still open, lowest first."""
    return sorted((level for level in companion.levels if level.choices_pending), key=lambda level: level.level)


def sync_companion_hit_dice(db: Session, master: Character) -> None:
    """Upward-only HD sync (roadmap slice 10 step 3): every companion of
    `master` gets the HD its current effective level's table row has and
    it doesn't — appended with open choices and no HP yet. Runs inside the
    master's own level-up transaction (`routers/characters.py`), so the
    caller commits."""
    pseudo_class = companion_class(db)
    for slot in companion_slots(db, master):
        if slot.companion is None:
            continue
        progression = progression_row(db, slot.level)
        if progression is None:
            continue
        companion = slot.companion
        for hd in range(companion.level + 1, progression.hit_dice + 1):
            companion.levels.append(
                CharacterLevel(level=hd, base_class_id=pseudo_class.id, hit_points=None, choices_pending=True)
            )


# "Tiergefährten mit einer Intelligenz von 3 oder mehr können Ränge in
# beliebigen Fertigkeiten erwerben" — below that, only the companion class's
# `allowed_skill_ids` ("Tierfertigkeiten").
ANY_SKILL_MIN_INTELLIGENCE = 3


def allowed_skill_ids(companion_class_row: BaseClass, intelligence: int) -> set[UUID] | None:
    """The skills a companion may put ranks into — `None` means any skill."""
    if intelligence >= ANY_SKILL_MIN_INTELLIGENCE or not companion_class_row.allowed_skill_ids:
        return None
    return {UUID(skill_id) for skill_id in companion_class_row.allowed_skill_ids}


def is_first_feat_level(hit_die: int) -> bool:
    """Whether completing HD `hit_die` grants the companion's first feat —
    the one that may not require GAB +1 ("Außerdem dürfen Tiergefährten
    ein Talent mit der Vorraussetzung eines Grund-Angriffsbonus von +1 (oder
    besser) nicht als erstes Talent wählen")."""
    return base_feat_count(hit_die - 1) == 0 and base_feat_count(hit_die) > 0


def natural_weapon_facts(db: Session, character: Character) -> NaturalWeaponFacts:
    """Natural armor and natural attacks, for the monster feats'
    prerequisites and Verbesserter Natürlicher Angriff's sub-choice: a
    companion's species statblock, or a PC's always-present racial natural
    attacks (an attack only some state unlocks — a rage power's claws —
    doesn't count; PCs have no natural armor source modeled here)."""
    state = companion_state(db, character)
    if state is not None:
        return NaturalWeaponFacts(
            natural_armor=state.natural_armor,
            natural_attack_names=tuple(dict.fromkeys(attack.name for attack in state.natural_attacks)),
            natural_attack_count=state.natural_attack_count,
        )
    from .routers.races import effective_race_ability_ids
    from .rules.handlers import NATURAL_ATTACK_HANDLERS

    race_ability_ids = effective_race_ability_ids(
        db, character.race_id, {choice.ability_id for choice in character.racial_choices}
    )
    attacks = [
        attack
        for ability_id in race_ability_ids
        if (handler := NATURAL_ATTACK_HANDLERS.get(ability_id)) is not None
        and (attack := handler(CharacterContext())) is not None
    ]
    return NaturalWeaponFacts(
        natural_attack_names=tuple(dict.fromkeys(attack.name for attack in attacks)),
        natural_attack_count=sum(attack.count for attack in attacks if not attack.alternative),
    )


def companion_intelligence(db: Session, companion: Character) -> int:
    """The IN the companion's sheet shows (species, ability increases,
    master → companion bonuses such as the Paladin mount's "IN mind. 6") —
    decides whether any skill may get ranks."""
    from .sheet import build_character_sheet

    sheet = build_character_sheet(companion, db)
    return next(ability["score"] for ability in sheet["abilities"] if ability["key"] == "IN")


# ---- tricks (step 5) ----


def trick_catalog(db: Session) -> tuple[dict[UUID, BaseCompanionTrick], dict[UUID, TrickPurposeRef]]:
    tricks = {trick.id: trick for trick in db.scalars(select(BaseCompanionTrick).order_by(BaseCompanionTrick.name))}
    trick_ids_by_purpose: dict[UUID, set[UUID]] = {}
    for row in db.scalars(select(BaseCompanionTrickPurposeTrick)):
        trick_ids_by_purpose.setdefault(row.purpose_id, set()).add(row.trick_id)
    purposes = {
        purpose.id: TrickPurposeRef(purpose.id, purpose.name, frozenset(trick_ids_by_purpose.get(purpose.id, ())))
        for purpose in db.scalars(select(BaseCompanionTrickPurpose))
    }
    return tricks, purposes


def _required_ability_names(db: Session, tricks: dict[UUID, BaseCompanionTrick]) -> dict[UUID, str]:
    ids = {trick.required_ability_id for trick in tricks.values() if trick.required_ability_id}
    if not ids:
        return {}
    return {row.id: row.name for row in db.scalars(select(BaseRaceAbility).where(BaseRaceAbility.id.in_(ids)))}


def _trick_state(db: Session, companion: Character) -> CompanionState:
    """The companion's state, or 422 for anything that has no tricks
    (a PC, a familiar)."""
    state = companion_state(db, companion)
    if state is None or state.link.track == "familiar":
        raise HTTPException(status_code=422, detail="Only animal companions and mounts know tricks")
    return state


def _stored_purpose_id(companion: Character) -> UUID | None:
    return next((pick.purpose_id for pick in companion.companion_tricks if pick.purpose_id), None)


def tricks_payload(db: Session, state: CompanionState, companion: Character, intelligence: int) -> dict:
    """The sheet's trick section: known tricks with their pool and training,
    slots used per pool and whether a pool is over its limit."""
    tricks, purposes = trick_catalog(db)
    purpose_id = _stored_purpose_id(companion)
    bonus_max = state.progression.bonus_tricks if state.progression else 0
    picks = [TrickPick(pick.trick_id, pick.source) for pick in companion.companion_tricks]
    limits = trick_limits(picks, tricks, bonus_max, intelligence)
    return {
        "tricks": [
            {
                "id": str(pick.trick_id),
                "name": tricks[pick.trick_id].name,
                "dc": tricks[pick.trick_id].dc,
                "cost": tricks[pick.trick_id].cost,
                "description": tricks[pick.trick_id].description,
                "source": pick.source,
                "purposeName": purposes[pick.purpose_id].name if pick.purpose_id else None,
            }
            for pick in sorted(companion.companion_tricks, key=lambda pick: tricks[pick.trick_id].name)
        ],
        "trickPurpose": (
            {"id": str(purpose_id), "name": purposes[purpose_id].name} if purpose_id else None
        ),
        "trickLimits": {
            "bonus": {"used": limits.bonus_used, "max": limits.bonus_max},
            "trained": {"used": limits.trained_used, "max": limits.trained_max},
            "intelligence": intelligence,
            "overLimit": limits.over_limit,
        },
    }


def trick_options_payload(db: Session, companion: Character | None) -> dict:
    """`GET /api/companion-tricks`: every trick and training, and — for a
    given companion — whether it can learn each (species abilities, IN)."""
    tricks, purposes = trick_catalog(db)
    ability_names = _required_ability_names(db, tricks)
    state = _trick_state(db, companion) if companion is not None else None
    intelligence = companion_intelligence(db, companion) if companion is not None else None
    purpose_rows = {row.id: row for row in db.scalars(select(BaseCompanionTrickPurpose))}

    def trick_reason(trick: BaseCompanionTrick) -> str | None:
        if state is None:
            return None
        return trick_unavailable_reason(trick, state.species_ability_ids, ability_names)

    def purpose_reason(purpose: TrickPurposeRef) -> str | None:
        if state is None:
            return None
        return purpose_unavailable_reason(purpose, tricks, state.species_ability_ids, ability_names, intelligence)

    return {
        "tricks": [
            {
                "id": str(trick.id),
                "name": trick.name,
                "dc": trick.dc,
                "cost": trick.cost,
                "description": trick.description,
                "variantOfId": str(trick.variant_of_id) if trick.variant_of_id else None,
                "requiredAbility": ability_names.get(trick.required_ability_id) if trick.required_ability_id else None,
                "unavailableReason": trick_reason(trick),
            }
            for trick in tricks.values()
        ],
        "purposes": [
            {
                "id": str(purpose.id),
                "name": purpose.name,
                "dc": purpose_rows[purpose.id].dc,
                "weeks": purpose_rows[purpose.id].weeks,
                "description": purpose_rows[purpose.id].description,
                "trickIds": sorted(str(trick_id) for trick_id in purpose.trick_ids),
                "unavailableReason": purpose_reason(purpose),
            }
            for purpose in sorted(purposes.values(), key=lambda purpose: purpose.name)
        ],
    }


def set_companion_tricks(
    db: Session, companion: Character, purpose_id: UUID | None, picks: list[TrickPick]
) -> None:
    """Replaces the companion's full trick set (`PUT …/tricks`), after
    `trick_errors` found nothing wrong. Each pick that is one of the
    training's tricks is stored with its `purpose_id`. The caller commits."""
    state = _trick_state(db, companion)
    tricks, purposes = trick_catalog(db)
    if purpose_id is not None and purpose_id not in purposes:
        raise HTTPException(status_code=422, detail="Unbekannte Aufgabe")
    purpose = purposes.get(purpose_id) if purpose_id else None
    errors = trick_errors(
        picks,
        purpose,
        tricks,
        state.species_ability_ids,
        _required_ability_names(db, tricks),
        state.progression.bonus_tricks if state.progression else 0,
        companion_intelligence(db, companion),
    )
    if errors:
        raise HTTPException(status_code=422, detail=" ".join(errors))
    companion.companion_tricks.clear()
    db.flush()
    companion.companion_tricks.extend(
        CharacterCompanionTrick(
            trick_id=pick.trick_id,
            source=pick.source,
            purpose_id=purpose.id if is_purpose_trick(pick.trick_id, purpose, tricks) else None,
        )
        for pick in picks
    )
