"""Handler registry for magic weapon special abilities (roadmap.md's
"Magische Verzauberung/Material als Berechnung statt Freitext" decision, see
CLAUDE.md: composition — what abilities exist — stays data, computing what
one actually does stays code).

Deliberately **not** an attack/damage-bonus engine: this app is a tabletop
aid for a player, not a combat simulator (per the roadmap decision this
module implements). Of the ~90 cataloged abilities, most either depend on
opponent data this app never models (alignment/creature type/condition — e.g.
Verderben, Heilig/Unheilig) or only matter on the player's own crit roll (e.g.
Blitzinferno, Hinrichtung) — the player reads the ability off the weapon and
applies it at the table themselves. So unlike `race_abilities.py` (where
every id has a real, distinct computed effect), every ability here resolves
through the same trivial fallback, `_generic`, which just surfaces the
catalog's own name/description for display — no id-keyed constants needed
today since there's no distinct behavior yet to name one by.

`HANDLERS` still exists and is still what every caller goes through
(`resolve()`), not a shortcut some abilities skip and others don't — so that
`sheet.py` never has to branch between "abilities with a handler" and
"abilities without one" the way `race_abilities.py`'s flavor-only abilities
do (see that module's docstring). The one identified future exception is
Zornig/Kräftigend, whose effect depends on the wielder's own rage/knockout
state rather than an opponent's — once roadmap slice 5 (Effects/Conditions)
adds state tracking, those two get a real entry here; until then they render
through `_generic` like everything else."""

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from ..models.item import BaseWeaponSpecialAbility


def _generic(ability: "BaseWeaponSpecialAbility") -> dict[str, str | None]:
    return {"name": ability.name, "description": ability.description}


HANDLERS: dict[UUID, Callable[["BaseWeaponSpecialAbility"], dict[str, str | None]]] = {}


def resolve(ability: "BaseWeaponSpecialAbility") -> dict[str, str | None]:
    return HANDLERS.get(ability.id, _generic)(ability)
