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
    # Melee attack rolls/melee+thrown damage rolls (`sheet.py`'s
    # `_build_weapon_attacks` computed readout) — first producer is
    # Kampfrausch's flat +2 (`rules/classes/barbarian.py`). Single slot, no
    # `target_id`, same as AC/SPEED/SAVE_*.
    ATTACK = "attack"
    DAMAGE = "damage"


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


def stack_by_target(modifiers: list[Modifier]) -> dict[tuple[ModifierTarget, str | None], int]:
    """`readme.md`'s "Request pipeline" step 4 in one call: group every
    `Modifier` by `(target, target_id)` and `stack()` each group, once, up
    front — rather than every consumer re-filtering the same flat list and
    calling `stack()` itself (`sheet.py` used to do this once per save, once
    per skill row, ...). Callers look up their own key; a `(target,
    target_id)` pair with no contributing modifiers simply isn't a key, so
    callers should default to 0 (`dict.get(key, 0)`).

    Callers whose modifiers come from more than one source (e.g. AC: both
    composition-driven modifiers and gear's own armor/shield bonus) must
    combine them into one list *before* calling this — grouping/stacking
    them separately and adding the two results back together would break
    the same-type-cap rule across sources (two "armor"-type bonuses from
    different origins still don't stack)."""
    by_key: dict[tuple[ModifierTarget, str | None], list[Modifier]] = {}
    for modifier in modifiers:
        by_key.setdefault((modifier.target, modifier.target_id), []).append(modifier)
    return {key: stack(group) for key, group in by_key.items()}
