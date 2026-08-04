from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import BaseItem

from test_characters import _item_id, _spells_by_class
from test_items import _create_character


def _ability_score(sheet: dict, key: str) -> int:
    return next(a["score"] for a in sheet["abilities"] if a["key"] == key)


def test_equip_ability_bonus_item_raises_ability_score_on_sheet(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    belt_id = _item_id(client, db_session, "Gürtel der großen Konstitution +2")

    before = client.get(f"/api/characters/{character_id}").json()
    ko_before = _ability_score(before, "KO")

    client.post(f"/api/characters/{character_id}/gear", json={"item_id": belt_id, "quantity": 1})
    equip = client.put(f"/api/characters/{character_id}/slots/guertel", json={"item_id": belt_id})
    assert equip.status_code == 200

    after = client.get(f"/api/characters/{character_id}").json()
    ko_after = _ability_score(after, "KO")
    assert ko_after == ko_before + 2


def test_ability_bonus_item_only_offered_for_its_own_slot(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    belt_id = _item_id(client, db_session, "Gürtel der großen Konstitution +2")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": belt_id, "quantity": 1})

    sheet = client.get(f"/api/characters/{character_id}").json()
    slots_by_key = {s["key"]: s for s in sheet["equipmentSlots"]}
    guertel_options = {o["value"] for o in slots_by_key["guertel"]["options"]}
    hals_options = {o["value"] for o in slots_by_key["hals"]["options"]}
    assert belt_id in guertel_options
    assert belt_id not in hals_options


def test_equip_wondrous_item_wrong_slot_is_rejected(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    belt_id = _item_id(client, db_session, "Gürtel der großen Konstitution +2")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": belt_id, "quantity": 1})

    response = client.put(f"/api/characters/{character_id}/slots/hals", json={"item_id": belt_id})
    assert response.status_code == 422


def test_both_ring_slots_can_be_equipped_independently(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    ring_a = _item_id(client, db_session, "Chamäleonring")
    ring_b = _item_id(client, db_session, "Flimmerring")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": ring_a, "quantity": 1})
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": ring_b, "quantity": 1})

    left = client.put(f"/api/characters/{character_id}/slots/ring-links", json={"item_id": ring_a})
    right = client.put(f"/api/characters/{character_id}/slots/ring-rechts", json={"item_id": ring_b})
    assert left.status_code == 200
    assert right.status_code == 200

    sheet = client.get(f"/api/characters/{character_id}").json()
    slots_by_key = {s["key"]: s for s in sheet["equipmentSlots"]}
    assert slots_by_key["ring-links"]["selected"] == ring_a
    assert slots_by_key["ring-rechts"]["selected"] == ring_b


def test_wand_charges_start_at_max_and_deplete_on_use(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    wand_id = _item_id(client, db_session, "Zauberstab")
    _, spells_by_name = _spells_by_class(client, db_session, "Magier")
    spell_id = next(iter(spells_by_name.values()))

    client.post(f"/api/characters/{character_id}/gear", json={"item_id": wand_id, "quantity": 1})
    set_spell = client.patch(f"/api/characters/{character_id}/gear/{wand_id}", json={"stored_spell_id": spell_id})
    assert set_spell.status_code == 200

    sheet = client.get(f"/api/characters/{character_id}").json()
    gear = next(g for g in sheet["gear"] if g["id"] == wand_id)
    assert gear["chargesRemaining"] == 50
    assert gear["maxCharges"] == 50

    use = client.patch(f"/api/characters/{character_id}/gear/{wand_id}/use")
    assert use.status_code == 200
    sheet = client.get(f"/api/characters/{character_id}").json()
    gear = next(g for g in sheet["gear"] if g["id"] == wand_id)
    assert gear["chargesRemaining"] == 49


def test_stored_spell_id_rejected_for_non_wand_item(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    dolch_id = _item_id(client, db_session, "Dolch")
    _, spells_by_name = _spells_by_class(client, db_session, "Magier")
    spell_id = next(iter(spells_by_name.values()))
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": dolch_id, "quantity": 1})

    response = client.patch(f"/api/characters/{character_id}/gear/{dolch_id}", json={"stored_spell_id": spell_id})
    assert response.status_code == 422


def test_use_gear_with_no_trackable_counter_is_rejected(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    dolch_id = _item_id(client, db_session, "Dolch")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": dolch_id, "quantity": 1})

    response = client.patch(f"/api/characters/{character_id}/gear/{dolch_id}/use")
    assert response.status_code == 422


def test_uses_per_day_counter_depletes_and_resets_on_rest(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    ring_id = _item_id(client, db_session, "Chamäleonring")
    # No seeded item has uses_per_day populated yet (deliberate import gap,
    # see build_wondrous_items_seed.py) - set it directly for this test.
    item = db_session.get(BaseItem, ring_id)
    item.activation = "activatable"
    item.uses_per_day = 2
    db_session.commit()

    client.post(f"/api/characters/{character_id}/gear", json={"item_id": ring_id, "quantity": 1})

    sheet = client.get(f"/api/characters/{character_id}").json()
    gear = next(g for g in sheet["gear"] if g["id"] == ring_id)
    assert gear["usesRemainingToday"] == 2

    client.patch(f"/api/characters/{character_id}/gear/{ring_id}/use")
    client.patch(f"/api/characters/{character_id}/gear/{ring_id}/use")
    depleted = client.patch(f"/api/characters/{character_id}/gear/{ring_id}/use")
    assert depleted.status_code == 422

    rest = client.post(f"/api/characters/{character_id}/rest")
    assert rest.status_code == 200
    sheet = client.get(f"/api/characters/{character_id}").json()
    gear = next(g for g in sheet["gear"] if g["id"] == ring_id)
    assert gear["usesRemainingToday"] == 2


def test_toggle_active_flips_state_for_activatable_item(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    ring_id = _item_id(client, db_session, "Energieschildring")
    item = db_session.get(BaseItem, ring_id)
    item.activation = "activatable"
    db_session.commit()

    client.post(f"/api/characters/{character_id}/gear", json={"item_id": ring_id, "quantity": 1})

    sheet = client.get(f"/api/characters/{character_id}").json()
    gear = next(g for g in sheet["gear"] if g["id"] == ring_id)
    assert gear["isActive"] is False

    toggle = client.patch(f"/api/characters/{character_id}/gear/{ring_id}/toggle")
    assert toggle.status_code == 200
    sheet = client.get(f"/api/characters/{character_id}").json()
    gear = next(g for g in sheet["gear"] if g["id"] == ring_id)
    assert gear["isActive"] is True


def test_toggle_rejected_for_non_activatable_item(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    dolch_id = _item_id(client, db_session, "Dolch")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": dolch_id, "quantity": 1})

    response = client.patch(f"/api/characters/{character_id}/gear/{dolch_id}/toggle")
    assert response.status_code == 422
