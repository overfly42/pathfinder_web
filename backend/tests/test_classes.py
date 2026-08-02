from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.class_ability_seed import seed_class_abilities
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.skill_seed import seed_skills


def test_list_classes_exposes_bonus_feat_levels_from_real_data(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    response = client.get("/api/classes")
    assert response.status_code == 200
    classes = {c["name"]: c for c in response.json()}

    assert classes["Kämpfer"]["bonusFeatLevels"] == [1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
    # No seeded bonus-feat data for other classes -> empty, not a guess.
    assert classes["Waldläufer"]["bonusFeatLevels"] == []


def test_list_classes_exposes_bab_and_save_progression(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)

    response = client.get("/api/classes")
    assert response.status_code == 200
    classes = {c["name"]: c for c in response.json()}

    # Kämpfer (Fighter): full BAB, good fort, poor ref/will.
    assert classes["Kämpfer"]["babProgression"] == 1.0
    assert classes["Kämpfer"]["fortSave"] is True
    assert classes["Kämpfer"]["refSave"] is False
    assert classes["Kämpfer"]["willSave"] is False
    # Magier (Wizard): half BAB, poor fort/ref, good will.
    assert classes["Magier"]["babProgression"] == 0.5
    assert classes["Magier"]["fortSave"] is False
    assert classes["Magier"]["willSave"] is True


def test_list_classes_exposes_skill_points_base_from_real_data(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)

    response = client.get("/api/classes")
    assert response.status_code == 200
    classes = {c["name"]: c for c in response.json()}

    assert classes["Schurke"]["skillPointsBase"] == 8
    assert classes["Kämpfer"]["skillPointsBase"] == 2


def test_list_classes_exposes_kaempfer_class_skills_from_real_data(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)  # base_class_skills.option_choice_id FKs here
    seed_skills(db_session)

    response = client.get("/api/classes")
    assert response.status_code == 200
    classes = {c["name"]: c for c in response.json()}

    skills = {s["id"]: s["name"] for s in client.get("/api/skills").json()}
    kaempfer_skill_names = {skills[skill_id] for skill_id in classes["Kämpfer"]["classSkills"]}

    # http://prd.5footstep.de/Grundregelwerk/Klassen/Kaempfer - the 10 class
    # skills listed in the "Klassenfertigkeiten" section.
    assert kaempfer_skill_names == {
        "Beruf",
        "Einschüchtern",
        "Handwerk",
        "Klettern",
        "Mit Tieren umgehen",
        "Reiten",
        "Schwimmen",
        "Überlebenskunst",
        "Wissen (Baukunst)",
        "Wissen (Gewölbekunde)",
    }


def test_list_classes_exposes_waldlaeufer_class_skills_from_real_data(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)  # base_class_skills.option_choice_id FKs here
    seed_skills(db_session)

    response = client.get("/api/classes")
    assert response.status_code == 200
    classes = {c["name"]: c for c in response.json()}

    skills = {s["id"]: s["name"] for s in client.get("/api/skills").json()}
    waldlaeufer_skill_names = {skills[skill_id] for skill_id in classes["Waldläufer"]["classSkills"]}

    # http://prd.5footstep.de/Grundregelwerk/Klassen/Waldlaeufer - the 15
    # class skills listed in the "Klassenfertigkeiten" section. "Entfesselungskunst"
    # was previously seeded here by mistake and is not part of this list.
    assert waldlaeufer_skill_names == {
        "Beruf",
        "Einschüchtern",
        "Handwerk",
        "Heilkunde",
        "Heimlichkeit",
        "Klettern",
        "Mit Tieren umgehen",
        "Reiten",
        "Schwimmen",
        "Überlebenskunst",
        "Wahrnehmung",
        "Wissen (Geographie)",
        "Wissen (Gewölbekunde)",
        "Wissen (Natur)",
        "Zauberkunde",
    }
