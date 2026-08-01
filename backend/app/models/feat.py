import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
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
    prerequisite."""

    __tablename__ = "base_feats"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(64))
    prerequisite_text: Mapped[str | None] = mapped_column(Text, nullable=True)


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
    each group by matching at least one row in it. Not evaluated anywhere
    yet — see `BaseFeatRequiredBab`'s note on why (no prerequisite-checking
    code exists yet, slice 6 territory)."""

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
    """Data-only for now: nothing in the codebase computes a character's
    base attack bonus yet (no combat-stats calculator exists), so this
    requirement kind cannot be evaluated until that lands — a future slice 6
    concern, not something to fake here. See `BaseFeatRequiredFeat.group_id`
    for OR-group semantics."""

    __tablename__ = "base_feat_required_babs"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    minimum_bab: Mapped[int] = mapped_column(Integer)
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class CharacterFeat(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A feat granted at one specific `CharacterLevel` — same per-level audit
    shape as `CharacterSkillRank`, not a flat list on `Character` directly, so
    a future level-up (roadmap slice 7) can add new rows the same way it adds
    new skill-rank rows. `(level_id, feat_id)` is unique to stop the same feat
    being recorded twice at the same level by accident; a feat legitimately
    taken more than once across a career (e.g. explicitly repeatable feats)
    is still two rows, just at different levels."""

    __tablename__ = "character_feats"
    __table_args__ = (UniqueConstraint("level_id", "feat_id"),)

    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("character_levels.id"))
    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))

    feat: Mapped["BaseFeat"] = relationship()
