"""Which levels a `BaseClassOptionGroup` recurs at (e.g. Barbar's
`kampfrauschkraft` at 2/4/6/.../20, Mystiker's `revelation` at
1/3/7/11/15/19) — shared by `main.py`'s `get_classes`/`get_class_level_options`
(what to show/offer) and `routers/characters.py`'s `_validate_options` (what
to actually accept), so the three can never drift on what counts as "this
character has reached this group yet."

A group's own occurrences aren't stored directly — they're derived the same
way `BaseClassAbilityGrant`'s own docstring describes the "one shared slot
ability, several per-level grant rows" shape (Kämpfer's bonus feat, Barbar's
Kampfrauschkraft, Schurke's Trick, ...): the `BaseClassAbility` whose *name*
matches the group's own `label` is that slot ability, and its unconditional
(`option_choice_id IS NULL`) grant levels for this root class are exactly
the group's occurrence levels. A one-time group with no such matching
ability (Kleriker's `domain`, Hexenmeister's `bloodline`, Magier's `school`)
has no occurrence-based floor at all — empty list, meaning "always
available", the same as before this module existed."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BaseClassAbility, BaseClassAbilityGrant, BaseClassOptionGroup


def ability_ids_by_name(db: Session) -> dict[str, list[UUID]]:
    """Every `BaseClassAbility` id, grouped by name — a name can map to more
    than one id (e.g. a shared-name ability re-seeded per class with
    distinct ids), so `group_occurrence_levels` below checks grants against
    the whole list, not a single id."""
    result: dict[str, list[UUID]] = {}
    for ability in db.scalars(select(BaseClassAbility)).all():
        result.setdefault(ability.name, []).append(ability.id)
    return result


def group_occurrence_levels(
    db: Session, group: BaseClassOptionGroup, ability_ids_by_name_map: dict[str, list[UUID]]
) -> list[int]:
    """This group's own occurrence levels, sorted — empty if the group isn't
    tied to any recurring grant (a one-time creation-time pick)."""
    ids = ability_ids_by_name_map.get(group.label, [])
    if not ids:
        return []
    return sorted(
        {
            grant.level
            for grant in db.scalars(
                select(BaseClassAbilityGrant).where(
                    BaseClassAbilityGrant.base_class_id == group.base_class_id,
                    BaseClassAbilityGrant.ability_id.in_(ids),
                    BaseClassAbilityGrant.option_choice_id.is_(None),
                )
            ).all()
        }
    )
