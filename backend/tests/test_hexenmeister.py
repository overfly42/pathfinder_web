"""Hexenmeister (`rules/classes/hexenmeister.py`) — first real content:
Meeresblutlinie's "Wasserstoß" bloodline power, granted at real class level
1 via the already-seeded `base_class_ability_grants` (option_choice_id
scoped to the chosen bloodline)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.rules.classes.hexenmeister import WASSERSTOSS_ABILITY_ID

from test_characters import DEFAULT_ABILITY_SCORES, _character_payload, _create_user, _elf_race_id


def test_wasserstoss_uses_per_day_scales_with_charisma_modifier(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Hexenmeister", "level": 1, "options": {"bloodline": ["Meeresblutlinie"]}}],
        ability_scores={**DEFAULT_ABILITY_SCORES, "CH": 14},
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201
    character_id = response.json()["id"]

    sheet = client.get(f"/api/characters/{character_id}").json()
    action = next(a for a in sheet["actions"] if a["sourceId"] == str(WASSERSTOSS_ABILITY_ID))
    assert action["name"] == "Wasserstoß"
    # CH 14 -> mod +2, "täglich in Höhe deines CH-Modifikators +3" -> 5.
    assert action["usesPerDay"] == 5
    assert action["usesRemainingToday"] == 5
    # "SG 10 + deine ½ Stufe als Hexenmeister + deinen CH-Modifikator" -> level 1 // 2 = 0 -> 12.
    assert action["dc"] == 12


def test_wasserstoss_dc_scales_with_hexenmeister_level(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Hexenmeister", "level": 4, "options": {"bloodline": ["Meeresblutlinie"]}}],
        ability_scores={**DEFAULT_ABILITY_SCORES, "CH": 14},
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201
    character_id = response.json()["id"]

    sheet = client.get(f"/api/characters/{character_id}").json()
    action = next(a for a in sheet["actions"] if a["sourceId"] == str(WASSERSTOSS_ABILITY_ID))
    # Level 4 // 2 = 2, CH mod +2 -> 10 + 2 + 2 = 14.
    assert action["dc"] == 14
