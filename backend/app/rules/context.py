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
    granted_ability_ids: frozenset[UUID] = frozenset()
    # Full rows, not just ids: unlike the other composition fields above, a
    # handler resolving an active effect needs to decide *how multiple
    # independent instances of its own id combine* (ability damage from two
    # sources sums; the same fear condition from two sources doesn't double
    # up) — see `rules/effects.py`'s docstring, which this field replaces
    # the reasoning of.
    active_effects: list["CharacterEffect"] = field(default_factory=list)
    gear_item_ids: frozenset[UUID] = frozenset()
