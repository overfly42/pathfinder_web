from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.class_ability_seed import seed_class_abilities
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.feat_seed import seed_feats
from app.seed.race_seed import seed_races
from app.seed.skill_seed import seed_skills

from test_characters import _character_payload, _create_user, _human_race_id


def test_list_feats_is_database_backed(client: TestClient, db_session: Session) -> None:
    # base_feat_required_* FKs into base_races/base_classes/base_class_abilities/base_skills.
    seed_races(db_session)
    seed_classes(db_session)
    seed_class_options(db_session)  # base_class_ability_grants.option_choice_id FKs here
    seed_class_abilities(db_session)
    seed_skills(db_session)
    seed_feats(db_session)

    response = client.get("/api/feats")
    assert response.status_code == 200
    feats = response.json()

    assert len(feats) == 334  # includes the 9 Ork-specific feats (import_ork_feats.py)
    assert all({"id", "name", "description", "type"} <= set(feat) for feat in feats)

    waffenfokus = next(f for f in feats if f["name"] == "Waffenfokus")
    assert waffenfokus["type"] == "combat"
    assert waffenfokus["subChoiceType"] == "weapon"

    fertigkeitsfokus = next(f for f in feats if f["name"] == "Fertigkeitsfokus")
    assert fertigkeitsfokus["type"] == "general"
    assert fertigkeitsfokus["subChoiceType"] == "skill"

    zauberfokus = next(f for f in feats if f["name"] == "Zauberfokus")
    assert zauberfokus["subChoiceType"] == "spell_school"

    ausweichen = next(f for f in feats if f["name"] == "Ausweichen")
    assert ausweichen["subChoiceType"] is None


def test_list_feats_filters_by_character_prerequisites(client: TestClient, db_session: Session) -> None:
    """A `character_id` query param reduces the catalog to only the feats
    this character currently qualifies for (`rules/feat_prerequisites.py`)
    — level-up's own feat picker relies on this (`useLevelUpOptions.ts`)."""
    seed_races(db_session)
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_class_abilities(db_session)
    seed_skills(db_session)
    seed_feats(db_session)

    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    # flex_ability="ST" (not "GE") keeps GE at the default 12 — one below
    # Ausweichen's GE-13 requirement — and a level-1 Waldläufer (full BAB
    # progression) has BAB 1, well below Kritischer-Treffer-Fokus's BAB 9.
    character_id = client.post(
        "/api/characters", json=_character_payload(user_id, race_id, db_session, flex_ability="ST")
    ).json()["id"]

    unfiltered = client.get("/api/feats").json()
    filtered_response = client.get("/api/feats", params={"character_id": character_id})
    assert filtered_response.status_code == 200
    filtered = filtered_response.json()
    filtered_names = {f["name"] for f in filtered}

    assert len(filtered) < len(unfiltered)
    assert "Verbesserte Initiative" in filtered_names  # no prerequisites at all
    assert "Ausweichen" not in filtered_names  # GE 13 required, character has 12
    assert "Kritischer-Treffer-Fokus" not in filtered_names  # BAB 9 required, character has 1

    missing_character = client.get("/api/feats", params={"character_id": "00000000-0000-0000-0000-000000000000"})
    assert missing_character.status_code == 404
