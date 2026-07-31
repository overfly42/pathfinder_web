from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.item_seed import seed_items


def test_list_items_is_database_backed(client: TestClient, db_session: Session) -> None:
    seed_items(db_session)

    response = client.get("/api/items")
    assert response.status_code == 200
    items = response.json()

    assert len(items) == 55
    assert all({"id", "name", "category", "price"} <= set(item) for item in items)

    dolch = next(i for i in items if i["name"] == "Dolch")
    assert dolch["category"] == "weapon"
    assert dolch["price"] == 2

    lederruestung = next(i for i in items if i["name"] == "Lederrüstung")
    assert lederruestung["category"] == "armor"
