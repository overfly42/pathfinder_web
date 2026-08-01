from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.class_ability_seed import seed_class_abilities
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.feat_seed import seed_feats
from app.seed.race_seed import seed_races
from app.seed.skill_seed import seed_skills


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

    assert len(feats) == 325
    assert all({"id", "name", "description", "type"} <= set(feat) for feat in feats)

    waffenfokus = next(f for f in feats if f["name"] == "Waffenfokus")
    assert waffenfokus["type"] == "combat"

    fertigkeitsfokus = next(f for f in feats if f["name"] == "Fertigkeitsfokus")
    assert fertigkeitsfokus["type"] == "general"
