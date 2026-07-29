from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.race_seed import seed_races


def _create_user(client: TestClient, name: str = "Anna") -> str:
    return client.post("/api/users", json={"name": name}).json()["id"]


def _elf_race_id(client: TestClient, db_session: Session) -> str:
    seed_races(db_session)
    races = client.get("/api/races").json()
    return next(r["id"] for r in races if r["name"] == "Elf")


def test_create_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json={
            "name": "Elyra",
            "user_id": user_id,
            "race_id": race_id,
            "class_name": "Waldläufer",
            "current_hit_points": 8,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Elyra"
    assert body["race_id"] == race_id
    assert body["level"] == 1
    assert body["current_hit_points"] == 8


def test_create_character_with_unknown_race_is_rejected(client: TestClient) -> None:
    user_id = _create_user(client)
    response = client.post(
        "/api/characters",
        json={
            "name": "Elyra",
            "user_id": user_id,
            "race_id": "00000000-0000-0000-0000-000000000000",
            "class_name": "Waldläufer",
            "current_hit_points": 8,
        },
    )
    assert response.status_code == 422


def test_get_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post(
        "/api/characters",
        json={"name": "Elyra", "user_id": user_id, "race_id": race_id, "class_name": "Waldläufer", "current_hit_points": 8},
    ).json()

    response = client.get(f"/api/characters/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Elyra"


def test_get_unknown_character_returns_404(client: TestClient) -> None:
    response = client.get("/api/characters/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_rename_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post(
        "/api/characters",
        json={"name": "Elyra", "user_id": user_id, "race_id": race_id, "class_name": "Waldläufer", "current_hit_points": 8},
    ).json()

    response = client.patch(f"/api/characters/{created['id']}", json={"name": "Elyra Silberauge"})
    assert response.status_code == 200
    assert response.json()["name"] == "Elyra Silberauge"


def test_delete_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post(
        "/api/characters",
        json={"name": "Elyra", "user_id": user_id, "race_id": race_id, "class_name": "Waldläufer", "current_hit_points": 8},
    ).json()

    response = client.delete(f"/api/characters/{created['id']}")
    assert response.status_code == 204

    response = client.get(f"/api/characters/{created['id']}")
    assert response.status_code == 404


def test_mock_character_fixtures_still_served(client: TestClient) -> None:
    response = client.get("/api/characters/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Elyra Silberauge"
