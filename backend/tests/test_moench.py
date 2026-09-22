"""Mönch (Monk) import - http://prd.5footstep.de/Grundregelwerk/Klassen/
Moench, see scripts/import_moench.py - plus its two new archetypes,
Meister aller Kampfstile (http://prd.5footstep.de/AusbauregelnIIKampf/
Archetypen/Moench/MeisterallerKampfstile, scripts/import_meister_aller_kampfstile.py)
and Beschuppte Faust (Scaled Fist, d20pfsrd, scripts/import_scaled_fist_archetype.py).
Before this pass Mönch had only a placeholder `base_classes` row and no real
class-feature content at all (see todos.md)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import BaseClass, BaseClassAbility, BaseClassAbilityFeatOption, BaseClassAbilityGrant
from app.seed.class_ability_seed import seed_class_abilities
from app.seed.class_ability_option_seed import seed_class_ability_options
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.feat_seed import seed_feats
from app.seed.skill_seed import seed_skills

from test_characters import _character_payload, _create_user, _elf_race_id


def _moench(db_session: Session) -> BaseClass:
    return db_session.query(BaseClass).filter_by(name="Mönch").one()


def test_moench_base_class_fields_match_the_page(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)

    response = client.get("/api/classes")
    moench = next(c for c in response.json() if c["name"] == "Mönch")

    moench_row = _moench(db_session)
    assert moench_row.hit_dice == 8
    assert moench["castingAbility"] is None
    assert moench["spellTradition"] is None
    assert moench["babProgression"] == 0.75
    assert moench["fortSave"] is True
    assert moench["refSave"] is True
    assert moench["willSave"] is True
    assert moench["skillPointsBase"] == 4


def test_moench_class_skills_are_the_full_14(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)  # base_class_skills.option_choice_id FKs here
    seed_skills(db_session)

    response = client.get("/api/classes")
    moench = next(c for c in response.json() if c["name"] == "Mönch")
    skills = {s["id"]: s["name"] for s in client.get("/api/skills").json()}
    names = {skills[sid] for sid in moench["classSkills"]}

    assert names == {
        "Akrobatik",
        "Auftreten",
        "Beruf",
        "Einschüchtern",
        "Entfesselungskunst",
        "Handwerk",
        "Heimlichkeit",
        "Klettern",
        "Motiv erkennen",
        "Reiten",
        "Schwimmen",
        "Wahrnehmung",
        "Wissen (Geschichte)",
        "Wissen (Religion)",
    }
    # Heilkunde was wrongly on the old, pre-import list - not a real Monk class skill.
    assert "Heilkunde" not in names


def test_moench_bonustalent_grants_every_expected_level(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)  # base_class_ability_grants.option_choice_id FKs here
    seed_class_abilities(db_session)

    moench = _moench(db_session)
    ability = db_session.query(BaseClassAbility).filter_by(name="Bonustalent").join(
        BaseClassAbilityGrant, BaseClassAbilityGrant.ability_id == BaseClassAbility.id
    ).filter(BaseClassAbilityGrant.base_class_id == moench.id).one()
    levels = sorted(
        g.level for g in db_session.query(BaseClassAbilityGrant).filter_by(base_class_id=moench.id, ability_id=ability.id)
    )
    assert levels == [1, 2, 6, 10, 14, 18]


def test_moench_ki_vorrat_and_sturz_abbremsen_repeat_at_the_right_levels(
    client: TestClient, db_session: Session
) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)  # base_class_ability_grants.option_choice_id FKs here
    seed_class_abilities(db_session)

    moench = _moench(db_session)
    ki_vorrat = db_session.query(BaseClassAbility).filter_by(name="Ki-Vorrat").one()
    sturz_abbremsen = db_session.query(BaseClassAbility).filter_by(name="Sturz abbremsen").one()

    ki_levels = sorted(
        g.level for g in db_session.query(BaseClassAbilityGrant).filter_by(base_class_id=moench.id, ability_id=ki_vorrat.id)
    )
    sturz_levels = sorted(
        g.level
        for g in db_session.query(BaseClassAbilityGrant).filter_by(base_class_id=moench.id, ability_id=sturz_abbremsen.id)
    )

    assert ki_levels == [4, 7, 10, 16]
    assert sturz_levels == [4, 6, 8, 10, 12, 14, 16, 18, 20]


def test_moench_bonustalent_feat_options_are_gated_by_min_level(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)  # base_class_ability_grants.option_choice_id FKs here
    seed_class_abilities(db_session)
    seed_skills(db_session)  # base_feat_required_skills FKs into base_skills
    seed_feats(db_session)  # base_class_ability_feat_options.feat_id FKs here
    seed_class_ability_options(db_session)

    moench = _moench(db_session)
    bonustalent = db_session.query(BaseClassAbility).filter_by(name="Bonustalent").join(
        BaseClassAbilityGrant, BaseClassAbilityGrant.ability_id == BaseClassAbility.id
    ).filter(BaseClassAbilityGrant.base_class_id == moench.id).one()

    options = db_session.query(BaseClassAbilityFeatOption).filter_by(ability_id=bonustalent.id).all()
    assert len(options) == 17
    by_min_level: dict[int | None, int] = {}
    for option in options:
        by_min_level[option.min_level] = by_min_level.get(option.min_level, 0) + 1
    assert by_min_level == {None: 7, 6: 6, 10: 4}


def test_class_features_show_moench_features_at_level_20(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    payload = _character_payload(
        user_id, race_id, db_session, classes=[{"class_name": "Mönch", "level": 20, "archetypes": []}]
    )
    seed_skills(db_session)

    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201
    character_id = response.json()["id"]

    body = client.get(f"/api/characters/{character_id}").json()
    feature_names = {f["name"] for f in body["classFeatures"]}

    assert {
        "Umgang mit Waffen und Rüstungen",
        "Rüstungsklassenbonus",
        "Schlaghagel",
        "Waffenloser Schlag",
        "Betäubender Schlag",
        "Diamantseele",
        "Vibrierende Handfläche",
        "Zeitloser Körper",
        "Sprache von Sonne und Mond",
        "Körper lösen",
        "Perfektes Selbst",
    } <= feature_names


def test_class_features_apply_meister_aller_kampfstile_replacements(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Mönch", "level": 20, "archetypes": ["Meister aller Kampfstile"]}],
    )
    seed_skills(db_session)

    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201
    character_id = response.json()["id"]

    body = client.get(f"/api/characters/{character_id}").json()
    feature_names = {f["name"] for f in body["classFeatures"]}

    assert {"Bonustalente (Meister aller Kampfstile)", "Kampfstile verschmelzen", "Perfekter Stil"} <= feature_names
    assert "Bonustalent" not in feature_names
    assert "Schlaghagel" not in feature_names
    assert "Perfektes Selbst" not in feature_names
    # Unaffected base features still show.
    assert {"Waffenloser Schlag", "Diamantseele", "Ki-Vorrat"} <= feature_names


def test_class_features_apply_beschuppte_faust_replacements(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Mönch", "level": 15, "archetypes": ["Beschuppte Faust"]}],
    )
    seed_skills(db_session)

    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201
    character_id = response.json()["id"]

    body = client.get(f"/api/characters/{character_id}").json()
    feature_names = {f["name"] for f in body["classFeatures"]}

    assert {"Drachenmacht", "Drachenmut", "Drachenfurie", "Drachenatem"} <= feature_names
    assert "Ruhiger Geist" not in feature_names
    assert "Manövertraining" not in feature_names
    assert "Vibrierende Handfläche" not in feature_names
    # Unaffected base features still show.
    assert {"Schlaghagel", "Bonustalent", "Ki-Vorrat"} <= feature_names
