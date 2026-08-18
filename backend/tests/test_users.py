from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.class_seed import seed_classes
from app.seed.race_seed import seed_races

DEFAULT_ABILITY_SCORES = {"ST": 10, "GE": 12, "KO": 13, "IN": 10, "WE": 10, "CH": 8}


def _create_character(client: TestClient, db_session: Session, user_id: str, name: str) -> dict:
    seed_races(db_session)
    seed_classes(db_session)
    race_id = next(r["id"] for r in client.get("/api/races").json() if r["name"] == "Elf")
    return client.post(
        "/api/characters",
        json={
            "name": name,
            "user_id": user_id,
            "race_id": race_id,
            "classes": [{"class_name": "Kämpfer", "level": 1}],
            "favored_class_bonus": {"1": "hp"},
            "ability_scores": DEFAULT_ABILITY_SCORES,
            "point_budget": 20,
        },
    ).json()


def test_list_user_characters_returns_only_that_users_characters(client: TestClient, db_session: Session) -> None:
    owner_id = client.post("/api/users", json={"name": "Anna"}).json()["id"]
    other_id = client.post("/api/users", json={"name": "Bram"}).json()["id"]
    _create_character(client, db_session, owner_id, "Elyra")
    _create_character(client, db_session, other_id, "Not Elyra's")

    response = client.get(f"/api/users/{owner_id}/characters")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert names == ["Elyra"]


def test_list_characters_for_unknown_user_returns_404(client: TestClient) -> None:
    response = client.get("/api/users/00000000-0000-0000-0000-000000000000/characters")
    assert response.status_code == 404


def test_create_user(client: TestClient) -> None:
    response = client.post("/api/users", json={"name": "Anna"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Anna"
    assert "id" in body


def test_list_users_reflects_created_users(client: TestClient) -> None:
    client.post("/api/users", json={"name": "Bram"})
    client.post("/api/users", json={"name": "Anna"})

    response = client.get("/api/users")
    assert response.status_code == 200
    names = [user["name"] for user in response.json()]
    assert names == ["Anna", "Bram"]


def test_rename_user(client: TestClient) -> None:
    created = client.post("/api/users", json={"name": "Anna"}).json()

    response = client.patch(f"/api/users/{created['id']}", json={"name": "Annika"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["name"] == "Annika"


def test_rename_unknown_user_returns_404(client: TestClient) -> None:
    response = client.patch(
        "/api/users/00000000-0000-0000-0000-000000000000", json={"name": "Annika"}
    )
    assert response.status_code == 404


def test_create_user_with_blank_name_is_rejected(client: TestClient) -> None:
    response = client.post("/api/users", json={"name": "   "})
    assert response.status_code == 422
