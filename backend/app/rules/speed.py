"""Racial base speed — composition (which race grants which speed) is real
data (`RaceAbilityGrant`), same split as `rules/skill_points.py`. Unlike
ability-score bonuses, a race's speed grant maps to a formatted display
string, not an (attribute, value) pair, so it gets its own small handler
dict rather than sharing `rules/race_abilities.py`'s `HANDLERS`.

Every seeded race grants exactly one of these two (`race_seed.py`), so
`race_speed` always finds a value — no stored default needed, unlike the
old `BaseRace.speed` column this replaces."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import RaceAbilityGrant

RACE_NORMAL_SPEED_ABILITY_ID = UUID("2e0186d5-e532-4532-b7f7-b4c6f4834bde")
RACE_SLOW_SPEED_ABILITY_ID = UUID("9a5db666-54d4-4112-b750-dbb1abf1265d")

SPEED_HANDLERS: dict[UUID, str] = {
    RACE_NORMAL_SPEED_ABILITY_ID: "9 m",
    RACE_SLOW_SPEED_ABILITY_ID: "6 m",
}


def race_speed(db: Session, race_id: UUID) -> str | None:
    """This race's base speed, from its non-alternate speed grant."""
    grants = db.scalars(
        select(RaceAbilityGrant).where(RaceAbilityGrant.race_id == race_id, RaceAbilityGrant.is_alternate.is_(False))
    ).all()
    for grant in grants:
        value = SPEED_HANDLERS.get(grant.ability_id)
        if value is not None:
            return value
    return None
