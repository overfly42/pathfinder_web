"""Tiergefährte — the pseudo class a companion takes one level in per HD
(roadmap slice 10 step 2b, `scripts/import_companion_species.py`). Its
abilities come from the progression table by effective level, not by HD
(`app/companions.py`).

- "Verbindung" (`FEATURE_SUMMARY_HANDLERS`): the master's +4 on Tierempathie
  and Mit Tieren umgehen concerning this companion — situational, so a
  read-out on the companion's sheet, not a master-side modifier (decided
  2026-10-14).
- "Hingabe" (`FEATURE_SUMMARY_HANDLERS`): +4 morale on Will saves against
  enchantments — situational as well.
- "Mehrfachangriff": with three or more natural attacks it is the
  Mehrfachangriff feat as a bonus feat — `sheet.py`'s `_build_natural_attacks`
  then gives secondary attacks −2 instead of −5 (`APPLIED_OUTSIDE_HANDLERS_IDS`);
  with fewer, one extra attack with one natural weapon at −5, which the
  summary states (which weapon is the player's call at the table).
- Zauber teilen, Entrinnen, Verbessertes Entrinnen: descriptive.
"""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext

VERBINDUNG_ABILITY_ID = UUID("e373697e-ded5-5ec8-aff2-9c386967a88a")
HINGABE_ABILITY_ID = UUID("68174d66-9730-5400-b702-71d24aaf4747")
MEHRFACHANGRIFF_ABILITY_ID = UUID("25d66f4b-94be-5d10-a40b-7a50c2848ed7")


def has_multiattack_bonus_feat(context: CharacterContext) -> bool:
    """Whether the companion's "Mehrfachangriff" counts as the feat (three
    or more natural attacks)."""
    return MEHRFACHANGRIFF_ABILITY_ID in context.granted_ability_ids and context.natural_attack_count >= 3


def _mehrfachangriff_summary(context: CharacterContext) -> str:
    if has_multiattack_bonus_feat(context):
        return "Bonustalent Mehrfachangriff: sekundäre natürliche Angriffe −2 statt −5"
    return "1 zusätzlicher Angriff mit einer natürlichen Waffe, Malus −5"


FEATURE_SUMMARY_HANDLERS: dict[UUID, Callable[[CharacterContext], str]] = {
    VERBINDUNG_ABILITY_ID: lambda _context: "Meister: +4 auf Tierempathie und Mit Tieren umgehen für diesen Gefährten",
    HINGABE_ABILITY_ID: lambda _context: "+4 Moral auf Willenswürfe gegen Verzauberungen",
    MEHRFACHANGRIFF_ABILITY_ID: _mehrfachangriff_summary,
}
APPLIED_OUTSIDE_HANDLERS_IDS: frozenset[UUID] = frozenset({MEHRFACHANGRIFF_ABILITY_ID})
