from collections import Counter
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.models import (
    BaseClass,
    BaseClassAbility,
    BaseClassAbilityFeatOption,
    BaseClassAbilityGrant,
    BaseClassAbilitySpellOption,
    BaseClassOptionChoice,
    BaseClassOptionGroup,
    BaseClassSkill,
    BaseRace,
    BaseSkill,
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


def test_hexenmeister_bloodlines_each_grant_a_bonus_class_skill(db_session: Session) -> None:
    """http://prd.5footstep.de/Grundregelwerk/Klassen/Hexenmeister - every
    bloodline section has its own "Klassenfertigkeit: X" line (missed by the
    original bloodline import, which only extracted the "Bonustalente:"
    paragraph) - same `BaseClassSkill.option_choice_id` mechanism as
    Mystiker's per-mystery bonus skills, found the same way (see the
    conversation this was scoped from)."""
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_skills(db_session)

    hexenmeister = db_session.query(BaseClass).filter_by(name="Hexenmeister").one()
    skills_by_id = {s.id: s.name for s in db_session.query(BaseSkill).all()}

    def bonus_skills(bloodline_name: str) -> set[str]:
        choice = db_session.query(BaseClassOptionChoice).filter_by(name=bloodline_name).one()
        rows = db_session.query(BaseClassSkill).filter_by(base_class_id=hexenmeister.id, option_choice_id=choice.id)
        return {skills_by_id[r.skill_id] for r in rows}

    assert bonus_skills("Drachenblutlinie") == {"Wahrnehmung"}
    assert bonus_skills("Teuflische Blutlinie") == {"Diplomatie"}
    assert bonus_skills("Himmlische Blutlinie") == {"Heilkunde"}
    # "Wissen (freie Wahl)" - modeled as all 10 Wissen sub-skills, see
    # add_hexenmeister_bloodline_skills.py's docstring for why.
    arkane_skills = bonus_skills("Arkane Blutlinie")
    assert len(arkane_skills) == 10
    assert all(name.startswith("Wissen (") for name in arkane_skills)


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


def test_waldlaeufer_kampfstiltalent_is_seeded_per_combat_style(db_session: Session) -> None:
    """http://prd.5footstep.de/Grundregelwerk/Klassen/Waldlaeufer - unlike
    Hexenmeister's bloodline talents, there was no pre-resolved import for
    this; the per-style feat lists only exist as prose on the class page."""
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)
    seed_races(db_session)
    seed_skills(db_session)
    seed_feats(db_session)
    seed_class_ability_options(db_session)

    waldlaeufer = db_session.query(BaseClass).filter_by(name="Waldläufer").one()
    combat_style = db_session.query(BaseClassOptionGroup).filter_by(key="combat_style").one()
    assert combat_style.base_class_id == waldlaeufer.id
    assert combat_style.max_choices == 1
    style_choices = {c.name: c.id for c in db_session.query(BaseClassOptionChoice).filter_by(group_id=combat_style.id).all()}
    assert set(style_choices) == {"Bogenschießen", "Kampf mit zwei Waffen"}

    kampfstiltalent = db_session.query(BaseClassAbility).filter_by(name="Kampfstiltalent").one()

    bogenschiessen_rows = (
        db_session.query(BaseClassAbilityFeatOption)
        .filter_by(ability_id=kampfstiltalent.id, option_choice_id=style_choices["Bogenschießen"])
        .all()
    )
    zwei_waffen_rows = (
        db_session.query(BaseClassAbilityFeatOption)
        .filter_by(ability_id=kampfstiltalent.id, option_choice_id=style_choices["Kampf mit zwei Waffen"])
        .all()
    )
    # 4 base + 2 at 6th + 2 at 10th level per style. min_level tags when each
    # tier opens up (null = eligible from the 2nd-level slot that first
    # grants the ability) - see BaseClassAbilityFeatOption.min_level.
    assert len(bogenschiessen_rows) == 8
    assert len(zwei_waffen_rows) == 8
    assert all(r.feat_type is None and r.feat_id is not None for r in bogenschiessen_rows + zwei_waffen_rows)
    expected_tiers = Counter([None, None, None, None, 6, 6, 10, 10])
    assert Counter(r.min_level for r in bogenschiessen_rows) == expected_tiers
    assert Counter(r.min_level for r in zwei_waffen_rows) == expected_tiers


def test_waldlaeufer_enemy_and_terrain_allow_all_repeated_picks(db_session: Session) -> None:
    """http://prd.5footstep.de/Grundregelwerk/Klassen/Waldlaeufer - Erzfeind
    is granted at 1st/5th/10th/15th/20th (5 picks total across a career),
    Bevorzugtes Gelände at 3rd/8th/13th/18th (4 picks) - the grant rows for
    both were already correct, only `max_choices` was stuck at 1 from when
    these were modeled as one-time picks (see roadmap.md)."""
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    waldlaeufer = db_session.query(BaseClass).filter_by(name="Waldläufer").one()
    enemy = db_session.query(BaseClassOptionGroup).filter_by(key="enemy").one()
    terrain = db_session.query(BaseClassOptionGroup).filter_by(key="terrain").one()
    assert enemy.base_class_id == waldlaeufer.id
    assert enemy.max_choices == 5
    assert terrain.max_choices == 4

    erzfeind = db_session.query(BaseClassAbility).filter_by(name="Erzfeind").one()
    gelaende = db_session.query(BaseClassAbility).filter_by(name="Bevorzugtes Gelände").one()
    erzfeind_levels = [
        g.level for g in db_session.query(BaseClassAbilityGrant).filter_by(ability_id=erzfeind.id).order_by(BaseClassAbilityGrant.level)
    ]
    gelaende_levels = [
        g.level for g in db_session.query(BaseClassAbilityGrant).filter_by(ability_id=gelaende.id).order_by(BaseClassAbilityGrant.level)
    ]
    assert erzfeind_levels == [1, 5, 10, 15, 20]
    assert gelaende_levels == [3, 8, 13, 18]


def test_waldlaeufer_bund_des_jaegers_has_two_gated_branches(db_session: Session) -> None:
    """The class page describes Bund des Jägers as a one-time, irreversible
    choice at 4th level between an ally-bonus branch and an animal-companion
    branch (the latter itself picks from a fixed animal list, described in
    prose only - the animal catalog itself is out of scope, see the
    conversation this was scoped from)."""
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    waldlaeufer = db_session.query(BaseClass).filter_by(name="Waldläufer").one()
    hunter_bond = db_session.query(BaseClassOptionGroup).filter_by(key="hunter_bond").one()
    assert hunter_bond.base_class_id == waldlaeufer.id
    assert hunter_bond.max_choices == 1

    branch_choices = {c.name: c.id for c in db_session.query(BaseClassOptionChoice).filter_by(group_id=hunter_bond.id).all()}
    assert set(branch_choices) == {"Bund mit Gefährten", "Tiergefährte"}

    overview = db_session.query(BaseClassAbility).filter_by(name="Bund des Jägers").one()
    overview_grant = db_session.query(BaseClassAbilityGrant).filter_by(ability_id=overview.id).one()
    assert overview_grant.option_choice_id is None  # everyone gets the overview text
    assert overview_grant.level == 4

    companion = db_session.query(BaseClassAbility).filter_by(name="Bund mit Gefährten").one()
    animal = db_session.query(BaseClassAbility).filter_by(name="Tiergefährte (Bund des Jägers)").one()
    companion_grant = db_session.query(BaseClassAbilityGrant).filter_by(ability_id=companion.id).one()
    animal_grant = db_session.query(BaseClassAbilityGrant).filter_by(ability_id=animal.id).one()
    assert companion_grant.option_choice_id == branch_choices["Bund mit Gefährten"]
    assert animal_grant.option_choice_id == branch_choices["Tiergefährte"]
    assert companion_grant.level == animal_grant.level == 4


def test_option_choice_min_level_and_requires_choice_id_round_trip(db_session: Session) -> None:
    """No class uses these two fields yet - they exist ahead of Mystiker
    (Oracle), whose Offenbarung ("revelation") choices each carry their own
    minimum Mystiker level and are only legal once the character has already
    picked the matching Mysterium, and ahead of a data-driven replacement for
    Schurke's hardcoded "Verbesserte Tricks unlock at 10th level" split (see
    the conversation this was scoped from). Exercises the mechanism directly
    against a synthetic choice gated behind Kleriker's "Domäne des Krieges"
    domain pick, since no real class needs it today - both columns
    round-trip through the database exactly like any other."""
    seed_classes(db_session)
    seed_class_options(db_session)

    kriegsdomaene = db_session.query(BaseClassOptionChoice).filter_by(name="Domäne des Krieges").one()

    gated = BaseClassOptionChoice(
        group_id=kriegsdomaene.group_id,
        name="Testfähigkeit (nur mit Domäne des Krieges, ab Stufe 11)",
        min_level=11,
        requires_choice_id=kriegsdomaene.id,
    )
    db_session.add(gated)
    db_session.commit()

    reloaded = db_session.query(BaseClassOptionChoice).filter_by(id=gated.id).one()
    assert reloaded.min_level == 11
    assert reloaded.requires_choice_id == kriegsdomaene.id
