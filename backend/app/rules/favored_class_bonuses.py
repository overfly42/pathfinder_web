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

The ids below are the literal, hand-frozen `BaseClassOptionChoice` ids the
various per-race importers (`import_favored_class_bonus_halbork.py`, `_elf.py`,
`_katzenvolk.py`, Ork's own rows via `import_ork.py`) write (deterministic
`uuid5(ID_NAMESPACE, "fcb-choice|<base_class_id>")`, reproduced here as
literals since those scripts aren't importable at runtime — same convention
`rules/classes/barbarian.py` already uses for Seeräuber's ability id). A
row's id either equals one of these constants (and gets a handler here) or
it doesn't (and `sheet.py` falls back to showing only the pick count and
description text — Mönch's two-effects-per-pick and Mystiker's/Hexe's "+1
known spell" are exactly that case: not a single accumulating number, so no
handler, same "absent handler = flavor-only" convention `race_abilities.py`
already established for Darkvision).

2026-09-06: originally every constant here was one of Halb-Ork's own
choices, one per class. Several other races grant a *mechanically identical*
bonus for the same class under their own separate `BaseClassOptionChoice`
(scoped per race for the picker UI, per `routers/races.py`'s
`favored_class_bonus_race_choices`) — those now reuse the very same
`functools.partial(_fraction_bonus, ...)` instance rather than duplicating
the formula: Ork's own "Barbar" choice reuses `BARBAR`'s partial, Elf's own
"Druide"/"Kleriker" choices reuse `DRUIDE`'s/`KLERIKER`'s, Ork's own
"Waldläufer" choice reuses `WALDLAEUFER`'s. (The underlying
`BaseClassAbility` catalog rows for these were likewise consolidated to one
shared row per mechanic, keeping only the race-scoped `BaseClassOptionChoice`
rows separate — see `base_class_ability_grants.json`.)

Not yet given a handler, despite sharing a *shape* (not identical content,
so no catalog-row merge either):
- Kleriker (Halb-Ork/Elf, already merged above), Magier (Elf), and
  Hexenmeister (Elf/Katzenvolk, merged into one shared "Blutlinienkraft"
  row) all follow "choose a level-1 [domain/school/bloodline] power,
  normally usable (3+mod)/day, +1/2 daily use per pick" — the *fraction* is
  exactly `_fraction_bonus(numerator=1, denominator=2)`, same as `KLERIKER`
  already uses, but applying it for real needs to know *which specific
  power* the player chose (a sub-choice this project has no storage for yet,
  unlike e.g. Kensai's `CharacterClassAbilityWeaponChoice`) — a shared
  factory here would only get the number right, not where it applies.
- Waldläufer's Elf/Katzenvolk weapon-choice bonus ("+1/2 confirm-crit with a
  chosen weapon from a race-specific list, max +4") is `_fraction_bonus(
  numerator=1, denominator=2, max_bonus=4)` for both, but again needs a
  weapon sub-choice to actually apply to `_build_weapon_attacks` — same gap.
- Mystiker's (Halb-Ork/Katzenvolk, merged above) and Hexe's (Ork/Elf, merged
  above) "+1 known spell, grade < highest castable" bonuses are the other
  kind of gap: not parameterizable via `_fraction_bonus` at all (there is no
  running numeric total, the payoff is a whole extra spell pick) — see the
  separate Hexe/Mystiker "Zusätzlicher Zauber" design note."""

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

# Other races' own choices for a mechanically identical bonus — see module
# docstring's 2026-09-06 note. Each reuses its Halb-Ork sibling's exact
# `_fraction_bonus` partial/short label below rather than a new one.
ORK_BARBAR = UUID("bb5d2ece-b8e5-51e5-85d3-4f3233b0387e")
ELF_DRUIDE = UUID("0990b9a2-2461-5f4d-9871-fea995ea05c4")
ELF_KLERIKER = UUID("e91f9ce5-7ba6-5e8e-b3b4-968c3f38ad9a")
ORK_WALDLAEUFER = UUID("af331aea-194f-5a57-8458-c1b1bc496c9f")


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
    contribute — they *are* real `BaseClassOptionChoice` rows now too
    (`add_generic_favored_class_bonus_choices.py`), but they're excluded
    here by name on purpose: their effect is already folded directly into
    HP/skill ranks, so counting them here would surface two meaningless
    "hp"/"skill" entries in `sheet.py`'s `_build_favored_class_bonuses`
    display, which is meant for actual class features."""
    return Counter(
        option.choice_id
        for option in character.class_options
        if option.group_key == "favored_class_bonus"
        and option.choice_id is not None
        and option.choice not in ("hp", "skill")
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
    ORK_BARBAR: functools.partial(_fraction_bonus, numerator=1, denominator=1),
    ELF_DRUIDE: functools.partial(_fraction_bonus, numerator=1, denominator=3),
    ELF_KLERIKER: functools.partial(_fraction_bonus, numerator=1, denominator=2),
    ORK_WALDLAEUFER: functools.partial(_fraction_bonus, numerator=1, denominator=1),
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
    ORK_BARBAR: "+1 Rd. Kampfrausch/Tag",
    ELF_DRUIDE: "+1/3 Rüstung (Tiergestalt)",
    ELF_KLERIKER: "+1/2 Domänenfähigkeit/Tag",
    ORK_WALDLAEUFER: "+1 TP Gefährte",
}
