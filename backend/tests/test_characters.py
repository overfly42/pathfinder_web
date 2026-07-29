from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Character, CharacterAbilityChoice
from app.rules.race_abilities import HANDLERS
from app.seed.race_seed import seed_races

DEFAULT_ABILITY_SCORES = {"ST": 10, "GE": 12, "KO": 13, "IN": 10, "WE": 10, "CH": 8}


def _create_user(client: TestClient, name: str = "Anna") -> str:
    return client.post("/api/users", json={"name": name}).json()["id"]


def _race_id(client: TestClient, db_session: Session, name: str) -> str:
    seed_races(db_session)
    races = client.get("/api/races").json()
    return next(r["id"] for r in races if r["name"] == name)


def _elf_race_id(client: TestClient, db_session: Session) -> str:
    return _race_id(client, db_session, "Elf")


def _human_race_id(client: TestClient, db_session: Session) -> str:
    return _race_id(client, db_session, "Mensch")


def _character_payload(user_id: str, race_id: str, **overrides) -> dict:
    payload = {
        "name": "Elyra",
        "user_id": user_id,
        "race_id": race_id,
        "class_name": "Waldläufer",
        "current_hit_points": 8,
        "ability_scores": DEFAULT_ABILITY_SCORES,
        "point_budget": 20,
    }
    payload.update(overrides)
    return payload


def test_create_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post("/api/characters", json=_character_payload(user_id, race_id))
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Elyra"
    assert body["race_id"] == race_id
    assert body["level"] == 1
    assert body["current_hit_points"] == 8
    assert body["ability_scores"] == DEFAULT_ABILITY_SCORES
    assert body["point_budget"] == 20
    assert body["flex_ability"] is None


def test_create_character_with_unknown_race_is_rejected(client: TestClient) -> None:
    user_id = _create_user(client)
    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, "00000000-0000-0000-0000-000000000000"),
    )
    assert response.status_code == 422


def test_create_character_over_point_buy_budget_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, ability_scores={"ST": 18, "GE": 18, "KO": 18, "IN": 18, "WE": 18, "CH": 18}
        ),
    )
    assert response.status_code == 422


def test_create_character_with_ability_score_out_of_range_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, ability_scores={**DEFAULT_ABILITY_SCORES, "ST": 19}),
    )
    assert response.status_code == 422


def test_create_character_for_flex_race_requires_flex_ability(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    response = client.post("/api/characters", json=_character_payload(user_id, race_id))
    assert response.status_code == 422


def test_create_character_for_flex_race_with_flex_ability_succeeds(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    response = client.post("/api/characters", json=_character_payload(user_id, race_id, flex_ability="GE"))
    assert response.status_code == 201
    assert response.json()["flex_ability"] == "GE"


def test_create_character_for_flex_race_persists_choice_via_replacement_system(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    created = client.post("/api/characters", json=_character_payload(user_id, race_id, flex_ability="ST")).json()

    character = db_session.get(Character, created["id"])
    choices = db_session.scalars(
        select(CharacterAbilityChoice).where(CharacterAbilityChoice.character_id == character.id)
    ).all()
    assert len(choices) == 1
    # The stored row is an ability_id resolved through RaceAbilityReplacement,
    # not a raw "ST" string — resolving it back through HANDLERS must agree
    # with what was requested.
    attribute, value = HANDLERS[choices[0].ability_id]()
    assert (attribute, value) == ("ST", 2)


def test_create_character_for_non_flex_race_rejects_flex_ability(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post("/api/characters", json=_character_payload(user_id, race_id, flex_ability="GE"))
    assert response.status_code == 422


def test_get_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post("/api/characters", json=_character_payload(user_id, race_id)).json()

    response = client.get(f"/api/characters/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Elyra"
    assert response.json()["ability_scores"] == DEFAULT_ABILITY_SCORES


def test_get_unknown_character_returns_404(client: TestClient) -> None:
    response = client.get("/api/characters/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_rename_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post("/api/characters", json=_character_payload(user_id, race_id)).json()

    response = client.patch(f"/api/characters/{created['id']}", json={"name": "Elyra Silberauge"})
    assert response.status_code == 200
    assert response.json()["name"] == "Elyra Silberauge"


def test_delete_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post("/api/characters", json=_character_payload(user_id, race_id)).json()

    response = client.delete(f"/api/characters/{created['id']}")
    assert response.status_code == 204

    response = client.get(f"/api/characters/{created['id']}")
    assert response.status_code == 404


def test_mock_character_fixtures_still_served(client: TestClient) -> None:
    response = client.get("/api/characters/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Elyra Silberauge"
