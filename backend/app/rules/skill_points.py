"""Racial bonus to the skill-point budget — e.g. Human's "Geschult" (Skilled):
one extra skill rank at 1st level and one more at every level after, i.e. a
flat +1 per *character* level, not per class. Composition (which race grants
this) is real data (`RaceAbilityGrant`); only the counting is code, same
composition-vs-computation split as `rules/feat_slots.py`'s
`race_grants_bonus_feat` (mirrored here, including the alternate-trait
trade-away check)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import RaceAbilityGrant

# "Geschult" (Human's Skilled trait) — hand-frozen id, same convention as
# rules/feat_slots.py's RACE_BONUS_FEAT_ABILITY_ID: the only link to
# base_race_abilities.json is this id, never a name/description lookup.
RACE_SKILLED_ABILITY_ID = UUID("6aeda00f-a761-4f4e-b943-d770c0018d07")


def background_skill_points_total(character_level: int) -> int:
    """2 skill ranks per character level, spendable only on
    `BaseSkill.is_background` skills — the "Hintergrundfertigkeiten"
    alternate rule (http://prd.5footstep.de/Alternativregeln/Fertigkeiten/
    Hintergrundfertigkeiten). Unlike `_skill_points_total`
    (routers/characters.py), this is never modified by the Intelligence
    modifier or any race/class bonus — the PRD is explicit that it isn't.
    Only meaningful when `Character.use_background_skills` is set; callers
    pass 0 for `character_level` (or skip calling this) otherwise."""
    return 2 * character_level


def race_grants_bonus_skill_point_per_level(db: Session, race_id: UUID, replaced_ability_ids: set[UUID]) -> bool:
    """Whether this race's default (non-alternate) grants include the
    Skilled ability, and the character didn't trade it away for an
    alternate trait that replaces it (`replaced_ability_ids`, from resolved
    `alt_traits`)."""
    if RACE_SKILLED_ABILITY_ID in replaced_ability_ids:
        return False
    grant = db.scalar(
        select(RaceAbilityGrant).where(
            RaceAbilityGrant.race_id == race_id,
            RaceAbilityGrant.ability_id == RACE_SKILLED_ABILITY_ID,
            RaceAbilityGrant.is_alternate.is_(False),
        )
    )
    return grant is not None
