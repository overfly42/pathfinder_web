"""Druide (Druid) — roadmap slice 10, step 0a (`scripts/import_druide.py`).

- "Naturgespür" (`HANDLERS`): +2 on Wissen (Natur) and Überlebenskunst.
- "Tiergestalt" (`DAILY_LIMITS` + `FEATURE_SUMMARY_HANDLERS`): uses/day and
  which form spells the current Druide level unlocks. The forms themselves
  (Bestiengestalt/Elementargestalt/Pflanzengestalt stats) are not applied
  yet — descriptive, per the roadmap.
- "Tierempathie" (`FEATURE_SUMMARY_HANDLERS`): one ability row shared with
  the Waldläufer (decided 2026-10-14) and the Jäger, so the bonus sums the
  levels of every class that grants it. Lives here rather than in a Waldläufer file because
  the Waldläufer has no class module of its own yet.
- "Umgang mit Waffen und Rüstungen" (`WEAPON_PROFICIENCY_HANDLERS`): the
  Druide's named weapon list doesn't match a category feat (two of the ten
  are martial), so it resolves to exact `BaseItem` ids, the same shape as
  Elf's "Elfische Waffenvertrautheit" (`rules/race_abilities.py`). Armor/
  shield proficiency is ordinary `BaseClassAbilityGrantedFeat` data.

Tierschamanen (Bärenschamane, Löwenschamane — see their block below):
Totemverwandlung as a minute pool with one activatable ability per aspect,
the delayed Tiergestalt.

Everything else the Druide gets (Unterholz durchqueren, Spurloser Schritt,
Lockruf der Natur widerstehen, Immunität gegen Gifte, ...) is descriptive."""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..modifiers import Modifier, ModifierTarget, NaturalAttack
from ..progression import ability_mod

DRUIDE_ROOT_CLASS_ID = UUID("2835c712-7129-41fe-a61e-8ef05de2e0cf")
WALDLAEUFER_ROOT_CLASS_ID = UUID("91ab69e8-7ab5-46de-af7f-292f585645b4")
JAEGER_ROOT_CLASS_ID = UUID("022e365e-1869-506f-8c77-88e85910b35f")

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
# levels count toward the check ("Druidenstufe" / "Waldläuferstufe" /
# "Jägerstufe", `scripts/import_jaeger.py`).
_TIEREMPATHIE_CLASS_IDS = (DRUIDE_ROOT_CLASS_ID, WALDLAEUFER_ROOT_CLASS_ID, JAEGER_ROOT_CLASS_ID)

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
    return tiergestalt_uses_at(_druide_level(context))


def tiergestalt_uses_at(level: int) -> int:
    if level >= 20:
        return TIERGESTALT_UNLIMITED_USES
    if level < 4:
        return 0
    return min(8, (level - 4) // 2 + 1)


def _tiergestalt_summary(context: CharacterContext) -> str:
    return _tiergestalt_summary_at(_druide_level(context))


def _tiergestalt_summary_at(level: int) -> str:
    uses = "beliebig oft" if level >= 20 else f"{tiergestalt_uses_at(level)}/Tag"
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


# ---- Tierschamanen (Bärenschamane, Löwenschamane; `scripts/import_druide_tierschamanen.py`) ----
# Totemverwandlung: a pool of Druide-level minutes per day; every aspect is
# its own activatable ability spending one minute from it (10 rounds).
# Tiergestalt comes at 6th with Druide level −2 (+2 in the totem animal's
# form, a read-out). One aspect at a time isn't enforced.
BAER_TOTEMVERWANDLUNG_ID = UUID("1ccc5c25-15eb-55f9-b075-b514eff16a10")
BAER_BEWEGUNG_ID = UUID("0babf5d4-5772-5239-a43b-f34e3164231f")
BAER_SINNE_ID = UUID("acc6ab02-2354-57f7-b2f5-88a781f7b622")
BAER_ABHAERTUNG_ID = UUID("ca48ccb8-87ed-580e-9147-6f91f1fce375")
BAER_WAFFEN_ID = UUID("cd1e83b9-53a5-5f05-94a4-17fbcc1d0f8c")
BAER_TIERGESTALT_ID = UUID("1efe331d-877b-5f40-b323-a73632e9fadf")
BAER_BONUSTALENT_ID = UUID("a812ac64-7230-5c38-8e09-9a2b5d529d32")
LOEWE_TOTEMVERWANDLUNG_ID = UUID("e343a32b-b6d6-5b42-8642-40bfa2ff6e6d")
LOEWE_BEWEGUNG_ID = UUID("ffeec0d2-22d6-5a57-b10a-ba1a8f5317a9")
LOEWE_SINNE_ID = UUID("9ae79766-329b-5bf3-a81a-1c9a6c8e19f6")
LOEWE_WAFFEN_ID = UUID("9af8cdd2-cef3-5e56-b1db-762a50588b91")
LOEWE_TIERGESTALT_ID = UUID("2d8f2af4-37e2-561a-b88e-acff4ed052be")
LOEWE_BONUSTALENT_ID = UUID("d4399098-c304-5918-9687-61d8459ccecf")
_SCHWIMMEN_SKILL_ID = "e5fa3283-96aa-49ee-8836-ba3062bae32d"
_SHAMAN_TIERGESTALT_OFFSET = -2
_TOTEM_FORMS = {BAER_TIERGESTALT_ID: "Bären", LOEWE_TIERGESTALT_ID: "katzenartiger"}


def _shaman_tiergestalt_uses(context: CharacterContext) -> int:
    level = _druide_level(context)
    return tiergestalt_uses_at(level + _SHAMAN_TIERGESTALT_OFFSET) if level >= 6 else 0


def _shaman_tiergestalt_summary(ability_id: UUID) -> Callable[[CharacterContext], str]:
    def summary(context: CharacterContext) -> str:
        level = _druide_level(context) + _SHAMAN_TIERGESTALT_OFFSET
        return (
            f"{_tiergestalt_summary_at(level)} (effektive Druidenstufe {level}; in {_TOTEM_FORMS[ability_id]} "
            f"Gestalt {level + 4})"
        )

    return summary


def _while_active(
    ability_id: UUID, handler: Callable[[CharacterContext], list[Modifier]]
) -> Callable[[CharacterContext], list[Modifier]]:
    """An aspect only counts while its own effect is active — the ability
    is granted from 2nd level, so the granted-ability paths call it too."""
    return lambda context: handler(context) if context.has_active(ability_id) else []


def _speed_bonus(source: str, value: int) -> Callable[[CharacterContext], list[Modifier]]:
    return lambda _context: [Modifier(source=source, type="enhancement", value=value, target=ModifierTarget.SPEED)]


def _baer_bewegung(context: CharacterContext) -> list[Modifier]:
    return _speed_bonus("Totemverwandlung (Bewegung)", 3)(context) + [
        Modifier(
            source="Totemverwandlung (Bewegung)",
            type="racial",
            value=4,
            target=ModifierTarget.SKILL,
            target_id=_SCHWIMMEN_SKILL_ID,
        )
    ]


def _baer_abhaertung(context: CharacterContext) -> list[Modifier]:
    del context
    return [Modifier(source="Totemverwandlung (Abhärtung)", type="natural", value=2, target=ModifierTarget.AC)]


def _totem_weapons(bite_dice: str, ability_id: UUID) -> Callable[[CharacterContext], list[NaturalAttack]]:
    """Bite and two claws while the aspect is active (dice for a Medium
    shaman, `sheet.py` scales them by size)."""

    def attacks(context: CharacterContext) -> list[NaturalAttack]:
        if not context.has_active(ability_id):
            return []
        return [
            NaturalAttack(name="Biss", count=1, damage_dice=bite_dice, damage_type="H/S/W"),
            NaturalAttack(name="Klauen", count=2, damage_dice="1W4", damage_type="H/W"),
        ]

    return attacks


HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    NATURGESPUER_ABILITY_ID: _naturgespuer,
    BAER_BEWEGUNG_ID: _while_active(BAER_BEWEGUNG_ID, _baer_bewegung),
    BAER_ABHAERTUNG_ID: _while_active(BAER_ABHAERTUNG_ID, _baer_abhaertung),
    LOEWE_BEWEGUNG_ID: _while_active(LOEWE_BEWEGUNG_ID, _speed_bonus("Totemverwandlung (Bewegung)", 6)),
}
NATURAL_ATTACK_HANDLERS: dict[UUID, Callable[[CharacterContext], list[NaturalAttack]]] = {
    BAER_WAFFEN_ID: _totem_weapons("1W6", BAER_WAFFEN_ID),
    LOEWE_WAFFEN_ID: _totem_weapons("1W4", LOEWE_WAFFEN_ID),
}
POOL_SOURCE_ID: dict[UUID, UUID] = {
    **{aspect: BAER_TOTEMVERWANDLUNG_ID for aspect in (BAER_BEWEGUNG_ID, BAER_SINNE_ID, BAER_ABHAERTUNG_ID, BAER_WAFFEN_ID)},
    **{aspect: LOEWE_TOTEMVERWANDLUNG_ID for aspect in (LOEWE_BEWEGUNG_ID, LOEWE_SINNE_ID, LOEWE_WAFFEN_ID)},
}
POOL_COST_AT_ACTIVATION: dict[UUID, int] = {aspect: 1 for aspect in POOL_SOURCE_ID}
DAILY_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    TIERGESTALT_ABILITY_ID: tiergestalt_uses_per_day,
    BAER_TOTEMVERWANDLUNG_ID: _druide_level,
    LOEWE_TOTEMVERWANDLUNG_ID: _druide_level,
    BAER_TIERGESTALT_ID: _shaman_tiergestalt_uses,
    LOEWE_TIERGESTALT_ID: _shaman_tiergestalt_uses,
    # Every aspect draws on its pool (`POOL_SOURCE_ID`) and needs the pool's
    # size as its own entry (`rules/daily_limits.py`'s docstring).
    **{aspect: _druide_level for aspect in POOL_SOURCE_ID},
}
DAILY_LIMIT_UNIT_LABEL: dict[UUID, str] = {
    TIERGESTALT_ABILITY_ID: "Anwendungen",
    BAER_TOTEMVERWANDLUNG_ID: "Minuten",
    LOEWE_TOTEMVERWANDLUNG_ID: "Minuten",
    BAER_TIERGESTALT_ID: "Anwendungen",
    LOEWE_TIERGESTALT_ID: "Anwendungen",
}
WEAPON_PROFICIENCY_HANDLERS: dict[UUID, frozenset[UUID]] = {
    UMGANG_MIT_WAFFEN_ABILITY_ID: DRUIDE_WEAPON_IDS,
}
FEATURE_SUMMARY_HANDLERS: dict[UUID, Callable[[CharacterContext], str]] = {
    TIERGESTALT_ABILITY_ID: _tiergestalt_summary,
    TIEREMPATHIE_ABILITY_ID: _tierempathie_summary,
    BAER_TIERGESTALT_ID: _shaman_tiergestalt_summary(BAER_TIERGESTALT_ID),
    LOEWE_TIERGESTALT_ID: _shaman_tiergestalt_summary(LOEWE_TIERGESTALT_ID),
}
