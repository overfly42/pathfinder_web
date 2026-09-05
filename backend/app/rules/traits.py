"""Handler registry for trait effects that need real computation, not just
composition — mirrors `rules/feats.py` (same "first entry" scale, same
"merged into `rules/handlers.py`'s `HANDLERS` since ids are globally unique
across every family" integration). Empty until now because every trait in
this catalog was flavor-only (see `todos.md`'s "Volksspezifische Optionen
zur Bevorzugten Klasse" entry's sibling note on traits, 2026-08-21).

First entry: "Gewitztes Wortspiel" (Clever Wordplay, `scripts/
import_trait_clever_wordplay.py`), the first trait in this catalog with a
`BaseTrait.skill_choice_ability`-gated sub-choice (`CharacterTrait.
chosen_skill_id`, validated in `routers/characters.py`)."""

from collections.abc import Callable
from uuid import UUID

from .context import CharacterContext
from .modifiers import Modifier, ModifierTarget
from .progression import ability_mod

# `base_traits.json`'s "Gewitztes Wortspiel" row id.
GEWITZTES_WORTSPIEL = UUID("d190edc6-d19d-5db8-8eb6-3a38fb1eea1c")

# `base_traits.json`'s "Fokussierter Verstand" row id ("Du erhältst einen
# Wesenszugbonus von +2 auf Konzentrationswürfe.") — unconditional (unlike
# Zäher Zauberer's defensive-cast-only +4 or Arkane Konzentration's
# underwater-only +2, neither of which is a `HANDLERS` entry since neither
# has a trigger this sheet can detect, see `sheet.py`'s
# `_build_concentration` docstring), so it's a perfectly ordinary flat
# `Modifier` like any other trait bonus, needing no special-casing outside
# the standard composition (trait exists) / computation (this handler) /
# stacking (`rules/modifiers.py`'s `stack()`) pipeline.
FOKUSSIERTER_VERSTAND = UUID("f5a594bc-a429-587e-918c-b607caf20212")

# `base_traits.json`'s "Begabt" row id ("+1 Wesenszugbonus auf eine
# Auftretenfertigkeit deiner Wahl. Auftreten ist für dich stets eine
# Klassenfertigkeit."). No `skill_choice_ability` sub-choice needed despite
# the "deiner Wahl" wording: Auftreten (`_AUFTRETEN_SKILL_ID` below) is
# modeled as one skill with specializations (`base_skill_specializations.json`:
# Gesang/Tanz/Schauspiel, plus a free-typed one), not as several sibling
# skills the way `skill_choice_ability` picks between — the "choice" is which
# *specialization*, and `sheet.py`'s skill-bonus system already only targets
# a base skill id, never one specialization (same imprecision its existing
# class-skill bonus has, see `sheet.py`'s `_skill_entry` docstring) — so
# there's nothing left to disambiguate here, same reasoning `feats.py`'s
# `_einschuechternde_kraft` uses for hardcoding a single skill id outright.
BEGABT = UUID("8b17eb40-3e3d-59e2-b95a-ea6d591b4606")
# `base_skills.json`'s "Auftreten" row id.
_AUFTRETEN_SKILL_ID = "fa72f72e-b86a-4d93-9382-bbcee12fdfd9"


def _gewitztes_wortspiel(context: CharacterContext) -> list[Modifier]:
    """"Wähle eine charismabasierte Fertigkeit. Du legst Fertigkeitswürfe für
    diese Fertigkeit mit deinem IN-Modifikator anstelle deines
    CH-Modifikators ab." `sheet.py`'s `_build_skills` always folds a skill's
    normal `ability_mods[skill.ability]` (here: the CH modifier) into its
    base value first, the same as every other skill — this handler doesn't
    override that calculation, it adds the *delta* between the IN and CH
    modifiers as an extra untyped skill bonus on top, landing at the same
    total (CH mod + (IN mod - CH mod) = IN mod) without needing a special
    case in `_build_skills` itself. Untyped since no named PF1e bonus type
    fits a modifier substitution, same convention `rules/feats.py`'s
    `_einschuechternde_kraft` uses for its own off-ability skill bonus.
    Returns nothing if the trait wasn't taken (`context.trait_skill_choices`
    has no entry) or the delta happens to be exactly 0."""
    skill_id = context.trait_skill_choices.get(GEWITZTES_WORTSPIEL)
    if skill_id is None:
        return []
    delta = ability_mod(context.ability_scores.get("IN", 10)) - ability_mod(context.ability_scores.get("CH", 10))
    if delta == 0:
        return []
    return [
        Modifier(
            source="Gewitztes Wortspiel",
            type="untyped",
            value=delta,
            target=ModifierTarget.SKILL,
            target_id=str(skill_id),
        )
    ]


def _fokussierter_verstand(context: CharacterContext) -> list[Modifier]:
    # Unconditional (see `FOKUSSIERTER_VERSTAND`'s own docstring above),
    # same reasoning as `race_abilities.py`'s `_attribute_bonus`.
    del context
    return [Modifier(source="Fokussierter Verstand", type="trait", value=2, target=ModifierTarget.CONCENTRATION)]


def _begabt(context: CharacterContext) -> list[Modifier]:
    # Unconditional (see `BEGABT`'s own docstring above) — the class-skill
    # half of this trait isn't a `Modifier` at all, see `CLASS_SKILL_GRANTS`
    # below.
    del context
    return [
        Modifier(
            source="Begabt",
            type="trait",
            value=1,
            target=ModifierTarget.SKILL,
            target_id=_AUFTRETEN_SKILL_ID,
        )
    ]


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    GEWITZTES_WORTSPIEL: _gewitztes_wortspiel,
    FOKUSSIERTER_VERSTAND: _fokussierter_verstand,
    BEGABT: _begabt,
}

# Trigger id -> skill ids it makes a class skill regardless of the
# character's actual classes — the other half of any trait/feat shaped like
# "+bonus, and X is always a class skill" (Begabt is the first of at least 8
# traits in `base_traits.json` with this exact shape, e.g. "Machtvolle
# Präsenz", "Sucher" — those stay unimplemented until a future pass actually
# needs them, same "empty until now" convention this module's own docstring
# used before `HANDLERS` had its first entry). Kept separate from `HANDLERS`
# since class-skill status isn't a `Modifier` (`sheet.py`'s `class_skill_ids`
# is a set of ids, not a stat with a value) — merged into `rules/handlers.py`'s
# `granted_class_skill_ids` the same way `SITUATIONAL_SKILL_HANDLERS` merges
# per-family slices into one registry.
CLASS_SKILL_GRANTS: dict[UUID, frozenset[UUID]] = {
    BEGABT: frozenset({UUID(_AUFTRETEN_SKILL_ID)}),
}
