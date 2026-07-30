from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BaseRaceAbility, Character, CharacterRacialChoice, CharacterSkillRank, RaceAbilityReplacement
from app.rules.race_abilities import HANDLERS
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.race_seed import seed_races
from app.seed.skill_seed import seed_skills

DEFAULT_ABILITY_SCORES = {"ST": 10, "GE": 12, "KO": 13, "IN": 10, "WE": 10, "CH": 8}


def _create_user(client: TestClient, name: str = "Anna") -> str:
    return client.post("/api/users", json={"name": name}).json()["id"]


def _race_id(client: TestClient, db_session: Session, name: str) -> str:
    seed_races(db_session)
    races = client.get("/api/races").json()
    return next(r["id"] for r in races if r["name"] == name)


def _elf_race_id(client: TestClient, db_session: Session) -> str:
    return _race_id(client, db_session, "Elf")


def _human_race_id(client: TestClient, db_session: Session) -> str:
    return _race_id(client, db_session, "Mensch")


def _skill_id(client: TestClient, db_session: Session, name: str) -> str:
    seed_classes(db_session)  # base_class_skills FKs into base_classes
    seed_skills(db_session)
    skills = client.get("/api/skills").json()
    return next(s["id"] for s in skills if s["name"] == name)


def _character_payload(user_id: str, race_id: str, db_session: Session, **overrides) -> dict:
    seed_classes(db_session)  # base_class_option_groups FKs into base_classes
    seed_class_options(db_session)
    payload = {
        "name": "Elyra",
        "user_id": user_id,
        "race_id": race_id,
        "classes": [{"class_name": "Waldläufer", "level": 1}],
        "current_hit_points": 8,
        "ability_scores": DEFAULT_ABILITY_SCORES,
        "point_budget": 20,
    }
    payload.update(overrides)
    return payload


def test_create_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session))
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Elyra"
    assert body["race_id"] == race_id
    assert body["level"] == 1
    assert body["classes"] == [
        {"class_name": "Waldläufer", "level": 1, "archetypes": [], "is_favored": True, "options": {}}
    ]
    assert body["current_hit_points"] == 8
    assert body["ability_scores"] == DEFAULT_ABILITY_SCORES
    assert body["point_budget"] == 20
    assert body["flex_ability"] is None


def test_create_character_with_unknown_race_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, "00000000-0000-0000-0000-000000000000", db_session),
    )
    assert response.status_code == 422


def test_create_character_with_unknown_class_name_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, classes=[{"class_name": "Nichtklasse", "level": 1}]),
    )
    assert response.status_code == 422


def test_create_character_with_multiple_classes_persists_per_level_history(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Krieger", "level": 2}, {"class_name": "Schurke", "level": 1}],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["level"] == 3
    assert body["classes"] == [
        {"class_name": "Krieger", "level": 2, "archetypes": [], "is_favored": True, "options": {}},
        {"class_name": "Schurke", "level": 1, "archetypes": [], "is_favored": False, "options": {}},
    ]


def test_create_character_with_archetype_persists_and_round_trips(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Krieger", "level": 2, "archetypes": ["Waffenmeister"]}],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["classes"] == [
        {"class_name": "Krieger", "level": 2, "archetypes": ["Waffenmeister"], "is_favored": True, "options": {}}
    ]

    refetched = client.get(f"/api/characters/{body['id']}").json()
    assert refetched["classes"] == body["classes"]


def test_create_character_with_unknown_archetype_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, classes=[{"class_name": "Krieger", "level": 1, "archetypes": ["Berserker"]}]
        ),
    )
    assert response.status_code == 422


def test_create_character_with_multiple_archetypes_on_one_class_succeeds(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[
                {
                    "class_name": "Krieger",
                    "level": 1,
                    "archetypes": ["Waffenmeister", "Söldnerkommandant"],
                }
            ],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body["classes"][0]["archetypes"]) == {"Waffenmeister", "Söldnerkommandant"}


def test_create_character_with_same_class_across_rows_merges_archetypes(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[
                {"class_name": "Krieger", "level": 1, "archetypes": ["Waffenmeister"]},
                {"class_name": "Schurke", "level": 1},
                {"class_name": "Krieger", "level": 1, "archetypes": ["Söldnerkommandant"]},
            ],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["classes"]) == 2
    krieger = next(c for c in body["classes"] if c["class_name"] == "Krieger")
    assert krieger["level"] == 2
    assert set(krieger["archetypes"]) == {"Waffenmeister", "Söldnerkommandant"}


def test_create_character_with_option_group_choice_persists(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Kleriker", "level": 1, "options": {"domain": ["Sonne", "Tod"]}}],
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["classes"][0]["options"] == {"domain": ["Sonne", "Tod"]}


def test_create_character_with_invalid_option_choice_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Kleriker", "level": 1, "options": {"domain": ["Nichtdomäne"]}}],
        ),
    )
    assert response.status_code == 422


def test_create_character_exceeding_option_group_max_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[
                {
                    "class_name": "Kleriker",
                    "level": 1,
                    "options": {"domain": ["Sonne", "Tod", "Wissen"]},
                }
            ],
        ),
    )
    assert response.status_code == 422


def test_create_character_over_point_buy_budget_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, ability_scores={"ST": 18, "GE": 18, "KO": 18, "IN": 18, "WE": 18, "CH": 18}
        ),
    )
    assert response.status_code == 422


def test_create_character_with_ability_score_out_of_range_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, ability_scores={**DEFAULT_ABILITY_SCORES, "ST": 19}),
    )
    assert response.status_code == 422


def test_create_character_for_flex_race_requires_flex_ability(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    response = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session))
    assert response.status_code == 422


def test_create_character_for_flex_race_with_flex_ability_succeeds(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    response = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session, flex_ability="GE"))
    assert response.status_code == 201
    assert response.json()["flex_ability"] == "GE"


def test_create_character_for_flex_race_persists_choice_via_replacement_system(
    client: TestClient, db_session: Session
) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    created = client.post(
        "/api/characters", json=_character_payload(user_id, race_id, db_session, flex_ability="ST")
    ).json()

    character = db_session.get(Character, created["id"])
    choices = db_session.scalars(
        select(CharacterRacialChoice).where(CharacterRacialChoice.character_id == character.id)
    ).all()
    assert len(choices) == 1
    # The stored row is an ability_id resolved through RaceAbilityReplacement,
    # not a raw "ST" string — resolving it back through HANDLERS must agree
    # with what was requested.
    attribute, value = HANDLERS[choices[0].ability_id]()
    assert (attribute, value) == ("ST", 2)


def test_create_character_for_non_flex_race_rejects_flex_ability(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session, flex_ability="GE"))
    assert response.status_code == 422


def test_create_character_persists_alt_traits(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, alt_traits=["Eisenkultur", "Küstenbewohner"]),
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body["alt_traits"]) == {"Eisenkultur", "Küstenbewohner"}

    character = db_session.get(Character, body["id"])
    choices = db_session.scalars(
        select(CharacterRacialChoice).where(CharacterRacialChoice.character_id == character.id)
    ).all()
    assert len(choices) == 2


def test_create_character_rejects_unknown_alt_trait(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)

    response = client.post(
        "/api/characters", json=_character_payload(user_id, race_id, db_session, alt_traits=["Nicht Existent"])
    )
    assert response.status_code == 422


def test_create_character_rejects_flex_only_alternate_as_alt_trait(client: TestClient, db_session: Session) -> None:
    """The flex "+2 to any attribute" alternates share the ability catalog
    with real alt-traits (both are `is_alternate=True` grants) but must only
    be pickable via `flex_ability`, never via `alt_traits`."""
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id, race_id, db_session, flex_ability="GE", alt_traits=["+2 auf Geschicklichkeit"]
        ),
    )
    assert response.status_code == 422


def test_create_character_rejects_conflicting_alt_traits(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)

    kuestenbewohner_id = db_session.scalar(select(BaseRaceAbility.id).where(BaseRaceAbility.name == "Küstenbewohner"))
    waffenvertrautheit_id = db_session.scalar(
        select(BaseRaceAbility.id).where(BaseRaceAbility.name == "Elfische Waffenvertrautheit")
    )
    # Force a genuine conflict for this test: two alternates both replacing
    # "Elfische Waffenvertrautheit" (no such overlap exists in the seed data
    # today, see `race_ability_replacements.json`).
    db_session.add(
        RaceAbilityReplacement(
            base_race_id=UUID(race_id), ability_id=kuestenbewohner_id, replaces_ability_id=waffenvertrautheit_id
        )
    )
    db_session.commit()

    user_id = _create_user(client)
    response = client.post(
        "/api/characters",
        json=_character_payload(user_id, race_id, db_session, alt_traits=["Eisenkultur", "Küstenbewohner"]),
    )
    assert response.status_code == 422


def test_create_character_persists_skill_ranks_on_highest_level(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    klettern_id = _skill_id(client, db_session, "Klettern")
    reiten_id = _skill_id(client, db_session, "Reiten")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            classes=[{"class_name": "Waldläufer", "level": 3}],
            skill_ranks={klettern_id: 3, reiten_id: 2},
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["skill_ranks"] == {klettern_id: 3, reiten_id: 2}

    character = db_session.get(Character, body["id"])
    # No per-level breakdown for multi-level creation: both skills land as a
    # single audit row each, tied to the highest CharacterLevel created.
    highest_level = max(character.levels, key=lambda level: level.level)
    ranks = db_session.scalars(
        select(CharacterSkillRank).where(CharacterSkillRank.level_id == highest_level.id)
    ).all()
    assert {(str(r.skill_id), r.ranks) for r in ranks} == {(klettern_id, 3), (reiten_id, 2)}


def test_create_character_skill_ranks_exceeding_level_are_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    klettern_id = _skill_id(client, db_session, "Klettern")

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            classes=[{"class_name": "Waldläufer", "level": 1}],
            skill_ranks={klettern_id: 2},
        ),
    )
    assert response.status_code == 422


def test_create_character_skill_ranks_exceeding_budget_are_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    # Waldläufer's skillPointsBase is 6; INT modifier is 0 for these scores,
    # so 7 skills at 1 rank each (level cap at level 1) overspends the budget.
    skill_names = ["Akrobatik", "Fingerfertigkeit", "Fluchtkunst", "Heimlichkeit", "Reiten", "Falle entschärfen", "Klettern"]
    skill_ranks = {_skill_id(client, db_session, name): 1 for name in skill_names}

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            classes=[{"class_name": "Waldläufer", "level": 1}],
            skill_ranks=skill_ranks,
        ),
    )
    assert response.status_code == 422


def test_create_character_with_unknown_skill_id_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            flex_ability="ST",
            skill_ranks={"00000000-0000-0000-0000-000000000000": 1},
        ),
    )
    assert response.status_code == 422


def test_get_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session)).json()

    response = client.get(f"/api/characters/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Elyra"
    assert response.json()["ability_scores"] == DEFAULT_ABILITY_SCORES


def test_get_unknown_character_returns_404(client: TestClient) -> None:
    response = client.get("/api/characters/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_rename_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session)).json()

    response = client.patch(f"/api/characters/{created['id']}", json={"name": "Elyra Silberauge"})
    assert response.status_code == 200
    assert response.json()["name"] == "Elyra Silberauge"


def test_delete_character(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    created = client.post("/api/characters", json=_character_payload(user_id, race_id, db_session)).json()

    response = client.delete(f"/api/characters/{created['id']}")
    assert response.status_code == 204

    response = client.get(f"/api/characters/{created['id']}")
    assert response.status_code == 404


def test_mock_character_fixtures_still_served(client: TestClient) -> None:
    response = client.get("/api/characters/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Elyra Silberauge"
