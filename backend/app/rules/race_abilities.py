"""Handler registry for racial ability effects (see CLAUDE.md: composition —
what a race grants — stays data; computing what an ability actually does
stays code).

The ids below are literal, hand-frozen UUIDs — the *only* link between this
module and the matching rows in
`backend/app/fixtures/seed/base_race_abilities.json`. They are never derived
(no hashing, no lookup by name/description text): a row's id in the JSON
either equals one of these constants (and gets a handler here) or it
doesn't (and it's a flavor-only ability, e.g. Darkvision, with no mechanical
effect modeled yet). If you change an id here, update the JSON row to match,
and vice versa — nothing enforces the link automatically.

Ability-score bonuses are the one case relevant to races today; they're the
same rulebook ability across races (e.g. "+2 auf einen Attributswert" is one
concept shared by Human/Half-Elf/Half-Orc), so each occurring (attribute,
value) combination gets exactly one id/handler, reused by every race that
grants it.

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

# attribute=None means the player picks which attribute at character
# creation (e.g. Human's "Anpassungsfähig") — see module docstring above for
# how that choice is modeled/persisted.
ABILITY_GE_PLUS2 = UUID("8e4cf2e6-4510-4aa9-b2bb-9be8b47b0332")
ABILITY_IN_PLUS2 = UUID("dc5ec0fe-68ce-47e0-9d61-4a86f8f2e651")
ABILITY_KO_MINUS2 = UUID("f98fed0e-f32b-46c7-8575-34875bbab69a")
ABILITY_KO_PLUS2 = UUID("9a2bf962-3eee-41d6-acef-972fc4b65ec0")
ABILITY_WE_PLUS2 = UUID("f4278c92-0328-476d-818a-ae0ce9e0aaef")
ABILITY_CH_MINUS2 = UUID("15891f93-77b5-4ee2-85c2-3486fc7365e5")
ABILITY_CH_PLUS2 = UUID("1dfff0e2-95a6-4635-a76e-639a2dab82af")
ABILITY_ST_MINUS2 = UUID("8ccc99e8-00c5-4245-8fb0-73d7fcd5bbdb")
ABILITY_ST_PLUS2 = UUID("04d2de62-ece9-4345-be84-cf8bf00d94dd")
ABILITY_ANY_PLUS2 = UUID("2756eef0-10f0-42d4-a6d4-10f0b44ec4be")


def _attribute_bonus(*, attribute: str | None, value: int) -> tuple[str | None, int]:
    return (attribute, value)


# Select by UUID, then call the looked-up function to get its (attribute,
# value) — no separate schema column, no text parsing.
HANDLERS: dict[UUID, Callable[[], tuple[str | None, int]]] = {
    ABILITY_GE_PLUS2: functools.partial(_attribute_bonus, attribute="GE", value=2),
    ABILITY_IN_PLUS2: functools.partial(_attribute_bonus, attribute="IN", value=2),
    ABILITY_KO_MINUS2: functools.partial(_attribute_bonus, attribute="KO", value=-2),
    ABILITY_KO_PLUS2: functools.partial(_attribute_bonus, attribute="KO", value=2),
    ABILITY_WE_PLUS2: functools.partial(_attribute_bonus, attribute="WE", value=2),
    ABILITY_CH_MINUS2: functools.partial(_attribute_bonus, attribute="CH", value=-2),
    ABILITY_CH_PLUS2: functools.partial(_attribute_bonus, attribute="CH", value=2),
    ABILITY_ST_MINUS2: functools.partial(_attribute_bonus, attribute="ST", value=-2),
    ABILITY_ST_PLUS2: functools.partial(_attribute_bonus, attribute="ST", value=2),
    ABILITY_ANY_PLUS2: functools.partial(_attribute_bonus, attribute=None, value=2),
}
