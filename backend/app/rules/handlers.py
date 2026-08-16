"""The unified ability-effect handler registry: one `HANDLERS: dict[UUID,
Callable[[CharacterContext], list[Modifier]]]` covering every ability id this
codebase can actually compute an effect for, regardless of which catalog
it's a row in (`BaseRaceAbility`, `BaseClassAbility`, active-effect source
ids, ...). This is the registry CLAUDE.md describes — "computing what an
ability actually does is always resolved by a Python-side handler function,
looked up by the ability's own UUID" — kept as one dict so every consumer
shares one lookup instead of each subsystem inventing its own handler dict.

Real integration point (2026-08-11, closing the gap the previous revision of
this module left open): every consumer that used to import a per-family
`HANDLERS`/`EFFECT_HANDLERS` slice directly now imports it from here instead
(`routers/races.py`, `models/character.py`, `sheet.py`'s `character_modifiers`
below) — the merged dict is the one every caller actually goes through, not
just documentation of the target shape.

Composition (which ability ids a given character actually has) stays
resolved separately per source — race grants are unconditional
(`routers/races.py`), class grants are level/archetype/option-gated and
repeat-count-aware (`sheet.py`'s `_granted_class_ability_ids`, `rules/speed.py`'s
`class_speed_bonus`) — since those gating rules differ by source and have
nothing to do with computing an effect. Only the "what does this ability id
compute" half is shared here.

Each source module authors its own slice of `HANDLERS` locally, for the
same locality/git-blame reason `base_class_abilities.json`/
`base_race_abilities.json` stay separate fixture files rather than one
combined one; this module only merges them. Race-tied content stays split
by mechanic (`race_abilities.py` for ability-score bonuses, `speed.py` for
base land speed) since there are few races and each one's handlers are
trivial one-liners; class-tied content is split by *class* instead
(`rules/classes/`, one file per class, e.g. `barbarian.py` — CLAUDE.md's
"Working Conventions") since PF1e's ~40 classes/archetypes each have many
individually complex features, a very different growth shape than races'.
Non-class-tied active effects (conditions/poisons/diseases) stay in
`effects.py`. Ability ids are globally unique across catalogs (each is its
own hand-frozen UUID, see `race_abilities.py`'s docstring), so the merge can
never silently shadow one source's handler with another's.

Every entry takes the uniform `CharacterContext` signature (`rules/context.py`,
`roadmap.md`'s "Uniform CharacterContext handler signature") as of
2026-08-10/11 — `rules/effects.py`'s `EFFECT_HANDLERS` is folded in here too
now that the signature difference that used to keep it separate is gone (see
that module's docstring).

## `SITUATIONAL_SKILL_HANDLERS` — conditional skill bonuses (2026-08-16)

`HANDLERS`' `Modifier`s are all unconditional: whatever a handler returns
gets stacked and folded straight into a stat's displayed value. Some PF1e
bonuses genuinely aren't unconditional — they only apply in a situation the
sheet has no way to detect on its own (Seeräuber's Wilder Seemann only
applies in water/on ships/at the coast; Akrobatik's jump-specific Volksbonus
only applies to a jump check, not Akrobatik's other uses). Folding one of
these into `value` would silently misrepresent the character (a dry-land
Klettern check shouldn't get Wilder Seemann's bonus). `SITUATIONAL_SKILL_HANDLERS:
dict[UUID, Callable[[CharacterContext], list[SkillNote]]]` is the parallel
registry for exactly this shape — `SkillNote` (`rules/modifiers.py`) instead
of `Modifier`, and `sheet.py`'s `_build_skills` renders every note as that
skill's info `note` rather than adding it to `value`.

Three scopes a conditional bonus's *trigger* can take, and how each is modeled:

1. **Only with a given class** (a granted class ability, gated by level/
   archetype/replacement — e.g. Wilder Seemann): keyed by that ability's own
   id in `SITUATIONAL_SKILL_HANDLERS`, contributed by the owning class's own
   file (`rules/classes/<class>.py`) and merged in via `rules/classes`, same
   pipeline `HANDLERS` already uses. Composition gating (does this character
   actually have the ability right now) is already fully resolved upstream
   by `sheet.py`'s `_granted_class_ability_ids` before it ever reaches this
   registry — a handler here only computes magnitude, the same division of
   labor `HANDLERS` keeps.
2. **Only with a specific talent (feat)**: the *same* `SITUATIONAL_SKILL_HANDLERS`
   dict, just keyed by a feat's id instead of a class ability's — catalog ids
   are globally unique across every family (the same guarantee that already
   lets `HANDLERS` merge race/class/effect ids into one dict without
   collision), so a feat-granted entry needs no dict of its own. No feat
   needs this yet, so nothing is registered for it today — the resolution
   loop below already checks `context.feat_ids`/`context.trait_ids` against
   this one merged dict regardless, so the day one does, it's a one-file
   addition with zero changes here or in `sheet.py`, the same promise
   `HANDLERS` already makes for unconditional effects.
3. **For every character, unconditionally** (nothing grants it — e.g. the
   jump bonus, an automatic consequence of resolved speed): NOT a
   `SITUATIONAL_SKILL_HANDLERS` entry, because there's no ability/feat/trait
   id to key a lookup off in the first place (same reasoning `jump_skill_bonus`
   already had for staying out of `HANDLERS`). `rules/speed.py`'s
   `jump_skill_note` stays a small function `sheet.py` calls directly and
   unconditionally for every character — forcing it through an id-keyed
   registry it structurally doesn't have an id for would be a worse fit, not
   a cleaner one. It shares `SkillNote` as its output shape purely so
   `_build_skills` has one rendering path regardless of which scope produced
   a given note."""

from collections.abc import Callable, Iterable
from uuid import UUID

from .classes import DAILY_LIMITS as _CLASS_DAILY_LIMITS
from .classes import HANDLERS as _CLASS_HANDLERS
from .classes import NATURAL_ATTACK_HANDLERS as _CLASS_NATURAL_ATTACK_HANDLERS
from .classes import ON_END as _CLASS_ON_END
from .classes import SITUATIONAL_SKILL_HANDLERS as _CLASS_SITUATIONAL_SKILL_HANDLERS
from .classes import TEMP_HP_GRANTS as _CLASS_TEMP_HP_GRANTS
from .context import CharacterContext
from .effects import EFFECT_HANDLERS as _EFFECT_HANDLERS
from .feats import HANDLERS as _FEAT_HANDLERS
from .modifiers import Modifier, NaturalAttack, SkillNote
from .race_abilities import HANDLERS as _RACE_ABILITY_HANDLERS
from .race_abilities import NATURAL_ATTACK_HANDLERS as _RACE_NATURAL_ATTACK_HANDLERS
from .speed import HANDLERS as _SPEED_HANDLERS

HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    **_RACE_ABILITY_HANDLERS,
    **_SPEED_HANDLERS,
    **_EFFECT_HANDLERS,
    **_CLASS_HANDLERS,
    **_FEAT_HANDLERS,
}

# Scopes 1/2 of this module's own "SITUATIONAL_SKILL_HANDLERS" docstring
# section above — only classes contribute today; a future feat-granted entry
# merges in here the same way.
SITUATIONAL_SKILL_HANDLERS: dict[UUID, Callable[[CharacterContext], list[SkillNote]]] = {
    **_CLASS_SITUATIONAL_SKILL_HANDLERS,
}

# How many rounds/uses per day a daily-limited ability id grants, computed
# per character (`rules/daily_limits.py`'s `CharacterAbilityUsage` tracks
# consumption against whatever this returns). Only class abilities
# contribute today (`rules/classes`'s own merge) — a future race ability
# with the same shape would merge in here the same way.
DAILY_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    **_CLASS_DAILY_LIMITS,
}

# Which bite/claw/etc.-style natural weapon attack an ability id grants, or
# `None` if it doesn't currently manifest (e.g. a rage power's claws while
# not raging — see `NaturalAttack`'s own docstring) — `sheet.py`'s
# `_build_natural_attacks`, folded into the same "Waffen" section
# `_build_weapon_attacks` renders. Not part of `HANDLERS` above: a
# `NaturalAttack` (`rules/modifiers.py`), not a `Modifier`.
NATURAL_ATTACK_HANDLERS: dict[UUID, Callable[[CharacterContext], NaturalAttack | None]] = {
    **_RACE_NATURAL_ATTACK_HANDLERS,
    **_CLASS_NATURAL_ATTACK_HANDLERS,
}

# How much temporary HP activating an ability id grants
# (`routers/characters.py`'s `activate_effect`), set directly onto
# `Character.temporary_hit_points` rather than through the `Modifier`/
# `stack()` pipeline (not a stat bonus).
TEMP_HP_GRANTS: dict[UUID, Callable[[CharacterContext], int]] = {
    **_CLASS_TEMP_HP_GRANTS,
}

# Which condition (id, duration in rounds) an ability id's active effect
# grants when it ends (`routers/characters.py`'s `_expire_effect`) — e.g.
# Kampfrausch ending into Erschöpft.
ON_END: dict[UUID, Callable[[CharacterContext], tuple[UUID, int]]] = {
    **_CLASS_ON_END,
}


def resolve_ids(ability_ids: Iterable[UUID], context: CharacterContext) -> list[Modifier]:
    """`readme.md`'s "Request pipeline" step 3: every id resolved exactly
    once, against the same raw `context`, via this single merged registry.
    An id with no handler (flavor text, e.g. Darkvision, or a race's size
    trait today) just passes through with no computed effect."""
    modifiers: list[Modifier] = []
    for ability_id in ability_ids:
        handler = HANDLERS.get(ability_id)
        if handler is not None:
            modifiers.extend(handler(context))
    return modifiers


def character_modifiers(context: CharacterContext) -> list[Modifier]:
    """Every `Modifier` produced by composition sources that don't already
    have their own dedicated, repeat-count-aware resolution pipeline: feats,
    traits, and active effects (`context.feat_ids`/`trait_ids`/
    `active_effects`).

    Deliberately excludes `context.granted_ability_ids` (race + class
    granted abilities): a race's ability-score bonuses are already resolved
    into `context.ability_scores` itself before this ever runs
    (`rules/effective_scores.py`), and a class ability's other effects go
    through `rules/speed.py`'s `race_speed`/`class_speed_bonus`, which call
    a handler once *per qualifying grant*, not once per distinct id — a
    class ability shared by two grants on a multiclassed character (e.g.
    Barbar/Entfesselter Barbar's shared "Schnelle Bewegung" id, see
    `sheet.py`'s `_granted_class_ability_ids` docstring) must stack twice.
    This function's `ability_ids` are a plain deduplicated `set`, so routing
    `granted_ability_ids` through it too would silently drop that
    per-grant repetition. Once a granted-ability id needs a non-SCORE/
    non-SPEED effect, its resolution should move to a repeat-count-aware
    caller of `resolve_ids` alongside `class_speed_bonus`, not into this
    flat pass."""
    ids = context.feat_ids | context.trait_ids | {effect.source_id for effect in context.active_effects}
    return resolve_ids(ids, context)


def situational_skill_notes(context: CharacterContext) -> list[SkillNote]:
    """Resolves scopes 1 and 2 of `SITUATIONAL_SKILL_HANDLERS`'s model
    (this module's own docstring) against everything the character actually
    has that could trigger one: granted class abilities (`context.granted_ability_ids`,
    already gated by level/archetype/replacement) and feats/traits
    (`context.feat_ids`/`trait_ids`, presence-only — a feat/trait isn't
    scaled by a repeat count the way a class ability grant can be). Scope 3
    (universal, e.g. `rules/speed.py`'s `jump_skill_note`) isn't resolved
    here — it has no id to look up, `sheet.py`'s `_build_skills` calls it
    directly instead.

    A trigger id with no entry (the overwhelming majority — most granted
    abilities/feats/traits don't grant a situational skill bonus at all)
    simply contributes nothing, same "id with no handler just passes
    through" convention `resolve_ids` already documents."""
    trigger_ids: set[UUID] = set(context.granted_ability_ids) | context.feat_ids | context.trait_ids
    notes: list[SkillNote] = []
    for trigger_id in trigger_ids:
        handler = SITUATIONAL_SKILL_HANDLERS.get(trigger_id)
        if handler is not None:
            notes.extend(handler(context))
    return notes
