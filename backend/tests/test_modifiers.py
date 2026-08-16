"""Unit tests for `rules/modifiers.py`'s stacking/breakdown primitives —
pure functions, no DB needed unlike this repo's other tests."""

from app.rules.modifiers import Modifier, ModifierTarget, contributing, group_by_target, stack


def test_contributing_drops_the_lower_of_two_same_type_modifiers() -> None:
    """PF1e: two bonuses of the same named type don't stack, only the higher
    applies — `contributing()` must reflect exactly what `stack()` already
    enforces for the total, not list every raw Modifier regardless of
    whether it actually counted."""
    modifiers = [
        Modifier(source="A", type="racial", value=2, target=ModifierTarget.SKILL, target_id="x"),
        Modifier(source="B", type="racial", value=5, target=ModifierTarget.SKILL, target_id="x"),
    ]
    result = contributing(modifiers)
    assert [m.source for m in result] == ["B"]
    assert sum(m.value for m in result) == stack(modifiers) == 5


def test_contributing_keeps_every_always_stacking_modifier() -> None:
    modifiers = [
        Modifier(source="A", type="dodge", value=1, target=ModifierTarget.AC),
        Modifier(source="B", type="dodge", value=2, target=ModifierTarget.AC),
    ]
    result = contributing(modifiers)
    assert {m.source for m in result} == {"A", "B"}
    assert sum(m.value for m in result) == stack(modifiers) == 3


def test_group_by_target_groups_match_stack_totals() -> None:
    modifiers = [
        Modifier(source="A", type="racial", value=2, target=ModifierTarget.SKILL, target_id="x"),
        Modifier(source="B", type="untyped", value=1, target=ModifierTarget.SKILL, target_id="x"),
        Modifier(source="C", type="armor", value=2, target=ModifierTarget.AC),
    ]
    groups = group_by_target(modifiers)
    assert stack(groups[(ModifierTarget.SKILL, "x")]) == 3
    assert stack(groups[(ModifierTarget.AC, None)]) == 2
