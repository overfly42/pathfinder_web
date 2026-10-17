"""Aasimar, added straight from the real German SRD
(<http://prd.5footstep.de/AusbauregelnIIIVoelker/UngewoehnlicheVoelker/Aasimare>,
`import_aasimar.py`): its standard/alternate racial traits, and the flat
skill bonuses `rules/race_abilities.py` models for Bewandert and
Sprachenmeister."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.race_seed import seed_races
from test_characters import _character_payload, _create_user, _race_id, _skill_id


def test_aasimar_standard_traits_and_alternates_are_real(client: TestClient, db_session: Session) -> None:
    seed_races(db_session)

    aasimar = {r["name"]: r for r in client.get("/api/races").json()}["Aasimar"]

    assert aasimar["flex"] is False
    assert aasimar["mods"] == {"WE": 2, "CH": 2}

    assert {t["name"] for t in aasimar["traits"]} == {
        "Einheimischer Externar",
        "Mittelgroß",
        "Normale Bewegungsrate",
        "Bewandert",
        "Celestische Resistenz",
        "Dunkelsicht",
        "Zauberähnliche Fähigkeit (Tageslicht)",
    }

    replaces_by_name = {a["name"]: set(a["replaces"]) for a in aasimar["alt"]}
    assert replaces_by_name == {
        "Charakterstark": {"Zauberähnliche Fähigkeit (Tageslicht)"},
        "Celestischer Kreuzfahrer": {"Bewandert", "Celestische Resistenz"},
        "Erhabene Resistenz": {"Celestische Resistenz"},
        "Heiligenschein": {"Dunkelsicht"},
        "Himmelsgeboren": {"Bewandert", "Zauberähnliche Fähigkeit (Tageslicht)"},
        "Spross der Menschheit": {"Einheimischer Externar"},
        "Sprachenmeister": {"Bewandert"},
        "Unsterblicher Geist": {"Celestische Resistenz"},
        "Unsterblicher Lebensfunke": {"Bewandert", "Zauberähnliche Fähigkeit (Tageslicht)"},
    }


def test_sprachenmeister_replaces_bewandert_skill_bonus(client: TestClient, db_session: Session) -> None:
    """Default Aasimar gets Bewandert's +2 Diplomatie; picking Sprachenmeister
    drops it and grants +2 Motiv erkennen instead. Compared relative to each
    other so the test doesn't depend on the payload's default scores."""
    user_id = _create_user(client)
    race_id = _race_id(client, db_session, "Aasimar")
    diplomatie_id = _skill_id(client, db_session, "Diplomatie")
    motiv_id = _skill_id(client, db_session, "Motiv erkennen")

    def skill_values(**overrides) -> dict[str, int]:
        character = client.post(
            "/api/characters", json=_character_payload(user_id, race_id, db_session, **overrides)
        ).json()
        sheet = client.get(f"/api/characters/{character['id']}").json()
        return {s["key"]: int(s["value"]) for s in sheet["skills"]}

    default = skill_values()
    sprachenmeister = skill_values(alt_traits=["Sprachenmeister"])

    assert default[diplomatie_id] - sprachenmeister[diplomatie_id] == 2
    assert sprachenmeister[motiv_id] - default[motiv_id] == 2


def test_partially_computed_traits_carry_a_partial_note(client: TestClient, db_session: Session) -> None:
    """Three badge states (`rules/handlers.py`'s `partial_effect_note`):
    fully computed (Bewandert) -> no note; partly computed (Sprachenmeister:
    skill bonus yes, extra languages no) -> note; not computed at all
    (Celestische Resistenz) -> `hasHandler` false, no note."""
    user_id = _create_user(client)
    race_id = _race_id(client, db_session, "Aasimar")

    aasimar = {r["name"]: r for r in client.get("/api/races").json()}["Aasimar"]
    traits = {t["name"]: t for t in aasimar["traits"]}
    alts = {a["name"]: a for a in aasimar["alt"]}
    assert traits["Bewandert"]["hasHandler"] is True
    assert traits["Bewandert"]["partialNote"] is None
    assert traits["Celestische Resistenz"]["hasHandler"] is False
    assert traits["Celestische Resistenz"]["partialNote"] is None
    assert alts["Sprachenmeister"]["hasHandler"] is True
    assert "Sprachenkunde" in alts["Sprachenmeister"]["partialNote"]

    character = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, alt_traits=["Sprachenmeister"]),
    ).json()
    sheet = client.get(f"/api/characters/{character['id']}").json()
    race_abilities = {a["name"]: a for a in sheet["raceAbilities"]}
    assert race_abilities["Sprachenmeister"]["partialNote"]
    assert race_abilities["Celestische Resistenz"]["partialNote"] is None
