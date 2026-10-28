"""Magier (Wizard) arcane school powers (`scripts/import_magier_schulen.py`).

- Elementarmagieschule der Luft/des Wassers: Luft-/Wasserüberlegenheit's
  enhancement bonus on Fliegen/Schwimmen, +2 and +1 per 5 Magier levels
  (`HANDLERS`); the rest of each power (Federfall at will, a swim speed,
  ...) stays text (partial note)."""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..modifiers import Modifier, ModifierTarget
from ..skill_ids import FLIEGEN_SKILL_ID, SCHWIMMEN_SKILL_ID

MAGIER_ROOT_CLASS_ID = UUID("3533626c-bcc9-41c6-a16b-0313bd5ddb9c")

LUFTUEBERLEGENHEIT_ID = UUID("cfd6a618-493b-5881-b0e3-e0fff81cb671")
WASSERUEBERLEGENHEIT_ID = UUID("2be6366a-6cbd-59c6-82da-f13eae7b442e")


def magier_level(context: CharacterContext) -> int:
    return context.level_counts_by_root_id.get(MAGIER_ROOT_CLASS_ID, 0)


def _elemental_skill_bonus(source: str, skill_id: UUID) -> Callable[[CharacterContext], list[Modifier]]:
    """"+2 ... Dieser Bonus steigt für jeweils 5 Stufen als Magier um weitere +1"."""
    return lambda context: [
        Modifier(source=source, type="enhancement", value=2 + magier_level(context) // 5,
                 target=ModifierTarget.SKILL, target_id=str(skill_id))
    ]


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    LUFTUEBERLEGENHEIT_ID: _elemental_skill_bonus("Luftüberlegenheit", FLIEGEN_SKILL_ID),
    WASSERUEBERLEGENHEIT_ID: _elemental_skill_bonus("Wasserüberlegenheit", SCHWIMMEN_SKILL_ID),
}
PARTIAL_EFFECT_NOTES: dict[UUID, str] = {
    LUFTUEBERLEGENHEIT_ID: (
        "Federfall/Schweben/Fliegen nach Belieben und natürliche 20 ab der 20. Stufe nicht berechnet"
    ),
    WASSERUEBERLEGENHEIT_ID: (
        "Atem anhalten, Schwimmbewegungsrate ab der 10. Stufe und natürliche 20 ab der 20. Stufe nicht berechnet"
    ),
}
