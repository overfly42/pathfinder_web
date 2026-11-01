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

from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from . import favored_class_bonuses
from .classes import jaeger
from .context import CharacterContext
from .modifiers import Modifier, ModifierTarget, SkillNote

TRACKS =("animal_companion", "familiar")
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
MYSTIKER_REITTIER_ABILITY_ID = UUID("399600a9-0ff4-5988-a3dd-f94d88427bb7")


def _companion_hit_points(choice_id: UUID) -> Callable[[CharacterContext], list[Modifier]]:
    """+1 HP on the companion per pick (Katzenvolk Druide, Halb-Ork Jäger,
    Halb-Ork/Ork Waldläufer) —
    a replacement companion gets them too, which holds by construction:
    the bonus is read from the master, never stored on the companion."""

    def handler(context: CharacterContext) -> list[Modifier]:
        picks = context.master_favored_class_bonus_pick_counts.get(choice_id, 0)
        return [
            Modifier(source="Bevorzugte Klasse des Meisters", type="untyped", value=picks, target=ModifierTarget.HIT_POINTS)
        ]

    return handler


def _ork_druide(context: CharacterContext) -> list[Modifier]:
    """"Addiere +1/2 auf den Schaden der natürlichen Angriffe des
    Tiergefährten des Druiden" per pick, rounded down."""
    picks = context.master_favored_class_bonus_pick_counts.get(ORK_DRUIDE_FCB_CHOICE_ID, 0)
    return [
        Modifier(source="Bevorzugte Klasse des Meisters", type="untyped", value=picks // 2, target=ModifierTarget.NATURAL_DAMAGE)
    ]


def _mount_intelligence(context: CharacterContext) -> list[Modifier]:
    """Paladin: "Das Reittier besitzt eine Intelligenz von mindestens 6";
    Mystiker: "So gebundene Reittiere haben einen Intelligenzwert von
    mindestens 6" — raises a lower IN to 6."""
    intelligence = context.ability_scores.get("IN", 10)
    if intelligence >= 6:
        return []
    return [
        Modifier(source="Gebundenes Reittier", type="untyped", value=6 - intelligence, target=ModifierTarget.SCORE, target_id="IN")
    ]


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


def _jaeger_notes(text: str) -> Callable[[CharacterContext], list[str]]:
    return lambda _context: [text]


def _paladin_mount_notes(context: CharacterContext) -> list[str]:
    level = context.master_level_counts_by_root_id.get(PALADIN_ROOT_CLASS_ID, 0)
    notes = []
    if level >= 11:
        notes.append("Celestische Schablone; gilt für Zauber als magische Bestie")
    if level >= 15:
        notes.append(f"Zauberresistenz {level + 11}")
    return notes


COMPANION_MODIFIER_HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]] = {
    KATZENVOLK_DRUIDE_FCB_CHOICE_ID: _companion_hit_points(KATZENVOLK_DRUIDE_FCB_CHOICE_ID),
    favored_class_bonuses.HALBORK_JAEGER: _companion_hit_points(favored_class_bonuses.HALBORK_JAEGER),
    favored_class_bonuses.WALDLAEUFER: _companion_hit_points(favored_class_bonuses.WALDLAEUFER),
    favored_class_bonuses.ORK_WALDLAEUFER: _companion_hit_points(favored_class_bonuses.ORK_WALDLAEUFER),
    ORK_DRUIDE_FCB_CHOICE_ID: _ork_druide,
    PALADIN_REITTIER_ABILITY_ID: _mount_intelligence,
    MYSTIKER_REITTIER_ABILITY_ID: _mount_intelligence,
    **jaeger.COMPANION_MODIFIER_HANDLERS,
}
COMPANION_NOTE_HANDLERS: dict[UUID, Callable[[CharacterContext], list[str]]] = {
    WALDLAEUFER_TIERGEFAEHRTE_ABILITY_ID: _waldlaeufer_notes,
    PALADIN_REITTIER_ABILITY_ID: _paladin_mount_notes,
    # Jäger (`rules/classes/jaeger.py`): what the master's features give the
    # companion, as text — the master's feats aren't in the companion's
    # context. The aspects are computed (`COMPANION_MODIFIER_HANDLERS`), the
    # note names them.
    **jaeger.COMPANION_NOTE_HANDLERS,
    jaeger.GENAUES_AUSMANOEVRIEREN_ID: _jaeger_notes(
        "Genaues Ausmanövrieren: Ausmanövrieren als Talent, wenn der Jäger es gewählt hat"
    ),
    jaeger.JAEGERTAKTIKEN_ID: _jaeger_notes(
        "Jägertaktiken: erhält die Gemeinschaftstalente des Jägers, ohne ihre Voraussetzungen zu erfüllen"
    ),
    jaeger.UNTERHOLZ_DURCHQUEREN_ID: _jaeger_notes("Unterholz durchqueren (wie der Jäger)"),
    jaeger.AUSSERWELTLICHER_GEFAEHRTE_ID: _jaeger_notes(
        "Außerweltlicher Gefährte: Schablone Celestische oder Infernalische Kreatur (HG = Trefferwürfel)"
    ),
}


def master_bonus_tricks(master_granted_ability_ids: Counter[UUID]) -> int:
    """Bonus tricks the master's class features add on top of the
    progression row's `bonus_tricks` (the Jäger's Bonustricks)."""
    return jaeger.master_bonus_tricks(master_granted_ability_ids)


def _master_trigger_ids(context: CharacterContext) -> list[UUID]:
    return sorted(
        {*context.master_granted_ability_ids, *context.master_favored_class_bonus_pick_counts}, key=str
    )


def master_companion_modifiers(context: CharacterContext) -> list[Modifier]:
    """Every modifier the master's composition gives this companion — an
    animal companion or mount only; `sheet.py` doesn't call this for a
    familiar (a Halb-Ork Jäger's +1 HP per pick is for the Tiergefährte)."""
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


# ---- barding (Pferdeharnisch) ----
# Any armor a companion wears is barding (PRD Grundregelwerk, Ausrüstung,
# "Pferdeharnisch"). Its speed reduction is the general armor rule
# (`rules/armor.py`'s `armored_speed`, applied to every wearer); the one
# companion-only part is "Fliegende Reittiere können in einem mittelschweren
# oder schweren Pferdeharnisch nicht fliegen" (`sheet.py`).


# ---- tricks (step 5) ----
# PRD Grundregelwerk, Fertigkeiten, Mit Tieren umgehen. Which tricks and
# trainings exist (and what a trick requires) is data
# (`BaseCompanionTrick`/`…Purpose`); this is the fixed counting rule:
# "Ein Tier mit Intelligenz 1 kann maximal drei Tricks, ein Tier mit
# Intelligenz 2 maximal 6 Tricks erlernen" — bonus tricks don't count
# against it ("werden nicht in die normale Beschränkung bekannter Tricks mit
# einberechnet"). The PRD says nothing about IN 3+; decided 2026-10-25: no
# limit from IN 3 on.
TRAINED_TRICK_LIMITS = {1: 3, 2: 6}
UNLIMITED_TRICKS_MIN_INTELLIGENCE = 3
# "Enthält die Ausbildung mehr als drei Tricks, muss das Tier eine
# Intelligenz von 2 oder höher besitzen."
LARGE_PURPOSE_TRICKS = 3
LARGE_PURPOSE_MIN_INTELLIGENCE = 2
TRICK_SOURCES = ("bonus", "trained")


class TrickRow(Protocol):
    """The `BaseCompanionTrick` columns this module reads."""

    id: UUID
    name: str
    cost: int
    required_ability_id: UUID | None
    variant_of_id: UUID | None


@dataclass(frozen=True)
class TrickPick:
    trick_id: UUID
    source: str


@dataclass(frozen=True)
class TrickPurposeRef:
    id: UUID
    name: str
    trick_ids: frozenset[UUID]


@dataclass(frozen=True)
class TrickLimits:
    bonus_used: int
    bonus_max: int
    trained_used: int
    # `None` = no limit (IN 3+).
    trained_max: int | None

    @property
    def over_limit(self) -> bool:
        return self.bonus_used > self.bonus_max or (
            self.trained_max is not None and self.trained_used > self.trained_max
        )


def trained_trick_limit(intelligence: int) -> int | None:
    if intelligence >= UNLIMITED_TRICKS_MIN_INTELLIGENCE:
        return None
    return TRAINED_TRICK_LIMITS.get(intelligence, 0)


def trick_limits(
    picks: Iterable[TrickPick], tricks_by_id: dict[UUID, TrickRow], bonus_max: int, intelligence: int
) -> TrickLimits:
    """Slots used per pool, each trick counted at its `cost`."""
    used = {source: 0 for source in TRICK_SOURCES}
    for pick in picks:
        used[pick.source] += tricks_by_id[pick.trick_id].cost
    return TrickLimits(used["bonus"], bonus_max, used["trained"], trained_trick_limit(intelligence))


def trick_unavailable_reason(
    trick: TrickRow, species_ability_ids: Iterable[UUID], ability_names: dict[UUID, str]
) -> str | None:
    """Why the companion can't learn `trick` (Spuren suchen without
    Geruchssinn), `None` if it can."""
    if trick.required_ability_id is not None and trick.required_ability_id not in set(species_ability_ids):
        return f"braucht {ability_names.get(trick.required_ability_id, 'eine besondere Fähigkeit')}"
    return None


def purpose_unavailable_reason(
    purpose: TrickPurposeRef,
    tricks_by_id: dict[UUID, TrickRow],
    species_ability_ids: Iterable[UUID],
    ability_names: dict[UUID, str],
    intelligence: int,
) -> str | None:
    """"Das Tier muss alle Voraussetzungen für alle Tricks erfüllen" and the
    IN 2 minimum for a training of more than three tricks."""
    species_ability_ids = set(species_ability_ids)
    for trick_id in sorted(purpose.trick_ids, key=lambda trick_id: tricks_by_id[trick_id].name):
        trick = tricks_by_id[trick_id]
        reason = trick_unavailable_reason(trick, species_ability_ids, ability_names)
        if reason is not None:
            return f"{trick.name} {reason}"
    if len(purpose.trick_ids) > LARGE_PURPOSE_TRICKS and intelligence < LARGE_PURPOSE_MIN_INTELLIGENCE:
        return f"mehr als {LARGE_PURPOSE_TRICKS} Tricks, braucht IN {LARGE_PURPOSE_MIN_INTELLIGENCE}"
    return None


def is_purpose_trick(pick_trick_id: UUID, purpose: TrickPurposeRef | None, tricks_by_id: dict[UUID, TrickRow]) -> bool:
    """Whether a pick is one of the training's tricks — a variant covers the
    trick it includes (Angreifen (alle Wesen) for Angreifen)."""
    if purpose is None:
        return False
    trick = tricks_by_id[pick_trick_id]
    return trick.id in purpose.trick_ids or trick.variant_of_id in purpose.trick_ids


def trick_errors(
    picks: list[TrickPick],
    purpose: TrickPurposeRef | None,
    tricks_by_id: dict[UUID, TrickRow],
    species_ability_ids: Iterable[UUID],
    ability_names: dict[UUID, str],
    bonus_max: int,
    intelligence: int,
) -> list[str]:
    """Everything wrong with a full trick set the player wants to store.
    The Mit-Tieren-umgehen check and the training time aren't modeled — a
    "trained" pick is the player's own statement."""
    errors: list[str] = []
    species_ability_ids = set(species_ability_ids)
    unknown = [pick.trick_id for pick in picks if pick.trick_id not in tricks_by_id]
    if unknown:
        return [f"Unbekannter Trick: {trick_id}" for trick_id in unknown]
    if any(pick.source not in TRICK_SOURCES for pick in picks):
        errors.append("Quelle muss 'bonus' oder 'trained' sein.")
        return errors
    counts = Counter(pick.trick_id for pick in picks)
    errors += [f"{tricks_by_id[trick_id].name} ist doppelt gewählt." for trick_id, n in counts.items() if n > 1]
    picked = set(counts)
    for trick_id in picked:
        trick = tricks_by_id[trick_id]
        if trick.variant_of_id in picked:
            errors.append(f"{trick.name} enthält bereits {tricks_by_id[trick.variant_of_id].name}.")
        reason = trick_unavailable_reason(trick, species_ability_ids, ability_names)
        if reason is not None:
            errors.append(f"{trick.name} {reason}.")
    if purpose is not None:
        reason = purpose_unavailable_reason(purpose, tricks_by_id, species_ability_ids, ability_names, intelligence)
        if reason is not None:
            errors.append(f"{purpose.name}: {reason}.")
        covered = picked | {
            tricks_by_id[trick_id].variant_of_id for trick_id in picked if tricks_by_id[trick_id].variant_of_id
        }
        missing = sorted(tricks_by_id[trick_id].name for trick_id in purpose.trick_ids - covered)
        if missing:
            errors.append(f"{purpose.name} umfasst auch: {', '.join(missing)}.")
    limits = trick_limits(picks, tricks_by_id, bonus_max, intelligence)
    if limits.bonus_used > limits.bonus_max:
        errors.append(f"Zu viele Bonustricks ({limits.bonus_used}/{limits.bonus_max}).")
    if limits.trained_max is not None and limits.trained_used > limits.trained_max:
        errors.append(f"Zu viele abgerichtete Tricks ({limits.trained_used}/{limits.trained_max}, IN {intelligence}).")
    return errors
