from fastapi.testclient import TestClient


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
