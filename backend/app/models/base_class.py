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
    # fewer fixtures, not more. Usually only set on root rows (an archetype
    # doesn't normally change its parent's casting ability or tradition,
    # same reasoning as `hit_dice`) — but unlike `hit_dice`, this one has a
    # real exception: Hexe's Narbiger Hexendoktor (Scarred Witch Doctor)
    # archetype casts on KO instead of IN. So an archetype row *can* set its
    # own non-null value here, which `effective_casting_ability` prefers
    # over the root's; a null archetype value still falls back to root,
    # covering every archetype that doesn't change this.
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
    # Self-referencing FK, `None` for the overwhelming majority of classes
    # (each casts from its own `base_class_spells` list). Set only when RAW
    # says the class's spell *selection* is drawn from another class's list
    # wholesale rather than having one of its own — the one confirmed case
    # today is Mystiker (Oracle), whose own "Zauber" class-ability text says
    # outright "wirkt göttliche Zauber von der Liste der Klerikerzauber"
    # (casts from the Cleric spell list). This is a real RAW fact, not a
    # missing-data workaround: the PRD's own per-spell class index
    # (`zauber_prd_import.json`) never tags a single spell "Mystiker" at
    # all, confirming the site doesn't maintain an independent Oracle list
    # either — Mystiker having its own handful of `BaseClassSpell` rows
    # before this field existed was leftover legacy data from before the
    # bulk PRD spell import, not a partially-completed real list (see
    # `effective_spell_list_class_id`'s docstring for how this is resolved).
    # Distinct from `known_grades`/`spontaneous_known_budget`
    # (`base_class_spells_known`): those stay Mystiker's own real, distinct
    # per-level known-spell *counts* (Oracle knows far fewer spells than a
    # preparing Cleric ever does) — only the pool of *which* spells exist to
    # choose from is shared, never how many of them a level lets you pick.
    #
    # 2026-09-05: Mystiker legitimately owns a *small* number of its own
    # `BaseClassSpell` rows again — not a regression of the legacy-data
    # cleanup above, but the Heimgesucht curse's Magierhand/Geisterhaftes
    # Geräusch/Telekinese/Schwerkraft umkehren, four genuinely foreign
    # (arcane, off Kleriker's list entirely) spells this one curse grants.
    # Only the grade-resolution call sites that resolve an *already-granted*
    # spell's own grade (`sheet.py`'s `_build_prepared_spell_grades`,
    # `routers/characters.py`'s `_resolve_prepared_class_spell`,
    # `routers/spells.py`'s `get_granted_spells_by_choice`) fall back to
    # these — every "which spells exist to pick from" query
    # (`effective_spell_list_class_id`'s own docstring, `/api/spells-by-class`,
    # creation/level-up manual-pick validation) still resolves exclusively
    # through Kleriker's list, so these four never appear as a manually
    # pickable Mystiker spell.
    spell_list_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_classes.id"), nullable=True
    )

    parent: Mapped["BaseClass | None"] = relationship(
        remote_side="BaseClass.id", back_populates="archetypes", foreign_keys="BaseClass.arch_class_of"
    )
    archetypes: Mapped[list["BaseClass"]] = relationship(back_populates="parent", foreign_keys="BaseClass.arch_class_of")

    @property
    def root(self) -> "BaseClass":
        return self.parent.root if self.parent is not None else self

    @property
    def effective_hit_dice(self) -> int | None:
        return self.root.hit_dice

    @property
    def effective_casting_ability(self) -> str | None:
        return self.casting_ability if self.casting_ability is not None else self.root.casting_ability

    @property
    def effective_spell_tradition(self) -> str | None:
        return self.spell_tradition if self.spell_tradition is not None else self.root.spell_tradition

    @property
    def effective_spell_list_class_id(self) -> uuid.UUID:
        """Which `BaseClass.id` a `base_class_spells`/`base_class_spell_grants`
        query should actually filter on for this class — itself, unless
        `spell_list_source_id` redirects to another class's list entirely
        (see that column's docstring). Every existing call site that used to
        query `BaseClassSpell.base_class_id == root.id` directly should use
        this instead wherever the query is about *which spells exist to
        pick from* (creation/level-up known-spell validation, the
        `/api/spells-by-class` picker) — not about a character's own
        already-*chosen* spells (`CharacterSpell.base_class_id` stays the
        real class the character took, regardless of where its candidate
        list came from)."""
        return self.spell_list_source_id if self.spell_list_source_id is not None else self.id


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
    ability where `is_persistent_effect` is `False`.

    `requires_active_ability_id` (self-referencing, same shape as
    `BaseClass.arch_class_of` above): `None` (default) means this ability
    has no activation prerequisite; when set, this ability only counts
    (appears as usable/active/listed) while a `CharacterEffect` sourced from
    *that other* ability id is currently active on the character. Generic on
    purpose, not specific to rage — e.g. Entfesselter Barbar's Kampfrauschkräfte
    (Erneuerte Lebenskraft, Bestientotem, ...) set this to their own class's
    Kampfrausch id, since PRD text is explicit that rage powers only work
    while raging (`rules/classes/barbarian.py`).

    `requires_weapon_choice` (2026-08-25, Kensai's "one type of martial or
    exotic weapon he chooses at 1st level") declares that this ability needs
    a one-off weapon sub-choice at creation, persisted in
    `CharacterClassAbilityWeaponChoice` — same "catalog data declares what's
    needed, router validates against it" split as `BaseTrait.skill_choice_ability`.
    Unlike that trait column there's no further qualifier to store (a weapon
    choice doesn't need an "ability the skill must match" dimension), so a
    plain boolean is enough. Deliberately not folded into the existing feat
    sub-choice machinery (`BaseFeat.sub_choice_type`): this grants the
    ability's own mechanical effect (proficiency, Weapon Focus) entirely for
    free, with no feat spent, so it needs its own composition/persistence
    rather than posing as a chosen `CharacterFeat` — see
    `rules/class_weapon_choices.py`'s module docstring.

    `default_duration_rounds` (2026-08-26, Kampfmagus's Arkaner Vorrat) only
    pre-fills the activation form's duration field — same role
    `BaseFeat.default_duration_rounds`/`BaseCondition.default_duration_rounds`
    already play for feats/conditions (see `BaseFeat`'s own docstring); the
    `CharacterEffect` row's actual `duration_remaining` is still whatever
    the player submits. `None` for most abilities (either no fixed RAW
    duration, or `is_persistent_effect` is `False` to begin with)."""

    __tablename__ = "base_class_abilities"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    is_persistent_effect: Mapped[bool] = mapped_column(Boolean, default=False)
    activation_scope: Mapped[str | None] = mapped_column(String(16), nullable=True)
    requires_active_ability_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_class_abilities.id"), nullable=True
    )
    requires_weapon_choice: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    default_duration_rounds: Mapped[int | None] = mapped_column(Integer, nullable=True)


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
      from level 10 onward).

    `is_secondary_class_initial_pick` (2026-09-04) marks a group whose choice
    the Sekundärklasse alternate rule (`models/base_class.py`'s
    `BaseSecondaryClassAbilityGrant`) requires *immediately* at 1st level,
    the moment the class is picked as someone's Sekundärklasse — before any
    milestone ability is granted at all, and independent of
    `BaseSecondaryClassAbilityGrant.option_group_key`'s milestone-tied reuse
    (that field resolves a sub-choice *at* a 3/7/11/15/19 milestone; this
    flag is about a pick due at 1st level on its own, because later
    milestone abilities are worded relative to it — e.g. Hexenmeister's
    source text: "Auf der 1. Stufe muss er eine Hexenmeisterblutlinie
    wählen", with the bloodline's own level-1 power only granted later at
    the 3rd-level milestone; same shape for Magier's `school`, Mystiker's
    `mystery`/`curse`, Hexe's `patron`). `False` (default) for every group a
    class's Sekundärklasse text doesn't call out this way (e.g. Waldläufer's
    `enemy`/`terrain`, which the source text only ever ties to their own
    milestone levels, never to 1st level) — `routers/characters.py`'s
    `create_character` only accepts `CharacterCreate.secondary_class_options`
    entries whose group key has this flag set, resolved at a hardcoded
    `character_level=1` (`_validate_options`), regardless of the
    character's real total level."""

    __tablename__ = "base_class_option_groups"
    __table_args__ = (UniqueConstraint("base_class_id", "key"),)

    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(255))
    max_choices: Mapped[int] = mapped_column(Integer)
    is_secondary_class_initial_pick: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


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
    by a sibling choice, so there was no field to express it.

    `race_id` (nullable) restricts a choice to one race — first used
    2026-08-16 for Advanced Race Guide alternate favored-class-bonus options
    (e.g. Half-Orc Barbarian's own "Kampfrauschrunden" choice in that
    class's own `favored_class_bonus` group, alongside the two
    race-independent "hp"/"skill" values every class offers, which aren't
    `BaseClassOptionChoice` rows at all — see `routers/characters.py`'s
    `level_up_character`). `None` means available regardless of race, the
    same meaning every choice already had implicitly before this column
    existed."""

    __tablename__ = "base_class_option_choices"
    __table_args__ = (UniqueConstraint("group_id", "name"),)

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_option_groups.id"))
    name: Mapped[str] = mapped_column(String(255))
    min_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_choice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_class_option_choices.id"), nullable=True
    )
    race_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("base_races.id"), nullable=True)


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


class BaseClassAbilityGrantedFeat(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """`ability_id` inherently confers `feat_id`, automatically and for free
    — distinct from `BaseClassAbilityFeatOption`, which models a *slot* the
    character spends a bonus-feat pick on (counted by `rules/feat_slots.py`'s
    `base_feat_count`, recorded as an ordinary `CharacterFeat` the player
    chose into). A weapon/armor proficiency class feature (e.g. "Umgang mit
    Waffen und Rüstungen") isn't a slot — every character with that ability
    just has the proficiency, no pick and no feat-count cost involved — so it
    needs its own always-on grant, not a one-candidate `FeatOption` row.

    Read by `routers/feats.py`'s `_character_prereq_state`, which folds
    `feat_id` into the character's effective `feat_ids` for every ability in
    `granted_ability_ids` — so a class-granted proficiency satisfies a
    downstream feat's `BaseFeatRequiredFeat` prerequisite (e.g. "Umgang mit
    Rüstungen (mittelschwere)" requiring "Umgang mit Rüstungen (leichte)")
    the same way actually having taken that feat would, without a character
    needing to spend a pick on a proficiency their class already grants.
    Archetypes that narrow a class's proficiencies (e.g. Seeräuber dropping
    medium armor) simply have fewer rows under their own replacement
    `ability_id` than the base class's — no extra "revoke" concept needed."""

    __tablename__ = "base_class_ability_granted_feats"

    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))
    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))


class BaseSecondaryClassAbilityGrant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Which ability a character granted this class as their **Sekundärklasse**
    (http://prd.5footstep.de/Alternativregeln/Fertigkeiten/
    AlternativesSystemfuerCharakteremitKlassenkombinationen) receives at a
    given character level — the alternate-rule sibling of
    `BaseClassAbilityGrant`, not a reuse of it: `level` there is the
    character's level *in that class*, but a Sekundärklasse character never
    has real levels in it at all, so `character_level` here is deliberately
    the character's *total* character level instead (always one of 3/7/11/
    15/19 per the rule's own table — every character gets a talent on every
    other odd level, and one of these five instead on the rest).

    `ability_id` points at the *existing* `BaseClassAbility` row wherever the
    source text just grants that class's own real feature (e.g. Barbar's
    real "Kampfrausch") — the common case, since the rule almost always
    phrases a tier as "erhält das Klassenmerkmal X". A tier whose text
    describes something the primary class doesn't have verbatim gets its own
    fresh `BaseClassAbility` row instead. Either way this stays pure
    composition (CLAUDE.md): which ability, at which milestone, for which
    class — never a mechanical field.

    `effective_level_offset`/`effective_level_divisor`/`effective_level_minimum`
    encode this tier's own "effektive Klassenstufe" formula against the
    character's total level — every tier across all 19 classes in the source
    text reduces to this same shape (an offset, optionally halved, optionally
    floored), so one shared function (`rules/secondary_class.py`'s
    `secondary_effective_level`) computes it; no per-class handler needed for
    the level number itself. Defaults (`offset=0, divisor=1, minimum=None`)
    mean "use the character's real total level unmodified".

    `option_group_key` (nullable) is set only when this tier requires a
    sub-choice (Kampfmagus' Arkanum, Barbar's "eine Kampfrauschkraft",
    Mystiker's Offenbarung, ...) and names an *existing*
    `BaseClassOptionGroup.key` on the same root class — the Sekundärklasse
    system never needs its own option-group schema, it just resolves that
    group's existing choices against this tier's own effective level instead
    of the character's real level in that class (see
    `routers/characters.py`'s `_validate_options`, which already takes
    `character_level` as a plain parameter)."""

    __tablename__ = "base_secondary_class_ability_grants"
    __table_args__ = (UniqueConstraint("secondary_base_class_id", "character_level", "ability_id"),)

    secondary_base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    character_level: Mapped[int] = mapped_column(Integer)
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))
    effective_level_offset: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    effective_level_divisor: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    effective_level_minimum: Mapped[int | None] = mapped_column(Integer, nullable=True)
    option_group_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
