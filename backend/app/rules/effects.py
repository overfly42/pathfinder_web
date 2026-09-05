"""Handler registry for active effects that aren't tied to a single class —
conditions, poisons, diseases, and spells (`todos.md`'s "Effekt-Handler-
Inventar" tracks the concrete remaining inventory — a spell isn't tied to
one class either, so it stays here rather than under `rules/classes/`).
Effects that *are* a specific class's own ability (e.g. a barbarian rage
power) belong in that class's own file under `rules/classes/` instead
(CLAUDE.md's "Working Conventions") — Entfesselter Barbar's Kampfrausch,
this registry's first and only content until 2026-08-11, moved there for
exactly that reason.

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
from .modifiers import Modifier, ModifierTarget

# "Erschöpft" (Fatigued, `base_conditions.json` row cb149263-…) — granted
# automatically when Entfesselter Barbar's Kampfrausch ends
# (`rules/classes/barbarian.py`'s `_kampfrausch_entfesselter_barbar_end`,
# which imports this id) as well as activatable directly like any other
# condition. PRD text: "-2 auf Stärke und Geschicklichkeit"; the run/charge
# ban isn't modeled — no action-economy engine exists anywhere in this
# codebase to gate against, same "narrative only" scope every other
# condition currently has (`todos.md`'s "Effekt-Handler-Inventar").
ERSCHOPFT_CONDITION_ID = UUID("cb149263-435d-52f1-93c5-72fb0a01ff85")


def _erschoepft(context: CharacterContext) -> list[Modifier]:
    """Doesn't scale with instance count — same "self-scoped toggle,
    presence not sum" reasoning `rules/classes/barbarian.py`'s
    `_kampfrausch_entfesselter_barbar` documents for its own flat bonus:
    being Erschöpft from two sources at once isn't worse than from one."""
    instances = [e for e in context.active_effects if e.source_id == ERSCHOPFT_CONDITION_ID]
    if not instances:
        return []
    return [
        Modifier(source="Erschöpft", type="untyped", value=-2, target=ModifierTarget.SCORE, target_id="ST"),
        Modifier(source="Erschöpft", type="untyped", value=-2, target=ModifierTarget.SCORE, target_id="GE"),
    ]


# Magierrüstung (Mage Armor, `base_spells.json` id b987fa2d-…) — first
# `BaseSpell` marked `is_persistent_effect`. PRD text: +4 armor bonus to AC;
# the "legendäre" +6/critical-negation upgrade in the same description is a
# mythic-rules variant, not a separate catalog row, so it isn't modeled
# (same "no mythic layer" scope everything else in this codebase has).
MAGIERRUESTUNG_SPELL_ID = UUID("b987fa2d-d38f-5913-8073-93a4f671a92e")


def _magierruestung(context: CharacterContext) -> list[Modifier]:
    """An "armor"-type `Modifier` correctly never stacks with worn armor's
    own armor bonus, or with a second casting (`stack()`'s same-type-cap
    rule) — both are RAW. Doesn't scale with instance count for the same
    reason `_erschoepft` doesn't: presence, not sum, is all that matters
    once the type cap already caps it."""
    instances = [e for e in context.active_effects if e.source_id == MAGIERRUESTUNG_SPELL_ID]
    if not instances:
        return []
    return [Modifier(source="Magierrüstung", type="armor", value=4, target=ModifierTarget.AC)]


# Schild des Glaubens (Shield of Faith, `base_spells.json` id ced7dda5-…).
# PRD text: "Ablenkungsbonus von +2 auf die RK +1 pro sechs Zauberstufen
# (maximaler Ablenkungsbonus von +5 auf der 18. Stufe)" — unlike
# Magierrüstung's flat bonus, this one scales with the caster level entered
# at activation (`CharacterEffect.level`), so each active instance gets its
# own `Modifier` value rather than one flat constant; `stack()`'s
# same-type-cap rule (a "deflection" bonus, explicitly called out in
# `modifiers.py`'s own docstring as a capped type) still correctly picks the
# highest one if the character somehow has two active at once, same
# "presence, not sum" outcome `_magierruestung` gets from an explicit early
# return. The "Legendärer" mythic-tier addition in the same description
# isn't modeled (same "no mythic layer" scope `_magierruestung` documents).
SCHILD_DES_GLAUBENS_SPELL_ID = UUID("ced7dda5-77df-53f3-8028-bde2dc433fd2")


def _schild_des_glaubens(context: CharacterContext) -> list[Modifier]:
    instances = [e for e in context.active_effects if e.source_id == SCHILD_DES_GLAUBENS_SPELL_ID]
    return [
        Modifier(
            source="Schild des Glaubens",
            type="deflection",
            value=min(5, 2 + (effect.level or 0) // 6),
            target=ModifierTarget.AC,
        )
        for effect in instances
    ]


EFFECT_HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    ERSCHOPFT_CONDITION_ID: _erschoepft,
    MAGIERRUESTUNG_SPELL_ID: _magierruestung,
    SCHILD_DES_GLAUBENS_SPELL_ID: _schild_des_glaubens,
}
