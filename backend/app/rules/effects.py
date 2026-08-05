"""Handler registry for active effects (roadmap slice 5) — resolves what an
applied `CharacterEffect` instance actually does to a character's stats,
mirroring `rules/handlers.py`'s composition-vs-computation split: which
effects a character has is data (`CharacterEffect` rows), what each one does
is a handler function keyed by the effect's own catalog id.

Kept as its own registry rather than merged into `rules/handlers.py`'s
unified `HANDLERS`, same as `weapon_abilities.py`'s own `HANDLERS` stays
separate: the call signature differs. Race-ability/speed handlers take no
arguments (ownership alone determines the effect); an effect handler instead
needs every one of the character's active `CharacterEffect` rows for that
`source_id`, since only the handler itself can decide how multiple
instances of the same effect combine (ability damage from two sources sums;
the same fear condition from two sources doesn't double up) — the database
deliberately allows multiple independent rows per character+source_id to
leave that call open (see `models/effect.py`).

No real conditions/handlers are seeded yet — this is thin infrastructure
only, same "identity only for now" state `BaseClassAbility` started in.
Content gets added one id at a time once an actual poison/disease/buff needs
a computed effect rather than just display text."""

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

from .modifiers import Modifier

if TYPE_CHECKING:
    from ..models.effect import CharacterEffect

EFFECT_HANDLERS: dict[UUID, Callable[[list["CharacterEffect"]], list[Modifier]]] = {}


def resolve(source_id: UUID, instances: list["CharacterEffect"]) -> list[Modifier]:
    handler = EFFECT_HANDLERS.get(source_id)
    if handler is None:
        return []
    return handler(instances)
