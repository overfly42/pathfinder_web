"""The "Sekundärklasse" alternate rule (http://prd.5footstep.de/
Alternativregeln/Fertigkeiten/AlternativesSystemfuerCharakteremitKlassenkombinationen):
a character picks one root class at 1st level they never take real levels
in, but which grants a handful of its own features at total character level
3/7/11/15/19 instead of a talent on those levels — see
`models/base_class.py`'s `BaseSecondaryClassAbilityGrant` for the schema this
module computes against, and `rules/feat_slots.py`'s
`secondary_class_suppressed_feat_count` for the talent-slot side.

Composition (which ability a class's Sekundärklasse track grants at which
milestone) is `BaseSecondaryClassAbilityGrant` rows — pure data. The one
thing that needs code is the "effektive Klassenstufe" formula every tier in
the source text uses (an offset off the character's total level, sometimes
halved, sometimes floored at a minimum) — `secondary_effective_level` below
is the one shared function for that, since the shape is identical across
every class the source text lists; no per-class handler needed for the
level number itself (CLAUDE.md's composition-vs-computation split).

`secondary_granted_ability_ids_and_levels` is `sheet.py`'s integration
point: it feeds straight into the same `granted_ability_ids`/
`level_counts_by_root_id` structures `granted_class_ability_ids`/real
`CharacterLevel` rows already populate, so any class that gets a real
`HANDLERS` entry for its primary version (currently only Barbar/Kampfmagus,
see `rules/classes/`) automatically also gets a correctly-computed
Sekundärklasse version — no new handler code required for that class.

Known simplification: if more than one unlocked tier for the same
Sekundärklasse ever needed *different* effective-level formulas at once
(the source text's one documented case is Barbar's Kampfrauschkraft, which
uses half the character's level to check rage-power *eligibility* at pick
time but full level for the *effect* of whichever power was picked), only
one synthetic level per root class id can be reflected in
`level_counts_by_root_id` at a time — the most-recently-unlocked tier's own
formula wins. The eligibility-at-pick-time half of that split doesn't need
this dict at all (it's resolved once, at the level-up moment, by passing
the half-level formula straight into `routers/characters.py`'s
`_validate_options` as its `character_level` argument — see that function's
own docstring, which already treats `character_level` as a caller-supplied
parameter, not something it derives itself)."""

from collections import Counter
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BaseSecondaryClassAbilityGrant

if TYPE_CHECKING:
    from ..models import Character


def secondary_effective_level(
    total_level: int, *, offset: int = 0, divisor: int = 1, minimum: int | None = None
) -> int:
    """One tier's "effektive Klassenstufe" against the character's real
    total level — every tier across all 19 classes in the source text
    reduces to this same (offset, optionally halved, optionally floored)
    shape. Defaults mean "use the character's total level unmodified"."""
    level = (total_level + offset) // divisor
    return max(level, minimum) if minimum is not None else level


def secondary_granted_ability_ids_and_levels(
    db: Session, character: "Character"
) -> tuple[Counter[UUID], dict[UUID, int]]:
    """Every `BaseSecondaryClassAbilityGrant` ability id this character has
    actually reached (`character_level <= character.level`, the character's
    real total level — see that model's own docstring for why this isn't
    the character's level *in* the class), plus a synthetic
    `{secondary_base_class_id: effective_level}` entry ready to merge into
    `sheet.py`'s `level_counts_by_root_id` (see this module's own docstring
    for the "most-recently-unlocked tier wins" simplification when more than
    one reached tier's formula would disagree). Empty of both when the
    character hasn't opted into this rule at all."""
    if character.secondary_base_class_id is None:
        return Counter(), {}

    grants = db.scalars(
        select(BaseSecondaryClassAbilityGrant)
        .where(
            BaseSecondaryClassAbilityGrant.secondary_base_class_id == character.secondary_base_class_id,
            BaseSecondaryClassAbilityGrant.character_level <= character.level,
        )
        .order_by(BaseSecondaryClassAbilityGrant.character_level)
    ).all()
    if not grants:
        return Counter(), {}

    ability_ids: Counter[UUID] = Counter()
    effective_level = 0
    for grant in grants:
        ability_ids[grant.ability_id] += 1
        effective_level = secondary_effective_level(
            character.level,
            offset=grant.effective_level_offset,
            divisor=grant.effective_level_divisor,
            minimum=grant.effective_level_minimum,
        )
    return ability_ids, {character.secondary_base_class_id: effective_level}
