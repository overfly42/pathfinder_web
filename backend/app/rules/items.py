"""Computed effects of individual magic items, keyed by `BaseItem.id` —
the item-side counterpart of `rules/handlers.py`'s ability/feat `HANDLERS`
(CLAUDE.md's composition-vs-computation boundary: *which* items exist is
catalog data in `base_items.json`, *what one does* is code looked up by the
catalog row's own id, so no schema column is needed per new item shape).

Each handler gets the character's equipped `CharacterGear` row for that
item and returns the `Modifier`s it contributes. `sheet.py` calls these only
for items sitting in an equipped slot, and merges the result into the same
raw modifier list as everything else before stacking, so same-type bonuses
from different sources still only count once.

Attribute-boosting items (Gürtel/Stirnreif der ...) are *not* here: their
single-attribute bonus is plain catalog data (`BaseItem.granted_ability`/
`ability_bonus`), applied by `rules/effective_scores.py`.

Item ids are the stable `uuid5` ids `scripts/build_wondrous_items_seed.py`
derives from the PRD name, so they are the same in every database.
"""

import functools
from collections.abc import Callable
from uuid import UUID

from ..models import CharacterGear
from .modifiers import Modifier, ModifierTarget
from .skill_ids import SCHWIMMEN_SKILL_ID

AMULETT_DER_NATUERLICHEN_RUESTUNG = UUID("79c4612e-064d-5bac-b068-2a9d5bd74e0c")
RESISTENZUMHANG = UUID("79dd49d1-907f-536f-a367-f0517c1954a8")
SCHWIMMERRING = UUID("9787037d-3b61-5eb8-8c8a-4000c7fe7691")
VERBESSERTER_SCHWIMMERRING = UUID("24336625-2e57-5245-a1b0-a0273a6bdc2c")
RING_DES_WAESSRIGEN_WEGES = UUID("b62ae519-0a9f-57a6-b195-232d241f0fb4")


_SAVE_TARGETS = (ModifierTarget.SAVE_FORT, ModifierTarget.SAVE_REF, ModifierTarget.SAVE_WILL)


def _natural_armor_enhancement(gear: CharacterGear, *, source: str) -> list[Modifier]:
    """Amulett der natürlichen Rüstung: an *enhancement* bonus (+1..+5, the
    instance's own `CharacterGear.enhancement`) on the wearer's natural
    armor. Typed "enhancement" rather than "natural" so it stacks on top of
    a natural armor bonus from a feat/race/class (`rules/feats.py`'s
    `_natural_armor_bonus`) instead of competing with it."""
    return [Modifier(source=source, type="enhancement", value=gear.enhancement, target=ModifierTarget.AC)]


def _resistance_bonus(gear: CharacterGear, *, source: str) -> list[Modifier]:
    """Resistenzumhang: a resistance bonus (+1..+5, `CharacterGear.
    enhancement`) on Fortitude, Reflex and Will saves."""
    return [
        Modifier(source=source, type="resistance", value=gear.enhancement, target=target)
        for target in _SAVE_TARGETS
    ]


def _swim_competence(gear: CharacterGear, *, source: str, value: int) -> list[Modifier]:
    """Schwimmerring family: a fixed competence bonus on Schwimmen checks
    (the PRD's "Kompetenzbonus"), a fixed property of the catalog row — not
    scaled by `CharacterGear.enhancement` like the tiered +N items."""
    del gear
    return [
        Modifier(
            source=source,
            type="competence",
            value=value,
            target=ModifierTarget.SKILL,
            target_id=str(SCHWIMMEN_SKILL_ID),
        )
    ]


def _wassriger_weg(gear: CharacterGear) -> list[Modifier]:
    """Ring des wässrigen Weges: a 9 m swim speed. The +8 Volksbonus on
    Schwimmen the PRD text lists comes from the swim speed itself
    (`rules/speed.py`'s `movement_mode_skill_modifiers`), not declared here.
    Typed "base" like Aquatische Anpassung's swim speed, so two sources
    don't add up. (The once-per-day Dimensionstür is not modelled.)"""
    del gear
    return [Modifier(source="Ring des wässrigen Weges", type="base", value=9, target=ModifierTarget.SWIM_SPEED)]


ITEM_HANDLERS: dict[UUID, Callable[[CharacterGear], list[Modifier]]] = {
    AMULETT_DER_NATUERLICHEN_RUESTUNG: functools.partial(
        _natural_armor_enhancement, source="Amulett der natürlichen Rüstung"
    ),
    RESISTENZUMHANG: functools.partial(_resistance_bonus, source="Resistenzumhang"),
    SCHWIMMERRING: functools.partial(_swim_competence, source="Schwimmerring", value=5),
    VERBESSERTER_SCHWIMMERRING: functools.partial(
        _swim_competence, source="Verbesserter Schwimmerring", value=10
    ),
    RING_DES_WAESSRIGEN_WEGES: _wassriger_weg,
}


def equipped_item_modifiers(equipped: list[CharacterGear]) -> list[Modifier]:
    modifiers: list[Modifier] = []
    for gear in equipped:
        handler = ITEM_HANDLERS.get(gear.item_id)
        if handler is not None:
            modifiers.extend(handler(gear))
    return modifiers
