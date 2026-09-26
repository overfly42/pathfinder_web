"""Mönch's "Rüstungsklassenbonus" (`rules/classes/moench.py`) — AC/CMD bonus
while unarmored and shieldless, scaled by Wisdom mod (Charisma for a
Beschuppte Faust archetype character) plus a level-4+ progression."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from test_characters import DEFAULT_ABILITY_SCORES, _character_payload, _create_user, _elf_race_id, _item_id


def _create_moench(
    client: TestClient,
    db_session: Session,
    *,
    level: int = 1,
    archetypes: list[str] | None = None,
    ability_scores: dict[str, int] | None = None,
    gear: list[dict] | None = None,
    equip: tuple[str, str] | None = None,
    point_budget: int = 20,
) -> dict:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Mönch", "level": level, "archetypes": archetypes or []}],
        ability_scores=ability_scores or DEFAULT_ABILITY_SCORES,
        gear=gear or [],
        point_budget=point_budget,
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.json()
    character_id = response.json()["id"]
    if equip is not None:
        slot, item_id = equip
        assert client.put(f"/api/characters/{character_id}/slots/{slot}", json={"item_id": item_id}).status_code == 200
    return client.get(f"/api/characters/{character_id}").json()


def test_ruestungsklassenbonus_adds_wisdom_mod_to_ac_and_cmd_when_unarmored(
    client: TestClient, db_session: Session
) -> None:
    body = _create_moench(client, db_session, level=1, ability_scores={**DEFAULT_ABILITY_SCORES, "WE": 16})

    assert {"label": "Rüstungsklassenbonus", "value": 3} in body["armorClassBreakdown"]

    combat = {c["key"]: c["value"] for c in body["combat"]}
    bab = int(combat["bab"])
    str_mod = int(combat["cmb"]) - bab
    dex_mod = next(e["value"] for e in body["armorClassBreakdown"] if e["label"] == "Geschicklichkeit")
    assert int(combat["cmd"]) == 10 + bab + str_mod + dex_mod + 3


def test_ruestungsklassenbonus_scales_with_level(client: TestClient, db_session: Session) -> None:
    level_1 = _create_moench(client, db_session, level=1)
    level_4 = _create_moench(client, db_session, level=4)
    level_8 = _create_moench(client, db_session, level=8, ability_scores={**DEFAULT_ABILITY_SCORES, "WE": 16})

    # WE 10 -> +0 mod at levels 1/4, so only the level-based part shows.
    assert not any(e["label"] == "Rüstungsklassenbonus" for e in level_1["armorClassBreakdown"])
    assert {"label": "Rüstungsklassenbonus", "value": 1} in level_4["armorClassBreakdown"]
    # Level 8 (+2) plus WE 16's +3 mod.
    assert {"label": "Rüstungsklassenbonus", "value": 5} in level_8["armorClassBreakdown"]


def test_ruestungsklassenbonus_lost_when_armored_or_shielded(client: TestClient, db_session: Session) -> None:
    lederruestung_id = _item_id(client, db_session, "Lederrüstung")
    rundschild_id = _item_id(client, db_session, "Rundschild")
    ability_scores = {**DEFAULT_ABILITY_SCORES, "WE": 16}

    armored = _create_moench(
        client,
        db_session,
        level=1,
        ability_scores=ability_scores,
        gear=[{"item_id": lederruestung_id, "quantity": 1}],
        equip=("ruestung", lederruestung_id),
    )
    shielded = _create_moench(
        client,
        db_session,
        level=1,
        ability_scores=ability_scores,
        gear=[{"item_id": rundschild_id, "quantity": 1}],
        equip=("schild", rundschild_id),
    )

    assert not any(e["label"] == "Rüstungsklassenbonus" for e in armored["armorClassBreakdown"])
    assert not any(e["label"] == "Rüstungsklassenbonus" for e in shielded["armorClassBreakdown"])


def test_ruestungsklassenbonus_uses_charisma_for_beschuppte_faust(client: TestClient, db_session: Session) -> None:
    body = _create_moench(
        client,
        db_session,
        level=1,
        archetypes=["Beschuppte Faust"],
        ability_scores={"ST": 7, "GE": 10, "KO": 10, "IN": 10, "WE": 16, "CH": 18},
        point_budget=25,
    )

    # CH 18 -> +4, not WE 16's +3 - proves Drachenmacht's WIS->CHA swap is read.
    assert {"label": "Rüstungsklassenbonus", "value": 4} in body["armorClassBreakdown"]
