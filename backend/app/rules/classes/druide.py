"""Druide (Druid) — roadmap slice 10, step 0a (`scripts/import_druide.py`).

- "Naturgespür" (`HANDLERS`): +2 on Wissen (Natur) and Überlebenskunst.
- "Tiergestalt" (`DAILY_LIMITS` + `FEATURE_SUMMARY_HANDLERS`): uses/day and
  which form spells the current Druide level unlocks. The forms themselves
  (Bestiengestalt/Elementargestalt/Pflanzengestalt stats) are not applied
  yet — descriptive, per the roadmap.
- "Tierempathie" (`FEATURE_SUMMARY_HANDLERS`): one ability row shared with
  the Waldläufer (decided 2026-10-14), so the bonus sums the levels of every
  class that grants it. Lives here rather than in a Waldläufer file because
  the Waldläufer has no class module of its own yet.
- "Umgang mit Waffen und Rüstungen" (`WEAPON_PROFICIENCY_HANDLERS`): the
  Druide's named weapon list doesn't match a category feat (two of the ten
  are martial), so it resolves to exact `BaseItem` ids, the same shape as
  Elf's "Elfische Waffenvertrautheit" (`rules/race_abilities.py`). Armor/
  shield proficiency is ordinary `BaseClassAbilityGrantedFeat` data.

Everything else the Druide gets (Unterholz durchqueren, Spurloser Schritt,
Lockruf der Natur widerstehen, Immunität gegen Gifte, ...) is descriptive."""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..modifiers import Modifier, ModifierTarget
from ..progression import ability_mod

DRUIDE_ROOT_CLASS_ID = UUID("2835c712-7129-41fe-a61e-8ef05de2e0cf")
WALDLAEUFER_ROOT_CLASS_ID = UUID("91ab69e8-7ab5-46de-af7f-292f585645b4")

NATURGESPUER_ABILITY_ID = UUID("27df2b87-4cb4-5b9b-86a4-39c5454e785c")
TIERGESTALT_ABILITY_ID = UUID("248a0b40-17ab-5124-a2bc-cf50e76692e1")
UMGANG_MIT_WAFFEN_ABILITY_ID = UUID("88dde2d5-5916-53eb-9a5d-1caeafce2c5f")
# The Waldläufer's existing row, granted to the Druide as well.
TIEREMPATHIE_ABILITY_ID = UUID("ebd5060b-066a-4bc0-bdfa-064222de85bf")

_WISSEN_NATUR_SKILL_ID = UUID("0f6a271e-7eda-4d06-bdf8-8148a2c947ff")
_UEBERLEBENSKUNST_SKILL_ID = UUID("1b9fe08d-09e0-46c8-8772-dd573cab6fff")

DRUIDE_WEAPON_IDS = frozenset(
    UUID(item_id)
    for item_id in (
        "248d13cd-51fd-470b-8d88-cb63e7f15e46",  # Dolch
        "a5c2cbb1-7c1b-59e0-a8a9-bcba0636f3d0",  # Kampfstab
        "057662cc-c71d-5021-8da0-1f0f553acb9c",  # Keule
        "25994f9d-92fe-5dc6-bfff-5e4646899bb5",  # Krummsäbel
        "1449389b-2d5b-5a4d-9f9a-b84ad5568353",  # Kurzspeer
        "09a718cb-3012-4617-a7fb-376b1ad100ba",  # Schleuder
        "813e2ff6-5978-5a98-878e-e3a13689219e",  # Sichel
        "6e9d28f6-1170-51e1-9805-ec800d523668",  # Sense
        "d1887a60-0a90-4692-b957-7d4620207a40",  # Speer
        "8ef324a2-3c0c-5c0a-8453-a6efb0878a9b",  # Wurfpfeil
    )
)

# Every root class whose own grant of `TIEREMPATHIE_ABILITY_ID` makes its
# levels count toward the check ("Druidenstufe" / "Waldläuferstufe").
_TIEREMPATHIE_CLASS_IDS = (DRUIDE_ROOT_CLASS_ID, WALDLAEUFER_ROOT_CLASS_ID)

# Tiergestalt at 20th level is "jederzeit" — `DAILY_LIMITS` has no unlimited
# sentinel, so the 20th-level value is simply larger than any table could
# use up; the feature summary says "beliebig oft" instead of the number.
TIERGESTALT_UNLIMITED_USES = 99

# (from Druide level, forms the PRD adds at that level)
_TIERGESTALT_FORMS: tuple[tuple[int, str], ...] = (
    (4, "Bestiengestalt I"),
    (6, "Bestiengestalt II"),
    (6, "Elementargestalt I"),
    (8, "Bestiengestalt III"),
    (8, "Elementargestalt II"),
    (8, "Pflanzengestalt I"),
    (10, "Elementargestalt III"),
    (10, "Pflanzengestalt II"),
    (12, "Elementargestalt IV"),
    (12, "Pflanzengestalt III"),
)


def _druide_level(context: CharacterContext) -> int:
    return context.level_counts_by_root_id.get(DRUIDE_ROOT_CLASS_ID, 0)


def _naturgespuer(context: CharacterContext) -> list[Modifier]:
    del context
    return [
        Modifier(source="Naturgespür", type="untyped", value=2, target=ModifierTarget.SKILL, target_id=str(skill_id))
        for skill_id in (_WISSEN_NATUR_SKILL_ID, _UEBERLEBENSKUNST_SKILL_ID)
    ]


def tiergestalt_uses_per_day(context: CharacterContext) -> int:
    """1/Tag at 4th, +1 at 6th and every two levels after, max 8 at 18th;
    unlimited at 20th."""
    level = _druide_level(context)
    if level >= 20:
        return TIERGESTALT_UNLIMITED_USES
    if level < 4:
        return 0
    return min(8, (level - 4) // 2 + 1)


def _tiergestalt_summary(context: CharacterContext) -> str:
    level = _druide_level(context)
    uses = "beliebig oft" if level >= 20 else f"{tiergestalt_uses_per_day(context)}/Tag"
    # A later form of the same spell family replaces the earlier one
    # (Bestiengestalt III supersedes I/II), so keep only the highest per family.
    best_by_family: dict[str, str] = {}
    for min_level, form in _TIERGESTALT_FORMS:
        if level >= min_level:
            best_by_family[form.rsplit(" ", 1)[0]] = form
    return f"{uses}, Dauer {level} Std.; wie {', '.join(best_by_family.values())}"


def tierempathie_bonus(context: CharacterContext) -> int:
    class_levels = sum(context.level_counts_by_root_id.get(class_id, 0) for class_id in _TIEREMPATHIE_CLASS_IDS)
    return class_levels + ability_mod(context.ability_scores.get("CH", 10))


def _tierempathie_summary(context: CharacterContext) -> str:
    bonus = tierempathie_bonus(context)
    return f"1W20 {'+' if bonus >= 0 else '−'} {abs(bonus)} (magische Bestien mit IN 1–2: zusätzlich −4)"


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    NATURGESPUER_ABILITY_ID: _naturgespuer,
}
DAILY_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    TIERGESTALT_ABILITY_ID: tiergestalt_uses_per_day,
}
DAILY_LIMIT_UNIT_LABEL: dict[UUID, str] = {
    TIERGESTALT_ABILITY_ID: "Anwendungen",
}
WEAPON_PROFICIENCY_HANDLERS: dict[UUID, frozenset[UUID]] = {
    UMGANG_MIT_WAFFEN_ABILITY_ID: DRUIDE_WEAPON_IDS,
}
FEATURE_SUMMARY_HANDLERS: dict[UUID, Callable[[CharacterContext], str]] = {
    TIERGESTALT_ABILITY_ID: _tiergestalt_summary,
    TIEREMPATHIE_ABILITY_ID: _tierempathie_summary,
}
