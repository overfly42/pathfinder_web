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
    effort than the feats slice this was introduced for.

    `is_persistent_effect` (roadmap slice 5) marks which abilities create a
    tracked `CharacterEffect` row when activated — most class features are
    instantaneous (Sneak Attack) or always-on passives with no activation
    step, so this defaults to `False`; only ones with an active duration
    (Rage, Bardic Performance, an "aktivierbare" aura) set it.

    `activation_scope` (plain tag, same convention as `BaseFeat.type`) is
    only meaningful when `is_persistent_effect` is `True` and distinguishes
    two shapes found while classifying Barbar/Barde: `"self"` — the owning
    character activates it on themselves (Rage) — stays gated by that
    character's own granted abilities, same as today; `"external"` — the
    effect only ever lands on someone *other* than the activating character
    (Barde's Lied des Erfolgs explicitly can't target the Barde themselves),
    so it must be offered to any character the same way a `BaseCondition`
    is, not gated by ownership; `"both"` — usable on the owner as well as
    others (Barde's Lied des Mutes/Lied der Größe/Lied des Heldenmuts name
    the Barde as an eligible target alongside allies). `None` for every
    ability where `is_persistent_effect` is `False`."""

    __tablename__ = "base_class_abilities"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    is_persistent_effect: Mapped[bool] = mapped_column(Boolean, default=False)
    activation_scope: Mapped[str | None] = mapped_column(String(16), nullable=True)


class BaseClassAbilityGrant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Which class grants which class ability, and at what level.
    `base_class_id` is usually a root class's id (`arch_class_of is None`) —
    same simplification as `BaseClassSkill` for classes that don't need
    otherwise. An archetype that adds its own class features (rather than
    only replacing base ones) instead has grant rows of its own, with
    `base_class_id` set to the archetype's `BaseClass` id and `level` still
    read against the character's level in the parent root class (archetypes
    don't have independent levels) — see `BaseClassAbilityReplacement` for
    how those archetype grants supersede specific root grants.

    `option_choice_id` is null for a grant every member of the class gets
    (e.g. Cleric's Energie fokussieren) and set for a grant conditional on
    one specific `BaseClassOptionChoice` (e.g. the "Domäne der Sonne"'s
    Nimbus des Lichts — only characters who picked that domain in Cleric's
    `domain` group get it). This is the only place that conditioning lives;
    `CharacterClassOption` stays a plain record of the pick with no
    mechanical meaning of its own.

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


class BaseClassAbilityReplacement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Scopes an archetype's class-feature swap to one specific parent grant:
    within `archetype_class_id` (an archetype `BaseClass` row, `arch_class_of`
    set), `ability_id` replaces `replaces_grant_id` — one exact
    `BaseClassAbilityGrant` row of the parent root class, not the whole
    ability. Grant-level rather than ability-level (contrast
    `RaceAbilityReplacement`, which is ability-level since racial alternate
    traits aren't leveled) because a Kämpfer archetype typically only swaps
    some of a recurring feature's grants — e.g. Zwei-Waffen-Kämpfer's
    Defensiver Wirbel replaces only the Kämpfer's level-3 and level-7
    Rüstungstraining grants, leaving the level-11/15 grants to be separately
    replaced by that archetype's Verbesserte Balance/Perfekte Balance."""

    __tablename__ = "base_class_ability_replacements"

    archetype_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))
    replaces_grant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_class_ability_grants.id")
    )


class BaseClassOptionGroup(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A selectable option group a class offers (Cleric's `domain`,
    Sorcerer's `bloodline`, Wizard's `school`, Oracle's `mystery`/`curse`,
    Ranger's `enemy`/`terrain`, Rogue's `trick`, ...) — replaces the
    `key`/`label`/`max` fields of `classes.json`'s `optionGroups` array.
    `base_class_id` is always a root class's id, same simplification as
    `BaseClassSkill`/`BaseClassAbilityGrant` (no archetype adds/swaps an
    option group yet).

    `max_choices` has two meanings depending on the group's shape, told
    apart by whether its members are picked once or repeatedly:
    - **One-time group** (domain/bloodline/school/enemy/terrain): pick up to
      `max_choices` values, once, at character creation.
      `CharacterClassOption.grant_id` stays null for these picks.
    - **Repeated-pick group** (Rogue's `trick`): `max_choices` is the total
      number of picks allowed across a character's whole career, one per
      qualifying `BaseClassAbilityGrant` occurrence (e.g. Rogue's Trick is
      granted at 10 different levels, so `max_choices = 10`) — each pick
      records which specific grant occurrence it fills via
      `CharacterClassOption.grant_id`, since eligibility can vary by
      occurrence (Rogue's "Verbesserte Tricks" pool only opens up for grants
      from level 10 onward)."""

    __tablename__ = "base_class_option_groups"
    __table_args__ = (UniqueConstraint("base_class_id", "key"),)

    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(255))
    max_choices: Mapped[int] = mapped_column(Integer)


class BaseClassOptionChoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One selectable value within a `BaseClassOptionGroup` (e.g. Cleric's
    "Domäne des Krieges" within its `domain` group, or — for a repeated-pick group
    like Rogue's `trick` — one individual trick) — identity only, same
    caveat as `BaseClassAbility`: no mechanical effect lives here, this only
    replaces the `choices` string array in `classes.json`. A choice's actual
    effect is a `BaseClassAbility`/`BaseClassAbilityGrant(option_choice_id=
    this.id)` pair, same pattern regardless of group shape.
    `CharacterClassOption.choice_id` (`character.py`) is the real FK to this
    table; `CharacterClassOption.choice` (the free string) is kept alongside
    it as a cheap display/debug mirror, not the source of truth anymore.

    `min_level` (nullable) is the class level a character must have reached
    before this choice is legal to pick, independent of which grant
    occurrence fills the slot — e.g. Mystiker (Oracle)'s Offenbarung
    ("revelation") choices each carry their own threshold (some need
    Mystiker 7, others 11 or 15), so a level-1 Offenbarung slot simply can't
    offer them yet even though later slots can. This generalizes what used
    to be an ad hoc, class-specific cutoff hardcoded in Python for Rogue's
    "Verbesserte Tricks" pool (see the old wording in
    `CharacterClassOption`'s docstring, `character.py`) into data: tag the
    higher tier's tricks with `min_level=10` instead, and any repeated-pick
    group gets the same "pool grows with level" behavior for free. Null
    means no threshold beyond the slot's own grant level.

    `requires_choice_id` (nullable, self-referencing) is the cross-group
    sibling of `min_level`: this choice is only legal if the character has
    already picked *that other* `BaseClassOptionChoice`, typically in a
    different one-time `BaseClassOptionGroup` of the same class. This is
    what scopes Mystiker's Offenbarung choices to the Mysterium the
    character picked at 1st level (e.g. "Sternenmantel" requires the
    "Firmament" mystery choice) — every option group before this one was
    either fully open or restricted purely by grant-occurrence level, never
    by a sibling choice, so there was no field to express it."""

    __tablename__ = "base_class_option_choices"
    __table_args__ = (UniqueConstraint("group_id", "name"),)

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_option_groups.id"))
    name: Mapped[str] = mapped_column(String(255))
    min_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_choice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_class_option_choices.id"), nullable=True
    )


class BaseClassAbilityFeatOption(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One eligible pick for a bonus-feat-slot ability (Kämpfer's
    Bonus-Kampftalent, Magier's Bonustalent, Hexenmeister's Talent des
    Blutes, Waldläufer's Kampfstiltalent, or a feat-granting Schurke trick
    like Kampfkniff/Schurkenfinesse) — a slot's full eligibility is the
    union of its rows. Exactly one of `feat_type`/`feat_id` is set per row:
    - `feat_type`: any `BaseFeat` with this type is eligible (broad
      category — Kämpfer: "combat"; Magier: one row each for
      "metamagic"/"item_creation").
    - `feat_id`: this exact feat is eligible (closed list — Hexenmeister's
      per-bloodline talent list; Magier's "Zaubermeisterschaft" exception;
      Schurkenfinesse's/Waffentraining's single fixed feat, a closed list of
      one — i.e. no real choice at all, just reusing this table rather than
      a separate deterministic-grant concept).

    `option_choice_id` (nullable) narrows the row to characters who picked
    that `BaseClassOptionChoice`, same meaning as
    `BaseClassAbilityGrant.option_choice_id` — lets "Talent des Blutes"
    share one `ability_id` across 10 different eligible lists (one per
    bloodline).

    `min_level` (nullable) — same meaning as `BaseClassOptionChoice.min_level`:
    the class level a character must have reached before this specific
    eligible feat opens up, on top of whichever level the slot itself is
    first granted at. Waldläufer's Kampfstiltalent needs this: each combat
    style's feat pool (already scoped via `option_choice_id`) grows twice
    more, at 6th and 10th level, with feats that aren't legal picks for the
    2nd-level slot that first grants the ability.

    "Is this ability a feat slot" is `EXISTS(row WHERE ability_id = this
    ability)` — retires the hand-frozen `BONUS_FEAT_SLOT_ABILITY_IDS` set in
    `rules/feat_slots.py` once seeded, so a future class's bonus feat,
    whatever shape its eligibility takes, is a pure data change."""

    __tablename__ = "base_class_ability_feat_options"

    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))
    option_choice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_class_option_choices.id"), nullable=True
    )
    feat_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    feat_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"), nullable=True)
    min_level: Mapped[int | None] = mapped_column(Integer, nullable=True)


class BaseClassAbilitySpellOption(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Sibling to `BaseClassAbilityFeatOption` for abilities that grant a
    pick from a spell list instead of a feat (Schurke's Höhere/Niedere
    Magie: pick a spell from the Hexenmeister/Magier list at a fixed grade).
    Exactly one shape is set per row:
    - `spell_id`: this exact spell is eligible (closed list).
    - `source_class_id` + `source_grade`: any spell in that class's list
      (`BaseClassSpell`) at that grade is eligible (broad filter — reuses
      the existing class spell list as the source of truth instead of
      enumerating every eligible spell by hand).

    `option_choice_id` — same meaning as `BaseClassAbilityFeatOption`.
    `min_level` — same meaning as `BaseClassAbilityFeatOption.min_level`."""

    __tablename__ = "base_class_ability_spell_options"

    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))
    option_choice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_class_option_choices.id"), nullable=True
    )
    spell_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_spells.id"), nullable=True
    )
    source_class_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_classes.id"), nullable=True
    )
    source_grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
