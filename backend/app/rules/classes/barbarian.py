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
from ..modifiers import Modifier, ModifierTarget, SkillNote
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
    levels, matching RAW."""
    con_mod = ability_mod(context.ability_scores.get("KO", 10))
    barbar_level = context.level_counts_by_root_id.get(BARBAR_ENTFESSELTER_ROOT_CLASS_ID, 0)
    return con_mod + 2 + 2 * barbar_level


def _kampfrausch_entfesselter_barbar_temp_hp(context: CharacterContext) -> int:
    """"2 temporäre Trefferpunkte pro Trefferwürfel" — Hit Dice, here taken
    as total character level (this app's existing simplification, same one
    `sheet.py`'s `max_hit_points` already uses: no racial HD modeled)."""
    return 2 * sum(context.level_counts_by_root_id.values())


ERSCHOPFT_CONDITION_ID = UUID("cb149263-435d-52f1-93c5-72fb0a01ff85")


def _kampfrausch_entfesselter_barbar_end(context: CharacterContext) -> tuple[UUID, int]:
    """"Der Barbar kann seinen Kampfrausch als Freie Aktion beenden und
    erhält sodann für 1 Minute den Zustand Erschöpft" — a fixed 10-round
    (1-minute) Fatigued condition regardless of how long the rage lasted
    (contrast plain Barbar's own Kampfrausch, whose fatigue instead scales
    with rounds raged — a different id, out of scope here, see roadmap.md)."""
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
