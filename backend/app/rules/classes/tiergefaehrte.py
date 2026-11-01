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

Archetype (Hausregel, `scripts/import_hausregel_elementargefaehrte.py`):
- Elementargefährte (Luft/Erde/Feuer/Wasser) — replaces Entrinnen,
  Verbessertes Entrinnen and Mehrfachangriff (`app/companions.py` drops
  them). Computed: Luft's flight at 9th (6 m gut, or one maneuverability
  category better for a species that already flies) and Wasser's swim
  speed at 2nd (6 m, or +3 m on an existing one). Erde's SR (1/Adamant, +1
  per 4 effective master levels — "Druidenstufen" read as the companion
  level, so it works for every master) and Feuer's extra fire damage (1W6
  per 5 HD) are read-outs: the sheet has no SR value and the attack is the
  player's pick. Feuer's Behände Bewegung is a granted feat
  (`base_class_ability_granted_feats.json`). Elementare Unterart is text.
"""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..modifiers import Modifier, ModifierTarget
from ..speed import improved_maneuverability

VERBINDUNG_ABILITY_ID = UUID("e373697e-ded5-5ec8-aff2-9c386967a88a")
HINGABE_ABILITY_ID = UUID("68174d66-9730-5400-b702-71d24aaf4747")
MEHRFACHANGRIFF_ABILITY_ID = UUID("25d66f4b-94be-5d10-a40b-7a50c2848ed7")

LUFT_GERINGER_ID = UUID("aa727b10-08c4-5b19-bcc6-e1b19c8d6983")
LUFT_GROESSER_ID = UUID("15f1f607-71b5-56a9-906d-1f6095741293")
ERDE_GERINGER_ID = UUID("6fb5c805-ae8c-5085-90a4-bb35effaffa8")
ERDE_GROESSER_ID = UUID("1a124e65-87ec-5503-b47a-dd9b6287c0be")
FEUER_GERINGER_ID = UUID("4ef87fa4-fd6d-5179-9ad1-a1b1f0336ff5")
FEUER_GROESSER_ID = UUID("b1b6ca49-0071-59c9-aa97-8f18a9eb9389")
WASSER_GERINGER_ID = UUID("0a8966f2-65f5-54c7-8d7a-6c22e2d2070f")
WASSER_GROESSER_ID = UUID("cb0b5465-3582-5290-aed3-33e4b1cf4c59")
_LESSER = "Geringere elementare Manifestation"
_GREATER = "Größere elementare Manifestation"
ELEMENTAL_FLY_SPEED = 6
ELEMENTAL_SWIM_SPEED = 6
ELEMENTAL_SWIM_BONUS = 3


def has_multiattack_bonus_feat(context: CharacterContext) -> bool:
    """Whether the companion's "Mehrfachangriff" counts as the feat (three
    or more natural attacks)."""
    return MEHRFACHANGRIFF_ABILITY_ID in context.granted_ability_ids and context.natural_attack_count >= 3


def _mehrfachangriff_summary(context: CharacterContext) -> str:
    if has_multiattack_bonus_feat(context):
        return "Bonustalent Mehrfachangriff: sekundäre natürliche Angriffe −2 statt −5"
    return "1 zusätzlicher Angriff mit einer natürlichen Waffe, Malus −5"


def _luft_flight(context: CharacterContext) -> list[Modifier]:
    """6 m (gut), or the species' own fly speed one maneuverability
    category better (`sheet.py` keeps the better one at equal speed)."""
    species_fly = context.companion_species_speeds.get("fly")
    if species_fly:
        maneuverability = improved_maneuverability(context.companion_fly_maneuverability)
        return [Modifier(source=_GREATER, type="base", value=species_fly, target=ModifierTarget.FLY_SPEED,
                         detail=maneuverability)]
    return [Modifier(source=_GREATER, type="base", value=ELEMENTAL_FLY_SPEED, target=ModifierTarget.FLY_SPEED,
                     detail="gut")]


def _wasser_swim(context: CharacterContext) -> list[Modifier]:
    """6 m, or +3 m on the species' own swim speed."""
    if context.companion_species_speeds.get("swim"):
        return [Modifier(source=_LESSER, type="untyped", value=ELEMENTAL_SWIM_BONUS, target=ModifierTarget.SWIM_SPEED)]
    return [Modifier(source=_LESSER, type="base", value=ELEMENTAL_SWIM_SPEED, target=ModifierTarget.SWIM_SPEED)]


def _erde_damage_reduction(context: CharacterContext) -> str:
    return f"SR {1 + (context.companion_effective_level or 0) // 4}/Adamant"


def _feuer_damage(context: CharacterContext) -> str:
    return f"+{max(1, context.character_level // 5)}W6 Feuerschaden mit einem natürlichen Angriff nach Wahl"


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    LUFT_GROESSER_ID: _luft_flight,
    WASSER_GERINGER_ID: _wasser_swim,
}
FEATURE_SUMMARY_HANDLERS: dict[UUID, Callable[[CharacterContext], str]] = {
    VERBINDUNG_ABILITY_ID: lambda _context: "Meister: +4 auf Tierempathie und Mit Tieren umgehen für diesen Gefährten",
    HINGABE_ABILITY_ID: lambda _context: "+4 Moral auf Willenswürfe gegen Verzauberungen",
    MEHRFACHANGRIFF_ABILITY_ID: _mehrfachangriff_summary,
    LUFT_GERINGER_ID: lambda _context: "20 % Fehlschlagchance gegen Fernkampfangriffe",
    ERDE_GERINGER_ID: _erde_damage_reduction,
    ERDE_GROESSER_ID: lambda _context: "Natürliche Angriffe überwinden SR wie Adamant, kaltes Eisen und Silber",
    FEUER_GERINGER_ID: lambda _context: "Sicht durch Feuer, Nebel und Rauch; Bonustalent Behände Bewegung",
    FEUER_GROESSER_ID: _feuer_damage,
    WASSER_GROESSER_ID: lambda _context: "Stoßen (3 m) mit einem natürlichen Nahkampfangriff nach Wahl",
}
PARTIAL_EFFECT_NOTES: dict[UUID, str] = {
    WASSER_GERINGER_ID: "Unterwasseratmung und +2 Ausweichbonus auf RK gegen Gelegenheitsangriffe nicht berechnet",
}
APPLIED_OUTSIDE_HANDLERS_IDS: frozenset[UUID] = frozenset({MEHRFACHANGRIFF_ABILITY_ID})
