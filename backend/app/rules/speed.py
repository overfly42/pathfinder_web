"""Land speed — base (racial) plus any bonus from a granted class ability,
composed via the shared `Modifier`/`stack()` primitive (`rules/modifiers.py`)
through the same unified ability-effect registry `rules/race_abilities.py`
uses for ability-score bonuses (see `rules/handlers.py`, which merges every
family's `HANDLERS` into the one dict `sheet.py` ultimately looks up
against) — composition (which race/class grants which speed-affecting
ability) is real data (`RaceAbilityGrant`/`BaseClassAbilityGrant`), same
split as `rules/skill_points.py`; only the *computation* (how many meters,
and how it stacks) lives here.

Every seeded race grants exactly one of the two base-speed abilities
(`race_seed.py`), so `race_speed` always finds a value — no stored default
needed, unlike the old `BaseRace.speed` column this replaces. Race-tied
content stays local to this module's own `HANDLERS` (same locality/
git-blame reason `race_abilities.py` keeps its own slice too).

`fast_movement` is the generic, reusable factory a class's own fast-movement
ability partial-applies (e.g. `rules/classes/barbarian.py`'s "Schnelle
Bewegung", CLAUDE.md's "trivial cases share one generic handler factory"
guidance) — a *class*-granted ability, so its concrete id/registration lives
in that class's own file (`rules/classes/`, one file per class — CLAUDE.md's
"Working Conventions"), not here; this module only hosts the shape every
such ability shares. `class_speed_bonus` below therefore looks up a granted
ability id against `rules/handlers.py`'s full merged registry, not this
module's own smaller `HANDLERS` — the id could now live in any class file."""

import functools
from collections import Counter
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .context import CharacterContext
from .modifiers import Modifier, ModifierTarget, stack

RACE_NORMAL_SPEED_ABILITY_ID = UUID("2e0186d5-e532-4532-b7f7-b4c6f4834bde")
RACE_SLOW_SPEED_ABILITY_ID = UUID("9a5db666-54d4-4112-b750-dbb1abf1265d")


def _base_speed(context: CharacterContext, *, meters: int) -> list[Modifier]:
    # Unconditional, same as race_abilities.py's `_attribute_bonus` — a
    # race's base speed never depends on anything about the character it's
    # granted to.
    del context
    return [Modifier(source="race", type="base", value=meters, target=ModifierTarget.SPEED)]


def fast_movement(context: CharacterContext, *, meters: int) -> list[Modifier]:
    """A flat, always-stacking (`type="untyped"`) bonus to land speed —
    the shape PF1e's various "fast movement"-style class features share
    (Barbar/Entfesselter Barbar's "Schnelle Bewegung", Mönch's
    "Schnelligkeit", ...): per PF1e RAW text ("dieser Bonus ist kumulativ
    mit allen anderen Boni... auf seine Bewegungsrate an Land"), deliberately
    not a one-time flat add. `class_speed_bonus` below calls a granted
    ability's handler once per currently-qualified grant, not once per
    distinct id, so a genuinely repeating fast-movement feature (granted
    again at higher levels) stacks correctly with no change needed here —
    each class file just registers its own ability id against this same
    factory, parameterized with its own `meters`."""
    # Unconditional: ownership/repetition count is already decided by the
    # caller (`class_speed_bonus`'s per-grant loop below), not by anything
    # this handler would read off `context` itself.
    del context
    return [Modifier(source="Schnelle Bewegung", type="untyped", value=meters, target=ModifierTarget.SPEED)]


# This module's own slice of `rules/handlers.py`'s unified `HANDLERS` —
# race-tied speed content only. A class's fast-movement ability (built from
# `fast_movement` above) registers its id in that class's own file under
# `rules/classes/`, not here.
HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    RACE_NORMAL_SPEED_ABILITY_ID: functools.partial(_base_speed, meters=9),
    RACE_SLOW_SPEED_ABILITY_ID: functools.partial(_base_speed, meters=6),
}

# `race_speed` only ever resolves a race's own base-speed grant, never
# anything conditional on a character — same reasoning as
# `routers/races.py`'s `_NO_CHARACTER_CONTEXT` (that module's `HANDLERS`
# entries, from `race_abilities.py`, share the exact same "ignores context"
# property as `_base_speed` above).
_NO_CHARACTER_CONTEXT = CharacterContext()


def race_speed(db: Session, race_id: UUID) -> int | None:
    """This race's base land speed in meters, from its non-alternate speed
    grant."""
    # Imported here, not at module level: `rules/handlers.py` merges this
    # module's `HANDLERS` for `models/character.py` to use, and
    # `models/character.py` loads partway through `models/__init__.py`
    # (before `RaceAbilityGrant` is defined there) — a module-level `from
    # ..models import RaceAbilityGrant` here would make that a circular
    # import. Deferred to call time, well after `models` is fully loaded.
    from ..models import RaceAbilityGrant

    grants = db.scalars(
        select(RaceAbilityGrant).where(RaceAbilityGrant.race_id == race_id, RaceAbilityGrant.is_alternate.is_(False))
    ).all()
    modifiers: list[Modifier] = []
    for grant in grants:
        handler = HANDLERS.get(grant.ability_id)
        if handler is not None:
            modifiers.extend(m for m in handler(_NO_CHARACTER_CONTEXT) if m.target == ModifierTarget.SPEED)
    return stack(modifiers) if modifiers else None


def class_speed_bonus(granted_class_ability_counts: Counter[UUID], context: CharacterContext) -> int:
    """Total land-speed bonus (meters) from this character's actually-granted
    class abilities (`sheet.py`'s `_granted_class_ability_ids` — already
    resolved against level count/archetype/option picks). The handler is
    called once per qualifying grant, not once per distinct ability id, so a
    repeatedly-granted fast-movement feature stacks correctly (see
    `fast_movement`'s docstring).

    Looks a granted ability id up against `rules/handlers.py`'s full merged
    registry, not this module's own `HANDLERS`: a class's fast-movement
    ability is registered in that class's own file under `rules/classes/`
    (CLAUDE.md's "Working Conventions"), which could be any of them — this
    function has no way to know which one without asking the merged
    registry. Imported here, not at module level, since `rules/handlers.py`
    itself imports this module's own `HANDLERS` — a module-level import here
    would be circular."""
    from .handlers import HANDLERS as _MERGED_HANDLERS

    modifiers: list[Modifier] = []
    for ability_id, count in granted_class_ability_counts.items():
        handler = _MERGED_HANDLERS.get(ability_id)
        if handler is None:
            continue
        for _ in range(count):
            modifiers.extend(m for m in handler(context) if m.target == ModifierTarget.SPEED)
    return stack(modifiers)


def jump_skill_bonus(total_land_speed: int) -> int:
    """Volksbonus (PF1e "racial" bonus type, `type="racial"` on a `Modifier`
    if/once this feeds one) on Akrobatik checks specifically to jump
    (Hoch-/Weitsprung), per the Akrobatik skill's "Springen" rule: +4 per
    full 3 m the character's *already fully resolved* land speed
    (`race_speed(...) + class_speed_bonus(...)`, not just the racial part)
    is above 9 m, or -4 per full 3 m it's below — partial 3 m steps don't
    count (a character at 11 m gets +0, not a fraction of +4).

    Deliberately not a `HANDLERS` entry: nothing grants this, it's an
    automatic consequence of a character's resolved speed, so there's no
    ability/feat/trait catalog row (no UUID) to key a handler off of — a
    fixed formula belongs in the derivation phase alongside
    `rules/progression.py`'s `ability_mod`, not the composition-driven
    registry. Only applies to jump checks, not Akrobatik's other uses
    (Balancieren, Abrollen, ...), so `sheet.py`'s `_build_skills` never folds
    it into the general Akrobatik `value` shown on the skill row — it only
    appears combined with that value in the row's info-note (a ready-to-roll
    jump total), computed there, not here."""
    diff = total_land_speed - 9
    increments = abs(diff) // 3
    return 4 * increments if diff >= 0 else -4 * increments
