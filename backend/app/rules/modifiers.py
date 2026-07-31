"""Shared bonus-stacking primitive (roadmap slice 4's "shared modifier/
bonus-stacking design", built here so slice 5 (effects) can reuse it without
a second implementation — see `readme.md`'s Guiding Decisions).

PF1e stacking rule: two bonuses of the same named type don't stack (only the
higher applies); dodge/circumstance/untyped bonuses always stack with
anything, including each other. Only "armor" and "shield" types are actually
produced today (`sheet.py`'s AC computation from equipped gear); the
type-max logic for everything else is inert until effects start
contributing other typed bonuses (e.g. a spell granting natural armor or
deflection)."""

from dataclasses import dataclass

ALWAYS_STACKS = {"dodge", "circumstance", "untyped"}


@dataclass
class Modifier:
    source: str
    type: str
    value: int


def stack(modifiers: list[Modifier]) -> int:
    total = 0
    best_by_type: dict[str, int] = {}
    for modifier in modifiers:
        if modifier.type in ALWAYS_STACKS:
            total += modifier.value
        else:
            best_by_type[modifier.type] = max(best_by_type.get(modifier.type, 0), modifier.value)
    return total + sum(best_by_type.values())
