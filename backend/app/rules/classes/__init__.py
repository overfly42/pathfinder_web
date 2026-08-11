"""Per-class handler files — one module per class, closely related variants
(a class and its unchained/archetype sibling, e.g. `barbarian.py`'s Barbar +
Entfesselter Barbar) sharing a file rather than one per grantor
(CLAUDE.md's "Working Conventions"). Organized by class instead of by
mechanic family (the older `race_abilities.py`/`speed.py`/`effects.py`
split): class abilities are numerous and individually complex enough
(PF1e's ~40 classes/archetypes, each with many distinct features) that a
single `class_abilities.py` would grow without a natural seam, the same
concern that already keeps `base_class_abilities.json` split from
`base_race_abilities.json` — each class module is small and self-contained,
easy to find, easy to blame.

This module only merges every class file's own `HANDLERS` into one dict,
the same merge-only role `rules/handlers.py` plays for every family —
`rules/handlers.py` imports this package's `HANDLERS`, not each class file
individually, so a new class module only needs registering once, here.

Adding a class: create `rules/classes/<class_name>.py`, define its
handlers, export its own `HANDLERS: dict[UUID, Callable[[CharacterContext],
list[Modifier]]]` (ability ids are globally unique, hand-frozen UUIDs, same
convention as every other catalog — see `race_abilities.py`'s docstring —
so merging can never silently shadow one class's handler with another's),
then merge it in below."""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..modifiers import Modifier
from .barbarian import HANDLERS as _BARBARIAN_HANDLERS

HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    **_BARBARIAN_HANDLERS,
}
