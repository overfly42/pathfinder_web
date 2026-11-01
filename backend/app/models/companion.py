import uuid

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseCompanionLevelSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One source of an effective master level for a companion track
    (roadmap slice 10, step 1) — e.g. "Druide level" or "Waldläufer level −3"
    for `animal_companion`, "Magier level" for `familiar`. Pure data; the
    sum per track is computed by `rules/companions.py`'s
    `master_effective_level`.

    `track` is the stacking group: `animal_companion` (mounts included) or
    `familiar`. Sources of one track add up (PF1e: companion levels from
    several sources stack), unless they share a `stack_group` — then only
    the highest counts (no source needs that yet).

    Trigger: exactly one of `class_ability_id` / `feat_id` (check
    constraint). A source only counts while its trigger is among the
    character's granted class abilities (`CharacterContext.
    granted_ability_ids`, Sekundärklasse grants included) or picked feats.

    `kind`: `class_level` (levels in `root_class_id`, then
    `(level + offset) // divisor`, floored at `minimum` and at 0 — same
    formula as `rules/secondary_class.py`'s `secondary_effective_level`),
    `character_level` (total level, same formula) or `flat_bonus` (`offset`
    as a plain bonus, e.g. Stallmeister +1). A source whose real rule
    doesn't fit (the Kleriker's Tier-Domäne taken by a Druide counts *Druide*
    level −3) gets a `rules/companions.py` `COMPANION_LEVEL_HANDLERS` entry
    keyed by this row's id instead of extra columns.

    `label` is the breakdown text on the sheet ("Druide", "Stallmeister")."""

    __tablename__ = "base_companion_level_sources"
    __table_args__ = (
        CheckConstraint(
            "(class_ability_id IS NULL) <> (feat_id IS NULL)", name="ck_companion_level_source_one_trigger"
        ),
        CheckConstraint(
            "kind IN ('class_level', 'character_level', 'flat_bonus')", name="ck_companion_level_source_kind"
        ),
        CheckConstraint("track IN ('animal_companion', 'familiar')", name="ck_companion_level_source_track"),
    )

    track: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(255))
    class_ability_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_class_abilities.id"), nullable=True
    )
    feat_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(32))
    root_class_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_classes.id"), nullable=True
    )
    offset: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    divisor: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    minimum: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stack_group: Mapped[str | None] = mapped_column(String(64), nullable=True)


class BaseCompanionSpeciesStage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One stage of a companion species (`BaseRace` with `companion_kind`
    set): `level` 1 is the species' starting statblock ("Spielwerte zu
    Beginn"), a later row its advancement ("Aufstieg auf die vierte/siebte
    Stufe", keyed by the *effective master level* it unlocks at) — roadmap
    slice 10 step 2b. Pure data, applied at read time by
    `app/companions.py`, never written back into the companion's stored
    scores.

    Columns read differently on the starting row vs. an advancement row:
    - `ability_scores`: starting row = the species' base scores (copied onto
      the companion `Character` when it's created); advancement = deltas.
    - `natural_armor`: starting row = the species' natural armor;
      advancement = additional natural armor ("RK: +2 natürliche RK").
    - `size`: starting row = base size; advancement = new size, `None` if
      unchanged (Kamel, Pferd, Pony, Vogel).
    - `natural_attacks`: a list of `{name, count, dice, damage_type,
      secondary, note, alternative}`; on an advancement row it *replaces*
      the earlier list, `None` keeps it.
    - `speeds` (`{"land": 9, "climb": 9, ...}`, meters) and
      `fly_maneuverability` only on the starting row."""

    __tablename__ = "base_companion_species_stages"
    __table_args__ = (UniqueConstraint("race_id", "level", name="uq_companion_species_stage_level"),)

    race_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_races.id"))
    level: Mapped[int] = mapped_column(Integer)
    size: Mapped[str | None] = mapped_column(String(32), nullable=True)
    natural_armor: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    ability_scores: Mapped[dict] = mapped_column(JSON)
    speeds: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fly_maneuverability: Mapped[str | None] = mapped_column(String(32), nullable=True)
    natural_attacks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Familiar species only (step 4), from the Monsterhandbuch statblock:
    # racial skill modifiers ("Volksmodifikatoren", `{skill_id: value}`) and
    # the species' own feats (`[{feat_id, chosen_skill_id}]`). A familiar has
    # no levels, so neither can live in `CharacterSkillRank`/`CharacterFeat`.
    skill_modifiers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    feats: Mapped[list | None] = mapped_column(JSON, nullable=True)


class BaseCompanionSpeciesStageAbility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A special ability (a `BaseRaceAbility` catalog row: Dämmersicht,
    Geruchssinn, Anspringen, ...) a species stage adds — cumulative, a later
    stage never removes an earlier stage's abilities."""

    __tablename__ = "base_companion_species_stage_abilities"
    __table_args__ = (UniqueConstraint("stage_id", "ability_id", name="uq_companion_stage_ability"),)

    stage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_companion_species_stages.id"))
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_race_abilities.id"))


class BaseCompanionProgression(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One row of the PRD's "Tabelle: Tiergefährte", keyed by the effective
    master level (1–20). BAB/saves/skill ranks/feat count aren't columns:
    they follow from the companion's `CharacterLevel` rows (one per HD) of
    the pseudo class "Tiergefährte" (`BaseClass.is_companion_class`) —
    verified against all 20 rows (roadmap slice 10)."""

    __tablename__ = "base_companion_progression"

    level: Mapped[int] = mapped_column(Integer, unique=True)
    hit_dice: Mapped[int] = mapped_column(Integer)
    natural_armor: Mapped[int] = mapped_column(Integer)
    str_dex_bonus: Mapped[int] = mapped_column(Integer)
    bonus_tricks: Mapped[int] = mapped_column(Integer)


class BaseCompanionProgressionAbility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A companion class ability (Verbindung, Zauber teilen, Entrinnen,
    Hingabe, Mehrfachangriff, Verbessertes Entrinnen) unlocked at an
    effective master level — keyed by that level, not by HD, because
    several levels share an HD count (Entrinnen comes at level 3, which has
    the same 3 HD as level 2)."""

    __tablename__ = "base_companion_progression_abilities"
    __table_args__ = (UniqueConstraint("level", "ability_id", name="uq_companion_progression_ability"),)

    level: Mapped[int] = mapped_column(Integer)
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))


class BaseCompanionArchetype(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An animal companion archetype (Hausregel, `requirements_v2.md` §10 —
    the PRD has none): it trades progression abilities for its own. One row
    per selectable variant, so an archetype with a pick (Elementargefährte:
    Luft/Erde/Feuer/Wasser) is one row per pick — the pick never changes
    afterwards, so it needs no separate option table."""

    __tablename__ = "base_companion_archetypes"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)


class BaseCompanionArchetypeAbility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A class ability an archetype adds at an effective master level — the
    same level axis as `BaseCompanionProgressionAbility`."""

    __tablename__ = "base_companion_archetype_abilities"
    __table_args__ = (UniqueConstraint("archetype_id", "ability_id", name="uq_companion_archetype_ability"),)

    archetype_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_companion_archetypes.id"))
    level: Mapped[int] = mapped_column(Integer)
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))


class BaseCompanionArchetypeReplacement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A progression ability (`BaseCompanionProgressionAbility.ability_id`)
    a companion of this archetype doesn't get."""

    __tablename__ = "base_companion_archetype_replacements"
    __table_args__ = (UniqueConstraint("archetype_id", "ability_id", name="uq_companion_archetype_replacement"),)

    archetype_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_companion_archetypes.id"))
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))


class BaseFamiliarProgression(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One row per master level (1–20) of the PRD's familiar table (Magier,
    "Besondere Fähigkeiten des Vertrauten"; the PRD lists two-level
    brackets): the bonus to the familiar's existing natural armor and its
    Intelligence. Everything else about a familiar is derived from its
    master (`app/companions.py`)."""

    __tablename__ = "base_familiar_progression"

    level: Mapped[int] = mapped_column(Integer, unique=True)
    natural_armor: Mapped[int] = mapped_column(Integer)
    intelligence: Mapped[int] = mapped_column(Integer)


class BaseFamiliarProgressionAbility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A familiar ability (Wachsamkeit, Empathische Verbindung, ...,
    Vertrauten ausspähen) unlocked at a master level."""

    __tablename__ = "base_familiar_progression_abilities"
    __table_args__ = (UniqueConstraint("level", "ability_id", name="uq_familiar_progression_ability"),)

    level: Mapped[int] = mapped_column(Integer)
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))


class BaseCompanionSlotGrant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An entitlement to one companion: while `class_ability_id` is granted,
    the master may have a companion of `track` in `slot_key` ("primary",
    ...). Several triggers naming the same slot (a Druide/Waldläufer)
    mean *one* companion whose species may come from any of their lists.
    `level_offset`/`divisor`/`minimum` adjust the track's master level for
    this slot (all 0/1/None for every base class; archetypes with a second,
    weaker companion will use them)."""

    __tablename__ = "base_companion_slot_grants"

    class_ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))
    track: Mapped[str] = mapped_column(String(32))
    slot_key: Mapped[str] = mapped_column(String(32))
    level_offset: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    divisor: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    minimum: Mapped[int | None] = mapped_column(Integer, nullable=True)


class BaseCompanionSlotSpecies(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A species an entitlement allows. `master_sizes` (e.g. `["Klein"]`
    for the Paladin's Kriegspony) restricts it to masters of those sizes,
    `min_level` to an effective master level (the Mystiker's Eber/Hund from
    4th); both `None` = always."""

    __tablename__ = "base_companion_slot_species"
    __table_args__ = (UniqueConstraint("slot_grant_id", "race_id", name="uq_companion_slot_species"),)

    slot_grant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_companion_slot_grants.id"))
    race_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_races.id"))
    master_sizes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    min_level: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CharacterCompanion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Links a companion `Character` (`Character.master_character_id` set)
    to its master's slot. The companion is a full `Character` row so the
    sheet, effects, HP, gear and print page work unchanged.

    `advancement_choice`: "species" (the species' 4th/7th-level
    advancement) or "dex_con" (+2 GE and +2 KO instead, PRD "Auswahl einer
    Tierart"). A master who loses the entitlement keeps the companion —
    shown as "ohne Anspruch", never deleted.

    `archetype_id`: the companion's archetype (`BaseCompanionArchetype`,
    animal companions only), `None` for none."""

    __tablename__ = "character_companions"
    __table_args__ = (
        UniqueConstraint("master_character_id", "track", "slot_key", name="uq_character_companion_track_slot"),
    )

    master_character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id"))
    companion_character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id"), unique=True
    )
    track: Mapped[str] = mapped_column(String(32))
    slot_key: Mapped[str] = mapped_column(String(32))
    advancement_choice: Mapped[str] = mapped_column(String(16), default="species", server_default="species")
    archetype_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_companion_archetypes.id"), nullable=True
    )


class BaseCompanionTrick(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A trick of the skill Mit Tieren umgehen (PRD "Tier einen Trick
    beibringen") — roadmap slice 10 step 5, imported by
    `scripts/import_companion_tricks.py`.

    `cost`: how many of the companion's tricks it takes up — 1, except the
    variant "Angreifen (alle Wesen)" ("wird als zwei Tricks gewertet").
    `variant_of_id`: the trick a variant includes (knowing the variant
    counts as knowing Angreifen; both can't be picked together).
    `required_ability_id`: a `BaseRaceAbility` the companion's species must
    have (Spuren suchen → Geruchssinn) — checked against the species stage
    abilities, no special case in code."""

    __tablename__ = "base_companion_tricks"

    name: Mapped[str] = mapped_column(String(255), unique=True)
    dc: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    cost: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    required_ability_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_race_abilities.id"), nullable=True
    )
    variant_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_companion_tricks.id"), nullable=True
    )


class BaseCompanionTrickPurpose(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A training ("Ein Tier für eine Aufgabe ausbilden": Kampfausbildung,
    Jagen, …) — a preset bundle of tricks (`BaseCompanionTrickPurposeTrick`),
    taught with one check instead of one per trick. A companion can have one
    at most."""

    __tablename__ = "base_companion_trick_purposes"

    name: Mapped[str] = mapped_column(String(255), unique=True)
    dc: Mapped[int] = mapped_column(Integer)
    weeks: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)


class BaseCompanionTrickPurposeTrick(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "base_companion_trick_purpose_tricks"
    __table_args__ = (UniqueConstraint("purpose_id", "trick_id", name="uq_companion_trick_purpose_trick"),)

    purpose_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_companion_trick_purposes.id"))
    trick_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_companion_tricks.id"))


class CharacterCompanionTrick(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A trick an animal companion knows (`character_id` = the companion
    `Character`). Not on `CharacterLevel`: tricks are taught at any time
    during downtime, and bonus tricks grow with the effective level, not HD.

    `source`: "bonus" (one of the progression row's `bonus_tricks`, no
    check needed) or "trained" (taught, counts against the IN limit — the
    player's own statement, the check and the week of training aren't
    modeled). `purpose_id` is set when the trick came in via a training;
    a training is stored as its tricks, so a trick already known isn't paid
    twice."""

    __tablename__ = "character_companion_tricks"
    __table_args__ = (
        UniqueConstraint("character_id", "trick_id", name="uq_character_companion_trick"),
        CheckConstraint("source IN ('bonus', 'trained')", name="ck_character_companion_trick_source"),
    )

    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id"))
    trick_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_companion_tricks.id"))
    source: Mapped[str] = mapped_column(String(16))
    purpose_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_companion_trick_purposes.id"), nullable=True
    )
