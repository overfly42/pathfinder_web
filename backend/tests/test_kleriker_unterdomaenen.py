"""The Kleriker subdomains (`scripts/import_kleriker_unterdomaenen.py`) and
the `BaseClassOptionChoice.exclusion_keys` check they needed
(`routers/characters.py`'s `_check_exclusions`)."""

from collections import Counter

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.rules.classes.kleriker import FEDERN_VERLIEHENE_FAEHIGKEITEN_ID, FLIEGEN_SKILL_ID
from app.rules.context import CharacterContext
from app.rules.handlers import granted_class_skill_ids

from test_characters import _character_payload, _create_user, _human_race_id


def _create(client: TestClient, db_session: Session, selection: dict):
    payload = _character_payload(
        _create_user(client), _human_race_id(client, db_session), db_session, classes=[selection], flex_ability="CH"
    )
    return client.post("/api/characters", json=payload)


def _kleriker(client: TestClient, db_session: Session, domains: list[str], level: int = 8):
    return _create(client, db_session, {"class_name": "Kleriker", "level": level, "options": {"domain": domains}})


def _features(client: TestClient, response) -> set[str]:
    assert response.status_code == 201, response.text
    sheet = client.get(f"/api/characters/{response.json()['id']}").json()
    return {f["name"] for f in sheet["classFeatures"]}


def _group(client: TestClient, class_name: str, key: str) -> dict:
    cls = next(c for c in client.get("/api/classes").json() if c["name"] == class_name)
    return next(g for g in cls["optionGroups"] if g["key"] == key)


def test_subdomain_swaps_one_power_of_its_main_domain(client: TestClient, db_session: Session) -> None:
    features = _features(client, _kleriker(client, db_session, ["Unterdomäne der Asche", "Domäne des Guten"]))

    # Feuerpfeil stays, Feuerresistenz (8th) becomes Aschewand.
    assert {
        "Verliehene Fähigkeiten (Domäne des Feuers)",
        "Verliehene Fähigkeiten (Unterdomäne der Asche)",
        "Feuerpfeil",
        "Aschewand",
    } <= features
    assert "Feuerresistenz" not in features


def test_subdomain_excludes_its_main_domain_and_siblings(client: TestClient, db_session: Session) -> None:
    for domains in (
        ["Domäne des Feuers", "Unterdomäne der Asche"],
        ["Unterdomäne der Asche", "Unterdomäne des Rauches"],
        ["Unterdomäne der Archonten (Gutes)", "Unterdomäne der Archonten (Ordnung)"],
    ):
        response = _kleriker(client, db_session, domains)
        assert response.status_code == 422, domains
        assert "can't be combined" in response.json()["detail"]


def test_two_main_domain_subdomain_replaces_the_chosen_domains_power(client: TestClient, db_session: Session) -> None:
    features = _features(
        client, _kleriker(client, db_session, ["Unterdomäne der Archonten (Ordnung)", "Domäne der Erde"])
    )

    assert {"Hauch der Ordnung", "Aura der Bedrohung"} <= features
    assert "Stab der Ordnung" not in features


def test_federn_makes_fliegen_a_class_skill(client: TestClient, db_session: Session) -> None:
    features = _features(client, _kleriker(client, db_session, ["Unterdomäne der Federn", "Domäne der Erde"], level=4))

    # Mit-Tieren-sprechen replaced, the Tier-Domäne's Tiergefährte kept.
    assert {"Adleraugen", "Tiergefährte"} <= features
    assert "Mit-Tieren-sprechen" not in features
    context = CharacterContext(granted_ability_ids=Counter({FEDERN_VERLIEHENE_FAEHIGKEITEN_ID: 1}))
    assert FLIEGEN_SKILL_ID in granted_class_skill_ids(context)


def test_druide_and_goettlicher_jaeger_get_the_subdomains(client: TestClient, db_session: Session) -> None:
    nature = {c["name"] for c in _group(client, "Druide", "nature_domain")["choices"]}
    hunter = {c["name"] for c in _group(client, "Jäger", "divine_hunter_domain")["choices"]}

    assert {"Unterdomäne der Höhlen", "Unterdomäne der Federn"} <= nature
    assert "Unterdomäne der Metalle" not in nature
    assert "Unterdomäne der Proteaner" not in nature  # Chaos isn't a Naturdomäne
    assert {"Unterdomäne der Metalle", "Unterdomäne der Proteaner"} <= hunter

    druide = _create(
        client,
        db_session,
        {
            "class_name": "Druide",
            "level": 6,
            "options": {"bond": ["Domäne (Natur)"], "nature_domain": ["Unterdomäne der Höhlen"]},
        },
    )
    features = _features(client, druide)
    assert {"Säuregeschoss", "Tunnelläufer"} <= features
    assert "Säureresistenz" not in features


def test_exclusion_keys_reach_the_wizard(client: TestClient, db_session: Session) -> None:
    choices = {c["name"]: c for c in _group(client, "Kleriker", "domain")["choices"]}

    assert choices["Domäne des Feuers"]["exclusionKeys"] == ["Domäne des Feuers"]
    assert choices["Unterdomäne der Asche"]["exclusionKeys"] == ["Domäne des Feuers", "Unterdomäne der Asche"]
