"""Weapon proficiency — composition (which category or specific weapon a
class ability or chosen feat confers) is real data (`BaseClassAbilityGrantedFeat`,
the three category feats in `base_feats.json`); this module is purely the
*computation* half, per CLAUDE.md's composition-vs-computation split:
resolving a character's effective proficiency and mapping it to the
`BaseItem.weapon_type` categories (or exact weapon ids) it covers.

No per-class handler is needed here (unlike most of `rules/classes/`):
`BaseClassAbilityGrantedFeat` already links almost every class's own "Umgang
mit Waffen und Rüstungen" variant to the matching category feats (see that
model's docstring) — this module's lookup is generic over that existing
data, so it applies automatically to every class with such data, not just
Kampfmagus/Kensai.

"Umgang mit exotischen Waffen" is dual-natured (matching PF1e's actual
Exotic Weapon Proficiency, which is always per-weapon regardless of who
takes it): if a class ever auto-grants it (`BaseClassAbilityGrantedFeat`, not
the case for anything in this codebase's data today) it would mean the whole
category; picked by a player as an ordinary feat (`sub_choice_type="weapon"`,
`CharacterFeat.chosen_weapon_id`) it instead names one specific weapon.
"Umgang mit Kriegswaffen" stays plain blanket-only either way — real PF1e's
Martial Weapon Proficiency has no per-weapon variant. `known_weapon_types`
only ever sees the blanket half; a player's own single-weapon pick is
checked separately, against the exact equipped weapon id — same field
(`CharacterContext.chosen_weapon_ids`) a Kensai's own free weapon choice
also feeds into (`rules/class_weapon_choices.py`), since both answer the
identical "is this exact weapon id one I'm proficient with" question
regardless of how that proficiency was earned."""

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

# The one feat whose meaning depends on how a character got it — see this
# module's own docstring. Neither `EINFACHE_WAFFEN_FEAT_ID` nor
# `KRIEGSWAFFEN_FEAT_ID` is included: nothing ever narrows either to a single
# weapon, so a player picking either manually still means the whole category.
DUAL_NATURE_WEAPON_FEAT_IDS = frozenset({EXOTISCHE_WAFFEN_FEAT_ID})

# PF1e's flat penalty for attacking with a weapon the character isn't
# proficient with (GRW S. 122).
NOT_PROFICIENT_ATTACK_PENALTY = -4


def class_granted_proficiency_feat_ids(db: Session, granted_ability_ids: Iterable[UUID]) -> frozenset[UUID]:
    """Feats a character has via a class ability's automatic grant
    (`BaseClassAbilityGrantedFeat`) — always blanket-category (an automatic
    grant never carries a chosen weapon), shared by `effective_proficiency_feat_ids`
    (prerequisite checks) and `sheet.py`'s weapon-attack malus (blanket half
    of `known_weapon_types`, see this module's docstring)."""
    granted_ids = set(granted_ability_ids)
    return frozenset(
        row.feat_id for row in db.scalars(select(BaseClassAbilityGrantedFeat)) if row.ability_id in granted_ids
    )


def effective_proficiency_feat_ids(
    db: Session, feat_ids: frozenset[UUID], granted_ability_ids: Iterable[UUID]
) -> frozenset[UUID]:
    """Feats actually picked folded in with feats granted automatically by a
    class ability — used by `routers/feats.py`'s prerequisite checks, which
    only care *whether* a character has a feat, not which weapon (if any) it
    names, so the dual-nature distinction doesn't apply here."""
    return frozenset(feat_ids) | class_granted_proficiency_feat_ids(db, granted_ability_ids)


def known_weapon_types(class_granted_feat_ids: frozenset[UUID], feat_ids: frozenset[UUID]) -> frozenset[str]:
    """Which `BaseItem.weapon_type` categories this character is
    blanket-proficient with — every class-auto-granted proficiency feat,
    plus any picked feat *except* the one dual-nature one (a player's own
    pick of "Umgang mit exotischen Waffen" always names one specific weapon
    instead, checked separately via `CharacterContext.chosen_weapon_ids`)."""
    blanket_ids = class_granted_feat_ids | (feat_ids - DUAL_NATURE_WEAPON_FEAT_IDS)
    return frozenset(
        weapon_type for feat_id, weapon_type in WEAPON_PROFICIENCY_FEAT_TYPES.items() if feat_id in blanket_ids
    )
