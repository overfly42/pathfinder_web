import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseFeat(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Identity-only catalog of feats, replacing `feats.json`'s flat name
    list. `type` is a plain categorization tag (e.g. "combat", "item_creation",
    "metamagic", "teamwork", "general") — same plain-string convention as
    `BaseSkill.ability` — used today to filter feat pickers (e.g. the fighter
    bonus-feat slot, see todos.md) and later by prerequisite display, not a
    computed rule itself.

    `prerequisite_text` is the prerequisite line as written in the rulebook,
    kept verbatim alongside the structured `BaseFeatRequired*` rows rather
    than instead of them: some prerequisite phrasing (free prose, references
    to content not yet modeled) still can't be structured at all, so this is
    always the source of truth for display; the structured rows are a
    best-effort machine-checkable subset. Null when the feat has no
    prerequisite.

    `is_persistent_effect`/`default_duration_rounds` (2026-08-16, same
    "activatable" concept `BaseClassAbility`/`BaseSpell` already have) mark
    which feats a player can activate as a tracked `CharacterEffect` via
    `POST .../effects` — most feats are passive or instantaneous, so this
    defaults to `False`/`None`; only ones with a real per-declaration effect
    (Heftiger Angriff) set it. Unlike `BaseClassAbility`, there's no
    `activation_scope` here — no feat found so far only makes sense on
    someone other than its owner, so every persistent-effect feat is
    implicitly self-scoped; add it if that ever changes, same as
    `BaseClassAbility`'s own docstring explains its scope tag.
    `default_duration_rounds` pre-fills the activation form's duration field
    (rounds — GRW's "bis zu deinem nächsten Zug", i.e. 1 round, for Heftiger
    Angriff) the same way `BaseCondition.default_duration_rounds` pre-fills a
    poison/disease's; the player can still override it, same as there."""

    __tablename__ = "base_feats"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(64))
    prerequisite_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_persistent_effect: Mapped[bool] = mapped_column(Boolean, default=False)
    default_duration_rounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Declares which kind of one-off sub-choice this feat needs beyond just
    # taking it (roadmap.md's "Talent-Sub-Wahl-Schema") — "weapon" (Waffenfokus,
    # Mächtiger Waffenfokus, Waffenspezialisierung, Mächtige
    # Waffenspezialisierung), "skill" (Fertigkeitsfokus), or "spell_school"
    # (Zauberfokus, Mächtiger Zauberfokus). Same plain-string-tag convention as
    # `type` — not an FK, since the choice's *target* table differs per value
    # (base_items/base_skills/a bare BaseSpell.school string) rather than
    # pointing at one shared catalog. Null means the feat is taken as-is, no
    # further choice needed (the common case). The actual pick lives on
    # `CharacterFeat`, one column per possible target; which one is populated
    # is validated server-side (`routers/characters.py`) against this field,
    # not enforced by the schema itself — same split as
    # `BaseClassAbilityFeatOption.feat_type`/`feat_id`.
    sub_choice_type: Mapped[str | None] = mapped_column(String(32), nullable=True)


class BaseFeatRequiredFeat(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """`feat_id` requires the character to already have `required_feat_id`.

    `group_id` is null for a plain, unconditional (AND) requirement — the
    default, and the only case that existed before OR-groups were added.
    When set, every row sharing the same `(feat_id, group_id)` pair — across
    *any* of the six `BaseFeatRequired*` tables, not just this one, since a
    group can mix kinds (e.g. "Elf oder Volksmerkmal Geschärfte Sinne") — is
    OR-ed together into one clause; that clause is then AND-ed against every
    other requirement (grouped or not) for that feat. A character satisfies
    the feat's prerequisites iff it satisfies every distinct group_id value
    (treating each null-group row as its own singleton group) and satisfies
    each group by matching at least one row in it. Evaluated by
    `rules/feat_prerequisites.py` (roadmap.md Slice 6, 2026-08-20), wired
    into `GET /api/feats`'s optional `character_id` filter."""

    __tablename__ = "base_feat_required_feats"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    required_feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class BaseFeatRequiredSkill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """See `BaseFeatRequiredFeat.group_id` for OR-group semantics."""

    __tablename__ = "base_feat_required_skills"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_skills.id"))
    minimum_ranks: Mapped[int] = mapped_column(Integer)
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class BaseFeatRequiredClassLevel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """`base_class_id` is always a root class's id, matching `BaseClassSkill`.
    See `BaseFeatRequiredFeat.group_id` for OR-group semantics."""

    __tablename__ = "base_feat_required_class_levels"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    minimum_level: Mapped[int] = mapped_column(Integer)
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class BaseFeatRequiredClassAbility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """See `BaseFeatRequiredFeat.group_id` for OR-group semantics."""

    __tablename__ = "base_feat_required_class_abilities"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class BaseFeatRequiredRace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """See `BaseFeatRequiredFeat.group_id` for OR-group semantics."""

    __tablename__ = "base_feat_required_races"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    race_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_races.id"))
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class BaseFeatRequiredAbilityScore(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """`ability` is the same fixed 2-letter code convention used everywhere
    else (`BaseSkill.ability`, `Character.ability_score_*`), not a
    `BaseAttribute` FK. See `BaseFeatRequiredFeat.group_id` for OR-group
    semantics."""

    __tablename__ = "base_feat_required_ability_scores"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    ability: Mapped[str] = mapped_column(String(2))
    minimum_score: Mapped[int] = mapped_column(Integer)
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class BaseFeatRequiredBab(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Evaluated against `Character.bab` by `rules/feat_prerequisites.py`
    (roadmap.md Slice 6, 2026-08-20). See `BaseFeatRequiredFeat.group_id`
    for OR-group semantics."""

    __tablename__ = "base_feat_required_babs"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    minimum_bab: Mapped[int] = mapped_column(Integer)
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class CharacterFeat(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A feat granted at one specific `CharacterLevel` — same per-level audit
    shape as `CharacterSkillRank`, not a flat list on `Character` directly, so
    a future level-up (roadmap slice 7) can add new rows the same way it adds
    new skill-rank rows. `(level_id, feat_id, chosen_*)` is unique to stop the
    same feat+sub-choice being recorded twice at the same level by accident,
    while still allowing an open-choice feat (e.g. Waffenfokus) to be taken
    more than once at the same level for two different targets (e.g.
    Waffenfokus: Zweihänder and Waffenfokus: Langbogen both picked at 1st
    level) — the plain `(level_id, feat_id)` shape this replaces couldn't
    represent that at all. A feat legitimately taken more than once across a
    career the old-fashioned way (different levels) is still two rows too,
    just at different levels, same as before.

    Exactly one of `chosen_weapon_id`/`chosen_skill_id`/`chosen_spell_school`
    is set when `feat.sub_choice_type` is not null (matching that value), and
    all three are null otherwise — see `BaseFeat.sub_choice_type`'s docstring
    for why this isn't itself an FK to one shared table. Validated
    server-side (`routers/characters.py`), not by a DB constraint: a CHECK
    can't reach across to `base_feats` to compare against `sub_choice_type`."""

    __tablename__ = "character_feats"
    __table_args__ = (
        UniqueConstraint(
            "level_id", "feat_id", "chosen_weapon_id", "chosen_skill_id", "chosen_spell_school"
        ),
    )

    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("character_levels.id"))
    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    chosen_weapon_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_items.id"), nullable=True
    )
    chosen_skill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_skills.id"), nullable=True
    )
    # Same plain-string convention as `BaseSpell.school` (not an FK — school
    # isn't its own catalog table, see that column's docstring).
    chosen_spell_school: Mapped[str | None] = mapped_column(String(64), nullable=True)

    feat: Mapped["BaseFeat"] = relationship()
