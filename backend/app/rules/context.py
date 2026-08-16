"""`CharacterContext` — the single raw-data object every `HANDLERS`/
`EFFECT_HANDLERS` entry gets called with, across every rule-element family
(race abilities, class abilities, effects, weapon abilities with real
computed state). Decided 2026-08-10, refined 2026-08-10 (`roadmap.md`'s
"Uniform CharacterContext handler signature"; full rationale in
`readme.md`'s "Request pipeline" section). Holds only a character's own raw
state — ability scores, composition ids, active-effect rows — never a
computed/stacked value, so no handler can ever depend on another handler's
*output*, only on raw data every handler sees the same way.

Every field defaults to empty so a `CharacterContext` can be built even
where no persisted `Character` exists yet (e.g. `routers/races.py`'s
ability-score checks during character creation) — a handler that never
reads a given field is unaffected by that field being empty. Fields get
populated as the call sites that can actually supply them are migrated
(`roadmap.md`/`todos.md` track this per handler family); an empty field
today is an honest "not wired yet", the same convention `EFFECT_HANDLERS`
itself started with."""

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from ..models.effect import CharacterEffect


@dataclass
class CharacterContext:
    ability_scores: dict[str, int] = field(default_factory=dict)
    skill_ranks: dict[UUID, int] = field(default_factory=dict)
    feat_ids: frozenset[UUID] = frozenset()
    trait_ids: frozenset[UUID] = frozenset()
    # A `Counter`, not a `frozenset`: some class abilities are granted more
    # than once at different levels and each repetition has independent
    # mechanical weight (`sheet.py`'s `_granted_class_ability_ids` docstring
    # — e.g. Seeräuber's Wilder Seemann, `rules/classes/barbarian.py`), so a
    # handler reading its own id's count off this field (same pattern
    # `rules/speed.py`'s `class_speed_bonus` already used before this field
    # existed) sees how many of its own grants are currently met, not just
    # whether it has any. A plain membership/iteration check (`x in
    # context.granted_ability_ids`) still works unchanged — `Counter` is a
    # `dict` subclass.
    granted_ability_ids: Counter[UUID] = field(default_factory=Counter)
    # Full rows, not just ids: unlike the other composition fields above, a
    # handler resolving an active effect needs to decide *how multiple
    # independent instances of its own id combine* (ability damage from two
    # sources sums; the same fear condition from two sources doesn't double
    # up) — see `rules/effects.py`'s docstring, which this field replaces
    # the reasoning of.
    active_effects: list["CharacterEffect"] = field(default_factory=list)
    gear_item_ids: frozenset[UUID] = frozenset()
    # How many `CharacterLevel` rows this character has per root class taken
    # (`Character._class_level_counts()`, keyed by id instead of by
    # `BaseClass` row) — the one raw input a level-scaling class-ability
    # handler needs (e.g. Kampfrausch's rounds/day, `rules/classes/
    # barbarian.py`) that nothing else on this dataclass already carries.
    level_counts_by_root_id: dict[UUID, int] = field(default_factory=dict)
    # How many times this character has picked each race-scoped
    # favored-class-bonus `BaseClassOptionChoice` id over their whole career
    # (`CharacterClassOption` rows with `group_key == "favored_class_bonus"`,
    # same "count, not membership" shape `granted_ability_ids` uses since a
    # pick can recur every favored level) — the one raw input a handler whose
    # daily allowance an ARG racial favored-class bonus augments needs (e.g.
    # Entfesselter Barbar's Kampfrausch rounds/day, `rules/classes/
    # barbarian.py`) that nothing else here carries. `rules/
    # favored_class_bonuses.py`'s own `HANDLERS` still owns *converting* a
    # pick count into a bonus value; this field only supplies the raw count.
    favored_class_bonus_pick_counts: Counter[UUID] = field(default_factory=Counter)
