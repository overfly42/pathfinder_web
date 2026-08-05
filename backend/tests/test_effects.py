from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BaseClassAbility, BaseCondition, BaseSpell, CharacterEffect

from test_characters import _spells_by_class
from test_items import _create_character


def _make_condition(db_session: Session, name: str = "Gift: Riesenspinnengift") -> str:
    condition = BaseCondition(name=name, description="1W2 STÄ-Schaden, Häufigkeit 1/Runde für 4 Runden.")
    db_session.add(condition)
    db_session.commit()
    return str(condition.id)


def _persistent_spell_id(client: TestClient, db_session: Session) -> str:
    _, spells_by_name = _spells_by_class(client, db_session, "Magier")
    spell_id = next(iter(spells_by_name.values()))
    spell = db_session.get(BaseSpell, spell_id)
    spell.is_persistent_effect = True
    db_session.commit()
    return spell_id


def _persistent_class_ability_id(character_id: str, db_session: Session) -> str:
    ability = db_session.scalars(select(BaseClassAbility)).first()
    ability.is_persistent_effect = True
    db_session.commit()
    return str(ability.id)


def test_activate_condition_effect_creates_row(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    condition_id = _make_condition(db_session)

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": condition_id, "level": 3, "duration_remaining": 10},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "condition"
    assert body["level"] == 3
    assert body["duration_remaining"] == 10


def test_activate_unknown_condition_is_rejected(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 422


def test_activate_non_persistent_spell_is_rejected(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    _, spells_by_name = _spells_by_class(client, db_session, "Magier")
    spell_id = next(iter(spells_by_name.values()))

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "spell", "source_id": spell_id},
    )
    assert response.status_code == 422


def test_activate_persistent_spell_is_accepted(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    spell_id = _persistent_spell_id(client, db_session)

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "spell", "source_id": spell_id, "level": 5, "duration_remaining": 5},
    )
    assert response.status_code == 201


def test_activate_persistent_class_ability_is_accepted(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    ability_id = _persistent_class_ability_id(character_id, db_session)

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "class_ability", "source_id": ability_id},
    )
    assert response.status_code == 201


def test_same_effect_can_be_active_twice_from_independent_instances(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    condition_id = _make_condition(db_session)

    first = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": condition_id, "duration_remaining": 3},
    )
    second = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": condition_id, "duration_remaining": 8},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]

    rows = db_session.scalars(select(CharacterEffect)).all()
    assert len(rows) == 2


def test_remove_effect_deletes_it(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    condition_id = _make_condition(db_session)
    effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": condition_id, "duration_remaining": 3},
    ).json()["id"]

    response = client.delete(f"/api/characters/{character_id}/effects/{effect_id}")
    assert response.status_code == 204
    assert db_session.get(CharacterEffect, effect_id) is None


def test_advance_time_round_decrements_duration_and_expires_at_zero(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    condition_id = _make_condition(db_session, "Verängstigt")
    effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": condition_id, "duration_remaining": 2},
    ).json()["id"]

    response = client.post(f"/api/characters/{character_id}/advance-time", json={"unit": "round"})
    assert response.status_code == 200
    remaining = response.json()
    assert len(remaining) == 1
    assert remaining[0]["id"] == effect_id
    assert remaining[0]["duration_remaining"] == 1

    response = client.post(f"/api/characters/{character_id}/advance-time", json={"unit": "round"})
    assert response.json() == []
    assert db_session.get(CharacterEffect, effect_id) is None


def test_advance_time_day_clears_plain_effect_but_not_frequency_tracked_one(
    client: TestClient, db_session: Session
) -> None:
    character_id = _create_character(client, db_session)
    buff_id = _make_condition(db_session, "Gesegnet")
    poison_id = _make_condition(db_session, "Gift")

    buff_effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": buff_id, "duration_remaining": 50},
    ).json()["id"]
    poison_effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={
            "source_type": "condition",
            "source_id": poison_id,
            "incubation_remaining": 10,
            "frequency_rounds": 1,
            "successes_required": 2,
        },
    ).json()["id"]

    response = client.post(f"/api/characters/{character_id}/advance-time", json={"unit": "day"})
    assert response.status_code == 200
    remaining_ids = {row["id"] for row in response.json()}
    assert remaining_ids == {poison_effect_id}
    assert db_session.get(CharacterEffect, buff_effect_id) is None
    assert db_session.get(CharacterEffect, poison_effect_id) is not None


def test_save_result_success_increments_and_cures_at_threshold(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    poison_id = _make_condition(db_session, "Gift")
    effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={
            "source_type": "condition",
            "source_id": poison_id,
            "level": 4,
            "frequency_rounds": 1,
            "successes_required": 2,
        },
    ).json()["id"]

    first = client.post(f"/api/characters/{character_id}/effects/{effect_id}/save-result", json={"success": True})
    assert first.status_code == 200
    body = first.json()
    assert body["successes_current"] == 1
    assert db_session.get(CharacterEffect, effect_id) is not None

    second = client.post(f"/api/characters/{character_id}/effects/{effect_id}/save-result", json={"success": True})
    assert second.status_code == 200
    assert db_session.get(CharacterEffect, effect_id) is None


def test_save_result_failure_resets_successes_without_changing_level(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    poison_id = _make_condition(db_session, "Gift")
    effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={
            "source_type": "condition",
            "source_id": poison_id,
            "level": 4,
            "frequency_rounds": 1,
            "successes_required": 2,
        },
    ).json()["id"]
    client.post(f"/api/characters/{character_id}/effects/{effect_id}/save-result", json={"success": True})

    response = client.post(f"/api/characters/{character_id}/effects/{effect_id}/save-result", json={"success": False})
    assert response.status_code == 200
    body = response.json()
    assert body["successes_current"] == 0
    assert body["level"] == 4


def test_save_result_rejected_for_effect_without_frequency(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    condition_id = _make_condition(db_session, "Gesegnet")
    effect_id = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "condition", "source_id": condition_id, "duration_remaining": 5},
    ).json()["id"]

    response = client.post(f"/api/characters/{character_id}/effects/{effect_id}/save-result", json={"success": True})
    assert response.status_code == 422
