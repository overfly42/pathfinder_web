import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..rules.race_abilities import HANDLERS
from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .base_class import BaseClass


class Character(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """"Thin" + ability-scores character row (roadmap slice 2 + slice 3's
    point-buy item): identity, race, hit points, base ability scores.
    Skills/feats/traits are still a later "thick" pass.

    Class + level are not columns here — they're derived from `levels`
    (one `CharacterLevel` row per character level, per readme.md's ER
    diagram), pulled forward from roadmap slice 7 for the same reason races
    were pulled forward in slice 2: storing this as history from the start
    avoids a redesign once level-up needs it.

    The six `ability_score_*` columns are the base point-buy scores only —
    the character's only stored ability-score state. Race/item/spell
    modifiers are never written back into these columns; they're applied on
    top at read time (see `rules/race_abilities.py`'s `HANDLERS`), the same
    composition-vs-computation split CLAUDE.md uses for everything else."""

    __tablename__ = "characters"

    name: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    race_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_races.id"))
    # Current (not max) HP — see readme.md's ER diagram, where max HP is derived
    # from per-level CharacterLevel.hit_points rows, not stored here. Nullable:
    # HP calculation needs a class hit-die value that doesn't exist anywhere yet
    # (classes.json has no hit-die field) — a later slice 3 concern, not
    # something to fake here with a placeholder number.
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
    levels: Mapped[list["CharacterLevel"]] = relationship(
        order_by="CharacterLevel.level", cascade="all, delete-orphan"
    )

    @property
    def level(self) -> int:
        """Total character level = sum of class levels = count of `levels` rows."""
        return len(self.levels)

    @property
    def classes(self) -> list[dict]:
        """Reconstructs the class-row shape the creation wizard submitted
        (`[{class_name, level}, ...]`) by grouping consecutive same-class runs
        in `levels` (already ordered by level) — not a separate stored list."""
        result: list[dict] = []
        for character_level in self.levels:
            name = character_level.base_class.name
            if result and result[-1]["class_name"] == name:
                result[-1]["level"] += 1
            else:
                result.append({"class_name": name, "level": 1})
        return result

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


class CharacterLevel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One row per character level (readme.md's ER diagram): which class was
    taken at that level, and (once class hit-die data exists) the hit points
    rolled/gained at it. `Character.level`/`Character.classes` are derived
    from these rows rather than stored directly, so multiclassing and future
    level-up history need no schema change."""

    __tablename__ = "character_levels"
    __table_args__ = (UniqueConstraint("character_id", "level"),)

    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id"))
    level: Mapped[int] = mapped_column(Integer)
    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    hit_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    base_class: Mapped[BaseClass] = relationship()
