"""Armor beyond its AC bonus — Rüstungsmalus, the non-proficiency attack
penalty and the speed reduction (`rules/armor.py`,
`scripts/import_ruestungen_prd.py`)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from test_characters import _character_payload, _create_user, _human_race_id


def _character(client: TestClient, db_session: Session, class_name: str) -> str:
    payload = _character_payload(
        _create_user(client), _human_race_id(client, db_session), db_session,
        classes=[{"class_name": class_name, "level": 1}],
    )
    payload["flex_ability"] = "ST"
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _item_id(client: TestClient, name: str) -> str:
    return next(i["id"] for i in client.get("/api/items").json() if i["name"] == name)


def _equip(client: TestClient, character_id: str, slot: str, name: str, **gear) -> dict:
    item_id = _item_id(client, name)
    assert client.post(f"/api/characters/{character_id}/gear", json={"item_id": item_id, "quantity": 1}).status_code == 201
    if gear:
        assert client.patch(f"/api/characters/{character_id}/gear/{item_id}", json=gear).status_code == 200
    response = client.put(f"/api/characters/{character_id}/slots/{slot}", json={"item_id": item_id})
    assert response.status_code == 200, response.text
    return client.get(f"/api/characters/{character_id}").json()


def _skill(sheet: dict, label: str) -> int:
    return int(next(s for s in sheet["skills"] if s["label"] == label)["value"])


def test_armor_check_penalty_on_st_and_ge_skills(client: TestClient, db_session: Session) -> None:
    character_id = _character(client, db_session, "Kämpfer")
    before = client.get(f"/api/characters/{character_id}").json()
    armored = _equip(client, character_id, "ruestung", "Brustplatte")

    assert _skill(armored, "Klettern") == _skill(before, "Klettern") - 4
    assert _skill(armored, "Akrobatik") == _skill(before, "Akrobatik") - 4
    assert _skill(armored, "Wahrnehmung") == _skill(before, "Wahrnehmung")
    breakdown = next(s for s in armored["skills"] if s["label"] == "Klettern")["breakdown"]
    assert {"label": "Rüstungsmalus (Brustplatte)", "value": -4} in breakdown

    # Armor and shield add up.
    with_shield = _equip(client, character_id, "schild", "Schwerer Stahlschild")
    assert _skill(with_shield, "Klettern") == _skill(before, "Klettern") - 6


def test_masterwork_lowers_the_penalty(client: TestClient, db_session: Session) -> None:
    character_id = _character(client, db_session, "Kämpfer")
    before = client.get(f"/api/characters/{character_id}").json()
    armored = _equip(client, character_id, "ruestung", "Kettenhemd", is_masterwork=True)
    assert _skill(armored, "Klettern") == _skill(before, "Klettern") - 1


def test_medium_and_heavy_armor_slow_the_wearer(client: TestClient, db_session: Session) -> None:
    light = _equip(client, _character(client, db_session, "Kämpfer"), "ruestung", "Kettenhemd")
    medium = _equip(client, _character(client, db_session, "Kämpfer"), "ruestung", "Brustplatte")
    heavy = _equip(client, _character(client, db_session, "Kämpfer"), "ruestung", "Ritterrüstung")

    assert light["speed"] == "9 m"
    assert medium["speed"] == "6 m"
    assert heavy["speed"] == "6 m"


def test_non_proficient_armor_penalizes_attacks(client: TestClient, db_session: Session) -> None:
    """A Magier isn't proficient with any armor; a Kämpfer is."""
    def attack(sheet: dict) -> int:
        return int(next(a for a in sheet["weaponAttacks"])["attackBonus"].split("/")[0])

    magier_id = _character(client, db_session, "Magier")
    _equip(client, magier_id, "hauptwaffe", "Dolch")
    unarmored = client.get(f"/api/characters/{magier_id}").json()
    armored = _equip(client, magier_id, "ruestung", "Kettenhemd")
    assert attack(armored) == attack(unarmored) - 2

    kaempfer_id = _character(client, db_session, "Kämpfer")
    _equip(client, kaempfer_id, "hauptwaffe", "Dolch")
    fighter_before = client.get(f"/api/characters/{kaempfer_id}").json()
    assert attack(_equip(client, kaempfer_id, "ruestung", "Kettenhemd")) == attack(fighter_before)


def test_tower_shield_caps_dex_bonus(client: TestClient, db_session: Session) -> None:
    payload = _character_payload(
        _create_user(client), _human_race_id(client, db_session), db_session,
        classes=[{"class_name": "Kämpfer", "level": 1}],
        ability_scores={"ST": 10, "GE": 18, "KO": 10, "IN": 10, "WE": 10, "CH": 10},
    )
    payload["flex_ability"] = "ST"
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.text
    sheet = _equip(client, response.json()["id"], "schild", "Turmschild")
    dex = next(e for e in sheet["armorClassBreakdown"] if e["label"].startswith("Geschicklichkeit"))
    assert dex["value"] == 2


def test_catalog_has_the_prd_armor_table(client: TestClient, db_session: Session) -> None:
    items = {i["name"]: i for i in client.get("/api/items").json()}
    assert {"Waffenrock", "Fellrüstung", "Kettenpanzer", "Schienenpanzer", "Bänderpanzer", "Plattenpanzer",
            "Ritterrüstung", "Tartsche", "Leichter Holzschild", "Schwerer Stahlschild"} <= set(items)
    assert "Halbplatte" not in items and "Vollplatte" not in items


def test_barbarian_fast_movement_and_armor(client: TestClient, db_session: Session) -> None:
    """Schnelle Bewegung counts before the armor's reduction and not at all
    in heavy armor: 9 + 3 = 12 m; medium armor 12 -> 9 m; heavy 9 -> 6 m."""
    unarmored = client.get(f"/api/characters/{_character(client, db_session, 'Barbar')}").json()
    medium = _equip(client, _character(client, db_session, "Barbar"), "ruestung", "Brustplatte")
    heavy = _equip(client, _character(client, db_session, "Barbar"), "ruestung", "Ritterrüstung")

    assert unarmored["speed"] == "12 m"
    assert medium["speed"] == "9 m"
    assert heavy["speed"] == "6 m"
