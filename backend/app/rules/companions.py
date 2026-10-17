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
from .modifiers import Modifier, ModifierTarget

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
