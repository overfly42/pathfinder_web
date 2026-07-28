from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.race_seed import seed_races


def test_list_races_reconstructs_fixture_shape(client: TestClient, db_session: Session) -> None:
    seed_races(db_session)

    response = client.get("/api/races")
    assert response.status_code == 200
    races = {r["name"]: r for r in response.json()}

    assert set(races) == {"Mensch", "Elf", "Zwerg", "Halbling", "Gnom", "Halbelf", "Halb-Ork"}

    elf = races["Elf"]
    assert elf["flex"] is False
    assert elf["mods"] == {"GE": 2, "IN": 2, "KO": -2}
    trait_names = {t["name"] for t in elf["traits"]}
    assert trait_names == {
        "Niedrigsichtig",
        "Elfische Waffenvertrautheit",
        "Zauberkundig",
        "Widerstandsfähiger Geist",
    }
    alt_names = {a["name"]: a["replaces"] for a in elf["alt"]}
    assert alt_names == {
        "Eisenkultur": ["Elfische Waffenvertrautheit"],
        "Küstenbewohner": ["Zauberkundig"],
    }


def test_flex_attribute_bonus_is_shared_and_not_duplicated_as_a_trait(
    client: TestClient, db_session: Session
) -> None:
    seed_races(db_session)

    response = client.get("/api/races")
    races = {r["name"]: r for r in response.json()}

    mensch = races["Mensch"]
    halbork = races["Halb-Ork"]
    assert mensch["flex"] is True
    assert halbork["flex"] is True

    # The shared "+2 to any attribute" bonus must not also show up as a named
    # trait (it did, inconsistently, for Human only, in the raw fixture).
    assert "Anpassungsfähig" not in {t["name"] for t in mensch["traits"]}


def test_darkvision_is_one_shared_ability_across_races(client: TestClient, db_session: Session) -> None:
    seed_races(db_session)

    response = client.get("/api/races")
    races = {r["name"]: r for r in response.json()}

    zwerg_trait = next(t for t in races["Zwerg"]["traits"] if t["name"] == "Dunkelsicht")
    halbork_trait = next(t for t in races["Halb-Ork"]["traits"] if t["name"] == "Dunkelsicht")
    assert zwerg_trait["desc"] == halbork_trait["desc"]
