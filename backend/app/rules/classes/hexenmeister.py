"""Hexenmeister (Sorcerer) handlers — one file per class (CLAUDE.md's
"Working Conventions"). Feeds `rules/handlers.py`'s unified `HANDLERS`/
`DAILY_LIMITS`/`SAVE_DC_HANDLERS`, same merge-only role `race_abilities.py`/
`speed.py` play for their own slices — this file owns every Hexenmeister
ability id and its computation; nothing outside it should reference these
ids directly.

First content: Meeresblutlinie's 1st-level bloodline power "Wasserstoß"
(also reachable via the Sekundärklasse alternate rule, see
`scripts/build_secondary_class_hexenmeister_seed.py` — this handler applies
identically either way, since `DAILY_LIMITS`/`SAVE_DC_HANDLERS`/
`rules/daily_limits.py` key off the ability id alone, not how it was
granted).

Second content: Meeresblutlinie's 3rd-level "Aquatische Anpassung" (also
reachable via Sekundärklasse, same as Wasserstoß above)."""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..modifiers import Modifier, ModifierTarget
from ..progression import ability_mod

# Hexenmeister's own root `BaseClass` id (`base_classes.json`).
HEXENMEISTER_ROOT_CLASS_ID = UUID("ceb02ad1-268c-4a1c-a7c9-ea8a1cbbe67e")

# Meeresblutlinie's 1st-level bloodline power (`base_class_abilities.json`).
# PRD text: "Mit einer Standard-Aktion kannst du einen Wasserstrahl auf
# einen Gegner innerhalb von 9 m als Berührungsangriff im Fernkampf
# abschießen. Der Feind wird zu Boden geworfen und kann 1,50 m von dir
# weggeschoben werden [...]. Bei einem erfolgreichen Reflexwurf gegen SG 10
# + deine ½ Stufe als Hexenmeister + deinen CH-Modifikator hat dieser Effekt
# keine Wirkung. Du kannst diese Fähigkeit täglich in Höhe deines
# CH-Modifikators +3 einsetzen."
#
# The daily-use count and the save DC are modeled here (`DAILY_LIMITS`/
# `SAVE_DC_HANDLERS` below) — same "player-reminder text only, not
# automation" scope `rules/classes/kampfmagus.py`'s own docstring already
# establishes for e.g. Perfekter Schlag beyond that: the ranged touch attack
# roll itself, rolling the target's Reflex save against the DC computed
# here, and the knockdown/1.5m-push effect all stay the player's own call —
# there's no attack-roll/save-resolution engine anywhere in this codebase to
# hang them on (`base_class_abilities.json`'s stored description already has
# the full rules text for the player to resolve manually).
WASSERSTOSS_ABILITY_ID = UUID("5223e8ec-aff8-58ef-8033-0499b9a530e5")


def _wasserstoss_uses_per_day(context: CharacterContext) -> int:
    """"täglich in Höhe deines CH-Modifikators +3" — flat CH-mod + 3,
    doesn't scale with Hexenmeister level (unlike e.g. Barbar's Kampfrausch
    rounds/day)."""
    return ability_mod(context.ability_scores.get("CH", 10)) + 3


def _wasserstoss_dc(context: CharacterContext) -> int:
    """"SG 10 + deine ½ Stufe als Hexenmeister + deinen CH-Modifikator" —
    `level_counts_by_root_id[HEXENMEISTER_ROOT_CLASS_ID]` already carries
    the right number for either source: a real Hexenmeister's own class
    level, or (Sekundärklasse) the synthetic effective level `rules/
    secondary_class.py` merges in there, which the alternate rule's own
    "Blutlinie" clause already defines as the character's full total level
    for every bloodline ability — no separate real-vs-secondary branch
    needed here."""
    hexenmeister_level = context.level_counts_by_root_id.get(HEXENMEISTER_ROOT_CLASS_ID, 0)
    return 10 + hexenmeister_level // 2 + ability_mod(context.ability_scores.get("CH", 10))


# Meeresblutlinie's 3rd-level bloodline power (`base_class_abilities.json`).
# PRD text: "Ab der 3. Stufe hat der Hexenmeister eine Schwimm-Bewegungsrate
# von 9 m. Ab der 9. Stufe erhält er die Besondere Eigenschaft Amphibie und
# entwickelt eine Fettschicht, die ihm einen Bonus auf seine natürliche
# Rüstung von +1 sowie Kälteresistenz 5 verleiht. Im Wasser erhält er
# Blindgespür 9 m. Auf der 15. Stufe steigt die Schwimm-Bewegungsrate auf
# 18 m und die Reichweite von Blindgespür im Wasser auf 18 m."
#
# Only the swim speed and the 9th-level natural armor bonus are modeled as
# `Modifier`s below — `ModifierTarget.SWIM_SPEED` and `.AC`'s "natural" type
# both already have a computed slot in the sheet (the same slots Katzenvolk's
# Kletterer/various feats' natural-armor bonuses use), so this ability's
# contribution to them can be resolved the normal way. Amphibie, Kälteresistenz
# 5, and Blindgespür have no equivalent slot anywhere in this codebase yet (no
# special-quality/energy-resistance/sense list exists at all) — same
# "player-reminder text only, not automation" scope this file's own
# `WASSERSTOSS_ABILITY_ID` docstring already draws around the touch attack
# roll/save resolution it leaves manual; `base_class_abilities.json`'s stored
# description already has the full rules text for the player to apply by hand.
AQUATISCHE_ANPASSUNG_ABILITY_ID = UUID("efab193d-31e6-5162-aa8b-81ce99c98884")


def _aquatische_anpassung(context: CharacterContext) -> list[Modifier]:
    """Thresholds against the character's effective Hexenmeister level, the
    same `level_counts_by_root_id` lookup `_wasserstoss_dc` above uses — it
    already carries the right number for either a real Hexenmeister's own
    class level or (Sekundärklasse) `rules/secondary_class.py`'s synthetic
    effective level, and this ability's own "Ab der 3./9./15. Stufe" tiers
    are keyed off that same class level in the source text (not the
    character's total level directly, even though for a real Hexenmeister
    those happen to be identical)."""
    hexenmeister_level = context.level_counts_by_root_id.get(HEXENMEISTER_ROOT_CLASS_ID, 0)
    modifiers = [
        Modifier(
            source="Aquatische Anpassung",
            type="base",
            value=18 if hexenmeister_level >= 15 else 9,
            target=ModifierTarget.SWIM_SPEED,
        )
    ]
    if hexenmeister_level >= 9:
        modifiers.append(
            Modifier(source="Aquatische Anpassung", type="natural", value=1, target=ModifierTarget.AC)
        )
    return modifiers


# This class's slice of `rules/handlers.py`'s merged `HANDLERS` — see that
# module's docstring for what this covers.
HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    AQUATISCHE_ANPASSUNG_ABILITY_ID: _aquatische_anpassung,
}

# This class's slice of `rules/handlers.py`'s merged `DAILY_LIMITS` — see
# that module's docstring for what this covers.
DAILY_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    WASSERSTOSS_ABILITY_ID: _wasserstoss_uses_per_day,
}

# This class's slice of `rules/handlers.py`'s merged `SAVE_DC_HANDLERS` —
# see that module's docstring for what this covers.
SAVE_DC_HANDLERS: dict[UUID, Callable[[CharacterContext], int]] = {
    WASSERSTOSS_ABILITY_ID: _wasserstoss_dc,
}
