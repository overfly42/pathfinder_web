"""Mystiker (Oracle) handlers — one file per class (CLAUDE.md's "Working
Conventions"). Feeds `rules/handlers.py`'s unified `HANDLERS`, same
merge-only role `race_abilities.py`/`speed.py` play for their own slices —
this file owns every Mystiker ability id and its computation; nothing
outside it should reference these ids directly."""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..modifiers import Modifier, ModifierTarget
from ..progression import ability_mod

# Mystiker's own root `BaseClass` id (`base_classes.json`) — needed by
# Luftbarriere's level-scaled AC bonus below, which scales with *this*
# class's own levels, not total character level.
MYSTIKER_ROOT_CLASS_ID = UUID("949fe615-12a0-4eed-9e2e-25eaab3e3153")

# Mystiker's "Luftbarriere" revelation (`base_class_abilities.json` id
# 71b3df2b-…, option-choice-gated like Barbarian's Bestientotem — granted
# via `base_class_ability_grants.json`'s `option_choice_id`, so
# `context.granted_ability_ids`/`context.has_active` only ever see it once a
# player has actually picked this revelation). PRD text: "einen
# Rüstungsbonus von +4 [...] steigt auf der 7. Stufe und danach alle vier
# weiteren Stufen als Mystiker um +2 [...] täglich für 1 Stunde für je eine
# deiner Stufen als Mystiker [...] muss nicht aufeinander folgen, wird aber
# in Einheiten von jeweils 1 Stunde abgerechnet."
#
# The "billed in whole 1-hour units" clause is modeled the same way
# Kampfmagus's Arkaner Vorrat bills its own per-activation pool cost: this
# id is registered in `POOL_COST_AT_ACTIVATION` below (1 "Stunde" charged
# once, at activation, regardless of how long the effect actually stays
# active) rather than accruing continuously through `advance_time`'s
# generic per-round debit the way Kampfrausch's rounds/day does — see that
# registry's own docstring in `kampfmagus.py` for why the two pool shapes
# need telling apart. `base_class_abilities.json`'s `default_duration_rounds:
# 600` pre-fills the activation popup's duration field to exactly one hour,
# nudging normal play toward "one activation = one hour block"; a player who
# manually stretches the duration field past 600 rounds and keeps the
# effect running longer than that still only ever pays the one flat hour
# charged at activation — a known simplification, not a second, continuous
# billing pass. Reactivating for each additional hour of use (matching the
# "non-consecutive, billed per hour" RAW framing) is the correct action for
# longer continuous use.
#
# Not modeled: the 13th-level "50% miss chance against ranged attacks"
# clause — no miss-chance mechanic exists anywhere in this codebase to hang
# it on (same "no engine for this yet" scope as e.g. `weapon_abilities.py`'s
# unmodeled crit effects).
LUFTBARRIERE_ABILITY_ID = UUID("71b3df2b-2528-5c08-b734-ceec9643538b")


def _luftbarriere(context: CharacterContext) -> list[Modifier]:
    """Self-scoped toggle, same "presence not sum" reasoning
    `rules/classes/barbarian.py`'s `_kampfrausch_entfesselter_barbar`
    documents: this either isn't active (no bonus) or is (exactly one flat
    bonus, scaled by level) — there's no state where a character has two
    independent instances of their own Luftbarriere running at once.
    `type="armor"`: an armor bonus, so it correctly never stacks with worn
    armor's own bonus or a second source of armor bonus (`stack()`'s
    same-type-cap rule) — same convention `_magierruestung` in
    `rules/effects.py` already documents for its own +4 armor bonus."""
    if not context.has_active(LUFTBARRIERE_ABILITY_ID):
        return []
    mystiker_level = context.level_counts_by_root_id.get(MYSTIKER_ROOT_CLASS_ID, 0)
    bonus = 4 + 2 * max(0, (mystiker_level - 3) // 4)
    return [Modifier(source="Luftbarriere", type="armor", value=bonus, target=ModifierTarget.AC)]


def _luftbarriere_hours_per_day(context: CharacterContext) -> int:
    """"1 Stunde für je eine deiner Stufen als Mystiker" — unlike
    Kampfrausch's rounds/day pool, this one is never touched by
    `advance_time`'s per-round debit (see `LUFTBARRIERE_ABILITY_ID`'s
    docstring: it's a `POOL_COST_AT_ACTIVATION` id instead), so the pool can
    be counted in its own natural unit, whole hours, rather than rounds."""
    return context.level_counts_by_root_id.get(MYSTIKER_ROOT_CLASS_ID, 0)


# Wind-Mysterium's "Elektrische Berührung" revelation (`base_class_abilities
# .json` id 9d1c6536-…, option-choice-gated the same way as Luftbarriere
# above — both sit under the "Wind" mystery choice group). PRD text: "Als
# Standard-Aktion kannst du einen Berührungsangriff im Nahkampf ausführen,
# der 1W6 Punkte Elektrizitätsschaden +1 Punkt für je zwei deiner Stufen als
# Mystiker verursacht. Du kannst diese Fähigkeit täglich in Höhe deines
# CH-Modifikators +3 einsetzen. Ab der 11. Stufe gilt jede Waffe, die du
# benutzt, als Blitz-Waffe."
#
# Only the daily-use count is modeled here (`DAILY_LIMITS` below) — same
# "player-reminder text only" scope `rules/classes/hexenmeister.py`'s
# Wasserstoß already establishes for a touch-attack ability: the touch
# attack roll itself and its 1d6+½-level electricity damage stay the
# player's own call, since there's no attack-roll/damage-resolution engine
# anywhere in this codebase to hang them on (`BaseClassAbility` itself has no
# damage-dice/damage-type field at all — every implemented ability's damage
# lives purely in the stored `description` prose). Also not modeled: the
# 11th-level "every weapon you use counts as a Blitz-Waffe" clause — there's
# no mechanism anywhere for a class feature to grant a temporary weapon
# special ability to whichever weapon a character happens to be wielding
# (`rules/weapon_abilities.py` only resolves real, catalog-backed weapon
# enchantments already attached to a `CharacterGear` row); sibling revelation
# Winterliche Berührung (Eis-Waffe at 11th) has the identical gap and is
# likewise unimplemented.
ELEKTRISCHE_BERUEHRUNG_ABILITY_ID = UUID("9d1c6536-1914-5fe6-91ce-d47e5479f783")


def _elektrische_beruehrung_uses_per_day(context: CharacterContext) -> int:
    """"täglich in Höhe deines CH-Modifikators +3" — flat CH-mod + 3,
    doesn't scale with Mystiker level, identical shape to Hexenmeister's
    Wasserstoß (`rules/classes/hexenmeister.py`)."""
    return ability_mod(context.ability_scores.get("CH", 10)) + 3


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    LUFTBARRIERE_ABILITY_ID: _luftbarriere,
}

# This class's slice of `rules/handlers.py`'s merged `DAILY_LIMITS` — how
# many rounds/uses per day a daily-limited ability id grants, computed (not
# fixed), same locality convention as `HANDLERS` above.
DAILY_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    LUFTBARRIERE_ABILITY_ID: _luftbarriere_hours_per_day,
    ELEKTRISCHE_BERUEHRUNG_ABILITY_ID: _elektrische_beruehrung_uses_per_day,
}

# This class's slice of `rules/handlers.py`'s merged `POOL_COST_AT_ACTIVATION`
# — see `LUFTBARRIERE_ABILITY_ID`'s docstring above for why this ability
# pays a flat 1-"Stunde" cost once at activation rather than accruing
# continuously.
POOL_COST_AT_ACTIVATION: dict[UUID, int] = {
    LUFTBARRIERE_ABILITY_ID: 1,
}

# This class's slice of `rules/handlers.py`'s merged `DAILY_LIMIT_UNIT_LABEL`
# — every `DAILY_LIMITS` id before this one happened to be either rounds/day
# (Kampfrausch) or points (Arkaner Vorrat); Luftbarriere's pool is whole
# hours.
DAILY_LIMIT_UNIT_LABEL: dict[UUID, str] = {
    LUFTBARRIERE_ABILITY_ID: "Stunden",
}
