"""Handler registry for magic weapon special abilities (roadmap.md's
"Magische Verzauberung/Material als Berechnung statt Freitext" decision, see
CLAUDE.md: composition — what abilities exist — stays data, computing what
one actually does stays code).

Deliberately **not** a dice-rolling combat simulator: this app is a
tabletop aid for a player, it never rolls an attack or a die for you (per
the roadmap decision this module implements — see this file's 2026-08-11
addendum below for the one place a *static computed number*, not a roll,
is now in scope). Of the ~90 cataloged abilities, most either depend on
opponent data this app never models (alignment/creature type/condition — e.g.
Verderben, Heilig/Unheilig) or only matter on the player's own crit roll (e.g.
Hinrichtung) — the player reads the ability off the weapon and applies it at
the table themselves. So unlike `race_abilities.py` (where every id has a
real, distinct computed effect), most abilities here resolve through the
same trivial fallback, `_generic`, which just surfaces the catalog's own
name/description for display — no id-keyed constants needed for those, since
there's no distinct behavior to name one by.

`HANDLERS` still exists and is still what every caller goes through
(`resolve()`), not a shortcut some abilities skip and others don't — so that
`sheet.py` never has to branch between "abilities with a handler" and
"abilities without one" the way `race_abilities.py`'s flavor-only abilities
do (see that module's docstring). The one identified future exception is
Zornig/Kräftigend, whose effect depends on the wielder's own rage/knockout
state rather than an opponent's — once roadmap slice 5 (Effects/Conditions)
adds state tracking, those two get a real entry here; until then they render
through `_generic` like everything else.

**One narrow, deliberate exception to "no id gets distinct behavior"**
(roadmap.md's Slice-4 weapon-slot item, 2026-08-11): the "togglebar per
Befehlswort" flat on-hit energy abilities this module's own docstring above
already anticipated (Aufflammen/Blitz/Eis/Säure and their crit-only
"-inferno"/"-explosion" siblings, which the PRD text says "funktioniert wie
eine X-Waffe" for the on-hit part) are exactly `_generic`'s bar-none
opponent/crit-dependence exclusion turned inside out — they need *no*
opponent data and apply on every hit, not just a crit, gated only by the
wielder's own `CharacterGear.is_active` (already exists, previously only a
display flag — see that column's docstring). `_ENERGY_DAMAGE` keys these 8
by id to a flat extra damage die, read by `sheet.py`'s attack/damage readout
alongside `resolve()`'s existing name/description; every other ability's
`bonusDamage` stays `None`, still resolved through the one `HANDLERS`
mechanism below (`_energy_damage` wraps `_generic`, it doesn't replace it)."""

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from ..models.item import BaseWeaponSpecialAbility

# id -> (extra damage die, PF1e damage-type label). Deliberately not derived
# from `ability.name` (translation/renaming would silently break it) — hand-
# frozen ids, same convention as every other HANDLERS registry (CLAUDE.md).
_ENERGY_DAMAGE: dict[UUID, tuple[str, str]] = {
    UUID("74002e40-27c1-53dc-b8d1-73177d351ff2"): ("1W6", "Feuer"),  # Aufflammen
    UUID("fad02d75-ceb9-5587-95da-62f6e1c603ef"): ("1W6", "Feuer"),  # Flammeninferno
    UUID("ffb6d455-b583-5785-8e8f-369198af28f3"): ("1W6", "Elektrizität"),  # Blitz
    UUID("745664b9-a48a-5c97-8fe7-0a5b3a0350da"): ("1W6", "Elektrizität"),  # Blitzinferno
    UUID("3d8c421c-d0eb-5b97-98c5-c53e4024cc82"): ("1W6", "Kälte"),  # Eis
    UUID("a781f8f5-43d6-511c-a68a-6ae9b344b924"): ("1W6", "Kälte"),  # Eisinferno
    UUID("5f692f01-7a24-5659-a624-2d8a37901e86"): ("1W6", "Säure"),  # Säure
    UUID("61190d42-1ad7-51dc-a2bd-4439c94f66b3"): ("1W6", "Säure"),  # Säureexplosion
}


def _generic(ability: "BaseWeaponSpecialAbility") -> dict[str, object]:
    return {"name": ability.name, "description": ability.description, "bonusDamage": None}


def _energy_damage(ability: "BaseWeaponSpecialAbility") -> dict[str, object]:
    dice, damage_type = _ENERGY_DAMAGE[ability.id]
    result = _generic(ability)
    result["bonusDamage"] = {"dice": dice, "type": damage_type, "requiresActive": True}
    return result


HANDLERS: dict[UUID, Callable[["BaseWeaponSpecialAbility"], dict[str, object]]] = {
    ability_id: _energy_damage for ability_id in _ENERGY_DAMAGE
}


def resolve(ability: "BaseWeaponSpecialAbility") -> dict[str, object]:
    return HANDLERS.get(ability.id, _generic)(ability)


def is_togglable(ability_id: UUID) -> bool:
    """Whether this ability's effect is toggled by `CharacterGear.is_active`
    rather than always-on — used by `routers/characters.py`'s `toggle_gear`
    to allow toggling a weapon carrying one of these even though weapon rows
    never have `BaseItem.activation == "activatable"` (that field is only
    ever set for wondrous/ring/wand catalog rows)."""
    return ability_id in _ENERGY_DAMAGE
