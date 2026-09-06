"""Land speed — base (racial) plus any bonus from a granted class ability,
composed via the shared `Modifier`/`stack()` primitive (`rules/modifiers.py`)
through the same unified ability-effect registry `rules/race_abilities.py`
uses for ability-score bonuses (see `rules/handlers.py`, which merges every
family's `HANDLERS` into the one dict `sheet.py` ultimately looks up
against) — composition (which race/class grants which speed-affecting
ability) is real data (`RaceAbilityGrant`/`BaseClassAbilityGrant`), same
split as `rules/skill_points.py`; only the *computation* (how many meters,
and how it stacks) lives here.

Every seeded race grants exactly one of the two base-speed abilities
(`race_seed.py`), so `race_speed` always finds a value — no stored default
needed, unlike the old `BaseRace.speed` column this replaces. Race-tied
content stays local to this module's own `HANDLERS` (same locality/
git-blame reason `race_abilities.py` keeps its own slice too).

Also owns the one other movement mode seeded today, climb speed
(`ModifierTarget.CLIMB_SPEED`) — Katzenvolk's "Kletterer" alternate racial
trait, the mirror of the module's land-speed handling but for a mode most
characters simply don't have (`race_climb_speed` returns `None`, not 0, when
nobody granted one). Kletterer's own PF1e text bundles a flat +8 Volksbonus
on Klettern checks with the climb speed itself ("und den daraus
resultierenden Volksbonus"), so its one handler below returns both a
CLIMB_SPEED and a SKILL `Modifier` — kept here rather than split into
`race_abilities.py`'s skill-bonus slice, since a single ability id may only
be registered in one of `HANDLERS`' source modules (`rules/handlers.py`'s
docstring) and this ability's defining mechanic is the movement mode, the
skill bonus merely its stated consequence.

`fast_movement` is the generic, reusable factory a class's own fast-movement
ability partial-applies (e.g. `rules/classes/barbarian.py`'s "Schnelle
Bewegung", CLAUDE.md's "trivial cases share one generic handler factory"
guidance) — a *class*-granted ability, so its concrete id/registration lives
in that class's own file (`rules/classes/`, one file per class — CLAUDE.md's
"Working Conventions"), not here; this module only hosts the shape every
such ability shares. `class_speed_bonus` below therefore looks up a granted
ability id against `rules/handlers.py`'s full merged registry, not this
module's own smaller `HANDLERS` — the id could now live in any class file."""

import functools
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .context import CharacterContext
from .modifiers import Modifier, ModifierTarget, SkillNote, stack
from .skill_ids import AKROBATIK_SKILL_ID, KLETTERN_SKILL_ID

RACE_NORMAL_SPEED_ABILITY_ID = UUID("2e0186d5-e532-4532-b7f7-b4c6f4834bde")
RACE_SLOW_SPEED_ABILITY_ID = UUID("9a5db666-54d4-4112-b750-dbb1abf1265d")

# Katzenvolk's "Kletterer" alternate racial trait (`base_race_abilities.json`;
# `race_ability_grants.json`'s `is_alternate=True` row; replaces "Spurter"
# per `race_ability_replacements.json`) — see module docstring for why its
# handler lives here rather than in `race_abilities.py`.
KLETTERER_ABILITY_ID = UUID("79808852-df0d-49f6-a780-c00db591ad95")


def _base_speed(context: CharacterContext, *, meters: int) -> list[Modifier]:
    # Unconditional, same as race_abilities.py's `_attribute_bonus` — a
    # race's base speed never depends on anything about the character it's
    # granted to.
    del context
    return [Modifier(source="race", type="base", value=meters, target=ModifierTarget.SPEED)]


def _kletterer(context: CharacterContext) -> list[Modifier]:
    # Unconditional, same reasoning as `_base_speed` above — once granted,
    # Kletterer's climb speed and its Volksbonus are always present, neither
    # depends on anything about the character.
    del context
    return [
        Modifier(source="Kletterer", type="base", value=6, target=ModifierTarget.CLIMB_SPEED),
        Modifier(source="Kletterer", type="racial", value=8, target=ModifierTarget.SKILL, target_id=str(KLETTERN_SKILL_ID)),
    ]


def fast_movement(context: CharacterContext, *, meters: int) -> list[Modifier]:
    """A flat, always-stacking (`type="untyped"`) bonus to land speed —
    the shape PF1e's various "fast movement"-style class features share
    (Barbar/Entfesselter Barbar's "Schnelle Bewegung", Mönch's
    "Schnelligkeit", ...): per PF1e RAW text ("dieser Bonus ist kumulativ
    mit allen anderen Boni... auf seine Bewegungsrate an Land"), deliberately
    not a one-time flat add. `class_speed_bonus` below calls a granted
    ability's handler once per currently-qualified grant, not once per
    distinct id, so a genuinely repeating fast-movement feature (granted
    again at higher levels) stacks correctly with no change needed here —
    each class file just registers its own ability id against this same
    factory, parameterized with its own `meters`."""
    # Unconditional: ownership/repetition count is already decided by the
    # caller (`class_speed_bonus`'s per-grant loop below), not by anything
    # this handler would read off `context` itself.
    del context
    return [Modifier(source="Schnelle Bewegung", type="untyped", value=meters, target=ModifierTarget.SPEED)]


# This module's own slice of `rules/handlers.py`'s unified `HANDLERS` —
# race-tied speed content only. A class's fast-movement ability (built from
# `fast_movement` above) registers its id in that class's own file under
# `rules/classes/`, not here.
HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    RACE_NORMAL_SPEED_ABILITY_ID: functools.partial(_base_speed, meters=9),
    RACE_SLOW_SPEED_ABILITY_ID: functools.partial(_base_speed, meters=6),
    KLETTERER_ABILITY_ID: _kletterer,
}

# `race_speed` only ever resolves a race's own base-speed grant, never
# anything conditional on a character — same reasoning as
# `routers/races.py`'s `_NO_CHARACTER_CONTEXT` (that module's `HANDLERS`
# entries, from `race_abilities.py`, share the exact same "ignores context"
# property as `_base_speed` above).
_NO_CHARACTER_CONTEXT = CharacterContext()


def race_speed(db: Session, race_id: UUID) -> int | None:
    """This race's base land speed in meters, from its non-alternate speed
    grant."""
    # Imported here, not at module level: `rules/handlers.py` merges this
    # module's `HANDLERS` for `models/character.py` to use, and
    # `models/character.py` loads partway through `models/__init__.py`
    # (before `RaceAbilityGrant` is defined there) — a module-level `from
    # ..models import RaceAbilityGrant` here would make that a circular
    # import. Deferred to call time, well after `models` is fully loaded.
    from ..models import RaceAbilityGrant

    grants = db.scalars(
        select(RaceAbilityGrant).where(RaceAbilityGrant.race_id == race_id, RaceAbilityGrant.is_alternate.is_(False))
    ).all()
    modifiers: list[Modifier] = []
    for grant in grants:
        handler = HANDLERS.get(grant.ability_id)
        if handler is not None:
            modifiers.extend(m for m in handler(_NO_CHARACTER_CONTEXT) if m.target == ModifierTarget.SPEED)
    return stack(modifiers) if modifiers else None


def race_climb_speed(race_ability_ids: set[UUID]) -> int | None:
    """This character's climb speed in meters, or `None` if nothing grants
    one (the overwhelming majority of characters). Unlike `race_speed`
    above, which only ever needs a race's unconditional non-alternate grant
    (every race has exactly one base-speed ability), a climb speed today
    comes exclusively from an *alternate* trait (Katzenvolk's Kletterer), so
    this takes `race_ability_ids` — `effective_race_ability_ids`'s
    already-resolved set, the same input `routers/races.py`'s
    `race_skill_modifiers` uses for the same reason — rather than a bare
    `race_id`."""
    modifiers: list[Modifier] = []
    for ability_id in race_ability_ids:
        handler = HANDLERS.get(ability_id)
        if handler is not None:
            modifiers.extend(m for m in handler(_NO_CHARACTER_CONTEXT) if m.target == ModifierTarget.CLIMB_SPEED)
    return stack(modifiers) if modifiers else None


def class_speed_bonus(context: CharacterContext) -> int:
    """Total land-speed bonus (meters) from this character's actually-granted
    class abilities (`context.granted_ability_ids` — a `Counter`, already
    resolved against level count/archetype/option picks by `sheet.py`'s
    `granted_class_ability_ids` before it's placed on `context`). The
    handler is called once per qualifying grant, not once per distinct
    ability id, so a repeatedly-granted fast-movement feature stacks
    correctly (see `fast_movement`'s docstring).

    Looks a granted ability id up against `rules/handlers.py`'s full merged
    registry, not this module's own `HANDLERS`: a class's fast-movement
    ability is registered in that class's own file under `rules/classes/`
    (CLAUDE.md's "Working Conventions"), which could be any of them — this
    function has no way to know which one without asking the merged
    registry. Imported here, not at module level, since `rules/handlers.py`
    itself imports this module's own `HANDLERS` — a module-level import here
    would be circular."""
    from .handlers import HANDLERS as _MERGED_HANDLERS

    modifiers: list[Modifier] = []
    for ability_id, count in context.granted_ability_ids.items():
        handler = _MERGED_HANDLERS.get(ability_id)
        if handler is None:
            continue
        for _ in range(count):
            modifiers.extend(m for m in handler(context) if m.target == ModifierTarget.SPEED)
    return stack(modifiers)


def jump_skill_bonus(total_land_speed: int) -> int:
    """Volksbonus (PF1e "racial" bonus type, `type="racial"` on a `Modifier`
    if/once this feeds one) on Akrobatik checks specifically to jump
    (Hoch-/Weitsprung), per the Akrobatik skill's "Springen" rule: +4 per
    full 3 m the character's *already fully resolved* land speed
    (`race_speed(...) + class_speed_bonus(...)`, not just the racial part)
    is above 9 m, or -4 per full 3 m it's below — partial 3 m steps don't
    count (a character at 11 m gets +0, not a fraction of +4)."""
    diff = total_land_speed - 9
    increments = abs(diff) // 3
    return 4 * increments if diff >= 0 else -4 * increments


def jump_skill_note(total_land_speed: int) -> SkillNote:
    """Scope 3 ("conditional for all characters") of
    `rules/handlers.py`'s `SITUATIONAL_SKILL_HANDLERS` model: this bonus is
    an automatic consequence of a character's resolved speed, not something
    any ability/feat/trait grants — there's no catalog UUID to key a
    `SITUATIONAL_SKILL_HANDLERS` entry off, so unlike Wilder Seemann this
    isn't looked up by id at all. `sheet.py`'s `_build_skills` instead calls
    this directly and unconditionally for every character (every character
    can attempt a jump), the same way `race_speed`'s base-speed grant is
    unconditional rather than composition-gated.

    Always returns a note, even when the bonus is exactly 0 (a character at
    the default 9 m land speed) — unlike an id-keyed `SITUATIONAL_SKILL_HANDLERS`
    entry, which is simply never invoked for a character who lacks the
    triggering id, there's no "doesn't apply" state here: every character's
    Akrobatik total does interact with their speed for a jump check, +0 is
    itself the answer, not an absence of one. Only applies to jump checks,
    not Akrobatik's other uses (Balancieren, Abrollen, ...), so `_build_skills`
    never folds this into the general Akrobatik `value` shown on the skill
    row — it only appears combined with that value in the row's info-note (a
    ready-to-roll jump total)."""
    bonus = jump_skill_bonus(total_land_speed)
    return SkillNote(
        skill_id=AKROBATIK_SKILL_ID,
        title="Sprung (Hoch-/Weitsprung)",
        modifier_label="Volksbonus/-malus",
        value=bonus,
        detail=f" bei {total_land_speed} m Bewegungsrate, 4 pro volle 3 m über/unter 9 m",
    )
