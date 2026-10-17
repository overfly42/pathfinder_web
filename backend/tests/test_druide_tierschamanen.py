"""Druide archetypes Bärenschamane and Löwenschamane
(`scripts/import_druide_tierschamanen.py`, `rules/classes/druide.py`)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from test_characters import _character_payload, _create_user, _human_race_id

BAER_BEWEGUNG = "0babf5d4-5772-5239-a43b-f34e3164231f"
BAER_WAFFEN = "cd1e83b9-53a5-5f05-94a4-17fbcc1d0f8c"
LOEWE_WAFFEN = "9af8cdd2-cef3-5e56-b1db-762a50588b91"


def _create(client: TestClient, db_session: Session, archetype: str | None, level: int, options: dict):
    selection = {"class_name": "Druide", "level": level, "options": options}
    if archetype:
        selection["archetypes"] = [archetype]
    payload = _character_payload(_create_user(client), _human_race_id(client, db_session), db_session, classes=[selection])
    payload["flex_ability"] = "WE"
    return client.post("/api/characters", json=payload)


def _shaman(client: TestClient, db_session: Session, archetype: str, level: int, **options) -> dict:
    response = _create(client, db_session, archetype, level, options or {"bond": ["Tiergefährte"]})
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{response.json()['id']}").json()


def _features(sheet: dict) -> dict[str, dict]:
    return {f["name"]: f for f in sheet["classFeatures"]}


def test_baerenschamane_features_replace_the_druides(client: TestClient, db_session: Session) -> None:
    features = _features(_shaman(client, db_session, "Bärenschamane", 9))

    assert {
        "Tiergefährte (Bärenschamane)",
        "Tierempathie (Bärenschamane)",
        "Totemverwandlung (Bärenschamane)",
        "Totemverwandlung: Natürliche Waffen (Bärenschamane)",
        "Totemtier herbeizaubern (Bärenschamane)",
        "Tiergestalt (Bärenschamane)",
        "Bonustalent (Bärenschamane)",
    } <= set(features)
    assert "Tiergefährte (Druide)" not in features
    assert "Tiergestalt" not in features
    assert "Immunität gegen Gifte" not in features
    # Druide 9 − 2 = 7: 2/Tag; Bärengestalt counts Druide 11.
    assert features["Tiergestalt (Bärenschamane)"]["summary"].startswith("2/Tag")
    assert "in Bären Gestalt 11" in features["Tiergestalt (Bärenschamane)"]["summary"]


def test_tiergestalt_only_from_6th_level(client: TestClient, db_session: Session) -> None:
    assert "Tiergestalt (Bärenschamane)" not in _features(_shaman(client, db_session, "Bärenschamane", 5))
    assert "Tiergestalt" not in _features(_shaman(client, db_session, "Bärenschamane", 5))


def test_totem_companion_species_only(client: TestClient, db_session: Session) -> None:
    bear = _shaman(client, db_session, "Bärenschamane", 3)
    lion = _shaman(client, db_session, "Löwenschamane", 3)

    bear_track = next(t for t in bear["companionLevels"] if t["track"] == "animal_companion")
    lion_track = next(t for t in lion["companionLevels"] if t["track"] == "animal_companion")
    assert bear_track["level"] == 3
    assert [s["name"] for s in bear_track["slots"][0]["species"]] == ["Bär"]
    # The lion, plus the house-rule Säbelzahnkatze.
    assert [s["name"] for s in lion_track["slots"][0]["species"]] == [
        "Raubkatze, Groß (Löwe, Tiger)",
        "Säbelzahnkatze (Hausregel)",
    ]


def test_domain_choices_are_scoped_to_the_archetype(client: TestClient, db_session: Session) -> None:
    def domain(archetype: str | None, name: str) -> int:
        return _create(
            client, db_session, archetype, 1, {"bond": ["Domäne (Natur)"], "nature_domain": [name]}
        ).status_code

    assert domain("Bärenschamane", "Domäne des Schutzes") == 201
    assert domain("Bärenschamane", "Domäne der Tiere") == 201
    assert domain("Bärenschamane", "Domäne des Feuers") == 422
    assert domain("Löwenschamane", "Domäne der Sonne") == 201
    assert domain("Löwenschamane", "Domäne der Erde") == 422
    assert domain(None, "Domäne des Schutzes") == 422
    assert domain(None, "Domäne des Feuers") == 201

    druide = next(c for c in client.get("/api/classes").json() if c["name"] == "Druide")
    nature = next(g for g in druide["optionGroups"] if g["key"] == "nature_domain")
    schutz = next(c for c in nature["choices"] if c["name"] == "Domäne des Schutzes")
    assert schutz["onlyForArchetypes"] == ["Bärenschamane"]
    feuer = next(c for c in nature["choices"] if c["name"] == "Domäne des Feuers")
    assert feuer["excludedForArchetypes"] == ["Bärenschamane", "Löwenschamane"]


def test_totemverwandlung_aspects_spend_minutes(client: TestClient, db_session: Session) -> None:
    sheet = _shaman(client, db_session, "Bärenschamane", 4)
    character_id = sheet["id"]

    response = client.post(
        f"/api/characters/{character_id}/effects", json={"source_type": "class_ability", "source_id": BAER_BEWEGUNG}
    )
    assert response.status_code == 201, response.text
    moving = client.get(f"/api/characters/{character_id}").json()
    assert moving["speed"] == "12 m"

    client.post(f"/api/characters/{character_id}/effects", json={"source_type": "class_ability", "source_id": BAER_WAFFEN})
    armed = client.get(f"/api/characters/{character_id}").json()
    names = {a["name"]: a for a in armed["weaponAttacks"]}
    assert names["Biss"]["damage"].startswith("1W6")
    assert names["Klauen"]["damage"].startswith("1W4")
    # Druide 4: 4 minutes a day, two aspects took one each.
    pool = next(a for a in armed["actions"] if a.get("name") == "Totemverwandlung (Bärenschamane)")
    assert (pool["usesRemainingToday"], pool["usesPerDay"]) == (2, 4)


def test_bonus_feat_closed_lists(client: TestClient, db_session: Session) -> None:
    druide = next(c for c in client.get("/api/classes").json() if c["name"] == "Druide")
    bear = druide["archetypeBonusFeatOptionsByLevel"]["Bärenschamane"]
    assert {f["name"] for f in bear["9"]["feats"]} == {
        "Abhärtung", "Ausdauer", "Große Zähigkeit", "Unverwüstlich", "Verbesserte Große Zähigkeit"
    }
    lion = druide["archetypeBonusFeatOptionsByLevel"]["Löwenschamane"]
    assert "Ausfallschritt" in {f["name"] for f in lion["13"]["feats"]}


def test_aspects_do_nothing_until_activated(client: TestClient, db_session: Session) -> None:
    sheet = _shaman(client, db_session, "Bärenschamane", 4)
    assert sheet["speed"] == "9 m"
    assert not any(e["label"].startswith("Totemverwandlung") for e in sheet["armorClassBreakdown"])
    assert "Biss" not in {a["name"] for a in sheet["weaponAttacks"]}
