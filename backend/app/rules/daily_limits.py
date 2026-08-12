"""Per-day resource consumption for class/race abilities whose daily
allowance is itself computed rather than a fixed catalog number (contrast
`BaseItem.uses_per_day`/`CharacterGear.uses_remaining_today`, which cover
the fixed-number item case already). Composition-vs-computation split
(CLAUDE.md): *that* an ability is daily-limited, and how many per day, is a
handler function keyed by the ability's own id (`DAILY_LIMITS`, merged the
same three-tier way `HANDLERS` is — class file -> `rules/classes/__init__.py`
-> `rules/handlers.py`); *tracking consumption* is the one generic
`CharacterAbilityUsage` row this module reads/writes.

First (and so far only) entry: Kampfrausch's rounds/day
(`rules/classes/barbarian.py`), consumed a round at a time while its
`CharacterEffect` stays active (`routers/characters.py`'s `advance_time`).
A future discrete N/day ability (Channel Energy, Smite Evil, ...) would call
`record_usage` with `amount=1` at activation time instead — same table, same
functions, no schema change."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Character, CharacterAbilityUsage
from .context import CharacterContext


def _get_usage(db: Session, character: Character, source_id: UUID) -> CharacterAbilityUsage | None:
    return db.scalar(
        select(CharacterAbilityUsage).where(
            CharacterAbilityUsage.character_id == character.id,
            CharacterAbilityUsage.source_type == "class_ability",
            CharacterAbilityUsage.source_id == source_id,
        )
    )


def remaining_today(db: Session, character: Character, context: CharacterContext, source_id: UUID) -> int | None:
    """`None` if `source_id` isn't a daily-limited ability at all; otherwise
    this day's remaining allowance, which may be `<= 0` once exhausted."""
    # Deferred import: `rules/handlers.py` merges every family's registries
    # (including this one's `DAILY_LIMITS`), and `models/character.py`
    # imports `rules/handlers.py` at module level — a module-level import
    # here would be circular (same reasoning `rules/speed.py`'s
    # `class_speed_bonus` documents for its own merged-`HANDLERS` import).
    from .handlers import DAILY_LIMITS

    handler = DAILY_LIMITS.get(source_id)
    if handler is None:
        return None
    usage = _get_usage(db, character, source_id)
    used = usage.used_today if usage is not None else 0
    return handler(context) - used


def record_usage(
    db: Session, character: Character, source_id: UUID, amount: int, context: CharacterContext
) -> int | None:
    """`None` if `source_id` isn't a daily-limited ability at all (same
    sentinel convention as `remaining_today`, so callers can tell "not
    applicable" apart from "exhausted"); otherwise adds `amount` to its
    usage today (get-or-create the row) and returns the new remaining
    allowance (may go negative — callers decide what that means, e.g.
    `advance_time` ending the effect once it's `<= 0`)."""
    from .handlers import DAILY_LIMITS

    handler = DAILY_LIMITS.get(source_id)
    if handler is None:
        return None
    usage = _get_usage(db, character, source_id)
    if usage is None:
        usage = CharacterAbilityUsage(
            character_id=character.id, source_type="class_ability", source_id=source_id, used_today=0
        )
        db.add(usage)
    usage.used_today += amount
    return handler(context) - usage.used_today


def reset_all(db: Session, character: Character) -> None:
    """Full rest: every tracked daily use resets (`CharacterGear.rest`'s
    counterpart for class/race abilities)."""
    for usage in character.ability_usages:
        db.delete(usage)
