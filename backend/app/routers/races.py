from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseRace, BaseRaceAbility, RaceAbilityGrant, RaceAbilityReplacement
from ..rules.race_abilities import ABILITY_ANY_PLUS2, HANDLERS

router = APIRouter(prefix="/api/races", tags=["races"])


def race_has_flex(db: Session, race_id: UUID) -> bool:
    """Whether this race grants a player-chosen "+2 to any attribute" bonus
    (e.g. Human, Half-Elf, Half-Orc) — used to require/forbid
    `CharacterCreate.flex_ability` in `routers/characters.py`."""
    grants = db.scalars(
        select(RaceAbilityGrant).where(
            RaceAbilityGrant.race_id == race_id, RaceAbilityGrant.is_alternate.is_(False)
        )
    ).all()
    for grant in grants:
        ability = db.get(BaseRaceAbility, grant.ability_id)
        handler = HANDLERS.get(ability.id)
        if handler is not None and handler()[0] is None:
            return True
    return False


def resolve_flex_ability_id(db: Session, race_id: UUID, attribute: str) -> UUID | None:
    """Which alternate ability row grants +2 to `attribute` as this race's
    flex bonus, via the same `RaceAbilityGrant`/`RaceAbilityReplacement`
    composition used for every other racial choice — not a lookup table of
    attribute codes. Returns `None` if this race doesn't offer `attribute` as
    a flex choice (including if it has no flex bonus at all). The returned id
    is what `routers/characters.py` persists as a `CharacterAbilityChoice`."""
    replacements = db.scalars(
        select(RaceAbilityReplacement).where(
            RaceAbilityReplacement.base_race_id == race_id,
            RaceAbilityReplacement.replaces_ability_id == ABILITY_ANY_PLUS2,
        )
    ).all()
    for replacement in replacements:
        handler = HANDLERS.get(replacement.ability_id)
        if handler is not None and handler()[0] == attribute:
            return replacement.ability_id
    return None


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
        replaces = [
            base_ability_names.get(r.replaces_ability_id, "?")
            for r in replacements
            if r.replaces_ability_id != ABILITY_ANY_PLUS2
        ]
        if not replaces:
            # Purely a flex ability-bonus alternate (see
            # `resolve_flex_ability_id`), not a flavor alt-trait — surfaced
            # only via `flex` and the dedicated attribute picker, not here.
            continue
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
