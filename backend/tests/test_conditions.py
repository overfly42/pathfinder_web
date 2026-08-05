from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.condition_seed import seed_conditions


def test_list_conditions_is_database_backed(client: TestClient, db_session: Session) -> None:
    seed_conditions(db_session)

    response = client.get("/api/conditions")
    assert response.status_code == 200
    conditions = response.json()

    assert len(conditions) == 79
    assert all({"id", "name", "description", "type"} <= set(condition) for condition in conditions)

    veraengstigt = next(c for c in conditions if c["name"] == "Verängstigt")
    assert veraengstigt["type"] == "condition"
    assert "flieht vor der Quelle ihrer Furcht" in veraengstigt["description"]

    wyverngift = next(c for c in conditions if c["name"] == "Wyverngift")
    assert wyverngift["type"] == "poison"
    assert "SG: 17" in wyverngift["description"]

    beulenpest = next(c for c in conditions if c["name"] == "Beulenpest")
    assert beulenpest["type"] == "disease"
    assert "Frequenz 1/ Tag" in beulenpest["description"]
