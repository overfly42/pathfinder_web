"""Shared bonus-stacking primitive (roadmap slice 4's "shared modifier/
bonus-stacking design", built here so slice 5 (effects) can reuse it without
a second implementation — see `readme.md`'s Guiding Decisions).

PF1e stacking rule: two bonuses of the same named type don't stack (only the
higher applies); dodge/circumstance/untyped bonuses always stack with
anything, including each other. "armor"/"shield" (`sheet.py`'s AC from
equipped gear) and "enhancement" (`sheet.py`'s gear-granted ability-score
bonuses) are the types actually produced today; the type-max logic for
everything else is inert until effects start contributing other typed
bonuses (e.g. a spell granting natural armor or deflection).

`target`/`target_id` say *which* stat a `Modifier` applies to — the vocabulary
the unified ability-effect registry (`rules/handlers.py`) is keyed against, so
one `HANDLERS: dict[UUID, Callable[[], list[Modifier]]]` can serve every
computed stat instead of a separate handler dict per stat (see the
CLAUDE.md-guided design discussion this followed). `target_id` disambiguates
within a `target` that isn't a single fixed slot: which ability score
(`"ST"`/`"GE"`/...) for `SCORE`, or `None` for a player-chosen one (e.g.
Human's flex bonus); which skill (`BaseSkill.id` as `str`) for `SKILL`.
`AC`/`SPEED`/`SAVE_*` each have exactly one slot, so `target_id` stays `None`
for those. `SAVE_*`/`SKILL` have no producing handler yet — reserved, same
"inert until used" state the stacking-type comment above already documents
for AC's own bonus types."""

from dataclasses import dataclass
from enum import StrEnum

ALWAYS_STACKS = {"dodge", "circumstance", "untyped"}


class ModifierTarget(StrEnum):
    SCORE = "score"
    AC = "ac"
    SPEED = "speed"
    SAVE_FORT = "save_fort"
    SAVE_REF = "save_ref"
    SAVE_WILL = "save_will"
    SKILL = "skill"


@dataclass
class Modifier:
    source: str
    type: str
    value: int
    target: ModifierTarget
    target_id: str | None = None


def stack(modifiers: list[Modifier]) -> int:
    total = 0
    best_by_type: dict[str, int] = {}
    for modifier in modifiers:
        if modifier.type in ALWAYS_STACKS:
            total += modifier.value
        else:
            best_by_type[modifier.type] = max(best_by_type.get(modifier.type, 0), modifier.value)
    return total + sum(best_by_type.values())
