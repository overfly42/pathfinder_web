import uuid

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
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
    can't live in the `CharacterCreate` field validator alone).

    `skill_choice_abilities` (2026-08-21 as a single `skill_choice_ability`,
    "Gewitztes Wortspiel"/Clever Wordplay; a list since 2026-10-17 for
    "Personifizierte Weisheit": "eine auf Stärke, Geschicklichkeit oder
    Konstitution basierende Fertigkeit") declares that this trait needs a
    one-off skill sub-choice at creation, restricted to skills whose own
    `BaseSkill.ability` is one of these values — same "catalog data declares
    what's needed, router validates against it" split as
    `BaseFeat.sub_choice_type`. Every trait sub-choice found so far is a
    skill pick; the value carried is which *abilities* the skill may be
    governed by (Clever Wordplay: ["CH"]), not a fixed skill list — reusing
    `BaseSkill.ability` as the source of truth for "which skills qualify".
    `None` (the default, every other trait) means no sub-choice at all."""

    __tablename__ = "base_traits"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    area: Mapped[str] = mapped_column(String(64))
    skill_choice_abilities: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)


class CharacterTrait(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A trait taken at one specific `CharacterLevel` — same per-level audit
    shape as `CharacterFeat`/`CharacterSkillRank`. Traits are chosen once at
    creation (max 2, enforced server-side, not per level like feats), so in
    practice these rows all land on the first `CharacterLevel`, but the shape
    stays level-scoped for consistency with the rest of the audit tables.

    `chosen_skill_id` is set exactly when `trait.skill_choice_abilities` is not
    null (validated server-side in `routers/characters.py`, same "no DB
    CHECK across tables" caveat as `CharacterFeat.chosen_skill_id`'s own
    docstring), and null for every other trait."""

    __tablename__ = "character_traits"
    __table_args__ = (UniqueConstraint("level_id", "trait_id"),)

    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("character_levels.id"))
    trait_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_traits.id"))
    chosen_skill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_skills.id"), nullable=True
    )

    trait: Mapped["BaseTrait"] = relationship()
