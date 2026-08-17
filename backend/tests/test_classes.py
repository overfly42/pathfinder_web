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


def test_class_level_options_exposes_barbar_kampfrauschkraft_from_real_data(
    client: TestClient, db_session: Session
) -> None:
    """Regression test for the level-up wizard offering no rage powers at
    all - `/api/class-level-options` used to read a stale fixture (wrong
    group key, 6 leftover placeholder choices) instead of the real,
    ~54-choice Kampfrauschkraft catalog and its per-level grants."""
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    response = client.get("/api/class-level-options")
    assert response.status_code == 200
    body = response.json()

    barbar_groups = {g["key"]: g for g in body["Barbar"]}
    kampfrauschkraft = barbar_groups["kampfrauschkraft"]
    assert kampfrauschkraft["levels"] == [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
    # 28 real rage powers imported for Barbar specifically (roadmap.md) - far
    # more than the 6 stale placeholder choices the old fixture served. All
    # of them have min_level <= 20, so by the last occurrence every one is
    # unlocked.
    assert len(kampfrauschkraft["choicesByLevel"]["20"]) == 28
    # "Erneuerte Lebenskraft" needs Barbar 4 - not yet legal at the very
    # first occurrence (level 2), but present from its own min_level on.
    assert "Erneuerte Lebenskraft" not in kampfrauschkraft["choicesByLevel"]["2"]
    assert "Erneuerte Lebenskraft" in kampfrauschkraft["choicesByLevel"]["4"]
    # This wizard is not a player-facing rules reference: a choice gated
    # behind a later level (here "Innere Zähigkeit", Barbar 8) must not be
    # offered at an earlier occurrence at all.
    assert "Innere Zähigkeit" not in kampfrauschkraft["choicesByLevel"]["2"]
    assert "Innere Zähigkeit" in kampfrauschkraft["choicesByLevel"]["8"]


def test_class_level_options_omits_one_time_picks(client: TestClient, db_session: Session) -> None:
    """Kleriker's `domain` and Waldläufer's `hunter_bond` are each granted at
    exactly one level (or, for domain, not via a level-gated ability grant
    at all) - neither is a recurring level-up pick, so neither should appear
    here (they're already covered by /api/classes' one-time optionGroups)."""
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    response = client.get("/api/class-level-options")
    assert response.status_code == 200
    body = response.json()

    assert "domain" not in {g["key"] for g in body.get("Kleriker", [])}
    assert "hunter_bond" not in {g["key"] for g in body.get("Waldläufer", [])}


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


def test_hexe_hexerei_choices_carry_min_level_and_narbiger_hexendoktor_overrides_level_1(
    client: TestClient, db_session: Session
) -> None:
    """Regression test (2026-08-17, reported while adding Ork's Narbiger
    Hexendoktor archetype): a level-1 Hexe must not be offered Major/Grand
    Hexes (real class level 10/18) as pickable choices, and a Hexe who has
    taken Narbiger Hexendoktor must not be offered a level-1 `hexerei` pick
    at all, since that archetype's own Narbenschild ability already replaced
    it — see `ClassStep.tsx`'s `availableOptionGroups` (frontend) and
    `_validate_options` (backend, `test_recurring_option_groups.py`'s
    `test_narbiger_hexendoktor_*` for the actual server-side enforcement)."""
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)

    response = client.get("/api/classes")
    assert response.status_code == 200
    classes = {c["name"]: c for c in response.json()}
    hexe = classes["Hexe"]

    assert "Narbiger Hexendoktor" in hexe["archetypes"]

    hexerei = next(g for g in hexe["optionGroups"] if g["key"] == "hexerei")
    choices_by_name = {c["name"]: c["minLevel"] for c in hexerei["choices"]}
    assert choices_by_name["Bezauberung"] is None  # a regular 1st-level hex
    assert choices_by_name["Agonie"] == 10  # a Major Hex
    assert choices_by_name["Todesfluch"] == 18  # a Grand Hex

    assert hexerei["occurrenceLevels"][0] == 1
    assert hexe["archetypeOptionOverrides"]["Narbiger Hexendoktor"]["hexerei"] == [1]
