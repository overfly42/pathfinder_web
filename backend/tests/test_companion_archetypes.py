"""Companion archetypes — the house-rule Elementargefährte
(`scripts/import_hausregel_elementargefaehrte.py`, `app/companions.py`,
`app/rules/classes/tiergefaehrte.py`)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from test_companions import _companion, _druide, _slot


def _archetype_id(slot_or_sheet: list[dict], element: str) -> str:
    return next(a["id"] for a in slot_or_sheet if a["name"] == f"Elementargefährte: {element} (Hausregel)")


def _elemental(client: TestClient, db_session: Session, level: int, species: str, element: str) -> dict:
    master = _druide(client, db_session, level)
    return _companion(client, master, species, archetype_id=_archetype_id(_slot(master)["archetypes"], element))


def _features(sheet: dict) -> dict[str, dict]:
    return {f["name"]: f for f in sheet["classFeatures"]}


def test_archetype_replaces_evasion_and_multiattack(client: TestClient, db_session: Session) -> None:
    wolf = _elemental(client, db_session, 9, "Wolf", "Erde")
    features = _features(wolf)

    assert wolf["companion"]["archetype"]["name"] == "Elementargefährte: Erde (Hausregel)"
    assert {"Entrinnen", "Mehrfachangriff", "Verbessertes Entrinnen"}.isdisjoint(features)
    assert {"Elementare Unterart (Erde)", "Geringere elementare Manifestation (Erde)",
            "Größere elementare Manifestation (Erde)"} <= set(features)
    # 1 + 9 // 4 at effective level 9.
    assert features["Geringere elementare Manifestation (Erde)"]["summary"] == "SR 3/Adamant"


def test_manifestations_by_level(client: TestClient, db_session: Session) -> None:
    features = _features(_elemental(client, db_session, 1, "Wolf", "Luft"))
    assert "Elementare Unterart (Luft)" in features
    assert "Geringere elementare Manifestation (Luft)" not in features

    features = _features(_elemental(client, db_session, 2, "Wolf", "Luft"))
    assert features["Geringere elementare Manifestation (Luft)"]["summary"].startswith("20 %")
    assert "Größere elementare Manifestation (Luft)" not in features


def test_air_companion_flies_or_flies_better(client: TestClient, db_session: Session) -> None:
    wolf = _elemental(client, db_session, 9, "Wolf", "Luft")
    assert (wolf["flySpeed"], wolf["flyManeuverability"]) == ("6 m", "gut")

    bird = _elemental(client, db_session, 9, "Vogel", "Luft")
    assert (bird["flySpeed"], bird["flyManeuverability"]) == ("24 m", "gut")  # durchschnittlich -> gut


def test_water_companion_swims(client: TestClient, db_session: Session) -> None:
    wolf = _elemental(client, db_session, 2, "Wolf", "Wasser")
    assert wolf["swimSpeed"] == "6 m"
    assert _features(wolf)["Geringere elementare Manifestation (Wasser)"]["partialNote"]

    crocodile = _elemental(client, db_session, 2, "Krokodil", "Wasser")
    assert crocodile["swimSpeed"] == "12 m"  # 9 + 3


def test_fire_companion_bonus_feat_counts_as_prerequisite(client: TestClient, db_session: Session) -> None:
    wolf = _elemental(client, db_session, 9, "Wolf", "Feuer")
    assert _features(wolf)["Größere elementare Manifestation (Feuer)"]["summary"].startswith("+1W6 Feuerschaden")
    # Geschmeidige Bewegung requires Behände Bewegung (and GE 15).
    eligible = {f["name"] for f in client.get(f"/api/feats?character_id={wolf['id']}").json()}
    assert "Geschmeidige Bewegung" in eligible
    earth = _elemental(client, db_session, 9, "Wolf", "Erde")
    assert "Geschmeidige Bewegung" not in {f["name"] for f in client.get(f"/api/feats?character_id={earth['id']}").json()}


def test_archetype_can_be_set_and_cleared_later(client: TestClient, db_session: Session) -> None:
    master = _druide(client, db_session, 3)
    wolf = _companion(client, master, "Wolf")
    assert wolf["companion"]["archetype"] is None
    assert "Entrinnen" in _features(wolf)
    water = _archetype_id(wolf["companion"]["archetypeOptions"], "Wasser")

    response = client.put(f"/api/characters/{wolf['id']}/companion-archetype", json={"archetype_id": water})
    assert response.status_code == 200, response.text
    wolf = client.get(f"/api/characters/{wolf['id']}").json()
    assert wolf["companion"]["archetype"]["id"] == water
    assert "Entrinnen" not in _features(wolf)

    client.put(f"/api/characters/{wolf['id']}/companion-archetype", json={"archetype_id": None})
    assert "Entrinnen" in _features(client.get(f"/api/characters/{wolf['id']}").json())


def test_archetype_is_validated(client: TestClient, db_session: Session) -> None:
    master = _druide(client, db_session, 1)
    unknown = "00000000-0000-0000-0000-000000000000"
    response = client.put(f"/api/characters/{master['id']}/companion-archetype", json={"archetype_id": unknown})
    assert response.status_code == 422  # not a companion
    wolf = _companion(client, master, "Wolf")
    response = client.put(f"/api/characters/{wolf['id']}/companion-archetype", json={"archetype_id": unknown})
    assert response.status_code == 422
