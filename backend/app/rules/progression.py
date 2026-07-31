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
