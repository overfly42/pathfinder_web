import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
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
    class_options: Mapped[list["CharacterClassOption"]] = relationship(cascade="all, delete-orphan")
    class_memberships: Mapped[list["CharacterClass"]] = relationship(cascade="all, delete-orphan")

    @property
    def level(self) -> int:
        """Total character level = sum of class levels = count of `levels` rows."""
        return len(self.levels)

    @property
    def classes(self) -> list[dict]:
        """Reconstructs the class-row shape the creation wizard submitted
        (`[{class_name, level, archetypes, is_favored, options}, ...]`) from
        `levels` (always a root `BaseClass` per row — see `CharacterLevel`)
        plus `class_memberships` (which root classes/archetypes the character
        has, and which root is favored) — not a separate stored list.

        Levels are grouped by root class regardless of position (not just
        consecutive runs): a future non-contiguous multiclass level-up
        (Fighter/Rogue/Fighter) should total "Fighter: 2", not split into two
        entries, since archetype selection no longer lives per-level."""
        options_by_root_id: dict[uuid.UUID, dict[str, list[str]]] = {}
        for option in self.class_options:
            group = options_by_root_id.setdefault(option.base_class_id, {})
            group.setdefault(option.group_key, []).append(option.choice)

        favored_by_root_id: dict[uuid.UUID, bool] = {}
        archetypes_by_root_id: dict[uuid.UUID, list[str]] = {}
        for membership in self.class_memberships:
            base_class = membership.base_class
            if base_class.arch_class_of is None:
                favored_by_root_id[base_class.id] = membership.is_favored
            else:
                archetypes_by_root_id.setdefault(base_class.arch_class_of, []).append(base_class.name)

        order: list[BaseClass] = []
        level_counts: dict[uuid.UUID, int] = {}
        for character_level in self.levels:
            root = character_level.base_class
            if root.id not in level_counts:
                order.append(root)
                level_counts[root.id] = 0
            level_counts[root.id] += 1

        return [
            {
                "class_name": root.name,
                "level": level_counts[root.id],
                "archetypes": archetypes_by_root_id.get(root.id, []),
                "is_favored": favored_by_root_id.get(root.id, False),
                "options": options_by_root_id.get(root.id, {}),
            }
            for root in order
        ]

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
    rolled/gained at it. `base_class_id` always points at a root `BaseClass`
    row (`arch_class_of is None`) — never an archetype variant; archetype
    selection lives once per class-taken in `CharacterClass`, not per level,
    so a level-up only ever needs to record the base class. `Character.level`/
    `Character.classes` are derived from these rows rather than stored
    directly, so multiclassing and future level-up history need no schema
    change."""

    __tablename__ = "character_levels"
    __table_args__ = (UniqueConstraint("character_id", "level"),)

    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id"))
    level: Mapped[int] = mapped_column(Integer)
    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    hit_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    base_class: Mapped[BaseClass] = relationship()


class CharacterClassOption(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A chosen value for one of a class's `optionGroups` (domain, bloodline,
    mystery, arcane school, favored enemy/terrain, ...) from `classes.json`.
    One row per chosen value — a group allowing multiple picks (e.g. domains,
    max 2) is multiple rows sharing `group_key`. `base_class_id` is always the
    root class's id (options apply to the class as a whole, same reasoning
    as `CharacterClass.is_favored`)."""

    __tablename__ = "character_class_options"

    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id"))
    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    group_key: Mapped[str] = mapped_column(String(64))
    choice: Mapped[str] = mapped_column(String(255))


class CharacterClass(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One row per class-or-archetype a character has. Both root classes and
    archetype variants live in the same `base_classes` catalog (distinguished
    by `arch_class_of`), so this is a simple membership join: taking Fighter
    with one archetype is two rows — the Fighter root row and the archetype
    row — with no nested table needed to support any number of archetypes.
    `is_favored` only ever applies to root rows (a specific archetype isn't
    independently "favored" — the class as a whole is); nothing computes a
    favored-class bonus yet, this just records the choice."""

    __tablename__ = "character_classes"

    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id"))
    base_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_classes.id"))
    is_favored: Mapped[bool] = mapped_column(Boolean, default=False)

    base_class: Mapped[BaseClass] = relationship()
