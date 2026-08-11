"""Handler registry for active effects that aren't tied to a single class —
conditions, poisons, diseases (`todos.md`'s "Effekt-Handler-Inventar" tracks
the concrete remaining inventory). Effects that *are* a specific class's own
ability (e.g. a barbarian rage power) belong in that class's own file under
`rules/classes/` instead (CLAUDE.md's "Working Conventions") — Entfesselter
Barbar's Kampfrausch, this registry's first and only content until
2026-08-11, moved there for exactly that reason.

Mirrors `rules/handlers.py`'s composition-vs-computation split: which
effects a character has is data (`CharacterEffect` rows), what each one does
is a handler function keyed by the effect's own catalog id. Feeds
`rules/handlers.py`'s unified `HANDLERS`, same merge-only role
`race_abilities.py`/`speed.py`/`rules/classes/` play for their own slices —
every entry takes the uniform `CharacterContext` signature
(`rules/context.py`) and, for effects specifically, is expected to filter
`context.active_effects` for its own id itself (only the handler can decide
how multiple independent instances of its own effect combine — ability
damage from two sources sums, the same fear condition from two sources
doesn't double up — see `rules/classes/barbarian.py`'s
`_kampfrausch_entfesselter_barbar` for the pattern)."""

from collections.abc import Callable
from uuid import UUID

from .context import CharacterContext
from .modifiers import Modifier

EFFECT_HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {}
