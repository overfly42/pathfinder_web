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
    computed rule itself."""

    __tablename__ = "base_feats"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(64))


class BaseFeatRequiredFeat(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """`feat_id` requires the character to already have `required_feat_id`.
    All requirement rows across every `BaseFeatRequired*` table for a given
    `feat_id` are AND-ed together — there is no OR-group support (rare in the
    core rules; can be added later without reshaping what already exists)."""

    __tablename__ = "base_feat_required_feats"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    required_feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))


class BaseFeatRequiredSkill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "base_feat_required_skills"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_skills.id"))
    minimum_ranks: Mapped[int] = mapped_column(Integer)


class BaseFeatRequiredClassLevel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """`base_class_id` is always a root class's id, matching `BaseClassSkill`."""

    __tablename__ = "base_feat_required_class_levels"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    minimum_level: Mapped[int] = mapped_column(Integer)


class BaseFeatRequiredClassAbility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "base_feat_required_class_abilities"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))


class BaseFeatRequiredRace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "base_feat_required_races"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    race_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_races.id"))


class BaseFeatRequiredAbilityScore(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """`ability` is the same fixed 2-letter code convention used everywhere
    else (`BaseSkill.ability`, `Character.ability_score_*`), not a
    `BaseAttribute` FK."""

    __tablename__ = "base_feat_required_ability_scores"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    ability: Mapped[str] = mapped_column(String(2))
    minimum_score: Mapped[int] = mapped_column(Integer)


class BaseFeatRequiredBab(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Data-only for now: nothing in the codebase computes a character's
    base attack bonus yet (no combat-stats calculator exists), so this
    requirement kind cannot be evaluated until that lands — a future slice 6
    concern, not something to fake here."""

    __tablename__ = "base_feat_required_babs"

    feat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_feats.id"))
    minimum_bab: Mapped[int] = mapped_column(Integer)


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
