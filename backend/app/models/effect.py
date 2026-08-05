import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseCondition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Identity-only catalog (roadmap slice 5) for conditions/poisons/
    diseases/curses that aren't already a `BaseSpell`/`BaseClassAbility` row
    — mirrors `BaseRaceAbility`/`BaseClassAbility`'s identity-only shape.
    Seeded 2026-08-05 via `scripts/build_conditions_seed.py` (33 standard
    conditions, 35 example poisons, 11 example diseases).

    `type` is a plain categorization tag ("condition"/"poison"/"disease") —
    same plain-string convention as `BaseFeat.type` — for grouping/filtering
    a picker UI and choosing sensible default activation fields (a
    poison/disease is frequency+successes-shaped, a plain condition is
    usually duration-shaped); not a computed rule itself. A poison/disease's
    SG/Inkubationszeit/Frequenz/Heilung lives in `description` as formatted
    text rather than separate columns, same as `BaseSpell.description` holds
    a spell's full text — the actual per-application numbers are typed in by
    the player at activation time (`EffectActivate`), read off this text."""

    __tablename__ = "base_conditions"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(32))


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
