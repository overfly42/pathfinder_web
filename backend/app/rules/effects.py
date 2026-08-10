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

Content gets added one id at a time once an actual poison/disease/buff needs
a computed effect rather than just display text — see `todos.md`'s
"Effekt-Handler-Inventar" for the full remaining inventory (conditions,
poisons, diseases, the 78 persistent-effect class abilities)."""

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

from .modifiers import Modifier, ModifierTarget

if TYPE_CHECKING:
    from ..models.effect import CharacterEffect


def _kampfrausch_entfesselter_barbar(instances: list["CharacterEffect"]) -> list[Modifier]:
    """Entfesselter Barbar's Kampfrausch (`base_class_abilities.json` id
    ad985f6f-3b03-5861-bccf-a016ebaba4ec — Barbar's own, differently worded
    Kampfrausch is a *different* id, not shared, see roadmap.md). PRD text:
    +2 on melee attack/damage, thrown-weapon damage, and Will saves; -2 AC;
    2 temporary HP per Hit Die.

    Only the AC penalty and Will-save bonus are modeled here. The melee/
    thrown attack-and-damage bonus isn't — this app has no attack/damage-roll
    endpoint for a `Modifier` to attach to at all (project-wide scope
    decision, see roadmap.md's weapon-abilities writeup). Temporary HP isn't
    either — it needs its own tracked pool separate from `hp_max`/
    `damage_taken`, which doesn't exist yet (roadmap.md Slice 3's
    "Class-ability computation" item flags this explicitly). Both are
    deliberate gaps, not oversights.

    Doesn't scale with instance count: raging twice at once from the same
    source isn't a state this app can produce (self-scoped toggle), so the
    flat bonus applies once whenever at least one instance is active,
    rather than summing per row the way e.g. ability damage would."""
    if not instances:
        return []
    return [
        Modifier(source="Kampfrausch", type="untyped", value=-2, target=ModifierTarget.AC),
        Modifier(source="Kampfrausch", type="morale", value=2, target=ModifierTarget.SAVE_WILL),
    ]


EFFECT_HANDLERS: dict[UUID, Callable[[list["CharacterEffect"]], list[Modifier]]] = {
    UUID("ad985f6f-3b03-5861-bccf-a016ebaba4ec"): _kampfrausch_entfesselter_barbar,
}


def resolve(source_id: UUID, instances: list["CharacterEffect"]) -> list[Modifier]:
    handler = EFFECT_HANDLERS.get(source_id)
    if handler is None:
        return []
    return handler(instances)


def active_effect_modifiers(effects: list["CharacterEffect"]) -> list[Modifier]:
    """All `Modifier`s contributed by a character's active effects, resolved
    once per distinct `source_id` — multiple independent instances of the
    same effect are handed to that one handler call together rather than
    resolved (and potentially summed) per row, so the handler itself decides
    how they combine (see `resolve()`'s docstring). Returns a mixed-target
    list; callers filter down to whichever `ModifierTarget` they're
    computing, same as `sheet.py`'s `_build_equipment` already does for
    gear-sourced modifiers."""
    by_source: dict[UUID, list["CharacterEffect"]] = {}
    for effect in effects:
        by_source.setdefault(effect.source_id, []).append(effect)
    modifiers: list[Modifier] = []
    for source_id, instances in by_source.items():
        modifiers.extend(resolve(source_id, instances))
    return modifiers
