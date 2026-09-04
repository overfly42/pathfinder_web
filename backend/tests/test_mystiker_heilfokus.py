"""Mystiker's (Oracle's) "Stoßgebete-Fokus" (Kurieren/Verletzen) — real PF1e
rule: at 1st level an oracle chooses once between adding every "cure" or
every "inflict" spell to her spells known, each as soon as she's capable of
casting it, for free. `scripts/import_mystiker_heilfokus_spells.py` seeds the
`BaseClassSpellGrant` rows for the already-existing `heilfokus` option
group; this exercises the same `granted_option_choice_spells` wiring
`test_hexe_patron.py` covers for Hexe's Schutzherr, plus the new
`/api/granted-spells-by-choice` endpoint and the manual-pick rejection guard
(`routers/characters.py`'s `_granted_spell_ids`)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Character
from app.seed.spell_seed import seed_spells
from test_characters import _character_payload, _create_user, _elf_race_id, _spells_by_class
from test_level_up import _class_id, _level_up_payload


def test_granted_spells_by_choice_lists_mystiker_heilfokus(client: TestClient, db_session: Session) -> None:
    _spells_by_class(client, db_session, "Mystiker")  # seeds classes/options/spells

    by_choice = client.get("/api/granted-spells-by-choice").json()
    mystiker = by_choice["Mystiker"]

    heilen = {(s["name"], s["grade"], s["level"]) for s in mystiker["Wunden heilen"]}
    assert ("Leichte Wunden heilen", 1, 1) in heilen
    assert ("Mittelschwere Wunden heilen", 2, 4) in heilen
    assert ("Massen-Kritische Wunden heilen", 8, 16) in heilen
    assert len(heilen) == 8

    verursachen = {(s["name"], s["grade"], s["level"]) for s in mystiker["Wunden verursachen"]}
    assert ("Leichte Wunden verursachen", 1, 1) in verursachen
    assert len(verursachen) == 8
    assert not any("heilen" in name for name, *_ in verursachen)


def test_mystiker_heilfokus_grants_cure_spells_at_creation(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, _ = _spells_by_class(client, db_session, "Mystiker")
    seed_spells(db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Mystiker", "level": 4, "options": {"heilfokus": ["Wunden heilen"]}}],
        ),
    )
    assert response.status_code == 201
    character_id = response.json()["id"]

    db_character = db_session.get(Character, character_id)
    known = {str(sid) for sid in db_character.spell_ids[base_class_id]}
    by_class = client.get("/api/spells-by-class").json()
    name_to_id = {s["name"]: s["id"] for s in by_class["Mystiker"]}

    assert name_to_id["Leichte Wunden heilen"] in known
    assert name_to_id["Mittelschwere Wunden heilen"] in known  # grade 2, reached at level 4
    assert name_to_id["Schwere Wunden heilen"] not in known  # grade 3, needs level 6
    assert name_to_id["Leichte Wunden verursachen"] not in known  # the other track wasn't chosen


def test_mystiker_heilfokus_verletzen_grants_inflict_not_cure(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, _ = _spells_by_class(client, db_session, "Mystiker")
    seed_spells(db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Mystiker", "level": 1, "options": {"heilfokus": ["Wunden verursachen"]}}],
        ),
    )
    assert response.status_code == 201
    character_id = response.json()["id"]

    db_character = db_session.get(Character, character_id)
    known = {str(sid) for sid in db_character.spell_ids[base_class_id]}
    by_class = client.get("/api/spells-by-class").json()
    name_to_id = {s["name"]: s["id"] for s in by_class["Mystiker"]}

    assert name_to_id["Leichte Wunden verursachen"] in known
    assert name_to_id["Leichte Wunden heilen"] not in known


def test_mystiker_heilfokus_spell_rejected_as_manual_pick(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _elf_race_id(client, db_session)
    base_class_id, spells = _spells_by_class(client, db_session, "Mystiker")
    seed_spells(db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            user_id,
            race_id,
            db_session,
            classes=[{"class_name": "Mystiker", "level": 1, "options": {"heilfokus": ["Wunden heilen"]}}],
            spell_ids={base_class_id: [spells["Leichte Wunden heilen"]]},
        ),
    )
    assert response.status_code == 422
    assert "already known automatically" in response.json()["detail"]


def test_mystiker_heilfokus_grants_new_grade_on_level_up_without_duplicating(
    client: TestClient, db_session: Session
) -> None:
    race_id = _elf_race_id(client, db_session)
    mystiker_id = _class_id(client, db_session, "Mystiker")  # seeds classes
    base_class_id, _ = _spells_by_class(client, db_session, "Mystiker")
    seed_spells(db_session)

    response = client.post(
        "/api/characters",
        json=_character_payload(
            _create_user(client),
            race_id,
            db_session,
            classes=[{"class_name": "Mystiker", "level": 1, "options": {"heilfokus": ["Wunden heilen"]}}],
        ),
    )
    assert response.status_code == 201
    character_id = response.json()["id"]

    for target_level in (2, 3, 4):  # grade 2 (Mittelschwere) unlocks at level 4
        ability_increase = "IN" if target_level % 4 == 0 else None
        level_up = client.post(
            f"/api/characters/{character_id}/level-up",
            json=_level_up_payload(mystiker_id, hit_points=4, ability_increase=ability_increase),
        )
        assert level_up.status_code == 201

    db_character = db_session.get(Character, character_id)
    known = [str(sid) for sid in db_character.spell_ids[base_class_id]]
    by_class = client.get("/api/spells-by-class").json()
    name_to_id = {s["name"]: s["id"] for s in by_class["Mystiker"]}

    assert known.count(name_to_id["Leichte Wunden heilen"]) == 1
    assert known.count(name_to_id["Mittelschwere Wunden heilen"]) == 1
