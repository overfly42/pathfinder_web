from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.trait_seed import seed_traits


def test_list_traits_is_database_backed(client: TestClient, db_session: Session) -> None:
    seed_traits(db_session)

    response = client.get("/api/traits")
    assert response.status_code == 200
    traits = response.json()

    assert len(traits) == 10
    assert all({"id", "name", "description", "area"} <= set(trait) for trait in traits)

    reaktionsschnell = next(t for t in traits if t["name"] == "Reaktionsschnell")
    assert "Initiativewurf" in reaktionsschnell["description"]
    assert reaktionsschnell["area"] == "combat"
