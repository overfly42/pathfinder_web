from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.rules.feat_slots import class_bonus_feat_slot_count
from app.seed.class_ability_seed import seed_class_abilities
from app.seed.class_seed import seed_classes


def _selection(class_name: str, level: int) -> SimpleNamespace:
    return SimpleNamespace(class_name=class_name, level=level)


def test_class_bonus_feat_slot_count_is_cumulative_by_class_level(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_abilities(db_session)

    # Krieger grants a bonus feat slot at 1st and every even level.
    assert class_bonus_feat_slot_count(db_session, [_selection("Krieger", 1)]) == 1
    assert class_bonus_feat_slot_count(db_session, [_selection("Krieger", 2)]) == 2
    # Level 3 doesn't add a new slot (no grant at level 3) -> still 2.
    assert class_bonus_feat_slot_count(db_session, [_selection("Krieger", 3)]) == 2
    assert class_bonus_feat_slot_count(db_session, [_selection("Krieger", 4)]) == 3


def test_class_bonus_feat_slot_count_sums_non_contiguous_class_selections(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_abilities(db_session)

    split = class_bonus_feat_slot_count(
        db_session, [_selection("Krieger", 1), _selection("Schurke", 1), _selection("Krieger", 2)]
    )
    single = class_bonus_feat_slot_count(db_session, [_selection("Krieger", 3)])
    assert split == single == 2


def test_class_bonus_feat_slot_count_is_zero_for_classes_with_no_seeded_bonus_feats(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_abilities(db_session)

    assert class_bonus_feat_slot_count(db_session, [_selection("Waldläufer", 5)]) == 0


def test_class_bonus_feat_slot_count_is_zero_with_no_classes(db_session: Session) -> None:
    assert class_bonus_feat_slot_count(db_session, []) == 0
