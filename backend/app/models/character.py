import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..rules.progression import class_bab, class_save_bonus
from ..rules.race_abilities import HANDLERS
from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .base_class import BaseClass
from .race import BaseRaceAbility


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

    racial_choices: Mapped[list["CharacterRacialChoice"]] = relationship()
    levels: Mapped[list["CharacterLevel"]] = relationship(
        order_by="CharacterLevel.level", cascade="all, delete-orphan"
    )
    class_options: Mapped[list["CharacterClassOption"]] = relationship(cascade="all, delete-orphan")
    class_memberships: Mapped[list["CharacterClass"]] = relationship(cascade="all, delete-orphan")
    gear: Mapped[list["CharacterGear"]] = relationship(cascade="all, delete-orphan")

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

    def _class_level_counts(self) -> dict[BaseClass, int]:
        """How many `levels` rows this character has per root class taken —
        the shared grouping `bab`/`saves` need (each class's own progression
        is computed against its own level count, then summed, per
        `requirements_v2.md` §2's multiclass rule)."""
        counts: dict[uuid.UUID, int] = {}
        roots: dict[uuid.UUID, BaseClass] = {}
        for character_level in self.levels:
            root = character_level.base_class
            counts[root.id] = counts.get(root.id, 0) + 1
            roots[root.id] = root
        return {roots[root_id]: count for root_id, count in counts.items()}

    @property
    def bab(self) -> int:
        """Total base attack bonus, computed (not stored) from each class's
        own `bab_progression` and level count, summed across classes."""
        return sum(class_bab(root.bab_progression, count) for root, count in self._class_level_counts().items())

    @property
    def saves(self) -> dict[str, int]:
        """Total Fortitude/Reflex/Will save bonuses, computed (not stored)
        the same way as `bab` — each class's own good/poor progression
        against its own level count, summed across classes."""
        counts = self._class_level_counts()
        return {
            "fort": sum(class_save_bonus(root.fort_save, count) for root, count in counts.items()),
            "ref": sum(class_save_bonus(root.ref_save, count) for root, count in counts.items()),
            "will": sum(class_save_bonus(root.wil_save, count) for root, count in counts.items()),
        }

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
    def skill_ranks(self) -> dict[str, int]:
        """Current ranks per skill, summed from every `CharacterSkillRank`
        row across all levels — never stored as its own total (CLAUDE.md)."""
        totals: dict[str, int] = {}
        for level in self.levels:
            for entry in level.skill_ranks:
                key = str(entry.skill_id)
                totals[key] = totals.get(key, 0) + entry.ranks
        return totals

    @property
    def feat_ids(self) -> list[uuid.UUID]:
        """Every feat granted across all levels, flattened — never stored as
        its own list (CLAUDE.md), same reasoning as `skill_ranks`."""
        return [entry.feat_id for level in self.levels for entry in level.feats]

    @property
    def trait_ids(self) -> list[uuid.UUID]:
        """Every trait taken across all levels, flattened — same reasoning
        as `feat_ids`."""
        return [entry.trait_id for level in self.levels for entry in level.traits]

    @property
    def spell_ids(self) -> dict[str, list[uuid.UUID]]:
        """Every spell known/in the spellbook, flattened across all levels and
        grouped by `base_class_id` (stringified — UUID keys aren't valid JSON
        object keys, same convention as `CharacterCreate.skill_ranks`) — same
        per-level-audit-but-never-stored-as-its-own-list reasoning as
        `feat_ids`/`trait_ids`, but grouped since a multiclassed character's
        known spells are tracked separately per class."""
        result: dict[str, list[uuid.UUID]] = {}
        for level in self.levels:
            for entry in level.spells:
                result.setdefault(str(entry.base_class_id), []).append(entry.spell_id)
        return result

    @property
    def flex_ability(self) -> str | None:
        """Which attribute the race's flex "+2 to any" bonus (if any) was put
        on, resolved from `racial_choices` via the same `HANDLERS` registry
        used everywhere else — not a stored column. See `routers/races.py`'s
        `resolve_flex_ability_id` for how a choice gets recorded. An
        ability-score-bonus alternate is always the flex pick, never a
        flavor alt-trait (see `alt_traits`), so this is exactly the rows
        with a `HANDLERS` entry."""
        for choice in self.racial_choices:
            handler = HANDLERS.get(choice.ability_id)
            if handler is None:
                continue
            attribute, _ = handler()
            if attribute is not None:
                return attribute
        return None

    @property
    def alt_traits(self) -> list[str]:
        """Names of chosen optional alternate racial traits — flavor swaps
        (e.g. Elf's Keen Senses variant), distinct from the mandatory flex
        ability-score pick above. Resolved as every `racial_choices` row
        *without* a `HANDLERS` entry, the mirror image of `flex_ability`."""
        return [choice.ability.name for choice in self.racial_choices if choice.ability_id not in HANDLERS]


class CharacterRacialChoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Which specific alternate ability a character picked, for any racial
    grant that requires a choice among several `RaceAbilityReplacement`
    options scoped to the character's race: the mandatory "+2 to any
    attribute" flex bonus (Human/Half-Elf/Half-Orc) and optional
    alternate-trait swaps (e.g. Elf's Keen Senses variant) both persist here
    — one shared table rather than a second one per roadmap slice 3, since
    both are "pick one ability id from this race's alternates" the same way."""

    __tablename__ = "character_racial_choices"
    __table_args__ = (UniqueConstraint("character_id", "ability_id"),)

    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id"))
    ability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_race_abilities.id"))

    ability: Mapped["BaseRaceAbility"] = relationship()


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
    skill_ranks: Mapped[list["CharacterSkillRank"]] = relationship(cascade="all, delete-orphan")
    feats: Mapped[list["CharacterFeat"]] = relationship(cascade="all, delete-orphan")
    traits: Mapped[list["CharacterTrait"]] = relationship(cascade="all, delete-orphan")
    spells: Mapped[list["CharacterSpell"]] = relationship(cascade="all, delete-orphan")


class CharacterSkillRank(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Ranks granted to a skill by one specific `CharacterLevel` — an audit
    entry, not a running total. A character's current ranks in a skill is
    always SUM(ranks) across these rows (see `Character.skill_ranks`),
    computed rather than stored redundantly (CLAUDE.md). Multi-level
    creation collapses onto the highest `CharacterLevel` row created in that
    request (no per-level breakdown asked of the wizard); a later level-up
    (roadmap slice 7) instead adds one new row per skill tied to the new
    level, holding only that level's newly bought ranks — same table, same
    insert shape, just a smaller delta."""

    __tablename__ = "character_skill_ranks"
    __table_args__ = (UniqueConstraint("level_id", "skill_id"),)

    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("character_levels.id"))
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_skills.id"))
    ranks: Mapped[int] = mapped_column(Integer)


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


class CharacterGear(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A character's current inventory: one row per distinct `BaseItem` held,
    with a quantity — not a per-`CharacterLevel` audit trail like
    `CharacterFeat`/`CharacterTrait` (gear is bought/found/dropped during
    play, not gained at level-up), so this is keyed by `character_id`
    directly, matching roadmap slice 4's character-scoped
    `POST/PATCH/DELETE .../gear` endpoints. Descriptive only for now — no
    equip slots, no AC/attack-bonus computation (slice 4)."""

    __tablename__ = "character_gear"
    __table_args__ = (UniqueConstraint("character_id", "item_id"),)

    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id"))
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_items.id"))
    quantity: Mapped[int] = mapped_column(Integer)
