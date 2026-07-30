import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseTrait(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Identity-only catalog of character traits (PF1e background traits,
    e.g. "Reaktionsschnell") — distinct from `RaceAbilityGrant`/
    `RaceAbilityReplacement`'s racial alternate traits, which are a different
    rule concept persisted via `CharacterRacialChoice`. Replaces
    `traits.json`'s flat name list, same convention as `BaseFeat`.

    `area` is a plain categorization tag (e.g. "combat", "faith", "magic",
    "race", "region", "social", "campaign", "general") — same
    `BaseFeat.type`/`BaseSkill.ability` convention — but unlike those, it's
    also load-bearing: PF1e caps a character at one trait per area, enforced
    in `routers/characters.py`'s `create_character` (needs a DB lookup, so it
    can't live in the `CharacterCreate` field validator alone)."""

    __tablename__ = "base_traits"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    area: Mapped[str] = mapped_column(String(64))


class CharacterTrait(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A trait taken at one specific `CharacterLevel` — same per-level audit
    shape as `CharacterFeat`/`CharacterSkillRank`. Traits are chosen once at
    creation (max 2, enforced server-side, not per level like feats), so in
    practice these rows all land on the first `CharacterLevel`, but the shape
    stays level-scoped for consistency with the rest of the audit tables."""

    __tablename__ = "character_traits"
    __table_args__ = (UniqueConstraint("level_id", "trait_id"),)

    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("character_levels.id"))
    trait_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_traits.id"))

    trait: Mapped["BaseTrait"] = relationship()
