import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin

SOURCE_TYPES = ("spell", "class_ability", "condition")


class BaseCondition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Identity-only catalog (roadmap slice 5) for conditions/poisons/
    diseases/curses that aren't already a `BaseSpell`/`BaseClassAbility` row
    — mirrors `BaseRaceAbility`/`BaseClassAbility`'s identity-only shape. No
    content seeded yet; a row only gets added once an actual condition needs
    one (CLAUDE.md: don't front-load ruleset content)."""

    __tablename__ = "base_conditions"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)


class CharacterEffect(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One applied instance of an effect on a character (roadmap slice 5) —
    a row per instance, not per character+effect, since the same effect can
    be active from two independent sources with two independent countdowns.

    `source_type`/`source_id` is a discriminated reference into whichever
    catalog the effect actually comes from (`base_spells`/
    `base_class_abilities`/`base_conditions`) — the same "plain-tag"
    convention as `BaseFeat.type`, not three nullable FK columns.

    `level` is the effect's potency/Stufe (e.g. the caster level behind an
    "X/level" duration) — asked of the player at activation time since
    nothing else in the data model can derive it, and fixed for the row's
    lifetime (a failed save does not escalate it).

    `incubation_remaining`/`duration_remaining` are plain round-based
    countdowns for effects with a flat duration. `frequency_rounds`/
    `next_check_in`/`successes_current`/`successes_required` are instead for
    effects resolved via repeated saves (poison/disease): `next_check_in`
    counts down to the next due save and resets to `frequency_rounds` after
    every save regardless of outcome; `successes_current` resets to 0 on a
    failure and the row is deleted once it reaches `successes_required`. An
    instance uses one countdown style or the other, not necessarily both."""

    __tablename__ = "character_effects"

    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id"))
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)

    incubation_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)

    frequency_rounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_check_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    successes_current: Mapped[int] = mapped_column(Integer, default=0)
    successes_required: Mapped[int | None] = mapped_column(Integer, nullable=True)
