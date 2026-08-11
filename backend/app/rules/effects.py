"""Handler registry for active effects (roadmap slice 5) — resolves what an
applied `CharacterEffect` instance actually does to a character's stats,
mirroring `rules/handlers.py`'s composition-vs-computation split: which
effects a character has is data (`CharacterEffect` rows), what each one does
is a handler function keyed by the effect's own catalog id.

Migrated (2026-08-10, alongside `rules/speed.py`) to the uniform
`CharacterContext` handler signature (`rules/context.py`, `roadmap.md`'s
"Uniform CharacterContext handler signature") — every entry now takes the
caller's full `CharacterContext` rather than a pre-grouped instance list,
and filters `context.active_effects` for its own id itself (see
`_kampfrausch_entfesselter_barbar` below): only the handler can decide how
multiple independent instances of its own effect combine (ability damage
from two sources sums; the same fear condition from two sources doesn't
double up) — the database deliberately allows multiple independent rows per
character+source_id to leave that call open (see `models/effect.py`).

`EFFECT_HANDLERS` is authored here (locality/git-blame, same reason
`race_abilities.py`/`speed.py` keep their own slices) but is folded into
`rules/handlers.py`'s unified `HANDLERS` (2026-08-11) — every family now
shares one call signature, so the "kept separate because the call signature
differs" rationale that used to justify a fully separate registry no longer
applies. `weapon_abilities.py`'s own `HANDLERS` still stays genuinely
separate: its `resolve()` returns a display dict, not `list[Modifier]`, a
real type difference this migration doesn't touch.

Content gets added one id at a time once an actual poison/disease/buff needs
a computed effect rather than just display text — see `todos.md`'s
"Effekt-Handler-Inventar" for the full remaining inventory (conditions,
poisons, diseases, the 78 persistent-effect class abilities)."""

from collections.abc import Callable
from uuid import UUID

from .context import CharacterContext
from .modifiers import Modifier, ModifierTarget

KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID = UUID("ad985f6f-3b03-5861-bccf-a016ebaba4ec")


def _kampfrausch_entfesselter_barbar(context: CharacterContext) -> list[Modifier]:
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
    flat bonus applies once whenever at least one of *this handler's own*
    instances (filtered from `context.active_effects` by this ability's id)
    is active, rather than summing per row the way e.g. ability damage
    would."""
    instances = [e for e in context.active_effects if e.source_id == KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID]
    if not instances:
        return []
    return [
        Modifier(source="Kampfrausch", type="untyped", value=-2, target=ModifierTarget.AC),
        Modifier(source="Kampfrausch", type="morale", value=2, target=ModifierTarget.SAVE_WILL),
    ]


EFFECT_HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID: _kampfrausch_entfesselter_barbar,
}


def resolve(source_id: UUID, context: CharacterContext) -> list[Modifier]:
    handler = EFFECT_HANDLERS.get(source_id)
    if handler is None:
        return []
    return handler(context)


def active_effect_modifiers(context: CharacterContext) -> list[Modifier]:
    """All `Modifier`s contributed by a character's active effects
    (`context.active_effects`), resolved once per distinct `source_id` —
    each handler call gets the *whole* context and filters its own instances
    out of it itself (see `resolve()`'s docstring), rather than being handed
    a pre-grouped instance list. Returns a mixed-target list; callers filter
    down to whichever `ModifierTarget` they're computing, same as
    `sheet.py`'s `_build_equipment` already does for gear-sourced
    modifiers."""
    source_ids = {effect.source_id for effect in context.active_effects}
    modifiers: list[Modifier] = []
    for source_id in source_ids:
        modifiers.extend(resolve(source_id, context))
    return modifiers
