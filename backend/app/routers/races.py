from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseRace, BaseRaceAbility, RaceAbilityGrant, RaceAbilityReplacement
from ..rules.context import CharacterContext
from ..rules.handlers import HANDLERS
from ..rules.modifiers import Modifier, ModifierTarget
from ..rules.race_abilities import ABILITY_ANY_PLUS2

router = APIRouter(prefix="/api/races", tags=["races"])

# These functions resolve race-level ability ids scoped only to a `race_id`
# — several run before a `Character` row exists at all (creation-time
# validation), so there's no real per-character state to build a
# `CharacterContext` from. An empty one is correct here regardless: every
# `HANDLERS` entry reachable from a *race* grant is `_attribute_bonus`
# (`race_abilities.py`), which never reads its `context` argument.
_NO_CHARACTER_CONTEXT = CharacterContext()


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
        if handler is None:
            continue
        modifier = handler(_NO_CHARACTER_CONTEXT)[0]
        # `HANDLERS` is the merged registry now (`rules/handlers.py`), so a
        # race's own base-speed grant resolves too — its `Modifier` also has
        # `target_id=None` (SPEED never sets it), the same shape the flex
        # placeholder uses. Must check `target == SCORE` explicitly, not just
        # `target_id is None`, or every race would look flex-eligible.
        if modifier.target == ModifierTarget.SCORE and modifier.target_id is None:
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
        modifier = handler(_NO_CHARACTER_CONTEXT)[0]
        # Explicit target check (not just `target_id is not None`): a race's
        # base-speed grant also resolves via the merged `HANDLERS` now, and
        # must not be folded into an ability-score dict.
        if modifier.target == ModifierTarget.SCORE and modifier.target_id is not None:
            mods[modifier.target_id] = mods.get(modifier.target_id, 0) + modifier.value
    return mods


def race_skill_modifiers(db: Session, race_id: UUID) -> list[Modifier]:
    """Every SKILL-target `Modifier` this race's own (non-alternate) grants
    produce, e.g. Halb-Ork's Einschüchternd (+2 Volksbonus on Einschüchtern).
    Same non-alternate-grant-only scope as `race_ability_score_mods` above —
    alt-trait replacement swaps aren't computed here either, the same
    existing gap those already have (`models/character.py`'s `alt_traits`
    resolves a chosen swap's *name* for display only, never its mechanical
    effect).

    Unlike SCORE (folded straight into effective ability scores) and SPEED
    (folded into total land speed, `rules/speed.py`'s `race_speed`) — both of
    which already have a dedicated resolution path — a race's SKILL bonus has
    none yet, so this returns raw `Modifier`s for `sheet.py` to merge into
    its own `all_modifiers` list *before* `stack_by_target`, same "combine
    before stacking" reasoning that list's own docstring already spells out
    for gear's AC bonus."""
    grants = db.scalars(
        select(RaceAbilityGrant).where(RaceAbilityGrant.race_id == race_id, RaceAbilityGrant.is_alternate.is_(False))
    ).all()
    modifiers: list[Modifier] = []
    for grant in grants:
        handler = HANDLERS.get(grant.ability_id)
        if handler is None:
            continue
        modifiers.extend(m for m in handler(_NO_CHARACTER_CONTEXT) if m.target == ModifierTarget.SKILL)
    return modifiers


def effective_race_ability_ids(db: Session, race_id: UUID, chosen_ability_ids: set[UUID]) -> set[UUID]:
    """Which race ability ids a character actually has: every base
    (non-alternate) grant, minus whichever base ids a chosen alternate swaps
    away, plus the chosen alternates themselves (`chosen_ability_ids` —
    a character's own `CharacterRacialChoice.ability_id`s, both the flex
    ability-score pick and any flavor alt-trait swap). Closes the gap
    `race_skill_modifiers`'s docstring already flags for its own SKILL-only
    scope (a chosen alt-trait's mechanical effect was never resolved
    anywhere, only its *name* shown via `Character.alt_traits`) — first real
    consumer is `sheet.py`'s race-ability display and natural-attack lookup,
    both of which need the character's actual trait set, not the race's
    unconditional default one `race_ability_score_mods`/`race_skill_modifiers`
    still use."""
    base_ids = {
        grant.ability_id
        for grant in db.scalars(
            select(RaceAbilityGrant).where(RaceAbilityGrant.race_id == race_id, RaceAbilityGrant.is_alternate.is_(False))
        ).all()
    }
    if chosen_ability_ids:
        replaced_ids = {
            replacement.replaces_ability_id
            for replacement in db.scalars(
                select(RaceAbilityReplacement).where(
                    RaceAbilityReplacement.base_race_id == race_id,
                    RaceAbilityReplacement.ability_id.in_(chosen_ability_ids),
                )
            ).all()
        }
        base_ids -= replaced_ids
    return base_ids | chosen_ability_ids


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
        if handler is None:
            continue
        modifier = handler(_NO_CHARACTER_CONTEXT)[0]
        if modifier.target == ModifierTarget.SCORE and modifier.target_id == attribute:
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
    registry (`HANDLERS`) — select by UUID, call the function, get a
    `Modifier` back — rather than a stored column, and are
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
        if handler is not None and (modifier := handler(_NO_CHARACTER_CONTEXT)[0]).target == ModifierTarget.SCORE:
            if modifier.target_id is None:
                flex = True
            else:
                mods[modifier.target_id] = modifier.value
        else:
            # `handler is not None` here means a real, computed effect that
            # just isn't a SCORE modifier (e.g. a SKILL bonus resolved by
            # `race_skill_modifiers`, or SPEED) — not the same as a purely
            # flavor-only ability with no `HANDLERS` entry at all.
            traits.append({"name": ability.name, "desc": ability.description, "hasHandler": handler is not None})

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
        alt.append(
            {
                "name": ability.name,
                "desc": ability.description,
                "replaces": replaces,
                "hasHandler": HANDLERS.get(ability.id) is not None,
            }
        )

    return {
        "id": str(race.id),
        "name": race.name,
        "short": race.short_description,
        "flex": flex,
        "mods": mods,
        "traits": traits,
        "alt": alt,
    }
