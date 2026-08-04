from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Character
from app.seed.class_seed import seed_classes
from test_characters import (
    DEFAULT_ABILITY_SCORES,
    _character_payload,
    _create_user,
    _elf_race_id,
    _feat_id,
    _feat_selection,
    _human_race_id,
    _item_id,
    _skill_id,
    _spells_by_class,
)


def _class_id(client: TestClient, db_session: Session, name: str) -> str:
    seed_classes(db_session)
    classes = client.get("/api/classes").json()
    return next(c["id"] for c in classes if c["name"] == name)


def _level_up_payload(base_class_id: str, hit_points: int, **overrides) -> dict:
    payload = {
        "target": {"mode": "existing", "base_class_id": base_class_id},
        "hit_points": hit_points,
    }
    payload.update(overrides)
    return payload


def _create_level_n_character(
    client: TestClient, db_session: Session, race_id: str, class_name: str, level: int, **overrides
) -> str:
    """Creates a level-`level` single-class character and returns its id."""
    response = client.post(
        "/api/characters",
        json=_character_payload(
            _create_user(client),
            race_id,
            db_session,
            classes=[{"class_name": class_name, "level": level}],
            **overrides,
        ),
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_level_up_persists_new_level_on_existing_class(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    # Waldläufer is a d10; character level 2 grants no new feat (base_feat_count(2) == base_feat_count(1)).
    response = client.post(f"/api/characters/{character_id}/level-up", json=_level_up_payload(base_class_id, 6))
    assert response.status_code == 201
    body = response.json()
    assert body["level"] == 2
    assert body["classes"] == [{"class_name": "Waldläufer", "level": 2, "archetypes": [], "is_favored": True, "options": {}}]

    sheet = client.get(f"/api/characters/{character_id}").json()
    # Level 1 (auto-maxed d10) + rolled 6, no CON mod (KO 13 -> +1, elf -2 KO -> 11 -> +0).
    assert sheet["hp"]["max"] == 16


def test_level_up_rejects_hit_points_out_of_range(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(f"/api/characters/{character_id}/level-up", json=_level_up_payload(base_class_id, 11))
    assert response.status_code == 422


def test_level_up_unknown_character_is_404(client: TestClient, db_session: Session) -> None:
    base_class_id = _class_id(client, db_session, "Waldläufer")
    response = client.post(
        "/api/characters/00000000-0000-0000-0000-000000000000/level-up",
        json=_level_up_payload(base_class_id, 5),
    )
    assert response.status_code == 404


def test_level_up_rejects_base_class_id_not_owned_by_character(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    other_class_id = _class_id(client, db_session, "Kämpfer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(f"/api/characters/{character_id}/level-up", json=_level_up_payload(other_class_id, 5))
    assert response.status_code == 422


def test_level_up_grants_a_feat_on_an_odd_level(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    # Level 1 -> 2 grants no feat; level 2 -> 3 does (base_feat_count(3) - base_feat_count(2) == 1).
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 2, hit_points={"2": 5})

    ausweichen_id = _feat_id(client, db_session, "Ausweichen")
    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, feats=[_feat_selection(ausweichen_id)]),
    )
    assert response.status_code == 201
    body = response.json()
    assert {f["feat_id"] for f in body["feats"]} == {ausweichen_id}


def test_level_up_rejects_a_feat_on_an_even_level(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    ausweichen_id = _feat_id(client, db_session, "Ausweichen")
    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, feats=[_feat_selection(ausweichen_id)]),
    )
    assert response.status_code == 422


def test_level_up_rejects_a_feat_already_known(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    ausweichen_id = _feat_id(client, db_session, "Ausweichen")
    character_id = _create_level_n_character(
        client, db_session, race_id, "Waldläufer", 2, hit_points={"2": 5}, feats=[_feat_selection(ausweichen_id)]
    )

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, feats=[_feat_selection(ausweichen_id)]),
    )
    assert response.status_code == 422


def test_level_up_rejects_too_many_feats_for_the_delta(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 2, hit_points={"2": 5})

    langschwert_id = _item_id(client, db_session, "Langschwert")
    feats = [
        _feat_selection(_feat_id(client, db_session, "Ausweichen")),
        _feat_selection(_feat_id(client, db_session, "Waffenfokus"), chosen_weapon_id=langschwert_id),
    ]
    response = client.post(f"/api/characters/{character_id}/level-up", json=_level_up_payload(base_class_id, 5, feats=feats))
    assert response.status_code == 422


def test_level_up_fighter_bonus_feat_on_even_level(client: TestClient, db_session: Session) -> None:
    """Kämpfer grants a bonus combat feat at 1st and every even level - level 1 -> 2
    grants no *regular* feat slot (base_feat_count(2) == base_feat_count(1)) but does
    grant the class bonus slot, so exactly one feat still fits."""
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Kämpfer")
    character_id = _create_level_n_character(client, db_session, race_id, "Kämpfer", 1)

    ausweichen_id = _feat_id(client, db_session, "Ausweichen")
    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 6, feats=[_feat_selection(ausweichen_id)]),
    )
    assert response.status_code == 201


def test_level_up_requires_ability_increase_on_4th_level(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(
        client, db_session, race_id, "Waldläufer", 3, hit_points={"2": 5, "3": 5}
    )

    without_increase = client.post(
        f"/api/characters/{character_id}/level-up", json=_level_up_payload(base_class_id, 5)
    )
    assert without_increase.status_code == 422

    with_increase = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, ability_increase="ST"),
    )
    assert with_increase.status_code == 201
    body = with_increase.json()
    assert body["ability_scores"]["ST"] == DEFAULT_ABILITY_SCORES["ST"] + 1


def test_level_up_rejects_ability_increase_on_an_ineligible_level(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, ability_increase="ST"),
    )
    assert response.status_code == 422


def test_level_up_skill_ranks_within_and_over_budget(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)
    skill_id = _skill_id(client, db_session, "Akrobatik")

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 5, skill_ranks=[skill_id]),
    )
    assert response.status_code == 201
    assert response.json()["skill_ranks"][skill_id] == 1

    # Absurdly oversized request - guaranteed to exceed any class's per-level budget.
    character_id_2 = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)
    other_skill_ids = [
        _skill_id(client, db_session, name)
        for name in [
            "Akrobatik",
            "Mit Tieren umgehen",
            "Klettern",
            "Fingerfertigkeit",
            "Fliegen",
            "Heilkunde",
            "Heimlichkeit",
            "Reiten",
            "Schwimmen",
            "Wahrnehmung",
        ]
    ]
    response = client.post(
        f"/api/characters/{character_id_2}/level-up",
        json=_level_up_payload(base_class_id, 5, skill_ranks=other_skill_ids),
    )
    assert response.status_code == 422


def test_level_up_multiclass_into_a_new_class_with_archetype(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json={
            "target": {
                "mode": "new",
                "class_name": "Kämpfer",
                "archetypes": ["Zwei-Waffen-Kämpfer"],
            },
            "hit_points": 6,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["level"] == 2
    kaempfer = next(c for c in body["classes"] if c["class_name"] == "Kämpfer")
    assert kaempfer["level"] == 1
    assert kaempfer["archetypes"] == ["Zwei-Waffen-Kämpfer"]
    assert kaempfer["is_favored"] is False


def test_level_up_multiclass_into_a_new_class_with_option_group(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json={
            "target": {
                "mode": "new",
                "class_name": "Kleriker",
                "options": {"domain": ["Domäne der Sonne", "Domäne des Todes"]},
            },
            "hit_points": 6,
        },
    )
    assert response.status_code == 201
    body = response.json()
    kleriker = next(c for c in body["classes"] if c["class_name"] == "Kleriker")
    assert kleriker["options"] == {"domain": ["Domäne der Sonne", "Domäne des Todes"]}


def test_level_up_rejects_multiclassing_into_an_already_owned_class(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json={"target": {"mode": "new", "class_name": "Waldläufer"}, "hit_points": 6},
    )
    assert response.status_code == 422


def test_level_up_spontaneous_caster_rejects_new_spell_when_grade_budget_unchanged(
    client: TestClient, db_session: Session
) -> None:
    """Hexenmeister's grade-1 known-spell cap is 2 at both character level 1
    and 2 (no delta) - a character who already knows 2 grade-1 spells can't
    pick a 3rd just by leveling up to 2."""
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Hexenmeister")
    grade1_known = [spells["Magisches Geschoss"], spells["Schild"]]
    character_id = _create_level_n_character(
        client, db_session, race_id, "Hexenmeister", 1, spell_ids={base_class_id: grade1_known}
    )

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 1, spell_id=spells["Farbenstrahl"]),
    )
    assert response.status_code == 422


def test_level_up_spontaneous_caster_grants_new_spell_when_grade_budget_grows(
    client: TestClient, db_session: Session
) -> None:
    """Hexenmeister's grade-1 known-spell cap grows from 2 to 3 between
    character level 2 and 3."""
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Hexenmeister")
    grade1_known = [spells["Magisches Geschoss"], spells["Schild"]]
    character_id = _create_level_n_character(
        client, db_session, race_id, "Hexenmeister", 2, hit_points={"2": 1}, spell_ids={base_class_id: grade1_known}
    )

    response = client.post(
        f"/api/characters/{character_id}/level-up",
        json=_level_up_payload(base_class_id, 1, spell_id=spells["Farbenstrahl"]),
    )
    assert response.status_code == 201
    assert spells["Farbenstrahl"] in response.json()["spell_ids"][base_class_id]


def test_level_up_arcane_prepared_new_spell_within_and_over_grade(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Magier")
    cantrips = [spells["Licht"], spells["Kleiner Trick"], spells["Widerstand"]]

    character_id_a = _create_level_n_character(
        client, db_session, race_id, "Magier", 1, spell_ids={base_class_id: cantrips}
    )
    # Level 1 -> 2 still only unlocks grades {0, 1} (grade 2 opens at level 3).
    ok_response = client.post(
        f"/api/characters/{character_id_a}/level-up",
        json=_level_up_payload(base_class_id, 3, spell_id=spells["Magisches Geschoss"]),
    )
    assert ok_response.status_code == 201

    character_id_b = _create_level_n_character(
        client, db_session, race_id, "Magier", 1, spell_ids={base_class_id: cantrips}
    )
    rejected_response = client.post(
        f"/api/characters/{character_id_b}/level-up",
        json=_level_up_payload(base_class_id, 3, spell_id=spells["Nebelwolke"]),
    )
    assert rejected_response.status_code == 422


def test_progression_and_history_reflect_a_real_level_up(client: TestClient, db_session: Session) -> None:
    race_id = _elf_race_id(client, db_session)
    base_class_id = _class_id(client, db_session, "Waldläufer")
    character_id = _create_level_n_character(client, db_session, race_id, "Waldläufer", 1)

    before = client.get(f"/api/characters/{character_id}/progression").json()
    assert before["classes"][0]["level"] == 1
    assert before["history"] == []

    response = client.post(f"/api/characters/{character_id}/level-up", json=_level_up_payload(base_class_id, 6))
    assert response.status_code == 201

    after = client.get(f"/api/characters/{character_id}/progression").json()
    assert after["classes"][0]["level"] == 2
    assert len(after["history"]) == 1
    assert "Waldläufer" in after["history"][0]["description"]

    history = client.get(f"/api/characters/{character_id}/history").json()
    assert history == after["history"]


def test_mock_progression_and_history_fixtures_still_served(client: TestClient) -> None:
    assert client.get("/api/characters/1/progression").status_code == 200
    assert client.get("/api/characters/1/history").json() == []
