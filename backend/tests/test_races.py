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

    # Elf, Zwerg, Gnom and Halbelf were never checked against the real SRD
    # (only plausibly LLM-guessed content, see todos.md's disclaimer). Zwerg,
    # Gnom and Halbelf have since been removed outright (unbacked by any
    # source); Elf was instead corrected against the real source (see
    # test_elf_standard_traits_and_alternates_are_real) since it's also the
    # reference race used throughout the character-creation test suite.
    assert set(races) == {"Mensch", "Elf", "Halbling", "Halb-Ork"}

    elf = races["Elf"]
    assert elf["flex"] is False
    assert elf["mods"] == {"GE": 2, "IN": 2, "KO": -2}
    trait_names = {t["name"] for t in elf["traits"]}
    assert trait_names == {
        "Dämmersicht",
        "Elfische Immunität",
        "Elfenmagie",
        "Geschärfte Sinne",
        "Elfische Waffenvertrautheit",
        # Speed/size (previously a plain `BaseRace.speed` column and an
        # unmodeled default) are now racial-trait grants like everything
        # else — see rules/speed.py.
        "Normale Bewegungsrate",
        "Mittelgroß",
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
    # Halb-Ork's real optional trait swaps (see
    # test_mensch_standard_traits_and_alternates_are_real /
    # test_halbork_standard_traits_and_alternates_are_real for the full,
    # content-checked alternate-trait lists).
    flex_backing_names = {
        "+2 auf Geschicklichkeit",
        "+2 auf Intelligenz",
        "+2 auf Konstitution",
        "+2 auf Weisheit",
        "+2 auf Charisma",
        "+2 auf Stärke",
    }
    assert flex_backing_names.isdisjoint({a["name"] for a in mensch["alt"]})
    assert flex_backing_names.isdisjoint({a["name"] for a in halbork["alt"]})


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
    must be granted to every race, including the real Small race
    (Halbling) that was previously silently assumed Medium."""
    seed_races(db_session)
    races = {r["name"]: r["id"] for r in client.get("/api/races").json()}

    assert race_speed(db_session, races["Halbling"]) == 6
    assert race_speed(db_session, races["Mensch"]) == 9
    assert race_speed(db_session, races["Elf"]) == 9
    assert race_speed(db_session, races["Halb-Ork"]) == 9

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


def test_mensch_standard_traits_and_alternates_are_real(client: TestClient, db_session: Session) -> None:
    """Content-correction pass against the real German SRD
    (<http://prd.5footstep.de/AusbauregelnIIIVoelker/Grundvoelker/Menschen>,
    see todos.md) — the earlier Mensch-correction pass verified the standard
    traits but incorrectly concluded Mensch has no alternate traits at all;
    the source's "Alternative Volksmerkmale" section actually lists 15 real
    entries, now seeded."""
    seed_races(db_session)

    response = client.get("/api/races")
    mensch = {r["name"]: r for r in response.json()}["Mensch"]

    trait_names = {t["name"] for t in mensch["traits"]}
    assert trait_names == {"Bonustalent", "Geschult", "Normale Bewegungsrate", "Mittelgroß"}

    alt_names = {a["name"] for a in mensch["alt"]}
    assert alt_names == {
        "Bergkind", "Blick für Begabungen", "Doppelte Begabung", "Elendskind", "Findelkind",
        "Glattzüngig", "Heldenhaft", "Konzentriertes Lernen", "Landkind", "Meereskind",
        "Mischling", "Naturkind", "Sommerkind", "Stadtkind", "Winterkind",
    }
    assert "Bemerkenswerte Fertigkeit" not in alt_names
    assert "Fokussierter Geist" not in alt_names

    replaces_by_name = {a["name"]: set(a["replaces"]) for a in mensch["alt"]}
    assert replaces_by_name["Bergkind"] == {"Geschult"}
    assert replaces_by_name["Blick für Begabungen"] == {"Bonustalent"}
    # Replaces all three standard traits at once; the shared flex "+2 to any
    # attribute" marker is filtered from `replaces` by `_race_option` (it's
    # not a player-facing named trait), so only the other two show up.
    assert replaces_by_name["Doppelte Begabung"] == {"Bonustalent", "Geschult"}


def test_halbork_standard_traits_and_alternates_are_real(client: TestClient, db_session: Session) -> None:
    """Content-correction pass against the real German SRD
    (<http://prd.5footstep.de/AusbauregelnIIIVoelker/Grundvoelker/HalbOrks>,
    see todos.md) — the DB previously had two missing standard traits
    ("Einschüchternd", "Waffenvertrautheit (Halb-Orks)"), a standard trait
    that existed but was misnamed/under-described ("Kampfrausch", now
    "Orkische Wildheit"), and two invented alternates ("Einschüchternde
    Erscheinung"/"Wildnisschritt") that didn't match any real trait. Now
    corrected to the real standard traits plus all 14 real alternates."""
    seed_races(db_session)

    response = client.get("/api/races")
    halbork = {r["name"]: r for r in response.json()}["Halb-Ork"]

    trait_names = {t["name"] for t in halbork["traits"]}
    assert trait_names == {
        "Dunkelsicht",
        "Orkische Wildheit",
        "Orkblut",
        "Einschüchternd",
        "Waffenvertrautheit (Halb-Orks)",
        "Normale Bewegungsrate",
        "Mittelgroß",
    }
    assert "Kampfrausch" not in trait_names

    alt_names = {a["name"] for a in halbork["alt"]}
    assert alt_names == {
        "Bestiensinne", "Geschult", "Gesteigerte Dunkelsicht", "Geübter Kletterer",
        "Heilige Tätowierung", "Herr der Bestien", "Höhlenkundiger", "Kettenkrieger",
        "Kind der Großstadt", "Lumpensammler", "Reißzähne", "Schamanenschüler",
        "Waldwanderer", "Zerstörer",
    }
    assert "Einschüchternde Erscheinung" not in alt_names
    assert "Wildnisschritt" not in alt_names

    replaces_by_name = {a["name"]: set(a["replaces"]) for a in halbork["alt"]}
    assert replaces_by_name["Geschult"] == {"Dunkelsicht"}
    assert replaces_by_name["Kind der Großstadt"] == {"Waffenvertrautheit (Halb-Orks)"}
    assert replaces_by_name["Gesteigerte Dunkelsicht"] == {"Orkische Wildheit"}


def test_elf_standard_traits_and_alternates_are_real(client: TestClient, db_session: Session) -> None:
    """Content-correction pass against the real German SRD
    (<http://prd.5footstep.de/AusbauregelnIIIVoelker/Grundvoelker/Elfen>, see
    todos.md) — the DB previously had two misnamed/under-described standard
    traits ("Niedrigsichtig" for the real "Dämmersicht"; "Widerstandsfähiger
    Geist" and "Zauberkundig" as a split, misnamed version of the real
    "Elfische Immunität"/"Elfenmagie") and two invented alternates
    ("Eisenkultur", "Küstenbewohner" — neither matched any real trait). Now
    corrected to the real standard traits plus all 13 real alternates."""
    seed_races(db_session)

    response = client.get("/api/races")
    elf = {r["name"]: r for r in response.json()}["Elf"]

    trait_names = {t["name"] for t in elf["traits"]}
    assert "Niedrigsichtig" not in trait_names
    assert "Widerstandsfähiger Geist" not in trait_names
    assert "Zauberkundig" not in trait_names

    alt_names = {a["name"] for a in elf["alt"]}
    assert alt_names == {
        "Abgesandter", "Arkane Konzentration", "Dunkelsicht", "Elementarresistenz", "Ewiger Groll",
        "Leichtfüßig", "Lichtbringer", "Naturverbundenheit", "Schleichender Jäger", "Stadtverbundenheit",
        "Traumdeuter", "Wasserverbundenheit", "Wüstenläufer",
    }
    assert "Eisenkultur" not in alt_names
    assert "Küstenbewohner" not in alt_names

    replaces_by_name = {a["name"]: set(a["replaces"]) for a in elf["alt"]}
    assert replaces_by_name["Dunkelsicht"] == {"Dämmersicht"}
    assert replaces_by_name["Leichtfüßig"] == {"Geschärfte Sinne", "Elfische Waffenvertrautheit"}
    assert replaces_by_name["Wasserverbundenheit"] == {"Elfenmagie", "Elfische Waffenvertrautheit"}


def test_medium_size_is_one_shared_ability_across_races(client: TestClient, db_session: Session) -> None:
    """"Mittelgroß" (like "Dunkelsicht") is one shared catalog row reused by
    every medium-sized race's grant, not duplicated with a fresh id each
    time — see rules/speed.py and the composition-vs-computation split in
    CLAUDE.md. (Elf's "Dunkelsicht" alternate is a deliberate exception: it
    carries an extra light-sensitivity drawback the plain shared ability
    doesn't have, so it's intentionally its own catalog row instead of
    reusing Half-Ork's/Zwerg's.)"""
    seed_races(db_session)

    response = client.get("/api/races")
    races = {r["name"]: r for r in response.json()}

    mensch_trait = next(t for t in races["Mensch"]["traits"] if t["name"] == "Mittelgroß")
    halbork_trait = next(t for t in races["Halb-Ork"]["traits"] if t["name"] == "Mittelgroß")
    elf_trait = next(t for t in races["Elf"]["traits"] if t["name"] == "Mittelgroß")
    assert mensch_trait["desc"] == halbork_trait["desc"] == elf_trait["desc"]
