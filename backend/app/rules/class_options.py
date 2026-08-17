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

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BaseClassAbility, BaseClassAbilityGrant, BaseClassAbilityReplacement, BaseClassOptionGroup


def ability_ids_by_name(db: Session) -> dict[str, list[UUID]]:
    """Every `BaseClassAbility` id, grouped by name — a name can map to more
    than one id (e.g. a shared-name ability re-seeded per class with
    distinct ids), so `group_occurrence_levels` below checks grants against
    the whole list, not a single id."""
    result: dict[str, list[UUID]] = {}
    for ability in db.scalars(select(BaseClassAbility)).all():
        result.setdefault(ability.name, []).append(ability.id)
    return result


def archetype_replaced_grant_ids(db: Session, archetype_ids: Collection[UUID]) -> set[UUID]:
    """Every root-class `BaseClassAbilityGrant` id superseded by one of
    `archetype_ids` (`BaseClassAbilityReplacement.replaces_grant_id`) — the
    same "which grants has this archetype swapped out" lookup `sheet.py`'s
    `_granted_class_ability_ids` already does for the character-sheet
    display, reused here so `group_occurrence_levels` can apply the same
    exclusion to an option group's occurrence-level *count* (2026-08-17):
    an archetype whose own ability replaces a root class's only grant for an
    option-group's backing ability (e.g. Ork's Narbiger Hexendoktor archetype
    replacing Hexe's level-1 "Hexerei" grant with its own Narbenschild) must
    also remove that level from the group's occurrence list, not just hide
    the replaced ability from the sheet — otherwise the creation/level-up UI
    still prompts for a pick the character can no longer make."""
    if not archetype_ids:
        return set()
    return set(
        db.scalars(
            select(BaseClassAbilityReplacement.replaces_grant_id).where(
                BaseClassAbilityReplacement.archetype_class_id.in_(archetype_ids)
            )
        ).all()
    )


def group_occurrence_levels(
    db: Session,
    group: BaseClassOptionGroup,
    ability_ids_by_name_map: dict[str, list[UUID]],
    *,
    replaced_grant_ids: Collection[UUID] | None = None,
) -> list[int]:
    """This group's own occurrence levels, sorted — empty if the group isn't
    tied to any recurring grant (a one-time creation-time pick).

    `replaced_grant_ids` (`archetype_replaced_grant_ids` above, 2026-08-17)
    excludes any grant an already-chosen archetype has superseded — omitted
    (the default) when no archetype context applies, e.g. `/api/classes`'
    generic, archetype-agnostic per-class payload, which instead exposes
    each archetype's own delta separately (see that endpoint's
    `archetypeOptionOverrides`)."""
    ids = ability_ids_by_name_map.get(group.label, [])
    if not ids:
        return []
    excluded = set(replaced_grant_ids or ())
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
            if grant.id not in excluded
        }
    )
