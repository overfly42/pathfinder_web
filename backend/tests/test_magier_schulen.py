"""The Magier's elemental schools and subschools
(`scripts/import_magier_schulen.py`, `rules/classes/magier.py`)."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import BaseFeat, Character
from app.routers.feats import _character_prereq_state

from test_characters import _character_payload, _create_user, _human_race_id


def _magier(client: TestClient, db_session: Session, school: str, level: int = 8) -> dict:
    payload = _character_payload(
        _create_user(client),
        _human_race_id(client, db_session),
        db_session,
        classes=[{"class_name": "Magier", "level": level, "options": {"school": [school]}}],
        flex_ability="IN",
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{response.json()['id']}").json()


def _features(sheet: dict) -> set[str]:
    return {f["name"] for f in sheet["classFeatures"]}


def test_school_group_lists_the_new_schools(client: TestClient) -> None:
    magier = next(c for c in client.get("/api/classes").json() if c["name"] == "Magier")
    names = {c["name"] for c in next(g for g in magier["optionGroups"] if g["key"] == "school")["choices"]}

    assert len(names) == 29
    assert {"Elementarmagieschule der Erde", "Unterschule der Vorsehung", "Universalist"} <= names


def test_elemental_school_grants_its_own_powers(client: TestClient, db_session: Session) -> None:
    features = _features(_magier(client, db_session, "Elementarmagieschule des Feuers"))

    assert {"Elementarmagieschule des Feuers", "Feuerüberlegenheit", "Flammenstrahl", "Tanzende Flamme"} <= features
    assert "Starke Zauber" not in features


def test_subschool_swaps_powers_of_its_main_school(client: TestClient, db_session: Session) -> None:
    features = _features(_magier(client, db_session, "Unterschule der Gegenzauber"))

    # Resistenz stays, Schutz/Energieabsorption (6th) become the new powers.
    assert {"Unterschule der Gegenzauber", "Resistenz", "Zauber stören", "Gegenzaubermeisterschaft"} <= features
    assert not {"Schutz", "Energieabsorption"} & features


def test_gegenzaubermeisterschaft_grants_verbesserter_gegenzauber(client: TestClient, db_session: Session) -> None:
    # A class-granted feat isn't a `CharacterFeat` pick, it counts for
    # prerequisites (`BaseClassAbilityGrantedFeat`).
    sheet = _magier(client, db_session, "Unterschule der Gegenzauber", level=6)
    feat = db_session.query(BaseFeat).filter_by(name="Verbesserter Gegenzauber").one()

    state = _character_prereq_state(db_session, db_session.get(Character, UUID(sheet["id"])))
    assert feat.id in state.feat_ids


def test_luftueberlegenheit_scales_with_magier_level(client: TestClient, db_session: Session) -> None:
    sheet = _magier(client, db_session, "Elementarmagieschule der Luft", level=10)

    breakdown = next(s for s in sheet["skills"] if s["label"] == "Fliegen")["breakdown"]
    assert {"label": "Luftüberlegenheit", "value": 4} in breakdown
