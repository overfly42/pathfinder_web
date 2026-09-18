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
granted)."""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
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
