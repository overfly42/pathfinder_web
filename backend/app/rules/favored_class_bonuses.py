"""Handler registry for Advanced Race Guide alternate favored-class-bonus
options (see CLAUDE.md: composition — which options exist, `scripts/
import_favored_class_bonus_halbork.py` — stays data; computing what a pick
actually converts to stays code). Deliberately *not* part of
`rules/handlers.py`'s unified `HANDLERS`/`CharacterContext` pipeline: a
character's favored-class-bonus picks are `CharacterClassOption` rows, not
`context.feat_ids`/`granted_ability_ids`-style composition, so `sheet.py`
reads them directly and calls this module's own `HANDLERS` with each
choice's *pick count* (not a `CharacterContext`) — see `sheet.py`'s
`_build_favored_class_bonuses` for the read side.

The ids below are the literal, hand-frozen `BaseClassOptionChoice` ids
`import_favored_class_bonus_halbork.py` writes (deterministic
`uuid5(ID_NAMESPACE, "fcb-choice|<base_class_id>")`, reproduced here as
literals since that script isn't importable at runtime — same convention
`rules/classes/barbarian.py` already uses for Seeräuber's ability id). A
row's id either equals one of these constants (and gets a handler here) or
it doesn't (and `sheet.py` falls back to showing only the pick count and
description text — Mönch's two-effects-per-pick and Mystiker's "+1 known
spell" are exactly that case: not a single accumulating number, so no
handler, same "absent handler = flavor-only" convention `race_abilities.py`
already established for Darkvision)."""

import functools
from collections import Counter
from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from ..models.character import Character

BARBAR = UUID("0f134941-47fc-5601-bad2-bc5414f6e963")
ENTFESSELTER_BARBAR = UUID("a6da0398-ab08-5864-b396-c5d848523f79")
BARDE = UUID("4b5e3ead-1d1c-50df-8507-e1ec9237b732")
DRUIDE = UUID("f3de15fb-55bd-5447-ba11-ab84df30d590")
HEXENMEISTER = UUID("ad431597-4bc0-560a-84ca-9196a48209db")
KAEMPFER = UUID("f30e2ef2-2ae6-57f2-80cd-649b70fd4034")
KLERIKER = UUID("28c71980-6db8-5935-9853-03a0287db086")
MAGIER = UUID("2f7a1a57-9eaa-5576-bc7c-d2b7567210d9")
MOENCH = UUID("f55206e5-4b5c-53f8-b64b-ea047b783914")
MYSTIKER = UUID("42690b35-2058-5f6d-883f-2d3761f6e791")
PALADIN = UUID("511e4867-b45c-51fa-8821-3f392db5638b")
SCHURKE = UUID("6d173894-9b17-59b2-90c6-b03e2a60f498")
WALDLAEUFER = UUID("9c7bd1ef-bf5f-5a95-9aa4-f6851823ff2c")


def pick_counts(character: "Character") -> Counter[UUID]:
    """How many times `character` has picked each race-scoped
    favored-class-bonus `BaseClassOptionChoice` id over their whole career
    — the one raw count both `sheet.py`'s `_build_favored_class_bonuses`
    (display) and `CharacterContext.favored_class_bonus_pick_counts` (so a
    handler whose daily allowance an ARG racial bonus augments, e.g.
    Entfesselter Barbar's Kampfrausch rounds/day in `rules/classes/
    barbarian.py`, can actually add it rather than only display it) need —
    shared here so `sheet.py`'s full-sheet build and `routers/characters.py`'s
    leaner `_ability_context` compute it identically instead of two
    independent implementations drifting apart. "hp"/"skill" picks never
    contribute — they're not `BaseClassOptionChoice` rows at all (folded
    directly into HP/skill ranks already)."""
    return Counter(
        option.choice_id
        for option in character.class_options
        if option.group_key == "favored_class_bonus" and option.choice_id is not None
    )


def _fraction_bonus(pick_count: int, *, numerator: int, denominator: int, max_bonus: int | None = None) -> int:
    """The current whole-number bonus from `pick_count` picks of a
    `numerator`/`denominator`-per-pick option (e.g. Paladin's +1/3 per pick,
    capped at +5) — floor division, since a fractional remainder grants
    nothing until the next pick completes it. `numerator > denominator`
    expresses a flat per-pick bonus (e.g. Kämpfer's +2/pick is
    `numerator=2, denominator=1`), same formula, no special case needed."""
    bonus = (pick_count * numerator) // denominator
    return bonus if max_bonus is None else min(bonus, max_bonus)


HANDLERS: dict[UUID, Callable[[int], int]] = {
    BARBAR: functools.partial(_fraction_bonus, numerator=1, denominator=1),
    ENTFESSELTER_BARBAR: functools.partial(_fraction_bonus, numerator=1, denominator=1),
    BARDE: functools.partial(_fraction_bonus, numerator=1, denominator=1),
    DRUIDE: functools.partial(_fraction_bonus, numerator=1, denominator=3),
    HEXENMEISTER: functools.partial(_fraction_bonus, numerator=1, denominator=2),
    KAEMPFER: functools.partial(_fraction_bonus, numerator=2, denominator=1),
    KLERIKER: functools.partial(_fraction_bonus, numerator=1, denominator=2),
    MAGIER: functools.partial(_fraction_bonus, numerator=1, denominator=1),
    PALADIN: functools.partial(_fraction_bonus, numerator=1, denominator=3, max_bonus=5),
    SCHURKE: functools.partial(_fraction_bonus, numerator=1, denominator=3, max_bonus=5),
    WALDLAEUFER: functools.partial(_fraction_bonus, numerator=1, denominator=1),
}

# Short, button-sized labels for the level-up wizard's picker chips — the
# full rules text (`sheet.py`'s `_favored_class_bonus_descriptions`) doesn't
# fit there and used to only surface on hover, which the project owner found
# less clear than a short always-visible label (2026-08-16). Purely a
# display convenience, not new rules content, so it lives here as plain
# strings rather than earning its own schema column (CLAUDE.md's "don't grow
# ad hoc columns per exception" is about *computation* shape, not UI text).
SHORT_LABELS: dict[UUID, str] = {
    BARBAR: "+1 Rd. Kampfrausch/Tag",
    ENTFESSELTER_BARBAR: "+1 Rd. Kampfrausch/Tag",
    BARDE: "+1 Rd. Bardenauftritt/Tag",
    DRUIDE: "+1/3 Rüstung (Tiergestalt)",
    HEXENMEISTER: "+1/2 Feuerschaden (Zauber)",
    KAEMPFER: "+2 Stabilisierung",
    KLERIKER: "+1/2 Domänenfähigkeit/Tag",
    MAGIER: "+1 Konzentration (bei Schaden)",
    MOENCH: "+1 KMV, +1/2 Betäub. Schlag",
    MYSTIKER: "+1 bekannter Zauber",
    PALADIN: "+1/3 Krit.-Bestätigung (Niederstrecken)",
    SCHURKE: "+1/3 Krit.-Bestätigung (Hinterhalt)",
    WALDLAEUFER: "+1 TP Gefährte",
}
