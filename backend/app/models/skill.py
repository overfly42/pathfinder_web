import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseSkill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Identity-only catalog of skills (name + governing ability), replacing
    the old `skills.json` fixture — a real table so `BaseClassSkill` has a
    proper FK target and skill names have a stable id a future translation
    layer can key off of (name stays a single, unlocalized string for now,
    matching `BaseRace`/`BaseClass` — real DE/EN is still an open item, see
    todos.md)."""

    __tablename__ = "base_skills"

    name: Mapped[str] = mapped_column(String(255))
    # "ST"/"GE"/"KO"/"IN"/"WE"/"CH" — the same fixed 2-letter code convention
    # used everywhere else in this codebase (Character.ability_score_*,
    # rules/race_abilities.py), not a BaseAttribute FK.
    ability: Mapped[str] = mapped_column(String(2))


class BaseClassSkill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Which skills are class skills for a class — replaces `classes.json`'s
    `classSkills: string[]` arrays. `base_class_id` is always a root class's
    id, matching what `classes.json` covers today (no archetype adds/swaps a
    class skill yet)."""

    __tablename__ = "base_class_skills"
    __table_args__ = (UniqueConstraint("base_class_id", "skill_id"),)

    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_skills.id"))
