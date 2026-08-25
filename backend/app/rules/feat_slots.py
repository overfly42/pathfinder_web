"""How many feats a character may choose at creation: the base progression
every character gets (1st level, then every odd level after) plus any bonus
feat *slots* granted by race or class. Composition — which race/class grants
a bonus slot, and at what level — is real data (`RaceAbilityGrant`,
`BaseClassAbilityGrant`); only the counting itself is code, per CLAUDE.md's
composition-vs-computation split. Mirrors the frontend's `featMax` in
creationCalculations.ts — keep both in sync.

Deliberately NOT a per-class hardcoded rule ("if class_name == 'Kämpfer'"):
Fighter isn't the only source of bonus feats in the core rules (e.g. a
handful of other classes/features grant feats too), and hardcoding one name
would silently miss the rest and be wrong the moment a second source is
needed. Instead, `BONUS_FEAT_SLOT_ABILITY_IDS` tags which
`BaseClassAbilityGrant` rows represent a feat slot; adding another class's
bonus feats later is a pure data change (seed rows + one more id in this
set), not a new code path.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BaseClass, BaseClassAbilityGrant, RaceAbilityGrant

# "Bonustalent" (Human's bonus feat at 1st level) — a literal, hand-frozen id,
# same convention as rules/race_abilities.py's ABILITY_* constants: the only
# link to base_race_abilities.json is this id, never a name/description
# lookup. Human can trade it away for a skill bonus via the "Bemerkenswerte
# Fertigkeit" alternate trait — see race_grants_bonus_feat's replaced_ability_ids.
RACE_BONUS_FEAT_ABILITY_ID = UUID("e55030a3-b066-480f-ba0a-0653a8f132ca")

# Kämpfer's (Fighter's) recurring bonus combat feat — one shared
# BaseClassAbility catalog row ("Bonus-Kampftalent"), granted via several
# BaseClassAbilityGrant rows (one per granting level: 1st, then every even
# level — see app/seed/class_ability_seed.py). A set, not a single id,
# because a second bonus-feat source (another class, or a different race)
# gets its own catalog id added here, tagging its grants the same way —
# still a pure data change. This is the *only* link to that seed data, same
# hand-frozen-UUID convention as everywhere else in rules/ — nothing derives
# or hashes it.
#
# Kensai's own weapon choice does NOT belong here (2026-08-25, corrected
# after an earlier wrong attempt): real PF1e grants proficiency + Weapon
# Focus for one chosen weapon entirely for free, not via a spent feat pick —
# see `rules/class_weapon_choices.py` for the actual mechanism.
BONUS_FEAT_SLOT_ABILITY_IDS: frozenset[UUID] = frozenset(
    {
        UUID("62ac4cf1-04b9-431b-9047-4156f6cb3481"),  # Kämpfer: Bonus-Kampftalent
    }
)


def base_feat_count(total_level: int) -> int:
    """1st level, then every odd level after that (3rd, 5th, 7th, ...)."""
    return (total_level + 1) // 2


def race_grants_bonus_feat(db: Session, race_id: UUID, replaced_ability_ids: set[UUID]) -> bool:
    """Whether this race's default (non-alternate) grants include the bonus-
    feat ability, and the character didn't trade it away for an alternate
    trait that replaces it (`replaced_ability_ids`, from resolved `alt_traits`)."""
    if RACE_BONUS_FEAT_ABILITY_ID in replaced_ability_ids:
        return False
    grant = db.scalar(
        select(RaceAbilityGrant).where(
            RaceAbilityGrant.race_id == race_id,
            RaceAbilityGrant.ability_id == RACE_BONUS_FEAT_ABILITY_ID,
            RaceAbilityGrant.is_alternate.is_(False),
        )
    )
    return grant is not None


def class_bonus_feat_slot_count(db: Session, classes: list) -> int:
    """Bonus feat slots granted by the character's classes, counted from real
    per-level `BaseClassAbilityGrant` rows tagged as feat slots
    (`BONUS_FEAT_SLOT_ABILITY_IDS`) — never by checking a class's name.
    `classes` is duck-typed (`.class_name`, `.level`), same as
    `routers/characters.py`'s `_skill_points_total`.

    Levels taken in the same class across multiple selections (e.g. a class
    picked non-contiguously, per `test_create_character_with_same_class_across_rows_merges_archetypes`)
    are summed first: a grant's `level` is the class's own cumulative level,
    not a per-selection one."""
    level_by_class_name: dict[str, int] = {}
    for selection in classes:
        level_by_class_name[selection.class_name] = level_by_class_name.get(selection.class_name, 0) + selection.level
    if not level_by_class_name:
        return 0

    roots = db.scalars(
        select(BaseClass).where(BaseClass.name.in_(level_by_class_name), BaseClass.arch_class_of.is_(None))
    ).all()

    total = 0
    for root in roots:
        class_level = level_by_class_name[root.name]
        grants = db.scalars(
            select(BaseClassAbilityGrant.id).where(
                BaseClassAbilityGrant.base_class_id == root.id,
                BaseClassAbilityGrant.ability_id.in_(BONUS_FEAT_SLOT_ABILITY_IDS),
                BaseClassAbilityGrant.level <= class_level,
            )
        ).all()
        total += len(grants)

    return total
