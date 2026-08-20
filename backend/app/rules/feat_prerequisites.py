"""Feat prerequisite evaluation — roadmap.md §6 "Possible actions / legality
checks" territory ("does this feat's prerequisites check out"), previously
undone (`models/feat.py`'s `BaseFeatRequiredBab`/`BaseFeatRequiredFeat`
docstrings called this out explicitly: "not evaluated anywhere yet").

Composition (which requirement rows a feat has) is real data, across the
seven `BaseFeatRequired*` tables (`models/feat.py`); this module is purely
the *evaluation* half against one character's current raw state, per
CLAUDE.md's composition-vs-computation split.

OR-group semantics, per `BaseFeatRequiredFeat.group_id`'s docstring: every
row sharing a feat's `group_id` — across *any* of the seven tables, not just
one — is OR-ed into a single clause; a null `group_id` row is its own
singleton clause. A feat's prerequisites are met iff every one of its
clauses is met (at least one row in that clause is satisfied)."""

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    BaseFeatRequiredAbilityScore,
    BaseFeatRequiredBab,
    BaseFeatRequiredClassAbility,
    BaseFeatRequiredClassLevel,
    BaseFeatRequiredFeat,
    BaseFeatRequiredRace,
    BaseFeatRequiredSkill,
)


@dataclass
class CharacterPrereqState:
    """The raw character inputs every `BaseFeatRequired*` kind reads —
    assembled by the caller (`routers/feats.py`) from whichever subsystem
    already owns each value (effective ability scores, `Character.bab`,
    `sheet.py`'s `granted_class_ability_ids`, ...), not re-derived here.
    Ability scores are the full *effective* score (base + race + gear +
    ability damage, `rules/effective_scores.py`'s `full_effective_ability_scores`)
    since a permanent ability-score-boosting item legitimately qualifies a
    character for a feat the same way a high rolled score would."""

    ability_scores: dict[str, int]
    bab: int
    feat_ids: frozenset[UUID]
    granted_ability_ids: frozenset[UUID]
    level_counts_by_root_id: dict[UUID, int]
    race_id: UUID | None
    skill_ranks: dict[UUID, int]


def eligible_feat_ids(db: Session, candidate_feat_ids: Iterable[UUID], state: CharacterPrereqState) -> set[UUID]:
    """Which of `candidate_feat_ids` `state` currently satisfies the
    prerequisites for — a feat with no requirement rows at all is trivially
    eligible. Queries all seven `BaseFeatRequired*` tables unfiltered (cheap:
    a few hundred rows total, no per-feat round trip) rather than one query
    per candidate feat."""
    candidates = set(candidate_feat_ids)
    # (feat_id, group_key) -> whether at least one row in that OR-clause is
    # satisfied so far. `group_key` is the row's own `group_id` when set, or
    # its own primary key otherwise (an always-unique singleton clause).
    clauses: dict[tuple[UUID, UUID], bool] = {}

    def record(feat_id: UUID, group_id: UUID | None, row_id: UUID, satisfied: bool) -> None:
        if feat_id not in candidates:
            return
        key = (feat_id, group_id if group_id is not None else row_id)
        clauses[key] = clauses.get(key, False) or satisfied

    for row in db.scalars(select(BaseFeatRequiredAbilityScore)):
        record(row.feat_id, row.group_id, row.id, state.ability_scores.get(row.ability, 0) >= row.minimum_score)

    for row in db.scalars(select(BaseFeatRequiredBab)):
        record(row.feat_id, row.group_id, row.id, state.bab >= row.minimum_bab)

    for row in db.scalars(select(BaseFeatRequiredClassAbility)):
        record(row.feat_id, row.group_id, row.id, row.ability_id in state.granted_ability_ids)

    for row in db.scalars(select(BaseFeatRequiredClassLevel)):
        record(
            row.feat_id,
            row.group_id,
            row.id,
            state.level_counts_by_root_id.get(row.base_class_id, 0) >= row.minimum_level,
        )

    for row in db.scalars(select(BaseFeatRequiredFeat)):
        record(row.feat_id, row.group_id, row.id, row.required_feat_id in state.feat_ids)

    for row in db.scalars(select(BaseFeatRequiredRace)):
        record(row.feat_id, row.group_id, row.id, row.race_id == state.race_id)

    for row in db.scalars(select(BaseFeatRequiredSkill)):
        record(row.feat_id, row.group_id, row.id, state.skill_ranks.get(row.skill_id, 0) >= row.minimum_ranks)

    feats_with_requirements: dict[UUID, list[bool]] = {}
    for (feat_id, _group_key), satisfied in clauses.items():
        feats_with_requirements.setdefault(feat_id, []).append(satisfied)

    return {
        feat_id
        for feat_id in candidates
        if feat_id not in feats_with_requirements or all(feats_with_requirements[feat_id])
    }
