from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseRace, BaseRaceAbility, RaceAbilityGrant, RaceAbilityReplacement
from ..rules.race_abilities import HANDLERS

router = APIRouter(prefix="/api/races", tags=["races"])


@router.get("")
def list_races(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    races = db.scalars(select(BaseRace).order_by(BaseRace.name)).all()
    return [_race_option(db, race) for race in races]


def _race_option(db: Session, race: BaseRace) -> dict:
    """Reconstructs the frontend's `RaceOption` shape (id, name, short, flex,
    mods, traits, alt) from the normalized composition tables. Ability-score
    bonuses are recognized by looking their ability id up in the handler
    registry (`HANDLERS`) — select by UUID, call the function, get
    (attribute, value) back — rather than a stored column, and are
    represented only via `flex`/`mods`, never duplicated as a `traits` entry
    too, unlike the old fixture data."""
    grants = db.scalars(select(RaceAbilityGrant).where(RaceAbilityGrant.race_id == race.id)).all()

    mods: dict[str, int] = {}
    flex = False
    traits: list[dict] = []
    alt_grants: list[tuple[RaceAbilityGrant, BaseRaceAbility]] = []
    base_ability_names: dict = {}

    for grant in grants:
        ability = db.get(BaseRaceAbility, grant.ability_id)
        handler = HANDLERS.get(ability.id)

        if grant.is_alternate:
            alt_grants.append((grant, ability))
            continue

        base_ability_names[ability.id] = ability.name
        if handler is not None:
            attribute, value = handler()
            if attribute is None:
                flex = True
            else:
                mods[attribute] = value
        else:
            traits.append({"name": ability.name, "desc": ability.description})

    alt: list[dict] = []
    for grant, ability in alt_grants:
        replacements = db.scalars(
            select(RaceAbilityReplacement).where(
                RaceAbilityReplacement.base_race_id == race.id,
                RaceAbilityReplacement.ability_id == ability.id,
            )
        ).all()
        replaces = [base_ability_names.get(r.replaces_ability_id, "?") for r in replacements]
        alt.append({"name": ability.name, "desc": ability.description, "replaces": replaces})

    return {
        "id": str(race.id),
        "name": race.name,
        "short": race.short_description,
        "flex": flex,
        "mods": mods,
        "traits": traits,
        "alt": alt,
    }
