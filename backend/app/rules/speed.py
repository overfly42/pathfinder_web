"""Land speed — base (racial) plus any bonus from a granted class ability,
composed via the shared `Modifier`/`stack()` primitive (`rules/modifiers.py`)
through the same unified ability-effect registry `rules/race_abilities.py`
uses for ability-score bonuses (see `rules/handlers.py`, which merges both
modules' `HANDLERS` into the one dict `sheet.py` ultimately looks up
against) — composition (which race/class grants which speed-affecting
ability) is real data (`RaceAbilityGrant`/`BaseClassAbilityGrant`), same
split as `rules/skill_points.py`; only the *computation* (how many meters,
and how it stacks) lives here.

Every seeded race grants exactly one of the two base-speed abilities
(`race_seed.py`), so `race_speed` always finds a value — no stored default
needed, unlike the old `BaseRace.speed` column this replaces.

"Schnelle Bewegung" (+3 m at level 1): one `BaseClassAbility` row/id shared
by Barbar and Entfesselter Barbar via two separate `BaseClassAbilityGrant`
rows (same mechanic — identical bonus, identical conditions — so one catalog
row per CLAUDE.md/`race_abilities.py`'s "same rulebook ability shared by
every grantor gets exactly one id" rule, not one row per importing script).
Its handler's `Modifier` is `type="untyped"` (`modifiers.ALWAYS_STACKS`) per
its own RAW text ("dieser Bonus ist kumulativ mit allen anderen Boni... auf
seine Bewegungsrate an Land") — deliberately not a one-time flat add:
`class_speed_bonus` calls the handler once per currently-qualified grant
(`sheet.py`'s `_granted_class_ability_ids` `Counter`), so a genuinely
repeating fast-movement feature (e.g. Mönch's Schnelligkeit, +3 m at
3./6./9./12./15./18. Stufe — not imported yet, see todos.md) would stack
correctly the moment its own grants exist, with no change needed here.
Applied unconditionally — RAW gates it on wearing no more than medium armor
and not being under a heavy load, but armor weight category/encumbrance
aren't modeled yet (`models/item.py` only has `ac_bonus`/`max_dex_bonus`),
same "honest simplification" `sheet.py`'s `_build_equipment` documents for
AC/CMB/CMD."""

import functools
from collections import Counter
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import RaceAbilityGrant
from .modifiers import Modifier, ModifierTarget, stack

RACE_NORMAL_SPEED_ABILITY_ID = UUID("2e0186d5-e532-4532-b7f7-b4c6f4834bde")
RACE_SLOW_SPEED_ABILITY_ID = UUID("9a5db666-54d4-4112-b750-dbb1abf1265d")
BARBAR_SCHNELLE_BEWEGUNG_ABILITY_ID = UUID("b311443b-a086-52ae-a079-d31880638921")


def _base_speed(*, meters: int) -> list[Modifier]:
    return [Modifier(source="race", type="base", value=meters, target=ModifierTarget.SPEED)]


def _fast_movement(*, meters: int) -> list[Modifier]:
    return [Modifier(source="Schnelle Bewegung", type="untyped", value=meters, target=ModifierTarget.SPEED)]


# Feeds `rules/handlers.py`'s unified `HANDLERS` — kept local to this module
# (not that merged dict) for the same locality/git-blame reason
# `race_abilities.py` keeps its own `HANDLERS` slice separate too.
HANDLERS: dict[UUID, Callable[[], list[Modifier]]] = {
    RACE_NORMAL_SPEED_ABILITY_ID: functools.partial(_base_speed, meters=9),
    RACE_SLOW_SPEED_ABILITY_ID: functools.partial(_base_speed, meters=6),
    BARBAR_SCHNELLE_BEWEGUNG_ABILITY_ID: functools.partial(_fast_movement, meters=3),
}


def race_speed(db: Session, race_id: UUID) -> int | None:
    """This race's base land speed in meters, from its non-alternate speed
    grant."""
    grants = db.scalars(
        select(RaceAbilityGrant).where(RaceAbilityGrant.race_id == race_id, RaceAbilityGrant.is_alternate.is_(False))
    ).all()
    modifiers: list[Modifier] = []
    for grant in grants:
        handler = HANDLERS.get(grant.ability_id)
        if handler is not None:
            modifiers.extend(m for m in handler() if m.target == ModifierTarget.SPEED)
    return stack(modifiers) if modifiers else None


def class_speed_bonus(granted_class_ability_counts: Counter[UUID]) -> int:
    """Total land-speed bonus (meters) from this character's actually-granted
    class abilities (`sheet.py`'s `_granted_class_ability_ids` — already
    resolved against level count/archetype/option picks). The handler is
    called once per qualifying grant, not once per distinct ability id, so a
    repeatedly-granted fast-movement feature stacks correctly (see module
    docstring)."""
    modifiers: list[Modifier] = []
    for ability_id, count in granted_class_ability_counts.items():
        handler = HANDLERS.get(ability_id)
        if handler is None:
            continue
        for _ in range(count):
            modifiers.extend(m for m in handler() if m.target == ModifierTarget.SPEED)
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
    registry. Only applies to jump checks, not the general Akrobatik total
    shown in `sheet.py`'s skill list — not wired into `_build_skills` (see
    that decision's discussion in conversation)."""
    diff = total_land_speed - 9
    increments = abs(diff) // 3
    return 4 * increments if diff >= 0 else -4 * increments
