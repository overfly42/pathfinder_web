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

Not yet (step 3): HD sync when the master levels up, feat/skill/ability-
increase choices, the companion level-up mode, the master→companion channel.
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
    BaseRace,
    Character,
    CharacterClass,
    CharacterCompanion,
    CharacterLevel,
)
from .rules.companions import TRACK_LABELS, TrackLevel, master_effective_level
from .rules.context import CharacterContext
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
    )


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
    links = {link.slot_key: link for link in db.scalars(
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
            link = links.get(grant.slot_key)
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


def companion_effective_level(db: Session, master: Character, link: CharacterCompanion) -> tuple[int | None, TrackLevel | None]:
    """The companion's effective level ("effektive Druidenstufe") — `None`
    when the master no longer has the entitlement. The single function the
    sheet, creation (and later sync/level-up) all use."""
    for slot in companion_slots(db, master):
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


def companion_state(db: Session, companion: Character) -> CompanionState | None:
    """Everything the companion's sheet derives from its master, progression
    and species — `None` for a character that isn't a companion."""
    if companion.master_character_id is None:
        return None
    link = db.scalar(select(CharacterCompanion).where(CharacterCompanion.companion_character_id == companion.id))
    master = db.get(Character, companion.master_character_id)
    if link is None or master is None:
        return None
    effective_level, track_level = companion_effective_level(db, master, link)
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
    for key, target in _SPEED_TARGETS.items():
        if speeds.get(key):
            modifiers.append(
                Modifier(
                    source="Tierart",
                    type="base",
                    value=speeds[key],
                    target=target,
                    detail=base.fly_maneuverability if key == "fly" else None,
                )
            )

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
    )


def companion_payload(state: CompanionState, companion: Character) -> dict:
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
        "hitDice": companion.level,
        "expectedHitDice": state.progression.hit_dice if state.progression else None,
        "bonusTricks": state.progression.bonus_tricks if state.progression else 0,
        "advancementChoice": state.link.advancement_choice,
        "advanced": state.advanced,
    }


def companion_class(db: Session) -> BaseClass:
    return db.scalar(select(BaseClass).where(BaseClass.is_companion_class.is_(True)))


def create_companion(
    db: Session,
    master: Character,
    *,
    slot_key: str,
    species_id: UUID,
    name: str,
    hit_points: list[int],
    advancement_choice: str,
) -> Character:
    """Creates the companion `Character` for one of `master`'s free slots:
    species' starting scores, one pseudo-class level per HD of the current
    effective level, the given HP per HD (W8, the first one not maxed).
    Feats, skill ranks and ability increases stay open (step 3)."""
    if master.master_character_id is not None:
        raise HTTPException(status_code=422, detail="A companion can't have companions of its own")
    slot = next((s for s in companion_slots(db, master) if s.slot_key == slot_key), None)
    if slot is None:
        raise HTTPException(status_code=422, detail=f"No companion entitlement '{slot_key}'")
    if slot.companion is not None:
        raise HTTPException(status_code=422, detail=f"Slot '{slot_key}' already has a companion")
    species = next((race for race in slot.species if race.id == species_id), None)
    if species is None:
        raise HTTPException(status_code=422, detail="This species isn't allowed for this companion")
    progression = progression_row(db, slot.level)
    pseudo_class = companion_class(db)
    if len(hit_points) != progression.hit_dice:
        raise HTTPException(
            status_code=422, detail=f"Expected {progression.hit_dice} hit point values (one per HD), got {len(hit_points)}"
        )
    if any(not 1 <= value <= pseudo_class.hit_dice for value in hit_points):
        raise HTTPException(status_code=422, detail=f"Each hit point value must be between 1 and {pseudo_class.hit_dice}")
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
        companion.levels.append(CharacterLevel(level=hd, base_class_id=pseudo_class.id, hit_points=value))
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
            "hitDice": progression.hit_dice if (progression := progression_row(db, slot.level)) else None,
            "species": [{"id": str(race.id), "name": race.name} for race in slot.species],
            "companion": {"id": str(slot.companion.id), "name": slot.companion.name} if slot.companion else None,
        }
        for slot in slots
    ]
