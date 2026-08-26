"""Kampfmagus's own "Arkaner Vorrat" (Arcane Reservoir) — pool size
(`rules/classes/kampfmagus.py`'s `_arkaner_vorrat_pool_points`) plus its
headline "verbessere eine Waffe" action (`_arkaner_vorrat_weapon_enhancement`).
Not yet covered: the Skirnir archetype's own variant, the other class
abilities that spend from the same pool (Zauberrückruf, Wissensvorrat,
Kensai's Perfekter Schlag, ...), and the pool's level-5 special-ability
unlock — see that module's own docstring."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from test_characters import _character_payload, _create_user, _elf_race_id, _item_id

ARKANER_VORRAT_ABILITY_ID = "571a2783-adb7-5222-8040-a1c4d40b4b0c"


def _create_kampfmagus(client: TestClient, db_session: Session, level: int = 1) -> str:
    """A real Kampfmagus/Elf (unlike `test_items.py`'s generic
    `_create_character`) — Arkaner Vorrat must actually be *granted*
    (`base_class_ability_grants.json`, level 1) to show up in
    `activatableClassAbilities`. Elf's ability mods (+2 GE/+2 IN/-2 KO on
    `DEFAULT_ABILITY_SCORES`) put IN at 12 (mod +1) — used throughout this
    file's expected pool sizes."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    payload = _character_payload(
        user_id, race_id, db_session, classes=[{"class_name": "Kampfmagus", "level": level}]
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def _arkaner_vorrat_entry(sheet: dict) -> dict:
    return next(a for a in sheet["activatableClassAbilities"] if a["key"] == ARKANER_VORRAT_ABILITY_ID)


def test_arkaner_vorrat_pool_size_scales_with_half_level_and_int_mod(
    client: TestClient, db_session: Session
) -> None:
    """"Eine Anzahl an Punkten in Höhe seiner halben Stufe als Kampfmagus
    (Minimum 1) + seines IN-Modifikators" — level 1: max(1, 1//2)=1, +1
    (Elf IN 12) = 2. Level 5: max(1, 5//2)=2, +1 = 3."""
    level1_id = _create_kampfmagus(client, db_session, level=1)
    sheet = client.get(f"/api/characters/{level1_id}").json()
    assert _arkaner_vorrat_entry(sheet)["description"] == "2 von 2 Punkten heute übrig"

    level5_id = _create_kampfmagus(client, db_session, level=5)
    sheet = client.get(f"/api/characters/{level5_id}").json()
    assert _arkaner_vorrat_entry(sheet)["description"] == "3 von 3 Punkten heute übrig"


def test_arkaner_vorrat_weapon_bonus_scales_with_level_and_costs_one_point(
    client: TestClient, db_session: Session
) -> None:
    """"+1 auf der 1. Stufe... für jeweils 4 weitere Stufen (ab der 5., 9.
    ...) ein weiterer +1" — a 5th-level Kampfmagus's activation grants +2,
    for a flat, always-1-point pool cost (not the bonus size itself, see
    `ARKANER_VORRAT_ABILITY_ID`'s own docstring on why those two are
    decoupled)."""
    character_id = _create_kampfmagus(client, db_session, level=5)
    langschwert_id = _item_id(client, db_session, "Langschwert")  # one-handed, 1W8 H, melee, martial
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": langschwert_id, "quantity": 1})
    client.put(f"/api/characters/{character_id}/slots/hauptwaffe", json={"item_id": langschwert_id})

    baseline = client.get(f"/api/characters/{character_id}").json()
    baseline_weapon = next(w for w in baseline["weaponAttacks"] if w["key"] == "hauptwaffe")
    assert baseline_weapon["attackBonus"] == "+3"  # bab 3 (int(5 * 0.75)), no other bonuses
    assert baseline_weapon["damage"] == "1W8 H"
    assert _arkaner_vorrat_entry(baseline)["description"] == "3 von 3 Punkten heute übrig"

    activation = client.post(
        f"/api/characters/{character_id}/effects",
        json={
            "source_type": "class_ability",
            "source_id": ARKANER_VORRAT_ABILITY_ID,
            "duration_remaining": 10,
            "target_item_id": langschwert_id,
        },
    )
    assert activation.status_code == 201

    sheet = client.get(f"/api/characters/{character_id}").json()
    weapon = next(w for w in sheet["weaponAttacks"] if w["key"] == "hauptwaffe")
    assert weapon["attackBonus"] == "+5"  # +3 baseline + Arkaner Vorrat's level-5 +2
    assert weapon["damage"] == "1W8+2 H"
    # Only 1 point spent, not 2 (the bonus size), and the round-tick below
    # must not drain it further.
    assert _arkaner_vorrat_entry(sheet)["description"] == "2 von 3 Punkten heute übrig"
    active = next(e for e in sheet["activeEffects"] if e["sourceId"] == ARKANER_VORRAT_ABILITY_ID)
    assert active["dailyLimitRemaining"] == 2
    assert active["dailyLimitTotal"] == 3
    assert active["durationRemaining"] == 10
    assert active["targetItemId"] == langschwert_id

    client.post(f"/api/characters/{character_id}/advance-time", json={"unit": "round"})
    sheet = client.get(f"/api/characters/{character_id}").json()
    # Pool untouched by the round tick (contrast Kampfrausch, whose
    # rounds/day pool *is* its own active duration) - only the effect's own
    # countdown moves.
    assert _arkaner_vorrat_entry(sheet)["description"] == "2 von 3 Punkten heute übrig"
    active = next(e for e in sheet["activeEffects"] if e["sourceId"] == ARKANER_VORRAT_ABILITY_ID)
    assert active["durationRemaining"] == 9
    weapon = next(w for w in sheet["weaponAttacks"] if w["key"] == "hauptwaffe")
    assert weapon["attackBonus"] == "+5"  # still active


def test_arkaner_vorrat_weapon_bonus_caps_combined_enhancement_at_5(
    client: TestClient, db_session: Session
) -> None:
    """"Diese Boni können auch zu Waffen hinzuaddiert werden, die bereits
    über einen Bonus verfügen, der Maximalbonus beträgt aber auch hier +5"
    — a +4 weapon plus a level-17 Kampfmagus's own +5 must cap at +5 total,
    not add to +9."""
    character_id = _create_kampfmagus(client, db_session, level=17)
    langschwert_id = _item_id(client, db_session, "Langschwert")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": langschwert_id, "quantity": 1})
    client.patch(f"/api/characters/{character_id}/gear/{langschwert_id}", json={"enhancement": 4})
    client.put(f"/api/characters/{character_id}/slots/hauptwaffe", json={"item_id": langschwert_id})

    baseline = client.get(f"/api/characters/{character_id}").json()
    baseline_weapon = next(w for w in baseline["weaponAttacks"] if w["key"] == "hauptwaffe")

    client.post(
        f"/api/characters/{character_id}/effects",
        json={
            "source_type": "class_ability",
            "source_id": ARKANER_VORRAT_ABILITY_ID,
            "duration_remaining": 10,
            "target_item_id": langschwert_id,
        },
    )

    sheet = client.get(f"/api/characters/{character_id}").json()
    weapon = next(w for w in sheet["weaponAttacks"] if w["key"] == "hauptwaffe")
    baseline_first_attack = int(baseline_weapon["attackBonus"].split("/")[0])
    activated_first_attack = int(weapon["attackBonus"].split("/")[0])
    # +4 permanent already applied at baseline; capped combined total is
    # +5, i.e. only +1 more than baseline, not Arkaner Vorrat's own nominal
    # +5 on top.
    assert activated_first_attack == baseline_first_attack + 1


def test_arkaner_vorrat_activation_rejects_unknown_target_item(
    client: TestClient, db_session: Session
) -> None:
    character_id = _create_kampfmagus(client, db_session, level=1)
    not_carried_item_id = _item_id(client, db_session, "Langschwert")

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={"source_type": "class_ability", "source_id": ARKANER_VORRAT_ABILITY_ID, "target_item_id": not_carried_item_id},
    )
    assert response.status_code == 422


def test_arkaner_vorrat_activation_rejected_once_pool_exhausted(
    client: TestClient, db_session: Session
) -> None:
    """Level 1: pool = 2 points, 1 per activation - a third activation the
    same day must be rejected; a full rest restores it."""
    character_id = _create_kampfmagus(client, db_session, level=1)
    langschwert_id = _item_id(client, db_session, "Langschwert")
    client.post(f"/api/characters/{character_id}/gear", json={"item_id": langschwert_id, "quantity": 1})

    for _ in range(2):
        response = client.post(
            f"/api/characters/{character_id}/effects",
            json={
                "source_type": "class_ability",
                "source_id": ARKANER_VORRAT_ABILITY_ID,
                "duration_remaining": 10,
                "target_item_id": langschwert_id,
            },
        )
        assert response.status_code == 201

    sheet = client.get(f"/api/characters/{character_id}").json()
    assert _arkaner_vorrat_entry(sheet)["description"] == "0 von 2 Punkten heute übrig"

    response = client.post(
        f"/api/characters/{character_id}/effects",
        json={
            "source_type": "class_ability",
            "source_id": ARKANER_VORRAT_ABILITY_ID,
            "duration_remaining": 10,
            "target_item_id": langschwert_id,
        },
    )
    assert response.status_code == 422

    client.post(f"/api/characters/{character_id}/rest")
    sheet = client.get(f"/api/characters/{character_id}").json()
    assert _arkaner_vorrat_entry(sheet)["description"] == "2 von 2 Punkten heute übrig"
