from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.feat_seed import seed_feats


def test_list_feats_is_database_backed(client: TestClient, db_session: Session) -> None:
    seed_feats(db_session)

    response = client.get("/api/feats")
    assert response.status_code == 200
    feats = response.json()

    assert len(feats) == 16
    assert all({"id", "name", "description", "type"} <= set(feat) for feat in feats)

    waffenfokus = next(f for f in feats if f["name"] == "Waffenfokus")
    assert waffenfokus["type"] == "combat"

    fertigkeitsfokus = next(f for f in feats if f["name"] == "Fertigkeitsfokus")
    assert fertigkeitsfokus["type"] == "general"
