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


def race_ability_score_mods(db: Session, race_id: UUID) -> dict[str, int]:
    """Flat (non-flex) ability-score bonuses this race grants by default,
    e.g. Elf's +2 GE/-2 KO — via the same `HANDLERS` registry as everywhere
    else. Used wherever a *total* (not base) ability score is needed before
    item/effect modifiers exist yet, e.g. `routers/characters.py`'s
    skill-point budget check (skill points depend on total INT, not base)."""
    grants = db.scalars(
        select(RaceAbilityGrant).where(RaceAbilityGrant.race_id == race_id, RaceAbilityGrant.is_alternate.is_(False))
    ).all()
    mods: dict[str, int] = {}
    for grant in grants:
        ability = db.get(BaseRaceAbility, grant.ability_id)
        handler = HANDLERS.get(ability.id)
        if handler is None:
            continue
        attribute, value = handler()
        if attribute is not None:
            mods[attribute] = mods.get(attribute, 0) + value
    return mods


def resolve_flex_ability_id(db: Session, race_id: UUID, attribute: str) -> UUID | None:
    """Which alternate ability row grants +2 to `attribute` as this race's
    flex bonus, via the same `RaceAbilityGrant`/`RaceAbilityReplacement`
    composition used for every other racial choice — not a lookup table of
    attribute codes. Returns `None` if this race doesn't offer `attribute` as
    a flex choice (including if it has no flex bonus at all). The returned id
    is what `routers/characters.py` persists as a `CharacterRacialChoice`."""
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


def resolve_alt_trait(db: Session, race_id: UUID, name: str) -> tuple[UUID, set[UUID]] | None:
    """Resolves a chosen optional alternate-trait name (matching
    `_race_option`'s `alt[].name`) to its ability id plus the set of
    base-trait ability ids it replaces, scoped to this race. Returns `None`
    both when no such alternate exists for this race and when `name` refers
    to a flex-only alternate (empty `replaces` once the `ABILITY_ANY_PLUS2`
    marker is excluded) — those aren't valid `alt_traits` picks, they go
    through `flex_ability`/`resolve_flex_ability_id` instead. The returned
    ability id is what `routers/characters.py` persists as a
    `CharacterRacialChoice`, same table as the flex pick."""
    grant = db.scalar(
        select(RaceAbilityGrant)
        .join(BaseRaceAbility, BaseRaceAbility.id == RaceAbilityGrant.ability_id)
        .where(
            RaceAbilityGrant.race_id == race_id,
            RaceAbilityGrant.is_alternate.is_(True),
            BaseRaceAbility.name == name,
        )
    )
    if grant is None:
        return None
    replacements = db.scalars(
        select(RaceAbilityReplacement).where(
            RaceAbilityReplacement.base_race_id == race_id,
            RaceAbilityReplacement.ability_id == grant.ability_id,
            RaceAbilityReplacement.replaces_ability_id != ABILITY_ANY_PLUS2,
        )
    ).all()
    replaces = {r.replaces_ability_id for r in replacements}
    if not replaces:
        return None
    return grant.ability_id, replaces


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
