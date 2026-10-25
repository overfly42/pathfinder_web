"""Companion tricks as data — roadmap slice 10, step 5
(`scripts/import_companion_tricks.py`, `rules/companions.py`'s trick rules,
`app/companions.py`'s `set_companion_tricks`/`tricks_payload`)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CharacterCompanionTrick

from test_companions import _companion, _druide, _master
from test_familiars import _familiar, _magier


def _catalog(client: TestClient, character_id: str | None = None) -> dict:
    params = {"character_id": character_id} if character_id else {}
    response = client.get("/api/companion-tricks", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _ids(client: TestClient) -> dict[str, str]:
    catalog = _catalog(client)
    return {entry["name"]: entry["id"] for entry in catalog["tricks"] + catalog["purposes"]}


def _put(client: TestClient, companion_id: str, tricks: dict[str, str], purpose: str | None = None):
    ids = _ids(client)
    body = {
        "purpose_id": ids[purpose] if purpose else None,
        "tricks": [{"trick_id": ids[name], "source": source} for name, source in tricks.items()],
    }
    return client.put(f"/api/characters/{companion_id}/tricks", json=body)


def _sheet(client: TestClient, character_id: str) -> dict:
    return client.get(f"/api/characters/{character_id}").json()


def test_catalog_matches_the_prd(client: TestClient) -> None:
    catalog = _catalog(client)
    tricks = {t["name"]: t for t in catalog["tricks"]}
    assert len(tricks) == 13
    assert tricks["Spuren suchen"]["requiredAbility"] == "Geruchssinn"
    assert tricks["Angreifen (alle Wesen)"]["cost"] == 2
    assert tricks["Angreifen (alle Wesen)"]["variantOfId"] == tricks["Angreifen"]["id"]
    purposes = {p["name"]: p for p in catalog["purposes"]}
    assert len(purposes) == 7
    names_by_id = {t["id"]: name for name, t in tricks.items()}
    assert {names_by_id[i] for i in purposes["Jagen"]["trickIds"]} == {
        "Angreifen", "Bei Fuß gehen", "Bringen", "Spuren suchen", "Suchen", "Zurückziehen",
    }
    assert purposes["Kampfausbildung"]["weeks"] == 6


def test_new_companion_has_no_tricks_and_open_bonus_tricks(client: TestClient, db_session: Session) -> None:
    wolf = _companion(client, _druide(client, db_session, 1), "Wolf")

    assert wolf["companion"]["tricks"] == []
    assert wolf["companion"]["trickLimits"] == {
        "bonus": {"used": 0, "max": 1},
        "trained": {"used": 0, "max": 6},
        "intelligence": 2,
        "overLimit": False,
    }


def test_limits_for_in_2(client: TestClient, db_session: Session) -> None:
    wolf = _companion(client, _druide(client, db_session, 1), "Wolf")
    six = {name: "trained" for name in ("Bleiben", "Bringen", "Kommen", "Kunststück", "Suchen", "Wachen")}

    response = _put(client, wolf["id"], {"Angreifen": "bonus", **six})
    assert response.status_code == 200, response.text
    sheet = _sheet(client, wolf["id"])
    assert sheet["companion"]["trickLimits"]["bonus"] == {"used": 1, "max": 1}
    assert sheet["companion"]["trickLimits"]["trained"] == {"used": 6, "max": 6}
    assert {t["name"]: t["source"] for t in sheet["companion"]["tricks"]}["Angreifen"] == "bonus"

    assert _put(client, wolf["id"], {**six, "Verteidigen": "trained"}).status_code == 422
    assert _put(client, wolf["id"], {"Angreifen": "bonus", "Verteidigen": "bonus"}).status_code == 422


def test_in_1_limit_scent_gate_and_large_trainings(client: TestClient, db_session: Session) -> None:
    crocodile = _companion(client, _druide(client, db_session, 1), "Krokodil")

    assert _put(client, crocodile["id"], {n: "trained" for n in ("Bleiben", "Kommen", "Wachen")}).status_code == 200
    assert _put(client, crocodile["id"], {n: "trained" for n in ("Bleiben", "Kommen", "Wachen", "Bringen")}).status_code == 422
    # No Geruchssinn.
    assert _put(client, crocodile["id"], {"Spuren suchen": "trained"}).status_code == 422

    options = _catalog(client, crocodile["id"])
    reasons = {entry["name"]: entry["unavailableReason"] for entry in options["tricks"] + options["purposes"]}
    assert reasons["Spuren suchen"] == "braucht Geruchssinn"
    assert reasons["Jagen"] == "Spuren suchen braucht Geruchssinn"
    assert reasons["Wache halten"] == "mehr als 3 Tricks, braucht IN 2"
    assert reasons["Kämpfen"] is None

    response = _put(client, crocodile["id"], {n: "trained" for n in ("Angreifen", "Bleiben", "Zurückziehen")}, "Kämpfen")
    assert response.status_code == 200, response.text


def test_training_expands_into_its_tricks_without_double_counting(client: TestClient, db_session: Session) -> None:
    wolf = _companion(client, _druide(client, db_session, 1), "Wolf")
    training = {"Angreifen": "bonus", **{n: "trained" for n in ("Bei Fuß gehen", "Kommen", "Verteidigen", "Wachen", "Zurückziehen")}}

    response = _put(client, wolf["id"], {**training, "Bleiben": "trained"}, "Kampfausbildung")
    assert response.status_code == 200, response.text
    companion = _sheet(client, wolf["id"])["companion"]
    assert companion["trickPurpose"]["name"] == "Kampfausbildung"
    purpose_names = {t["name"]: t["purposeName"] for t in companion["tricks"]}
    assert purpose_names["Angreifen"] == "Kampfausbildung"
    assert purpose_names["Bleiben"] is None
    # Angreifen is paid from the bonus pool, not twice.
    assert companion["trickLimits"]["trained"]["used"] == 6
    assert companion["trickLimits"]["bonus"]["used"] == 1

    # A training must bring all of its tricks.
    missing = {k: v for k, v in training.items() if k != "Wachen"}
    assert _put(client, wolf["id"], missing, "Kampfausbildung").status_code == 422


def test_attack_all_creatures_costs_two_and_covers_angreifen(client: TestClient, db_session: Session) -> None:
    wolf = _companion(client, _druide(client, db_session, 1), "Wolf")

    assert _put(client, wolf["id"], {"Angreifen": "trained", "Angreifen (alle Wesen)": "trained"}).status_code == 422
    response = _put(client, wolf["id"], {n: "trained" for n in ("Angreifen (alle Wesen)", "Bleiben", "Zurückziehen")}, "Kämpfen")
    assert response.status_code == 200, response.text
    companion = _sheet(client, wolf["id"])["companion"]
    assert companion["trickLimits"]["trained"]["used"] == 4
    assert {t["name"]: t["purposeName"] for t in companion["tricks"]}["Angreifen (alle Wesen)"] == "Kämpfen"


def test_bonus_tricks_grow_with_the_masters_level(client: TestClient, db_session: Session) -> None:
    wolf = _companion(client, _druide(client, db_session, 3), "Wolf")

    assert wolf["companion"]["trickLimits"]["bonus"]["max"] == 2
    assert _put(client, wolf["id"], {"Angreifen": "bonus", "Bleiben": "bonus"}).status_code == 200


def test_in_3_or_more_has_no_trained_limit(client: TestClient, db_session: Session) -> None:
    paladin = _master(client, db_session, [{"class_name": "Paladin", "level": 5, "options": {"divine_bond": ["Reittier"]}}])
    horse = _companion(client, paladin, "Pferd")

    names = ("Angreifen", "Arbeiten", "Bei Fuß gehen", "Bleiben", "Bringen", "Kommen", "Kunststück", "Suchen")
    response = _put(client, horse["id"], {n: "trained" for n in names})
    assert response.status_code == 200, response.text
    limits = _sheet(client, horse["id"])["companion"]["trickLimits"]
    assert limits["trained"] == {"used": 8, "max": None}
    assert limits["overLimit"] is False


def test_over_limit_is_flagged_not_deleted(client: TestClient, db_session: Session) -> None:
    wolf = _companion(client, _druide(client, db_session, 1), "Wolf")
    # As if the limit had dropped after the picks were made.
    for name in ("Angreifen", "Bleiben"):
        db_session.add(CharacterCompanionTrick(character_id=wolf["id"], trick_id=_ids(client)[name], source="bonus"))
    db_session.flush()

    companion = _sheet(client, wolf["id"])["companion"]
    assert len(companion["tricks"]) == 2
    assert companion["trickLimits"]["bonus"] == {"used": 2, "max": 1}
    assert companion["trickLimits"]["overLimit"] is True


def test_familiars_and_player_characters_have_no_tricks(client: TestClient, db_session: Session) -> None:
    magier = _magier(client, db_session, 1)
    cat = _familiar(client, magier, "Katze")

    assert cat["companion"]["tricks"] == []
    assert cat["companion"]["trickLimits"] is None
    assert _put(client, cat["id"], {"Kommen": "trained"}).status_code == 422
    assert _put(client, magier["id"], {"Kommen": "trained"}).status_code == 422
