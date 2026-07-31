from app.rules.progression import class_bab, class_save_bonus, is_valid_rolled_hit_points


def test_is_valid_rolled_hit_points_accepts_the_full_die_range_inclusive() -> None:
    assert is_valid_rolled_hit_points(10, 1) is True
    assert is_valid_rolled_hit_points(10, 10) is True
    assert is_valid_rolled_hit_points(10, 5) is True


def test_is_valid_rolled_hit_points_rejects_outside_the_die_range() -> None:
    assert is_valid_rolled_hit_points(10, 0) is False
    assert is_valid_rolled_hit_points(10, 11) is False
    assert is_valid_rolled_hit_points(6, 7) is False


def test_class_bab_progressions() -> None:
    assert class_bab(1.0, 5) == 5
    assert class_bab(0.75, 5) == 3
    assert class_bab(0.5, 5) == 2


def test_class_save_bonus_good_vs_poor() -> None:
    assert [class_save_bonus(True, level) for level in range(1, 6)] == [2, 3, 3, 4, 4]
    assert [class_save_bonus(False, level) for level in range(1, 6)] == [0, 0, 1, 1, 1]
