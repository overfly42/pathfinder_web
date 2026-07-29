from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.routers.races import race_has_flex, resolve_flex_ability_id
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

    # The 6 per-attribute alternates that back the flex bonus (see
    # `resolve_flex_ability_id`) are internal plumbing, not player-facing
    # alternate traits — they must not leak into `alt` alongside Mensch's/
    # Halb-Ork's real optional trait swaps.
    assert {a["name"] for a in mensch["alt"]} == {"Bemerkenswerte Fertigkeit", "Fokussierter Geist"}
    assert {a["name"] for a in halbork["alt"]} == {"Einschüchternde Erscheinung", "Wildnisschritt"}


def test_resolve_flex_ability_id_goes_through_the_replacement_system(client: TestClient, db_session: Session) -> None:
    seed_races(db_session)
    races = {r["name"]: r["id"] for r in client.get("/api/races").json()}

    assert race_has_flex(db_session, races["Mensch"]) is True
    assert race_has_flex(db_session, races["Elf"]) is False

    st_choice = resolve_flex_ability_id(db_session, races["Mensch"], "ST")
    ge_choice = resolve_flex_ability_id(db_session, races["Mensch"], "GE")
    assert st_choice is not None
    assert ge_choice is not None
    assert st_choice != ge_choice

    # Elf has no flex bonus at all, so no attribute resolves for it.
    assert resolve_flex_ability_id(db_session, races["Elf"], "ST") is None


def test_darkvision_is_one_shared_ability_across_races(client: TestClient, db_session: Session) -> None:
    seed_races(db_session)

    response = client.get("/api/races")
    races = {r["name"]: r for r in response.json()}

    zwerg_trait = next(t for t in races["Zwerg"]["traits"] if t["name"] == "Dunkelsicht")
    halbork_trait = next(t for t in races["Halb-Ork"]["traits"] if t["name"] == "Dunkelsicht")
    assert zwerg_trait["desc"] == halbork_trait["desc"]
