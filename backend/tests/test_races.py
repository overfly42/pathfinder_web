from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.routers.races import race_has_flex, resolve_flex_ability_id
from app.rules.speed import race_speed
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
        # Speed/size (previously a plain `BaseRace.speed` column and an
        # unmodeled default) are now racial-trait grants like everything
        # else — see rules/speed.py.
        "Normale Bewegungsrate",
        "Mittelgroß",
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
    # Mensch has no alternate racial traits modeled yet (roadmap: only the
    # real, verified PF1e standard traits are seeded for now; see todos.md).
    assert {a["name"] for a in mensch["alt"]} == set()
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


def test_race_speed_and_size_are_grants_not_a_column(client: TestClient, db_session: Session) -> None:
    """`BaseRace.speed` was removed (migration 005957a8da7f) in favor of a
    real racial-trait grant, same composition-vs-computation split as
    everything else — see rules/speed.py. Size (Klein/Mittelgroß) has no
    computation yet (flavor-only, like Darkvision), but the correct trait
    must be granted to every race, including the two real Small races
    (Halbling/Gnom) that were previously silently assumed Medium."""
    seed_races(db_session)
    races = {r["name"]: r["id"] for r in client.get("/api/races").json()}

    assert race_speed(db_session, races["Halbling"]) == "6 m"
    assert race_speed(db_session, races["Gnom"]) == "6 m"
    assert race_speed(db_session, races["Zwerg"]) == "6 m"
    assert race_speed(db_session, races["Mensch"]) == "9 m"
    assert race_speed(db_session, races["Elf"]) == "9 m"
    assert race_speed(db_session, races["Halbelf"]) == "9 m"
    assert race_speed(db_session, races["Halb-Ork"]) == "9 m"

    response = client.get("/api/races")
    races_by_name = {r["name"]: r for r in response.json()}
    halbling_traits = {t["name"] for t in races_by_name["Halbling"]["traits"]}
    mensch_traits = {t["name"] for t in races_by_name["Mensch"]["traits"]}
    assert "Klein" in halbling_traits
    assert "Mittelgroß" not in halbling_traits
    assert "Mittelgroß" in mensch_traits
    assert "Klein" not in mensch_traits


def test_halbling_standard_traits_and_alternates_are_real(client: TestClient, db_session: Session) -> None:
    """Content-correction pass against the real German SRD
    (<http://prd.5footstep.de/AusbauregelnIIIVoelker/Grundvoelker/Halblinge>,
    see todos.md) — the DB previously had "Flink"/"Glücklich" (wrong
    names/values) and two invented alternates ("Unauffällig"/"Geschickter
    Wanderer") that didn't match any real trait. Now corrected to the real
    standard traits plus all 13 real alternates."""
    seed_races(db_session)

    response = client.get("/api/races")
    halbling = {r["name"]: r for r in response.json()}["Halbling"]

    trait_names = {t["name"] for t in halbling["traits"]}
    assert trait_names == {
        "Furchtlos",
        "Halblingsglück",
        "Wendig",
        "Verminderte Bewegungsrate",
        "Klein",
        "Geschärfte Sinne",
        "Waffenvertrautheit (Halblinge)",
    }
    assert "Flink" not in trait_names
    assert "Glücklich" not in trait_names

    alt_names = {a["name"] for a in halbling["alt"]}
    assert alt_names == {
        "Arglistig", "Einschmeichelnd", "Flinker Schleuderer", "Grenzreiter", "Mehrsprachigkeit",
        "Praktisch begabt", "Schnell wie ein Schatten", "Schnell zu Fuß", "Tiefschlag",
        "Vielseitiges Glück", "Wanderslust", "Wuselig", "Zaghaft",
    }
    assert "Unauffällig" not in alt_names
    assert "Geschickter Wanderer" not in alt_names

    replaces_by_name = {a["name"]: set(a["replaces"]) for a in halbling["alt"]}
    assert replaces_by_name["Schnell zu Fuß"] == {"Verminderte Bewegungsrate", "Wendig"}
    assert replaces_by_name["Wanderslust"] == {"Furchtlos", "Halblingsglück"}


def test_darkvision_is_one_shared_ability_across_races(client: TestClient, db_session: Session) -> None:
    seed_races(db_session)

    response = client.get("/api/races")
    races = {r["name"]: r for r in response.json()}

    zwerg_trait = next(t for t in races["Zwerg"]["traits"] if t["name"] == "Dunkelsicht")
    halbork_trait = next(t for t in races["Halb-Ork"]["traits"] if t["name"] == "Dunkelsicht")
    assert zwerg_trait["desc"] == halbork_trait["desc"]
