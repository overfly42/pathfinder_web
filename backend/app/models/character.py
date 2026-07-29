import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..rules.race_abilities import HANDLERS
from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Character(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """"Thin" + ability-scores character row (roadmap slice 2 + slice 3's
    point-buy item): identity, race, class, level fixed at 1, hit points,
    base ability scores. Skills/feats/traits are still a later "thick" pass.
    `class_name` is a plain fixture reference (the class name as it appears
    in `classes.json`), not a FK — classes stay in JSON fixtures until
    roadmap slice 8, unlike races.

    The six `ability_score_*` columns are the base point-buy scores only —
    the character's only stored ability-score state. Race/item/spell
    modifiers are never written back into these columns; they're applied on
    top at read time (see `rules/race_abilities.py`'s `HANDLERS`), the same
    composition-vs-computation split CLAUDE.md uses for everything else."""

    __tablename__ = "characters"

    name: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    race_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_races.id"))
    class_name: Mapped[str] = mapped_column(String(255))
    level: Mapped[int] = mapped_column(Integer, default=1)
    # Current (not max) HP — see readme.md's ER diagram, where max HP is derived
    # from per-level CharacterLevel.hit_points rows (roadmap slice 7), not stored
    # here. Nullable: HP calculation needs a class hit-die value that doesn't
    # exist anywhere yet (classes.json has no hit-die field) — a slice 3 concern,
    # not something to fake here with a placeholder number.
    current_hit_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    ability_score_st: Mapped[int] = mapped_column(Integer)
    ability_score_ge: Mapped[int] = mapped_column(Integer)
    ability_score_ko: Mapped[int] = mapped_column(Integer)
    ability_score_in: Mapped[int] = mapped_column(Integer)
    ability_score_we: Mapped[int] = mapped_column(Integer)
    ability_score_ch: Mapped[int] = mapped_column(Integer)
    # Point-buy budget the scores above were purchased against (10/15/20/25);
    # kept alongside the scores for display/audit, not re-validated on read.
    point_budget: Mapped[int] = mapped_column(Integer)

    ability_choices: Mapped[list["CharacterAbilityChoice"]] = relationship()

    @property
    def ability_scores(self) -> dict[str, int]:
        return {
            "ST": self.ability_score_st,
            "GE": self.ability_score_ge,
            "KO": self.ability_score_ko,
            "IN": self.ability_score_in,
            "WE": self.ability_score_we,
            "CH": self.ability_score_ch,
        }

    @property
    def flex_ability(self) -> str | None:
        """Which attribute the race's flex "+2 to any" bonus (if any) was put
        on, resolved from `ability_choices` via the same `HANDLERS` registry
        used everywhere else — not a stored column. See `routers/races.py`'s
        `resolve_flex_ability_id` for how a choice gets recorded."""
        for choice in self.ability_choices:
            handler = HANDLERS.get(choice.ability_id)
            if handler is None:
                continue
            attribute, _ = handler()
            if attribute is not None:
                return attribute
        return None


class CharacterAbilityChoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Which specific alternate ability a character picked, for any racial
    grant that requires a choice among several `RaceAbilityReplacement`
    options scoped to the character's race. Today the only user is the
    mandatory "+2 to any attribute" flex bonus (Human/Half-Elf/Half-Orc); a
    later "Traits" pass (roadmap slice 3) can reuse this same table for
    optional alternate-trait picks instead of inventing a second one."""

    __tablename__ = "character_ability_choices"
    __table_args__ = (UniqueConstraint("character_id", "ability_id"),)

    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id"))
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_race_abilities.id"))
