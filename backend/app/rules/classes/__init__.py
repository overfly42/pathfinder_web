"""Per-class handler files — one module per class, closely related variants
(a class and its unchained/archetype sibling, e.g. `barbarian.py`'s Barbar +
Entfesselter Barbar) sharing a file rather than one per grantor
(CLAUDE.md's "Working Conventions"). Organized by class instead of by
mechanic family (the older `race_abilities.py`/`speed.py`/`effects.py`
split): class abilities are numerous and individually complex enough
(PF1e's ~40 classes/archetypes, each with many distinct features) that a
single `class_abilities.py` would grow without a natural seam, the same
concern that already keeps `base_class_abilities.json` split from
`base_race_abilities.json` — each class module is small and self-contained,
easy to find, easy to blame.

This module only merges every class file's own `HANDLERS`/`DAILY_LIMITS`/
`TEMP_HP_GRANTS`/`ON_END`/`SITUATIONAL_SKILL_HANDLERS`/
`WEAPON_BONUS_DAMAGE_HANDLERS`/`WEAPON_ENHANCEMENT_HANDLERS`/
`POOL_COST_AT_ACTIVATION`/`APPLIED_OUTSIDE_HANDLERS_IDS` into one dict (or
set) apiece, the same merge-only role `rules/handlers.py` plays for every
family —
`rules/handlers.py` imports this package's dicts, not each class file
individually, so a new class module only needs registering once, here.

Adding a class: create `rules/classes/<class_name>.py`, define its
handlers, export its own `HANDLERS: dict[UUID, Callable[[CharacterContext],
list[Modifier]]]` (ability ids are globally unique, hand-frozen UUIDs, same
convention as every other catalog — see `race_abilities.py`'s docstring —
so merging can never silently shadow one class's handler with another's),
and, only if it actually has content for them, its own `DAILY_LIMITS`/
`TEMP_HP_GRANTS`/`ON_END`/`SITUATIONAL_SKILL_HANDLERS` slices (see
`rules/handlers.py` for what each covers) — then merge whichever it defines
in below."""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..modifiers import Modifier, NaturalAttack, SkillNote
from .barbarian import DAILY_LIMITS as _BARBARIAN_DAILY_LIMITS
from .barbarian import HANDLERS as _BARBARIAN_HANDLERS
from .barbarian import NATURAL_ATTACK_HANDLERS as _BARBARIAN_NATURAL_ATTACK_HANDLERS
from .barbarian import ON_END as _BARBARIAN_ON_END
from .barbarian import SITUATIONAL_SKILL_HANDLERS as _BARBARIAN_SITUATIONAL_SKILL_HANDLERS
from .barbarian import TEMP_HP_GRANTS as _BARBARIAN_TEMP_HP_GRANTS
from .barbarian import WEAPON_BONUS_DAMAGE_HANDLERS as _BARBARIAN_WEAPON_BONUS_DAMAGE_HANDLERS
from .kampfmagus import APPLIED_OUTSIDE_HANDLERS_IDS as _KAMPFMAGUS_APPLIED_OUTSIDE_HANDLERS_IDS
from .kampfmagus import DAILY_LIMIT_UNIT_LABEL as _KAMPFMAGUS_DAILY_LIMIT_UNIT_LABEL
from .kampfmagus import DAILY_LIMITS as _KAMPFMAGUS_DAILY_LIMITS
from .kampfmagus import HANDLERS as _KAMPFMAGUS_HANDLERS
from .kampfmagus import POOL_COST_AT_ACTIVATION as _KAMPFMAGUS_POOL_COST_AT_ACTIVATION
from .kampfmagus import POOL_SOURCE_ID as _KAMPFMAGUS_POOL_SOURCE_ID
from .kampfmagus import SPELL_SLOT_DELTA as _KAMPFMAGUS_SPELL_SLOT_DELTA
from .kampfmagus import WEAPON_ENHANCEMENT_HANDLERS as _KAMPFMAGUS_WEAPON_ENHANCEMENT_HANDLERS

HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    **_BARBARIAN_HANDLERS,
    **_KAMPFMAGUS_HANDLERS,
}
NATURAL_ATTACK_HANDLERS: dict[UUID, Callable[[CharacterContext], NaturalAttack | None]] = {
    **_BARBARIAN_NATURAL_ATTACK_HANDLERS,
}
WEAPON_BONUS_DAMAGE_HANDLERS: dict[UUID, Callable[[CharacterContext], tuple[str, str] | None]] = {
    **_BARBARIAN_WEAPON_BONUS_DAMAGE_HANDLERS,
}
# An ability id's currently active temporary enhancement bonus on one
# specific `CharacterGear` row, or `None` if not currently active — see
# `rules/handlers.py`'s own merged `WEAPON_ENHANCEMENT_HANDLERS` docstring.
# Only Kampfmagus's Arkaner Vorrat contributes today.
WEAPON_ENHANCEMENT_HANDLERS: dict[UUID, Callable[[CharacterContext], tuple[UUID, int] | None]] = {
    **_KAMPFMAGUS_WEAPON_ENHANCEMENT_HANDLERS,
}

# Merged the same way as `HANDLERS` above — see `rules/handlers.py`'s
# `DAILY_LIMITS`/`TEMP_HP_GRANTS`/`ON_END`/`SITUATIONAL_SKILL_HANDLERS`
# docstrings for what each covers.
DAILY_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    **_BARBARIAN_DAILY_LIMITS,
    **_KAMPFMAGUS_DAILY_LIMITS,
}
# Ability ids whose active effect pays its own `DAILY_LIMITS` pool cost once
# at activation rather than accruing it per round of active duration — see
# `rules/classes/kampfmagus.py`'s `ARKANER_VORRAT_ABILITY_ID` docstring, the
# only source today. A flat ability-id -> point-cost map, not a `Callable`:
# every current entry is a fixed constant.
POOL_COST_AT_ACTIVATION: dict[UUID, int] = {
    **_KAMPFMAGUS_POOL_COST_AT_ACTIVATION,
}
# An ability id -> the id of the pool it actually draws from, when that
# differs from its own id (`rules/daily_limits.py`'s own docstring). Absent
# means "draws from its own pool" — every entry before Kampfmagus's Arkaner-
# Vorrat-spending tricks.
POOL_SOURCE_ID: dict[UUID, UUID] = {
    **_KAMPFMAGUS_POOL_SOURCE_ID,
}
# Display unit ("Runden"/"Punkte"/...) for a `DAILY_LIMITS` id's sheet text
# — see `rules/classes/kampfmagus.py`'s own docstring.
DAILY_LIMIT_UNIT_LABEL: dict[UUID, str] = {
    **_KAMPFMAGUS_DAILY_LIMIT_UNIT_LABEL,
}
TEMP_HP_GRANTS: dict[UUID, Callable[[CharacterContext], int]] = {
    **_BARBARIAN_TEMP_HP_GRANTS,
}
ON_END: dict[UUID, Callable[[CharacterContext], tuple[UUID, int]]] = {
    **_BARBARIAN_ON_END,
}
SITUATIONAL_SKILL_HANDLERS: dict[UUID, Callable[[CharacterContext], list[SkillNote]]] = {
    **_BARBARIAN_SITUATIONAL_SKILL_HANDLERS,
}
# Merged the same way, but a flat ability-id -> int map rather than a
# handler `Callable` — every current entry is a fixed constant that never
# depends on character state, so a `CharacterContext`-taking function would
# just be unused indirection (see `rules/spells.py`'s `total_spell_slots`,
# the one consumer).
SPELL_SLOT_DELTA: dict[UUID, int] = {
    **_KAMPFMAGUS_SPELL_SLOT_DELTA,
}

# Merged the same way as `HANDLERS` above, but a plain id set rather than a
# dict — see `kampfmagus.py`'s own `APPLIED_OUTSIDE_HANDLERS_IDS` docstring
# for what this covers (`rules/handlers.py`'s `has_mechanical_effect` reads
# the merged result).
APPLIED_OUTSIDE_HANDLERS_IDS: frozenset[UUID] = frozenset(_KAMPFMAGUS_APPLIED_OUTSIDE_HANDLERS_IDS)
