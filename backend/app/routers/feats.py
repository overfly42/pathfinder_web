from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BaseFeat, Character
from ..rules.effective_scores import full_effective_ability_scores
from ..rules.feat_prerequisites import CharacterPrereqState, eligible_feat_ids
from ..rules.feats import COMPUTED_OUTSIDE_HANDLERS_FEAT_IDS
from ..rules.handlers import HANDLERS
from ..rules.proficiency import effective_proficiency_feat_ids
from ..sheet import granted_class_ability_ids
from .races import race_ability_score_mods

router = APIRouter(prefix="/api/feats", tags=["feats"])


def _character_prereq_state(db: Session, character: Character) -> CharacterPrereqState:
    """Assembles `CharacterPrereqState` from whichever subsystem already
    owns each raw value — same "gather from existing owners, don't
    re-derive" shape `routers/characters.py`'s `_ability_context` uses for
    its own smaller `CharacterContext`."""
    race_mods = race_ability_score_mods(db, character.race_id)
    effective_scores = full_effective_ability_scores(db, character, race_mods)
    level_counts_by_root_id: dict[UUID, int] = {}
    for lvl in character.levels:
        level_counts_by_root_id[lvl.base_class_id] = level_counts_by_root_id.get(lvl.base_class_id, 0) + 1
    granted_ability_ids = frozenset(granted_class_ability_ids(db, character, level_counts_by_root_id))
    # Proficiency-granting class abilities (e.g. "Umgang mit Waffen und
    # Rüstungen") count the same as literally holding the matching
    # proficiency feat for prerequisite purposes — see
    # `BaseClassAbilityGrantedFeat`'s docstring — so a downstream feat's
    # `BaseFeatRequiredFeat` row (e.g. Medium Armor Proficiency requiring
    # Light) is satisfied without spending a pick on a proficiency the
    # character's class already grants for free. Shared with `sheet.py`'s
    # weapon-attack proficiency malus, which needs the identical merge.
    return CharacterPrereqState(
        ability_scores=effective_scores,
        bab=character.bab,
        feat_ids=effective_proficiency_feat_ids(db, frozenset(character.feat_ids), granted_ability_ids),
        granted_ability_ids=granted_ability_ids,
        level_counts_by_root_id=level_counts_by_root_id,
        race_id=character.race_id,
        skill_ranks={UUID(skill_id): ranks for skill_id, ranks in character.skill_ranks.items()},
    )


@router.get("")
def list_feats(db: Annotated[Session, Depends(get_db)], character_id: UUID | None = None) -> list[dict]:
    feats = db.scalars(select(BaseFeat).order_by(BaseFeat.name)).all()

    # Unfiltered when no character is given (e.g. character-creation's own
    # picker, where ability scores/class aren't settled yet to check
    # against) — same "additive, backward-compatible" shape as every other
    # optional query param in this codebase. With a character, reduce to
    # only the feats whose prerequisites (`base_feat_required_*`) it
    # currently meets — level-up's own feat step (`routers/feats.py`'s
    # caller, `useLevelUpOptions.ts`) passes this so the picker only ever
    # shows a legal choice.
    if character_id is not None:
        character = db.get(Character, character_id)
        if character is None:
            raise HTTPException(status_code=404, detail="Character not found")
        state = _character_prereq_state(db, character)
        allowed = eligible_feat_ids(db, (feat.id for feat in feats), state)
        feats = [feat for feat in feats if feat.id in allowed]

    return [
        {
            "id": str(feat.id),
            "name": feat.name,
            "description": feat.description,
            "type": feat.type,
            # camelCase on the wire (unlike the DB column) to match the
            # frontend's `FeatDef.subChoiceType` — same "backend picks the
            # JSON shape a consumer wants" precedent as `main.py`'s classes
            # endpoint (`skillPointsBase`, `bonusFeatLevels`, ...).
            "subChoiceType": feat.sub_choice_type,
            # Whether this feat's effect is actually computed anywhere — via
            # `rules/handlers.py`'s merged `HANDLERS`, or via `sheet.py`'s
            # own per-weapon-slot handling for the handful of feats that
            # can't be a flat `Modifier` (`rules/feats.py`'s
            # `COMPUTED_OUTSIDE_HANDLERS_FEAT_IDS`) — vs. it only ever
            # showing as name/description text on the sheet. See CLAUDE.md's
            # composition-vs-computation split.
            "hasHandler": feat.id in HANDLERS or feat.id in COMPUTED_OUTSIDE_HANDLERS_FEAT_IDS,
        }
        for feat in feats
    ]
