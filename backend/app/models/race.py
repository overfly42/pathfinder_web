import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseRace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "base_races"

    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    short_description: Mapped[str] = mapped_column(Text)


class BaseRaceAbility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reusable catalog of racial abilities/traits — identity only (name +
    description), no mechanical fields. What an ability actually does (flat
    bonus or conditional rule) is resolved by the handler registry in
    `app.rules.race_abilities`, keyed by this row's own `id` (see CLAUDE.md).
    """

    __tablename__ = "base_race_abilities"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)


class RaceAbilityGrant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Which abilities a race has — by default, or as an optional alternate pick."""

    __tablename__ = "race_ability_grants"

    race_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_races.id"))
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_race_abilities.id"))
    is_alternate: Mapped[bool] = mapped_column(Boolean, default=False)


class RaceAbilityReplacement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Scopes an alternate-trait swap to one race: within `base_race_id`,
    `ability_id` (the alternate) replaces `replaces_ability_id` (the default)."""

    __tablename__ = "race_ability_replacements"

    base_race_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_races.id"))
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_race_abilities.id"))
    replaces_ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_race_abilities.id"))
