"""The unified ability-effect handler registry: one `HANDLERS: dict[UUID,
Callable[[CharacterContext], list[Modifier]]]` covering every ability id this
codebase can actually compute an effect for, regardless of which catalog
it's a row in (`BaseRaceAbility`, `BaseClassAbility`, active-effect source
ids, ...). This is the registry CLAUDE.md describes — "computing what an
ability actually does is always resolved by a Python-side handler function,
looked up by the ability's own UUID" — kept as one dict so every consumer
shares one lookup instead of each subsystem inventing its own handler dict.

Real integration point (2026-08-11, closing the gap the previous revision of
this module left open): every consumer that used to import a per-family
`HANDLERS`/`EFFECT_HANDLERS` slice directly now imports it from here instead
(`routers/races.py`, `models/character.py`, `sheet.py`'s `character_modifiers`
below) — the merged dict is the one every caller actually goes through, not
just documentation of the target shape.

Composition (which ability ids a given character actually has) stays
resolved separately per source — race grants are unconditional
(`routers/races.py`), class grants are level/archetype/option-gated and
repeat-count-aware (`sheet.py`'s `_granted_class_ability_ids`, `rules/speed.py`'s
`class_speed_bonus`) — since those gating rules differ by source and have
nothing to do with computing an effect. Only the "what does this ability id
compute" half is shared here.

Each source module (`race_abilities.py`, `speed.py`, `effects.py`) authors
its own slice of `HANDLERS` locally, for the same locality/git-blame reason
`base_class_abilities.json`/`base_race_abilities.json` stay separate
fixture files rather than one combined one; this module only merges them.
Ability ids are globally unique across catalogs (each is its own hand-frozen
UUID, see `race_abilities.py`'s docstring), so the merge can never silently
shadow one source's handler with another's.

Every entry takes the uniform `CharacterContext` signature (`rules/context.py`,
`roadmap.md`'s "Uniform CharacterContext handler signature") as of
2026-08-10/11 — `rules/effects.py`'s `EFFECT_HANDLERS` is folded in here too
now that the signature difference that used to keep it separate is gone (see
that module's docstring)."""

from collections.abc import Callable, Iterable
from uuid import UUID

from .context import CharacterContext
from .effects import EFFECT_HANDLERS as _EFFECT_HANDLERS
from .modifiers import Modifier
from .race_abilities import HANDLERS as _RACE_ABILITY_HANDLERS
from .speed import HANDLERS as _SPEED_HANDLERS

HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    **_RACE_ABILITY_HANDLERS,
    **_SPEED_HANDLERS,
    **_EFFECT_HANDLERS,
}


def resolve_ids(ability_ids: Iterable[UUID], context: CharacterContext) -> list[Modifier]:
    """`readme.md`'s "Request pipeline" step 3: every id resolved exactly
    once, against the same raw `context`, via this single merged registry.
    An id with no handler (flavor text, e.g. Darkvision, or a race's size
    trait today) just passes through with no computed effect."""
    modifiers: list[Modifier] = []
    for ability_id in ability_ids:
        handler = HANDLERS.get(ability_id)
        if handler is not None:
            modifiers.extend(handler(context))
    return modifiers


def character_modifiers(context: CharacterContext) -> list[Modifier]:
    """Every `Modifier` produced by composition sources that don't already
    have their own dedicated, repeat-count-aware resolution pipeline: feats,
    traits, and active effects (`context.feat_ids`/`trait_ids`/
    `active_effects`).

    Deliberately excludes `context.granted_ability_ids` (race + class
    granted abilities): a race's ability-score bonuses are already resolved
    into `context.ability_scores` itself before this ever runs
    (`rules/effective_scores.py`), and a class ability's other effects go
    through `rules/speed.py`'s `race_speed`/`class_speed_bonus`, which call
    a handler once *per qualifying grant*, not once per distinct id — a
    class ability shared by two grants on a multiclassed character (e.g.
    Barbar/Entfesselter Barbar's shared "Schnelle Bewegung" id, see
    `sheet.py`'s `_granted_class_ability_ids` docstring) must stack twice.
    This function's `ability_ids` are a plain deduplicated `set`, so routing
    `granted_ability_ids` through it too would silently drop that
    per-grant repetition. Once a granted-ability id needs a non-SCORE/
    non-SPEED effect, its resolution should move to a repeat-count-aware
    caller of `resolve_ids` alongside `class_speed_bonus`, not into this
    flat pass."""
    ids = context.feat_ids | context.trait_ids | {effect.source_id for effect in context.active_effects}
    return resolve_ids(ids, context)
