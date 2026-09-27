"""Handler registry for feat effects — the family CLAUDE.md's "implementing
`HANDLERS` one feat at a time" refers to. First entry (2026-08-16); kept as
one file rather than pre-split (CLAUDE.md: "don't split preemptively before a
family shows that growth shape" — race abilities/class abilities only split
the way they do because they'd already outgrown a single file).

Same id-linkage convention as `race_abilities.py`: the UUID below is the
literal, hand-frozen id matching the row in
`backend/app/fixtures/seed/base_feats.json` — never derived, never looked up
by name/description text.
"""

import functools
from collections.abc import Callable
from uuid import UUID

from .classes.moench import DRACHENMACHT_ABILITY_ID
from .context import CharacterContext
from .effects import DEFENSIV_KAEMPFEN_CONDITION_ID, VOLLE_VERTEIDIGUNG_CONDITION_ID
from .modifiers import Modifier, ModifierTarget
from .progression import ability_mod

EINSCHUECHTERNDE_KRAFT = UUID("73238862-9538-590c-b498-0d96e1ae9b43")

# `base_feats.json`'s "Eisenhaut" row id (Halb-Ork/Ork/Zwerg racial feat,
# "Natürlicher Rüstungsbonus von +1 auf RK").
EISENHAUT = UUID("bddd2053-a03a-5206-83e7-2e6966686c4c")

# `base_feats.json`'s "Heftiger Angriff" (Power Attack) row id.
HEFTIGER_ANGRIFF = UUID("4696cb39-3218-4f95-9d61-d0cef28b4ac0")

# `base_feats.json`'s "Ausweichen" (Dodge) row id (GRW S. 119). Description
# corrected 2026-08-20 from a stale D&D-3.5-style "single chosen opponent"
# text to the real PF1e GRW wording ("Ausweichbonus +1 auf RK" — a universal
# dodge bonus, not opponent-specific), confirmed against the full permalink
# text at prd.5footstep.de/Permalink?page_id=1285 (`scripts/README.md`'s §2
# workflow): "Du erhältst einen Ausweichbonus von +1 auf deine RK. Eine
# Bedingung, die dich deinen GE-Bonus auf die RK verlieren lässt, lässt dich
# auch den Bonus dieses Talents verlieren."
AUSWEICHEN = UUID("2249f151-0809-4c55-80cc-76920111782e")

# `base_feats.json`'s "Waffenfinesse" (Weapon Finesse) row id. Not a
# `HANDLERS` entry: it doesn't add a modifier, it swaps which ability score
# (`Dex` instead of `Str`) an attack roll uses, and only for weapons the
# catalog marks `BaseItem.is_light` (light weapons plus PF1e's named
# exceptions — Rapier, Peitsche, Stachelkette, Elfisches Krummschwert — see
# that field's docstring) — a per-weapon-slot decision `sheet.py`'s
# `_build_weapon_attacks` has to make itself when it already knows which
# weapon is equipped, same reasoning as `power_attack_bonus` below. Passive
# (no `CharacterEffect` needed), unlike Heftiger Angriff: GRW gives it no
# activation clause, just possession of the feat.
#
# "Speziell: Natürliche Waffen gelten immer als leichte Waffen" (GRW S.
# 135) — a natural weapon (claws, bite, ...) is unconditionally light for
# this feat's purposes, no `BaseItem.is_light` to check at all (natural
# attacks aren't `BaseItem` rows in the first place). `sheet.py`'s
# `_build_natural_attacks` applies the swap unconditionally whenever the
# character has this feat, rather than gating it on anything per-attack.
WAFFENFINESSE = UUID("6f0fd239-157e-567a-b1d8-f5c4c529eeec")

# `base_feats.json`'s "Waffenfokus" (Weapon Focus) row id (GRW S. 131: "+1
# auf Angriffswürfe mit der gewählten Waffe"). Not a `HANDLERS` entry, same
# reasoning as `WAFFENFINESSE` above: the bonus only applies to the one
# weapon chosen at pick time (`CharacterFeat.chosen_weapon_id`), a per-
# weapon-slot decision `sheet.py`'s `_build_weapon_attacks` makes itself
# once it already knows which weapon is equipped. Also the weapon a Kensai's
# own "Waffenfokus (Kensai)" class ability grants this same bonus for, for
# free (`rules/classes/kampfmagus.py`'s `KENSAI_WEAPON_FOCUS_ABILITY_ID`) —
# `_build_weapon_attacks` folds both sources into one check rather than
# treating Kensai's grant as a parallel one-off.
WAFFENFOKUS = UUID("bd72fbe8-e7ae-4eb0-b74c-fbc295f306c8")
WAFFENFOKUS_ATTACK_BONUS = 1

# `base_feats.json`'s "Derwischtanz" row id (Weltenband der Inneren See S.
# 285, Dervish Dance). Not a `HANDLERS` entry, same reasoning as
# `WAFFENFINESSE` above: swaps Str for Dex on both the attack *and* damage
# roll (unlike Waffenfinesse, attack only), but only for one named weapon
# held one-handed with nothing in the other hand — a per-weapon-slot
# decision `sheet.py`'s `_build_weapon_attacks` makes itself, same as
# Waffenfinesse/Waffenfokus.
#
# The PRD's own German translation mislabels this feat's weapon
# "Krummschwert" (elven curve blade, two-handed — `base_items.json` seeds it
# `hands: "two"`) throughout its prerequisite and benefit text. The real
# feat (Dervish Dance) applies to the one-handed scimitar, "Krummsäbel" —
# corrected in `base_feats.json`'s `prerequisite_text`/`description` and
# used here via `DERWISCHTANZ_WEAPON_ID`.
DERWISCHTANZ = UUID("e3ed7db7-928f-5bf8-b983-f39508f1823d")
# `base_items.json`'s "Krummsäbel" row id.
DERWISCHTANZ_WEAPON_ID = UUID("25994f9d-92fe-5dc6-bfff-5e4646899bb5")

# `BaseSkill.id` for Einschüchtern (`base_skills.json`) — the one skill this
# feat's bonus targets.
_EINSCHUECHTERN_SKILL_ID = "3c60b6e1-8c58-4ed0-9c3a-5e003b9da1cf"


def _einschuechternde_kraft(context: CharacterContext) -> list[Modifier]:
    """GRW S. 121: "Addiere deinen ST-Modifikator zusätzlich zu deinem
    CH-Modifikator auf deine Würfe für Einschüchtern." Unlike Einschüchtern's
    own CH modifier (folded into `ability_mods` before any handler runs,
    `sheet.py`'s `_build_skills`), this ST-based addition has no named bonus
    type in the rulebook, so it's untyped (stacks with everything, same
    convention `rules/classes/barbarian.py`'s Schnelle Bewegung uses for its
    own untyped bonus)."""
    st_mod = ability_mod(context.ability_scores.get("ST", 10))
    return [
        Modifier(
            source="Einschüchternde Kraft",
            type="untyped",
            value=st_mod,
            target=ModifierTarget.SKILL,
            target_id=_EINSCHUECHTERN_SKILL_ID,
        )
    ]


def _natural_armor_bonus(context: CharacterContext, *, source: str, value: int) -> list[Modifier]:
    # Unconditional (a flat racial feat bonus never depends on anything
    # about the character it's granted to), same reasoning as
    # `race_abilities.py`'s `_attribute_bonus`. `type="natural"` is its own
    # stacking bucket (`rules/modifiers.py`'s `stack()`): a second source of
    # natural armor (another feat, a racial trait) would cap at the higher
    # of the two rather than adding, while a spell granting an *enhancement*
    # bonus to natural armor (`type="enhancement"`, once one exists) stacks
    # on top of this normally, since it's a different type.
    del context
    return [Modifier(source=source, type="natural", value=value, target=ModifierTarget.AC)]


def _ausweichen(context: CharacterContext) -> list[Modifier]:
    """GRW S. 119: "Du erhältst einen Ausweichbonus von +1 auf deine RK."
    `type="dodge"` (`rules/modifiers.py`'s `ALWAYS_STACKS`) — a dodge bonus
    always stacks with everything, including another dodge bonus, unlike
    `_natural_armor_bonus`'s `type="natural"` above. The clause tying this
    bonus to the same conditions that suppress a Dex bonus to AC (flat-
    footed, immobilized, ...) isn't modeled: this app has no flat-footed/
    immobilized state anywhere (`sheet.py`'s AC computation applies
    `capped_dex_mod` unconditionally), same "known gap" pattern
    `BARBAR_SCHNELLE_BEWEGUNG_ABILITY_ID`'s unmodeled armor-weight gating
    documents — so the bonus applies unconditionally here too."""
    del context
    return [Modifier(source="Ausweichen", type="dodge", value=1, target=ModifierTarget.AC)]


# `base_feats.json`'s "Kranichstil" (Crane Style) row id (ABR II S. 103).
# Voraussetzungen: Ausweichen, Verbesserter waffenloser Schlag, GAB +2 oder
# Mönch 1. Vorteil (quoted in full, 2026-09-23 conversation): "Du erleidest
# nur einen Malus von -2 auf Angriffswürfe, wenn du defensiv kämpfst. Wenn
# du diesen Kampfstil nutzt und defensiv kämpfst oder die Aktion Volle
# Verteidigung nutzt, erhältst du einen zusätzlichen Ausweichbonus von +1
# auf deine Rüstungsklasse."
#
# Modeled as passive (like `AUSWEICHEN`/`_ausweichen` above), not gated
# behind its own activatable `CharacterEffect` toggle like Heftiger Angriff:
# unlike Kampfrausch/Heftiger Angriff, the feat text never mentions an
# activation cost, a swift action, or its own duration — "wenn du diesen
# Kampfstil nutzt" reads as flavor for "while fighting under this
# discipline," not a second tracked resource. Simplifying assumption, easy
# to revisit if a later feat in this same family (Kranichschwinge,
# Kranichriposte) turns out to need Kranichstil's stance tracked as its own
# state independent of simply knowing the feat.
KRANICHSTIL = UUID("0d7d316e-c8ca-5934-acc8-c2437f00c781")


def _kranichstil(context: CharacterContext) -> list[Modifier]:
    """Reads `DEFENSIV_KAEMPFEN_CONDITION_ID`/`VOLLE_VERTEIDIGUNG_CONDITION_ID`
    (`rules/effects.py`) off `context.active_effects` — same "own-state
    toggle, but reacting to a *different* id's activation" shape as nothing
    else in this file yet, since Kranichstil's own benefit depends on which
    combat action the character is currently using, not on anything this
    feat itself activates. The +1 dodge applies for either action (RAW
    grants it once, not summed if both were somehow active at once — not
    RAW-legal simultaneously anyway, no action-economy engine enforces
    that, same gap `todos.md` already tracks); the -4→-2 attack-malus offset
    only applies while fighting defensively specifically (Volle Verteidigung
    makes no attacks at all, nothing to offset)."""
    fighting_defensively = any(e.source_id == DEFENSIV_KAEMPFEN_CONDITION_ID for e in context.active_effects)
    total_defense = any(e.source_id == VOLLE_VERTEIDIGUNG_CONDITION_ID for e in context.active_effects)
    if not fighting_defensively and not total_defense:
        return []
    modifiers = [Modifier(source="Kranichstil", type="dodge", value=1, target=ModifierTarget.AC)]
    if fighting_defensively:
        # Offsets, not replaces, the -4 `Modifier` `_defensiv_kaempfen`
        # (`rules/effects.py`) already contributes — both are `untyped`
        # (`ALWAYS_STACKS`, `rules/modifiers.py`), so -4 + 2 = -2 falls out
        # of plain additive stacking with no special-cased override.
        modifiers.append(Modifier(source="Kranichstil", type="untyped", value=2, target=ModifierTarget.ATTACK))
    return modifiers


def power_attack_bonus(bab: int) -> tuple[int, int]:
    """GRW S. 124: "Du kannst wählen, einen Malus von –1 auf alle
    Nahkampf-Angriffswürfe und Kampfmanöver-Würfe zu erhalten. Dafür
    gewinnst du einen Bonus von +2 auf alle Nahkampf-Schadenswürfe. [...]
    Wenn dein Grund-Angriffsbonus +4 erreicht und für jede +4 danach erhöht
    sich der Malus um weitere –1 und der Schadensbonus um weitere +2." —
    returns `(attack_penalty, damage_bonus)` for a one-handed main-hand
    weapon/attack; the grip-based 150%/50% scaling for a two-handed weapon
    or an off-hand/secondary attack (same rule `sheet.py`'s
    `_weapon_damage_str_mod` already applies to Str-to-damage) is the
    caller's job, since it depends on which weapon/attack this is being
    added to, not on the feat itself.

    Not a `HANDLERS` entry: unlike every other entry in this file, Power
    Attack's damage bonus varies per weapon (grip), which a single flat
    `ModifierTarget.DAMAGE` value can't represent (contrast Kampfrausch's
    flat +2, `rules/classes/barbarian.py`, which really does apply the same
    way to every melee attack at once). `sheet.py`'s `_build_weapon_attacks`/
    `_build_natural_attacks` call this directly (via `_power_attack_effect`)
    and fold the per-weapon-scaled result into their own attack-bonus/
    damage-dice numbers instead.

    Gated on activation, not mere possession (2026-08-16): `BaseFeat.
    is_persistent_effect`/`default_duration_rounds` (mirroring `BaseSpell`/
    `BaseClassAbility`) let a player activate Heftiger Angriff as a tracked
    `CharacterEffect` via `POST .../effects` with `source_type: "feat"`,
    default-prefilled to 1 round (GRW: "Seine Wirkung dauert bis zu deinem
    nächsten Zug an") but overridable, same as every other activatable
    entry — `_power_attack_effect` only applies this bonus while such an
    effect is active, the same `context.active_effects` check
    `_kampfrausch_entfesselter_barbar` uses for its own id."""
    tier = 1 + bab // 4
    return -tier, 2 * tier


# `base_feats.json`'s "Kosmopolit" row id (Expertenregeln S. 163). No
# `HANDLERS` entry: its class-skill grant isn't a `Modifier` — same
# non-value "membership in a set" shape as `traits.py`'s
# `CLASS_SKILL_GRANTS` — just resolved from the player's own two picks
# (`CharacterFeat.chosen_skill_id`/`chosen_skill_id_2`) instead of a fixed
# skill set, see `DYNAMIC_CLASS_SKILL_GRANT_FEAT_IDS` below and
# `rules/handlers.py`'s `granted_class_skill_ids`. Its other clause (2 bonus
# languages) is unmodeled: this app has no character-language tracking at
# all yet (see todos.md).
KOSMOPOLIT = UUID("8df9604c-0a73-505e-94c5-b753e3362911")

# `base_feats.json`'s "Inbegriff des Katzenvolkes" row id (Katzenvolk racial
# feat, repeatable, one of three manifestations chosen per pick,
# `sub_choice_type == "manifestation"`). No `HANDLERS` entry: its "Scharfe
# Krallen" manifestation upgrades an existing natural attack's damage die
# rather than contributing a `Modifier`, so it's resolved in
# `race_abilities.py`'s `_katzenkrallen` (via `context.feat_manifestation_choices`)
# the same "per-attack decision made where the attack itself is built" way
# `WAFFENFINESSE`/`WAFFENFOKUS` are. "Schneller Spurter" (Volksbonus +3 m,
# doubled with Spurter) and "Verbesserte Sinne" (Dämmersicht<->Geruchssinn
# cross-grant) aren't modeled yet — no movement-bonus-by-action-type or
# senses concept exists in `rules/` today; see `todos.md`.
INBEGRIFF_DES_KATZENVOLKES = UUID("459485d5-ae02-551b-8077-b1d0964cbf71")
SCHARFE_KRALLEN_MANIFESTATION = "Scharfe Krallen"

# `base_feats.json`'s "Betäubender Schlag" (Stunning Fist) row id (GRW S.
# 120). Full permalink text (prd.5footstep.de/Permalink?page_id=1292):
# "Vorteil: Du musst die Anwendung dieses Talents ankündigen, bevor du
# deinen Angriffswurf ausführst [...]. Betäubender Schlag verursacht
# normalen Schaden und zwingt zusätzlich deinen Gegner dazu, einen
# Zähigkeitswurf zu machen (SG 10 + ½ Erfahrungsstufe deines Charakters +
# dein WE-Modifikator). Ein Verteidiger, dessen Zähigkeitswurf misslingt,
# ist eine Runde lang betäubt [...]. Für je vier Erfahrungsstufen, die dein
# Charakter erreicht hat, kannst du einen solchen betäubenden Angriff
# einmal pro Tag versuchen. [...] Speziell: Mönche können das Talent
# Betäubender Schlag auf der 1. Stufe als Bonustalent auswählen, auch wenn
# sie die Voraussetzungen dazu nicht erfüllen. Ein Mönch, der dieses Talent
# wählt, kann jeden Tag so viele betäubende Angriffe versuchen, wie er
# Klassenstufen als Mönch hat plus einmal je vier Stufen, die er in anderen
# Klassen als Mönch besitzt."
#
# The actual "target is stunned" effect lands on an opponent, which this
# app has no model for at all (no NPC/monster state) — same "character-
# facing stats only" scope limit spells' damage rolls already have. Only
# the two character-facing numbers (uses/day, save DC) below are computed.
#
# `DAILY_LIMITS`/`SAVE_DC_HANDLERS` below cover the *generic* case — a
# character with an actual `CharacterFeat` row for this feat (e.g. a
# Fighter bonus feat). A monk's own grant (`base_class_abilities.json`'s
# "Betäubender Schlag" wrapper ability, auto-granted at level 1 with
# prerequisites waived, `base_class_ability_granted_feats.json`) never
# creates a `CharacterFeat` row — same "just has it, no pick, no feat-count
# cost" shape `BaseClassAbilityGrantedFeat`'s own docstring documents for a
# class-granted proficiency — so it needs its own entry keyed by that
# wrapper ability's id instead, with the monk-specific uses/day formula
# ("Speziell" above): `rules/classes/moench.py`'s own `DAILY_LIMITS`/
# `SAVE_DC_HANDLERS` slice.
BETAEUBENDER_SCHLAG = UUID("e7ac15b5-29a3-53f1-bbbf-37a594667c1b")


def _betaeubender_schlag_dc(context: CharacterContext) -> int:
    """"SG 10 + ½ Erfahrungsstufe deines Charakters + dein WE-Modifikator."
    CH instead of WE for a Beschuppte Faust (`rules/classes/moench.py`'s
    `DRACHENMACHT_ABILITY_ID`, "Alle Klassenmerkmale des Mönchs, die
    Berechnungen anhand seines Weisheitswertes vornehmen (... wie
    Betäubender Schlag) ... verwenden stattdessen seinen Charismawert.") —
    checked here too (not just in `moench.py`'s own copy of this formula)
    since a Beschuppte-Faust character could in principle also hold an
    actual `CharacterFeat` pick of this same feat from a non-monk source."""
    ability = "CH" if DRACHENMACHT_ABILITY_ID in context.granted_ability_ids else "WE"
    return 10 + context.character_level // 2 + ability_mod(context.ability_scores.get(ability, 10))


def _betaeubender_schlag_uses_per_day(context: CharacterContext) -> int:
    """"Für je vier Erfahrungsstufen, die dein Charakter erreicht hat,
    kannst du einen solchen betäubenden Angriff einmal pro Tag versuchen."
    — floor(character level / 4), the generic (non-monk) formula. A monk's
    own better formula lives in `moench.py` instead (see `BETAEUBENDER_SCHLAG`'s
    own docstring above)."""
    return context.character_level // 4


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    EINSCHUECHTERNDE_KRAFT: _einschuechternde_kraft,
    EISENHAUT: functools.partial(_natural_armor_bonus, source="Eisenhaut", value=1),
    AUSWEICHEN: _ausweichen,
    KRANICHSTIL: _kranichstil,
}

# Feat ids whose class-skill grant is the player's own choice
# (`CharacterFeat.chosen_skill_id`/`chosen_skill_id_2`, `sub_choice_type ==
# "skill_pair"`) rather than a fixed set like `traits.py`'s
# `CLASS_SKILL_GRANTS` — resolved via `context.feat_skill_pair_choices`
# instead of a static frozenset here, since the granted skill ids differ per
# character. Currently just Kosmopolit.
DYNAMIC_CLASS_SKILL_GRANT_FEAT_IDS: frozenset[UUID] = frozenset({KOSMOPOLIT})

# This module's own slice of `rules/handlers.py`'s merged `DAILY_LIMITS`/
# `SAVE_DC_HANDLERS` — see `BETAEUBENDER_SCHLAG`'s own docstring above.
# Only the generic case contributes here; the monk case is
# `rules/classes/moench.py`'s own slice, merged in separately.
DAILY_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    BETAEUBENDER_SCHLAG: _betaeubender_schlag_uses_per_day,
}
SAVE_DC_HANDLERS: dict[UUID, Callable[[CharacterContext], int]] = {
    BETAEUBENDER_SCHLAG: _betaeubender_schlag_dc,
}

# Feats whose mechanical effect is genuinely computed on the sheet, just not
# through this module's own `HANDLERS` above — each one's own docstring
# (`WAFFENFINESSE`, `WAFFENFOKUS`, `power_attack_bonus`) explains why it's a
# per-weapon-slot decision `sheet.py`'s `_build_weapon_attacks` makes
# directly instead of a flat `Modifier`. `sheet.py`'s feat-list "Nur Text"
# badge (`hasHandler`) checks this set too, so a feat that's actually applied
# elsewhere doesn't get mislabeled as flavor-only merely for not being a
# `HANDLERS` entry.
COMPUTED_OUTSIDE_HANDLERS_FEAT_IDS = frozenset(
    {WAFFENFINESSE, WAFFENFOKUS, HEFTIGER_ANGRIFF, DERWISCHTANZ, INBEGRIFF_DES_KATZENVOLKES}
)
