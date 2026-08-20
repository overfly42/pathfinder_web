"""Barbar + Entfesselter Barbar (unchained Barbarian) handlers, plus
Entfesselter Barbar's Seeräuber archetype (`import_barbar_seereauber.py`) —
one file per class, closely related variants sharing a file (CLAUDE.md's
"Working Conventions"): the two root classes are the same rulebook character
concept, and their mechanics either share an id outright ("Schnelle
Bewegung" below) or are independently worded/tuned variants of the same
feature (each has its own Kampfrausch — see roadmap.md — so those get
separate ids, not a shared one); an archetype belongs in its parent's file
by the same "closely related variant" rule.

Feeds `rules/handlers.py`'s unified `HANDLERS`, same merge-only role
`race_abilities.py`/`speed.py` play for their own slices — this file owns
every Barbar/Entfesselter-Barbar ability id and its computation; nothing
outside it should reference these ids directly."""

import functools
from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..effects import ERSCHOPFT_CONDITION_ID
from ..favored_class_bonuses import ENTFESSELTER_BARBAR as ENTFESSELTER_BARBAR_FCB_CHOICE_ID
from ..favored_class_bonuses import HANDLERS as FAVORED_CLASS_BONUS_HANDLERS
from ..modifiers import Modifier, ModifierTarget, NaturalAttack, SkillNote
from ..progression import ability_mod
from ..skill_ids import (
    AKROBATIK_SKILL_ID,
    BERUF_SKILL_ID,
    KLETTERN_SKILL_ID,
    SCHWIMMEN_SKILL_ID,
    UEBERLEBENSKUNST_SKILL_ID,
)
from ..speed import fast_movement

# Entfesselter Barbar's own root `BaseClass` id (it's modeled as an
# independent root class here, not an archetype of Barbar — confirmed
# against `base_classes.json`/`base_class_ability_grants.json`) — needed by
# Kampfrausch's rounds/day formula below, which scales with *this* class's
# levels specifically, not total character level.
BARBAR_ENTFESSELTER_ROOT_CLASS_ID = UUID("332f742d-d2a1-5375-8bff-0924f92d2b9d")

# "Schnelle Bewegung" (+3 m at level 1): one `BaseClassAbility` row/id shared
# by Barbar and Entfesselter Barbar via two separate `BaseClassAbilityGrant`
# rows (same mechanic — identical bonus, identical conditions — so one
# catalog row per CLAUDE.md/`race_abilities.py`'s "same rulebook ability
# shared by every grantor gets exactly one id" rule, not one row per
# importing script). Built from `rules/speed.py`'s generic `fast_movement`
# factory — see that module for the RAW-text reasoning behind its
# always-stacking `type="untyped"` bonus and its class-agnostic shape.
# Applied unconditionally — RAW gates it on wearing no more than medium
# armor and not being under a heavy load, but armor weight category/
# encumbrance aren't modeled yet (`models/item.py` only has `ac_bonus`/
# `max_dex_bonus`), same "honest simplification" `sheet.py`'s
# `_build_equipment` documents for AC/CMB/CMD.
BARBAR_SCHNELLE_BEWEGUNG_ABILITY_ID = UUID("b311443b-a086-52ae-a079-d31880638921")

KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID = UUID("ad985f6f-3b03-5861-bccf-a016ebaba4ec")

# Entfesselter Barbar's "Bestientotem, Schwächeres" Kampfrauschkraft
# (`base_class_ability_grants.json` id 3de886d8-…, option-choice-gated —
# `_granted_class_ability_ids` in `sheet.py` only counts it when actually
# picked). Grants two primary claw attacks, 1W6 slashing each. Not in
# `HANDLERS` below: it produces a `NaturalAttack`, not a `Modifier`, so it
# lives in this module's own `NATURAL_ATTACK_HANDLERS` instead (merged into
# `rules/handlers.py`'s registry of the same name via `rules/classes/
# __init__.py`, same "each family owns its own slice" pattern `HANDLERS`
# already uses).
BESTIENTOTEM_SCHWAECHERES_ABILITY_ID = UUID("694f425e-d5f9-55d7-978e-4f7e50296dec")

# Entfesselter Barbar's "Bestientotem" Kampfrauschkraft (mid tier;
# `base_class_option_choices.json` id 206ceefa-…, `min_level: 6`,
# `requires_choice_id` pointing at Bestientotem, Schwächeres above — so it's
# only ever a character's granted ability once the lesser tier already is).
# PRD text: "Der Barbar erhält einen Bonus von +1 auf seine natürliche
# Rüstung. Dieser Bonus steigt um weitere +1 pro 4 Barbarenstufen." Read as
# "+1 more for every four barbarian levels beyond the level it's first
# available (6th)" — the same "beyond the prerequisite level" convention
# real-book rage powers of this shape use, not a flat `level // 4` that
# would put the first increase at a level unrelated to when the power is
# actually gained. Unlike Bestientotem, Schwächeres's `NaturalAttack`, this
# is a flat AC bonus, so it's a `HANDLERS`/`Modifier` entry below instead.
BESTIENTOTEM_ABILITY_ID = UUID("a26e564e-295b-5c25-be44-4a75ee3ce486")

# Entfesselter Barbar's "Elementare Kampfhaltung" Kampfrauschkraft
# (`base_class_abilities.json` id d80a2280-…, option-choice-gated the same
# way as Bestientotem above). PRD text: the barbarian picks one energy type
# (Elektrizität/Feuer/Kälte/Säure) when taking this stance; melee attacks
# deal +1 point of that type, rising to 1W6 at 8th level; from 12th level,
# critical hits deal an extra 1W10 (2W10/3W10 on a x3/x4-crit weapon) of the
# same type. Two deliberate simplifications, chosen 2026-08-17 to keep this
# a same-depth-as-Bestientotem handler rather than a new cross-cutting
# feature:
# - No player choice of energy type is modeled yet (`BaseClassOptionChoice`
#   has no sub-choice mechanism for class abilities the way `BaseFeat.
#   sub_choice_type`/`CharacterFeat.chosen_*` do for feats) — the type is a
#   fixed placeholder (`_ENERGY_TYPE` below), same "known gap" pattern as
#   e.g. `BARBAR_SCHNELLE_BEWEGUNG_ABILITY_ID`'s unmodeled armor-weight
#   gating. A real chosen-type sub-pick is future work, not started here.
# - The 12th-level crit bonus isn't modeled: nothing in this app computes
#   critical-hit-only damage anywhere (`rules/weapon_abilities.py`'s module
#   docstring — the ~90 weapon special abilities take the same stance, crit
#   effects are left for the player to apply at the table), and this
#   ability's crit bonus additionally needs the wielded weapon's own crit
#   multiplier, which isn't parsed out of `BaseItem.critical`'s raw string
#   anywhere either. Only the flat on-hit part (1 / 1W6) is computed.
ELEMENTARE_KAMPFHALTUNG_ABILITY_ID = UUID("d80a2280-25f5-52e6-add7-7f216989a163")

# Placeholder energy type until a real per-character choice exists (see
# `ELEMENTARE_KAMPFHALTUNG_ABILITY_ID`'s docstring above) — Feuer chosen
# arbitrarily, same as `weapon_abilities.py`'s own hand-picked types for its
# 8 flat on-hit energy abilities.
_ELEMENTARE_KAMPFHALTUNG_ENERGY_TYPE = "Feuer"


def _bestientotem_schwaecheres(context: CharacterContext) -> NaturalAttack | None:
    """Unlike Reißzähne's racial bite (always present once granted), a rage
    power only manifests while actually raging — same `context.active_effects`
    "instances" check `_kampfrausch_entfesselter_barbar` below uses for its
    own flat Modifiers, since both keys off the same Kampfrausch activation
    (`KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID`), not this ability's own
    id (Bestientotem itself has no separate on/off state, only Kampfrausch
    does)."""
    instances = [e for e in context.active_effects if e.source_id == KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID]
    if not instances:
        return None
    return NaturalAttack(name="Klauen", count=2, damage_dice="1W6", damage_type="H")


def _bestientotem(context: CharacterContext) -> list[Modifier]:
    """Same rage-gated shape as `_bestientotem_schwaecheres` above (only
    manifests while `KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID` is active
    — Entfesselter Barbar rage powers work continuously while raging,
    `import_entfesselter_barbar.py`'s module docstring), scaled by this
    class's own levels the same way `_elementare_kampfhaltung_damage`
    below is. `type="natural"`: a second source of natural armor (e.g.
    `feats.py`'s Eisenhaut) caps at the higher of the two rather than
    adding, same convention that module's `_natural_armor_bonus`
    documents."""
    instances = [e for e in context.active_effects if e.source_id == KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID]
    if not instances:
        return []
    barbar_level = context.level_counts_by_root_id.get(BARBAR_ENTFESSELTER_ROOT_CLASS_ID, 0)
    bonus = 1 + max(0, barbar_level - 6) // 4
    return [Modifier(source="Bestientotem", type="natural", value=bonus, target=ModifierTarget.AC)]


def _elementare_kampfhaltung_damage(context: CharacterContext) -> tuple[str, str] | None:
    """Flat on-hit melee damage die Elementare Kampfhaltung adds while
    raging (see `ELEMENTARE_KAMPFHALTUNG_ABILITY_ID`'s docstring for what's
    deliberately not modeled) — same rage-gated shape as
    `_bestientotem_schwaecheres` above (only manifests while
    `KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID` is active), returning
    `None` otherwise. "1 zusätzlicher Schadenspunkt ... Mit der 8. Stufe
    steigt dieser Schaden auf 1W6" — a level-scaled *replacement*, not an
    additive stack, so this returns exactly one die/type pair, scaled by
    this class's own levels (`BARBAR_ENTFESSELTER_ROOT_CLASS_ID`), same
    scoping `_kampfrausch_entfesselter_barbar_rounds_per_day` uses."""
    instances = [e for e in context.active_effects if e.source_id == KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID]
    if not instances:
        return None
    barbar_level = context.level_counts_by_root_id.get(BARBAR_ENTFESSELTER_ROOT_CLASS_ID, 0)
    dice = "1W6" if barbar_level >= 8 else "1"
    return (dice, _ELEMENTARE_KAMPFHALTUNG_ENERGY_TYPE)


def _kampfrausch_entfesselter_barbar(context: CharacterContext) -> list[Modifier]:
    """Entfesselter Barbar's Kampfrausch (`base_class_abilities.json` id
    ad985f6f-3b03-5861-bccf-a016ebaba4ec — Barbar's own, differently worded
    Kampfrausch is a *different* id, not shared, see roadmap.md). PRD text:
    +2 on melee attack/damage, thrown-weapon damage, and Will saves; -2 AC;
    2 temporary HP per Hit Die; a limited number of rounds/day.

    AC/Will/melee-attack/melee-damage are all modeled here as flat
    `Modifier`s. Thrown-weapon damage isn't: `sheet.py`'s `_build_weapon_attacks`
    conflates thrown and true-ranged weapons under one `is_ranged` flag
    (documented existing simplification there), so the ATTACK/DAMAGE
    modifiers below are only ever read for melee weapons — applying them to
    every "ranged" item would incorrectly buff a bow. Temporary HP and the
    rounds/day limit aren't `Modifier`s at all (2026-08-12): temp HP is
    granted directly onto `Character.temporary_hit_points` at activation
    (`TEMP_HP_GRANTS` below, applied by `routers/characters.py`'s
    `activate_effect`), and rounds/day is tracked via `rules/daily_limits.py`
    (`DAILY_LIMITS` below) rather than through the stacking pipeline, since
    neither is a stat bonus a `Modifier`/`stack()` call could represent.

    Doesn't scale with instance count: raging twice at once from the same
    source isn't a state this app can produce (self-scoped toggle), so the
    flat bonus applies once whenever at least one of *this handler's own*
    instances (filtered from `context.active_effects` by this ability's id)
    is active, rather than summing per row the way e.g. ability damage
    would."""
    instances = [e for e in context.active_effects if e.source_id == KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID]
    if not instances:
        return []
    return [
        Modifier(source="Kampfrausch", type="untyped", value=-2, target=ModifierTarget.AC),
        Modifier(source="Kampfrausch", type="morale", value=2, target=ModifierTarget.SAVE_WILL),
        Modifier(source="Kampfrausch", type="morale", value=2, target=ModifierTarget.ATTACK),
        Modifier(source="Kampfrausch", type="morale", value=2, target=ModifierTarget.DAMAGE),
    ]


def _kampfrausch_entfesselter_barbar_rounds_per_day(context: CharacterContext) -> int:
    """PRD text: "eine Anzahl von Runden ... welche der Höhe seines
    KO-Modifikators +4 entspricht. Mit Erreichen jeder weiteren Stufe erhält
    er 2 weitere Runden" — level 1: con_mod+4; +2/level thereafter, i.e.
    `con_mod + 2 + 2*level`. Scoped to *this* class's own levels
    (`BARBAR_ENTFESSELTER_ROOT_CLASS_ID`), not total character level, so a
    multiclassed character's rounds/day only grow with Entfesselter-Barbar
    levels, matching RAW.

    Plus this class's own race-scoped favored-class-bonus alternate ("+1
    Runde Kampfrausch/Tag" per pick, `rules/favored_class_bonuses.py`'s
    `ENTFESSELTER_BARBAR` choice) — picked and displayed
    (`sheet.py`'s `_build_favored_class_bonuses`) since 2026-08-16 but never
    actually added to this total until now (todos.md's "Volksspezifische
    Optionen zur Bevorzugten Klasse" gap)."""
    con_mod = ability_mod(context.ability_scores.get("KO", 10))
    barbar_level = context.level_counts_by_root_id.get(BARBAR_ENTFESSELTER_ROOT_CLASS_ID, 0)
    fcb_picks = context.favored_class_bonus_pick_counts.get(ENTFESSELTER_BARBAR_FCB_CHOICE_ID, 0)
    fcb_bonus = FAVORED_CLASS_BONUS_HANDLERS[ENTFESSELTER_BARBAR_FCB_CHOICE_ID](fcb_picks) if fcb_picks else 0
    return con_mod + 2 + 2 * barbar_level + fcb_bonus


def _kampfrausch_entfesselter_barbar_temp_hp(context: CharacterContext) -> int:
    """"2 temporäre Trefferpunkte pro Trefferwürfel" — Hit Dice, here taken
    as total character level (this app's existing simplification, same one
    `sheet.py`'s `max_hit_points` already uses: no racial HD modeled)."""
    return 2 * sum(context.level_counts_by_root_id.values())


def _kampfrausch_entfesselter_barbar_end(context: CharacterContext) -> tuple[UUID, int]:
    """"Der Barbar kann seinen Kampfrausch als Freie Aktion beenden und
    erhält sodann für 1 Minute den Zustand Erschöpft" — a fixed 10-round
    (1-minute) Fatigued condition regardless of how long the rage lasted
    (contrast plain Barbar's own Kampfrausch, whose fatigue instead scales
    with rounds raged — a different id, out of scope here, see roadmap.md).
    `ERSCHOPFT_CONDITION_ID` itself now lives in `rules/effects.py` (its own
    `-2 ST/GE` handler is there too) — imported here rather than redefined,
    since it's a generic condition, not a Barbar-specific one."""
    del context
    return (ERSCHOPFT_CONDITION_ID, 10)


# Seeräuber (Entfesselter Barbar archetype, `import_barbar_seereauber.py`)'s
# "Wilder Seemann" — id is that script's own deterministic
# `uid("seereauber-ability", "Wilder Seemann")` (against its own
# `ID_NAMESPACE`), reproduced here as a plain literal since the seed script
# isn't importable at runtime (it's a one-off fixture-writer, not a package
# module).
SEERAEUBER_WILDER_SEEMANN_ABILITY_ID = UUID("0f023bbd-cdea-5ea3-9518-c530cb119f1f")

# The five skills Wilder Seemann's bonus applies to — Beruf stands in for
# "Beruf (Seemann)" specifically, since Profession specializations aren't
# modeled as distinct `BaseSkill` rows anywhere in this codebase.
SEERAEUBER_WILDER_SEEMANN_SKILL_IDS = (
    AKROBATIK_SKILL_ID,
    BERUF_SKILL_ID,
    KLETTERN_SKILL_ID,
    SCHWIMMEN_SKILL_ID,
    UEBERLEBENSKUNST_SKILL_ID,
)


def _wilder_seemann_notes(context: CharacterContext) -> list[SkillNote]:
    """"+1 auf ... Akrobatik, Beruf (Seemann), Klettern, Schwimmen und
    Überlebenskunst im Wasser, auf Schiffen und an der Küste [...] steigen
    alle weiteren drei Stufen ... um zusätzliche +1" — granted via 6
    separate `BaseClassAbilityGrant` rows (3rd/6th/9th/12th/15th/18th, same
    repeated-grant shape as core Barbar's Schadensreduzierung), so the
    count of this ability's own currently-met grants
    (`context.granted_ability_ids[SEERAEUBER_WILDER_SEEMANN_ABILITY_ID]`,
    already resolved by `sheet.py`'s `_granted_class_ability_ids`) *is* the
    total +1-per-grant bonus, no separate scaling formula needed.

    Only called at all when this id is actually one of the character's
    granted abilities (`rules/handlers.py`'s `SITUATIONAL_SKILL_HANDLERS`
    resolution loop looks the id up in `context.granted_ability_ids`
    first), so the count read here is always > 0 — no extra presence check
    needed the way `HANDLERS` entries sometimes need one.

    Conditional on where the check is made (water/ships/coast), unlike
    Fallengespür's unconditional AC/Reflex bonus — so this is a
    `SITUATIONAL_SKILL_HANDLERS` entry (produces `SkillNote`s,
    `sheet.py`'s `_build_skills` renders them as an info note, never folded
    into a skill's base value) rather than a `HANDLERS`/`Modifier` one,
    which would incorrectly apply the bonus to every
    Akrobatik/Klettern/Schwimmen/... check regardless of location."""
    count = context.granted_ability_ids[SEERAEUBER_WILDER_SEEMANN_ABILITY_ID]
    return [
        SkillNote(
            skill_id=skill_id,
            title="Wilder Seemann (im Wasser, auf Schiffen, an der Küste)",
            modifier_label="Wilder Seemann",
            value=count,
        )
        for skill_id in SEERAEUBER_WILDER_SEEMANN_SKILL_IDS
    ]


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    BARBAR_SCHNELLE_BEWEGUNG_ABILITY_ID: functools.partial(fast_movement, meters=3),
    KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID: _kampfrausch_entfesselter_barbar,
    BESTIENTOTEM_ABILITY_ID: _bestientotem,
}

# This class's slice of `rules/handlers.py`'s merged `SITUATIONAL_SKILL_HANDLERS`
# — conditional skill bonuses that only apply in some situation the sheet
# can't detect on its own, surfaced as a note rather than folded into a
# skill's base value (see that module's docstring for the full model).
SITUATIONAL_SKILL_HANDLERS: dict[UUID, Callable[[CharacterContext], list[SkillNote]]] = {
    SEERAEUBER_WILDER_SEEMANN_ABILITY_ID: _wilder_seemann_notes,
}

# This class's slice of `rules/handlers.py`'s merged `DAILY_LIMITS` — how
# many rounds/uses per day a daily-limited ability id grants, computed (not
# fixed), same locality convention as `HANDLERS` above.
DAILY_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID: _kampfrausch_entfesselter_barbar_rounds_per_day,
}

# This class's slice of `rules/handlers.py`'s merged `TEMP_HP_GRANTS` — how
# much temporary HP activating an ability id grants
# (`routers/characters.py`'s `activate_effect`).
TEMP_HP_GRANTS: dict[UUID, Callable[[CharacterContext], int]] = {
    KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID: _kampfrausch_entfesselter_barbar_temp_hp,
}

# This class's slice of `rules/handlers.py`'s merged `ON_END` — which
# condition (id, duration in rounds) an ability id's active effect grants
# when it ends (`routers/characters.py`'s `_expire_effect`).
ON_END: dict[UUID, Callable[[CharacterContext], tuple[UUID, int]]] = {
    KAMPFRAUSCH_ENTFESSELTER_BARBAR_ABILITY_ID: _kampfrausch_entfesselter_barbar_end,
}

# This class's slice of `rules/handlers.py`'s merged `NATURAL_ATTACK_HANDLERS`
# — class-granted natural weapon attacks only (see
# `_bestientotem_schwaecheres` above).
NATURAL_ATTACK_HANDLERS: dict[UUID, Callable[[CharacterContext], NaturalAttack | None]] = {
    BESTIENTOTEM_SCHWAECHERES_ABILITY_ID: _bestientotem_schwaecheres,
}

# This class's slice of `rules/handlers.py`'s merged
# `WEAPON_BONUS_DAMAGE_HANDLERS` — an extra (dice, damage-type) pair a
# granted ability id adds to melee weapon damage while active, or `None` if
# it doesn't currently apply (same "return nothing if the condition isn't
# met" shape `NATURAL_ATTACK_HANDLERS` above already uses). Not a
# `Modifier`: it's a damage die, not a flat int `stack()` can fold in.
WEAPON_BONUS_DAMAGE_HANDLERS: dict[UUID, Callable[[CharacterContext], tuple[str, str] | None]] = {
    ELEMENTARE_KAMPFHALTUNG_ABILITY_ID: _elementare_kampfhaltung_damage,
}
