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


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    GEWITZTES_WORTSPIEL: _gewitztes_wortspiel,
}
