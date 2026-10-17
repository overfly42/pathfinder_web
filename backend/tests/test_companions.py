"""Animal companions as `Character` rows — roadmap slice 10, step 2b
(`app/companions.py`, `scripts/import_companion_species.py`)."""

from sqlalchemy import select
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CharacterClassOption

from test_characters import _character_payload, _create_user, _human_race_id, _race_id


def _master(client: TestClient, db_session: Session, classes: list[dict], race: str = "Mensch") -> dict:
    race_id = _human_race_id(client, db_session) if race == "Mensch" else _race_id(client, db_session, race)
    payload = _character_payload(_create_user(client), race_id, db_session, classes=classes)
    if race == "Mensch":
        payload["flex_ability"] = "CH"
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{response.json()['id']}").json()


def _druide(client: TestClient, db_session: Session, level: int) -> dict:
    return _master(client, db_session, [{"class_name": "Druide", "level": level, "options": {"bond": ["Tiergefährte"]}}])


def _slot(sheet: dict) -> dict:
    track = next(t for t in sheet["companionLevels"] if t["track"] == "animal_companion")
    return track["slots"][0]


def _species_id(slot: dict, name: str) -> str:
    return next(s["id"] for s in slot["species"] if s["name"].startswith(name))


def _add(client: TestClient, master: dict, species: str, hit_points: list[int] | None = None, **extra):
    slot = _slot(master)
    body = {
        "species_id": _species_id(slot, species),
        "name": species,
        "hit_points": hit_points if hit_points is not None else [5] * slot["hitDice"],
        **extra,
    }
    return client.post(f"/api/characters/{master['id']}/companions", json=body)


def _companion(client: TestClient, master: dict, species: str, **extra) -> dict:
    response = _add(client, master, species, **extra)
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{response.json()['id']}").json()


def _attack(sheet: dict, name: str) -> dict:
    return next(a for a in sheet["weaponAttacks"] if a["name"] == name)


def _value(entries: list[dict], key: str) -> str:
    return next(e for e in entries if e["key"] == key)["value"]


def test_species_and_pseudo_class_stay_out_of_player_choices(client: TestClient, db_session: Session) -> None:
    races = client.get("/api/races").json()
    assert "Wolf" not in {r["name"] for r in races}
    classes = client.get("/api/classes").json()
    assert "Tiergefährte" not in {c["name"] for c in classes}

    payload = _character_payload(
        _create_user(client), _human_race_id(client, db_session), db_session, classes=[{"class_name": "Tiergefährte", "level": 1}]
    )
    payload["flex_ability"] = "CH"
    assert client.post("/api/characters", json=payload).status_code == 422


def test_druide_has_one_companion_slot_with_all_17_species(client: TestClient, db_session: Session) -> None:
    slot = _slot(_druide(client, db_session, 1))

    assert slot["level"] == 1
    assert slot["hitDice"] == 2
    assert len(slot["species"]) == 17
    assert slot["companion"] is None


def test_level_1_wolf_companion_sheet(client: TestClient, db_session: Session) -> None:
    master = _druide(client, db_session, 1)
    wolf = _companion(client, master, "Wolf")

    assert wolf["kind"] == "companion"
    assert wolf["companion"]["master"] == {"id": master["id"], "name": master["name"]}
    assert wolf["companion"]["effectiveLevel"] == 1
    assert wolf["companion"]["hitDice"] == 2
    assert wolf["companion"]["expectedHitDice"] == 2
    assert wolf["companion"]["bonusTricks"] == 1
    assert wolf["companion"]["breakdown"][0]["detail"] == "Druide 1"
    assert {"Verbindung", "Zauber teilen"} <= {f["name"] for f in wolf["classFeatures"]}
    assert "Entrinnen" not in {f["name"] for f in wolf["classFeatures"]}
    assert "Geruchssinn" in {r["name"] for r in wolf["raceAbilities"]}
    assert wolf["speed"] == "15 m"
    assert wolf["hp"]["max"] == 5 + 5 + 2 * 2  # two HD, KO 15
    # ¾ BAB of 2 HD, good Fort/Ref, poor Will.
    assert _value(wolf["combat"], "bab") == "+1"
    assert _value(wolf["saves"], "fort") == "+5"
    assert _value(wolf["saves"], "ref") == "+5"
    assert _value(wolf["saves"], "will") == "+1"
    assert wolf["armorClass"] == 10 + 2 + 2
    bite = _attack(wolf, "Biss")
    # Sole natural attack: full BAB, 1½ × ST (+1 -> +1).
    assert bite["attackBonus"] == "+2"
    assert bite["damage"] == "1W6+1 H/S/W"
    assert bite["note"] == "Zu Fall bringen"
    assert _value(wolf["combat"], "size").startswith("Mittelgroß")

    master_again = client.get(f"/api/characters/{master['id']}").json()
    assert _slot(master_again)["companion"] == {"id": wolf["id"], "name": "Wolf"}


def test_wolf_advancement_at_7_or_dex_con_instead(client: TestClient, db_session: Session) -> None:
    advanced = _companion(client, _druide(client, db_session, 7), "Wolf")
    plain = _companion(client, _druide(client, db_session, 7), "Wolf", advancement_choice="dex_con")

    def score(sheet: dict, key: str) -> int:
        return next(a for a in sheet["abilities"] if a["key"] == key)["score"]

    assert advanced["companion"]["advanced"] is True
    assert _value(advanced["combat"], "size").startswith("Groß")
    assert score(advanced, "ST") == 13 + 8 + 2  # species advancement + table ST/GE
    assert _attack(advanced, "Biss")["damage"].startswith("1W8")
    natural = next(e for e in advanced["armorClassBreakdown"] if e["label"] == "Natürliche Rüstung")
    assert natural["value"] == 2 + 2 + 4

    assert plain["companion"]["advanced"] is False
    assert _value(plain["combat"], "size").startswith("Mittelgroß")
    assert score(plain, "GE") == 15 + 2 + 2
    assert score(plain, "KO") == 15 + 2
    assert _attack(plain, "Biss")["damage"].startswith("1W6")


def test_pony_hooves_are_primary_horse_hooves_secondary(client: TestClient, db_session: Session) -> None:
    pony = _companion(client, _druide(client, db_session, 1), "Pony")
    horse = _companion(client, _druide(client, db_session, 1), "Pferd")

    # Pony: one kind of attack -> primary despite hooves; BAB 1 + ST 13 (+1).
    assert _attack(pony, "Hufe")["attackBonus"] == "+2/+2"
    # Pferd (Groß, −1): bite primary, hooves secondary (−5, ½ ST); ST 16 (+3).
    assert _attack(horse, "Biss")["attackBonus"] == "+3"
    assert _attack(horse, "Hufe")["attackBonus"] == "-2/-2"
    assert _attack(horse, "Hufe")["damage"] == "1W6+1 W"
    assert _attack(horse, "Hufe")["hand"] == "Naturangriff (sekundär)"


def test_companion_creation_is_validated(client: TestClient, db_session: Session) -> None:
    master = _druide(client, db_session, 1)
    assert _add(client, master, "Wolf", hit_points=[5]).status_code == 422
    assert _add(client, master, "Wolf", hit_points=[9, 5]).status_code == 422
    assert _add(client, master, "Wolf").status_code == 201
    # The slot is taken now.
    assert _add(client, master, "Hund").status_code == 422

    fighter = _master(client, db_session, [{"class_name": "Kämpfer", "level": 1}])
    response = client.post(
        f"/api/characters/{fighter['id']}/companions",
        json={"species_id": _species_id(_slot(master), "Hund"), "name": "Rex", "hit_points": [5, 5]},
    )
    assert response.status_code == 422


def test_small_paladin_gets_a_pony_not_a_horse(client: TestClient, db_session: Session) -> None:
    paladin = _master(
        client, db_session, [{"class_name": "Paladin", "level": 5, "options": {"divine_bond": ["Reittier"]}}], race="Halbling"
    )
    names = {s["name"] for s in _slot(paladin)["species"]}

    assert {"Pony", "Wildschwein", "Hund", "Kamel"} <= names
    assert "Pferd" not in names
    assert _slot(paladin)["level"] == 5


def test_companion_is_listed_with_its_master_and_deleted_with_it(client: TestClient, db_session: Session) -> None:
    master = _druide(client, db_session, 1)
    wolf = _companion(client, master, "Wolf")

    characters = client.get(f"/api/users/{_owner(client, master['id'])}/characters").json()
    by_id = {c["id"]: c for c in characters}
    assert by_id[wolf["id"]]["master_character_id"] == master["id"]
    assert by_id[master["id"]]["master_character_id"] is None

    assert client.delete(f"/api/characters/{master['id']}").status_code == 204
    assert client.get(f"/api/characters/{wolf['id']}").status_code == 404


def _owner(client: TestClient, character_id: str) -> str:
    """The user id of a character (the sheet payload doesn't carry it)."""
    for user in client.get("/api/users").json():
        if any(c["id"] == character_id for c in client.get(f"/api/users/{user['id']}/characters").json()):
            return user["id"]
    raise AssertionError("owner not found")


def test_companion_without_entitlement_is_kept_and_flagged(client: TestClient, db_session: Session) -> None:
    master = _druide(client, db_session, 3)
    wolf = _companion(client, master, "Wolf")

    for option in db_session.scalars(select(CharacterClassOption).where(CharacterClassOption.group_key == "bond")):
        db_session.delete(option)
    db_session.flush()

    sheet = client.get(f"/api/characters/{wolf['id']}").json()
    assert sheet["companion"]["orphaned"] is True
    assert sheet["companion"]["effectiveLevel"] is None
    # Stats from the highest table row its 3 HD still match (level 3).
    assert "Entrinnen" in {f["name"] for f in sheet["classFeatures"]}
