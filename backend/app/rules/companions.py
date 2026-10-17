"""Effective master level per companion track — roadmap slice 10, step 1
(thin: there are no companion characters yet; this only computes and
explains the level a companion *would* have).

Which sources exist, what triggers them and their offsets is data
(`BaseCompanionLevelSource`); this module only sums them:

- A source counts while its trigger is granted — a class ability in
  `context.granted_ability_ids` (real levels and the Sekundärklasse track
  alike: `rules/secondary_class.py` already puts a tier's ability and a
  synthetic class level into the context, so a Sekundärklasse needs no
  source of its own) or a feat in `context.feat_ids`.
- Contributions of one track add up (PF1e: companion levels from several
  sources stack); sources sharing a `stack_group` count only their highest.
- A track only exists when at least one non-flat source counts — a lone
  flat bonus (Stallmeister) without any companion gives no companion.
- The total is capped at the character level, after flat bonuses.

`COMPANION_LEVEL_HANDLERS` (keyed by the source row's id) replaces the
formula for a source whose rule doesn't fit the columns.

Step 3 adds the master → companion channel at the end of this module:
`COMPANION_MODIFIER_HANDLERS`/`COMPANION_NOTE_HANDLERS`, keyed by the
master's favored-class-bonus choice or granted ability id and resolved
against the companion's own context (which carries the master's raw
composition, `CharacterContext.master_*`)."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from .context import CharacterContext
from .modifiers import Modifier, ModifierTarget, SkillNote

TRACKS = ("animal_companion", "familiar")
TRACK_LABELS = {"animal_companion": "Tiergefährte/Reittier", "familiar": "Vertrauter"}

KLERIKER_ROOT_CLASS_ID = UUID("1e6e60de-d72f-4910-b19d-55ca11e14190")
DRUIDE_ROOT_CLASS_ID = UUID("2835c712-7129-41fe-a61e-8ef05de2e0cf")
# The Kleriker's "Domäne der Tiere" source (`base_companion_level_sources.json`)
# and its trigger ability "Tiergefährte" (granted at level 4 by the Kleriker's
# own domain choice and by the Druide's `nature_domain` choice).
KLERIKER_TIERE_SOURCE_ID = UUID("b9bbb83b-7db6-5b21-9cb7-1f630016d6d6")
TIERE_DOMAIN_COMPANION_ABILITY_ID = UUID("38fe2b58-a26e-5733-b9db-3a61baf89508")


class LevelSource(Protocol):
    """The `BaseCompanionLevelSource` columns this module reads — a
    protocol so tests can pass plain objects."""

    id: UUID
    track: str
    label: str
    class_ability_id: UUID | None
    feat_id: UUID | None
    kind: str
    root_class_id: UUID | None
    offset: int
    divisor: int
    minimum: int | None
    stack_group: str | None


@dataclass(frozen=True)
class LevelContribution:
    label: str
    value: int
    # How `value` came about, e.g. "Waldläufer 6 − 3" — `None` for a flat bonus.
    detail: str | None = None


@dataclass(frozen=True)
class TrackLevel:
    track: str
    level: int
    uncapped: int
    contributions: tuple[LevelContribution, ...]


def _formula(level: int, source: LevelSource) -> int:
    """Same shape as `rules/secondary_class.py`'s `secondary_effective_level`,
    never below 0."""
    value = (level + source.offset) // source.divisor
    if source.minimum is not None:
        value = max(value, source.minimum)
    return max(0, value)


def _formula_detail(name: str, level: int, source: LevelSource) -> str:
    text = f"{name} {level}"
    if source.offset:
        text += f" {'+' if source.offset > 0 else '−'} {abs(source.offset)}"
    if source.divisor != 1:
        text = f"({text}) / {source.divisor}"
    if source.minimum is not None:
        text += f", mind. {source.minimum}"
    return text


def _is_triggered(source: LevelSource, context: CharacterContext) -> bool:
    if source.class_ability_id is not None:
        return context.granted_ability_ids.get(source.class_ability_id, 0) > 0
    return source.feat_id in context.feat_ids


def _contribution(
    source: LevelSource, context: CharacterContext, class_names: dict[UUID, str]
) -> LevelContribution:
    handler = COMPANION_LEVEL_HANDLERS.get(source.id)
    if handler is not None:
        value, detail = handler(source, context, class_names)
        return LevelContribution(source.label, value, detail)
    if source.kind == "flat_bonus":
        return LevelContribution(source.label, source.offset)
    if source.kind == "character_level":
        level = context.character_level
        return LevelContribution(source.label, _formula(level, source), _formula_detail("Stufe", level, source))
    level = context.level_counts_by_root_id.get(source.root_class_id, 0)
    name = class_names.get(source.root_class_id, source.label)
    return LevelContribution(source.label, _formula(level, source), _formula_detail(name, level, source))


def master_effective_level(
    track: str, sources: Iterable[LevelSource], context: CharacterContext, class_names: dict[UUID, str]
) -> TrackLevel | None:
    """The effective master level for `track` ("effektive Druidenstufe" for
    an animal companion, "Magierstufe" for a familiar), or `None` if no
    source of this track grants the character a companion at all.
    `class_names` maps root class ids to display names for the breakdown."""
    triggered = [s for s in sources if s.track == track and _is_triggered(s, context)]
    if not any(s.kind != "flat_bonus" for s in triggered):
        return None

    best_by_group: dict[str, tuple[LevelSource, LevelContribution]] = {}
    contributions: list[LevelContribution] = []
    for source in triggered:
        contribution = _contribution(source, context, class_names)
        if source.stack_group is None:
            contributions.append(contribution)
            continue
        current = best_by_group.get(source.stack_group)
        if current is None or contribution.value > current[1].value:
            best_by_group[source.stack_group] = (source, contribution)
    contributions += [contribution for _source, contribution in best_by_group.values()]

    uncapped = sum(c.value for c in contributions)
    return TrackLevel(
        track=track,
        level=min(uncapped, context.character_level),
        uncapped=uncapped,
        contributions=tuple(contributions),
    )


def _tiere_domain_companion(
    source: LevelSource, context: CharacterContext, class_names: dict[UUID, str]
) -> tuple[int, str]:
    """"Die angewandte Druidenstufe für diese Fähigkeit entspricht deiner
    Klerikerstufe −3. (Druiden, die diese Fähigkeit über ihren Bund der
    Natur erhalten, rechnen mit ihrer Druidenstufe −3 …)" — the class that
    actually granted the ability decides whose level counts; a character who
    has it from both sums the two, like any two sources would."""
    granting = context.granting_root_ids_by_ability.get(TIERE_DOMAIN_COMPANION_ABILITY_ID, frozenset())
    roots = [r for r in (KLERIKER_ROOT_CLASS_ID, DRUIDE_ROOT_CLASS_ID) if r in granting] or [KLERIKER_ROOT_CLASS_ID]
    level = sum(context.level_counts_by_root_id.get(root, 0) for root in roots)
    name = " + ".join(class_names.get(root, "?") for root in roots)
    return _formula(level, source), _formula_detail(name, level, source)


COMPANION_LEVEL_HANDLERS: dict[
    UUID, Callable[[LevelSource, CharacterContext, dict[UUID, str]], tuple[int, str]]
] = {
    KLERIKER_TIERE_SOURCE_ID: _tiere_domain_companion,
}


# ---- master → companion channel (step 3) ----
# Keyed by the *master's* ids: a favored-class-bonus choice
# (`context.master_favored_class_bonus_pick_counts`) or a granted class
# ability (`context.master_granted_ability_ids`), resolved against the
# companion's own context, which carries the master's raw composition.

KATZENVOLK_DRUIDE_FCB_CHOICE_ID = UUID("52420b4d-1051-58da-bb7e-2897863d8697")
ORK_DRUIDE_FCB_CHOICE_ID = UUID("3a4f258f-0a67-5e92-835d-c260ca6239dc")
WALDLAEUFER_TIERGEFAEHRTE_ABILITY_ID = UUID("a98d91f5-2dff-506e-8bcc-03b3166ae731")
PALADIN_ROOT_CLASS_ID = UUID("561465fe-7c72-4e47-b58e-05a8dbbf0a3e")
PALADIN_REITTIER_ABILITY_ID = UUID("0028e0bb-6d8f-5051-bdb8-3f960dcf1009")


def _katzenvolk_druide(context: CharacterContext) -> list[Modifier]:
    """"Addiere +1 TP zu den TP des Tiergefährten des Druiden" per pick —
    a replacement companion gets them too, which holds by construction:
    the bonus is read from the master, never stored on the companion."""
    picks = context.master_favored_class_bonus_pick_counts.get(KATZENVOLK_DRUIDE_FCB_CHOICE_ID, 0)
    return [Modifier(source="Bevorzugte Klasse des Meisters", type="untyped", value=picks, target=ModifierTarget.HIT_POINTS)]


def _ork_druide(context: CharacterContext) -> list[Modifier]:
    """"Addiere +1/2 auf den Schaden der natürlichen Angriffe des
    Tiergefährten des Druiden" per pick, rounded down."""
    picks = context.master_favored_class_bonus_pick_counts.get(ORK_DRUIDE_FCB_CHOICE_ID, 0)
    return [
        Modifier(source="Bevorzugte Klasse des Meisters", type="untyped", value=picks // 2, target=ModifierTarget.NATURAL_DAMAGE)
    ]


def _paladin_mount(context: CharacterContext) -> list[Modifier]:
    """"Das Reittier besitzt eine Intelligenz von mindestens 6" — raises
    a lower IN to 6."""
    intelligence = context.ability_scores.get("IN", 10)
    if intelligence >= 6:
        return []
    return [Modifier(source="Göttlicher Bund", type="untyped", value=6 - intelligence, target=ModifierTarget.SCORE, target_id="IN")]


def _waldlaeufer_notes(context: CharacterContext) -> list[str]:
    """"… der die Boni des Waldläufers für Erzfeinde und bevorzugtes Gelände
    teilt" — the Waldläufer's own bonuses aren't computed yet, so the
    companion lists which ones it shares."""
    notes = []
    for key, label in (("enemy", "Erzfeinde"), ("terrain", "Bevorzugtes Gelände")):
        choices = context.master_class_options.get(key, ())
        if choices:
            notes.append(f"{label} des Waldläufers (Boni geteilt): {', '.join(choices)}")
    return notes


def _paladin_mount_notes(context: CharacterContext) -> list[str]:
    level = context.master_level_counts_by_root_id.get(PALADIN_ROOT_CLASS_ID, 0)
    notes = []
    if level >= 11:
        notes.append("Celestische Schablone; gilt für Zauber als magische Bestie")
    if level >= 15:
        notes.append(f"Zauberresistenz {level + 11}")
    return notes


COMPANION_MODIFIER_HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    KATZENVOLK_DRUIDE_FCB_CHOICE_ID: _katzenvolk_druide,
    ORK_DRUIDE_FCB_CHOICE_ID: _ork_druide,
    PALADIN_REITTIER_ABILITY_ID: _paladin_mount,
}
COMPANION_NOTE_HANDLERS: dict[UUID, Callable[[CharacterContext], list[str]]] = {
    WALDLAEUFER_TIERGEFAEHRTE_ABILITY_ID: _waldlaeufer_notes,
    PALADIN_REITTIER_ABILITY_ID: _paladin_mount_notes,
}


def _master_trigger_ids(context: CharacterContext) -> list[UUID]:
    return sorted(
        {*context.master_granted_ability_ids, *context.master_favored_class_bonus_pick_counts}, key=str
    )


def master_companion_modifiers(context: CharacterContext) -> list[Modifier]:
    """Every modifier the master's composition gives this companion."""
    modifiers: list[Modifier] = []
    for trigger_id in _master_trigger_ids(context):
        handler = COMPANION_MODIFIER_HANDLERS.get(trigger_id)
        if handler is not None:
            modifiers.extend(m for m in handler(context) if m.value)
    return modifiers


def master_companion_notes(context: CharacterContext) -> list[str]:
    """What the master shares with this companion that the sheet only
    describes."""
    notes: list[str] = []
    for trigger_id in _master_trigger_ids(context):
        handler = COMPANION_NOTE_HANDLERS.get(trigger_id)
        if handler is not None:
            notes.extend(handler(context))
    return notes


# ---- familiar (step 4) ----
# A familiar is fully derived from its master (`app/companions.py`): these
# are the fixed parts of the PRD's familiar rules (Grundregelwerk, Magier,
# "Die Werte des Vertrauten").

# "der Grundbonus des Vertrauten (REF +2, WIL +0, ZÄH +2)" — each save uses
# this or the master's base save, whichever is better.
FAMILIAR_BASE_SAVES = {"fort": 2, "ref": 2, "will": 0}
# "Vertraute haben Akrobatik, Fliegen, Heimlichkeit, Klettern, Schwimmen und
# Wahrnehmung als Klassenfertigkeiten."
AKROBATIK_SKILL_ID = UUID("61a2cb21-fcda-4a2d-8fb5-8ed12133c648")
KLETTERN_SKILL_ID = UUID("bf8d0e63-8a96-4a0e-baf9-06a1cac4e4c7")
FLIEGEN_SKILL_ID = UUID("a71cd8ed-15b2-4594-9819-0e320071513c")
HEIMLICHKEIT_SKILL_ID = UUID("432bdbaa-0286-4203-a117-1dbc4d68056b")
SCHWIMMEN_SKILL_ID = UUID("e5fa3283-96aa-49ee-8836-ba3062bae32d")
WAHRNEHMUNG_SKILL_ID = UUID("3d5d4e5f-c749-4346-a53b-2006bca05abb")
SCHAETZEN_SKILL_ID = UUID("791a87d6-c13a-4f44-bde4-fb39a46a462b")
BLUFFEN_SKILL_ID = UUID("144fa65e-50ce-4eb7-b861-177692a86858")
MOTIV_ERKENNEN_SKILL_ID = UUID("9a4debc2-0c8f-4461-9a37-bd667d8535ee")
FAMILIAR_CLASS_SKILL_IDS = frozenset(
    {AKROBATIK_SKILL_ID, FLIEGEN_SKILL_ID, HEIMLICHKEIT_SKILL_ID, KLETTERN_SKILL_ID, SCHWIMMEN_SKILL_ID,
     WAHRNEHMUNG_SKILL_ID}
)

# Familiar species (`scripts/import_familiars.py`) -> what its master gets
# (PRD Magier, "Vertrauter | Speziell"). `CharacterContext.familiar_species_ids`
# holds the species of the master's familiars.
AFFE_FAMILIAR_ID = UUID("f0a41379-239b-5e50-b0b4-7de50de0a9c5")
ECHSE_FAMILIAR_ID = UUID("ead06fb8-f1a9-5c89-bf74-ef22aa251f95")
EULE_FAMILIAR_ID = UUID("98fbec86-6576-5693-8c7e-cedf4f9d6871")
FALKE_FAMILIAR_ID = UUID("11e1a385-f650-57de-b7e1-e053bb58c8d0")
FLEDERMAUS_FAMILIAR_ID = UUID("955e40a6-3f74-5a99-ab9c-ea5003783795")
KATZE_FAMILIAR_ID = UUID("b7ac8152-a6f0-5cd0-b507-a8d0b7ab3918")
KROETE_FAMILIAR_ID = UUID("af001685-7195-5396-8bc3-1010337726fc")
RABE_FAMILIAR_ID = UUID("b6b9c6c1-1dac-5cfa-8ef0-189d86668ad4")
RATTE_FAMILIAR_ID = UUID("1b11e768-69c0-5741-8b55-401df238bfff")
VIPER_FAMILIAR_ID = UUID("32ae3a27-7f72-5bec-ba5c-91745dbd9d66")
WIESEL_FAMILIAR_ID = UUID("ab70c927-3049-52b1-8be8-023e7fd0b90d")

_FAMILIAR_SOURCE = "Vertrauter"


def _master_skill_bonus(skill_id: UUID, value: int = 3) -> Callable[[CharacterContext], list[Modifier]]:
    return lambda _context: [
        Modifier(source=_FAMILIAR_SOURCE, type="untyped", value=value, target=ModifierTarget.SKILL, target_id=str(skill_id))
    ]


def _master_bonus(target: ModifierTarget, value: int) -> Callable[[CharacterContext], list[Modifier]]:
    return lambda _context: [Modifier(source=_FAMILIAR_SOURCE, type="untyped", value=value, target=target)]


FAMILIAR_MASTER_HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    AFFE_FAMILIAR_ID: _master_skill_bonus(AKROBATIK_SKILL_ID),
    ECHSE_FAMILIAR_ID: _master_skill_bonus(KLETTERN_SKILL_ID),
    FLEDERMAUS_FAMILIAR_ID: _master_skill_bonus(FLIEGEN_SKILL_ID),
    KATZE_FAMILIAR_ID: _master_skill_bonus(HEIMLICHKEIT_SKILL_ID),
    KROETE_FAMILIAR_ID: _master_bonus(ModifierTarget.HIT_POINTS, 3),
    RABE_FAMILIAR_ID: _master_skill_bonus(SCHAETZEN_SKILL_ID),
    RATTE_FAMILIAR_ID: _master_bonus(ModifierTarget.SAVE_FORT, 2),
    VIPER_FAMILIAR_ID: _master_skill_bonus(BLUFFEN_SKILL_ID),
    WIESEL_FAMILIAR_ID: _master_bonus(ModifierTarget.SAVE_REF, 2),
}
# Situational master bonuses: Eule/Falke only for sight-based Wahrnehmung
# in their light conditions.
FAMILIAR_MASTER_SKILL_NOTES: dict[UUID, SkillNote] = {
    EULE_FAMILIAR_ID: SkillNote(
        skill_id=WAHRNEHMUNG_SKILL_ID,
        title="Vertrauter Eule (Sicht, in Dunkelheit oder dämmrigem Licht)",
        modifier_label="Vertrauter",
        value=3,
    ),
    FALKE_FAMILIAR_ID: SkillNote(
        skill_id=WAHRNEHMUNG_SKILL_ID,
        title="Vertrauter Falke (Sicht, bei Tageslicht)",
        modifier_label="Vertrauter",
        value=3,
    ),
}


def familiar_master_modifiers(context: CharacterContext) -> list[Modifier]:
    """What the master's familiars give the master unconditionally."""
    modifiers: list[Modifier] = []
    for species_id in sorted(context.familiar_species_ids, key=str):
        handler = FAMILIAR_MASTER_HANDLERS.get(species_id)
        if handler is not None:
            modifiers.extend(handler(context))
    return modifiers


def familiar_master_skill_notes(context: CharacterContext) -> list[SkillNote]:
    """The situational ones, plus every familiar's "Wachsamkeit": "Solange
    sich der Vertraute innerhalb einer Armeslänge vom Meister entfernt
    befindet, erhält dieser das Talent Wachsamkeit" (+2 Wahrnehmung and
    Motiv erkennen)."""
    if not context.familiar_species_ids:
        return []
    notes = [
        FAMILIAR_MASTER_SKILL_NOTES[species_id]
        for species_id in sorted(context.familiar_species_ids, key=str)
        if species_id in FAMILIAR_MASTER_SKILL_NOTES
    ]
    for skill_id in (WAHRNEHMUNG_SKILL_ID, MOTIV_ERKENNEN_SKILL_ID):
        notes.append(
            SkillNote(
                skill_id=skill_id,
                title="Wachsamkeit (Vertrauter in Armeslänge)",
                modifier_label="Wachsamkeit",
                value=2,
            )
        )
    return notes
