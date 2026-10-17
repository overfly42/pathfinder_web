"""Paladin — roadmap slice 10, step 0b (`scripts/import_paladin.py`).

- "Böses niederstrecken" (`HANDLERS` + `DAILY_LIMITS` +
  `POOL_COST_AT_ACTIVATION`): a self effect activated like Kampfrausch,
  paying one daily use at activation (the smite lasts until the target dies
  or the Paladin rests — no per-round debit). While active: CH bonus on
  every weapon attack (melee and ranged, `ModifierTarget.ANY_ATTACK`),
  Paladin level on weapon damage, CH bonus as a deflection bonus to AC. All
  three are RAW only against the smite target — the sheet can't tell
  targets apart, so they show while the effect is active; the doubled
  damage against evil outsiders/dragons/undead is in the feature summary.
- "Göttliche Würde" (`HANDLERS`): CH bonus (if positive) on all saves.
- "Handauflegen" (`DAILY_LIMITS` + `FEATURE_SUMMARY_HANDLERS`): ½ Paladin
  level + CH mod uses/day, 1W6 per two levels.
- "Positive Energie fokussieren" (`POOL_SOURCE_ID` -> Handauflegen,
  `POOL_COST_AT_ACTIVATION` 2): spends two Handauflegen uses, channels as a
  Kleriker of Paladin level.
- "Aura der Gerechtigkeit" (`POOL_SOURCE_ID` -> Böses niederstrecken, cost
  2): spends two smites to share the smite with allies.
- "Göttlicher Bund: Waffe" (`DAILY_LIMITS` + `WEAPON_ENHANCEMENT_HANDLERS`):
  the weapon spirit — a self effect naming its weapon (`target_item_id`,
  same mechanism as Kampfmagus' Arkaner Vorrat); its +1…+6 bonus is applied
  as a temporary enhancement bonus (capped against the weapon's own at +5
  by `sheet.py`). Spending the bonus on special abilities stays text.
- "Reittier herbeirufen" (`DAILY_LIMITS`): call the mount, 1/day at 5, +1
  every four levels. "Göttlicher Bund: Reittier" itself is the trigger
  ability for slice 10's companion level sources — no handler here.

Everything else (auras, immunities, DR /Böses, Böses entdecken, the
mercies' effects) is descriptive."""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..modifiers import Modifier, ModifierTarget
from ..progression import ability_mod

PALADIN_ROOT_CLASS_ID = UUID("561465fe-7c72-4e47-b58e-05a8dbbf0a3e")

BOESES_NIEDERSTRECKEN_ABILITY_ID = UUID("e6a08f37-293c-5f74-a0d8-dd46898f9507")
GOETTLICHE_WUERDE_ABILITY_ID = UUID("aa08188c-8881-56cc-bfc2-99ec103c49c9")
HANDAUFLEGEN_ABILITY_ID = UUID("d76a1967-add5-5759-9545-846f8c099ebb")
POSITIVE_ENERGIE_FOKUSSIEREN_ABILITY_ID = UUID("281d97af-1d40-58b2-a628-6099669060f0")
AURA_DER_GERECHTIGKEIT_ABILITY_ID = UUID("10b1299f-b5ae-5818-9e09-a23bf556ac11")
GOETTLICHER_BUND_WAFFE_ABILITY_ID = UUID("61ef7479-f6f8-5e0a-86da-eeddd4949d44")
GOETTLICHER_BUND_REITTIER_ABILITY_ID = UUID("0028e0bb-6d8f-5051-bdb8-3f960dcf1009")
REITTIER_HERBEIRUFEN_ABILITY_ID = UUID("4d1f8309-3afd-5df9-a341-3af26025fee9")


def _paladin_level(context: CharacterContext) -> int:
    return context.level_counts_by_root_id.get(PALADIN_ROOT_CLASS_ID, 0)


def _charisma_bonus(context: CharacterContext) -> int:
    """"seinen CH-Bonus (wenn er einen hat)" — a negative modifier is no
    bonus, so it never turns into a penalty."""
    return max(0, ability_mod(context.ability_scores.get("CH", 10)))


def _signed(value: int) -> str:
    return f"+{value}" if value >= 0 else f"−{abs(value)}"


def smite_uses_per_day(context: CharacterContext) -> int:
    """1/Tag at 1st, +1 at 4th and every three levels after, max 7 at 19th."""
    level = _paladin_level(context)
    if level < 1:
        return 0
    return min(7, 1 + (level - 1) // 3)


def lay_on_hands_uses_per_day(context: CharacterContext) -> int:
    """½ Paladin level + CH modifier (from 2nd level), never below 0."""
    level = _paladin_level(context)
    if level < 2:
        return 0
    return max(0, level // 2 + ability_mod(context.ability_scores.get("CH", 10)))


def divine_bond_uses_per_day(context: CharacterContext) -> int:
    """1/Tag at 5th, +1 every four levels after, max 4 at 17th — the same
    count for the weapon spirit and for calling the mount."""
    level = _paladin_level(context)
    if level < 5:
        return 0
    return min(4, 1 + (level - 5) // 4)


def divine_bond_weapon_bonus(context: CharacterContext) -> int:
    """+1 at 5th, +1 every three levels after, max +6 at 20th."""
    level = _paladin_level(context)
    if level < 5:
        return 0
    return min(6, 1 + (level - 5) // 3)


def _boeses_niederstrecken(context: CharacterContext) -> list[Modifier]:
    """Self-gated on its own active effect, same shape as Kampfrausch
    (`rules/classes/barbarian.py`): this id is also a granted ability, so
    `granted_ability_modifiers` calls it while *not* smiting too."""
    if not context.has_active(BOESES_NIEDERSTRECKEN_ABILITY_ID):
        return []
    source = "Böses niederstrecken"
    charisma = _charisma_bonus(context)
    modifiers = [
        Modifier(source=source, type="untyped", value=_paladin_level(context), target=ModifierTarget.ANY_DAMAGE)
    ]
    if charisma:
        modifiers += [
            Modifier(source=source, type="untyped", value=charisma, target=ModifierTarget.ANY_ATTACK),
            Modifier(source=source, type="deflection", value=charisma, target=ModifierTarget.AC),
        ]
    return modifiers


def _goettliche_wuerde(context: CharacterContext) -> list[Modifier]:
    charisma = _charisma_bonus(context)
    if not charisma:
        return []
    return [
        Modifier(source="Göttliche Würde", type="untyped", value=charisma, target=target)
        for target in (ModifierTarget.SAVE_FORT, ModifierTarget.SAVE_REF, ModifierTarget.SAVE_WILL)
    ]


def _divine_bond_weapon_enhancement(context: CharacterContext) -> tuple[UUID, int] | None:
    """Same shape as Kampfmagus' `_arkaner_vorrat_weapon_enhancement`: the
    nominal bonus on whichever weapon the active effect names, `None` while
    not active or with no weapon chosen."""
    effect = next(
        (
            e
            for e in context.active_effects
            if e.source_id == GOETTLICHER_BUND_WAFFE_ABILITY_ID and e.target_item_id is not None
        ),
        None,
    )
    if effect is None:
        return None
    return (effect.target_item_id, divine_bond_weapon_bonus(context))


def _smite_summary(context: CharacterContext) -> str:
    level = _paladin_level(context)
    return (
        f"{smite_uses_per_day(context)}/Tag; gegen das Ziel {_signed(_charisma_bonus(context))} Angriff, "
        f"+{level} Schaden (Externare böse/böse Drachen/Untote: +{2 * level} beim ersten Treffer), "
        f"{_signed(_charisma_bonus(context))} Ablenkung auf RK"
    )


def _lay_on_hands_summary(context: CharacterContext) -> str:
    dice = max(1, _paladin_level(context) // 2)
    return f"{lay_on_hands_uses_per_day(context)}/Tag, heilt {dice}W6 (Untoten: {dice}W6 Schaden)"


def _channel_summary(context: CharacterContext) -> str:
    level = _paladin_level(context)
    dice = (level + 1) // 2
    dc = 10 + level // 2 + ability_mod(context.ability_scores.get("CH", 10))
    return f"{dice}W6, SG {dc}; kostet 2 Anwendungen Handauflegen"


def _divine_bond_weapon_summary(context: CharacterContext) -> str:
    level = _paladin_level(context)
    return (
        f"{divine_bond_uses_per_day(context)}/Tag, +{divine_bond_weapon_bonus(context)} für {level} Min. "
        "(als Verbesserungsbonus bis max. +5 gesamt)"
    )


def _divine_bond_mount_summary(context: CharacterContext) -> str:
    level = _paladin_level(context)
    extras = ["effektive Druidenstufe " + str(level), "IN mind. 6"]
    if level >= 11:
        extras.append("Celestische Schablone")
    if level >= 15:
        extras.append(f"ZR {level + 11}")
    return ", ".join(extras)


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    BOESES_NIEDERSTRECKEN_ABILITY_ID: _boeses_niederstrecken,
    GOETTLICHE_WUERDE_ABILITY_ID: _goettliche_wuerde,
}
DAILY_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    BOESES_NIEDERSTRECKEN_ABILITY_ID: smite_uses_per_day,
    AURA_DER_GERECHTIGKEIT_ABILITY_ID: smite_uses_per_day,
    HANDAUFLEGEN_ABILITY_ID: lay_on_hands_uses_per_day,
    POSITIVE_ENERGIE_FOKUSSIEREN_ABILITY_ID: lay_on_hands_uses_per_day,
    GOETTLICHER_BUND_WAFFE_ABILITY_ID: divine_bond_uses_per_day,
    REITTIER_HERBEIRUFEN_ABILITY_ID: divine_bond_uses_per_day,
}
DAILY_LIMIT_UNIT_LABEL: dict[UUID, str] = {
    BOESES_NIEDERSTRECKEN_ABILITY_ID: "Anwendungen",
    GOETTLICHER_BUND_WAFFE_ABILITY_ID: "Anwendungen",
}
# Both persistent self effects pay one use when activated (no per-round
# debit); the two instant ones spend two uses of the pool they share.
POOL_COST_AT_ACTIVATION: dict[UUID, int] = {
    BOESES_NIEDERSTRECKEN_ABILITY_ID: 1,
    GOETTLICHER_BUND_WAFFE_ABILITY_ID: 1,
    POSITIVE_ENERGIE_FOKUSSIEREN_ABILITY_ID: 2,
    AURA_DER_GERECHTIGKEIT_ABILITY_ID: 2,
}
POOL_SOURCE_ID: dict[UUID, UUID] = {
    POSITIVE_ENERGIE_FOKUSSIEREN_ABILITY_ID: HANDAUFLEGEN_ABILITY_ID,
    AURA_DER_GERECHTIGKEIT_ABILITY_ID: BOESES_NIEDERSTRECKEN_ABILITY_ID,
}
WEAPON_ENHANCEMENT_HANDLERS: dict[UUID, Callable[[CharacterContext], tuple[UUID, int] | None]] = {
    GOETTLICHER_BUND_WAFFE_ABILITY_ID: _divine_bond_weapon_enhancement,
}
FEATURE_SUMMARY_HANDLERS: dict[UUID, Callable[[CharacterContext], str]] = {
    BOESES_NIEDERSTRECKEN_ABILITY_ID: _smite_summary,
    HANDAUFLEGEN_ABILITY_ID: _lay_on_hands_summary,
    POSITIVE_ENERGIE_FOKUSSIEREN_ABILITY_ID: _channel_summary,
    GOETTLICHER_BUND_WAFFE_ABILITY_ID: _divine_bond_weapon_summary,
    GOETTLICHER_BUND_REITTIER_ABILITY_ID: _divine_bond_mount_summary,
}
