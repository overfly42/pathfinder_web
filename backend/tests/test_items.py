from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.item_seed import seed_items
from app.seed.weapon_ability_seed import seed_weapon_abilities

from test_characters import _character_payload, _create_user, _elf_race_id, _item_id


def _weapon_ability_id(client: TestClient, db_session: Session, name: str) -> str:
    seed_weapon_abilities(db_session)
    abilities = client.get("/api/weapon-abilities").json()
    return next(a["id"] for a in abilities if a["name"] == name)


def test_list_items_is_database_backed(client: TestClient, db_session: Session) -> None:
    seed_items(db_session)

    response = client.get("/api/items")
    assert response.status_code == 200
    items = response.json()

    assert len(items) == 507
    assert all({"id", "name", "category", "price", "acBonus", "maxDexBonus"} <= set(item) for item in items)

    dolch = next(i for i in items if i["name"] == "Dolch")
    assert dolch["category"] == "weapon"
    assert dolch["price"] == 2
    assert dolch["acBonus"] is None

    lederruestung = next(i for i in items if i["name"] == "Lederrüstung")
    assert lederruestung["category"] == "armor"
    assert lederruestung["acBonus"] == 2
    assert lederruestung["maxDexBonus"] == 6


def _create_character(client: TestClient, db_session: Session) -> str:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    response = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session))
    assert response.status_code == 201
    return response.json()["id"]


def test_add_gear_creates_inventory_row_and_merges_quantity(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    dolch_id = _item_id(client, db_session, "Dolch")

    response = client.post(f"/api/characters/{character_id}/gear", json={"item_id": dolch_id, "quantity": 2})
    assert response.status_code == 201
    assert {"item_id": dolch_id, "quantity": 2} in response.json()["gear"]

    # Adding the same item again merges quantity rather than erroring/duplicating.
    response = client.post(f"/api/characters/{character_id}/gear", json={"item_id": dolch_id, "quantity": 3})
    assert response.status_code == 201
    assert {"item_id": dolch_id, "quantity": 5} in response.json()["gear"]


def test_add_gear_with_unknown_item_is_rejected(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    response = client.post(
        f"/api/characters/{character_id}/gear",
        json={"item_id": "00000000-0000-0000-0000-000000000000", "quantity": 1},
    )
    assert response.status_code == 422


def test_patch_gear_updates_quantity_enhancement_and_properties(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    dolch_id = _item_id(client, db_session, "Dolch")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": dolch_id, "quantity": 1})

    response = client.patch(
        f"/api/characters/{character_id}/gear/{dolch_id}",
        json={"quantity": 4, "enhancement": 2, "properties": ["Flammend"]},
    )
    assert response.status_code == 200

    sheet = client.get(f"/api/characters/{character_id}").json()
    dolch = next(g for g in sheet["gear"] if g["name"] == "Dolch")
    assert dolch["qty"] == 4
    assert dolch["enhancement"] == "+2"
    assert dolch["properties"] == ["Flammend"]


def test_delete_gear_removes_item(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    dolch_id = _item_id(client, db_session, "Dolch")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": dolch_id, "quantity": 1})

    response = client.delete(f"/api/characters/{character_id}/gear/{dolch_id}")
    assert response.status_code == 204

    sheet = client.get(f"/api/characters/{character_id}").json()
    assert sheet["gear"] == []


def test_equip_armor_and_shield_updates_armor_class(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    lederruestung_id = _item_id(client, db_session, "Lederrüstung")  # +2 AC, max dex +6
    turmschild_id = _item_id(client, db_session, "Turmschild")  # +4 AC

    client.post(f"/api/characters/{character_id}/gear", json={"item_id": lederruestung_id, "quantity": 1})
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": turmschild_id, "quantity": 1})

    base_ac = client.get(f"/api/characters/{character_id}").json()["armorClass"]

    response = client.put(f"/api/characters/{character_id}/slots/ruestung", json={"item_id": lederruestung_id})
    assert response.status_code == 200
    response = client.put(f"/api/characters/{character_id}/slots/schild", json={"item_id": turmschild_id})
    assert response.status_code == 200

    sheet = client.get(f"/api/characters/{character_id}").json()
    assert sheet["armorClass"] == base_ac + 2 + 4

    ruestung_slot = next(s for s in sheet["equipmentSlots"] if s["key"] == "ruestung")
    assert ruestung_slot["selected"] == lederruestung_id
    schild_slot = next(s for s in sheet["equipmentSlots"] if s["key"] == "schild")
    assert schild_slot["selected"] == turmschild_id

    # Unequip clears the slot and reverts the AC.
    response = client.put(f"/api/characters/{character_id}/slots/ruestung", json={"item_id": None})
    assert response.status_code == 200
    sheet = client.get(f"/api/characters/{character_id}").json()
    assert sheet["armorClass"] == base_ac + 4


def test_equip_item_wrong_category_for_slot_is_rejected(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    turmschild_id = _item_id(client, db_session, "Turmschild")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": turmschild_id, "quantity": 1})

    response = client.put(f"/api/characters/{character_id}/slots/ruestung", json={"item_id": turmschild_id})
    assert response.status_code == 422


def test_equip_unowned_item_is_rejected(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    lederruestung_id = _item_id(client, db_session, "Lederrüstung")

    response = client.put(f"/api/characters/{character_id}/slots/ruestung", json={"item_id": lederruestung_id})
    assert response.status_code == 422


def test_equip_unknown_slot_is_rejected(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    response = client.put(f"/api/characters/{character_id}/slots/nonexistent-slot", json={"item_id": None})
    assert response.status_code == 422


def test_list_weapon_abilities_is_database_backed(client: TestClient, db_session: Session) -> None:
    seed_weapon_abilities(db_session)

    response = client.get("/api/weapon-abilities")
    assert response.status_code == 200
    abilities = response.json()

    assert len(abilities) == 93
    assert all(
        {"id", "name", "bonusEquivalent", "applicableCategories", "restrictionNote", "description"} <= set(a)
        for a in abilities
    )

    anarchie = next(a for a in abilities if a["name"] == "Anarchie")
    assert anarchie["bonusEquivalent"] == 2
    assert set(anarchie["applicableCategories"]) == {"melee", "ranged", "ammunition"}


def test_patch_gear_sets_and_replaces_special_abilities(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    langschwert_id = _item_id(client, db_session, "Langschwert")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": langschwert_id, "quantity": 1})
    anarchie_id = _weapon_ability_id(client, db_session, "Anarchie")
    aufflammen_id = _weapon_ability_id(client, db_session, "Aufflammen")

    response = client.patch(
        f"/api/characters/{character_id}/gear/{langschwert_id}",
        json={"special_ability_ids": [anarchie_id]},
    )
    assert response.status_code == 200

    sheet = client.get(f"/api/characters/{character_id}").json()
    langschwert = next(g for g in sheet["gear"] if g["name"] == "Langschwert")
    assert len(langschwert["specialAbilities"]) == 1
    assert langschwert["specialAbilities"][0]["name"] == "Anarchie"
    assert langschwert["specialAbilities"][0]["description"]

    # A second PATCH replaces (not appends to) the ability set.
    response = client.patch(
        f"/api/characters/{character_id}/gear/{langschwert_id}",
        json={"special_ability_ids": [aufflammen_id]},
    )
    assert response.status_code == 200
    sheet = client.get(f"/api/characters/{character_id}").json()
    langschwert = next(g for g in sheet["gear"] if g["name"] == "Langschwert")
    assert [a["name"] for a in langschwert["specialAbilities"]] == ["Aufflammen"]

    # An empty list clears it.
    response = client.patch(f"/api/characters/{character_id}/gear/{langschwert_id}", json={"special_ability_ids": []})
    assert response.status_code == 200
    sheet = client.get(f"/api/characters/{character_id}").json()
    langschwert = next(g for g in sheet["gear"] if g["name"] == "Langschwert")
    assert "specialAbilities" not in langschwert


def test_patch_gear_with_unknown_special_ability_id_is_rejected(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    dolch_id = _item_id(client, db_session, "Dolch")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": dolch_id, "quantity": 1})

    response = client.patch(
        f"/api/characters/{character_id}/gear/{dolch_id}",
        json={"special_ability_ids": ["00000000-0000-0000-0000-000000000000"]},
    )
    assert response.status_code == 422
