import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseClass(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A row is either a root class (`arch_class_of` is `None`) or one
    archetype variant of exactly one parent class (`arch_class_of` = the
    parent's id), per `readme.md`'s ER diagram (`BaseClasses.arch_class_of`,
    self-referencing). Unlike `BaseRace`, this isn't identity-only: `name`
    joins back to `classes.json` for skill points/class skills/spell type/
    etc., but mechanical facts that need a real FK target or a structural
    (not just fixture) representation — `hit_dice`, the archetype hierarchy
    — live here directly, and more are expected to migrate over time."""

    __tablename__ = "base_classes"

    name: Mapped[str] = mapped_column(String(255), unique=True)
    # Only ever set on root rows (`arch_class_of is None`) — archetypes swap
    # class features, not the hit die, so they resolve it via `root` instead
    # of duplicating it.
    hit_dice: Mapped[int | None] = mapped_column(Integer, nullable=True)
    arch_class_of: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_classes.id"), nullable=True
    )
    # Spellcasting ability (2-letter code, e.g. IN for Wizard, CH for
    # Sorcerer/Bard, WE for Druid/Cleric/Ranger) and tradition (`'arcane'`/
    # `'divine'`, the axis `BaseSpellComponent` keys off of) — null for
    # non-casters. Real columns rather than another `classes.json` field,
    # unlike `spellType`/etc.: these are new, and the intent going forward is
    # fewer fixtures, not more. Only ever set on root rows, same reasoning as
    # `hit_dice` (an archetype doesn't change its parent's casting ability or
    # tradition).
    casting_ability: Mapped[str | None] = mapped_column(String(2), nullable=True)
    spell_tradition: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # BAB/save progression (readme.md's ER diagram: `float bab_progression`,
    # `bool wil_save`/`fort_save`/`ref_save`) — only ever set on root rows,
    # same reasoning as `hit_dice`: an archetype doesn't change its parent's
    # progression. `bab_progression` is the fraction of character level
    # granted per level (1.0 full/0.75 3-in-4/0.5 half); a save being `True`
    # means "good" (2 + level/2), `False` means "poor" (level/3) — see
    # `rules/progression.py`.
    bab_progression: Mapped[float | None] = mapped_column(Float, nullable=True)
    fort_save: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ref_save: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    wil_save: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Skill points gained per level, before the INT modifier (`classes.json`'s
    # `skillPointsBase`) — only ever set on root rows, same reasoning as
    # `hit_dice`. Migrated out of the fixture the same way `bab_progression`/
    # the saves were: `_skill_points_total` (routers/characters.py) now reads
    # this column instead of looking the class up by name in `classes.json`.
    skill_points_base: Mapped[int | None] = mapped_column(Integer, nullable=True)

    parent: Mapped["BaseClass | None"] = relationship(
        remote_side="BaseClass.id", back_populates="archetypes"
    )
    archetypes: Mapped[list["BaseClass"]] = relationship(back_populates="parent")

    @property
    def root(self) -> "BaseClass":
        return self.parent.root if self.parent is not None else self

    @property
    def effective_hit_dice(self) -> int | None:
        return self.root.hit_dice

    @property
    def effective_casting_ability(self) -> str | None:
        return self.root.casting_ability

    @property
    def effective_spell_tradition(self) -> str | None:
        return self.root.spell_tradition


class BaseClassAbility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Identity-only catalog of class features (Channel Energy, Rage, Sneak
    Attack, ...) — mirrors `BaseRaceAbility`. Exists only so feat
    prerequisites can reference a class ability by id (`BaseFeatRequiredClassAbility`
    in `feat.py`); it is not yet a general class-features model (no
    mechanical fields, no handler registry) — that is a larger, separate
    effort than the feats slice this was introduced for."""

    __tablename__ = "base_class_abilities"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)


class BaseClassAbilityGrant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Which class grants which class ability, and at what level.
    `base_class_id` is always a root class's id (`arch_class_of is None`) —
    same simplification as `BaseClassSkill`: no archetype swaps a class
    ability yet.

    `option_choice_id` is null for a grant every member of the class gets
    (e.g. Cleric's Channel Energy) and set for a grant conditional on one
    specific `BaseClassOptionChoice` (e.g. the Sun domain's Searing Light —
    only characters who picked "Sonne" in Cleric's `domain` group get it).
    This is the only place that conditioning lives; `CharacterClassOption`
    stays a plain record of the pick with no mechanical meaning of its own.

    `level` is part of the uniqueness key (not just `base_class_id`/
    `ability_id`/`option_choice_id`) so the same ability can be granted more
    than once at different levels — e.g. Kämpfer's recurring bonus combat
    feat is one shared `BaseClassAbility` row granted via several
    `BaseClassAbilityGrant` rows, one per granting level, rather than one
    near-duplicate catalog row per level."""

    __tablename__ = "base_class_ability_grants"
    __table_args__ = (UniqueConstraint("base_class_id", "ability_id", "option_choice_id", "level"),)

    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))
    option_choice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_class_option_choices.id"), nullable=True
    )
    level: Mapped[int] = mapped_column(Integer)


class BaseClassOptionGroup(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A selectable option group a class offers at creation (Cleric's
    `domain`, Sorcerer's `bloodline`, Wizard's `school`, Oracle's `mystery`/
    `curse`, Ranger's `enemy`/`terrain`, ...) — replaces the `key`/`label`/
    `max` fields of `classes.json`'s `optionGroups` array. `base_class_id` is
    always a root class's id, same simplification as `BaseClassSkill`/
    `BaseClassAbilityGrant` (no archetype adds/swaps an option group yet)."""

    __tablename__ = "base_class_option_groups"
    __table_args__ = (UniqueConstraint("base_class_id", "key"),)

    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(255))
    max_choices: Mapped[int] = mapped_column(Integer)


class BaseClassOptionChoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One selectable value within a `BaseClassOptionGroup` (e.g. Cleric's
    "Kriegsdomäne" within its `domain` group) — identity only, same caveat as
    `BaseClassAbility`: no mechanical effect is modeled for any choice yet,
    this only replaces the `choices` string array in `classes.json`.
    `CharacterClassOption.choice` (`character.py`) still stores the pick as a
    free string rather than an FK to this table — reconciling that is a
    follow-up, not done here."""

    __tablename__ = "base_class_option_choices"
    __table_args__ = (UniqueConstraint("group_id", "name"),)

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_option_groups.id"))
    name: Mapped[str] = mapped_column(String(255))
