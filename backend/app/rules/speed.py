"""Land speed — base (racial) plus any flat bonus from a granted class
ability. Composition (which race grants which base speed, which class
ability grants a bonus) is real data (`RaceAbilityGrant`/
`BaseClassAbilityGrant`), same split as `rules/skill_points.py`. Unlike most
ability-score bonuses, a race's speed grant maps to a plain meters value, not
an (attribute, value) pair, so it gets its own small handler dict rather than
sharing `rules/race_abilities.py`'s `HANDLERS`; class-granted speed bonuses
reuse that same shape.

Every seeded race grants exactly one of the two base-speed abilities
(`race_seed.py`), so `race_speed` always finds a value — no stored default
needed, unlike the old `BaseRace.speed` column this replaces.

`CLASS_SPEED_BONUS_HANDLERS` covers "Schnelle Bewegung" (+3 m at level 1):
one `BaseClassAbility` row/id shared by Barbar and Entfesselter Barbar via
two separate `BaseClassAbilityGrant` rows (same mechanic — identical bonus,
identical conditions — so one catalog row per CLAUDE.md/`race_abilities.py`'s
"same rulebook ability shared by every grantor gets exactly one id" rule,
not one row per importing script). Applied unconditionally — RAW gates it on
wearing no more than medium armor and not being under a heavy load, but
armor weight category/encumbrance aren't modeled yet (`models/item.py` only
has `ac_bonus`/`max_dex_bonus`), same "honest simplification" `sheet.py`'s
`_build_equipment` documents for AC/CMB/CMD.

The handler value is a *per-grant* bonus, not a one-time flat one:
`class_speed_bonus` multiplies it by how many of that ability's
`BaseClassAbilityGrant` rows the character currently qualifies for
(`sheet.py`'s `_granted_class_ability_ids` `Counter`). Barbar's "Schnelle
Bewegung" only ever has one grant per class (count always 0 or 1), so this
degrades to the old flat-bonus behavior for it — but the same dict/function
is ready for a genuinely repeating bonus like Mönch's "Schnelligkeit" (+3 m
at 3./6./9./12./15./18. Stufe, real stacking per threshold reached), once
that class's own grants are actually imported (not done yet — see
todos.md)."""

from collections import Counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import RaceAbilityGrant

RACE_NORMAL_SPEED_ABILITY_ID = UUID("2e0186d5-e532-4532-b7f7-b4c6f4834bde")
RACE_SLOW_SPEED_ABILITY_ID = UUID("9a5db666-54d4-4112-b750-dbb1abf1265d")

SPEED_HANDLERS: dict[UUID, int] = {
    RACE_NORMAL_SPEED_ABILITY_ID: 9,
    RACE_SLOW_SPEED_ABILITY_ID: 6,
}

# BaseClassAbility id -> land-speed bonus in meters *per currently-qualified
# grant* of that ability (see module docstring on why this isn't just a
# one-time flat bonus).
CLASS_SPEED_BONUS_HANDLERS: dict[UUID, int] = {
    UUID("b311443b-a086-52ae-a079-d31880638921"): 3,  # Schnelle Bewegung (Barbar + Entfesselter Barbar)
}


def race_speed(db: Session, race_id: UUID) -> int | None:
    """This race's base land speed in meters, from its non-alternate speed
    grant."""
    grants = db.scalars(
        select(RaceAbilityGrant).where(RaceAbilityGrant.race_id == race_id, RaceAbilityGrant.is_alternate.is_(False))
    ).all()
    for grant in grants:
        value = SPEED_HANDLERS.get(grant.ability_id)
        if value is not None:
            return value
    return None


def class_speed_bonus(granted_class_ability_counts: Counter[UUID]) -> int:
    """Total land-speed bonus (meters) from this character's actually-granted
    class abilities (`sheet.py`'s `_granted_class_ability_ids` — already
    resolved against level count/archetype/option picks). Each handler's
    value is per-grant, so a repeatedly-granted ability (e.g. a class's own
    fast-movement feature reappearing every few levels) is counted once per
    qualifying grant, not just once for being present at all."""
    return sum(
        bonus * granted_class_ability_counts[ability_id] for ability_id, bonus in CLASS_SPEED_BONUS_HANDLERS.items()
    )
