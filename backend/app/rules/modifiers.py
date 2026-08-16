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
from uuid import UUID

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


@dataclass(frozen=True)
class SkillNote:
    """A *conditional* skill bonus — one that only applies in some
    situation the sheet can't itself detect (Seeräuber's Wilder Seemann
    only applies in water/on ships/at the coast; Sprung's Volksbonus only
    applies to a jump check, not Akrobatik's other uses) — sibling to
    `Modifier`, deliberately not a `Modifier`: everything that reaches
    `stack()`/`stack_by_target()` is treated as unconditionally active and
    folded straight into a stat's displayed value, which would be wrong
    here. `sheet.py`'s `_build_skills` is the only consumer — it renders
    every `SkillNote` targeting a skill as that skill's info `note` (never
    added to `value`) and is where `title`/`modifier_label`/`detail` end up
    in the sentence; this dataclass only carries the ingredients, not
    presentation logic, same "handler computes, sheet.py formats" split
    `Modifier`/`stack_by_target` already keep.

    Produced by two different kinds of source, per `rules/handlers.py`'s
    `SITUATIONAL_SKILL_HANDLERS` docstring:
    - id-keyed (granted class ability or feat) — `value` is already fully
      resolved by the handler (e.g. scaled by grant count), no further
      conditioning needed.
    - universal (`rules/speed.py`'s jump bonus) — applies to every
      character regardless of composition, so it's never looked up by id
      at all; called directly and unconditionally instead."""

    skill_id: UUID
    # The note's leading label, e.g. "Wilder Seemann (im Wasser, auf
    # Schiffen, an der Küste)" or "Sprung (Hoch-/Weitsprung)".
    title: str
    # The bonus's own name inside the "skill total + this" breakdown, e.g.
    # "Wilder Seemann" or "Volksbonus/-malus" — usually equal to `title`
    # minus its parenthetical, but kept separate since they diverge for
    # Sprung.
    modifier_label: str
    value: int
    # Trailing free text after the value, e.g. jump's
    # " bei 9 m Bewegungsrate, 4 pro volle 3 m über/unter 9 m" — empty for
    # notes with nothing more to add.
    detail: str = ""


def stack(modifiers: list[Modifier]) -> int:
    total = 0
    best_by_type: dict[str, int] = {}
    for modifier in modifiers:
        if modifier.type in ALWAYS_STACKS:
            total += modifier.value
        else:
            best_by_type[modifier.type] = max(best_by_type.get(modifier.type, 0), modifier.value)
    return total + sum(best_by_type.values())


def contributing(modifiers: list[Modifier]) -> list[Modifier]:
    """Same type-cap rule as `stack()` (`ALWAYS_STACKS` types all count;
    every other type only counts its highest-value entry), but returns the
    surviving `Modifier`s themselves instead of collapsing them to a single
    int — for provenance/breakdown display (`sheet.py`'s skill/AC breakdown),
    where the caller needs to know *which* modifiers actually counted toward
    the total, not just the total itself. `sum(m.value for m in
    contributing(mods)) == stack(mods)` always holds."""
    result: list[Modifier] = []
    best_by_type: dict[str, Modifier] = {}
    for modifier in modifiers:
        if modifier.type in ALWAYS_STACKS:
            result.append(modifier)
        else:
            current = best_by_type.get(modifier.type)
            if current is None or modifier.value > current.value:
                best_by_type[modifier.type] = modifier
    result.extend(best_by_type.values())
    return result


def group_by_target(modifiers: list[Modifier]) -> dict[tuple[ModifierTarget, str | None], list[Modifier]]:
    """Groups every `Modifier` by `(target, target_id)` — the shared first
    step `stack_by_target` (the summed total) and any breakdown/provenance
    caller (the raw list, via `contributing`) both need, factored out so
    `sheet.py` can compute both from the same grouping pass rather than
    grouping twice."""
    by_key: dict[tuple[ModifierTarget, str | None], list[Modifier]] = {}
    for modifier in modifiers:
        by_key.setdefault((modifier.target, modifier.target_id), []).append(modifier)
    return by_key


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
    return {key: stack(group) for key, group in group_by_target(modifiers).items()}
