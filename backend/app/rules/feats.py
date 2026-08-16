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

from collections.abc import Callable
from uuid import UUID

from .context import CharacterContext
from .modifiers import Modifier, ModifierTarget
from .progression import ability_mod

EINSCHUECHTERNDE_KRAFT = UUID("73238862-9538-590c-b498-0d96e1ae9b43")

# `base_feats.json`'s "Heftiger Angriff" (Power Attack) row id.
HEFTIGER_ANGRIFF = UUID("4696cb39-3218-4f95-9d61-d0cef28b4ac0")

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
}
