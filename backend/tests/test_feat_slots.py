from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.models import (
    BaseClassAbility,
    BaseClassAbilityFeatOption,
    BaseClassAbilitySpellOption,
    BaseClassOptionChoice,
    BaseClassOptionGroup,
    BaseRace,
)
from app.rules.feat_slots import RACE_BONUS_FEAT_ABILITY_ID, class_bonus_feat_slot_count, race_grants_bonus_feat
from app.seed.class_ability_option_seed import seed_class_ability_options
from app.seed.class_ability_seed import seed_class_abilities
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.feat_seed import seed_feats
from app.seed.race_seed import seed_races
from app.seed.skill_seed import seed_skills


def _selection(class_name: str, level: int) -> SimpleNamespace:
    return SimpleNamespace(class_name=class_name, level=level)


def test_class_bonus_feat_slot_count_is_cumulative_by_class_level(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    # Kämpfer grants a bonus feat slot at 1st and every even level.
    assert class_bonus_feat_slot_count(db_session, [_selection("Kämpfer", 1)]) == 1
    assert class_bonus_feat_slot_count(db_session, [_selection("Kämpfer", 2)]) == 2
    # Level 3 doesn't add a new slot (no grant at level 3) -> still 2.
    assert class_bonus_feat_slot_count(db_session, [_selection("Kämpfer", 3)]) == 2
    assert class_bonus_feat_slot_count(db_session, [_selection("Kämpfer", 4)]) == 3


def test_class_bonus_feat_slot_count_sums_non_contiguous_class_selections(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    split = class_bonus_feat_slot_count(
        db_session, [_selection("Kämpfer", 1), _selection("Schurke", 1), _selection("Kämpfer", 2)]
    )
    single = class_bonus_feat_slot_count(db_session, [_selection("Kämpfer", 3)])
    assert split == single == 2


def test_class_bonus_feat_slot_count_is_zero_for_classes_with_no_seeded_bonus_feats(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
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


def test_kaempfer_bonus_kampftalent_is_seeded_as_a_combat_only_feat_pool(db_session: Session) -> None:
    """roadmap.md's "pick from a restricted list" plan: a bonus-feat-slot
    ability's eligibility is the union of its `BaseClassAbilityFeatOption`
    rows. Kämpfer's Bonus-Kampftalent should resolve to exactly one row,
    `feat_type == "combat"` — nothing yet *enforces* this at creation time
    (that's still open, see roadmap.md), this only checks the data exists."""
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)
    seed_races(db_session)
    seed_skills(db_session)
    seed_feats(db_session)
    seed_class_ability_options(db_session)

    bonus_kampftalent = db_session.query(BaseClassAbility).filter_by(name="Bonus-Kampftalent").one()
    rows = db_session.query(BaseClassAbilityFeatOption).filter_by(ability_id=bonus_kampftalent.id).all()

    assert [(r.feat_type, r.feat_id) for r in rows] == [("combat", None)]


def test_magier_bonustalent_is_seeded_as_metamagic_item_creation_or_spell_mastery(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)
    seed_races(db_session)
    seed_skills(db_session)
    seed_feats(db_session)
    seed_class_ability_options(db_session)

    bonustalent = db_session.query(BaseClassAbility).filter_by(name="Bonustalent (Magier)").one()
    rows = db_session.query(BaseClassAbilityFeatOption).filter_by(ability_id=bonustalent.id).all()

    feat_types = {r.feat_type for r in rows if r.feat_type is not None}
    assert feat_types == {"metamagic", "item_creation"}
    # The one named exception (Spell Mastery) is a closed list of one feat,
    # not a type filter.
    closed_list_feat_ids = {r.feat_id for r in rows if r.feat_id is not None}
    assert len(closed_list_feat_ids) == 1
    from app.models import BaseFeat

    zaubermeisterschaft_id = db_session.query(BaseFeat).filter_by(name="Zaubermeisterschaft").one().id
    assert closed_list_feat_ids == {zaubermeisterschaft_id}


def test_hexenmeister_talent_des_blutes_is_seeded_per_bloodline(db_session: Session) -> None:
    """Each bloodline's talent list is gated by `option_choice_id` — the
    same bloodline choice `Zauber des Blutes`/`Macht des Blutes` grants
    already use. Spot-checks the Drachenblutlinie's list rather than all 10
    (the full ~80-row import is exercised implicitly by every row loading
    without a missing-FK error)."""
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)
    seed_races(db_session)
    seed_skills(db_session)
    seed_feats(db_session)
    seed_class_ability_options(db_session)

    talent_des_blutes = db_session.query(BaseClassAbility).filter_by(name="Talent des Blutes").one()
    drachenblutlinie = db_session.query(BaseClassOptionChoice).filter_by(name="Drachenblutlinie").one()

    rows = (
        db_session.query(BaseClassAbilityFeatOption)
        .filter_by(ability_id=talent_des_blutes.id, option_choice_id=drachenblutlinie.id)
        .all()
    )
    assert len(rows) > 0
    assert all(r.feat_id is not None and r.feat_type is None for r in rows)


def test_schurke_trick_and_advanced_trick_option_groups_are_seeded(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    schurke = db_session.query(BaseClassOptionGroup).filter(BaseClassOptionGroup.key == "trick").one()
    advanced = db_session.query(BaseClassOptionGroup).filter(BaseClassOptionGroup.key == "trick_advanced").one()

    trick_choices = db_session.query(BaseClassOptionChoice).filter_by(group_id=schurke.id).all()
    advanced_choices = db_session.query(BaseClassOptionChoice).filter_by(group_id=advanced.id).all()

    # http://prd.5footstep.de/Grundregelwerk/Klassen/Schurke - 15 basic
    # tricks, 8 advanced tricks ("Verbesserte Tricks").
    assert len(trick_choices) == 15
    assert len(advanced_choices) == 8
    assert schurke.max_choices == 10  # total Trick grants across a career
    assert advanced.max_choices == 6  # only the level-10+ grants can draw from this pool


def test_schurke_feat_and_spell_granting_tricks_have_pool_rows(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)
    seed_races(db_session)
    seed_skills(db_session)
    seed_feats(db_session)
    seed_class_ability_options(db_session)

    kampfkniff = db_session.query(BaseClassAbility).filter_by(name="Kampfkniff").one()
    schurkenfinesse = db_session.query(BaseClassAbility).filter_by(name="Schurkenfinesse").one()
    waffentraining_trick = (
        db_session.query(BaseClassAbility).filter_by(name="Waffentraining").filter(BaseClassAbility.description.contains("Bonustalent")).one()
    )

    kampfkniff_rows = db_session.query(BaseClassAbilityFeatOption).filter_by(ability_id=kampfkniff.id).all()
    assert [(r.feat_type, r.feat_id) for r in kampfkniff_rows] == [("combat", None)]

    schurkenfinesse_rows = db_session.query(BaseClassAbilityFeatOption).filter_by(ability_id=schurkenfinesse.id).all()
    assert len(schurkenfinesse_rows) == 1 and schurkenfinesse_rows[0].feat_type is None

    waffentraining_rows = (
        db_session.query(BaseClassAbilityFeatOption).filter_by(ability_id=waffentraining_trick.id).all()
    )
    assert len(waffentraining_rows) == 1 and waffentraining_rows[0].feat_type is None


def test_schurke_hoehere_and_niedere_magie_have_spell_pool_rows(db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)
    seed_races(db_session)
    seed_skills(db_session)
    seed_feats(db_session)
    seed_class_ability_options(db_session)

    hoehere_magie = db_session.query(BaseClassAbility).filter_by(name="Höhere Magie").one()
    niedere_magie = db_session.query(BaseClassAbility).filter_by(name="Niedere Magie").one()

    hoehere_rows = db_session.query(BaseClassAbilitySpellOption).filter_by(ability_id=hoehere_magie.id).all()
    niedere_rows = db_session.query(BaseClassAbilitySpellOption).filter_by(ability_id=niedere_magie.id).all()

    assert {r.source_grade for r in hoehere_rows} == {1}
    assert {r.source_grade for r in niedere_rows} == {0}
    assert len(hoehere_rows) == 2  # Magier + Hexenmeister lists
    assert len(niedere_rows) == 2
