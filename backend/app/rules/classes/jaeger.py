"""Jäger (Hunter) and its archetypes (`scripts/import_jaeger.py`,
`scripts/import_jaeger_archetypes.py`).

- "Tieraspekt": a pool of Jäger-level minutes per day (`DAILY_LIMITS`, unit
  "Minuten"); every aspect is its own activatable ability spending one
  minute (`POOL_SOURCE_ID`/`POOL_COST_AT_ACTIVATION`, 10 rounds) — the same
  shape as the Tierschamanen's Totemverwandlung (`druide.py`). An aspect
  only counts while its effect is active. Computed: Affe/Eule/Falke/Frosch
  (competence bonus on Klettern/Heimlichkeit/Wahrnehmung/Schwimmen, +4/+6/+8
  at 1st/8th/15th), Bär/Stier/Tiger (enhancement bonus on KO/ST/GE,
  +2/+4/+6), Hirsch (enhancement bonus on land speed — only from 8th: the
  1,5 m below that isn't a whole meter, `PARTIAL_EFFECT_NOTES`). Fledermaus,
  Maus, Schlange and Wolf are senses/Entrinnen/attacks of opportunity — text.
  The companion's own aspect and the second aspect from 8th aren't tracked
  separately (one aspect at a time isn't enforced either).
- "Spuren lesen" (`SITUATIONAL_SKILL_HANDLERS`): ½ Jäger level on
  Überlebenskunst to follow tracks.
- Tierempathie is the row shared with Druide/Waldläufer (`druide.py` sums
  the Jäger's levels too).
- "Bonustricks": extra companion bonus tricks, counted by
  `rules/companions.py`'s `master_bonus_tricks`; the feature summary states
  how many.

Archetypes:
- Bruder des Urzeitgefährten: Urzeitliche Verwandlung as a Jäger-level
  minute pool (the evolutions are text), Urzeitlicher Kraftschub 1/day.
- Bruder des Ungeziefergefährten: Ungezieferaspekt — same pool shape as
  Tieraspekt; computed: Ameise (ST), Käfer (natural armor, typed
  "enhancement" like the Amulett der natürlichen Rüstung, `rules/items.py`),
  Fliege (Wahrnehmung, untyped), Krabbe (Schwimmen), Skorpion/Spinne
  (Heimlichkeit), Tausendfüßler (Klettern); their grapple/CMD/web parts are
  partial notes. Egel, Floh, Gottesanbeterin, Motte, Schabe and Wurm are
  situational or senses — text. Phasmid and Wespe stay text too: the PRD
  gives "+4, mit der 8. Stufe +4, mit der 15. Stufe +6", which can't be the
  intended progression (every sibling aspect rises by 2 per step).
  Ungezieferempathie: the Tierempathie bonus as a read-out ("nur
  Ungeziefer").
- Göttlicher Jäger: Wissen (Religion) as a class skill (`CLASS_SKILL_GRANTS`);
  Wissen (Gewölbekunde) stays one (no removal mechanism, partial note).
- Wilder Jäger: Wilder Aspekt's twelve aspects use the Tieraspekt handlers,
  without pool or duration. Tiergestalt at Jäger level (the Druide's
  uses-per-day table), animal forms only."""

from collections import Counter
from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext
from ..modifiers import Modifier, ModifierTarget, SkillNote
from ..progression import ability_mod
from ..skill_ids import KLETTERN_SKILL_ID, SCHWIMMEN_SKILL_ID, UEBERLEBENSKUNST_SKILL_ID
from .druide import JAEGER_ROOT_CLASS_ID, tiergestalt_uses_at

HEIMLICHKEIT_SKILL_ID = UUID("432bdbaa-0286-4203-a117-1dbc4d68056b")
WAHRNEHMUNG_SKILL_ID = UUID("3d5d4e5f-c749-4346-a53b-2006bca05abb")
WISSEN_RELIGION_SKILL_ID = UUID("11de822f-9662-476b-9023-d86989ab9d49")

TIERASPEKT_ID = UUID("17999fe9-c02a-5f34-95ee-4923db8c25e3")
SPUREN_LESEN_ID = UUID("9e31517a-3c9c-5750-b945-ea11b1a56160")
BONUSTRICKS_ID = UUID("75358fdb-0859-5b98-ab34-98a5846b17d6")
TIERGEFAEHRTE_ID = UUID("8d2f4782-0cfe-5064-bd79-15860dec8e5b")
GENAUES_AUSMANOEVRIEREN_ID = UUID("4e83821b-8851-5442-bf5e-1fc1bf57d8a5")
JAEGERTAKTIKEN_ID = UUID("3a04047a-d85c-5d11-9c3c-e819df0cfa28")
UNTERHOLZ_DURCHQUEREN_ID = UUID("d226f0f6-6966-570f-8882-0aa1c7289909")

# "Tieraspekt: <Tier>" and the Wilder Jäger's "Wilder Aspekt: <Tier>".
TIERASPEKT_ASPECT_IDS = {
    "Affe": UUID("fd7ab838-fd68-5c89-a79f-511ad267096c"),
    "Bär": UUID("83b5e62c-aca1-59b3-8289-8e5a2fd392bd"),
    "Eule": UUID("e431a9e9-adf3-589f-993b-66afcca1ae64"),
    "Falke": UUID("bc1ae8c2-82bd-53fd-b309-04cd97f39361"),
    "Fledermaus": UUID("cd4157a6-6e42-5f60-a27b-bb444ae010c3"),
    "Frosch": UUID("4d0f2de6-7860-587a-a1be-484575608dc0"),
    "Hirsch": UUID("bb58fd3b-9ede-5a48-aa59-92347cf4bc53"),
    "Maus": UUID("7768bdad-ffc0-5f8b-98a8-9f15cbf76730"),
    "Schlange": UUID("36e4ffef-5222-52da-9fbf-f43c134a560a"),
    "Stier": UUID("42ceecf5-0cae-5f11-976a-f3fa43bc14cc"),
    "Tiger": UUID("f55f84f2-4142-59e6-acf1-d0ff78bcf565"),
    "Wolf": UUID("c2940a3e-b919-5524-a18d-dde35997f493"),
}
WILDER_ASPEKT_IDS = {
    "Affe": UUID("09b6f0b7-60b9-5bc7-9165-c3ab2b459b3e"),
    "Bär": UUID("8b30208a-f483-58e1-85be-60695b3f3970"),
    "Eule": UUID("005563c6-d038-586b-9578-d9544af4d1fd"),
    "Falke": UUID("61827bd2-e5c3-59fa-bbee-5be42e5f83e7"),
    "Fledermaus": UUID("12347ae4-cd34-59b2-90be-16f1151dffb1"),
    "Frosch": UUID("56f74bf9-58a6-59c7-94b4-1dfdb8d04e1a"),
    "Hirsch": UUID("6ba2c8cb-1bf3-5a14-9f91-c4a2dd798cf0"),
    "Maus": UUID("d022dc39-cd17-5110-8354-bee95cf8ff5f"),
    "Schlange": UUID("a10716ff-d6cf-5c99-b5b5-b7b9ed83733c"),
    "Stier": UUID("16b68d67-1f10-5f8c-948c-3aa9428b6231"),
    "Tiger": UUID("21e452db-7c35-54c3-af83-c69c84c62aa3"),
    "Wolf": UUID("a2e5d570-6353-5ae6-8ae6-5f12df56c6c4"),
}

# Archetypes.
URZEITLICHE_VERWANDLUNG_ID = UUID("52502622-d8bd-5c81-a8d5-202de9ac1fee")
URZEITLICHER_KRAFTSCHUB_ID = UUID("453a73e3-15c6-55df-811c-977ec8d82732")
UNGEZIEFERASPEKT_ID = UUID("ab2648ba-67a1-5317-bae7-b170589818bc")
UNGEZIEFEREMPATHIE_ID = UUID("81152f8c-dba2-5fce-829c-bf580f33e9de")
UNGEZIEFERASPEKT_ASPECT_IDS = {
    "Ameise": UUID("78326772-f1aa-50c6-8b7f-af8ffa03acb3"),
    "Egel": UUID("3bec71e3-1303-5191-a6eb-8bf0403c3162"),
    "Fliege": UUID("30d6c9ed-d0ed-5800-9270-2a56dca5a5e2"),
    "Floh": UUID("01333ffd-1af3-5b26-95d3-34035ddb8ed0"),
    "Gottesanbeterin": UUID("ee27e3a8-6391-548b-89fc-c4e0c113c223"),
    "Käfer": UUID("39a039a0-1219-5e7f-b72f-500011a84a04"),
    "Krabbe": UUID("33e8d3f6-1a30-599a-ac07-5e9f61c2e1f2"),
    "Motte": UUID("043d652d-2cdd-57f5-a2fb-9fdf2a712151"),
    "Phasmid": UUID("03f14f09-e59f-553b-8932-b8688b498321"),
    "Schabe": UUID("33b0c647-d84a-5355-8727-150df4e72194"),
    "Skorpion": UUID("3e8aacf1-a924-59b5-a59b-2cbc0bdd1f1b"),
    "Spinne": UUID("6dd65039-9d17-5d5f-9afd-8b7f0e836e13"),
    "Tausendfüßler": UUID("ef6c2bb1-8553-54f9-bbff-66dbc5ef3735"),
    "Wespe": UUID("fa6d4342-068f-54d5-bf77-257f3fd5bbd2"),
    "Wurm": UUID("1462c315-961e-579e-bab8-aaded986e9d7"),
}
GOETTLICHER_JAEGER_KLASSENFERTIGKEITEN_ID = UUID("6cc7c7e9-ed05-5b03-bec2-78f3129aeb06")
AUSSERWELTLICHER_GEFAEHRTE_ID = UUID("144888a0-c297-515f-81d6-cc44c92d1873")
RUDELBINDUNG_ID = UUID("d8473cd2-cdac-5326-961b-ee39d8149d1d")
WILDE_TIERGESTALT_ID = UUID("f46377fe-1b2a-5ba2-bc92-fa313845b92f")

# "Tabelle: Druide"'s Bestiengestalt steps — the Wilder Jäger takes only
# animal forms ("nicht aber von Elementaren oder Pflanzen").
_ANIMAL_FORMS: tuple[tuple[int, str], ...] = ((4, "Bestiengestalt I"), (6, "Bestiengestalt II"), (8, "Bestiengestalt III"))


def jaeger_level(context: CharacterContext) -> int:
    return context.level_counts_by_root_id.get(JAEGER_ROOT_CLASS_ID, 0)


def _step(context: CharacterContext) -> int:
    """0 below 8th, 1 from 8th, 2 from 15th — every aspect's bonus rises at
    those two levels ("steigt mit der 8. Stufe … und mit der 15. Stufe")."""
    level = jaeger_level(context)
    return (level >= 8) + (level >= 15)


def _while_active(
    ability_id: UUID, handler: Callable[[CharacterContext], list[Modifier]]
) -> Callable[[CharacterContext], list[Modifier]]:
    """An aspect only counts while its own effect is active — it's granted
    from 1st level, so the granted-ability paths call it too."""
    return lambda context: handler(context) if context.has_active(ability_id) else []


def _skill_aspect(
    source: str, skill_id: UUID, base: int, bonus_type: str = "competence"
) -> Callable[[CharacterContext], list[Modifier]]:
    return lambda context: [
        Modifier(source=source, type=bonus_type, value=base + 2 * _step(context), target=ModifierTarget.SKILL,
                 target_id=str(skill_id))
    ]


def _score_aspect(source: str, ability: str) -> Callable[[CharacterContext], list[Modifier]]:
    return lambda context: [
        Modifier(source=source, type="enhancement", value=2 + 2 * _step(context), target=ModifierTarget.SCORE,
                 target_id=ability)
    ]


def _speed_aspect(source: str) -> Callable[[CharacterContext], list[Modifier]]:
    """+1,5 m / +3 m / +6 m — speeds are whole meters, so only from 8th."""

    def handler(context: CharacterContext) -> list[Modifier]:
        value = {0: 0, 1: 3, 2: 6}[_step(context)]
        return [Modifier(source=source, type="enhancement", value=value, target=ModifierTarget.SPEED)] if value else []

    return handler


def _natural_armor_aspect(source: str) -> Callable[[CharacterContext], list[Modifier]]:
    return lambda context: [
        Modifier(source=source, type="enhancement", value=2 + 2 * _step(context), target=ModifierTarget.AC)
    ]


def _animal_aspect_handlers(source: str) -> dict[str, Callable[[CharacterContext], list[Modifier]]]:
    return {
        "Affe": _skill_aspect(f"{source} (Affe)", KLETTERN_SKILL_ID, 4),
        "Bär": _score_aspect(f"{source} (Bär)", "KO"),
        "Eule": _skill_aspect(f"{source} (Eule)", HEIMLICHKEIT_SKILL_ID, 4),
        "Falke": _skill_aspect(f"{source} (Falke)", WAHRNEHMUNG_SKILL_ID, 4),
        "Frosch": _skill_aspect(f"{source} (Frosch)", SCHWIMMEN_SKILL_ID, 4),
        "Hirsch": _speed_aspect(f"{source} (Hirsch)"),
        "Stier": _score_aspect(f"{source} (Stier)", "ST"),
        "Tiger": _score_aspect(f"{source} (Tiger)", "GE"),
    }


_VERMIN_HANDLERS = {
    "Ameise": _score_aspect("Ungezieferaspekt (Ameise)", "ST"),
    "Fliege": _skill_aspect("Ungezieferaspekt (Fliege)", WAHRNEHMUNG_SKILL_ID, 2, "untyped"),
    "Käfer": _natural_armor_aspect("Ungezieferaspekt (Käfer)"),
    "Krabbe": _skill_aspect("Ungezieferaspekt (Krabbe)", SCHWIMMEN_SKILL_ID, 4),
    "Skorpion": _skill_aspect("Ungezieferaspekt (Skorpion)", HEIMLICHKEIT_SKILL_ID, 2),
    "Spinne": _skill_aspect("Ungezieferaspekt (Spinne)", HEIMLICHKEIT_SKILL_ID, 2),
    "Tausendfüßler": _skill_aspect("Ungezieferaspekt (Tausendfüßler)", KLETTERN_SKILL_ID, 2),
}


def _spuren_lesen(context: CharacterContext) -> list[SkillNote]:
    return [
        SkillNote(
            skill_id=UEBERLEBENSKUNST_SKILL_ID,
            title="Spuren lesen (um Spuren zu folgen)",
            modifier_label="Spuren lesen",
            value=jaeger_level(context) // 2,
        )
    ]


def _aspect_pool_summary(skill_base: int) -> Callable[[CharacterContext], str]:
    def summary(context: CharacterContext) -> str:
        step = _step(context)
        return (
            f"{jaeger_level(context)} Minuten/Tag; Fertigkeitsaspekte +{skill_base + 2 * step}, "
            f"Attributsaspekte +{2 + 2 * step}"
        )

    return summary


def _urzeit_summary(context: CharacterContext) -> str:
    return f"{jaeger_level(context)} Minuten/Tag; {2 + 2 * _step(context)} Evolutionspunkte"


def _ungezieferempathie_summary(context: CharacterContext) -> str:
    bonus = jaeger_level(context) + ability_mod(context.ability_scores.get("CH", 10))
    return f"1W20 {'+' if bonus >= 0 else '−'} {abs(bonus)} (nur Ungeziefer)"


def _bonustricks_summary(context: CharacterContext) -> str:
    count = context.granted_ability_ids[BONUSTRICKS_ID]
    return f"Tiergefährte: +{count} Bonustrick{'s' if count != 1 else ''}"


def _wilde_tiergestalt_uses(context: CharacterContext) -> int:
    return tiergestalt_uses_at(jaeger_level(context))


def _wilde_tiergestalt_summary(context: CharacterContext) -> str:
    level = jaeger_level(context)
    uses = "beliebig oft" if level >= 20 else f"{tiergestalt_uses_at(level)}/Tag"
    form = [name for min_level, name in _ANIMAL_FORMS if level >= min_level][-1]
    return f"{uses}, Dauer {level} Std.; wie {form} (nur Tiere)"


_animal_handlers = _animal_aspect_handlers("Tieraspekt")
_wild_handlers = _animal_aspect_handlers("Wilder Aspekt")

HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    **{TIERASPEKT_ASPECT_IDS[name]: _while_active(TIERASPEKT_ASPECT_IDS[name], h) for name, h in _animal_handlers.items()},
    **{WILDER_ASPEKT_IDS[name]: _while_active(WILDER_ASPEKT_IDS[name], h) for name, h in _wild_handlers.items()},
    **{
        UNGEZIEFERASPEKT_ASPECT_IDS[name]: _while_active(UNGEZIEFERASPEKT_ASPECT_IDS[name], h)
        for name, h in _VERMIN_HANDLERS.items()
    },
}
SITUATIONAL_SKILL_HANDLERS: dict[UUID, Callable[[CharacterContext], list[SkillNote]]] = {
    SPUREN_LESEN_ID: _spuren_lesen,
}
POOL_SOURCE_ID: dict[UUID, UUID] = {
    **{aspect: TIERASPEKT_ID for aspect in TIERASPEKT_ASPECT_IDS.values()},
    **{aspect: UNGEZIEFERASPEKT_ID for aspect in UNGEZIEFERASPEKT_ASPECT_IDS.values()},
}
POOL_COST_AT_ACTIVATION: dict[UUID, int] = {aspect: 1 for aspect in POOL_SOURCE_ID}
DAILY_LIMITS: dict[UUID, Callable[[CharacterContext], int]] = {
    TIERASPEKT_ID: jaeger_level,
    UNGEZIEFERASPEKT_ID: jaeger_level,
    URZEITLICHE_VERWANDLUNG_ID: jaeger_level,
    URZEITLICHER_KRAFTSCHUB_ID: lambda _context: 1,
    WILDE_TIERGESTALT_ID: _wilde_tiergestalt_uses,
    # Every aspect draws on its pool (`POOL_SOURCE_ID`) and needs the pool's
    # size as its own entry (`rules/daily_limits.py`'s docstring).
    **{aspect: jaeger_level for aspect in POOL_SOURCE_ID},
}
DAILY_LIMIT_UNIT_LABEL: dict[UUID, str] = {
    TIERASPEKT_ID: "Minuten",
    UNGEZIEFERASPEKT_ID: "Minuten",
    URZEITLICHE_VERWANDLUNG_ID: "Minuten",
    WILDE_TIERGESTALT_ID: "Anwendungen",
}
FEATURE_SUMMARY_HANDLERS: dict[UUID, Callable[[CharacterContext], str]] = {
    TIERASPEKT_ID: _aspect_pool_summary(4),
    UNGEZIEFERASPEKT_ID: _aspect_pool_summary(2),
    URZEITLICHE_VERWANDLUNG_ID: _urzeit_summary,
    UNGEZIEFEREMPATHIE_ID: _ungezieferempathie_summary,
    BONUSTRICKS_ID: _bonustricks_summary,
    WILDE_TIERGESTALT_ID: _wilde_tiergestalt_summary,
}
CLASS_SKILL_GRANTS: dict[UUID, frozenset[UUID]] = {
    GOETTLICHER_JAEGER_KLASSENFERTIGKEITEN_ID: frozenset({WISSEN_RELIGION_SKILL_ID}),
}
_HIRSCH_NOTE = "+1,5 m bis zur 7. Stufe nicht berechnet (Bewegungsraten in ganzen Metern); ab der 8. Stufe +3 m/+6 m"
PARTIAL_EFFECT_NOTES: dict[UUID, str] = {
    TIERASPEKT_ASPECT_IDS["Hirsch"]: _HIRSCH_NOTE,
    WILDER_ASPEKT_IDS["Hirsch"]: _HIRSCH_NOTE,
    UNGEZIEFERASPEKT_ASPECT_IDS["Fliege"]: "Akrobatik zum Gleichgewicht halten/Sturz abfangen nicht berechnet",
    UNGEZIEFERASPEKT_ASPECT_IDS["Krabbe"]: "Ringkampf-Kampfmanöverbonus nicht berechnet",
    UNGEZIEFERASPEKT_ASPECT_IDS["Skorpion"]: "Ringkampf-Kampfmanöverbonus nicht berechnet",
    UNGEZIEFERASPEKT_ASPECT_IDS["Spinne"]: "Rettungswürfe/Würfe gegen Spinnennetze nicht berechnet",
    UNGEZIEFERASPEKT_ASPECT_IDS["Tausendfüßler"]: "KMV gegen Versetzen/Zerren/Ziehen/Zu-Fall-bringen nicht berechnet",
    GOETTLICHER_JAEGER_KLASSENFERTIGKEITEN_ID: "Wissen (Gewölbekunde) bleibt Klassenfertigkeit",
}


def master_bonus_tricks(master_granted_ability_ids: Counter[UUID]) -> int:
    """"erlernt der Tiergefährte … einen zusätzlichen Bonustrick" — one per
    Bonustricks grant (7th, 13th, 19th)."""
    return master_granted_ability_ids[BONUSTRICKS_ID]
