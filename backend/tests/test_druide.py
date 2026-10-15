"""Druide as a complete class — roadmap slice 10, step 0a
(http://prd.5footstep.de/Grundregelwerk/Klassen/Druide,
`scripts/import_druide.py`, `rules/classes/druide.py`)."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.rules.classes.druide import (
    DRUIDE_ROOT_CLASS_ID,
    TIERGESTALT_UNLIMITED_USES,
    WALDLAEUFER_ROOT_CLASS_ID,
    tierempathie_bonus,
    tiergestalt_uses_per_day,
)
from app.rules.context import CharacterContext
from app.seed.class_option_seed import seed_class_options
from app.seed.class_seed import seed_classes
from app.seed.skill_seed import seed_skills

from test_characters import _character_payload, _create_user, _human_race_id, _item_id
from test_weapon_slots import _equip, _weapon_attack

TIERGESTALT_ABILITY_ID = "248a0b40-17ab-5124-a2bc-cf50e76692e1"
TIEREMPATHIE_ABILITY_ID = "ebd5060b-066a-4bc0-bdfa-064222de85bf"
UEBERLEBENSKUNST_SKILL_ID = "1b9fe08d-09e0-46c8-8772-dd573cab6fff"


def _create_druide(client: TestClient, db_session: Session, classes: list[dict]) -> dict:
    """Human with the flex +2 on CH, so CH is 10 (mod +0) and the
    Tierempathie bonus is just the summed class levels."""
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    response = client.post(
        "/api/characters", json=_character_payload(user_id, race_id, db_session, classes=classes, flex_ability="CH")
    )
    assert response.status_code == 201, response.text
    return client.get(f"/api/characters/{response.json()['id']}").json()


def _feature(sheet: dict, name: str) -> dict | None:
    return next((f for f in sheet["classFeatures"] if f["name"] == name), None)


def test_druide_class_skills_are_the_pages_13(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)
    seed_skills(db_session)

    druide = next(c for c in client.get("/api/classes").json() if c["name"] == "Druide")
    skills = {s["id"]: s["name"] for s in client.get("/api/skills").json()}

    assert {skills[sid] for sid in druide["classSkills"]} == {
        "Beruf",
        "Fliegen",
        "Handwerk",
        "Heilkunde",
        "Klettern",
        "Mit Tieren umgehen",
        "Reiten",
        "Schwimmen",
        "Wahrnehmung",
        "Wissen (Geographie)",
        "Wissen (Natur)",
        "Überlebenskunst",
        "Zauberkunde",
    }


def test_druide_level_20_has_every_class_feature(client: TestClient, db_session: Session) -> None:
    sheet = _create_druide(
        client, db_session, [{"class_name": "Druide", "level": 20, "options": {"bond": ["Tiergefährte"]}}]
    )
    names = {f["name"] for f in sheet["classFeatures"]}

    assert {
        "Umgang mit Waffen und Rüstungen",
        "Spontanes Zaubern",
        "Bonussprachen",
        "Bund mit der Natur",
        "Naturgespür",
        "Tierempathie",
        "Unterholz durchqueren",
        "Spurloser Schritt",
        "Lockruf der Natur widerstehen",
        "Tiergestalt",
        "Immunität gegen Gifte",
        "Tausend Gesichter",
        "Zeitloser Körper",
        "Tiergefährte (Druide)",
    } <= names
    assert "Domäne (Natur)" not in names
    assert "Beliebig oft".lower() in _feature(sheet, "Tiergestalt")["summary"]


def test_nature_domain_choices_require_the_domain_bond(client: TestClient, db_session: Session) -> None:
    seed_classes(db_session)
    seed_class_options(db_session)

    druide = next(c for c in client.get("/api/classes").json() if c["name"] == "Druide")
    group = next(g for g in druide["optionGroups"] if g["key"] == "nature_domain")

    assert {c["name"] for c in group["choices"]} == {
        "Domäne der Erde",
        "Domäne des Feuers",
        "Domäne der Luft",
        "Domäne der Pflanzen",
        "Domäne der Tiere",
        "Domäne des Wassers",
        "Domäne des Wetters",
    }
    assert all(c["requiresChoice"] == {"groupKey": "bond", "name": "Domäne (Natur)"} for c in group["choices"])


def test_nature_domain_grants_the_kleriker_domain_powers_at_druide_level(
    client: TestClient, db_session: Session
) -> None:
    sheet = _create_druide(
        client,
        db_session,
        [
            {
                "class_name": "Druide",
                "level": 6,
                "options": {"bond": ["Domäne (Natur)"], "nature_domain": ["Domäne der Erde"]},
            }
        ],
    )
    names = {f["name"] for f in sheet["classFeatures"]}

    assert {"Domäne (Natur)", "Verliehene Fähigkeiten (Domäne der Erde)", "Säuregeschoss", "Säureresistenz"} <= names
    assert "Tiergefährte (Druide)" not in names


def test_nature_domain_without_the_domain_bond_is_rejected(client: TestClient, db_session: Session) -> None:
    user_id = _create_user(client)
    race_id = _human_race_id(client, db_session)
    payload = _character_payload(
        user_id,
        race_id,
        db_session,
        classes=[
            {
                "class_name": "Druide",
                "level": 1,
                "options": {"bond": ["Tiergefährte"], "nature_domain": ["Domäne der Erde"]},
            }
        ],
    )

    response = client.post("/api/characters", json=payload)

    assert response.status_code == 422
    assert "Domäne (Natur)" in response.json()["detail"]


def test_tierempathie_sums_druide_and_waldlaeufer_levels(client: TestClient, db_session: Session) -> None:
    sheet = _create_druide(
        client,
        db_session,
        [{"class_name": "Druide", "level": 4}, {"class_name": "Waldläufer", "level": 2}],
    )

    tierempathie = [f for f in sheet["classFeatures"] if f["key"] == TIEREMPATHIE_ABILITY_ID]
    assert len(tierempathie) == 1
    assert tierempathie[0]["summary"].startswith("1W20 + 6")
    assert tierempathie[0]["hasHandler"] is True


@pytest.mark.parametrize(
    ("level", "expected"),
    [(3, 0), (4, 1), (5, 1), (6, 2), (10, 4), (18, 8), (19, 8), (20, TIERGESTALT_UNLIMITED_USES)],
)
def test_tiergestalt_uses_per_day(level: int, expected: int) -> None:
    context = CharacterContext(level_counts_by_root_id={DRUIDE_ROOT_CLASS_ID: level})
    assert tiergestalt_uses_per_day(context) == expected


def test_tierempathie_bonus_includes_charisma() -> None:
    context = CharacterContext(
        ability_scores={"CH": 14},
        level_counts_by_root_id={DRUIDE_ROOT_CLASS_ID: 3, WALDLAEUFER_ROOT_CLASS_ID: 1, UUID(int=1): 5},
    )
    assert tierempathie_bonus(context) == 3 + 1 + 2


def test_tiergestalt_is_a_daily_action_from_level_4_with_its_forms(client: TestClient, db_session: Session) -> None:
    sheet = _create_druide(client, db_session, [{"class_name": "Druide", "level": 8}])

    action = next(a for a in sheet["actions"] if a["sourceId"] == TIERGESTALT_ABILITY_ID)
    assert action["usesPerDay"] == 3
    assert action["usesRemainingToday"] == 3
    assert _feature(sheet, "Tiergestalt")["summary"] == (
        "3/Tag, Dauer 8 Std.; wie Bestiengestalt III, Elementargestalt II, Pflanzengestalt I"
    )


def test_naturgespuer_adds_2_to_ueberlebenskunst(client: TestClient, db_session: Session) -> None:
    sheet = _create_druide(client, db_session, [{"class_name": "Druide", "level": 1}])

    skill = next(s for s in sheet["skills"] if s["key"] == UEBERLEBENSKUNST_SKILL_ID)
    assert any(entry["label"] == "Naturgespür" and entry["value"] == 2 for entry in skill["breakdown"])


def test_druide_is_proficient_with_its_weapon_list_only(client: TestClient, db_session: Session) -> None:
    sheet = _create_druide(client, db_session, [{"class_name": "Druide", "level": 1}])
    character_id = sheet["id"]

    for weapon_name, expected_note in (("Krummsäbel", None), ("Keule", None), ("Langschwert", "Nicht geübt (-4)")):
        item_id = _item_id(client, db_session, weapon_name)
        client.post(f"/api/characters/{character_id}/gear", json={"item_id": item_id, "quantity": 1})
        _equip(client, character_id, "hauptwaffe", item_id)
        weapon = _weapon_attack(client.get(f"/api/characters/{character_id}").json(), "hauptwaffe")
        assert weapon.get("note") == expected_note, weapon_name
