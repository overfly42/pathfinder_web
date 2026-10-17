"""Creature size — roadmap slice 10, step 2a ("Size as real data"). Used by
player characters now and by companions/familiars later (which need the
whole scale, Mini … Kolossal, not just Klein/Mittelgroß).

Composition stays data: a race's base size is its "Klein"/"Mittelgroß"
race ability (`BASE_SIZE_BY_ABILITY`, one grant per race — the shape
`todos.md`'s "Rassengröße" item decided, like `rules/speed.py`'s base-speed
abilities). Size-changing effects (Person vergrößern/verkleinern; later
Tiergestalt/Bestiengestalt) shift it in steps (`SIZE_STEP_HANDLERS`, keyed by
the effect's source id); the result is clamped to the nine categories.

Size is *resolved*, never stored, and isn't a `CharacterContext` field —
the context only carries raw data; `sheet.py` resolves the size once and
feeds `size_modifiers` into the ordinary stacking, so AC, attack, CMB/CMD
and skills pick it up like any other bonus.

`step_damage` is the one damage-dice step table (weapon damage by wielder
size, natural attacks by creature size, and later Verbesserter Natürlicher
Angriff's "one step up")."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from uuid import UUID

from .context import CharacterContext
from .modifiers import Modifier, ModifierTarget

SIZES: tuple[str, ...] = (
    "Mini",
    "Winzig",
    "Sehr klein",
    "Klein",
    "Mittelgroß",
    "Groß",
    "Riesig",
    "Gigantisch",
    "Kolossal",
)
MEDIUM = SIZES.index("Mittelgroß")
SMALL = SIZES.index("Klein")


@dataclass(frozen=True)
class SizeRow:
    # Size modifier on AC and attack rolls (a "size" bonus/penalty).
    ac_attack: int
    # Heimlichkeit / Fliegen size modifiers.
    stealth: int
    fly: int
    # Space and natural reach in meters; "long" creatures (most quadrupeds,
    # e.g. a horse) have less reach than "tall" ones of the same size.
    space: float
    reach_tall: float
    reach_long: float

    @property
    def special(self) -> int:
        """The CMB/CMD "special size modifier" is the inverse of the AC/
        attack one."""
        return -self.ac_attack


SIZE_TABLE: dict[str, SizeRow] = {
    "Mini": SizeRow(8, 16, 8, 0.15, 0, 0),
    "Winzig": SizeRow(4, 12, 6, 0.3, 0, 0),
    "Sehr klein": SizeRow(2, 8, 4, 0.75, 0, 0),
    "Klein": SizeRow(1, 4, 2, 1.5, 1.5, 1.5),
    "Mittelgroß": SizeRow(0, 0, 0, 1.5, 1.5, 1.5),
    "Groß": SizeRow(-1, -4, -2, 3, 3, 1.5),
    "Riesig": SizeRow(-2, -8, -4, 4.5, 4.5, 3),
    "Gigantisch": SizeRow(-4, -12, -6, 6, 6, 4.5),
    "Kolossal": SizeRow(-8, -16, -8, 9, 9, 6),
}

HEIMLICHKEIT_SKILL_ID = UUID("432bdbaa-0286-4203-a117-1dbc4d68056b")
FLIEGEN_SKILL_ID = UUID("a71cd8ed-15b2-4594-9819-0e320071513c")

# The race abilities naming a race's size (`base_race_abilities.json`).
KLEIN_ABILITY_ID = UUID("fa596c0c-5e34-48f7-ac77-c2d979d53738")
MITTELGROSS_ABILITY_ID = UUID("c98915e3-0ade-4fd4-a203-baed02fdfc7e")
BASE_SIZE_BY_ABILITY: dict[UUID, str] = {
    KLEIN_ABILITY_ID: "Klein",
    MITTELGROSS_ABILITY_ID: "Mittelgroß",
}

# Person vergrößern / Person verkleinern (`base_spells.json`) — one size
# category up/down while active; their ability-score changes are ordinary
# `rules/effects.py` handlers.
PERSON_VERGROESSERN_SPELL_ID = UUID("02b2b44d-660a-5896-9efa-fac7c3de9bdd")
PERSON_VERKLEINERN_SPELL_ID = UUID("53aa254b-30aa-559a-bde1-1d7fa7ff6904")


def _one_step(effect_id: UUID, steps: int) -> Callable[[CharacterContext], int]:
    def handler(context: CharacterContext) -> int:
        # Several castings of the same spell don't stack: presence, not sum.
        return steps if context.has_active(effect_id) else 0

    return handler


SIZE_STEP_HANDLERS: dict[UUID, Callable[[CharacterContext], int]] = {
    PERSON_VERGROESSERN_SPELL_ID: _one_step(PERSON_VERGROESSERN_SPELL_ID, 1),
    PERSON_VERKLEINERN_SPELL_ID: _one_step(PERSON_VERKLEINERN_SPELL_ID, -1),
}


def base_size(ability_ids: Iterable[UUID]) -> str:
    """The size named by one of `ability_ids` (a race's own size ability;
    for a companion later its species/advancement row) — Mittelgroß when
    none names one, the assumption the sheet made before size existed."""
    for ability_id in ability_ids:
        size = BASE_SIZE_BY_ABILITY.get(ability_id)
        if size is not None:
            return size
    return "Mittelgroß"


def resolve_size(base: str, context: CharacterContext) -> str:
    """`base` shifted by every active size-changing effect, clamped to the
    nine categories."""
    steps = sum(handler(context) for handler in SIZE_STEP_HANDLERS.values())
    index = min(len(SIZES) - 1, max(0, SIZES.index(base) + steps))
    return SIZES[index]


def _size_typed(value: int) -> str:
    """A bonus is typed "size" (one size bonus at a time); a penalty is
    "untyped" because `rules/modifiers.py`'s `stack()` keeps only a type's
    highest value from 0 up — a typed penalty would silently vanish (PF1e
    penalties stack anyway)."""
    return "size" if value > 0 else "untyped"


def size_modifiers(size: str) -> list[Modifier]:
    """The size category's modifiers as ordinary `Modifier`s: AC and every
    weapon attack (`ANY_ATTACK`, melee and ranged), the inverse on CMB/CMD,
    Heimlichkeit and Fliegen. Nothing for Mittelgroß."""
    row = SIZE_TABLE[size]
    source = f"Größe ({size})"
    modifiers: list[Modifier] = []
    if row.ac_attack:
        modifiers += [
            Modifier(source=source, type=_size_typed(row.ac_attack), value=row.ac_attack, target=ModifierTarget.AC),
            Modifier(source=source, type=_size_typed(row.ac_attack), value=row.ac_attack, target=ModifierTarget.ANY_ATTACK),
            Modifier(source=source, type=_size_typed(row.special), value=row.special, target=ModifierTarget.CMB),
            Modifier(source=source, type=_size_typed(row.special), value=row.special, target=ModifierTarget.CMD),
        ]
    if row.stealth:
        modifiers.append(
            Modifier(source=source, type=_size_typed(row.stealth), value=row.stealth, target=ModifierTarget.SKILL, target_id=str(HEIMLICHKEIT_SKILL_ID))
        )
    if row.fly:
        modifiers.append(
            Modifier(source=source, type=_size_typed(row.fly), value=row.fly, target=ModifierTarget.SKILL, target_id=str(FLIEGEN_SKILL_ID))
        )
    return modifiers


def format_meters(value: float) -> str:
    text = f"{value:g}".replace(".", ",")
    return f"{text} m"


# ---- damage dice by size ----

# Each list is one chain of the standard PF1e damage-by-size progression
# (Grundregelwerk "Waffen mit unterschiedlicher Größe" / Monsterhandbuch
# "Verbesserter Natürlicher Angriff"): moving one step right = one size
# larger. 1W10 and 1W12 sit on a branch of their own that joins the d8 chain.
_CHAINS: tuple[tuple[str, ...], ...] = (
    ("1", "1W2", "1W3", "1W4", "1W6", "1W8", "2W6", "3W6", "4W6", "6W6", "8W6", "12W6"),
    ("1W10", "2W8", "3W8", "4W8", "6W8", "8W8", "12W8"),
)
# Dice outside the chains, or where the step down leaves its own chain.
_STEP_UP: dict[str, str] = {"2W4": "2W6", "1W12": "3W6", "2W10": "4W8"}
_STEP_DOWN: dict[str, str] = {"2W4": "1W6", "1W12": "1W10", "2W10": "2W8", "1W10": "1W8", "2W8": "1W10"}


def _step_once(dice: str, up: bool) -> str | None:
    special = (_STEP_UP if up else _STEP_DOWN).get(dice)
    if special is not None:
        return special
    for chain in _CHAINS:
        if dice in chain:
            index = chain.index(dice) + (1 if up else -1)
            if 0 <= index < len(chain):
                return chain[index]
            return None
    return None


def step_damage(dice: str, steps: int) -> str:
    """`dice` moved `steps` size categories (positive = larger). Dice the
    table doesn't know (or that would leave it) stay unchanged; a double
    weapon's "1W6/1W6" is stepped per end."""
    if steps == 0 or not dice:
        return dice
    if "/" in dice:
        return "/".join(step_damage(part, steps) for part in dice.split("/"))
    current = dice
    for _ in range(abs(steps)):
        stepped = _step_once(current, steps > 0)
        if stepped is None:
            return current
        current = stepped
    return current


def weapon_damage(damage_medium: str | None, damage_small: str | None, wielder_size: str) -> str | None:
    """A manufactured weapon's damage for a wielder of `wielder_size` (the
    app has no per-item size: a character's weapons are assumed made for
    them). Klein uses the catalog's own `damage_small` when seeded."""
    if damage_medium is None:
        return None
    if wielder_size == "Klein" and damage_small:
        return damage_small
    return step_damage(damage_medium, SIZES.index(wielder_size) - MEDIUM)
