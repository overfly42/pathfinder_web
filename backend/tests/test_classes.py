from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.class_ability_seed import seed_class_abilities
from app.seed.class_seed import seed_classes


def test_list_classes_exposes_bonus_feat_levels_from_real_data(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_abilities(db_session)

    response = client.get("/api/classes")
    assert response.status_code == 200
    classes = {c["name"]: c for c in response.json()}

    assert classes["Krieger"]["bonusFeatLevels"] == [1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
    # No seeded bonus-feat data for other classes -> empty, not a guess.
    assert classes["Waldläufer"]["bonusFeatLevels"] == []
