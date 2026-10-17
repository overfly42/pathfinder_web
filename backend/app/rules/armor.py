"""Armor's effects beyond its AC bonus (PRD Grundregelwerk, Ausrüstung,
"Rüstungen"; todos.md 2026-08-20/2026-10-17):

- **Rüstungsmalus** (`BaseItem.armor_check_penalty`): "Der Rüstungsmalus
  wird auf alle Fertigkeitswürfe angerechnet, die auf Geschicklichkeit oder
  Stärke basieren" — armor's and shield's add up ("Wenn ein Charakter
  gleichzeitig eine Rüstung und einen Schild trägt, gelten beide
  Rüstungsmali"); masterwork lowers each by 1, never above 0.
- **Ungeübt**: "Ein Charakter, der Rüstungen und/oder Schilde trägt, in deren
  Umgang er nicht geübt ist, muss den Rüstungsmalus … auf alle
  Angriffswürfe rechnen" — per item, against its proficiency feat (picked
  or class-granted).
- **Bewegungsrate**: "Mittelschwere oder schwere Rüstungen verlangsamen ihren
  Träger" — 9 m -> 6 m, 6 m -> 4,5 m (the table's two columns, extended to
  faster speeds by the Pferdeharnisch table: 12 -> 9, 15 -> 10,5, 18 -> 12).
  Zwerge keep 6 m — no Zwerg is in the catalog yet; once one is, its
  "Langsam und beständig" belongs in `SPEED_UNAFFECTED_BY_ARMOR_ABILITY_IDS`.

Encumbrance (the same penalties from load) isn't modeled — there is no
carrying capacity yet.
"""

from collections.abc import Iterable
from uuid import UUID

from .modifiers import Modifier, ModifierTarget

ARMOR_SPEEDS: dict[float, float] = {6: 4.5, 9: 6, 12: 9, 15: 10.5, 18: 12}
SLOWING_ARMOR = frozenset({"medium", "heavy"})
# Race abilities that keep land speed in medium/heavy armor (Zwerg's
# "Langsam und beständig" once a Zwerg is seeded).
SPEED_UNAFFECTED_BY_ARMOR_ABILITY_IDS: frozenset[UUID] = frozenset()

UMGANG_LEICHTE_RUESTUNG = UUID("12ff29e6-13a9-52d5-899d-1e72be8ffbf6")
UMGANG_MITTELSCHWERE_RUESTUNG = UUID("f8d17fa6-e2a0-59b1-9c2b-d7352be3202a")
UMGANG_SCHWERE_RUESTUNG = UUID("38cd3d30-27d8-5cdc-a571-da1c2241ea7a")
UMGANG_SCHILDE = UUID("45f3215a-abe5-5836-b994-7504b0e1d14d")
UMGANG_TURMSCHILDE = UUID("a9a32b78-df28-51f1-a190-62144f6dee97")
TURMSCHILD_ITEM_ID = UUID("44b091af-8c4f-48f0-a6c0-7c85c1fb838c")
ARMOR_PROFICIENCY_FEATS = {
    "light": UMGANG_LEICHTE_RUESTUNG,
    "medium": UMGANG_MITTELSCHWERE_RUESTUNG,
    "heavy": UMGANG_SCHWERE_RUESTUNG,
}


def armored_speed(speed: float) -> float:
    """Land speed in medium/heavy armor; a speed off the table loses a
    third, rounded down to whole 1,5-m squares."""
    if speed in ARMOR_SPEEDS:
        return ARMOR_SPEEDS[speed]
    return int(speed * 2 / 3 / 1.5) * 1.5


def check_penalty(item, gear_row) -> int:
    """One equipped armor/shield's Rüstungsmalus (0 or negative)."""
    penalty = item.armor_check_penalty or 0
    if penalty and gear_row.is_masterwork:
        penalty += 1
    return min(0, penalty)


def required_proficiency_feat(item) -> UUID | None:
    if item.category == "shield":
        return UMGANG_TURMSCHILDE if item.id == TURMSCHILD_ITEM_ID else UMGANG_SCHILDE
    return ARMOR_PROFICIENCY_FEATS.get(item.armor_weight_class)


def armor_modifiers(
    equipped: Iterable[tuple[object, object]], proficiency_feat_ids: frozenset[UUID], skill_ids: Iterable[str]
) -> list[Modifier]:
    """Rüstungsmalus on each ST/GE skill (`skill_ids`) and, for an item the
    character isn't proficient with, on every attack. `equipped` are the
    (item, gear row) pairs in the armor and shield slots."""
    modifiers: list[Modifier] = []
    skill_ids = list(skill_ids)
    for item, gear_row in equipped:
        penalty = check_penalty(item, gear_row)
        if not penalty:
            continue
        modifiers += [
            Modifier(source=f"Rüstungsmalus ({item.name})", type="untyped", value=penalty, target=ModifierTarget.SKILL,
                     target_id=skill_id)
            for skill_id in skill_ids
        ]
        feat_id = required_proficiency_feat(item)
        if feat_id is not None and feat_id not in proficiency_feat_ids:
            modifiers.append(
                Modifier(source=f"Ungeübt: {item.name}", type="untyped", value=penalty, target=ModifierTarget.ANY_ATTACK)
            )
    return modifiers
