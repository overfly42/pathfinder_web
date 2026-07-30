import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
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
    ability yet."""

    __tablename__ = "base_class_ability_grants"
    __table_args__ = (UniqueConstraint("base_class_id", "ability_id"),)

    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_class_abilities.id"))
    level: Mapped[int] = mapped_column(Integer)
