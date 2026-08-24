"""Weapon proficiency — composition (which category a class ability or
chosen feat confers) is real data (`BaseClassAbilityGrantedFeat`, the three
category feats in `base_feats.json`); this module is purely the *computation*
half, per CLAUDE.md's composition-vs-computation split: resolving a
character's effective proficiency-feat set and mapping it to the
`BaseItem.weapon_type` categories it covers.

No per-class handler is needed here (unlike most of `rules/classes/`):
`BaseClassAbilityGrantedFeat` already links almost every class's own "Umgang
mit Waffen und Rüstungen" variant to the matching category feats (see that
model's docstring) — this module's lookup is generic over that existing
data, so it applies automatically to every class with such data, not just
Kampfmagus/Kensai."""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BaseClassAbilityGrantedFeat

EINFACHE_WAFFEN_FEAT_ID = UUID("9d19039e-78b7-50ea-ab5c-ea65b81b8a06")
KRIEGSWAFFEN_FEAT_ID = UUID("1bf92ea9-226c-5975-bad1-d91e46aefdd3")
EXOTISCHE_WAFFEN_FEAT_ID = UUID("eef862cb-9a84-5ceb-b97b-7ab3b3f6e838")

# Feat id -> the `BaseItem.weapon_type` category it confers proficiency
# with. `weapon_type` also has a `"firearm"` value with no matching feat
# here (PF1e core gates firearms behind their own Exotic Weapon Proficiency
# (Firearms), distinct from the generic exotic-weapon feat) — not modeled,
# so firearms always read as non-proficient, a known, harmless simplification
# since no class in this codebase's data grants firearm proficiency anyway.
WEAPON_PROFICIENCY_FEAT_TYPES: dict[UUID, str] = {
    EINFACHE_WAFFEN_FEAT_ID: "simple",
    KRIEGSWAFFEN_FEAT_ID: "martial",
    EXOTISCHE_WAFFEN_FEAT_ID: "exotic",
}

# PF1e's flat penalty for attacking with a weapon the character isn't
# proficient with (GRW S. 122).
NOT_PROFICIENT_ATTACK_PENALTY = -4


def effective_proficiency_feat_ids(
    db: Session, feat_ids: frozenset[UUID], granted_ability_ids: Iterable[UUID]
) -> frozenset[UUID]:
    """Feats a character has via a class ability's automatic grant
    (`BaseClassAbilityGrantedFeat`) folded in with feats actually picked —
    shared by `routers/feats.py`'s prerequisite checks and `sheet.py`'s
    weapon-attack malus, which both need the identical effective set."""
    granted_ids = set(granted_ability_ids)
    auto_feat_ids = {
        row.feat_id for row in db.scalars(select(BaseClassAbilityGrantedFeat)) if row.ability_id in granted_ids
    }
    return frozenset(feat_ids) | auto_feat_ids


def known_weapon_types(proficiency_feat_ids: frozenset[UUID]) -> frozenset[str]:
    """Which `BaseItem.weapon_type` categories `proficiency_feat_ids`
    covers — used by `sheet.py`'s `_build_weapon_attacks` to decide whether
    the equipped weapon's category is one of them."""
    return frozenset(
        weapon_type
        for feat_id, weapon_type in WEAPON_PROFICIENCY_FEAT_TYPES.items()
        if feat_id in proficiency_feat_ids
    )
