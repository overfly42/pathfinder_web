"""Full effective-ability-score computation: base point-buy scores plus
race/flex (`progression.effective_ability_scores`), plus equipped
CON/STR/etc.-boosting gear, minus ability damage/drain/burn. Shared by
`sheet.py`'s display and `routers/characters.py`'s `adjust_hp` so the two
can never compute a different Constitution score for the same character —
`adjust_hp` used to skip the gear/ability-damage adjustments entirely, so a
character wearing e.g. a "Gürtel der großen Konstitution" got a silently
wrong HP-max and death-floor (too low by the item's bonus, compounding with
level for HP-max)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BaseItem, Character
from .modifiers import Modifier, ModifierTarget, stack
from .progression import effective_ability_scores

# BaseItem.granted_ability's English code -> the character's own German
# ability-score key.
ABILITY_CODE_TO_KEY = {
    "strength": "ST",
    "dexterity": "GE",
    "constitution": "KO",
    "intelligence": "IN",
    "wisdom": "WE",
    "charisma": "CH",
}


def gear_ability_bonuses(db: Session, character: Character) -> dict[str, int]:
    """Enhancement bonuses to ability scores from equipped wondrous items
    (e.g. a "Gürtel der großen Konstitution +2" adds 2 to KO while
    equipped) — only the `BaseItem.granted_ability`/`ability_bonus` subset
    is structured this way, see that catalog's docstring for why the rest
    stays freetext. Only *equipped* gear counts (`equipped_slot` set), same
    as `sheet.py._build_equipment`'s AC logic; `stack()` applied per ability
    in case two equipped items ever grant the same one (same-type bonuses
    don't stack in PF1e)."""
    equipped_item_ids = [g.item_id for g in character.gear if g.equipped_slot]
    if not equipped_item_ids:
        return {}
    items = db.scalars(
        select(BaseItem).where(BaseItem.id.in_(equipped_item_ids), BaseItem.granted_ability.is_not(None))
    ).all()
    modifiers_by_key: dict[str, list[Modifier]] = {}
    for item in items:
        key = ABILITY_CODE_TO_KEY.get(item.granted_ability)
        if key is None:
            continue
        modifiers_by_key.setdefault(key, []).append(
            Modifier(
                source=item.name,
                type="enhancement",
                value=item.ability_bonus or 0,
                target=ModifierTarget.SCORE,
                target_id=key,
            )
        )
    return {key: stack(mods) for key, mods in modifiers_by_key.items()}


def ability_damage_totals(character: Character) -> dict[str, int]:
    """Ability damage/drain/burn (`CharacterAbilityDamage`, roadmap.md §5's
    open item) summed per ability — all three `kind`s reduce the score the
    same way for modifier purposes, only their recovery differs (see that
    model's docstring), so this doesn't need to distinguish them. Empty
    today since nothing writes to the table yet (no `EFFECT_HANDLERS` entry
    applies poison/disease ability damage) — every character's total is 0
    until that handler exists, which is the intended, honest default."""
    totals: dict[str, int] = {}
    for row in character.ability_damage:
        totals[row.ability] = totals.get(row.ability, 0) + row.amount
    return totals


def full_effective_ability_scores(
    db: Session, character: Character, race_mods: dict[str, int]
) -> dict[str, int]:
    """The complete effective ability scores: base/race/flex, plus equipped
    gear bonuses, minus ability damage — the single source of truth any HP
    or ability-check math should read from, rather than each caller
    re-composing the three adjustments itself."""
    scores = effective_ability_scores(character.ability_scores, race_mods, character.flex_ability)
    for key, bonus in gear_ability_bonuses(db, character).items():
        scores[key] = scores.get(key, 0) + bonus
    for key, amount in ability_damage_totals(character).items():
        scores[key] = scores.get(key, 0) - amount
    return scores
