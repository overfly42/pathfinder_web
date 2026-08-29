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

from .context import CharacterContext
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


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    EINSCHUECHTERNDE_KRAFT: _einschuechternde_kraft,
    EISENHAUT: functools.partial(_natural_armor_bonus, source="Eisenhaut", value=1),
    AUSWEICHEN: _ausweichen,
}

# Feats whose mechanical effect is genuinely computed on the sheet, just not
# through this module's own `HANDLERS` above — each one's own docstring
# (`WAFFENFINESSE`, `WAFFENFOKUS`, `power_attack_bonus`) explains why it's a
# per-weapon-slot decision `sheet.py`'s `_build_weapon_attacks` makes
# directly instead of a flat `Modifier`. `sheet.py`'s feat-list "Nur Text"
# badge (`hasHandler`) checks this set too, so a feat that's actually applied
# elsewhere doesn't get mislabeled as flavor-only merely for not being a
# `HANDLERS` entry.
COMPUTED_OUTSIDE_HANDLERS_FEAT_IDS = frozenset({WAFFENFINESSE, WAFFENFOKUS, HEFTIGER_ANGRIFF, DERWISCHTANZ})
