import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseSpell(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Identity-only global spell catalog — one row per spell regardless of
    which class(es) can cast it (a spell's grade is per-class, see
    `BaseClassSpell`, not a property of the spell itself). Replaces
    `spells_by_class.json`'s bare per-class name lists."""

    __tablename__ = "base_spells"

    name: Mapped[str] = mapped_column(String(255))
    school: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)


class BaseSpellComponent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Verbal/somatic/material/focus components, keyed by `(spell_id,
    tradition)` rather than by spell alone — the same spell's arcane and
    divine version can require different components (material vs. divine
    focus in particular). `tradition` is `'arcane'` or `'divine'`, matching
    `BaseClass.spell_tradition`. Pure descriptive data for now — nothing
    computes off it yet; it exists so a later "available actions" pass
    (roadmap slice 6) can check for a component pouch/holy symbol without a
    schema change."""

    __tablename__ = "base_spell_components"
    __table_args__ = (UniqueConstraint("spell_id", "tradition"),)

    spell_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_spells.id"))
    tradition: Mapped[str] = mapped_column(String(16))
    verbal: Mapped[bool] = mapped_column(Boolean, default=False)
    somatic: Mapped[bool] = mapped_column(Boolean, default=False)
    material: Mapped[bool] = mapped_column(Boolean, default=False)
    material_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    focus: Mapped[bool] = mapped_column(Boolean, default=False)
    focus_description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class BaseClassSpell(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Which classes can cast a spell, and at what grade — a spell's grade is
    per-class in PF1e (e.g. Cleric 3rd / Bard 2nd for the same spell), not a
    spell-level constant. Mirrors `BaseClassSkill`'s join shape.
    `base_class_id` is always a root class's id, same simplification as
    `BaseClassSkill`/`BaseClassAbilityGrant` (archetypes don't change a
    class's spell list yet)."""

    __tablename__ = "base_class_spells"
    __table_args__ = (UniqueConstraint("base_class_id", "spell_id"),)

    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    spell_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_spells.id"))
    grade: Mapped[int] = mapped_column(Integer)

    spell: Mapped["BaseSpell"] = relationship()


class BaseClassSpellsKnown(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """The classic per-class "spells known by level" table (e.g. a 3rd-level
    Sorcerer knows 4 grade-0 and 2 grade-1 spells) — one row per
    `(base_class_id, level, grade)` combination that exists at all; row
    *presence* is also the grade-accessibility gate: if no row exists for a
    given level/grade, that grade isn't castable yet at that level, for any
    casting style.

    `count` is the cumulative known-spells cap at that level for spontaneous
    casters (`BaseClass`s whose `classes.json` `spellType` is
    `'spontaneous'`) — a level-up grants only the *delta* versus the
    previous level's count for the same grade, never re-grants the whole
    total. For arcane-prepared (Wizard-style) classes, `count` is unused
    (nullable) — the spellbook has no known-spell cap, so only row
    *presence* matters there, purely for the grade gate."""

    __tablename__ = "base_class_spells_known"
    __table_args__ = (UniqueConstraint("base_class_id", "level", "grade"),)

    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    level: Mapped[int] = mapped_column(Integer)
    grade: Mapped[int] = mapped_column(Integer)
    count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CharacterSpell(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A spell known/in the spellbook, granted at one specific
    `CharacterLevel` — same per-level audit shape as `CharacterFeat`/
    `CharacterTrait`, but also keyed by `base_class_id` since a multiclassed
    character's known-spell budget is tracked separately per class (the same
    spell could in principle be known via two different classes). The in-play
    "add to spellbook" action (`requirements_v2.md` §2.2, arcane-prepared
    classes only) collapses onto the character's current highest
    `CharacterLevel`, same pattern used for multi-level creation elsewhere."""

    __tablename__ = "character_spells"
    __table_args__ = (UniqueConstraint("level_id", "base_class_id", "spell_id"),)

    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("character_levels.id"))
    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    spell_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_spells.id"))

    spell: Mapped["BaseSpell"] = relationship()
