"""Mönch (Monk) — currently only "Rüstungsklassenbonus" (`HANDLERS` below):
an AC/CMD bonus while unarmored and shieldless, using the Wisdom modifier
(or Charisma for a Beschuppte Faust archetype character, whose "Drachenmacht"
retools every Weisheit-keyed Mönch class feature onto Charisma —
`import_scaled_fist_archetype.py`'s own docstring flagged this handler as
the anchor point once the base Mönch had one at all). Meister aller
Kampfstile has no interaction with this ability (it replaces Bonustalent/
Schlaghagel/Vibrierende Handfläche instead), so it needs nothing here.

Not modeled (same "composition only" limits the archetype import already
documented): "bewegungsunfähig"/"hilflos" and encumbrance ("mittelschwere/
schwere Last") gate the RAW bonus too, but this app has no active-condition
tracking or carrying-capacity system to check either against (same gap
Barbar's Reflexbewegung leaves open for its own unevaluated conditions,
`base_class_abilities.json`'s "Diese klassenübergreifende Sonderregel wird
aktuell nicht ausgewertet" rows). "Hilft gegen Berührungsangriffe" has
nothing to plug into either — the sheet has no separate touch-AC stat yet."""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..modifiers import Modifier, ModifierTarget
from ..progression import ability_mod

# Mönch's own root `BaseClass` id (`base_classes.json`) — Meister aller
# Kampfstile/Beschuppte Faust are granted-ability sources only, not
# separately leveled classes; a character's actual class levels are always
# recorded against this id regardless of archetype
# (`character_levels.base_class_id`), so this is the one key
# `context.level_counts_by_root_id` needs.
MOENCH_ROOT_CLASS_ID = UUID("4ed3adcc-31e6-408d-a554-5e76a368df9d")

RUESTUNGSKLASSENBONUS_ABILITY_ID = UUID("8a4aa09f-00bf-59a5-9eb8-50e53b6e32b2")

# Beschuppte Faust's "Drachenmacht" (Draconic Might) — retools every
# Weisheit-keyed Mönch class feature onto Charisma instead. Granted
# alongside, not replacing, Rüstungsklassenbonus (no `BaseClassAbilityReplacement`
# row exists for it), so this handler reads it straight off
# `granted_ability_ids` to pick which ability score to use.
DRACHENMACHT_ABILITY_ID = UUID("17e0cf81-2b18-57f0-9eb5-28dc884b4251")


def _ruestungsklassenbonus(context: CharacterContext) -> list[Modifier]:
    """"Wenn der Mönch nicht gerüstet oder belastet ist, kann er seinen
    Weisheitsbonus (wenn er einen hat) zu seiner Rüstungsklasse und seiner
    Kampfmanöververteidigung addieren. Zusätzlich erhält er auf der 4. Stufe
    einen RK- und KMV-Bonus von +1. Dieser Bonus erhöht sich alle weiteren
    vier Stufen um eins, bis zu einem Maximum von +5 auf der 20. Stufe."
    (`base_class_abilities.json` id 8a4aa09f-...).

    The "unarmored, no shield" gate reuses the same `CharacterContext`
    fields Kensai's Gewitzte Verteidigung already relies on
    (`rules/classes/kampfmagus.py`) — "belastet" (medium/heavy load) isn't
    checked, see module docstring.

    Deliberately tagged a bonus type other than "dodge": unlike a dodge
    bonus, this one explicitly still applies when flat-footed, and
    `sheet.py`'s flat-footed AC only strips "dodge"-typed modifiers, so any
    other type already gets that right for free."""
    if context.equipped_armor_weight_class is not None or context.has_shield_equipped:
        return []
    ability = "CH" if DRACHENMACHT_ABILITY_ID in context.granted_ability_ids else "WE"
    ability_bonus = max(0, ability_mod(context.ability_scores.get(ability, 10)))
    moench_level = context.level_counts_by_root_id.get(MOENCH_ROOT_CLASS_ID, 0)
    level_bonus = min(5, (moench_level - 4) // 4 + 1) if moench_level >= 4 else 0
    total = ability_bonus + level_bonus
    if total <= 0:
        return []
    return [
        Modifier(source="Rüstungsklassenbonus", type="monk", value=total, target=ModifierTarget.AC),
        Modifier(source="Rüstungsklassenbonus", type="monk", value=total, target=ModifierTarget.CMD),
    ]


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    RUESTUNGSKLASSENBONUS_ABILITY_ID: _ruestungsklassenbonus,
}

# `base_class_abilities.json`'s "Betäubender Schlag" wrapper ability id — a
# monk gets the actual "Betäubender Schlag" feat (`rules/feats.py`'s
# `BETAEUBENDER_SCHLAG`) automatically at level 1 with prerequisites waived
# (`base_class_ability_grants.json`: this ability, level 1, every monk;
# `base_class_ability_granted_feats.json` links it to the feat), but that
# grant never creates an actual `CharacterFeat` row — same "just has it, no
# pick, no feat-count cost" shape `BaseClassAbilityGrantedFeat`'s own
# docstring documents for a class-granted proficiency. So this wrapper
# ability's own id (not the feat's) is what ends up in
# `context.granted_ability_ids` for every monk, and needs its own
# `DAILY_LIMITS`/`SAVE_DC_HANDLERS` entry below with the monk-specific
# uses/day formula — `rules/feats.py`'s own entries only cover a character
# with an actual `CharacterFeat` pick of the feat itself.
BETAEUBENDER_SCHLAG_ABILITY_ID = UUID("266c2fb4-3411-5f53-91ff-504d8e65b9df")


def _betaeubender_schlag_dc(context: CharacterContext) -> int:
    """Same "SG 10 + ½ Charakterstufe + WE- (oder CH-, Drachenmacht-)
    Modifikator" formula `rules/feats.py`'s own `_betaeubender_schlag_dc`
    uses for the generic case — duplicated rather than imported to avoid a
    `feats`<->`classes.moench` circular import over three lines of
    arithmetic (`feats.py` already imports `DRACHENMACHT_ABILITY_ID` from
    this module for its own copy of this check)."""
    ability = "CH" if DRACHENMACHT_ABILITY_ID in context.granted_ability_ids else "WE"
    return 10 + context.character_level // 2 + ability_mod(context.ability_scores.get(ability, 10))


def _betaeubender_schlag_uses_per_day(context: CharacterContext) -> int:
    """"Ein Mönch, der dieses Talent wählt, kann jeden Tag so viele
    betäubende Angriffe versuchen, wie er Klassenstufen als Mönch hat plus
    einmal je vier Stufen, die er in anderen Klassen als Mönch besitzt."
    (GRW S. 120, "Speziell")."""
    moench_level = context.level_counts_by_root_id.get(MOENCH_ROOT_CLASS_ID, 0)
    other_levels = context.character_level - moench_level
    return moench_level + other_levels // 4


DAILY_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    BETAEUBENDER_SCHLAG_ABILITY_ID: _betaeubender_schlag_uses_per_day,
}
SAVE_DC_HANDLERS: dict[UUID, Callable[[CharacterContext], int]] = {
    BETAEUBENDER_SCHLAG_ABILITY_ID: _betaeubender_schlag_dc,
}
