"""Hit points/BAB/saving-throw progression — pure arithmetic over per-class
level counts and `BaseClass`'s `hit_dice`/`bab_progression`/`*_save` columns
(roadmap slice 3's "fully playable level-1 character" item). Per
`requirements_v2.md` §2, a multiclass character's BAB/saves/HP are each
class's own contribution computed separately, then summed — never the total
level run against one averaged progression.
"""


def is_valid_rolled_hit_points(hit_dice: int, value: int) -> bool:
    """A player-entered HP roll for one level (any level *except* the
    character's very first, which is always maxed automatically — no rolling
    involved there) must fall within the class's hit die range, inclusive."""
    return 1 <= value <= hit_dice


def class_bab(bab_progression: float, class_level: int) -> int:
    """A class's own BAB contribution: `class_level * bab_progression`
    (1.0 full/0.75 three-quarters/0.5 half), floored."""
    return int(class_level * bab_progression)


def class_save_bonus(is_good_save: bool, class_level: int) -> int:
    """A class's own contribution to one saving throw: the standard PF1e
    good-save (`2 + class_level // 2`) or poor-save (`class_level // 3`)
    progression."""
    if is_good_save:
        return 2 + class_level // 2
    return class_level // 3


def ability_mod(score: int) -> int:
    """Standard PF1e ability modifier: floor((score - 10) / 2)."""
    return (score - 10) // 2


def effective_ability_scores(
    base_scores: dict[str, int], race_mods: dict[str, int], flex_ability: str | None
) -> dict[str, int]:
    """A character's effective (post-race/flex) ability scores: base
    point-buy scores plus the race's own (non-alternate) modifiers
    (`routers/races.py`'s `race_ability_score_mods`), plus +2 on the flex
    pick if the race grants one (`Character.flex_ability`). Never stored;
    computed at read time, same composition-vs-computation split as `bab`/
    `saves` (CLAUDE.md) — shared by `create_character`'s validation
    (`routers/characters.py`) and `sheet.py`'s display so the two never
    drift apart."""
    result = dict(base_scores)
    for ability, mod in race_mods.items():
        result[ability] = result.get(ability, 0) + mod
    if flex_ability is not None:
        result[flex_ability] = result.get(flex_ability, 0) + 2
    return result


def max_hit_points(hit_points_by_level: list[int | None], effective_con_mod: int, total_level: int) -> int:
    """Total max HP: sum of hit points gained/rolled at each level (the
    first level's die is always maxed, see `is_valid_rolled_hit_points`'s
    docstring) plus the effective CON modifier per level
    (`requirements_v2.md` §2). A freshly created character's starting
    current HP equals this too (see `create_character`) — damage tracking is
    a later `PATCH .../hp` concern (todos.md).

    Entries may be `None` for characters created before hit-die data existed
    (`Character.current_hit_points`'s docstring documents this as an
    expected historical state, not an error) — those contribute 0 rather
    than raising, so old characters can still be displayed."""
    return sum(hp or 0 for hp in hit_points_by_level) + effective_con_mod * total_level
