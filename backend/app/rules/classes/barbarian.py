"""Barbar + Entfesselter Barbar (unchained Barbarian) handlers — one file
per class, closely related variants sharing a file (CLAUDE.md's "Working
Conventions"): the two are the same rulebook character concept, and their
mechanics either share an id outright ("Schnelle Bewegung" below) or are
independently worded/tuned variants of the same feature (each has its own
Kampfrausch — see roadmap.md — so those get separate ids, not a shared one).

Feeds `rules/handlers.py`'s unified `HANDLERS`, same merge-only role
`race_abilities.py`/`speed.py` play for their own slices — this file owns
every Barbar/Entfesselter-Barbar ability id and its computation; nothing
outside it should reference these ids directly."""

import functools
from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..modifiers import Modifier, ModifierTarget
from ..speed import fast_movement

# "Schnelle Bewegung" (+3 m at level 1): one `BaseClassAbility` row/id shared
# by Barbar and Entfesselter Barbar via two separate `BaseClassAbilityGrant`
# rows (same mechanic — identical bonus, identical conditions — so one
# catalog row per CLAUDE.md/`race_abilities.py`'s "same rulebook ability
# shared by every grantor gets exactly one id" rule, not one row per
# importing script). Built from `rules/speed.py`'s generic `fast_movement`
# factory — see that module for the RAW-text reasoning behind its
# always-stacking `type="untyped"` bonus and its class-agnostic shape.
# Applied unconditionally — RAW gates it on wearing no more than medium
# armor and not being under a heavy load, but armor weight category/
# encumbrance aren't modeled yet (`models/item.py` only has `ac_bonus`/
# `max_dex_bonus`), same "honest simplification" `sheet.py`'s
# `_build_equipment` documents for AC/CMB/CMD.
BARBAR_SCHNELLE_BEWEGUNG_ABILITY_ID = UUID("b311443b-a086-52ae-a079-d31880638921")

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


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    BARBAR_SCHNELLE_BEWEGUNG_ABILITY_ID: functools.partial(fast_movement, meters=3),
    KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID: _kampfrausch_entfesselter_barbar,
}
