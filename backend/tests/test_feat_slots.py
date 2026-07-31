from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.models import BaseRace
from app.rules.feat_slots import RACE_BONUS_FEAT_ABILITY_ID, class_bonus_feat_slot_count, race_grants_bonus_feat
from app.seed.class_ability_seed import seed_class_abilities
from app.seed.class_seed import seed_classes
from app.seed.race_seed import seed_races


def _selection(class_name: str, level: int) -> SimpleNamespace:
    return SimpleNamespace(class_name=class_name, level=level)


def test_class_bonus_feat_slot_count_is_cumulative_by_class_level(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_abilities(db_session)

    # Kämpfer grants a bonus feat slot at 1st and every even level.
    assert class_bonus_feat_slot_count(db_session, [_selection("Kämpfer", 1)]) == 1
    assert class_bonus_feat_slot_count(db_session, [_selection("Kämpfer", 2)]) == 2
    # Level 3 doesn't add a new slot (no grant at level 3) -> still 2.
    assert class_bonus_feat_slot_count(db_session, [_selection("Kämpfer", 3)]) == 2
    assert class_bonus_feat_slot_count(db_session, [_selection("Kämpfer", 4)]) == 3


def test_class_bonus_feat_slot_count_sums_non_contiguous_class_selections(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_abilities(db_session)

    split = class_bonus_feat_slot_count(
        db_session, [_selection("Kämpfer", 1), _selection("Schurke", 1), _selection("Kämpfer", 2)]
    )
    single = class_bonus_feat_slot_count(db_session, [_selection("Kämpfer", 3)])
    assert split == single == 2


def test_class_bonus_feat_slot_count_is_zero_for_classes_with_no_seeded_bonus_feats(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_abilities(db_session)

    assert class_bonus_feat_slot_count(db_session, [_selection("Waldläufer", 5)]) == 0


def test_class_bonus_feat_slot_count_is_zero_with_no_classes(db_session: Session) -> None:
    assert class_bonus_feat_slot_count(db_session, []) == 0


def test_race_grants_bonus_feat_respects_replaced_ability_ids(db_session: Session) -> None:
    """Mensch's "Bonustalent" is a non-alternate grant; a resolved alt_trait
    that replaces it (`RACE_BONUS_FEAT_ABILITY_ID` in `replaced_ability_ids`,
    same as `routers/characters.py`'s `seen_replaced_ability_ids`) should
    drop it, regardless of which specific alternate trait did the
    replacing (Mensch itself has no such alternate seeded today, see
    todos.md — this exercises the mechanism directly rather than depending
    on that content existing)."""
    seed_races(db_session)
    mensch = db_session.query(BaseRace).filter_by(name="Mensch").one()

    assert race_grants_bonus_feat(db_session, mensch.id, set()) is True
    assert race_grants_bonus_feat(db_session, mensch.id, {RACE_BONUS_FEAT_ABILITY_ID}) is False
