from app.rules.speed import jump_skill_bonus


def test_jump_skill_bonus_is_zero_at_normal_speed() -> None:
    assert jump_skill_bonus(9) == 0


def test_jump_skill_bonus_grants_plus_four_per_full_three_meters_above_normal() -> None:
    assert jump_skill_bonus(12) == 4
    assert jump_skill_bonus(15) == 8
    assert jump_skill_bonus(21) == 16


def test_jump_skill_bonus_applies_minus_four_per_full_three_meters_below_normal() -> None:
    assert jump_skill_bonus(6) == -4
    assert jump_skill_bonus(3) == -8


def test_jump_skill_bonus_does_not_credit_partial_three_meter_steps() -> None:
    assert jump_skill_bonus(11) == 0
    assert jump_skill_bonus(10) == 0
    assert jump_skill_bonus(8) == 0
    assert jump_skill_bonus(7) == 0
