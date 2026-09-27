"""Betäubender Schlag (Stunning Fist, GRW S. 120) — the two character-facing
numbers this app can compute (uses/day, save DC; the actual "target is
stunned" effect lands on an opponent this app has no model for at all).
Two independent grant paths: a monk's automatic no-`CharacterFeat`-row
grant at level 1 (`rules/classes/moench.py`'s own `DAILY_LIMITS`/
`SAVE_DC_HANDLERS`, keyed by the class-ability wrapper id) and the generic
case of an actual `CharacterFeat` pick (`rules/feats.py`'s own slice)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.rules.classes.moench import BETAEUBENDER_SCHLAG_ABILITY_ID
from app.rules.feats import BETAEUBENDER_SCHLAG
from test_characters import (
    DEFAULT_ABILITY_SCORES,
    _character_payload,
    _create_user,
    _elf_race_id,
    _feat_id,
    _feat_selection,
)


def _action(sheet: dict, source_id: str) -> dict | None:
    return next((a for a in sheet["actions"] if a["sourceId"] == source_id), None)


def _create_moench(
    client: TestClient,
    db_session: Session,
    *,
    classes: list[dict],
    archetypes: list[str] | None = None,
    ability_scores: dict[str, int] | None = None,
) -> dict:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    if archetypes:
        classes = [{**classes[0], "archetypes": archetypes}, *classes[1:]]
    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=classes,
        ability_scores=ability_scores or DEFAULT_ABILITY_SCORES,
        point_budget=25,
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.json()
    character_id = response.json()["id"]
    return client.get(f"/api/characters/{character_id}").json()


def test_moench_gets_it_automatically_at_level_1_with_no_feat_pick(client: TestClient, db_session: Session) -> None:
    body = _create_moench(
        client,
        db_session,
        classes=[{"class_name": "Mönch", "level": 1}],
        ability_scores={**DEFAULT_ABILITY_SCORES, "WE": 16},
    )
    action = _action(body, str(BETAEUBENDER_SCHLAG_ABILITY_ID))
    assert action is not None
    assert action["sourceType"] == "class_ability"
    assert action["usesPerDay"] == 1  # moench_level=1 + other_levels(0)//4
    assert action["dc"] == 10 + 0 + 3  # 10 + level(1)//2 + WE 16's +3 mod
    # No actual CharacterFeat row — the monk's grant is a class-ability
    # wrapper, not a pick (`BaseClassAbilityGrantedFeat`'s docstring).
    assert str(BETAEUBENDER_SCHLAG) not in [f["feat_id"] for f in body["feats"]]


def test_moench_uses_per_day_scales_with_monk_and_other_levels(client: TestClient, db_session: Session) -> None:
    body = _create_moench(
        client,
        db_session,
        classes=[{"class_name": "Mönch", "level": 4}, {"class_name": "Kämpfer", "level": 4}],
    )
    action = _action(body, str(BETAEUBENDER_SCHLAG_ABILITY_ID))
    assert action is not None
    # moench_level=4 + other_levels(4)//4=1 -> 5.
    assert action["usesPerDay"] == 5
    assert action["dc"] == 10 + 8 // 2 + 0  # WE 10 -> +0 mod


def test_beschuppte_faust_uses_charisma_for_the_dc(client: TestClient, db_session: Session) -> None:
    body = _create_moench(
        client,
        db_session,
        classes=[{"class_name": "Mönch", "level": 8}],
        archetypes=["Beschuppte Faust"],
        ability_scores={"ST": 7, "GE": 10, "KO": 10, "IN": 10, "WE": 16, "CH": 18},
    )
    action = _action(body, str(BETAEUBENDER_SCHLAG_ABILITY_ID))
    assert action is not None
    # CH 18 -> +4, not WE 16's +3 - proves Drachenmacht's WIS->CHA swap is read.
    assert action["dc"] == 10 + 8 // 2 + 4


def test_use_endpoint_decrements_the_monks_daily_uses(client: TestClient, db_session: Session) -> None:
    body = _create_moench(
        client,
        db_session,
        classes=[{"class_name": "Mönch", "level": 8}],
        ability_scores={**DEFAULT_ABILITY_SCORES, "WE": 16},
    )
    character_id = body["id"]
    assert _action(body, str(BETAEUBENDER_SCHLAG_ABILITY_ID))["usesRemainingToday"] == 8

    use = client.patch(f"/api/characters/{character_id}/class-abilities/{BETAEUBENDER_SCHLAG_ABILITY_ID}/use")
    assert use.status_code == 200

    body = client.get(f"/api/characters/{character_id}").json()
    assert _action(body, str(BETAEUBENDER_SCHLAG_ABILITY_ID))["usesRemainingToday"] == 7


def test_generic_feat_pick_uses_the_non_monk_formula(client: TestClient, db_session: Session) -> None:
    """A non-monk character who took the feat directly (e.g. a Kämpfer bonus
    feat) gets the generic "floor(character level / 4)" formula instead of
    the monk's, resolved via an actual `CharacterFeat` row rather than the
    class-ability wrapper id."""
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    feat_id = _feat_id(client, db_session, "Betäubender Schlag")

    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[{"class_name": "Kämpfer", "level": 8}],
        ability_scores={**DEFAULT_ABILITY_SCORES, "WE": 16},
        feats=[_feat_selection(feat_id)],
    )
    response = client.post("/api/characters", json=payload)
    assert response.status_code == 201, response.json()
    character_id = response.json()["id"]

    body = client.get(f"/api/characters/{character_id}").json()
    action = _action(body, feat_id)
    assert action is not None
    assert action["sourceType"] == "feat"
    assert action["usesPerDay"] == 8 // 4
    assert action["dc"] == 10 + 8 // 2 + 3  # WE 16's +3 mod

    use = client.patch(f"/api/characters/{character_id}/class-abilities/{feat_id}/use")
    assert use.status_code == 200
    body = client.get(f"/api/characters/{character_id}").json()
    assert _action(body, feat_id)["usesRemainingToday"] == 8 // 4 - 1
