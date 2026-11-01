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
`SAVE_DC_HANDLERS`/`TEMP_HP_GRANTS`/`ON_END`/`SITUATIONAL_SKILL_HANDLERS`/
`WEAPON_BONUS_DAMAGE_HANDLERS`/`WEAPON_ENHANCEMENT_HANDLERS`/
`POOL_COST_AT_ACTIVATION`/`WEAPON_PROFICIENCY_HANDLERS`/`FEATURE_SUMMARY_HANDLERS`/
`APPLIED_OUTSIDE_HANDLERS_IDS` into one dict (or
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
from .druide import DAILY_LIMIT_UNIT_LABEL as _DRUIDE_DAILY_LIMIT_UNIT_LABEL
from .druide import DAILY_LIMITS as _DRUIDE_DAILY_LIMITS
from .druide import FEATURE_SUMMARY_HANDLERS as _DRUIDE_FEATURE_SUMMARY_HANDLERS
from .druide import HANDLERS as _DRUIDE_HANDLERS
from .druide import NATURAL_ATTACK_HANDLERS as _DRUIDE_NATURAL_ATTACK_HANDLERS
from .druide import POOL_COST_AT_ACTIVATION as _DRUIDE_POOL_COST_AT_ACTIVATION
from .druide import POOL_SOURCE_ID as _DRUIDE_POOL_SOURCE_ID
from .druide import WEAPON_PROFICIENCY_HANDLERS as _DRUIDE_WEAPON_PROFICIENCY_HANDLERS
from .hexenmeister import DAILY_LIMITS as _HEXENMEISTER_DAILY_LIMITS
from .hexenmeister import HANDLERS as _HEXENMEISTER_HANDLERS
from .hexenmeister import SAVE_DC_HANDLERS as _HEXENMEISTER_SAVE_DC_HANDLERS
from .jaeger import APPLIED_OUTSIDE_HANDLERS_IDS as _JAEGER_APPLIED_OUTSIDE_HANDLERS_IDS
from .jaeger import CLASS_SKILL_GRANTS as _JAEGER_CLASS_SKILL_GRANTS
from .jaeger import COMPANION_EFFECT_IDS as _JAEGER_COMPANION_EFFECT_IDS
from .jaeger import DAILY_LIMIT_UNIT_LABEL as _JAEGER_DAILY_LIMIT_UNIT_LABEL
from .jaeger import DAILY_LIMITS as _JAEGER_DAILY_LIMITS
from .jaeger import EFFECT_OPTION_LIMITS as _JAEGER_EFFECT_OPTION_LIMITS
from .jaeger import FEATURE_SUMMARY_HANDLERS as _JAEGER_FEATURE_SUMMARY_HANDLERS
from .jaeger import HANDLERS as _JAEGER_HANDLERS
from .jaeger import PARTIAL_EFFECT_NOTES as _JAEGER_PARTIAL_EFFECT_NOTES
from .jaeger import POOL_COST_AT_ACTIVATION as _JAEGER_POOL_COST_AT_ACTIVATION
from .jaeger import SITUATIONAL_SKILL_HANDLERS as _JAEGER_SITUATIONAL_SKILL_HANDLERS
from .kampfmagus import APPLIED_OUTSIDE_HANDLERS_IDS as _KAMPFMAGUS_APPLIED_OUTSIDE_HANDLERS_IDS
from .kampfmagus import DAILY_LIMIT_UNIT_LABEL as _KAMPFMAGUS_DAILY_LIMIT_UNIT_LABEL
from .kampfmagus import DAILY_LIMITS as _KAMPFMAGUS_DAILY_LIMITS
from .kampfmagus import HANDLERS as _KAMPFMAGUS_HANDLERS
from .kampfmagus import POOL_COST_AT_ACTIVATION as _KAMPFMAGUS_POOL_COST_AT_ACTIVATION
from .kampfmagus import POOL_SOURCE_ID as _KAMPFMAGUS_POOL_SOURCE_ID
from .kampfmagus import SPELL_SLOT_DELTA as _KAMPFMAGUS_SPELL_SLOT_DELTA
from .kampfmagus import WEAPON_ENHANCEMENT_HANDLERS as _KAMPFMAGUS_WEAPON_ENHANCEMENT_HANDLERS
from .kleriker import CLASS_SKILL_GRANTS as _KLERIKER_CLASS_SKILL_GRANTS
from .kleriker import PARTIAL_EFFECT_NOTES as _KLERIKER_PARTIAL_EFFECT_NOTES
from .magier import HANDLERS as _MAGIER_HANDLERS
from .magier import PARTIAL_EFFECT_NOTES as _MAGIER_PARTIAL_EFFECT_NOTES
from .moench import DAILY_LIMITS as _MOENCH_DAILY_LIMITS
from .moench import HANDLERS as _MOENCH_HANDLERS
from .moench import SAVE_DC_HANDLERS as _MOENCH_SAVE_DC_HANDLERS
from .mystiker import DAILY_LIMIT_UNIT_LABEL as _MYSTIKER_DAILY_LIMIT_UNIT_LABEL
from .mystiker import DAILY_LIMITS as _MYSTIKER_DAILY_LIMITS
from .mystiker import HANDLERS as _MYSTIKER_HANDLERS
from .mystiker import POOL_COST_AT_ACTIVATION as _MYSTIKER_POOL_COST_AT_ACTIVATION
from .paladin import DAILY_LIMIT_UNIT_LABEL as _PALADIN_DAILY_LIMIT_UNIT_LABEL
from .paladin import DAILY_LIMITS as _PALADIN_DAILY_LIMITS
from .paladin import FEATURE_SUMMARY_HANDLERS as _PALADIN_FEATURE_SUMMARY_HANDLERS
from .paladin import HANDLERS as _PALADIN_HANDLERS
from .paladin import POOL_COST_AT_ACTIVATION as _PALADIN_POOL_COST_AT_ACTIVATION
from .paladin import POOL_SOURCE_ID as _PALADIN_POOL_SOURCE_ID
from .paladin import WEAPON_ENHANCEMENT_HANDLERS as _PALADIN_WEAPON_ENHANCEMENT_HANDLERS
from .tiergefaehrte import APPLIED_OUTSIDE_HANDLERS_IDS as _TIERGEFAEHRTE_APPLIED_OUTSIDE_HANDLERS_IDS
from .tiergefaehrte import FEATURE_SUMMARY_HANDLERS as _TIERGEFAEHRTE_FEATURE_SUMMARY_HANDLERS
from .tiergefaehrte import HANDLERS as _TIERGEFAEHRTE_HANDLERS
from .tiergefaehrte import PARTIAL_EFFECT_NOTES as _TIERGEFAEHRTE_PARTIAL_EFFECT_NOTES
from .vertrauter import FEATURE_SUMMARY_HANDLERS as _VERTRAUTER_FEATURE_SUMMARY_HANDLERS

HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    **_BARBARIAN_HANDLERS,
    **_DRUIDE_HANDLERS,
    **_HEXENMEISTER_HANDLERS,
    **_JAEGER_HANDLERS,
    **_KAMPFMAGUS_HANDLERS,
    **_MAGIER_HANDLERS,
    **_MOENCH_HANDLERS,
    **_MYSTIKER_HANDLERS,
    **_PALADIN_HANDLERS,
    **_TIERGEFAEHRTE_HANDLERS,
}
# A handler may return several attacks at once (a Tierschamane's bite and
# claws) — see `rules/handlers.py`'s merged registry.
NATURAL_ATTACK_HANDLERS: dict[UUID, Callable[[CharacterContext], NaturalAttack | list[NaturalAttack] | None]] = {
    **_BARBARIAN_NATURAL_ATTACK_HANDLERS,
    **_DRUIDE_NATURAL_ATTACK_HANDLERS,
}
WEAPON_BONUS_DAMAGE_HANDLERS: dict[UUID, Callable[[CharacterContext], tuple[str, str] | None]] = {
    **_BARBARIAN_WEAPON_BONUS_DAMAGE_HANDLERS,
}
# An ability id's currently active temporary enhancement bonus on one
# specific `CharacterGear` row, or `None` if not currently active — see
# `rules/handlers.py`'s own merged `WEAPON_ENHANCEMENT_HANDLERS` docstring.
# Kampfmagus's Arkaner Vorrat and the Paladin's weapon-spirit Göttlicher Bund.
WEAPON_ENHANCEMENT_HANDLERS: dict[UUID, Callable[[CharacterContext], tuple[UUID, int] | None]] = {
    **_KAMPFMAGUS_WEAPON_ENHANCEMENT_HANDLERS,
    **_PALADIN_WEAPON_ENHANCEMENT_HANDLERS,
}

# Merged the same way as `HANDLERS` above — see `rules/handlers.py`'s
# `DAILY_LIMITS`/`TEMP_HP_GRANTS`/`ON_END`/`SITUATIONAL_SKILL_HANDLERS`
# docstrings for what each covers.
DAILY_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    **_BARBARIAN_DAILY_LIMITS,
    **_DRUIDE_DAILY_LIMITS,
    **_HEXENMEISTER_DAILY_LIMITS,
    **_JAEGER_DAILY_LIMITS,
    **_KAMPFMAGUS_DAILY_LIMITS,
    **_MOENCH_DAILY_LIMITS,
    **_MYSTIKER_DAILY_LIMITS,
    **_PALADIN_DAILY_LIMITS,
}
# A daily-limited class ability's own save DC, when it has one (e.g.
# Hexenmeister's Wasserstoß) — see `rules/handlers.py`'s `SAVE_DC_HANDLERS`
# docstring for what this covers.
SAVE_DC_HANDLERS: dict[UUID, Callable[[CharacterContext], int]] = {
    **_HEXENMEISTER_SAVE_DC_HANDLERS,
    **_MOENCH_SAVE_DC_HANDLERS,
}
# Ability ids whose active effect pays its own `DAILY_LIMITS` pool cost once
# at activation rather than accruing it per round of active duration — see
# `rules/classes/kampfmagus.py`'s `ARKANER_VORRAT_ABILITY_ID` docstring, the
# only source today. A flat ability-id -> point-cost map, not a `Callable`:
# every current entry is a fixed constant.
POOL_COST_AT_ACTIVATION: dict[UUID, int] = {
    **_DRUIDE_POOL_COST_AT_ACTIVATION,
    **_JAEGER_POOL_COST_AT_ACTIVATION,
    **_KAMPFMAGUS_POOL_COST_AT_ACTIVATION,
    **_MYSTIKER_POOL_COST_AT_ACTIVATION,
    **_PALADIN_POOL_COST_AT_ACTIVATION,
}
# An ability id -> the id of the pool it actually draws from, when that
# differs from its own id (`rules/daily_limits.py`'s own docstring). Absent
# means "draws from its own pool" — every entry before Kampfmagus's Arkaner-
# Vorrat-spending tricks.
POOL_SOURCE_ID: dict[UUID, UUID] = {
    **_DRUIDE_POOL_SOURCE_ID,
    **_KAMPFMAGUS_POOL_SOURCE_ID,
    **_PALADIN_POOL_SOURCE_ID,
}
# Display unit ("Runden"/"Punkte"/...) for a `DAILY_LIMITS` id's sheet text
# — see `rules/classes/kampfmagus.py`'s own docstring.
DAILY_LIMIT_UNIT_LABEL: dict[UUID, str] = {
    **_DRUIDE_DAILY_LIMIT_UNIT_LABEL,
    **_JAEGER_DAILY_LIMIT_UNIT_LABEL,
    **_KAMPFMAGUS_DAILY_LIMIT_UNIT_LABEL,
    **_MYSTIKER_DAILY_LIMIT_UNIT_LABEL,
    **_PALADIN_DAILY_LIMIT_UNIT_LABEL,
}
TEMP_HP_GRANTS: dict[UUID, Callable[[CharacterContext], int]] = {
    **_BARBARIAN_TEMP_HP_GRANTS,
}
ON_END: dict[UUID, Callable[[CharacterContext], tuple[UUID, int]]] = {
    **_BARBARIAN_ON_END,
}
SITUATIONAL_SKILL_HANDLERS: dict[UUID, Callable[[CharacterContext], list[SkillNote]]] = {
    **_BARBARIAN_SITUATIONAL_SKILL_HANDLERS,
    **_JAEGER_SITUATIONAL_SKILL_HANDLERS,
}
# Merged the same way, but a flat ability-id -> int map rather than a
# handler `Callable` — every current entry is a fixed constant that never
# depends on character state, so a `CharacterContext`-taking function would
# just be unused indirection (see `rules/spells.py`'s `total_spell_slots`,
# the one consumer).
SPELL_SLOT_DELTA: dict[UUID, int] = {
    **_KAMPFMAGUS_SPELL_SLOT_DELTA,
}

# Exact `BaseItem` ids a granted class ability makes the character
# proficient with — the class half of `rules/handlers.py`'s
# `WEAPON_PROFICIENCY_HANDLERS` (Druide's named weapon list).
WEAPON_PROFICIENCY_HANDLERS: dict[UUID, frozenset[UUID]] = {
    **_DRUIDE_WEAPON_PROFICIENCY_HANDLERS,
}
# A short computed read-out shown next to a class feature on the sheet
# (e.g. Tierempathie's "1W20 + 7") — see `rules/handlers.py`'s
# `FEATURE_SUMMARY_HANDLERS` docstring.
FEATURE_SUMMARY_HANDLERS: dict[UUID, Callable[[CharacterContext], str]] = {
    **_DRUIDE_FEATURE_SUMMARY_HANDLERS,
    **_JAEGER_FEATURE_SUMMARY_HANDLERS,
    **_PALADIN_FEATURE_SUMMARY_HANDLERS,
    **_TIERGEFAEHRTE_FEATURE_SUMMARY_HANDLERS,
    **_VERTRAUTER_FEATURE_SUMMARY_HANDLERS,
}

# Merged the same way as `HANDLERS` above, but a plain id set rather than a
# dict — see `kampfmagus.py`'s own `APPLIED_OUTSIDE_HANDLERS_IDS` docstring
# for what this covers (`rules/handlers.py`'s `has_mechanical_effect` reads
# the merged result).
APPLIED_OUTSIDE_HANDLERS_IDS: frozenset[UUID] = (
    _JAEGER_APPLIED_OUTSIDE_HANDLERS_IDS
    | _KAMPFMAGUS_APPLIED_OUTSIDE_HANDLERS_IDS
    | _TIERGEFAEHRTE_APPLIED_OUTSIDE_HANDLERS_IDS
)

# The class half of `rules/handlers.py`'s `EFFECT_OPTION_LIMITS`/
# `COMPANION_EFFECT_IDS`.
EFFECT_OPTION_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    **_JAEGER_EFFECT_OPTION_LIMITS,
}
COMPANION_EFFECT_IDS: frozenset[UUID] = _JAEGER_COMPANION_EFFECT_IDS

# A granted class ability making a skill a class skill (the Göttlicher
# Jäger's Wissen (Religion), the Unterdomäne der Federn's Fliegen) — the
# class half of `rules/handlers.py`'s `CLASS_SKILL_GRANTS`.
CLASS_SKILL_GRANTS: dict[UUID, frozenset[UUID]] = {
    **_JAEGER_CLASS_SKILL_GRANTS,
    **_KLERIKER_CLASS_SKILL_GRANTS,
}
# The sheet's "Teilweise" badge text for a class ability whose effect is
# only partly computed — the class half of `rules/handlers.py`'s
# `PARTIAL_EFFECT_NOTES`.
PARTIAL_EFFECT_NOTES: dict[UUID, str] = {
    **_JAEGER_PARTIAL_EFFECT_NOTES,
    **_KLERIKER_PARTIAL_EFFECT_NOTES,
    **_MAGIER_PARTIAL_EFFECT_NOTES,
    **_TIERGEFAEHRTE_PARTIAL_EFFECT_NOTES,
}
