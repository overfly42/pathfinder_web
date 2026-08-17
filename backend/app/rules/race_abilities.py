"""Handler registry for racial ability effects (see CLAUDE.md: composition —
what a race grants — stays data; computing what an ability actually does
stays code). Feeds `rules/handlers.py`'s unified `HANDLERS`, the one registry
every consumer (ability-score composition here, land speed in
`rules/speed.py`) looks up by ability UUID — see that module for why.

First family migrated (2026-08-10) to the uniform `CharacterContext` handler
signature (`rules/context.py`, `roadmap.md`'s "Uniform CharacterContext
handler signature") — every call site now passes a `CharacterContext`, even
though `_attribute_bonus` itself ignores it (a race's ability-score bonus is
never conditional on anything about the character). `rules/speed.py`'s and
`rules/effects.py`'s `HANDLERS`/`EFFECT_HANDLERS` haven't moved to this
signature yet (`todos.md`'s "Handler-Migration zu CharacterContext" tracks
the rest).

The ids below are literal, hand-frozen UUIDs — the *only* link between this
module and the matching rows in
`backend/app/fixtures/seed/base_race_abilities.json`. They are never derived
(no hashing, no lookup by name/description text): a row's id in the JSON
either equals one of these constants (and gets a handler here) or it
doesn't (and it's a flavor-only ability, e.g. Darkvision, with no mechanical
effect modeled yet). If you change an id here, update the JSON row to match,
and vice versa — nothing enforces the link automatically.

Ability-score bonuses are the main case; they're the same rulebook ability
across races (e.g. "+2 auf einen Attributswert" is one concept shared by
Human/Half-Elf/Half-Orc), so each occurring (attribute, value) combination
gets exactly one id/handler, reused by every race that grants it. Flat racial
skill bonuses (Halb-Ork's Einschüchternd — 2026-08-16) follow the same
"trivial one-liner" shape, just targeting `ModifierTarget.SKILL` instead of
`SCORE` — still small enough to live alongside the ability-score handlers
rather than needing their own file.

`ABILITY_ANY_PLUS2` ("Anpassungsfähig") is the one ability whose handler
returns `attribute=None` — the player picks at character creation. That
choice is modeled the same way as any other racial alternate-trait swap, not
as a special-cased scalar: each flex-granting race has 6 `is_alternate=True`
`RaceAbilityGrant` rows (one per `ABILITY_*_PLUS2`, reusing the same shared
catalog rows fixed-bonus races like Elf/Zwerg already use for their own
bonuses) plus matching `RaceAbilityReplacement` rows scoping each as
replacing `ABILITY_ANY_PLUS2` for that race. `ABILITY_ST_PLUS2` exists only
for this purpose today — no race grants a fixed +2 STÄ, so this is the sole
consumer of that catalog row. `routers/races.py`'s `resolve_flex_ability_id`
does the lookup; the character's actual pick is persisted as a
`CharacterRacialChoice` row, not a raw attribute-code column — the same
table optional alternate-trait picks use (see `routers/races.py`'s
`resolve_alt_trait`).
"""

import functools
from collections.abc import Callable
from uuid import UUID

from .context import CharacterContext
from .modifiers import Modifier, ModifierTarget, NaturalAttack

# attribute=None means the player picks which attribute at character
# creation (e.g. Human's "Anpassungsfähig") — see module docstring above for
# how that choice is modeled/persisted.
ABILITY_GE_PLUS2 = UUID("8e4cf2e6-4510-4aa9-b2bb-9be8b47b0332")
ABILITY_IN_PLUS2 = UUID("dc5ec0fe-68ce-47e0-9d61-4a86f8f2e651")
ABILITY_IN_MINUS2 = UUID("900f8f27-d0d8-43ec-a8a8-8e2473e8b2c8")
ABILITY_KO_MINUS2 = UUID("f98fed0e-f32b-46c7-8575-34875bbab69a")
ABILITY_KO_PLUS2 = UUID("9a2bf962-3eee-41d6-acef-972fc4b65ec0")
ABILITY_WE_PLUS2 = UUID("f4278c92-0328-476d-818a-ae0ce9e0aaef")
ABILITY_WE_MINUS2 = UUID("71cd3345-96eb-4b2d-9d43-365a4d25af77")
ABILITY_CH_MINUS2 = UUID("15891f93-77b5-4ee2-85c2-3486fc7365e5")
ABILITY_CH_PLUS2 = UUID("1dfff0e2-95a6-4635-a76e-639a2dab82af")
ABILITY_ST_MINUS2 = UUID("8ccc99e8-00c5-4245-8fb0-73d7fcd5bbdb")
ABILITY_ST_PLUS2 = UUID("04d2de62-ece9-4345-be84-cf8bf00d94dd")
ABILITY_ST_PLUS4 = UUID("c73e6c2e-6d66-459e-8789-bd5510d2a155")
ABILITY_ANY_PLUS2 = UUID("2756eef0-10f0-42d4-a6d4-10f0b44ec4be")

EINSCHUECHTERND = UUID("342e6626-6d77-47d5-a129-3a3ccc017088")
# `BaseSkill.id` for Einschüchtern (`base_skills.json`) — the one skill
# Einschüchternd's Volksbonus targets.
_EINSCHUECHTERN_SKILL_ID = "3c60b6e1-8c58-4ed0-9c3a-5e003b9da1cf"

# Halb-Ork's "Reißzähne" alternate racial trait (`race_ability_grants.json`,
# `is_alternate=True`; replaces "Orkische Wildheit" per
# `race_ability_replacements.json`) — a primary natural bite attack, 1W4
# piercing. Not in `HANDLERS` below: it produces a `NaturalAttack`, not a
# `Modifier`, so it lives in this module's own `NATURAL_ATTACK_HANDLERS`
# instead (merged into `rules/handlers.py`'s registry of the same name,
# same "each family owns its own slice" pattern `HANDLERS` already uses).
REISSZAEHNE_ABILITY_ID = UUID("91b06165-05ad-47b7-9732-18bdf36e1536")


def _attribute_bonus(context: CharacterContext, *, attribute: str | None, value: int) -> list[Modifier]:
    # Unconditional (a race's ability-score bonus never depends on anything
    # about the character it's granted to), so `context` goes unused here —
    # the parameter exists only to keep this handler's signature uniform
    # with every other `HANDLERS`/`EFFECT_HANDLERS` entry (`rules/context.py`,
    # `roadmap.md`'s "Uniform CharacterContext handler signature").
    del context
    return [
        Modifier(source="race ability", type="racial", value=value, target=ModifierTarget.SCORE, target_id=attribute)
    ]


def _skill_bonus(context: CharacterContext, *, source: str, skill_id: str, value: int) -> list[Modifier]:
    # Unconditional, same reasoning as `_attribute_bonus` above — a race's
    # flat skill Volksbonus never depends on anything about the character.
    # Unlike `_attribute_bonus`'s generic "race ability" (ability-score
    # `Modifier`s never reach a player-facing breakdown, that's out of scope
    # for now), `source` is the ability's own name here: `sheet.py`'s skill
    # breakdown (`_build_skills`) surfaces `Modifier.source` directly to the
    # player, so it must identify *which* ability granted the bonus, not
    # just "a race ability".
    del context
    return [
        Modifier(source=source, type="racial", value=value, target=ModifierTarget.SKILL, target_id=skill_id)
    ]


def _reisszaehne(context: CharacterContext) -> NaturalAttack:
    # Unconditional, same reasoning as `_attribute_bonus` above — a racial
    # trait's natural attack (unlike Bestientotem's rage-power claws,
    # `rules/classes/barbarian.py`) is always present once granted, not
    # gated on any active effect.
    del context
    return NaturalAttack(name="Biss", count=1, damage_dice="1W4", damage_type="S")


# Select by UUID, then call the looked-up function (with the caller's
# `CharacterContext`) to get its Modifier list — no separate schema column,
# no text parsing. `target_id=None` (flex, see module docstring) is the
# "player picks" marker every caller below checks for; a race never grants
# more than one ability-score `Modifier` per handler call, but the list
# shape matches every other entry in the unified `HANDLERS` registry
# (`rules/handlers.py`).
HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    ABILITY_GE_PLUS2: functools.partial(_attribute_bonus, attribute="GE", value=2),
    ABILITY_IN_PLUS2: functools.partial(_attribute_bonus, attribute="IN", value=2),
    ABILITY_IN_MINUS2: functools.partial(_attribute_bonus, attribute="IN", value=-2),
    ABILITY_KO_MINUS2: functools.partial(_attribute_bonus, attribute="KO", value=-2),
    ABILITY_KO_PLUS2: functools.partial(_attribute_bonus, attribute="KO", value=2),
    ABILITY_WE_PLUS2: functools.partial(_attribute_bonus, attribute="WE", value=2),
    ABILITY_WE_MINUS2: functools.partial(_attribute_bonus, attribute="WE", value=-2),
    ABILITY_CH_MINUS2: functools.partial(_attribute_bonus, attribute="CH", value=-2),
    ABILITY_CH_PLUS2: functools.partial(_attribute_bonus, attribute="CH", value=2),
    ABILITY_ST_MINUS2: functools.partial(_attribute_bonus, attribute="ST", value=-2),
    ABILITY_ST_PLUS2: functools.partial(_attribute_bonus, attribute="ST", value=2),
    ABILITY_ST_PLUS4: functools.partial(_attribute_bonus, attribute="ST", value=4),
    ABILITY_ANY_PLUS2: functools.partial(_attribute_bonus, attribute=None, value=2),
    EINSCHUECHTERND: functools.partial(
        _skill_bonus, source="Einschüchternd", skill_id=_EINSCHUECHTERN_SKILL_ID, value=2
    ),
}

# This module's own slice of `rules/handlers.py`'s merged
# `NATURAL_ATTACK_HANDLERS` — race-granted natural weapon attacks only (see
# `REISSZAEHNE_ABILITY_ID` above).
NATURAL_ATTACK_HANDLERS: dict[UUID, Callable[[CharacterContext], NaturalAttack | None]] = {
    REISSZAEHNE_ABILITY_ID: _reisszaehne,
}
