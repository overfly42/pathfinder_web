from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from test_characters import _character_payload, _create_user, _elf_race_id, _feat_id, _feat_selection, _human_race_id, _item_id
from test_items import _create_character, _weapon_ability_id

KAMPFMAGUS = {"class_name": "Kampfmagus", "level": 1}
KENSAI = {"class_name": "Kampfmagus", "level": 1, "archetypes": ["Kensai"]}


def _equip(client: TestClient, character_id: str, slot_key: str, item_id: str | None) -> dict:
    response = client.put(f"/api/characters/{character_id}/slots/{slot_key}", json={"item_id": item_id})
    assert response.status_code == 200, response.text
    return response.json()


def _weapon_attack(sheet: dict, slot_key: str) -> dict:
    return next(w for w in sheet["weaponAttacks"] if w["key"] == slot_key)


def test_equip_weapon_computes_attack_bonus_and_damage(client: TestClient, db_session: Session) -> None:
    # Default character: level-1 Waldläufer (full BAB -> bab 1), Elf ability
    # scores (ST 10 -> mod 0, GE 12+2 -> mod +2, per race_ability_score_mods).
    character_id = _create_character(client, db_session)
    langschwert_id = _item_id(client, db_session, "Langschwert")  # one-handed, 1W8 H, melee
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": langschwert_id, "quantity": 1})

    _equip(client, character_id, "hauptwaffe", langschwert_id)

    sheet = client.get(f"/api/characters/{character_id}").json()
    weapon = _weapon_attack(sheet, "hauptwaffe")
    assert weapon == {
        "key": "hauptwaffe",
        "hand": "Hauptwaffe",
        "name": "Langschwert",
        "attackBonus": "+1",
        "damage": "1W8 H",
    }

    hauptwaffe_slot = next(s for s in sheet["equipmentSlots"] if s["key"] == "hauptwaffe")
    assert hauptwaffe_slot["selected"] == langschwert_id


def test_equip_ranged_weapon_uses_dex_not_str_for_attack(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    langbogen_id = _item_id(client, db_session, "Langbogen")  # two-handed, 1W8 S, ranged
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": langbogen_id, "quantity": 1})

    _equip(client, character_id, "hauptwaffe", langbogen_id)

    sheet = client.get(f"/api/characters/{character_id}").json()
    weapon = _weapon_attack(sheet, "hauptwaffe")
    # bab 1 + dex mod +2 = +3; ranged damage doesn't add a Str modifier (simplification, see
    # sheet.py's _build_weapon_attacks docstring), so just the base die + damage type.
    assert weapon["attackBonus"] == "+3"
    assert weapon["damage"] == "1W8 S"


def test_waffenfinesse_uses_dex_for_light_weapon_but_not_for_non_light(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    dolch_id = _item_id(client, db_session, "Dolch")  # one-handed, light
    langschwert_id = _item_id(client, db_session, "Langschwert")  # one-handed, not light
    waffenfinesse_id = _feat_id(client, db_session, "Waffenfinesse")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="CH",  # leaves ST 10 (mod +0) and GE 12 (mod +1) apart
            feats=[_feat_selection(waffenfinesse_id)],
        ),
    )
    assert response.status_code == 201
    character_id = response.json()["id"]
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": dolch_id, "quantity": 1})
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": langschwert_id, "quantity": 1})

    _equip(client, character_id, "hauptwaffe", dolch_id)
    sheet = client.get(f"/api/characters/{character_id}").json()
    # bab 1 + dex mod +1 (Waffenfinesse applies: Dolch is light) = +2.
    assert _weapon_attack(sheet, "hauptwaffe")["attackBonus"] == "+2"

    _equip(client, character_id, "hauptwaffe", langschwert_id)
    sheet = client.get(f"/api/characters/{character_id}").json()
    # bab 1 + str mod +0 (Langschwert isn't light, feat doesn't apply) = +1.
    assert _weapon_attack(sheet, "hauptwaffe")["attackBonus"] == "+1"


def test_waffenfinesse_uses_dex_for_named_non_light_exception(client: TestClient, db_session: Session) -> None:
    """Rapier isn't a light weapon by weight class (`hands` "one", not the
    "Leichte Waffen" PRD subgroup) but is one of PF1e's named Waffenfinesse
    exceptions, `BaseItem.is_light` True regardless (see that field's
    docstring) — a separate case from the plain-light-weapon one above."""
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    rapier_id = _item_id(client, db_session, "Rapier")
    waffenfinesse_id = _feat_id(client, db_session, "Waffenfinesse")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="CH",  # leaves ST 10 (mod +0) and GE 12 (mod +1) apart
            feats=[_feat_selection(waffenfinesse_id)],
        ),
    )
    assert response.status_code == 201
    character_id = response.json()["id"]
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": rapier_id, "quantity": 1})

    _equip(client, character_id, "hauptwaffe", rapier_id)
    sheet = client.get(f"/api/characters/{character_id}").json()
    # bab 1 + dex mod +1 (Waffenfinesse's named exception applies to Rapier) = +2.
    assert _weapon_attack(sheet, "hauptwaffe")["attackBonus"] == "+2"


def test_equip_two_handed_weapon_clears_nebenwaffe(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    kurzschwert_id = _item_id(client, db_session, "Kurzschwert")  # one-handed, melee
    zweihaender_id = _item_id(client, db_session, "Zweihänder")  # two-handed, melee
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": kurzschwert_id, "quantity": 1})
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": zweihaender_id, "quantity": 1})

    _equip(client, character_id, "nebenwaffe", kurzschwert_id)
    body = _equip(client, character_id, "hauptwaffe", zweihaender_id)
    assert body is not None

    sheet = client.get(f"/api/characters/{character_id}").json()
    nebenwaffe_slot = next(s for s in sheet["equipmentSlots"] if s["key"] == "nebenwaffe")
    assert nebenwaffe_slot["selected"] == ""
    assert not any(w["key"] == "nebenwaffe" for w in sheet["weaponAttacks"])
    assert _weapon_attack(sheet, "hauptwaffe")["name"] == "Zweihänder"


def test_equip_nebenwaffe_while_hauptwaffe_is_two_handed_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    character_id = _create_character(client, db_session)
    zweihaender_id = _item_id(client, db_session, "Zweihänder")
    kurzschwert_id = _item_id(client, db_session, "Kurzschwert")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": zweihaender_id, "quantity": 1})
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": kurzschwert_id, "quantity": 1})
    _equip(client, character_id, "hauptwaffe", zweihaender_id)

    response = client.put(
        f"/api/characters/{character_id}/slots/nebenwaffe", json={"item_id": kurzschwert_id}
    )
    assert response.status_code == 422


def test_equip_nebenwaffe_and_schild_clear_each_other(client: TestClient, db_session: Session) -> None:
    character_id = _create_character(client, db_session)
    kurzschwert_id = _item_id(client, db_session, "Kurzschwert")
    turmschild_id = _item_id(client, db_session, "Turmschild")  # real shield category
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": kurzschwert_id, "quantity": 1})
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": turmschild_id, "quantity": 1})

    _equip(client, character_id, "nebenwaffe", kurzschwert_id)
    _equip(client, character_id, "schild", turmschild_id)

    sheet = client.get(f"/api/characters/{character_id}").json()
    nebenwaffe_slot = next(s for s in sheet["equipmentSlots"] if s["key"] == "nebenwaffe")
    schild_slot = next(s for s in sheet["equipmentSlots"] if s["key"] == "schild")
    assert nebenwaffe_slot["selected"] == ""
    assert schild_slot["selected"] == turmschild_id

    _equip(client, character_id, "nebenwaffe", kurzschwert_id)
    sheet = client.get(f"/api/characters/{character_id}").json()
    schild_slot = next(s for s in sheet["equipmentSlots"] if s["key"] == "schild")
    nebenwaffe_slot = next(s for s in sheet["equipmentSlots"] if s["key"] == "nebenwaffe")
    assert schild_slot["selected"] == ""
    assert nebenwaffe_slot["selected"] == kurzschwert_id


def test_weapon_energy_special_ability_bonus_damage_only_while_active(
    client: TestClient, db_session: Session
) -> None:
    character_id = _create_character(client, db_session)
    langschwert_id = _item_id(client, db_session, "Langschwert")
    aufflammen_id = _weapon_ability_id(client, db_session, "Aufflammen")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": langschwert_id, "quantity": 1})
    response = client.patch(
        f"/api/characters/{character_id}/gear/{langschwert_id}",
        json={"special_ability_ids": [aufflammen_id]},
    )
    assert response.status_code == 200
    _equip(client, character_id, "hauptwaffe", langschwert_id)

    sheet = client.get(f"/api/characters/{character_id}").json()
    assert _weapon_attack(sheet, "hauptwaffe")["damage"] == "1W8 H"

    response = client.patch(f"/api/characters/{character_id}/gear/{langschwert_id}/toggle")
    assert response.status_code == 200

    sheet = client.get(f"/api/characters/{character_id}").json()
    assert _weapon_attack(sheet, "hauptwaffe")["damage"] == "1W8 H + 1W6 Feuer"

    response = client.patch(f"/api/characters/{character_id}/gear/{langschwert_id}/toggle")
    assert response.status_code == 200
    sheet = client.get(f"/api/characters/{character_id}").json()
    assert _weapon_attack(sheet, "hauptwaffe")["damage"] == "1W8 H"


def test_attack_bonus_shows_iterative_attacks_at_high_bab(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    # Kämpfer (full BAB): level 6 -> bab 6, so a 2nd iterative attack (-5) kicks in.
    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Kämpfer", "level": 6}],
        hit_points={str(level): 6 for level in range(2, 7)},
    )
    character_id = client.post("/api/characters", json=payload).json()["id"]
    langschwert_id = _item_id(client, db_session, "Langschwert")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": langschwert_id, "quantity": 1})
    _equip(client, character_id, "hauptwaffe", langschwert_id)

    sheet = client.get(f"/api/characters/{character_id}").json()
    # bab 6 + str mod 0 (Elf ST 10) = +6, second attack at +1.
    assert _weapon_attack(sheet, "hauptwaffe")["attackBonus"] == "+6/+1"


def _create_character_with_class(client: TestClient, db_session: Session, class_entry: dict) -> str:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    payload = _character_payload(
        user_id, race_id, db_session, classes=[class_entry], flex_ability="CH"  # leaves ST 10 (mod +0) apart
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_kampfmagus_proficient_with_martial_weapon_has_no_penalty(client: TestClient, db_session: Session) -> None:
    character_id = _create_character_with_class(client, db_session, KAMPFMAGUS)
    langschwert_id = _item_id(client, db_session, "Langschwert")  # martial
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": langschwert_id, "quantity": 1})
    _equip(client, character_id, "hauptwaffe", langschwert_id)

    sheet = client.get(f"/api/characters/{character_id}").json()
    weapon = _weapon_attack(sheet, "hauptwaffe")
    # Kampfmagus is proficient with simple + martial weapons -> no malus.
    # bab 0 (3/4 BAB progression at level 1) + str mod 0 (human ST 10) = +0.
    assert weapon["attackBonus"] == "+0"
    assert "note" not in weapon


def test_kampfmagus_not_proficient_with_exotic_weapon_gets_attack_penalty(
    client: TestClient, db_session: Session
) -> None:
    character_id = _create_character_with_class(client, db_session, KAMPFMAGUS)
    bastardschwert_id = _item_id(client, db_session, "Bastardschwert")  # exotic
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": bastardschwert_id, "quantity": 1})
    _equip(client, character_id, "hauptwaffe", bastardschwert_id)

    sheet = client.get(f"/api/characters/{character_id}").json()
    weapon = _weapon_attack(sheet, "hauptwaffe")
    # bab 0 + str mod 0 - 4 (nicht geübt, Kampfmagus hat keine Kompetenz mit
    # exotischen Waffen) = -4.
    assert weapon["attackBonus"] == "-4"
    assert weapon["note"] == "Nicht geübt (-4)"


def test_kensai_proficient_with_simple_weapon_has_no_penalty(client: TestClient, db_session: Session) -> None:
    character_id = _create_character_with_class(client, db_session, KENSAI)
    kampfstab_id = _item_id(client, db_session, "Kampfstab")  # simple
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": kampfstab_id, "quantity": 1})
    _equip(client, character_id, "hauptwaffe", kampfstab_id)

    sheet = client.get(f"/api/characters/{character_id}").json()
    weapon = _weapon_attack(sheet, "hauptwaffe")
    assert weapon["attackBonus"] == "+0"  # bab 0 + str mod 0
    assert "note" not in weapon


def test_kensai_not_proficient_with_martial_weapon_gets_attack_penalty(
    client: TestClient, db_session: Session
) -> None:
    """Kensai's own "Umgang mit Waffen und Rüstungen (Kensai)" replaces the
    Kampfmagus base ability with just simple weapons plus a free choice of
    one martial/exotic weapon (PRD text) — the free single-weapon choice
    isn't modeled (no sub-choice mechanism for class abilities, see
    `class_ability_granted_feat_seed.py`'s docstring), so a Kensai currently
    reads as non-proficient with any martial weapon, a documented gap."""
    character_id = _create_character_with_class(client, db_session, KENSAI)
    langschwert_id = _item_id(client, db_session, "Langschwert")  # martial
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": langschwert_id, "quantity": 1})
    _equip(client, character_id, "hauptwaffe", langschwert_id)

    sheet = client.get(f"/api/characters/{character_id}").json()
    weapon = _weapon_attack(sheet, "hauptwaffe")
    assert weapon["attackBonus"] == "-4"  # bab 0 + str mod 0 - 4 (nicht geübt)
    assert weapon["note"] == "Nicht geübt (-4)"
