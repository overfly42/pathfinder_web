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
formula for a source whose rule doesn't fit the columns."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from .context import CharacterContext

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
