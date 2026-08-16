"""Handler registry for feat effects — the family CLAUDE.md's "implementing
`HANDLERS` one feat at a time" refers to. First entry (2026-08-16); kept as
one file rather than pre-split (CLAUDE.md: "don't split preemptively before a
family shows that growth shape" — race abilities/class abilities only split
the way they do because they'd already outgrown a single file).

Same id-linkage convention as `race_abilities.py`: the UUID below is the
literal, hand-frozen id matching the row in
`backend/app/fixtures/seed/base_feats.json` — never derived, never looked up
by name/description text.
"""

from collections.abc import Callable
from uuid import UUID

from .context import CharacterContext
from .modifiers import Modifier, ModifierTarget
from .progression import ability_mod

EINSCHUECHTERNDE_KRAFT = UUID("73238862-9538-590c-b498-0d96e1ae9b43")

# `BaseSkill.id` for Einschüchtern (`base_skills.json`) — the one skill this
# feat's bonus targets.
_EINSCHUECHTERN_SKILL_ID = "3c60b6e1-8c58-4ed0-9c3a-5e003b9da1cf"


def _einschuechternde_kraft(context: CharacterContext) -> list[Modifier]:
    """GRW S. 121: "Addiere deinen ST-Modifikator zusätzlich zu deinem
    CH-Modifikator auf deine Würfe für Einschüchtern." Unlike Einschüchtern's
    own CH modifier (folded into `ability_mods` before any handler runs,
    `sheet.py`'s `_build_skills`), this ST-based addition has no named bonus
    type in the rulebook, so it's untyped (stacks with everything, same
    convention `rules/classes/barbarian.py`'s Schnelle Bewegung uses for its
    own untyped bonus)."""
    st_mod = ability_mod(context.ability_scores.get("ST", 10))
    return [
        Modifier(
            source="Einschüchternde Kraft",
            type="untyped",
            value=st_mod,
            target=ModifierTarget.SKILL,
            target_id=_EINSCHUECHTERN_SKILL_ID,
        )
    ]


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    EINSCHUECHTERNDE_KRAFT: _einschuechternde_kraft,
}
