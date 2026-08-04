"""The unified ability-effect handler registry: one `HANDLERS: dict[UUID,
Callable[[], list[Modifier]]]` covering every ability id this codebase can
actually compute an effect for, regardless of which catalog it's a row in
(`BaseRaceAbility`, `BaseClassAbility`, ...). This is the registry CLAUDE.md
describes — "computing what an ability actually does is always resolved by
a Python-side handler function, looked up by the ability's own UUID" — kept
as one dict so every consumer (ability-score composition, land speed, and
whatever's next) shares one lookup instead of each subsystem inventing its
own handler dict shaped around its own return type.

Composition (which ability ids a given character actually has) stays
resolved separately per source — race grants are unconditional
(`routers/races.py`), class grants are level/archetype/option-gated
(`sheet.py`'s `_granted_class_ability_ids`) — since those gating rules
differ by source and have nothing to do with computing an effect. Only the
"what does this ability id compute" half is shared here.

Each source module (`race_abilities.py`, `speed.py`) authors its own slice
of `HANDLERS` locally, for the same locality/git-blame reason
`base_class_abilities.json`/`base_race_abilities.json` stay separate
fixture files rather than one combined one; this module only merges them.
Ability ids are globally unique across catalogs (each is its own hand-frozen
UUID, see `race_abilities.py`'s docstring), so the merge can never silently
shadow one source's handler with another's."""

from collections.abc import Callable
from uuid import UUID

from .modifiers import Modifier
from .race_abilities import HANDLERS as _RACE_ABILITY_HANDLERS
from .speed import HANDLERS as _SPEED_HANDLERS

HANDLERS: dict[UUID, Callable[[], list[Modifier]]] = {
    **_RACE_ABILITY_HANDLERS,
    **_SPEED_HANDLERS,
}
