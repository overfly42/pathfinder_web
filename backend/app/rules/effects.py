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


# "Defensiv kämpfen" (Fighting Defensively as a standard action, GRW Kampf
# chapter) — not a RAW "Zustand", but modeled as a `BaseCondition` row
# (`base_conditions.json` id 2b469d79-…, `default_duration_rounds=1`, "bis
# zum Beginn deines nächsten Zuges") since that's exactly the round-based
# activate/duration/advance-time machinery this needs, with no new mechanism
# required — same reuse as `_erschoepft` above. GRW: "Malus von -4 auf alle
# Angriffe in deiner Runde... Ausweichbonus +2 auf deine RK." Both modifier
# types (`dodge`/`untyped`) are in `ALWAYS_STACKS` (`rules/modifiers.py`), so
# Kranichstils eigener Offset-Bonus (`rules/feats.py`'s `_kranichstil`, +2
# ATTACK to bring the malus from -4 to -2) einfach dazu addiert wird statt
# diese Basiszahl ersetzen zu müssen — kein Sonderfall in `stack()` nötig.
#
# Known, documented simplification (same shape `_build_weapon_attacks`'s own
# docstring already flags for `ModifierTarget.ATTACK` generally): this only
# reaches melee attacks (`sheet.py`'s `melee_attack_bonus`), not ranged ones
# — PF1e RAW actually penalizes every attack this round, melee and ranged
# alike, but the app's shared ATTACK-stacking pipeline is melee-only
# end-to-end today (Kampfrausch's flat +2 has the exact same gap).
DEFENSIV_KAEMPFEN_CONDITION_ID = UUID("2b469d79-809a-530a-ac06-a1214bdc2181")


def _defensiv_kaempfen(context: CharacterContext) -> list[Modifier]:
    """Doesn't scale with instance count — same "presence, not sum" reasoning
    `_erschoepft` documents: fighting defensively twice at once isn't a
    thing."""
    instances = [e for e in context.active_effects if e.source_id == DEFENSIV_KAEMPFEN_CONDITION_ID]
    if not instances:
        return []
    return [
        Modifier(source="Defensiv kämpfen", type="dodge", value=2, target=ModifierTarget.AC),
        Modifier(source="Defensiv kämpfen", type="untyped", value=-4, target=ModifierTarget.ATTACK),
    ]


# "Volle Verteidigung" (Total Defense as a standard action, GRW Kampf
# chapter) — same "`BaseCondition` row reusing the round-based effect
# machinery" reasoning as `DEFENSIV_KAEMPFEN_CONDITION_ID` above
# (`base_conditions.json` id 18eaadc6-…, `default_duration_rounds=1`). GRW:
# "+4 Ausweichbonus auf RK eine Runde lang." No `ATTACK` modifier: Total
# Defense makes no attacks at all (a standard action spent entirely on
# defense), unlike Defensiv kämpfen's attack/AC trade-off.
VOLLE_VERTEIDIGUNG_CONDITION_ID = UUID("18eaadc6-8ed4-5817-9a6e-d14c67e6ef50")


def _volle_verteidigung(context: CharacterContext) -> list[Modifier]:
    """Same "presence, not sum" reasoning as `_erschoepft`/`_defensiv_kaempfen`."""
    instances = [e for e in context.active_effects if e.source_id == VOLLE_VERTEIDIGUNG_CONDITION_ID]
    if not instances:
        return []
    return [Modifier(source="Volle Verteidigung", type="dodge", value=4, target=ModifierTarget.AC)]


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


# Rindenhaut (Barkskin, `base_spells.json` id 630d626a-…). PRD text:
# "Verbesserungsbonus von +2 auf einen bereits vorhandenen natürlichen
# Rüstungsbonus. Dieser Verbesserungsbonus steigt alle 3 Zauberstufen über
# der dritten um +1, bis zu einem Maximum von +5 auf der 12. Stufe" — an
# *enhancement* bonus to natural armor, not a natural-armor bonus itself
# (RAW: it stacks with an actual natural armor bonus, e.g. a race's own,
# rather than capping against it the way two natural-armor bonuses would),
# hence `type="enhancement"` rather than a new "natural armor" type; grouped
# by target only (`stack_by_target`), so this never collides with an
# ability-score enhancement bonus's own "enhancement" type on `SCORE`. Scales
# with the caster level entered at activation (`CharacterEffect.level`), same
# per-instance-value shape as `_schild_des_glaubens`. The "Legendäre
# Rindenhaut" SR upgrade in the same description isn't modeled (same "no
# mythic layer" scope `_magierruestung` documents).
RINDENHAUT_SPELL_ID = UUID("630d626a-8f69-585f-a1ad-601b52d18039")


def _rindenhaut(context: CharacterContext) -> list[Modifier]:
    instances = [e for e in context.active_effects if e.source_id == RINDENHAUT_SPELL_ID]
    return [
        Modifier(
            source="Rindenhaut",
            type="enhancement",
            value=min(5, 2 + max(0, ((effect.level or 0) - 3) // 3)),
            target=ModifierTarget.AC,
        )
        for effect in instances
    ]


# Katzenhafte Anmut (Cat's Grace, `base_spells.json` id 7c57251a-…). PRD
# text: "Verbesserungsbonus von +4 auf Geschicklichkeit" — flat, doesn't
# scale with caster level, same "presence, not sum" shape as
# `_magierruestung`; the "übliche Vorteile für RK, Reflexwürfe ... GE-
# Modifikator" the description calls out need no separate handling here,
# since every one of those already reads the character's `SCORE`/"GE"
# modifier downstream (`sheet.py`), not a copy of it.
KATZENHAFTE_ANMUT_SPELL_ID = UUID("7c57251a-6b49-54c1-b149-e35cf2c36d0d")


def _katzenhafte_anmut(context: CharacterContext) -> list[Modifier]:
    instances = [e for e in context.active_effects if e.source_id == KATZENHAFTE_ANMUT_SPELL_ID]
    if not instances:
        return []
    return [Modifier(source="Katzenhafte Anmut", type="enhancement", value=4, target=ModifierTarget.SCORE, target_id="GE")]


EFFECT_HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    ERSCHOPFT_CONDITION_ID: _erschoepft,
    DEFENSIV_KAEMPFEN_CONDITION_ID: _defensiv_kaempfen,
    VOLLE_VERTEIDIGUNG_CONDITION_ID: _volle_verteidigung,
    MAGIERRUESTUNG_SPELL_ID: _magierruestung,
    SCHILD_DES_GLAUBENS_SPELL_ID: _schild_des_glaubens,
    RINDENHAUT_SPELL_ID: _rindenhaut,
    KATZENHAFTE_ANMUT_SPELL_ID: _katzenhafte_anmut,
}
